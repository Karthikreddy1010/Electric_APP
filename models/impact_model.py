"""
Bill Impact Model: XGBoost + SHAP explainability + DoWhy causal inference.

Purpose: Decompose electricity bill changes into component contributions
and identify causal drivers (weather, market prices, regulatory changes).
"""
import numpy as np
import pandas as pd
import xgboost as xgb
import shap
import joblib
import logging
from pathlib import Path
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from typing import Optional

logger = logging.getLogger(__name__)


class BillImpactModel:
    """
    XGBoost model for bill impact analysis with SHAP explanations.
    
    Features used:
    - Bill component rates (BGS, transmission, distribution, SBC, NUG)
    - Usage (kWh) and lagged usage
    - Weather (monthly HDD, CDD, avg temp)
    - Market (LMP average, volatility, capacity price)
    - Temporal (month cyclical, year trend)
    """
    
    def __init__(self, n_estimators=500, max_depth=6, learning_rate=0.05):
        self.params = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "learning_rate": learning_rate,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "reg_alpha": 0.1,
            "reg_lambda": 1.0,
            "random_state": 42,
            "objective": "reg:squarederror",
        }
        self.model = None
        self.explainer = None
        self.feature_names = None
        self.metrics = {}
    
    def train(self, X: pd.DataFrame, y: pd.Series, 
              eval_split: float = 0.2) -> dict:
        """
        Train XGBoost with time-series aware validation.
        Returns training metrics.
        """
        self.feature_names = list(X.columns)
        
        # Time-series split (no shuffling - preserves temporal order)
        split_idx = int(len(X) * (1 - eval_split))
        X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]
        
        self.model = xgb.XGBRegressor(**self.params)
        self.model.fit(
            X_train, y_train,
            eval_set=[(X_val, y_val)],
            verbose=False,
        )
        
        # Evaluate
        y_pred = self.model.predict(X_val)
        self.metrics = {
            "rmse": float(np.sqrt(mean_squared_error(y_val, y_pred))),
            "mae": float(mean_absolute_error(y_val, y_pred)),
            "r2": float(r2_score(y_val, y_pred)),
            "mape": float(np.mean(np.abs((y_val - y_pred) / y_val)) * 100),
            "n_train": len(X_train),
            "n_val": len(X_val),
            "n_features": len(self.feature_names),
        }
        
        logger.info(f"Impact model trained: RMSE=${self.metrics['rmse']:.2f}, "
                    f"R²={self.metrics['r2']:.4f}, MAPE={self.metrics['mape']:.1f}%")
        
        # Build SHAP explainer
        self.explainer = shap.TreeExplainer(self.model)
        
        return self.metrics
    
    def cross_validate(self, X: pd.DataFrame, y: pd.Series, 
                       n_splits: int = 5) -> dict:
        """Time-series cross-validation."""
        tscv = TimeSeriesSplit(n_splits=n_splits)
        scores = {"rmse": [], "mae": [], "r2": []}
        
        for train_idx, val_idx in tscv.split(X):
            X_tr, X_va = X.iloc[train_idx], X.iloc[val_idx]
            y_tr, y_va = y.iloc[train_idx], y.iloc[val_idx]
            
            model = xgb.XGBRegressor(**self.params)
            model.fit(X_tr, y_tr, verbose=False)
            y_pred = model.predict(X_va)
            
            scores["rmse"].append(np.sqrt(mean_squared_error(y_va, y_pred)))
            scores["mae"].append(mean_absolute_error(y_va, y_pred))
            scores["r2"].append(r2_score(y_va, y_pred))
        
        return {k: {"mean": np.mean(v), "std": np.std(v)} for k, v in scores.items()}
    
    def explain(self, X: pd.DataFrame) -> dict:
        """
        Compute SHAP values for bill impact decomposition.
        Returns dict with feature importances and per-sample explanations.
        """
        if self.explainer is None:
            raise RuntimeError("Model not trained. Call train() first.")
        
        shap_values = self.explainer.shap_values(X)
        
        # Global feature importance (mean absolute SHAP)
        importance = pd.DataFrame({
            "feature": self.feature_names,
            "mean_abs_shap": np.abs(shap_values).mean(axis=0),
            "mean_shap": shap_values.mean(axis=0),
        }).sort_values("mean_abs_shap", ascending=False)
        
        # Per-sample breakdown (last row = most recent)
        latest_shap = shap_values[-1]
        breakdown = pd.DataFrame({
            "feature": self.feature_names,
            "shap_value": latest_shap,
            "feature_value": X.iloc[-1].values,
        }).sort_values("shap_value", key=abs, ascending=False)
        
        base_value = float(self.explainer.expected_value)
        
        return {
            "global_importance": importance.to_dict(orient="records"),
            "latest_breakdown": breakdown.head(15).to_dict(orient="records"),
            "base_value": base_value,
            "predicted_value": float(base_value + latest_shap.sum()),
            "shap_values": shap_values,
        }
    
    def get_component_impact(self, X: pd.DataFrame) -> dict:
        """
        Group SHAP values by bill component category.
        Returns impact by: usage, weather, market, rates, temporal.
        """
        shap_values = self.explainer.shap_values(X)
        mean_shap = np.abs(shap_values).mean(axis=0)
        
        categories = {
            "usage": ["usage_kwh", "usage_kwh_lag", "hdd_per_kwh", "cdd_per_kwh"],
            "weather": ["monthly_hdd", "monthly_cdd", "avg_temp", "temp_std", "humidity"],
            "market": ["avg_lmp", "max_lmp", "lmp_volatility", "avg_capacity_price", "congestion"],
            "rates": ["bgs_rate", "transmission_rate", "distribution_rate", "sbc_rate", "nug_rate"],
            "temporal": ["month_sin", "month_cos", "year", "is_summer", "is_winter"],
        }
        
        impacts = {}
        for cat, keywords in categories.items():
            cat_indices = [i for i, f in enumerate(self.feature_names) 
                          if any(k in f.lower() for k in keywords)]
            if cat_indices:
                impacts[cat] = float(mean_shap[cat_indices].sum())
        
        total = sum(impacts.values()) or 1
        impacts = {k: {"absolute": v, "pct": round(v/total*100, 1)} 
                   for k, v in impacts.items()}
        
        return impacts
    
    def save(self, path: str):
        """Save model and explainer."""
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.model, p / "xgb_impact_model.joblib")
        joblib.dump(self.feature_names, p / "feature_names.joblib")
        joblib.dump(self.metrics, p / "metrics.joblib")
        logger.info(f"Model saved to {p}")
    
    def load(self, path: str):
        """Load model and rebuild explainer."""
        p = Path(path)
        self.model = joblib.load(p / "xgb_impact_model.joblib")
        self.feature_names = joblib.load(p / "feature_names.joblib")
        self.metrics = joblib.load(p / "metrics.joblib")
        self.explainer = shap.TreeExplainer(self.model)
        logger.info(f"Model loaded from {p}")


