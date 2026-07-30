"""
Central Dataset Registry & Access Control Policy Engine
Enforces explicit data access rules for every module in the application.
"""
from __future__ import annotations
import logging
from enum import Enum
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class AccessPolicy(str, Enum):
    READ_ONLY = "READ_ONLY"
    READ_ANALYZE = "READ_ANALYZE"
    READ_JOIN = "READ_JOIN"
    READ_FORECAST = "READ_FORECAST"
    NOT_ALLOWED = "NOT_ALLOWED"


class AccessPolicyViolation(PermissionError):
    """Raised when a module attempts an unpermitted operation on a dataset."""
    pass


class DatasetMetadata:
    def __init__(
        self,
        name: str,
        owner: str,
        source: str,
        update_frequency: str,
        coverage: str,
        granularity: str,
        join_keys: List[str],
        primary_tabs: List[str],
        supporting_tabs: List[str],
        access_policies: Dict[str, AccessPolicy],
        version: str = "v1",
        last_updated: str = "2026-05",
        quality_score: float = 99.5,
    ):
        self.name = name
        self.owner = owner
        self.source = source
        self.update_frequency = update_frequency
        self.coverage = coverage
        self.granularity = granularity
        self.join_keys = join_keys
        self.primary_tabs = primary_tabs
        self.supporting_tabs = supporting_tabs
        self.access_policies = access_policies
        self.version = version
        self.last_updated = last_updated
        self.quality_score = quality_score

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "owner": self.owner,
            "source": self.source,
            "update_frequency": self.update_frequency,
            "coverage": self.coverage,
            "granularity": self.granularity,
            "join_keys": self.join_keys,
            "primary_tabs": self.primary_tabs,
            "supporting_tabs": self.supporting_tabs,
            "version": self.version,
            "last_updated": self.last_updated,
            "quality_score": self.quality_score,
            "access_policies": {k: v.value for k, v in self.access_policies.items()},
        }


class DataRegistry:
    def __init__(self):
        self._datasets: Dict[str, DatasetMetadata] = {}
        self._register_default_datasets()

    def _register_default_datasets(self):
        # 1. EIA Retail Dataset Metadata & Access Control Policy
        self.register(
            DatasetMetadata(
                name="EIA Retail",
                owner="US Energy Information Administration",
                source="Monthly Electricity Retail Sales, Revenue, Price, & Customers (2001-Present)",
                update_frequency="Monthly",
                coverage="50 US States + DC",
                granularity="State-Level Monthly",
                join_keys=["period", "stateid", "sectorid", "year", "month"],
                primary_tabs=[
                    "Dashboard",
                    "Regional Insights",
                    "Benchmark",
                    "Forecast",
                    "Impact Simulator",
                    "Maps",
                    "Admin Analytics",
                ],
                supporting_tabs=["Bill Analysis", "Recommendations", "AI Chat"],
                access_policies={
                    "dashboard": AccessPolicy.READ_ANALYZE,
                    "bill_analysis": AccessPolicy.READ_JOIN,
                    "bill_breakdown": AccessPolicy.NOT_ALLOWED,
                    "bill_explanation": AccessPolicy.NOT_ALLOWED,
                    "forecast": AccessPolicy.READ_FORECAST,
                    "impact_simulator": AccessPolicy.READ_ANALYZE,
                    "regional_insights": AccessPolicy.READ_ANALYZE,
                    "benchmark": AccessPolicy.READ_ANALYZE,
                    "recommendations": AccessPolicy.READ_JOIN,
                    "ai_chat": AccessPolicy.READ_ONLY,
                    "maps": AccessPolicy.READ_ANALYZE,
                    "admin_analytics": AccessPolicy.READ_ANALYZE,
                },
                version="v1",
                last_updated="2026-05",
                quality_score=99.8,
            )
        )

        # 2. Customer Bills Dataset
        self.register(
            DatasetMetadata(
                name="Customer Bills",
                owner="User Upload / OCR Engine",
                source="Extracted Utility Bill PDF / Image Datasets",
                update_frequency="On Demand",
                coverage="Customer Specific",
                granularity="Billing Period / Account",
                join_keys=["state", "utility_id", "billing_period"],
                primary_tabs=["Bill Analysis", "Bill Breakdown", "Bill Explanation", "Recommendations"],
                supporting_tabs=["Impact Simulator", "Dashboard"],
                access_policies={
                    "bill_analysis": AccessPolicy.READ_ANALYZE,
                    "bill_breakdown": AccessPolicy.READ_ANALYZE,
                    "bill_explanation": AccessPolicy.READ_ANALYZE,
                    "recommendations": AccessPolicy.READ_JOIN,
                    "dashboard": AccessPolicy.READ_ONLY,
                },
                version="v1",
                quality_score=98.0,
            )
        )

        # 3. NOAA Weather Dataset
        self.register(
            DatasetMetadata(
                name="NOAA Weather",
                owner="NOAA NCEI",
                source="Monthly Heating & Cooling Degree Days (HDD/CDD)",
                update_frequency="Monthly",
                coverage="US States / Stations",
                granularity="State Monthly",
                join_keys=["stateid", "period", "year", "month"],
                primary_tabs=["Forecast", "Impact Simulator", "Recommendations"],
                supporting_tabs=["Regional Insights"],
                access_policies={
                    "forecast": AccessPolicy.READ_JOIN,
                    "impact_simulator": AccessPolicy.READ_JOIN,
                    "recommendations": AccessPolicy.READ_JOIN,
                    "regional_insights": AccessPolicy.READ_ONLY,
                },
                version="v1",
                quality_score=99.2,
            )
        )

    def register(self, metadata: DatasetMetadata):
        self._datasets[metadata.name.lower()] = metadata
        logger.info(f"Registered dataset '{metadata.name}' (v{metadata.version}) in DataRegistry.")

    def get(self, name: str) -> Optional[DatasetMetadata]:
        return self._datasets.get(name.lower())

    def enforce_policy(self, dataset_name: str, module_id: str, required_level: AccessPolicy) -> bool:
        """Enforces access control policies for a given module and dataset."""
        ds = self.get(dataset_name)
        if not ds:
            raise KeyError(f"Dataset '{dataset_name}' is not registered in DataRegistry.")

        policy = ds.access_policies.get(module_id.lower(), AccessPolicy.NOT_ALLOWED)
        if policy == AccessPolicy.NOT_ALLOWED:
            raise AccessPolicyViolation(
                f"Module '{module_id}' is explicitly FORBIDDEN from accessing dataset '{dataset_name}'."
            )

        # Rank check: NOT_ALLOWED (0) < READ_ONLY (1) < READ_JOIN (2) < READ_ANALYZE (3) < READ_FORECAST (4)
        policy_ranks = {
            AccessPolicy.NOT_ALLOWED: 0,
            AccessPolicy.READ_ONLY: 1,
            AccessPolicy.READ_JOIN: 2,
            AccessPolicy.READ_ANALYZE: 3,
            AccessPolicy.READ_FORECAST: 4,
        }

        if policy_ranks[policy] < policy_ranks[required_level]:
            raise AccessPolicyViolation(
                f"Module '{module_id}' requested '{required_level.value}' access to '{dataset_name}', "
                f"but policy allows maximum '{policy.value}'."
            )
        return True

    def list_all(self) -> List[Dict[str, Any]]:
        return [ds.to_dict() for ds in self._datasets.values()]


# Global Singleton Data Registry Instance
data_registry = DataRegistry()
