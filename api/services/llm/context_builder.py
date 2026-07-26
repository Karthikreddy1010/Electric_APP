"""
Centralized Context Builder.
Constructs minimal, clean, tab-tailored JSON contexts following a standard unified schema:
{
    "task": "...",
    "customer": {...},
    "bill": {...},
    "simulation": {...},
    "forecast": {...},
    "recommendations": {...},
    "statistics": {...},
    "metadata": {...}
}
"""
from typing import Dict, Any, Optional

class ContextBuilder:
    @staticmethod
    def _base_schema(task: str) -> Dict[str, Any]:
        return {
            "task": task,
            "customer": {},
            "bill": {},
            "simulation": {},
            "forecast": {},
            "recommendations": {},
            "statistics": {},
            "metadata": {"schema_version": "v1.0"}
        }

    @classmethod
    def build_bill_analysis_context(
        cls,
        uploaded_bill: Dict[str, Any],
        ocr_runs: Optional[list] = None,
        validation_flags: Optional[list] = None
    ) -> Dict[str, Any]:
        ctx = cls._base_schema("bill_analysis")
        ctx["customer"] = {
            "utility": uploaded_bill.get("utility"),
            "customer_id": uploaded_bill.get("customer_id"),
            "rate_schedule": uploaded_bill.get("rate_schedule")
        }
        ctx["bill"] = {
            "billing_period": uploaded_bill.get("billing_period"),
            "usage_kwh": uploaded_bill.get("usage_kwh"),
            "total_bill": uploaded_bill.get("total_bill"),
            "effective_rate": uploaded_bill.get("effective_rate"),
            "monthly_service_charge": uploaded_bill.get("monthly_service_charge"),
            "delivery_charge": uploaded_bill.get("delivery_charge"),
            "supply_charge": uploaded_bill.get("supply_charge"),
            "tax": uploaded_bill.get("tax"),
            "components": uploaded_bill.get("canonical_bill", {}).get("components", [])
        }
        if ocr_runs:
            ctx["bill"]["ocr_runs"] = ocr_runs
        if validation_flags:
            ctx["bill"]["validation_flags"] = validation_flags
        return ctx

    @classmethod
    def build_impact_context(
        cls,
        uploaded_bill: Dict[str, Any],
        simulation_results: Dict[str, Any],
        scenario_inputs: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        ctx = cls._base_schema("impact")
        ctx["bill"] = {
            "utility": uploaded_bill.get("utility"),
            "billing_period": uploaded_bill.get("billing_period"),
            "usage_kwh": uploaded_bill.get("usage_kwh"),
            "total_bill": uploaded_bill.get("total_bill"),
            "rates": uploaded_bill.get("rates", {})
        }
        ctx["simulation"] = {
            "simulated_bill": simulation_results.get("simulated_bill"),
            "total_impact": simulation_results.get("total_impact"),
            "usage_change_kwh": simulation_results.get("usage_change_kwh"),
            "learned_elasticity": simulation_results.get("learned_elasticity"),
            "contributions": simulation_results.get("contributions", {}),
            "decomposition": simulation_results.get("decomposition", {}),
            "distribution": simulation_results.get("distribution", {}),
            "probabilistic": simulation_results.get("probabilistic", {})
        }
        if scenario_inputs:
            ctx["simulation"]["scenario_inputs"] = scenario_inputs
        return ctx

    @classmethod
    def build_forecast_context(
        cls,
        uploaded_bill: Dict[str, Any],
        forecast_results: Dict[str, Any],
        weather_factors: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        ctx = cls._base_schema("forecast")
        ctx["bill"] = {
            "utility": uploaded_bill.get("utility"),
            "usage_kwh": uploaded_bill.get("usage_kwh"),
            "total_bill": uploaded_bill.get("total_bill")
        }
        ctx["forecast"] = {
            "predicted_kwh": forecast_results.get("predicted_kwh"),
            "predicted_cost": forecast_results.get("predicted_cost"),
            "horizon_months": forecast_results.get("horizon_months", 12),
            "confidence_intervals": forecast_results.get("confidence_intervals", {}),
            "trend_direction": forecast_results.get("trend_direction", "Stable")
        }
        if weather_factors:
            ctx["forecast"]["weather_factors"] = weather_factors
        return ctx

    @classmethod
    def build_recommendations_context(
        cls,
        uploaded_bill: Dict[str, Any],
        simulations: Optional[Dict[str, Any]] = None,
        forecast: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        ctx = cls._base_schema("recommendations")
        ctx["bill"] = {
            "utility": uploaded_bill.get("utility"),
            "total_bill": uploaded_bill.get("total_bill"),
            "usage_kwh": uploaded_bill.get("usage_kwh")
        }
        if simulations:
            ctx["simulation"] = simulations
        if forecast:
            ctx["forecast"] = forecast
        return ctx

    @classmethod
    def build_overview_context(
        cls,
        dashboard_summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        ctx = cls._base_schema("overview")
        ctx["bill"] = dashboard_summary.get("current_bill", {})
        ctx["statistics"] = dashboard_summary.get("metrics", {})
        ctx["forecast"] = dashboard_summary.get("forecast_overview", {})
        return ctx

    @classmethod
    def build_benchmark_context(
        cls,
        utility_code: str,
        peer_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        ctx = cls._base_schema("benchmark")
        ctx["customer"]["utility"] = utility_code
        ctx["statistics"] = peer_metrics
        return ctx

    @classmethod
    def build_geo_context(
        cls,
        state_code: str,
        geo_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        ctx = cls._base_schema("geo")
        ctx["statistics"] = {
            "state_code": state_code,
            "metrics": geo_data
        }
        return ctx

    @classmethod
    def build_chat_context(
        cls,
        current_tab: str,
        uploaded_bill: Optional[Dict[str, Any]] = None,
        simulation_results: Optional[Dict[str, Any]] = None,
        forecast_results: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[list] = None
    ) -> Dict[str, Any]:
        ctx = cls._base_schema("chat")
        ctx["metadata"]["current_tab"] = current_tab
        if uploaded_bill:
            ctx["bill"] = {
                "utility": uploaded_bill.get("utility"),
                "total_bill": uploaded_bill.get("total_bill"),
                "usage_kwh": uploaded_bill.get("usage_kwh"),
                "effective_rate": uploaded_bill.get("effective_rate"),
                "monthly_service_charge": uploaded_bill.get("monthly_service_charge") or uploaded_bill.get("fixed_charge"),
                "delivery_charge": uploaded_bill.get("delivery_charge"),
                "supply_charge": uploaded_bill.get("supply_charge"),
                "tax": uploaded_bill.get("tax") or uploaded_bill.get("taxes_and_fees"),
                "rate_schedule": uploaded_bill.get("rate_schedule"),
                "billing_period": uploaded_bill.get("billing_period")
            }
        if simulation_results:
            ctx["simulation"] = {
                "simulated_bill": simulation_results.get("simulated_bill"),
                "total_impact": simulation_results.get("total_impact"),
                "contributions": simulation_results.get("contributions", {})
            }
        if forecast_results:
            ctx["forecast"] = forecast_results
        if conversation_history:
            ctx["metadata"]["conversation_history"] = conversation_history[-5:]
        return ctx
