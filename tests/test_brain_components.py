"""Phase 3 Component Validation Tests."""
import pytest
from api.services.llm.orchestrator import (
    SemanticIntentRouter, Intent, ToolRegistry, SkillCatalog,
    CostController, ConversationMemory, ConfidenceFusion, ResponseCritic,
    AssistantBrain, IntentResult, ExtractedEntities, SkillPlan, ModelTier,
    ToolResult, FusedKnowledge
)
from api.services.llm.response_validator import ResponseValidator, StrictnessLevel


def test_semantic_intent_router():
    tests = [
        ("What is my total bill?", Intent.BILL_LOOKUP),
        ("Explain my electricity bill in simple terms", Intent.BILL_EXPLANATION),
        ("What is the delivery charge?", Intent.COMPONENT_DETAIL),
        ("Compare my bill to last month", Intent.COMPARISON),
        ("What will my bill be next month?", Intent.FORECAST_QUERY),
        ("What if I reduce usage by 15%?", Intent.SIMULATION_QUERY),
        ("How can I save money on electricity?", Intent.SAVINGS_QUERY),
        ("Tell me a joke", Intent.OUT_OF_SCOPE),
        ("What is my PSE&G tariff rate schedule?", Intent.TARIFF_QUERY),
        ("How does my bill compare to the national average?", Intent.BENCHMARK_QUERY),
        ("How does weather affect my bill?", Intent.WEATHER_QUERY),
    ]
    for query, expected in tests:
        result = SemanticIntentRouter.classify(query)
        assert result.intent == expected


def test_entity_extraction():
    r = SemanticIntentRouter.classify("What is my PSE&G delivery charge for last month?")
    assert r.entities.utility == "PSE&G"
    assert r.entities.component == "delivery_charge"
    assert r.entities.period == "last_month"
    assert r.requires_temporal is True

    r2 = SemanticIntentRouter.classify("Reduce usage by 15% and save $50")
    assert r2.entities.percentage == 15.0
    assert r2.entities.amount == 50.0


def test_tool_registry():
    tr = ToolRegistry()
    tools = tr.list_tools()
    assert len(tools) >= 15
    ae = tr.get("analytics_engine")
    assert ae is not None
    assert ae.confidence == 1.0
    assert ae.source_tier == 0


def test_skill_catalog():
    sc = SkillCatalog()
    skills = sc.resolve_skills(Intent.BILL_EXPLANATION)
    assert len(skills) == 1
    assert skills[0].name == "bill_explanation"
    assert skills[0].needs_llm_narration is True
    assert "analytics_engine" in skills[0].required_tools

    skills_lookup = sc.resolve_skills(Intent.BILL_LOOKUP)
    assert len(skills_lookup) == 1
    assert skills_lookup[0].needs_llm_narration is True
    assert skills_lookup[0].model_tier == ModelTier.FAST_LOCAL


def test_cost_controller():
    ir_lookup = IntentResult(intent=Intent.BILL_LOOKUP, confidence=0.95, entities=ExtractedEntities())
    sp_lookup = SkillPlan(required_skills=["bill_lookup"], required_tools=["bill_data", "analytics_engine"],
                          model_tier=ModelTier.FAST_LOCAL, needs_llm_narration=True)
    assert CostController.select_model_tier(ir_lookup, sp_lookup) == ModelTier.FAST_LOCAL

    ir_local = IntentResult(intent=Intent.BILL_EXPLANATION, confidence=0.90, entities=ExtractedEntities())
    sp_local = SkillPlan(required_skills=["bill_explanation"], required_tools=["bill_data", "analytics_engine"],
                         model_tier=ModelTier.FAST_LOCAL, needs_llm_narration=True)
    assert CostController.select_model_tier(ir_local, sp_local) == ModelTier.FAST_LOCAL

    ir_cloud = IntentResult(intent=Intent.MARKET_QUERY, confidence=0.85, entities=ExtractedEntities())
    sp_cloud = SkillPlan(required_skills=["market_intelligence"], required_tools=["eia_data"],
                         model_tier=ModelTier.FAST_LOCAL, needs_llm_narration=True)
    assert CostController.select_model_tier(ir_cloud, sp_cloud) == ModelTier.CLOUD


