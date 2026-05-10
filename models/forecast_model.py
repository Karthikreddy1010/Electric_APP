"""
Forecasting models: SARIMA (baseline), Prophet (mid-level), LSTM (advanced).
All models share a common interface for training, prediction, and evaluation.
"""
import numpy as np
import pandas as pd
import logging
import joblib
from pathlib import Path
from sklearn.metrics import mean_squared_error, mean_absolute_error
from sklearn.preprocessing import MinMaxScaler
from typing import Optional

logger = logging.getLogger(__name__)


def compute_metrics(y_true, y_pred):
    """Compute standard forecasting metrics."""
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    mask = y_true != 0
    return {
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "mape": float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100),
    }


class SARIMAForecaster:
    """
    SARIMA baseline forecaster for monthly electricity costs.
    Good for capturing trend + seasonality with minimal data.
    """
    
    def __init__(self, order=(1,1,1), seasonal_order=(1,1,1,12)):
        self.order = order
        self.seasonal_order = seasonal_order
        self.model = None
        self.fitted = None
    
    def train(self, y: pd.Series):
        """Fit SARIMA model on monthly time series."""
        from statsmodels.tsa.statespace.sarimax import SARIMAX
        
        self.model = SARIMAX(
            y, order=self.order, seasonal_order=self.seasonal_order,
            enforce_stationarity=False, enforce_invertibility=False,
        )
        self.fitted = self.model.fit(disp=False, maxiter=200)
        logger.info(f"SARIMA fitted: AIC={self.fitted.aic:.1f}, BIC={self.fitted.bic:.1f}")
        return {"aic": self.fitted.aic, "bic": self.fitted.bic}
    
    def predict(self, steps: int = 12, alpha: float = 0.05) -> pd.DataFrame:
        """Forecast future values with prediction intervals."""
        if self.fitted is None:
            raise RuntimeError("Model not trained")
        forecast = self.fitted.get_forecast(steps=steps)
        ci = forecast.conf_int(alpha=alpha)
        return pd.DataFrame({
            "forecast": forecast.predicted_mean.values,
            "lower": ci.iloc[:, 0].values,
            "upper": ci.iloc[:, 1].values,
        })
    
    def evaluate(self, y_train, y_test) -> dict:
        """Train on y_train, predict len(y_test), return metrics."""
        self.train(y_train)
        preds = self.predict(steps=len(y_test))
        return compute_metrics(y_test.values, preds["forecast"].values)


class ProphetForecaster:
    """Facebook Prophet forecaster with weather regressors."""
    
    def __init__(self, changepoint_prior=0.05):
        self.changepoint_prior = changepoint_prior
        self.model = None
    
    def train(self, df: pd.DataFrame, regressors: list[str] = None):
        """
        Train Prophet model.
        df must have columns: 'ds' (date), 'y' (target).
        Optional regressors: weather/market features.
        """
        from prophet import Prophet
        
        self.model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            changepoint_prior_scale=self.changepoint_prior,
            interval_width=0.95,
        )
        
        if regressors:
            for reg in regressors:
                if reg in df.columns:
                    self.model.add_regressor(reg)
        
        self.model.fit(df)
        logger.info("Prophet model trained")
    
    def predict(self, periods: int = 12, 
                future_regressors: pd.DataFrame = None) -> pd.DataFrame:
        """Generate forecast with uncertainty intervals."""
        future = self.model.make_future_dataframe(periods=periods, freq="MS")
        
        if future_regressors is not None:
            for col in future_regressors.columns:
                if col != "ds":
                    future[col] = future_regressors[col].values[:len(future)]
        
        forecast = self.model.predict(future)
        result = forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail(periods)
        result.columns = ["date", "forecast", "lower", "upper"]
        return result.reset_index(drop=True)
    
    def evaluate(self, df_train, df_test) -> dict:
        self.train(df_train)
        preds = self.predict(periods=len(df_test))
        return compute_metrics(df_test["y"].values, preds["forecast"].values)


