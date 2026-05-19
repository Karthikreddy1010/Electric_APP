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
    def __init__(self, data_path="data/raw/eia_pjm_daily_demand.csv"):
        # Resolve the full path based on project root if relative
        if not Path(data_path).is_absolute():
            project_root = Path(__file__).resolve().parent.parent
            self.data_path = project_root / data_path
        else:
            self.data_path = Path(data_path)
            
        self.weights = {"prophet": 0.5, "sarima": 0.5}
        self.metrics = {"MAE": np.nan, "RMSE": np.nan, "MAPE": np.nan}
        self.confidence_score = np.nan
        self.df_clean = None
        self.last_trained = None
        
    def prepare_data(self):
        """Parse, clean and feature engineer."""
        logger.info(f"Loading data from {self.data_path}")
        df = pd.read_csv(self.data_path)
        
        df = df.groupby('period')['value'].sum().reset_index()
        df.rename(columns={'period': 'date', 'value': 'demand_mw'}, inplace=True)
        
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").set_index("date")
        
        # Ensure daily continuity
        df = df.asfreq("D")
        
        # Handle missing values
        df["demand_mw"] = df["demand_mw"].interpolate(method="time")
        
        # Features
        df["dayofweek"] = df.index.dayofweek
        df["month"] = df.index.month
        df["is_weekend"] = (df["dayofweek"] >= 5).astype(int)
        
        self.df_clean = df
        return df

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
            daily_seasonality=False
        )
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
        rmse_prophet = np.sqrt(np.mean((y_test - prophet_test_pred)**2))
        rmse_sarima = np.sqrt(np.mean((y_test - sarima_test_pred)**2))
        
        # Weights inversely proportional to error
        w_prophet = 1 / rmse_prophet
        w_sarima = 1 / rmse_sarima
        w_total = w_prophet + w_sarima
        
        self.weights["prophet"] = float(w_prophet / w_total)
        self.weights["sarima"] = float(w_sarima / w_total)
        
        ensemble_pred = (self.weights["prophet"] * prophet_test_pred) + (self.weights["sarima"] * sarima_test_pred)
        
        self.metrics["MAE"] = float(np.mean(np.abs(y_test - ensemble_pred)))
        self.metrics["RMSE"] = float(np.sqrt(np.mean((y_test - ensemble_pred)**2)))
        self.metrics["MAPE"] = float(safe_mape(y_test, ensemble_pred))
        
        # Confidence score heuristically
        self.confidence_score = float(max(0.0, 100.0 - self.metrics["MAPE"]))
        self.last_trained = pd.Timestamp.now()
        logger.info(f"Ensemble Evaluation Metrics: {self.metrics}")
        
    def get_forecast(self, days=30):
        if self.df_clean is None or self.last_trained is None:
            self.train_and_evaluate()
            
        full_df = self.df_clean.copy()
        
        # Refit Prophet
        prophet_df = full_df.reset_index().rename(columns={"date": "ds", "demand_mw": "y"})
        final_prophet = Prophet(yearly_seasonality=True, weekly_seasonality=True, daily_seasonality=False)
        final_prophet.fit(prophet_df)
        
        future = final_prophet.make_future_dataframe(periods=days, freq='D')
        prophet_forecast = final_prophet.predict(future)
        prophet_future_pred = prophet_forecast.iloc[-days:]['yhat'].values
        prophet_lower = prophet_forecast.iloc[-days:]['yhat_lower'].values
        prophet_upper = prophet_forecast.iloc[-days:]['yhat_upper'].values
        
        # Refit SARIMA
        y_all = full_df["demand_mw"]
        is_stat = self._check_stationarity(y_all)
        d = 0 if is_stat else 1
        final_sarima = SARIMAX(
            y_all, 
            order=(1, d, 1), 
            seasonal_order=(1, 0, 1, 7),
            enforce_stationarity=False, 
            enforce_invertibility=False
        ).fit(disp=False)
        
        sarima_future_pred = final_sarima.forecast(steps=days).values
        
        ensemble_pred = (self.weights["prophet"] * prophet_future_pred) + (self.weights["sarima"] * sarima_future_pred)
        
        last_date = full_df.index[-1]
        future_dates = pd.date_range(last_date + pd.Timedelta(days=1), periods=days, freq='D')
        
        results = []
        
        # Add last 30 days of historical data
        hist_df = full_df.tail(30)
        for idx, row in hist_df.iterrows():
            results.append({
                "date": idx.strftime("%Y-%m-%d"),
                "historical_demand": float(row["demand_mw"]),
                "predicted_demand": None,
                "lower_band": None,
                "upper_band": None
            })
            
        for i in range(days):
            results.append({
                "date": future_dates[i].strftime("%Y-%m-%d"),
                "historical_demand": None,
                "predicted_demand": round(float(ensemble_pred[i]), 2),
                "lower_band": round(float(prophet_lower[i]), 2),
                "upper_band": round(float(prophet_upper[i]), 2)
            })
            
        return results
