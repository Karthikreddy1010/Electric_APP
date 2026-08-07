from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


@dataclass
class UserProfile:
    """User preferences and equipment profile for personalization."""
    user_id: str = "default_user"
    utility: str = "PSE&G"
    state: str = "NJ"
    rate_schedule: str = "RS"
    has_solar: bool = False
    has_ev: bool = False
    heating_type: str = "gas"  # gas | electric | heat_pump
    cooling_type: str = "central_ac"
    tone_preference: str = "concise"  # concise | detailed | simple
    budget_target_monthly: Optional[float] = None


class UserPersonalizationLayer:
    """Injects user preferences and home profile into analytics contexts."""

    @staticmethod
    def build_profile(
        user_id: str = "default_user",
        utility: str = "PSE&G",
        state: str = "NJ",
        rate_schedule: str = "RS",
        **kwargs: Any
    ) -> UserProfile:
        return UserProfile(
            user_id=user_id, utility=utility, state=state,
            rate_schedule=rate_schedule, **kwargs
        )

    @classmethod
    def inject_personalization(
        cls,
        ctx: Dict[str, Any],
        profile: Optional[UserProfile] = None
    ) -> Dict[str, Any]:
        if profile is None:
            profile = cls.build_profile()

        cust = ctx.setdefault("customer", {})
        if not cust.get("utility"):
            cust["utility"] = profile.utility
        if not cust.get("rate_schedule"):
            cust["rate_schedule"] = profile.rate_schedule

        ctx.setdefault("metadata", {})["personalization"] = {
            "state": profile.state,
            "has_solar": profile.has_solar,
            "has_ev": profile.has_ev,
            "heating_type": profile.heating_type,
            "cooling_type": profile.cooling_type,
            "tone_preference": profile.tone_preference,
            "budget_target_monthly": profile.budget_target_monthly
        }
        return ctx


class MultiTurnMemoryManager:
    """Manages chat conversation history windowing and context injection."""

    def __init__(self, max_turns: int = 5):
        self.max_turns = max_turns

    def format_history(self, history: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        formatted = []
        for msg in history[-self.max_turns:]:
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content") or msg.get("text") or ""
                formatted.append({"role": role, "content": content})
            elif hasattr(msg, "role") and hasattr(msg, "content"):
                formatted.append({"role": msg.role, "content": msg.content})
        return formatted


class ContextBuilder:
    @staticmethod
    def prune_empty_fields(data: Any) -> Any:
        """Recursively removes empty dictionaries, empty lists, and None values to minimize prompt payload."""
        if isinstance(data, dict):
            pruned = {}
            for k, v in data.items():
                if v is None:
                    continue
                pruned_v = ContextBuilder.prune_empty_fields(v)
                if isinstance(pruned_v, (dict, list)) and len(pruned_v) == 0:
                    continue
                pruned[k] = pruned_v
            return pruned
        elif isinstance(data, list):
            return [ContextBuilder.prune_empty_fields(item) for item in data if item is not None]
    @staticmethod
    def filter_by_intent(task: str, context_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Intent-aware context filtering. Filters out irrelevant context sections for specific tasks
        to guarantee prompts fit well within the context window budget.
        """
        if not isinstance(context_data, dict):
            return context_data

        filtered = dict(context_data)

        if task == "bill_analysis":
            filtered.pop("forecast", None)
            filtered.pop("simulation", None)
        elif task == "forecast":
            filtered.pop("simulation", None)
            filtered.pop("ocr_runs", None)
        elif task == "impact":
            filtered.pop("forecast", None)
        elif task in ("tariff", "faq", "chat"):
            filtered.pop("simulation", None)
            filtered.pop("forecast", None)

        return filtered

    @staticmethod
    def _base_schema(task: str) -> Dict[str, Any]:
        return {
            "task": task,
            "customer": {},
            "bill": {},
            "simulation": {},
            "forecast": {},
            "weather": {},
            "recommendations": {},
            "statistics": {},
            "metadata": {"schema_version": "v1.1"}
        }

    @staticmethod
    def _inject_weather_context(
        ctx: Dict[str, Any],
        year: Optional[int] = None,
        month: Optional[int] = None,
        location: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Inject pre-computed weather summary from WeatherService into context.
        Provides aggregated metrics (NOT raw rows) for LLM consumption.
        """
        try:
            from backend.analytics.weather import weather_service
            summary = weather_service.get_weather_summary(
                location=location, year=year, month=month
            )
            if summary.get("available"):
                ctx["weather"] = summary

                # Also load dataset catalog metadata for provenance
                try:
                    import json
                    from pathlib import Path
                    catalog_path = Path(__file__).resolve().parent.parent.parent.parent / "data" / "dataset_catalog.json"
                    if catalog_path.exists():
                        with open(catalog_path) as f:
                            catalog = json.load(f)
                        nrel_ds = next((d for d in catalog.get("datasets", []) if d["id"] == "nrel_nasa_power"), None)
                        if nrel_ds:
                            ctx["metadata"]["weather_dataset"] = {
                                "name": nrel_ds["name"],
                                "source": nrel_ds["source"],
                                "coverage": nrel_ds["temporal_coverage"],
                                "counties": nrel_ds["spatial_coverage"]["granularity"],
                            }
                except Exception:
                    pass
        except Exception:
            pass
        return ctx

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

        # Inject weather context for the billing period
        billing_period = uploaded_bill.get("billing_period", "")
        if billing_period:
            try:
                from datetime import datetime as _dt
                bp_date = _dt.strptime(billing_period[:10], "%Y-%m-%d")
                ctx = cls._inject_weather_context(ctx, year=bp_date.year, month=bp_date.month)
            except Exception:
                pass

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

        # Always inject weather context for forecast
        ctx = cls._inject_weather_context(ctx)

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

        # Attach EIA-923 Contextual Knowledge
        try:
            from api.services.eia923_service import get_eia923_fuel_cost_summary, get_eia923_generation_summary
            fuel_cost = get_eia923_fuel_cost_summary("NJ")
            gen_summary = get_eia923_generation_summary("NJ")
            ctx["metadata"]["eia923_context"] = {
                "delivered_gas_price_dollars_mmbtu": fuel_cost.get("avg_cost_dollars_mmbtu"),
                "fuel_price_mom_change_pct": fuel_cost.get("mom_change_pct"),
                "grid_clean_share_pct": gen_summary.get("clean_share_pct"),
                "grid_carbon_intensity_lbs_mwh": gen_summary.get("grid_carbon_intensity_lbs_mwh"),
                "state_fuel_mix": gen_summary.get("fuel_mix")
            }
        except Exception:
            pass

        # Inject weather summary for chat context
        ctx = cls._inject_weather_context(ctx)

        return ctx
