"""
Data Requirement Router & Intent Classification.
Produces StructuredQueryRequirement and deterministically plans tool calls.
"""
import re
import logging
from typing import Dict, Any, List, Optional
from ai.schemas import StructuredQueryRequirement, GeographicScope

logger = logging.getLogger(__name__)

# List of US State postal codes for rule-based geographic extraction
US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY"
}

STATE_NAMES = {
    "CALIFORNIA": "CA", "TEXAS": "TX", "NEW JERSEY": "NJ", "NEW YORK": "NY",
    "FLORIDA": "FL", "PENNSYLVANIA": "PA", "MASSACHUSETTS": "MA", "WYOMING": "WY",
    "ILLINOIS": "IL", "OHIO": "OH", "GEORGIA": "GA", "NORTH CAROLINA": "NC"
}


class DataRequirementRouter:
    """
    Analyzes user questions to construct a typed StructuredQueryRequirement
    and determines exact tool pipeline steps.
    """

    @staticmethod
    def analyze_query(query: str, current_tab: Optional[str] = None) -> StructuredQueryRequirement:
        q_upper = query.upper()
        q_lower = query.lower()

        # 1. Geography Extraction
        detected_state = None
        scope = GeographicScope.CUSTOMER

        # Check state names
        for full_name, code in STATE_NAMES.items():
            if full_name in q_upper:
                detected_state = code
                scope = GeographicScope.STATE
                break

        # Check 2-letter codes with word boundaries
        if not detected_state:
            for st in US_STATES:
                if re.search(r'\b' + st + r'\b', q_upper):
                    detected_state = st
                    scope = GeographicScope.STATE
                    break

        if "NATIONAL" in q_upper or "US" in q_upper or "UNITED STATES" in q_upper:
            scope = GeographicScope.NATIONAL

        # 2. Temporal Extraction (Years)
        year_match = re.search(r'\b(202[0-9])\b', query)
        detected_year = int(year_match.group(1)) if year_match else 2024

        # 3. Intent Detection
        intent = "general_energy"
        # Detect state-level average bill/price queries first (these are NOT customer bill lookups)
        is_state_level_query = scope == GeographicScope.STATE and detected_state and detected_state != "NJ"
        has_average_or_state_bill = any(w in q_lower for w in ["average bill", "average residential", "state average", "average electricity"])

        if has_average_or_state_bill or (is_state_level_query and "bill" in q_lower):
            intent = "price_query"
        elif any(w in q_lower for w in ["my bill", "last bill", "bill details", "my usage", "this month"]):
            intent = "bill_lookup"
        elif any(w in q_lower for w in ["why was my bill", "why higher", "bill increase", "component", "breakdown"]):
            intent = "bill_explanation"
        elif any(w in q_lower for w in ["compare", "vs", "versus", "cheaper", "more expensive"]):
            intent = "comparison"
        elif any(w in q_lower for w in ["price", "cents", "kwh rate", "average price", "electricity cost"]):
            intent = "price_query"
        elif any(w in q_lower for w in ["forecast", "project", "next month", "future"]):
            intent = "forecast_query"
        elif any(w in q_lower for w in ["reduce", "if i use", "scenario", "solar", "battery", "kwh to"]):
            intent = "simulation_query"
        elif any(w in q_lower for w in ["weather", "temperature", "cdd", "hdd", "cold", "hot"]):
            intent = "weather_query"
        elif any(w in q_lower for w in ["sbc", "bgs", "rggi", "rider", "tariff", "charge mean"]):
            intent = "tariff_query"
        elif any(w in q_lower for w in ["data sources", "datasets", "catalog", "what data"]):
            intent = "dataset_metadata"

        # 4. Calculation & External Flags
        is_calc = intent in ["simulation_query", "bill_explanation", "comparison"] or any(char in query for char in ["+", "-", "*", "%"]) or "reduce" in q_lower
        is_ext = scope in [GeographicScope.STATE, GeographicScope.NATIONAL] and detected_state != "NJ"

        return StructuredQueryRequirement(
            intent=intent,
            geography_scope=scope,
            state_code=detected_state,
            year=detected_year,
            required_metrics=["price_cents_per_kwh", "usage_kwh", "total_bill"],
            is_calculation_required=is_calc,
            is_external_retrieval_required=is_ext
        )

    @staticmethod
    def plan_tool_calls(req: StructuredQueryRequirement, query: str) -> List[Dict[str, Any]]:
        """
        Plans exact sequence of tool calls based on StructuredQueryRequirement.
        """
        tools_to_run = []
        intent = req.intent
        st = req.state_code or "NJ"

        if intent == "dataset_metadata":
            tools_to_run.append({"tool_name": "get_available_data_sources", "args": {}})
            return tools_to_run

        if intent == "bill_lookup":
            tools_to_run.append({"tool_name": "get_bill_details", "args": {}})
            tools_to_run.append({"tool_name": "get_bill_components", "args": {}})

        elif intent == "bill_explanation":
            tools_to_run.append({"tool_name": "get_bill_details", "args": {}})
            tools_to_run.append({"tool_name": "get_bill_components", "args": {}})
            tools_to_run.append({"tool_name": "get_bill_history", "args": {}})
            tools_to_run.append({"tool_name": "calculate_component_change", "args": {}})
            tools_to_run.append({"tool_name": "get_historical_weather", "args": {"period": "2026-06"}})

        elif intent == "comparison":
            tools_to_run.append({"tool_name": "get_bill_details", "args": {}})
            # Check states mentioned
            tools_to_run.append({"tool_name": "get_state_electricity_price", "args": {"state": st, "year": req.year}})
            if "TEXAS" in query.upper() or "TX" in query.upper():
                tools_to_run.append({"tool_name": "get_state_electricity_price", "args": {"state": "TX", "year": req.year}})
            if "CALIFORNIA" in query.upper() or "CA" in query.upper():
                tools_to_run.append({"tool_name": "get_state_electricity_price", "args": {"state": "CA", "year": req.year}})

        elif intent == "price_query":
            tools_to_run.append({"tool_name": "get_state_electricity_price", "args": {"state": st, "year": req.year}})
            tools_to_run.append({"tool_name": "eia_api_tool", "args": {"state": st, "year": req.year}})

        elif intent == "simulation_query":

            # Check for kWh adjustment pattern like "900 kWh to 700 kWh"
            nums = [float(x) for x in re.findall(r'\b\d+\b', query)]
            if len(nums) >= 2 and "kwh" in query.lower():
                tools_to_run.append({
                    "tool_name": "calculate_kwh_scenario",
                    "args": {"baseline_kwh": max(nums[0], nums[1]), "target_kwh": min(nums[0], nums[1]), "rate_per_kwh": 0.185}
                })
            else:
                tools_to_run.append({"tool_name": "run_bill_simulation", "args": {"scenario_type": "solar_pv", "capacity_kw": 5.0}})

        elif intent == "forecast_query":
            tools_to_run.append({"tool_name": "forecast_energy_usage", "args": {"months_ahead": 3}})
            tools_to_run.append({"tool_name": "forecast_bill", "args": {"months_ahead": 3}})

        elif intent == "tariff_query":
            tools_to_run.append({"tool_name": "explain_bill_component", "args": {"component_name": query}})
            tools_to_run.append({"tool_name": "query_vector_store", "args": {"query": query}})

        elif intent == "weather_query":
            tools_to_run.append({"tool_name": "get_historical_weather", "args": {"period": "2026-06"}})
            tools_to_run.append({"tool_name": "get_weather_normalization_data", "args": {"period": "2026-06"}})

        else:
            # General energy fallback — only include customer bill data for NJ/local scope
            if req.geography_scope == GeographicScope.CUSTOMER or (req.state_code or "NJ") == "NJ":
                tools_to_run.append({"tool_name": "get_bill_details", "args": {}})
            tools_to_run.append({"tool_name": "get_state_electricity_price", "args": {"state": st, "year": req.year}})

        return tools_to_run
