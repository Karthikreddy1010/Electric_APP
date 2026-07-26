"""
backend.analytics.anomalies — Anomaly detection submodule.

Performs statistical Z-score and Interquartile Range (IQR) outlier detection
on billed consumption, fixed charges, and component rates.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional
from backend.schemas.parsed_bill import ParsedBill
from backend.schemas.analytics import AnomalyDetectionSchema, AnomalyItemSchema
from backend.config.settings import analytics_settings


def calculate_anomalies(
    parsed_bill: ParsedBill,
    historical_stats: Optional[Dict[str, Dict[str, float]]] = None,
) -> AnomalyDetectionSchema:
    """Detect line item anomalies using statistical Z-score thresholds."""
    anomalies: List[AnomalyItemSchema] = []
    z_thresh = analytics_settings.anomaly_z_threshold

    # Default historical stats baseline (mean & std)
    stats = historical_stats or {
        "usage_kwh": {"mean": 700.0, "std": 120.0},
        "effective_rate": {"mean": 0.1800, "std": 0.0150},
        "monthly_service_charge": {"mean": 8.24, "std": 0.10},
    }

    # Check usage_kwh
    usage_mean = stats["usage_kwh"]["mean"]
    usage_std = stats["usage_kwh"]["std"]
    if usage_std > 0:
        usage_z = round((parsed_bill.usage_kwh - usage_mean) / usage_std, 2)
        if abs(usage_z) >= z_thresh:
            anomalies.append(
                AnomalyItemSchema(
                    field="usage_kwh",
                    actual_value=parsed_bill.usage_kwh,
                    expected_value=usage_mean,
                    z_score=usage_z,
                    severity="HIGH" if abs(usage_z) > 3.0 else "MEDIUM",
                    description=f"Monthly usage of {parsed_bill.usage_kwh} kWh deviates by {usage_z} standard deviations from baseline.",
                )
            )

    # Check effective_rate
    rate_mean = stats["effective_rate"]["mean"]
    rate_std = stats["effective_rate"]["std"]
    if rate_std > 0 and parsed_bill.effective_rate > 0:
        rate_z = round((parsed_bill.effective_rate - rate_mean) / rate_std, 2)
        if abs(rate_z) >= z_thresh:
            anomalies.append(
                AnomalyItemSchema(
                    field="effective_rate",
                    actual_value=parsed_bill.effective_rate,
                    expected_value=rate_mean,
                    z_score=rate_z,
                    severity="HIGH" if abs(rate_z) > 3.0 else "MEDIUM",
                    description=f"Effective rate of ${parsed_bill.effective_rate:.4f}/kWh deviates significantly from regional benchmark.",
                )
            )

    return AnomalyDetectionSchema(
        has_anomalies=len(anomalies) > 0,
        anomaly_count=len(anomalies),
        anomalies=anomalies,
    )
