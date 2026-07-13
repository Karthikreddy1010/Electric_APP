"""
Causal Model Service — Double Machine Learning for True Effect Estimation.

Upgrades the basic DoWhy linear regression to a proper DML framework that
controls for high-dimensional confounders (weather, market, lagged usage).

Estimation procedure:
    Step 1 (Nuisance): Y_residual = Y - E[Y | W]
    Step 2 (Nuisance): T_residual = T - E[T | W]
    Step 3 (Target):   Y_residual = θ × T_residual + ε

Where:
    Y = total_bill
    T = treatment rate (e.g., bgs_rate)
    W = confounders = {usage_kwh, monthly_CDD, monthly_HDD, month_sin,
                       month_cos, usage_kwh_lag_1, avg_lmp}
    θ = causal effect = ∂(total_bill) / ∂(component_rate)

Supports EconML LinearDML (primary) with a manual cross-fitted Ridge fallback.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import KFold

logger = logging.getLogger(__name__)

# Confounders to control for in causal estimation
CONFOUNDER_COLS = [
    "usage_kwh",
    "monthly_CDD",
    "monthly_HDD",
    "month_sin",
    "month_cos",
    "usage_kwh_lag_1",
    "avg_lmp",
]

# Treatment variables (rate components we can estimate causal effects for)
TREATMENT_COLS = [
    "bgs_rate",
    "distribution_rate",
    "transmission_rate",
    "sbc_rate",
    "avg_lmp",
]

OUTCOME_COL = "total_bill"


class CausalModelService:
    """
    Double Machine Learning causal inference for electricity rate effects.

    Estimates the true ∂(total_bill)/∂(rate_component) while controlling
    for weather, usage, seasonality, and wholesale market confounders.
    """

    def __init__(self):
        self.is_fitted: bool = False
        self._feature_df: Optional[pd.DataFrame] = None
        self._available_confounders: list[str] = []
        self._cached_estimates: Dict[str, Dict[str, Any]] = {}
        self._use_econml: bool = False

        # Check if econml is available
        try:
            from econml.dml import LinearDML  # noqa: F401
            self._use_econml = True
            logger.info("EconML available — will use LinearDML for causal inference")
        except ImportError:
            logger.info("EconML not installed — using manual cross-fitted DML fallback")

    def fit(self, feature_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Prepare the causal model on the full feature matrix.
        Pre-computes DML estimates for all treatment variables.

        Parameters
        ----------
        feature_df : DataFrame with billing + weather + market features

        Returns
        -------
        dict with fit summary
        """
        t0 = time.perf_counter()

        # Identify available confounders in this dataset
        self._available_confounders = [
            c for c in CONFOUNDER_COLS if c in feature_df.columns
        ]
        if len(self._available_confounders) < 2:
            logger.warning(
                f"Only {len(self._available_confounders)} confounders available. "
                f"Causal estimates will have limited validity."
            )

        # Filter to rows with all required columns present
        required = self._available_confounders + [OUTCOME_COL]
        available_treatments = [t for t in TREATMENT_COLS if t in feature_df.columns]
        all_cols = required + available_treatments
        df = feature_df.dropna(subset=[c for c in all_cols if c in feature_df.columns]).copy()

        if len(df) < 24:
            logger.warning(f"Only {len(df)} rows for causal model — insufficient")
            return {"status": "insufficient_data", "n_rows": len(df)}

        self._feature_df = df
        self._cached_estimates = {}

        # Pre-compute DML estimates for each treatment
        for treatment in available_treatments:
            try:
                estimate = self._estimate_dml(df, treatment)
                self._cached_estimates[treatment] = estimate
                logger.info(
                    f"  DML({treatment}): θ={estimate['causal_effect_estimate']:.2f}, "
                    f"p={estimate['p_value']:.4f}"
                )
            except Exception as e:
                logger.warning(f"  DML({treatment}) failed: {e}")
                self._cached_estimates[treatment] = {
                    "treatment": treatment,
                    "causal_effect_estimate": 0.0,
                    "std_error": 0.0,
                    "p_value": 1.0,
                    "ci_95": [0.0, 0.0],
                    "confounders_controlled": self._available_confounders,
                    "method": "failed",
                    "interpretation": f"Causal estimation failed for {treatment}",
                    "caveat": str(e),
                }

        self.is_fitted = True
        elapsed_ms = (time.perf_counter() - t0) * 1000

        return {
            "status": "fitted",
            "n_rows": len(df),
            "n_confounders": len(self._available_confounders),
            "treatments_estimated": list(self._cached_estimates.keys()),
            "method": "EconML LinearDML" if self._use_econml else "Manual Cross-Fitted DML",
            "fit_time_ms": round(elapsed_ms, 1),
        }

    def estimate(self, treatment: str) -> Dict[str, Any]:
        """
        Return the causal effect estimate for a treatment variable.
        Uses cached pre-computed estimates from fit().

        Parameters
        ----------
        treatment : rate component name (e.g., 'bgs_rate')

        Returns
        -------
        dict with causal_effect_estimate, std_error, p_value, ci_95, etc.
        """
        if not self.is_fitted:
            return {
                "treatment": treatment,
                "causal_effect_estimate": 0.0,
                "std_error": 0.0,
                "p_value": 1.0,
                "ci_95": [0.0, 0.0],
                "confounders_controlled": [],
                "method": "not_fitted",
                "interpretation": "Causal model has not been fitted yet.",
                "caveat": "Call fit() first with feature matrix data.",
            }

        if treatment in self._cached_estimates:
            return self._cached_estimates[treatment]

        # Compute on-demand if not pre-cached
        if self._feature_df is not None and treatment in self._feature_df.columns:
            try:
                result = self._estimate_dml(self._feature_df, treatment)
                self._cached_estimates[treatment] = result
                return result
            except Exception as e:
                logger.warning(f"On-demand DML for {treatment} failed: {e}")

        return {
            "treatment": treatment,
            "causal_effect_estimate": 0.0,
            "std_error": 0.0,
            "p_value": 1.0,
            "ci_95": [0.0, 0.0],
            "confounders_controlled": self._available_confounders,
            "method": "unavailable",
            "interpretation": f"Treatment '{treatment}' not found in dataset.",
            "caveat": f"Available treatments: {list(self._cached_estimates.keys())}",
        }

    # ─────────────────────────────────────────────────────────────────────
    #  DML ESTIMATION (PRIMARY: EconML, FALLBACK: Manual)
    # ─────────────────────────────────────────────────────────────────────

    def _estimate_dml(self, df: pd.DataFrame, treatment: str) -> Dict[str, Any]:
        """
        Estimate the causal effect of a rate component using DML.
        Tries EconML first, falls back to manual implementation.
        """
        if self._use_econml:
            return self._estimate_econml_dml(df, treatment)
        else:
            return self._estimate_manual_dml(df, treatment)

    def _estimate_econml_dml(self, df: pd.DataFrame, treatment: str) -> Dict[str, Any]:
        """
        EconML LinearDML estimation.

        Uses GradientBoostingRegressor as the nuisance model to flexibly
        control for nonlinear confounding.
        """
        from econml.dml import LinearDML

        W = df[self._available_confounders].values.astype(np.float64)
        T = df[treatment].values.astype(np.float64)
        Y = df[OUTCOME_COL].values.astype(np.float64)

        model = LinearDML(
            model_y=GradientBoostingRegressor(
                n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42
            ),
            model_t=GradientBoostingRegressor(
                n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42
            ),
            cv=3,
            random_state=42,
        )
        model.fit(Y, T, W=W)

        # Extract point estimate and inference
        theta = float(model.const_marginal_effect().flatten()[0])
        inference = model.const_marginal_effect_inference()
        ci = inference.conf_int(alpha=0.05)
        ci_lower = float(ci[0].flatten()[0])
        ci_upper = float(ci[1].flatten()[0])
        std_err = float(inference.std_err.flatten()[0]) if hasattr(inference, 'std_err') else abs(ci_upper - ci_lower) / 3.92
        p_val = float(inference.pvalue().flatten()[0]) if hasattr(inference, 'pvalue') else self._approx_pvalue(theta, std_err)

        # Human-readable interpretation
        direction = "increase" if theta > 0 else "decrease"
        if treatment == "avg_lmp":
            interpretation = (
                f"Controlling for {', '.join(self._available_confounders)}, "
                f"a $1/MWh increase in Wholesale LMP causes an average "
                f"${abs(theta):.2f} {direction} in the total bill."
            )
        else:
            label = treatment.replace("_rate", "").replace("_", " ").title()
            interpretation = (
                f"Controlling for {', '.join(self._available_confounders)}, "
                f"a $0.01/kWh increase in {label} Rate causes an average "
                f"${abs(theta * 0.01):.2f} {direction} in the total bill."
            )

        return {
            "treatment": treatment,
            "causal_effect_estimate": round(theta, 4),
            "std_error": round(std_err, 4),
            "p_value": round(p_val, 6),
            "ci_95": [round(ci_lower, 2), round(ci_upper, 2)],
            "confounders_controlled": self._available_confounders,
            "method": "EconML LinearDML (GBR nuisance)",
            "interpretation": interpretation,
            "caveat": (
                "Estimated via Double Machine Learning on observational data. "
                "Assumes no unobserved confounders beyond those controlled."
            ),
        }

    def _estimate_manual_dml(self, df: pd.DataFrame, treatment: str) -> Dict[str, Any]:
        """
        Manual cross-fitted DML using RidgeCV.

        Implements the Chernozhukov et al. (2018) procedure:
        1. Split data into K folds
        2. For each fold, fit nuisance models on complement
        3. Compute residuals on held-out fold
        4. Regress Y_residual on T_residual to get θ
        """
        W = df[self._available_confounders].values.astype(np.float64)
        T = df[treatment].values.astype(np.float64)
        Y = df[OUTCOME_COL].values.astype(np.float64)
        n = len(Y)

        # Cross-fitted residualization
        kf = KFold(n_splits=3, shuffle=True, random_state=42)
        Y_resid = np.zeros(n)
        T_resid = np.zeros(n)

        for train_idx, test_idx in kf.split(W):
            # Outcome nuisance: E[Y | W]
            model_y = RidgeCV(alphas=np.logspace(-2, 4, 30), cv=None)
            model_y.fit(W[train_idx], Y[train_idx])
            Y_resid[test_idx] = Y[test_idx] - model_y.predict(W[test_idx])

            # Treatment nuisance: E[T | W]
            model_t = RidgeCV(alphas=np.logspace(-2, 4, 30), cv=None)
            model_t.fit(W[train_idx], T[train_idx])
            T_resid[test_idx] = T[test_idx] - model_t.predict(W[test_idx])

        # Final stage: OLS of Y_resid on T_resid
        # θ = (T_resid' T_resid)^{-1} T_resid' Y_resid
        T_resid_sq_sum = float(np.dot(T_resid, T_resid))
        if T_resid_sq_sum < 1e-10:
            raise ValueError(f"Treatment '{treatment}' has near-zero residual variance after partialling out confounders")

        theta = float(np.dot(T_resid, Y_resid) / T_resid_sq_sum)

        # Standard error via heteroskedasticity-robust formula
        epsilon = Y_resid - theta * T_resid
        se_robust = float(np.sqrt(
            np.sum((T_resid ** 2) * (epsilon ** 2)) / (T_resid_sq_sum ** 2)
        ))

        # P-value (two-sided t-test)
        p_val = self._approx_pvalue(theta, se_robust)

        ci_lower = theta - 1.96 * se_robust
        ci_upper = theta + 1.96 * se_robust

        # Human-readable interpretation
        direction = "increase" if theta > 0 else "decrease"
        if treatment == "avg_lmp":
            interpretation = (
                f"Controlling for {', '.join(self._available_confounders)}, "
                f"a $1/MWh increase in Wholesale LMP causes an average "
                f"${abs(theta):.2f} {direction} in the total bill."
            )
        else:
            label = treatment.replace("_rate", "").replace("_", " ").title()
            interpretation = (
                f"Controlling for {', '.join(self._available_confounders)}, "
                f"a $0.01/kWh increase in {label} Rate causes an average "
                f"${abs(theta * 0.01):.2f} {direction} in the total bill."
            )

        return {
            "treatment": treatment,
            "causal_effect_estimate": round(theta, 4),
            "std_error": round(se_robust, 4),
            "p_value": round(p_val, 6),
            "ci_95": [round(ci_lower, 2), round(ci_upper, 2)],
            "confounders_controlled": self._available_confounders,
            "method": "Manual Cross-Fitted DML (RidgeCV nuisance)",
            "interpretation": interpretation,
            "caveat": (
                "Estimated via manual Double Machine Learning on observational data. "
                "Assumes no unobserved confounders beyond those controlled."
            ),
        }

    @staticmethod
    def _approx_pvalue(theta: float, se: float) -> float:
        """Approximate two-sided p-value from z-statistic."""
        if se <= 0 or np.isnan(se):
            return 1.0
        z = abs(theta / se)
        # Quick approximation of 2 * Φ(-|z|) using the error function
        from math import erfc, sqrt
        return float(erfc(z / sqrt(2)))

    # ─────────────────────────────────────────────────────────────────────
    #  BACKWARD-COMPATIBLE WRAPPER
    # ─────────────────────────────────────────────────────────────────────

    def get_causal_impact_legacy(self, treatment: str) -> Dict[str, Any]:
        """
        Return result in the existing CausalResponse schema format
        (treatment, causal_effect_estimate, p_value, interpretation, caveat).
        """
        result = self.estimate(treatment)
        return {
            "treatment": result["treatment"],
            "causal_effect_estimate": result["causal_effect_estimate"],
            "p_value": result["p_value"],
            "interpretation": result["interpretation"],
            "caveat": result["caveat"],
        }