class LSTMForecaster:
    """
    LSTM neural network for electricity cost forecasting.
    Captures non-linear temporal dependencies.
    """
    
    def __init__(self, seq_length=12, hidden_size=64, epochs=100, batch_size=32):
        self.seq_length = seq_length
        self.hidden_size = hidden_size
        self.epochs = epochs
        self.batch_size = batch_size
        self.model = None
        self.scaler = MinMaxScaler()
    
    def _create_sequences(self, data, seq_length):
        X, y = [], []
        for i in range(len(data) - seq_length):
            X.append(data[i:i+seq_length])
            y.append(data[i+seq_length])
        return np.array(X), np.array(y)
    
    def _build_model(self, n_features):
        """Build LSTM architecture using TensorFlow/Keras."""
        try:
            from tensorflow.keras.models import Sequential
            from tensorflow.keras.layers import LSTM, Dense, Dropout
            from tensorflow.keras.callbacks import EarlyStopping
        except ImportError:
            logger.error("TensorFlow not installed. LSTM forecaster unavailable.")
            raise
        
        model = Sequential([
            LSTM(self.hidden_size, input_shape=(self.seq_length, n_features),
                 return_sequences=True),
            Dropout(0.2),
            LSTM(self.hidden_size // 2),
            Dropout(0.2),
            Dense(32, activation="relu"),
            Dense(1),
        ])
        model.compile(optimizer="adam", loss="mse", metrics=["mae"])
        return model
    
    def train(self, series: np.ndarray):
        """Train LSTM on univariate or multivariate time series."""
        from tensorflow.keras.callbacks import EarlyStopping
        
        if series.ndim == 1:
            series = series.reshape(-1, 1)
        
        scaled = self.scaler.fit_transform(series)
        X, y = self._create_sequences(scaled, self.seq_length)
        
        # If multivariate, target is first column
        if y.ndim > 1:
            y = y[:, 0]
        
        self.model = self._build_model(X.shape[2])
        
        early_stop = EarlyStopping(patience=10, restore_best_weights=True)
        
        self.model.fit(
            X, y,
            epochs=self.epochs,
            batch_size=self.batch_size,
            validation_split=0.15,
            callbacks=[early_stop],
            verbose=0,
        )
        logger.info("LSTM model trained")
    
    def predict(self, last_sequence: np.ndarray, steps: int = 12) -> np.ndarray:
        """Generate multi-step forecast by iteratively predicting."""
        if last_sequence.ndim == 1:
            last_sequence = last_sequence.reshape(-1, 1)
        
        scaled = self.scaler.transform(last_sequence)
        current = scaled[-self.seq_length:].copy()
        preds = []
        
        for _ in range(steps):
            pred = self.model.predict(current.reshape(1, self.seq_length, -1), verbose=0)
            preds.append(pred[0, 0])
            new_row = current[-1].copy()
            new_row[0] = pred[0, 0]
            current = np.vstack([current[1:], new_row])
        
        # Inverse transform
        dummy = np.zeros((len(preds), last_sequence.shape[1]))
        dummy[:, 0] = preds
        unscaled = self.scaler.inverse_transform(dummy)[:, 0]
        return unscaled


class ForecastEnsemble:
    """
    Ensemble of SARIMA + Prophet + LSTM with weighted averaging.
    Degrades gracefully if Prophet/TensorFlow aren't installed.
    """
    
    def __init__(self):
        self.sarima = SARIMAForecaster()
        self.prophet = None
        self.has_prophet = False
        self.use_lstm = False
    
    def train_all(self, billing_series: pd.Series, dates: pd.Series):
        """Train all available models."""
        # SARIMA (always available)
        self.sarima.train(billing_series)
        
        # Prophet (optional)
        try:
            self.prophet = ProphetForecaster()
            prophet_df = pd.DataFrame({"ds": dates, "y": billing_series.values})
            self.prophet.train(prophet_df)
            self.has_prophet = True
            logger.info("Ensemble: SARIMA + Prophet trained")
        except Exception as e:
            logger.warning(f"Prophet unavailable, using SARIMA only: {e}")
            self.has_prophet = False
    
    def predict_ensemble(self, steps: int = 12) -> pd.DataFrame:
        """Generate weighted ensemble forecast (or SARIMA-only fallback)."""
        sarima_pred = self.sarima.predict(steps=steps)
        
        if self.has_prophet and self.prophet is not None:
            try:
                prophet_pred = self.prophet.predict(periods=steps)
                w_s, w_p = 0.4, 0.6
                ensemble = sarima_pred["forecast"].values * w_s + prophet_pred["forecast"].values * w_p
                lower = sarima_pred["lower"].values * 0.5 + prophet_pred["lower"].values * 0.5
                upper = sarima_pred["upper"].values * 0.5 + prophet_pred["upper"].values * 0.5
                return pd.DataFrame({
                    "forecast_ensemble": ensemble,
                    "forecast_sarima": sarima_pred["forecast"].values,
                    "forecast_prophet": prophet_pred["forecast"].values,
                    "lower": lower,
                    "upper": upper,
                })
            except Exception as e:
                logger.warning(f"Prophet prediction failed, using SARIMA only: {e}")
        
        # SARIMA-only fallback
        return pd.DataFrame({
            "forecast_ensemble": sarima_pred["forecast"].values,
            "forecast_sarima": sarima_pred["forecast"].values,
            "forecast_prophet": [None] * steps,
            "lower": sarima_pred["lower"].values,
            "upper": sarima_pred["upper"].values,
        })

