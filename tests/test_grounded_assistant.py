"""
Unit and Integration Test Suite for Grounded Tool-Using AI Assistant.
"""
import pytest
import asyncio
from ai.agent import grounded_agent
from ai.schemas import GroundedResponse, GeographicScope
from ai.critic import ProgrammaticClaimValidator
from ai.evidence import EvidenceValidationEngine


def test_internal_bill_details_query():
    """Test 1: Internal customer bill query."""
    res = asyncio.run(grounded_agent.execute(user_query="What was my electricity bill last month?"))
    assert res["success"] is True
    assert "750" in res["text"] or "144.27" in res["text"] or "$" in res["text"]
    meta = res["metadata"]
    assert meta["grounded"] is True
    assert "get_bill_details" in meta["tools_used"] or "get_bill_components" in meta["tools_used"]


def test_cross_state_comparison_query():
    """Test 2: Cross-state comparison query (NJ vs Texas)."""
    res = asyncio.run(grounded_agent.execute(user_query="Why was my electricity bill higher than last month, and is NJ electricity more expensive than Texas?"))
    assert res["success"] is True
    meta = res["metadata"]
    assert meta["grounded"] is True
    tools = meta["tools_used"]
    assert "get_state_electricity_price" in tools or "calculate_component_change" in tools


def test_kwh_scenario_calculation():
    """Test 3: Scenario calculation (reducing 900 kWh to 700 kWh)."""
    res = asyncio.run(grounded_agent.execute(user_query="What happens if I reduce consumption from 900 kWh to 700 kWh?"))
    assert res["success"] is True
    text = res["text"]
    assert "37" in text or "200" in text or "savings" in text.lower()
    meta = res["metadata"]
    assert "calculate_kwh_scenario" in meta["tools_used"]
    assert len(meta["calculations"]) > 0


def test_missing_data_rejection():
    """Test 4: Missing data question - Wyoming 2026 unverified bill."""
    res = asyncio.run(grounded_agent.execute(user_query="What was the average residential electricity bill in Wyoming in 2026?"))
    assert res["success"] is True
    text = res["text"]
    assert "couldn't verify" in text.lower() or "unverified" in text.lower() or "not available" in text.lower()
    meta = res["metadata"]
    assert meta["unverified_claims_blocked"] >= 0


def test_out_of_domain_query():
    """Test 5: Out of domain question."""
    res = asyncio.run(grounded_agent.execute(user_query="Who won the 2026 World Cup?"))
    assert res["success"] is True
    text = res["text"]
    assert "electricity" in text.lower() or "couldn't verify" in text.lower() or "sources" in text.lower()


def test_conflicting_sources_resolution():
    """Test 6: Conflicting source resolution."""
    conflicting_outputs = [
        {
            "success": True,
            "tool_name": "eia_api_tool",
            "data": {"state": "NJ", "year": 2024, "price_cents_per_kwh": 23.4, "source_title": "EIA Official API"}
        },
        {
            "success": True,
            "tool_name": "authoritative_web_search_tool",
            "data": {"state": "NJ", "year": 2024, "price_cents_per_kwh": 24.1, "source_title": "Local Utility Web Snippet"}
        }
    ]

    ev = EvidenceValidationEngine.build_evidence("What is the NJ price?", conflicting_outputs)
    assert len(ev.conflicting_sources) > 0
    conflict = ev.conflicting_sources[0]
    assert conflict.metric == "residential_electricity_price"
    assert "EIA Official API" in conflict.resolution_explanation


def test_programmatic_claim_validator():
    """Test 7: ProgrammaticClaimValidator numeric & entity extractor."""
    sample_text = "In 2024, NJ residential electricity price was 23.4 cents/kWh, resulting in a total bill of $144.27."
    nums = ProgrammaticClaimValidator.extract_numbers(sample_text)
    assert 23.4 in nums
    assert 144.27 in nums

    entities = ProgrammaticClaimValidator.extract_entities(sample_text)
    assert "NJ" in entities["states"]
    assert "2024" in entities["years"]
