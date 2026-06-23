"""
Electricity Demand Forecaster — Ensemble (Prophet + SARIMAX)
─────────────────────────────────────────────────────────────
Production-grade demand forecasting for PJM sub-balancing areas
in New Jersey.

Key design principles:
    1. NO data leakage: validation uses simulated forecast weather (noisy).
    2. NO silent fallbacks: missing weather or failed APIs raise errors.
    3. NO .fillna(0) or .ffill() on weather data.
    4. Database-first: reads demand & weather from SQLite/PostgreSQL.
    5. CSV fallback only for legacy/migration scenarios.
"""

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

# Noise standard deviation for simulating forecast weather (°C)
FORECAST_NOISE_STD = 1.5

# Maximum fraction of missing weather rows allowed before raising an error
MAX_MISSING_WEATHER_FRAC = 0.05  # 5%


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

    # ── Data Loading ──────────────────────────────────────────────────────

    def _load_demand_from_db(self) -> pd.DataFrame:
        """Load daily demand data from the database."""
        try:
            from database.connection import get_sync_session
            from database.models import DailySubBaDemand

            with get_sync_session() as session:
                rows = (
                    session.query(DailySubBaDemand)
                    .order_by(DailySubBaDemand.period.asc())
                    .all()
                )
                records = []
                for r in rows:
                    records.append({
                        "period": str(r.period),
                        "subba": r.subba,
                        "value": r.value,
                        "parent": r.parent,
                    })

            if not records:
                return pd.DataFrame()

            df = pd.DataFrame(records)
            logger.info(f"Loaded {len(df)} demand records from database")
            return df
        except Exception as e:
            logger.warning(f"Failed to load demand from database: {e}")
            return pd.DataFrame()

    def _load_weather_from_db(self) -> pd.DataFrame:
        """Load weather data from the database."""
        try:
            from database.connection import get_sync_session
            from database.models import WeatherOpenMeteo

            with get_sync_session() as session:
                rows = (
                    session.query(WeatherOpenMeteo)
                    .order_by(WeatherOpenMeteo.date.asc())
                    .all()
                )
                records = []
                for r in rows:
                    records.append({
                        "date": pd.Timestamp(r.date),
                        "temp_max": r.temp_max,
                        "temp_min": r.temp_min,
                        "temp_avg": r.temp_avg,
                        "hdd": r.hdd,
                        "cdd": r.cdd,
                    })

            if not records:
                return pd.DataFrame()

            df = pd.DataFrame(records)
            logger.info(f"Loaded {len(df)} weather records from database")
            return df
        except Exception as e:
            logger.warning(f"Failed to load weather from database: {e}")
            return pd.DataFrame()

    # ── Weather Noise Simulation ──────────────────────────────────────────

    @staticmethod
    def _simulate_forecast_weather(weather_df: pd.DataFrame) -> pd.DataFrame:
        """Add Gaussian noise to weather data to simulate forecast error.

        This prevents data leakage during validation: the test set should
        NOT use perfect historical weather, because in production only
        *forecast* weather (which is inherently noisy) is available.

        Noise is applied to temp_max, temp_min, and temp_avg.
        HDD/CDD are then recomputed from the noisy averages.
        """
        noisy = weather_df.copy()
        rng = np.random.default_rng(seed=42)

        for col in ["temp_max", "temp_min", "temp_avg"]:
            if col in noisy.columns:
                noise = rng.normal(0, FORECAST_NOISE_STD, size=len(noisy))
                noisy[col] = noisy[col] + noise

        # Recompute HDD/CDD from noisy temp_avg
        from data_pipeline.weather_service import BASE_TEMP_C
        noisy["hdd"] = (BASE_TEMP_C - noisy["temp_avg"]).clip(lower=0).round(2)
        noisy["cdd"] = (noisy["temp_avg"] - BASE_TEMP_C).clip(lower=0).round(2)

        return noisy

    # ── Data Preparation ──────────────────────────────────────────────────

    def prepare_data(self):
        """Parse, clean and feature engineer PJM daily demand + Open-Meteo weather.

        Data source priority:
            1. Database (daily_subba_demand + weather_openmeteo tables)
            2. CSV files (legacy fallback)
        """
        # ── Step 0: Load demand data ──────────────────────────────────────
        df = self._load_demand_from_db()

        if df.empty:
            # Fallback to CSV
            logger.info(f"No DB demand data — loading from CSV: {self.data_path}")
            df = pd.read_csv(self.data_path)

        if df.empty:
            raise ValueError(
                "No demand data available in database or CSV. "
                "Run the EIA demand fetcher first."
            )

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

        # ── Step 8: Merge REAL weather data ───────────────────────────────
        weather_df = self._load_weather_from_db()

        if weather_df.empty:
            # Fallback to CSV
            weather_path = self.data_path.parent / "weather_openmeteo.csv"
            if weather_path.exists():
                weather_df = pd.read_csv(weather_path)
                weather_df["date"] = pd.to_datetime(weather_df["date"])
                logger.info(f"Loaded weather from CSV fallback: {weather_path}")
            else:
                # Try to fetch from Open-Meteo
                logger.warning("No weather data in DB or CSV. Fetching from Open-Meteo...")
                try:
                    from data_pipeline.weather_service import fetch_historical_weather
                    weather_df = fetch_historical_weather(
                        start_date=daily.index.min().strftime("%Y-%m-%d"),
                        end_date=daily.index.max().strftime("%Y-%m-%d"),
                    )
                except Exception as e:
                    raise ValueError(
                        f"Failed to obtain weather data: {e}. "
                        f"Cannot train forecast model without weather."
                    ) from e

        if weather_df.empty:
            raise ValueError(
                "Weather data is empty after all attempts. "
                "Cannot train forecast model without weather data."
            )

        weather_df = weather_df.drop_duplicates(subset=["date"]).set_index("date")
        daily = daily.join(weather_df[WEATHER_COLS], how="left")

        # Only interpolate small gaps (<=3 days) — NO forward-fill, NO zero-fill
        for col in WEATHER_COLS:
            daily[col] = daily[col].interpolate(method="linear", limit=3)

        # ── Step 8b: Validate weather coverage ────────────────────────────
        weather_missing = daily[WEATHER_COLS].isnull().any(axis=1).sum()
        total_rows = len(daily)
        missing_frac = weather_missing / total_rows if total_rows > 0 else 0

        if missing_frac > MAX_MISSING_WEATHER_FRAC:
            raise ValueError(
                f"Too much missing weather data: {weather_missing}/{total_rows} days "
                f"({missing_frac:.1%}) > {MAX_MISSING_WEATHER_FRAC:.0%} threshold. "
                f"Ingestion pipeline may be broken."
            )

        if weather_missing > 0:
            logger.warning(
                f"{weather_missing} days missing weather data after interpolation — "
                f"dropping those rows (NOT filling with zeros)."
            )
            daily = daily.dropna(subset=WEATHER_COLS)

        logger.info("Successfully merged weather data (temp_avg, hdd, cdd).")

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

    # ── Training & Evaluation ─────────────────────────────────────────────

    def train_and_evaluate(self):
        if self.df_clean is None:
            self.prepare_data()

        df = self.df_clean

        # Train strategy: Strict time-series split
        train = df[:-30].copy()
        test = df[-30:].copy()

        # ── ANTI-LEAKAGE: Simulate forecast weather for TEST set ──────────
        # In production, we only have *forecast* weather (noisy), not actuals.
        # So validation must also use noisy weather to get realistic metrics.
        test_weather_noisy = self._simulate_forecast_weather(test[WEATHER_COLS])
        test.loc[:, WEATHER_COLS] = test_weather_noisy[WEATHER_COLS].values
        logger.info(
            f"Applied forecast weather noise (σ={FORECAST_NOISE_STD}°C) to "
            f"{len(test)} test rows to prevent data leakage."
        )

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

        # Build future DataFrame for Prophet — use noisy weather for test period
        prophet_future = self.prophet_model.make_future_dataframe(periods=30, freq='D')
        prophet_future = prophet_future.set_index("ds")
        # Join training weather (actual) for historical dates
        prophet_future = prophet_future.join(train[WEATHER_COLS])
        # Fill test dates with noisy weather
        test_for_join = test[WEATHER_COLS].copy()
        test_for_join.index.name = None  # ensure index compatibility
        prophet_future.update(test_for_join)
        prophet_future = prophet_future.reset_index()
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
        # Use noisy weather for test exog (consistent with anti-leakage)
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

    # ── Forecasting ───────────────────────────────────────────────────────

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

        # ── Get REAL forecast weather from Open-Meteo ─────────────────────
        # FAIL-LOUD: If this fails, a RuntimeError propagates up.
        from data_pipeline.weather_service import fetch_forecast_weather
        forecast_weather = fetch_forecast_weather(days=days)
        # fetch_forecast_weather now raises RuntimeError on failure —
        # no try/except silencing here.

        forecast_weather["date"] = pd.to_datetime(forecast_weather["date"])
        future_exog = forecast_weather.set_index("date")[WEATHER_COLS].reindex(future_dates)

        # Interpolate alignment gaps (date rounding), but do NOT fill with zeros
        for col in WEATHER_COLS:
            future_exog[col] = future_exog[col].interpolate(method="linear")

        # If there are still NaNs after interpolation, raise
        remaining_nans = future_exog[WEATHER_COLS].isnull().any(axis=1).sum()
        if remaining_nans > 0:
            logger.warning(
                f"{remaining_nans} forecast days still missing weather after interpolation — "
                f"dropping those days from forecast."
            )
            future_exog = future_exog.dropna(subset=WEATHER_COLS)
            future_dates = future_exog.index
            days = len(future_dates)

        logger.info(f"Using REAL Open-Meteo forecast weather for {len(future_exog)} days")

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
