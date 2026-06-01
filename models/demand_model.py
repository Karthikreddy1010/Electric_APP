"""
Demand Response Model: Learned Electricity Usage Prediction.

Replaces the hardcoded demand elasticity (ε = -0.2) with a data-driven model
that learns the relationship between price, weather, seasonality, and usage.

Model equation:
    kWh_t = β₀ + β₁·effective_rate + β₂·CDD + β₃·HDD
          + β₄·sin(month) + β₅·cos(month) + β₆·lag₁ + β₇·lag₁₂ + β₈·LMP

Training: RidgeCV with leave-one-out cross-validation (fast, interpretable).
Inference: <10ms per prediction, vectorized batch support for Monte Carlo.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

# Features the demand model uses — must exist in the feature matrix
DEMAND_FEATURES = [
    "effective_rate",       # $/kWh composite price signal
    "monthly_CDD",         # cooling degree days
    "monthly_HDD",         # heating degree days
    "month_sin",           # cyclical seasonality
    "month_cos",           # cyclical seasonality
    "usage_kwh_lag_1",     # autoregressive: last month
    "usage_kwh_lag_12",    # autoregressive: same month last year
    "avg_lmp",             # PJM wholesale price proxy
]

# Economically plausible elasticity bounds
ELASTICITY_LOWER = -0.60
ELASTICITY_UPPER = -0.02
FALLBACK_ELASTICITY = -0.20


class DemandResponseModel:
    """
    Learned demand model that predicts electricity usage (kWh) given
    price, weather, seasonality, and lagged usage.

    Replaces the fixed DEMAND_ELASTICITY = -0.2 with a data-driven estimate.
    """

    def __init__(self):
        self.model: Optional[RidgeCV] = None
        self.scaler: Optional[StandardScaler] = None
        self.feature_names: list[str] = []
        self.is_trained: bool = False
        self.training_stats: Dict[str, float] = {}
        self._learned_elasticity: float = FALLBACK_ELASTICITY
        self._residual_std: float = 0.0  # for prediction intervals
        self._coef_bootstrap: Optional[np.ndarray] = None  # (n_boot, n_features)

    # ─────────────────────────────────────────────────────────────────────
    #  TRAINING
    # ─────────────────────────────────────────────────────────────────────

    def train(self, feature_df: pd.DataFrame, feature_cols: list[str],
              target_col: str = "usage_kwh", n_bootstrap: int = 200) -> Dict[str, Any]:
        """
        Train the demand model on the feature matrix.

        Parameters
        ----------
        feature_df : DataFrame with all engineered features (from build_feature_matrix)
        feature_cols : list of available feature column names
        target_col : target variable (default: usage_kwh)
        n_bootstrap : number of bootstrap resamples for coefficient uncertainty

        Returns
        -------
        dict with training metrics
        """
        t0 = time.perf_counter()

        # Select available demand features
        available = [f for f in DEMAND_FEATURES if f in feature_df.columns]
        if len(available) < 3:
            logger.warning(
                f"Only {len(available)} demand features available ({available}). "
                f"Need ≥3. Falling back to hardcoded elasticity."
            )
            return {"status": "fallback", "elasticity": FALLBACK_ELASTICITY}

        self.feature_names = available
        df = feature_df.dropna(subset=available + [target_col]).copy()

        if len(df) < 24:
            logger.warning(f"Only {len(df)} rows for demand model. Need ≥24. Falling back.")
            return {"status": "fallback", "elasticity": FALLBACK_ELASTICITY}

        X = df[available].values.astype(np.float64)
        y = df[target_col].values.astype(np.float64)

        # Standardize features for stable Ridge regression
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        # RidgeCV with built-in LOO cross-validation
        self.model = RidgeCV(
            alphas=np.logspace(-3, 4, 50),
            scoring="neg_mean_squared_error",
            cv=None,  # efficient LOO
        )
        self.model.fit(X_scaled, y)

        # Compute residual std for prediction intervals
        y_pred = self.model.predict(X_scaled)
        residuals = y - y_pred
        self._residual_std = float(np.std(residuals))

        # Extract learned elasticity (coefficient on price feature)
        self._compute_elasticity(df, available, y)

        # Bootstrap for coefficient uncertainty (for interval predictions)
        self._bootstrap_coefficients(X_scaled, y, n_bootstrap)

        self.is_trained = True
        elapsed_ms = (time.perf_counter() - t0) * 1000

        # Training statistics
        r2 = float(self.model.score(X_scaled, y))
        mae = float(np.mean(np.abs(residuals)))
        self.training_stats = {
            "status": "trained",
            "n_samples": len(df),
            "n_features": len(available),
            "features_used": available,
            "r2": round(r2, 4),
            "mae_kwh": round(mae, 1),
            "residual_std_kwh": round(self._residual_std, 1),
            "alpha_selected": round(float(self.model.alpha_), 4),
            "learned_elasticity": round(self._learned_elasticity, 4),
            "training_time_ms": round(elapsed_ms, 1),
        }

        logger.info(
            f"DemandResponseModel trained: R²={r2:.4f}, MAE={mae:.1f} kWh, "
            f"ε={self._learned_elasticity:.4f}, α={self.model.alpha_:.4f}, "
            f"{elapsed_ms:.0f}ms"
        )
        return self.training_stats

    def _compute_elasticity(self, df: pd.DataFrame, features: list[str], y: np.ndarray):
        """
        Extract price elasticity from the fitted Ridge coefficients.

        Elasticity = (∂kWh/∂price) × (mean_price / mean_kWh)

        The coefficient is in standardized space, so we convert back:
            β_original = β_scaled / std(price)
        """
        price_col = "effective_rate"
        if price_col not in features:
            logger.warning("No price feature available — using fallback elasticity")
            self._learned_elasticity = FALLBACK_ELASTICITY
            return

        price_idx = features.index(price_col)
        # Convert standardized coefficient back to original scale
        beta_scaled = self.model.coef_[price_idx]
        price_std = self.scaler.scale_[price_idx]
        beta_original = beta_scaled / price_std

        mean_price = float(df[price_col].mean())
        mean_kwh = float(y.mean())

        if mean_kwh > 0 and mean_price > 0:
            elasticity = beta_original * (mean_price / mean_kwh)
        else:
            elasticity = FALLBACK_ELASTICITY

        # Clamp to economically plausible range
        self._learned_elasticity = float(np.clip(elasticity, ELASTICITY_LOWER, ELASTICITY_UPPER))

    def _bootstrap_coefficients(self, X: np.ndarray, y: np.ndarray, n_boot: int):
        """Bootstrap resample to estimate coefficient uncertainty."""
        n = len(y)
        rng = np.random.default_rng(42)
        coefs = np.zeros((n_boot, X.shape[1]))

        for i in range(n_boot):
            idx = rng.choice(n, size=n, replace=True)
            model_b = RidgeCV(
                alphas=[self.model.alpha_],  # reuse selected alpha for speed
                cv=None,
            )
            model_b.fit(X[idx], y[idx])
            coefs[i] = model_b.coef_

        self._coef_bootstrap = coefs

    # ─────────────────────────────────────────────────────────────────────
    #  PREDICTION
    # ─────────────────────────────────────────────────────────────────────

    def predict(self, features: Dict[str, float]) -> float:
        """
        Predict kWh for a single observation.

        Parameters
        ----------
        features : dict mapping feature names to values

        Returns
        -------
        Predicted kWh (clipped to [100, 5000])
        """
        if not self.is_trained:
            return features.get("usage_kwh_lag_1", 750.0)

        x = np.array([[features.get(f, 0.0) for f in self.feature_names]])
        x_scaled = self.scaler.transform(x)
        pred = float(self.model.predict(x_scaled)[0])
        return float(np.clip(pred, 100, 5000))

    def predict_batch(self, features_array: np.ndarray) -> np.ndarray:
        """
        Vectorized prediction for Monte Carlo simulation.

        Parameters
        ----------
        features_array : (n_samples, n_features) array in feature_names order

        Returns
        -------
        (n_samples,) array of predicted kWh values
        """
        if not self.is_trained:
            return np.full(features_array.shape[0], 750.0)

        x_scaled = self.scaler.transform(features_array)
        preds = self.model.predict(x_scaled)
        return np.clip(preds, 100, 5000)

    def predict_with_intervals(self, features: Dict[str, float],
                                confidence: float = 0.95) -> Dict[str, float]:
        """
        Predict kWh with prediction intervals using bootstrap + residual uncertainty.

        Returns
        -------
        dict with 'median', 'lower', 'upper', 'std'
        """
        if not self.is_trained or self._coef_bootstrap is None:
            point = features.get("usage_kwh_lag_1", 750.0)
            return {"median": point, "lower": point * 0.8, "upper": point * 1.2, "std": point * 0.1}

        x = np.array([[features.get(f, 0.0) for f in self.feature_names]])
        x_scaled = self.scaler.transform(x)

        # Bootstrap prediction distribution
        boot_preds = x_scaled @ self._coef_bootstrap.T + self.model.intercept_
        boot_preds = boot_preds.flatten()

        # Add residual noise
        rng = np.random.default_rng()
        noise = rng.normal(0, self._residual_std, len(boot_preds))
        boot_preds_noisy = boot_preds + noise

        alpha = (1 - confidence) / 2
        return {
            "median": float(np.clip(np.median(boot_preds_noisy), 100, 5000)),
            "lower": float(np.clip(np.percentile(boot_preds_noisy, alpha * 100), 100, 5000)),
            "upper": float(np.clip(np.percentile(boot_preds_noisy, (1 - alpha) * 100), 100, 5000)),
            "std": float(np.std(boot_preds_noisy)),
        }

    # ─────────────────────────────────────────────────────────────────────
    #  ACCESSORS
    # ─────────────────────────────────────────────────────────────────────

    def get_learned_elasticity(self) -> float:
        """Return the learned price elasticity of demand (always negative)."""
        return self._learned_elasticity

    def get_coefficients(self) -> Dict[str, float]:
        """Return feature coefficients in original (unscaled) space."""
        if not self.is_trained:
            return {}
        coefs_original = self.model.coef_ / self.scaler.scale_
        return {
            name: round(float(coef), 6)
            for name, coef in zip(self.feature_names, coefs_original)
        }

    def get_feature_importance(self) -> list[Dict[str, Any]]:
        """Return features ranked by absolute standardized coefficient magnitude."""
        if not self.is_trained:
            return []
        abs_coefs = np.abs(self.model.coef_)
        order = np.argsort(-abs_coefs)
        return [
            {
                "feature": self.feature_names[i],
                "importance": round(float(abs_coefs[i]), 4),
                "coefficient": round(float(self.model.coef_[i]), 4),
                "direction": "positive" if self.model.coef_[i] > 0 else "negative",
            }
            for i in order
        ]

    def build_features_from_row(self, row: dict, overrides: Optional[dict] = None) -> Dict[str, float]:
        """
        Extract demand model features from a billing row dict.
        Applies optional overrides (e.g., modified price or weather).
        """
        features = {}
        for f in self.feature_names:
            features[f] = float(row.get(f, 0.0))

        if overrides:
            features.update(overrides)

        return features

    def build_features_batch(self, base_features: Dict[str, float],
                              effective_rates: np.ndarray,
                              cdd_draws: np.ndarray,
                              hdd_draws: np.ndarray,
                              month: int) -> np.ndarray:
        """
        Build a (n_sim, n_features) array for vectorized Monte Carlo prediction.

        Parameters
        ----------
        base_features : base feature values from latest billing row
        effective_rates : (n_sim,) array of composite price signals
        cdd_draws : (n_sim,) array of CDD samples
        hdd_draws : (n_sim,) array of HDD samples
        month : calendar month (1-12)

        Returns
        -------
        (n_sim, n_features) array ready for predict_batch()
        """
        n_sim = len(effective_rates)
        n_feat = len(self.feature_names)
        X = np.zeros((n_sim, n_feat))

        for i, f in enumerate(self.feature_names):
            if f == "effective_rate":
                X[:, i] = effective_rates
            elif f == "monthly_CDD":
                X[:, i] = cdd_draws
            elif f == "monthly_HDD":
                X[:, i] = hdd_draws
            elif f == "month_sin":
                X[:, i] = np.sin(2 * np.pi * month / 12)
            elif f == "month_cos":
                X[:, i] = np.cos(2 * np.pi * month / 12)
            else:
                # Static features: lag values, LMP, etc. — use base
                X[:, i] = base_features.get(f, 0.0)

        return X
