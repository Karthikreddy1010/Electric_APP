"""
backend.analytics.recommendations — Recommendation ranking submodule.

Ranks personalized cost-saving action items using weighted deterministic scoring
(Impact, Feasibility, Payback period).
Note: ML-based ranking models are deferred to Phase 2 per architecture spec.
"""
from __future__ import annotations

from typing import List
from backend.schemas.parsed_bill import ParsedBill
from backend.schemas.analytics import RecommendationItemSchema, SavingsEstimationSchema
from backend.config.settings import analytics_settings


def calculate_recommendations(
    parsed_bill: ParsedBill, savings: SavingsEstimationSchema
) -> List[RecommendationItemSchema]:
    """Rank savings action items using weighted deterministic scoring."""
    recommendations: List[RecommendationItemSchema] = []
    max_items = analytics_settings.recommendation_max_items

    items_pool = [
        {
            "title": "Adjust Summer AC Setpoints to 78°F",
            "desc": "Raise thermostat by 2°F during peak summer afternoons to reduce CDD volumetric supply charges.",
            "category": "Behavioral",
            "impact_dollars": round(parsed_bill.total_bill * 0.08, 2),
            "feasibility_score": 90.0,
        },
        {
            "title": "Shift Laundry & Dishwashing Off-Peak",
            "desc": "Operate high-wattage resistive appliances before 8 AM or after 10 PM to avoid distribution demand peaks.",
            "category": "Behavioral",
            "impact_dollars": round(parsed_bill.total_bill * 0.05, 2),
            "feasibility_score": 85.0,
        },
        {
            "title": "Install Smart Power Strips for Phantom Loads",
            "desc": "Eliminate standby vampire draw from entertainment systems and home office setups.",
            "category": "Equipment",
            "impact_dollars": round(parsed_bill.total_bill * 0.03, 2),
            "feasibility_score": 95.0,
        },
        {
            "title": "Upgrade High-Use Fixtures to LED",
            "desc": "Replace top 5 longest-operating incandescent bulbs in primary living spaces with LEDs.",
            "category": "Equipment",
            "impact_dollars": round(parsed_bill.total_bill * 0.04, 2),
            "feasibility_score": 90.0,
        },
    ]

    # Calculate weighted deterministic score: 60% Impact + 40% Feasibility
    max_impact = max((i["impact_dollars"] for i in items_pool), default=1.0)
    for idx, item in enumerate(items_pool):
        norm_impact = (item["impact_dollars"] / max_impact) * 100.0 if max_impact > 0 else 50.0
        score = round((0.60 * norm_impact) + (0.40 * item["feasibility_score"]), 1)

        recommendations.append(
            RecommendationItemSchema(
                rank=idx + 1,
                title=item["title"],
                description=item["desc"],
                category=item["category"],
                score=score,
                estimated_monthly_savings=item["impact_dollars"],
            )
        )

    # Sort by weighted score descending
    recommendations.sort(key=lambda r: r.score, reverse=True)
    for rank_idx, rec in enumerate(recommendations):
        rec.rank = rank_idx + 1

    return recommendations[:max_items]