def test_conversation_memory():
    mem = ConversationMemory()
    mem.update_context({"bill": {"total_bill": 158.10, "utility": "PSE&G"}}, "Impact", "What is my bill?")
    assert mem.get_active_bill()["total_bill"] == 158.10
    assert mem.get_active_tab() == "Impact"
    entities = ExtractedEntities()
    enriched = mem.enrich_entities(entities)
    assert enriched.utility == "PSE&G"


def test_confidence_fusion():
    results = [
        ToolResult(tool_name="analytics_engine", success=True, data={"total_bill": 158.10}, confidence=1.0, source_tier=0),
        ToolResult(tool_name="eia_data", success=True, data={"avg_rate": 0.18}, confidence=0.93, source_tier=3),
    ]
    fused = ConfidenceFusion.fuse(results, {"bill": {"total_bill": 158.10}})
    assert fused.overall_confidence > 0.8
    assert fused.context_data["total_bill"] == 158.10
    assert fused.context_data["avg_rate"] == 0.18
    assert len(fused.provenance) == 2

    # Test contradiction detection
    results_conflict = [
        ToolResult(tool_name="analytics_engine", success=True, data={"total_bill": 158.10}, confidence=1.0, source_tier=0),
        ToolResult(tool_name="external", success=True, data={"total_bill": 160.00}, confidence=0.8, source_tier=3),
    ]
    fused_c = ConfidenceFusion.fuse(results_conflict, {})
    assert len(fused_c.contradictions) == 1
    assert fused_c.context_data["total_bill"] == 158.10  # Tier 0 wins


def test_response_critic():
    ir_test = IntentResult(intent=Intent.COMPONENT_DETAIL, confidence=0.88,
                           entities=ExtractedEntities(component="delivery_charge"))
    fk_test = FusedKnowledge(context_data={}, tool_results=[], contradictions=[])

    passed_ok, issues_ok = ResponseCritic.critique(
        "Your delivery charge is $46.75 for grid distribution.", "what is my delivery charge?", ir_test, fk_test
    )
    assert passed_ok is True

    passed_bad, issues_bad = ResponseCritic.critique(
        "As an AI, I think your bill is high.", "why is my bill high?", ir_test, fk_test
    )
    assert passed_bad is False
    assert any("AI self-reference" in i for i in issues_bad)


def test_response_validator_hardened():
    context = {"bill": {"total_bill": 158.10, "usage_kwh": 850.0, "delivery_charge": 46.75}}
    text_good = "Your total bill is $158.10 for 850.0 kWh with delivery charges of $46.75."
    is_valid, errors = ResponseValidator.validate(text_good, context)
    assert is_valid is True

    text_bad = "Your total bill is $999.99 which is very high."
    is_valid_bad, errors_bad = ResponseValidator.validate(text_bad, context)
    assert is_valid_bad is False
    assert len(errors_bad) > 0

    report = ResponseValidator.validate_detailed(text_bad, context, StrictnessLevel.STRICT)
    assert report.recommend_fallback is True


def test_assistant_brain_plan():
    brain = AssistantBrain()
    ctx = {"bill": {"total_bill": 158.10, "usage_kwh": 850.0, "utility": "PSE&G"}}
    ir, sp, trace = brain.plan("What is my total bill?", ctx, "Dashboard")
    assert ir.intent == Intent.BILL_LOOKUP
    assert sp.model_tier == ModelTier.FAST_LOCAL
    assert "bill_data" in sp.required_tools
    assert trace.llm_bypassed is False

    ir2, sp2, trace2 = brain.plan("Explain my electricity bill", ctx, "Dashboard")
    assert ir2.intent == Intent.BILL_EXPLANATION
    assert sp2.model_tier == ModelTier.FAST_LOCAL
    assert sp2.needs_llm_narration is True