def run_causal_analysis(df: pd.DataFrame, treatment: str, outcome: str,
                        common_causes: list[str]) -> dict:
    """
    Run DoWhy causal inference to estimate causal effect of treatment on outcome.
    
    Example: Does a rate increase *cause* higher bills, controlling for usage/weather?
    
    Args:
        df: Feature matrix
        treatment: column name of treatment variable (e.g., 'bgs_rate')
        outcome: column name of outcome (e.g., 'total_bill')
        common_causes: confounders to control for
    
    Returns:
        dict with causal estimate, confidence interval, refutation results
    """
    try:
        import dowhy
        from dowhy import CausalModel
    except ImportError:
        logger.warning("DoWhy not installed. Returning correlation-based estimate.")
        corr = df[[treatment, outcome]].corr().iloc[0, 1]
        return {"method": "correlation_fallback", "estimate": float(corr),
                "note": "Install dowhy for causal inference"}
    
    model = CausalModel(
        data=df,
        treatment=treatment,
        outcome=outcome,
        common_causes=common_causes,
    )
    
    identified = model.identify_effect(proceed_when_unidentifiable=True)
    estimate = model.estimate_effect(
        identified,
        method_name="backdoor.linear_regression",
    )
    
    # Refutation: placebo treatment
    refutation = model.refute_estimate(
        identified, estimate,
        method_name="placebo_treatment_refuter",
        placebo_type="permute",
        num_simulations=100,
    )
    
    return {
        "method": "backdoor.linear_regression",
        "treatment": treatment,
        "outcome": outcome,
        "causal_estimate": float(estimate.value),
        "p_value": float(getattr(estimate, 'test_stat_significance', {}).get('p_value', -1)),
        "refutation_result": str(refutation),
        "interpretation": (
            f"A unit increase in {treatment} causally changes {outcome} "
            f"by ${estimate.value:.2f}, controlling for {common_causes}"
        ),
    }
