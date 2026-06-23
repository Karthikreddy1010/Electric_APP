import numpy as np
import pandas as pd
import logging
from pathlib import Path
from prophet import Prophet
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller

logger = logging.getLogger(__name__)

# Weather feature columns used by the models
WEATHER_COLS = ["temp_avg", "hdd", "cdd"]
EXOG_COLS = ["temp_avg", "hdd", "cdd", "demand_lag1", "demand_lag7"]


def safe_mape(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    mask = y_true != 0
    if not np.any(mask):
        return np.nan
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


class ElectricityDemandForecaster:
    def __init__(self, data_path="data/raw/eia_pjm_daily_demand.csv"):
        # Resolve the full path based on project root if relative
        if not Path(data_path).is_absolute():
            project_root = Path(__file__).resolve().parent.parent
            self.data_path = project_root / data_path
        else:
            self.data_path = Path(data_path)

        self.weights = {"prophet": 0.7, "sarima": 0.3}
        self.metrics = {
            "ensemble": {"MAE": np.nan, "RMSE": np.nan, "MAPE": np.nan},
            "prophet": {"MAE": np.nan, "RMSE": np.nan, "MAPE": np.nan},
            "sarima": {"MAE": np.nan, "RMSE": np.nan, "MAPE": np.nan}
        }
        self.confidence_scores = {
            "ensemble": np.nan, "prophet": np.nan, "sarima": np.nan
        }
        self.df_clean = None
        self.last_trained = None

    def prepare_data(self):
        """Parse, clean and feature engineer PJM daily demand + Open-Meteo weather."""
        logger.info(f"Loading data from {self.data_path}")
        df = pd.read_csv(self.data_path)

        # Parse date (daily CSV uses YYYY-MM-DD format)
        df["date"] = pd.to_datetime(df["period"])

        # Step 1: Clean anomalies (unphysical zeros/negatives and extreme spikes)
        df.loc[df["value"] <= 0, "value"] = np.nan
        df.loc[df["value"] > 100000, "value"] = np.nan

        # Step 2: Smooth dropouts by linear interpolation per sub-balancing area
        df["value"] = df.groupby("subba")["value"].transform(
            lambda x: x.interpolate(method="linear", limit_direction="both")
        )

        # Step 3: Aggregate all sub-balancing areas per day -> PJM total per day
        daily = df.groupby("date").agg(
            demand_mw=("value", "sum"),
            peak_mw=("value", "max"),
            trough_mw=("value", "min"),
            subbas_recorded=("value", "count"),
        ).reset_index()

        daily = daily.sort_values("date").set_index("date")

        # Step 4: Drop days with incomplete sub-BA coverage (expect 4 sub-BAs)
        partial_days = daily["subbas_recorded"] < len(["AE", "JC", "PS", "RECO"])
        if partial_days.any():
            logger.info(f"Dropping {partial_days.sum()} partial days (< 4 sub-BAs)")
            daily = daily[~partial_days]

        # Step 5: Ensure daily continuity
        daily = daily.asfreq("D")

        # Step 6: Handle any remaining missing values via time interpolation
        for col in ["demand_mw", "peak_mw", "trough_mw"]:
            daily[col] = daily[col].interpolate(method="time")

        # Step 7: Feature engineering
        daily["dayofweek"] = daily.index.dayofweek
        daily["month"] = daily.index.month
        daily["is_weekend"] = (daily["dayofweek"] >= 5).astype(int)
        daily["load_factor"] = daily["trough_mw"] / daily["peak_mw"]

        # Keep subbas_recorded for historical filtering in get_forecast()
        daily["hours_recorded"] = daily["subbas_recorded"]

        # Step 8: Merge REAL weather data from Open-Meteo
        weather_path = self.data_path.parent / "weather_openmeteo.csv"
        if weather_path.exists():
            weather_df = pd.read_csv(weather_path)
            weather_df["date"] = pd.to_datetime(weather_df["date"])
            weather_df = weather_df.drop_duplicates(subset=["date"]).set_index("date")
            daily = daily.join(weather_df[WEATHER_COLS], how="left")
            # Only interpolate small gaps (<=3 days), NOT forward-fill
            for col in WEATHER_COLS:
                daily[col] = daily[col].interpolate(method="linear", limit=3)
            # Drop rows where weather is still missing (large gaps)
            weather_missing = daily[WEATHER_COLS].isnull().any(axis=1).sum()
            if weather_missing > 0:
                logger.warning(f"{weather_missing} days missing weather data after interpolation — filling with 0")
                daily[WEATHER_COLS] = daily[WEATHER_COLS].fillna(0)
            logger.info("Successfully merged Open-Meteo weather data (temp_avg, hdd, cdd).")
        else:
            logger.warning(f"Weather data not found at {weather_path}. Fetching from Open-Meteo...")
            try:
                from data_pipeline.weather_service import fetch_historical_weather
                weather_df = fetch_historical_weather(
                    start_date=daily.index.min().strftime("%Y-%m-%d"),
                    end_date=daily.index.max().strftime("%Y-%m-%d"),
                    output_path=weather_path,
                )
                weather_df["date"] = pd.to_datetime(weather_df["date"])
                weather_df = weather_df.set_index("date")
                daily = daily.join(weather_df[WEATHER_COLS], how="left")
                for col in WEATHER_COLS:
                    daily[col] = daily[col].interpolate(method="linear", limit=3).fillna(0)
                logger.info("Fetched and merged Open-Meteo historical weather.")
            except Exception as e:
                logger.error(f"Failed to fetch weather: {e}. Using zeros.")
                for col in WEATHER_COLS:
                    daily[col] = 0

        # Step 9: Lagged demand features
        daily["demand_lag1"] = daily["demand_mw"].shift(1)
        daily["demand_lag7"] = daily["demand_mw"].shift(7)
        # Fill the first few rows that don't have lags
        daily["demand_lag1"] = daily["demand_lag1"].bfill()
        daily["demand_lag7"] = daily["demand_lag7"].bfill()

        self.df_clean = daily
        logger.info(f"Prepared {len(daily)} days of PJM demand data "
                     f"({daily.index.min().date()} to {daily.index.max().date()})")
        return daily

    def _check_stationarity(self, series):
        result = adfuller(series.dropna())
        return result[1] < 0.05  # True if stationary

    def train_and_evaluate(self):
        if self.df_clean is None:
            self.prepare_data()

        df = self.df_clean

        # Train strategy: Strict time-series split
        train = df[:-30].copy()
        test = df[-30:].copy()

        # Model 1 - PROPHET
        prophet_df = train.reset_index().rename(columns={"date": "ds", "demand_mw": "y"})
        self.prophet_model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=False,
            seasonality_mode="multiplicative",
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=10.0
        )
        self.prophet_model.add_country_holidays(country_name='US')
        # Add weather regressors
        for col in WEATHER_COLS:
            self.prophet_model.add_regressor(col)
        self.prophet_model.fit(prophet_df)

        prophet_future = self.prophet_model.make_future_dataframe(periods=30, freq='D')
        prophet_future = prophet_future.set_index("ds").join(df[WEATHER_COLS]).reset_index()
        prophet_pred_full = self.prophet_model.predict(prophet_future)
        prophet_test_pred = prophet_pred_full.iloc[-30:]['yhat'].values

        # Model 2 - SARIMAX with exogenous weather + lagged demand
        y_train = train["demand_mw"]
        exog_train = train[EXOG_COLS]
        is_stationary = self._check_stationarity(y_train)
        d = 0 if is_stationary else 1

        # Seasonal SARIMA (weekly seasonality = 7)
        self.sarima_model = SARIMAX(
            y_train,
            exog=exog_train,
            order=(1, d, 1),
            seasonal_order=(1, 0, 1, 7),
            enforce_stationarity=False,
            enforce_invertibility=False
        )
        sarima_fitted = self.sarima_model.fit(disp=False)
        exog_test = test[EXOG_COLS]
        sarima_test_pred = sarima_fitted.forecast(steps=30, exog=exog_test).values

        # ENSEMBLE EVALUATION
        y_test = test["demand_mw"].values
        rmse_prophet = float(np.sqrt(np.mean((y_test - prophet_test_pred)**2)))
        rmse_sarima = float(np.sqrt(np.mean((y_test - sarima_test_pred)**2)))

        # PROPHET METRICS
        self.metrics["prophet"]["MAE"] = float(np.mean(np.abs(y_test - prophet_test_pred)))
        self.metrics["prophet"]["RMSE"] = rmse_prophet
        self.metrics["prophet"]["MAPE"] = float(safe_mape(y_test, prophet_test_pred))
        self.confidence_scores["prophet"] = float(max(0.0, 100.0 - self.metrics["prophet"]["MAPE"]))

        # SARIMA METRICS
        self.metrics["sarima"]["MAE"] = float(np.mean(np.abs(y_test - sarima_test_pred)))
        self.metrics["sarima"]["RMSE"] = rmse_sarima
        self.metrics["sarima"]["MAPE"] = float(safe_mape(y_test, sarima_test_pred))
        self.confidence_scores["sarima"] = float(max(0.0, 100.0 - self.metrics["sarima"]["MAPE"]))

        # Blended weighting based on validation MAPE
        w_prophet = 1.0 / (self.metrics["prophet"]["MAPE"] ** 2)
        w_sarima = 1.0 / (self.metrics["sarima"]["MAPE"] ** 2)
        w_total = w_prophet + w_sarima

        self.weights["prophet"] = float(w_prophet / w_total)
        self.weights["sarima"] = float(w_sarima / w_total)

        ensemble_pred = (self.weights["prophet"] * prophet_test_pred) + (self.weights["sarima"] * sarima_test_pred)

        # ENSEMBLE METRICS
        self.metrics["ensemble"]["MAE"] = float(np.mean(np.abs(y_test - ensemble_pred)))
        self.metrics["ensemble"]["RMSE"] = float(np.sqrt(np.mean((y_test - ensemble_pred)**2)))
        self.metrics["ensemble"]["MAPE"] = float(safe_mape(y_test, ensemble_pred))
        self.confidence_scores["ensemble"] = float(max(0.0, 100.0 - self.metrics["ensemble"]["MAPE"]))

        # Store fitted models for reuse in get_forecast()
        self.fitted_prophet = self.prophet_model
        self.fitted_sarima_result = sarima_fitted
        self.fitted_sarima_model_spec = self.sarima_model
        self.last_trained = pd.Timestamp.now()
        logger.info(f"Ensemble Evaluation Metrics: {self.metrics['ensemble']}")

    def get_forecast(self, days=30, model_type="ensemble"):
        if self.df_clean is None or self.last_trained is None:
            self.train_and_evaluate()

        full_df = self.df_clean.copy()

        # SKIP refitting — reuse stored fitted models
        # Only refit if new data has arrived since last training
        data_changed = full_df.index[-1] > self.last_trained

        if data_changed or not hasattr(self, "fitted_prophet"):
            self.train_and_evaluate()

        final_prophet = self.fitted_prophet
        final_sarima_result = self.fitted_sarima_result

        last_date = full_df.index[-1]
        future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=days, freq='D')

        # ── Get REAL forecast weather from Open-Meteo ──────────────────────
        try:
            from data_pipeline.weather_service import fetch_forecast_weather
            forecast_weather = fetch_forecast_weather(days=days)
            if len(forecast_weather) > 0:
                forecast_weather["date"] = pd.to_datetime(forecast_weather["date"])
                future_exog = forecast_weather.set_index("date")[WEATHER_COLS].reindex(future_dates)
                # Fill any remaining gaps with interpolation
                for col in WEATHER_COLS:
                    future_exog[col] = future_exog[col].interpolate(method="linear").fillna(0)
                logger.info(f"Using REAL Open-Meteo forecast weather for {len(future_exog)} days")
            else:
                raise ValueError("Empty forecast returned")
        except Exception as e:
            logger.warning(f"Open-Meteo forecast failed ({e}). Falling back to historical averages.")
            historical_weather = full_df.groupby(
                [full_df.index.month, full_df.index.day]
            )[WEATHER_COLS].mean()

            future_weather = []
            for d in future_dates:
                try:
                    row = historical_weather.loc[(d.month, d.day)]
                    future_weather.append(row.to_dict())
                except KeyError:
                    future_weather.append({c: 0 for c in WEATHER_COLS})

            future_exog = pd.DataFrame(future_weather, index=future_dates)

        # Add lagged demand for SARIMA exog
        # Use last known demand values for the lag features
        last_demand = full_df["demand_mw"].iloc[-1]
        last_demand_7 = full_df["demand_mw"].iloc[-7] if len(full_df) >= 7 else last_demand

        future_exog_sarima = future_exog.copy()
        # Build lag features iteratively for the forecast horizon
        lag1_values = [last_demand]
        lag7_values = []
        for i in range(days):
            if i >= 7:
                lag7_values.append(lag1_values[i - 7])
            elif len(full_df) >= (7 - i):
                lag7_values.append(full_df["demand_mw"].iloc[-(7 - i)])
            else:
                lag7_values.append(last_demand_7)
            if i > 0:
                # Use the previous day's predicted demand as lag1
                # For simplicity, use the last known demand (conservative estimate)
                lag1_values.append(last_demand)

        future_exog_sarima["demand_lag1"] = lag1_values[:days]
        future_exog_sarima["demand_lag7"] = lag7_values[:days]

        # Prophet forecast — needs weather columns on the full future dataframe
        future = final_prophet.make_future_dataframe(periods=days, freq='D')
        future = future.set_index("ds")
        # Join historical weather for past dates
        future = future.join(full_df[WEATHER_COLS])
        # Fill future dates with real forecast weather
        future.update(future_exog)
        future = future.reset_index()

        prophet_forecast = final_prophet.predict(future)
        prophet_future_pred = prophet_forecast.iloc[-days:]['yhat'].values
        prophet_lower = prophet_forecast.iloc[-days:]['yhat_lower'].values
        prophet_upper = prophet_forecast.iloc[-days:]['yhat_upper'].values

        # SARIMA forecast using stored fitted result + real exog
        sarima_future_pred = final_sarima_result.forecast(
            steps=days, exog=future_exog_sarima[EXOG_COLS]
        ).values
        sarima_forecast_obj = final_sarima_result.get_forecast(
            steps=days, exog=future_exog_sarima[EXOG_COLS]
        )
        sarima_ci = sarima_forecast_obj.conf_int(alpha=0.20)
        sarima_lower = sarima_ci.iloc[:, 0].values
        sarima_upper = sarima_ci.iloc[:, 1].values

        # Ensemble bands: weighted blend of both models
        ensemble_lower = (self.weights["prophet"] * prophet_lower +
                          self.weights["sarima"] * sarima_lower)
        ensemble_upper = (self.weights["prophet"] * prophet_upper +
                          self.weights["sarima"] * sarima_upper)

        # Select correct bands for the requested model
        band_map = {
            "prophet":  (prophet_lower, prophet_upper),
            "sarima":   (sarima_lower, sarima_upper),
            "ensemble": (ensemble_lower, ensemble_upper),
        }
        lower_band, upper_band = band_map.get(model_type, band_map["ensemble"])

        ensemble_pred = (self.weights["prophet"] * prophet_future_pred) + (self.weights["sarima"] * sarima_future_pred)

        if model_type == "prophet":
            target_pred = prophet_future_pred
        elif model_type == "sarima":
            target_pred = sarima_future_pred
        else:
            target_pred = ensemble_pred

        results = []

        # Add last 30 days of historical data
        hist_df = full_df[full_df["hours_recorded"] >= 4].tail(30)
        floor = full_df["demand_mw"].quantile(0.05)
        hist_df = hist_df[hist_df["demand_mw"] >= floor]

        for idx, row in hist_df.iterrows():
            results.append({
                "date": idx.strftime("%Y-%m-%d"),
                "historical_demand": float(row["demand_mw"]),
                "predicted_demand": None,
                "lower_band": None,
                "upper_band": None
            })

        # Share the last historical point as the first forecast anchor
        if len(results) > 0:
            results[-1]["predicted_demand"] = round(float(target_pred[0]), 2)
            results[-1]["lower_band"] = round(float(lower_band[0]), 2)
            results[-1]["upper_band"] = round(float(upper_band[0]), 2)

        for i in range(days):
            results.append({
                "date": future_dates[i].strftime("%Y-%m-%d"),
                "historical_demand": None,
                "predicted_demand": round(float(target_pred[i]), 2),
                "lower_band": round(float(lower_band[i]), 2),
                "upper_band": round(float(upper_band[i]), 2)
            })

        return results
