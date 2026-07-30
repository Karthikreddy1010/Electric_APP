"""
Global Feature Store Interface
Central router providing unified access to dataset modules while enforcing data access control policies.
"""
from __future__ import annotations
import logging
from typing import Dict, Any, Optional
import pandas as pd

from feature_store.data_registry import data_registry, AccessPolicy, AccessPolicyViolation
from feature_store.base.feature_registry import feature_registry
from feature_store.base.validation import validate_eia_retail_dataframe

logger = logging.getLogger(__name__)


class FeatureStoreManager:
    def __init__(self):
        self._dataframes: Dict[str, pd.DataFrame] = {}

    def register_dataframe(self, dataset_name: str, df: pd.DataFrame):
        """Registers a populated feature DataFrame in memory."""
        self._dataframes[dataset_name.lower()] = df
        logger.info(f"Registered DataFrame for '{dataset_name}' ({len(df)} rows, {len(df.columns)} cols).")

    def get_dataset(self, dataset_name: str, requesting_module: str, required_policy: AccessPolicy = AccessPolicy.READ_ANALYZE) -> pd.DataFrame:
        """
        Retrieves a dataset DataFrame after enforcing explicit dataset access control policies.
        """
        # 1. Enforce Access Policy
        data_registry.enforce_policy(dataset_name, requesting_module, required_policy)

        # 2. Retrieve DataFrame
        df = self._dataframes.get(dataset_name.lower())
        if df is None:
            logger.warning(f"DataFrame for '{dataset_name}' not loaded in FeatureStoreManager.")
            return pd.DataFrame()
        return df

    def get_feature_metadata(self, feature_name: str) -> Optional[Dict[str, Any]]:
        feat = feature_registry.get(feature_name)
        return feat.to_dict() if feat else None

    def list_all_features(self) -> list[Dict[str, Any]]:
        return feature_registry.list_all()

    def list_all_datasets(self) -> list[Dict[str, Any]]:
        return data_registry.list_all()


# Global Feature Store Manager Instance
global_feature_store = FeatureStoreManager()
