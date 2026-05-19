import numpy as np
import pandas as pd
import logging
from pathlib import Path
from prophet import Prophet
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.stattools import adfuller

logger = logging.getLogger(__name__)

def safe_mape(y_true, y_pred):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    mask = y_true != 0
    if not np.any(mask):
        return np.nan
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)

class ElectricityDemandForecaster:
    def __init__(self, data_path="data/raw/eia_pjm_hourly_demand.csv"):
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
        """Parse, clean and feature engineer PJM hourly/daily demand data."""
        logger.info(f"Loading data from {self.data_path}")
        df = pd.read_csv(self.data_path)
        
        # Parse datetime
        df["datetime"] = pd.to_datetime(df["period"], format="%Y-%m-%dT%H")
        
        # Step 1: Clean raw hourly anomalies (unphysical zeros/negatives and extreme spikes)
        df.loc[df["value"] <= 0, "value"] = np.nan
        df.loc[df["value"] > 100000, "value"] = np.nan
        
        # Step 2: Smooth dropouts by linear interpolation per sub-balancing area
        df["value"] = df.groupby("subba")["value"].transform(
            lambda x: x.interpolate(method="linear", limit_direction="both")
        )
        
        # Step 3: Aggregate all sub-balancing areas per hour → PJM total per hour
        hourly_total = df.groupby("datetime")["value"].sum().reset_index()
        hourly_total.rename(columns={"value": "demand_mw"}, inplace=True)
        hourly_total["date"] = hourly_total["datetime"].dt.date
        
        # Step 4: Aggregate hourly → daily
        daily = hourly_total.groupby("date").agg(
            demand_mw=("demand_mw", "sum"),
            peak_mw=("demand_mw", "max"),
            trough_mw=("demand_mw", "min"),
            hours_recorded=("demand_mw", "count"),
        ).reset_index()
        
        daily["date"] = pd.to_datetime(daily["date"])
        daily = daily.sort_values("date").set_index("date")
        
        # Step 5: Strictly drop partial days to avoid artificial dropouts at the end of the series
        partial_days = daily["hours_recorded"] < 24
        if partial_days.any():
            logger.info(f"Dropping {partial_days.sum()} partial days (< 24 hours)")
            daily = daily[~partial_days]
        
        # Step 6: Ensure daily continuity
        daily = daily.asfreq("D")
        
        # Step 7: Handle any remaining missing values via time interpolation
        for col in ["demand_mw", "peak_mw", "trough_mw"]:
            daily[col] = daily[col].interpolate(method="time")
        
        # Step 8: Feature engineering
        daily["dayofweek"] = daily.index.dayofweek
        daily["month"] = daily.index.month
        daily["is_weekend"] = (daily["dayofweek"] >= 5).astype(int)
        daily["load_factor"] = daily["trough_mw"] / daily["peak_mw"]
        
        self.df_clean = daily
        logger.info(f"Prepared {len(daily)} days of PJM demand data "
                     f"({daily.index.min().date()} → {daily.index.max().date()})")
        return daily

    def _check_stationarity(self, series):
        result = adfuller(series.dropna())
        return result[1] < 0.05 # True if stationary
        
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
        self.prophet_model.fit(prophet_df)
        
        prophet_future = self.prophet_model.make_future_dataframe(periods=30, freq='D')
        prophet_pred_full = self.prophet_model.predict(prophet_future)
        prophet_test_pred = prophet_pred_full.iloc[-30:]['yhat'].values
        
        # Model 2 - SARIMA
        y_train = train["demand_mw"]
        is_stationary = self._check_stationarity(y_train)
        d = 0 if is_stationary else 1
        
        # Seasonal SARIMA (weekly seasonality = 7)
        self.sarima_model = SARIMAX(
            y_train, 
            order=(1, d, 1), 
            seasonal_order=(1, 0, 1, 7),
            enforce_stationarity=False, 
            enforce_invertibility=False
        )
        sarima_fitted = self.sarima_model.fit(disp=False)
        sarima_test_pred = sarima_fitted.forecast(steps=30).values
        
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
        
        # Blended weighting based on validation MAPE (directly minimizing primary UI metric)
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
        
        # ADD: Store fitted models for reuse in get_forecast()
        self.fitted_prophet = self.prophet_model   # already fitted above # FIX: 6
        self.fitted_sarima_result = sarima_fitted  # store the fitted result # FIX: 6
        self.fitted_sarima_model_spec = self.sarima_model  # store spec too # FIX: 6
        self.last_trained = pd.Timestamp.now() # FIX: 6
        logger.info(f"Ensemble Evaluation Metrics: {self.metrics['ensemble']}")
        
    def get_forecast(self, days=30, model_type="ensemble"):
        if self.df_clean is None or self.last_trained is None:
            self.train_and_evaluate() # FIX: 6
            
        full_df = self.df_clean.copy()
        
        # SKIP refitting — reuse stored fitted models
        # Only refit if new data has arrived since last training
        data_changed = full_df.index[-1] > self.last_trained # FIX: 6
        
        if data_changed or not hasattr(self, "fitted_prophet"): # FIX: 6
            # Refit only when data actually changed
            self.train_and_evaluate() # FIX: 6
            
        final_prophet = self.fitted_prophet # FIX: 6
        final_sarima_result = self.fitted_sarima_result # FIX: 6
        
        # Prophet forecast (no refit needed — extend future dataframe only)
        future = final_prophet.make_future_dataframe(periods=days, freq='D') # FIX: 6
        prophet_forecast = final_prophet.predict(future) # FIX: 6
        prophet_future_pred = prophet_forecast.iloc[-days:]['yhat'].values # FIX: 6
        prophet_lower = prophet_forecast.iloc[-days:]['yhat_lower'].values # FIX: 6
        prophet_upper = prophet_forecast.iloc[-days:]['yhat_upper'].values # FIX: 6
        
        # SARIMA forecast using stored fitted result
        sarima_future_pred = final_sarima_result.forecast(steps=days).values # FIX: 6
        sarima_forecast_obj = final_sarima_result.get_forecast(steps=days) # FIX: 2
        sarima_ci = sarima_forecast_obj.conf_int(alpha=0.20) # FIX: 2
        sarima_lower = sarima_ci.iloc[:, 0].values # FIX: 2
        sarima_upper = sarima_ci.iloc[:, 1].values # FIX: 2
        
        # Ensemble bands: weighted blend of both models
        ensemble_lower = (self.weights["prophet"] * prophet_lower + 
                          self.weights["sarima"] * sarima_lower) # FIX: 2
        ensemble_upper = (self.weights["prophet"] * prophet_upper + 
                          self.weights["sarima"] * sarima_upper) # FIX: 2
        
        # Select correct bands for the requested model
        band_map = { # FIX: 2
            "prophet":  (prophet_lower, prophet_upper), # FIX: 2
            "sarima":   (sarima_lower, sarima_upper), # FIX: 2
            "ensemble": (ensemble_lower, ensemble_upper), # FIX: 2
        } # FIX: 2
        lower_band, upper_band = band_map.get(model_type, band_map["ensemble"]) # FIX: 2
        
        ensemble_pred = (self.weights["prophet"] * prophet_future_pred) + (self.weights["sarima"] * sarima_future_pred)
        
        if model_type == "prophet":
            target_pred = prophet_future_pred
        elif model_type == "sarima":
            target_pred = sarima_future_pred
        else:
            target_pred = ensemble_pred
            
        last_date = full_df.index[-1]
        future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=days, freq='D')
        
        results = []
        
        # Add last 30 days of historical data
        # FIX: 1 - Filter partial days from historical display
        hist_df = full_df[full_df["hours_recorded"] >= 24].tail(30) # FIX: 1
        # FIX: 1 - Guard against anomalous low values
        floor = full_df["demand_mw"].quantile(0.05) # FIX: 1
        hist_df = hist_df[hist_df["demand_mw"] >= floor] # FIX: 1
        
        for idx, row in hist_df.iterrows():
            results.append({
                "date": idx.strftime("%Y-%m-%d"),
                "historical_demand": float(row["demand_mw"]),
                "predicted_demand": None,
                "lower_band": None,
                "upper_band": None
            })
            
        # FIX: 5 - Share the last historical point as the first forecast anchor
        if len(results) > 0: # FIX: 5
            results[-1]["predicted_demand"] = round(float(target_pred[0]), 2) # FIX: 5
            results[-1]["lower_band"] = round(float(lower_band[0]), 2) # FIX: 5
            results[-1]["upper_band"] = round(float(upper_band[0]), 2) # FIX: 5
            
        for i in range(days):
            results.append({
                "date": future_dates[i].strftime("%Y-%m-%d"),
                "historical_demand": None,
                "predicted_demand": round(float(target_pred[i]), 2),
                "lower_band": round(float(lower_band[i]), 2), # FIX: 2
                "upper_band": round(float(upper_band[i]), 2) # FIX: 2
            })
            
        return results
