"""
Master Feature Registry
Defines metadata, formulas, units, null policies, and dependencies for all engineered features.
"""
from __future__ import annotations
from typing import Dict, List, Any, Optional


class FeatureMetadata:
    def __init__(
        self,
        name: str,
        description: str,
        unit: str,
        formula: str,
        source_dataset: str,
        source_columns: List[str],
        null_policy: str,
        validation_rules: Dict[str, Any],
        consuming_tabs: List[str],
        visualization_type: str,
    ):
        self.name = name
        self.description = description
        self.unit = unit
        self.formula = formula
        self.source_dataset = source_dataset
        self.source_columns = source_columns
        self.null_policy = null_policy
        self.validation_rules = validation_rules
        self.consuming_tabs = consuming_tabs
        self.visualization_type = visualization_type

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "unit": self.unit,
            "formula": self.formula,
            "source_dataset": self.source_dataset,
            "source_columns": self.source_columns,
            "null_policy": self.null_policy,
            "validation_rules": self.validation_rules,
            "consuming_tabs": self.consuming_tabs,
            "visualization_type": self.visualization_type,
        }


class FeatureRegistry:
    def __init__(self):
        self._features: Dict[str, FeatureMetadata] = {}
        self._register_default_features()

    def _register_default_features(self):
        # 1. Effective Price
        self.register(
            FeatureMetadata(
                name="effective_price",
                description="Calculated average price per kWh from total revenue and sales",
                unit="cents/kWh",
                formula="retail_revenue * 100 / retail_sales",
                source_dataset="EIA Retail",
                source_columns=["retail_revenue", "retail_sales"],
                null_policy="Fill 0.0 or forward fill",
                validation_rules={"min": 0.0, "max": 100.0},
                consuming_tabs=["Dashboard", "Regional Insights", "Benchmark", "Forecast"],
                visualization_type="line_chart",
            )
        )

        # 2. YoY Price Growth
        self.register(
            FeatureMetadata(
                name="price_yoy_growth",
                description="Year-over-Year percentage change in retail price",
                unit="percentage (%)",
                formula="(price[t] - price[t-12]) / price[t-12] * 100",
                source_dataset="EIA Retail",
                source_columns=["retail_price", "period"],
                null_policy="Fill 0.0",
                validation_rules={"min": -50.0, "max": 100.0},
                consuming_tabs=["Dashboard", "Regional Insights", "Benchmark", "Recommendations"],
                visualization_type="bar_chart",
            )
        )

        # 3. 12-Month Rolling Price Average
        self.register(
            FeatureMetadata(
                name="price_rolling_12m",
                description="12-month trailing moving average of retail electricity price",
                unit="cents/kWh",
                formula="rolling_mean(retail_price, window=12)",
                source_dataset="EIA Retail",
                source_columns=["retail_price"],
                null_policy="Backfill using available months",
                validation_rules={"min": 0.0, "max": 100.0},
                consuming_tabs=["Dashboard", "Forecast", "Regional Insights"],
                visualization_type="smoothed_line",
            )
        )

        # 4. Price Volatility Index
        self.register(
            FeatureMetadata(
                name="price_volatility_index",
                description="12-month rolling standard deviation normalized by mean price",
                unit="index (0-1)",
                formula="rolling_std(retail_price, 12) / rolling_mean(retail_price, 12)",
                source_dataset="EIA Retail",
                source_columns=["retail_price"],
                null_policy="Fill 0.0",
                validation_rules={"min": 0.0, "max": 1.0},
                consuming_tabs=["Regional Insights", "Benchmark"],
                visualization_type="gauge",
            )
        )

        # 5. Average Monthly Usage per Customer
        self.register(
            FeatureMetadata(
                name="avg_usage_per_customer",
                description="Average monthly kWh consumed per customer account",
                unit="kWh/customer",
                formula="retail_sales * 1,000,000 / retail_customers",
                source_dataset="EIA Retail",
                source_columns=["retail_sales", "retail_customers"],
                null_policy="Fill 0.0",
                validation_rules={"min": 0.0, "max": 50000.0},
                consuming_tabs=["Dashboard", "Regional Insights", "Benchmark"],
                visualization_type="kpi_card",
            )
        )

        # 6. Real Price Inflation Adjusted
        self.register(
            FeatureMetadata(
                name="real_price_cpi_adjusted",
                description="Retail price adjusted for inflation using CPI deflators",
                unit="cents/kWh (real dollars)",
                formula="retail_price / cpi_factor",
                source_dataset="EIA Retail + CPI",
                source_columns=["retail_price", "cpi"],
                null_policy="Use nominal price fallback",
                validation_rules={"min": 0.0, "max": 100.0},
                consuming_tabs=["Dashboard", "Regional Insights", "Benchmark"],
                visualization_type="line_chart",
            )
        )

    def register(self, feature: FeatureMetadata):
        self._features[feature.name] = feature

    def get(self, name: str) -> Optional[FeatureMetadata]:
        return self._features.get(name)

    def list_all(self) -> List[Dict[str, Any]]:
        return [f.to_dict() for f in self._features.values()]


# Global Feature Registry Instance
feature_registry = FeatureRegistry()
