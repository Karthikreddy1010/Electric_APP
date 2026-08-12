"""
Central Unified Tool Registry for Grounded AI Assistant.
Organizes all internal, external, calculation, metadata, and RAG tools.
"""
import logging
from typing import Dict, Any, List, Optional
from langchain_core.tools import BaseTool

from ai.tools.metadata_tools import get_available_data_sources
from ai.tools.bill_tools import (
    get_bill_details,
    get_bill_components,
    get_bill_history,
    calculate_bill_total,
    calculate_component_change,
    explain_bill_component,
    compare_bill_periods,
)
from ai.tools.impact_tools import (
    calculate_bill_sensitivity,
    run_bill_simulation,
    calculate_component_impact,
    calculate_kwh_scenario,
)
from ai.tools.forecast_tools import (
    forecast_energy_usage,
    forecast_bill,
    retrieve_forecast_inputs,
)
from ai.tools.energy_data_tools import (
    get_state_electricity_price,
    get_county_electricity_statistics,
    get_utility_rate_data,
    get_energy_consumption_data,
    get_generation_data,
    get_demand_data,
)
from ai.tools.weather_tools import (
    get_historical_weather,
    get_current_weather,
    get_weather_normalization_data,
)
from ai.tools.external_api_tools import (
    eia_api_tool,
    noaa_api_tool,
    open_meteo_tool,
    pjm_api_tool,
    authoritative_web_search_tool,
)
from ai.tools.rag_tools import query_vector_store

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Central Manager registering all LangChain tools.
    """

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._register_all()

    def _register_all(self):
        all_tools = [
            # Metadata
            get_available_data_sources,
            # Bill Tools
            get_bill_details,
            get_bill_components,
            get_bill_history,
            calculate_bill_total,
            calculate_component_change,
            explain_bill_component,
            compare_bill_periods,
            # Impact Tools
            calculate_bill_sensitivity,
            run_bill_simulation,
            calculate_component_impact,
            calculate_kwh_scenario,
            # Forecast Tools
            forecast_energy_usage,
            forecast_bill,
            retrieve_forecast_inputs,
            # Energy Data Tools
            get_state_electricity_price,
            get_county_electricity_statistics,
            get_utility_rate_data,
            get_energy_consumption_data,
            get_generation_data,
            get_demand_data,
            # Weather Tools
            get_historical_weather,
            get_current_weather,
            get_weather_normalization_data,
            # Specialized External API Tools
            eia_api_tool,
            noaa_api_tool,
            open_meteo_tool,
            pjm_api_tool,
            authoritative_web_search_tool,
            # RAG Vector Store Tool
            query_vector_store,
        ]

        for t in all_tools:
            name = getattr(t, "name", None) or getattr(t, "__name__", str(t))
            self._tools[name] = t


    def get_tool(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[BaseTool]:
        return list(self._tools.values())

    def list_tool_names(self) -> List[str]:
        return list(self._tools.keys())

    def invoke_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Safely invokes a named tool with arguments, wrapping errors in a structured payload.
        """
        t = self.get_tool(name)
        if not t:
            return {
                "success": False,
                "tool_name": name,
                "error": f"Tool '{name}' is not registered in ToolRegistry.",
                "data": None
            }

        try:
            res = t.invoke(args)
            if isinstance(res, dict):
                return res
            return {
                "success": True,
                "tool_name": name,
                "data": res
            }
        except Exception as e:
            logger.error(f"Error executing tool '{name}' with args {args}: {e}")
            return {
                "success": False,
                "tool_name": name,
                "error": str(e),
                "data": None
            }


# Global singleton instance
tool_registry = ToolRegistry()
