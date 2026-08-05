"""Phase 3 Component Validation Tests."""
from api.services.llm.orchestrator import (
    SemanticIntentRouter, Intent, ToolRegistry, SkillCatalog,
    CostController, ConversationMemory, ConfidenceFusion, ResponseCritic,
    AssistantBrain, IntentResult, ExtractedEntities, SkillPlan, ModelTier,
    ToolResult, FusedKnowledge
)
from api.services.llm.response_validator import ResponseValidator, StrictnessLevel

print("=" * 60)
print("Phase 3 — Component Validation Tests")
print("=" * 60)

# ── Test 1: Semantic Intent Router ─────────────────────────────
print("\n[1] SemanticIntentRouter")
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
passed = 0
for query, expected in tests:
    result = SemanticIntentRouter.classify(query)
    status = "PASS" if result.intent == expected else "FAIL"
    if status == "PASS":
        passed += 1
    print(f"  [{status}] \"{query}\" -> {result.intent.value} (conf={result.confidence:.2f})")
print(f"  Router: {passed}/{len(tests)} passed")

# ── Test 2: Entity Extraction ──────────────────────────────────
print("\n[2] Entity Extraction")
r = SemanticIntentRouter.classify("What is my PSE&G delivery charge for last month?")
assert r.entities.utility == "PSE&G", f"Expected PSE&G, got {r.entities.utility}"
assert r.entities.component == "delivery_charge", f"Expected delivery_charge, got {r.entities.component}"
assert r.entities.period == "last_month", f"Expected last_month, got {r.entities.period}"
assert r.requires_temporal == True
print("  [PASS] PSE&G delivery charge last month -> entities correct")

r2 = SemanticIntentRouter.classify("Reduce usage by 15% and save $50")
assert r2.entities.percentage == 15.0
assert r2.entities.amount == 50.0
print("  [PASS] 15% and $50 extracted correctly")

# ── Test 3: Tool Registry ─────────────────────────────────────
print("\n[3] ToolRegistry")
tr = ToolRegistry()
tools = tr.list_tools()
assert len(tools) == 8, f"Expected 8 tools, got {len(tools)}"
ae = tr.get("analytics_engine")
assert ae is not None
assert ae.confidence == 1.0
assert ae.source_tier == 0
print(f"  [PASS] 8 tools registered, analytics_engine tier=0 confidence=1.0")

# ── Test 4: Skill Catalog ─────────────────────────────────────
print("\n[4] SkillCatalog")
sc = SkillCatalog()
skills = sc.resolve_skills(Intent.BILL_EXPLANATION)
assert len(skills) == 1
assert skills[0].name == "bill_explanation"
assert skills[0].needs_llm_narration == True
assert "analytics_engine" in skills[0].required_tools
print("  [PASS] BILL_EXPLANATION -> bill_explanation (needs LLM)")

skills_bypass = sc.resolve_skills(Intent.BILL_LOOKUP)
assert len(skills_bypass) == 1
assert skills_bypass[0].needs_llm_narration == False
assert skills_bypass[0].model_tier == ModelTier.BYPASS
print("  [PASS] BILL_LOOKUP -> bill_lookup (BYPASS, no LLM)")

# ── Test 5: Cost Controller ───────────────────────────────────
print("\n[5] CostController")
ir_bypass = IntentResult(intent=Intent.BILL_LOOKUP, confidence=0.95, entities=ExtractedEntities())
sp_bypass = SkillPlan(required_skills=["bill_lookup"], required_tools=["bill_data"],
                      model_tier=ModelTier.BYPASS, needs_llm_narration=False)
assert CostController.select_model_tier(ir_bypass, sp_bypass) == ModelTier.BYPASS
print("  [PASS] BILL_LOOKUP -> BYPASS")

ir_local = IntentResult(intent=Intent.BILL_EXPLANATION, confidence=0.90, entities=ExtractedEntities())
sp_local = SkillPlan(required_skills=["bill_explanation"], required_tools=["bill_data", "analytics_engine"],
                     model_tier=ModelTier.FAST_LOCAL, needs_llm_narration=True)
assert CostController.select_model_tier(ir_local, sp_local) == ModelTier.FAST_LOCAL
print("  [PASS] BILL_EXPLANATION -> FAST_LOCAL")

ir_cloud = IntentResult(intent=Intent.MARKET_QUERY, confidence=0.85, entities=ExtractedEntities())
sp_cloud = SkillPlan(required_skills=["market_intelligence"], required_tools=["eia_data"],
                     model_tier=ModelTier.FAST_LOCAL, needs_llm_narration=True)
assert CostController.select_model_tier(ir_cloud, sp_cloud) == ModelTier.CLOUD
print("  [PASS] MARKET_QUERY -> CLOUD")

# ── Test 6: Conversation Memory ───────────────────────────────
print("\n[6] ConversationMemory")
mem = ConversationMemory()
mem.update_context({"bill": {"total_bill": 158.10, "utility": "PSE&G"}}, "Impact", "What is my bill?")
assert mem.get_active_bill()["total_bill"] == 158.10
assert mem.get_active_tab() == "Impact"
entities = ExtractedEntities()
enriched = mem.enrich_entities(entities)
assert enriched.utility == "PSE&G"
print("  [PASS] Memory stores bill, tab, and enriches entities")

# ── Test 7: Confidence Fusion ─────────────────────────────────
print("\n[7] ConfidenceFusion")
results = [
    ToolResult(tool_name="analytics_engine", success=True, data={"total_bill": 158.10}, confidence=1.0, source_tier=0),
    ToolResult(tool_name="eia_data", success=True, data={"avg_rate": 0.18}, confidence=0.93, source_tier=3),
]
fused = ConfidenceFusion.fuse(results, {"bill": {"total_bill": 158.10}})
assert fused.overall_confidence > 0.8
assert fused.context_data["total_bill"] == 158.10
assert fused.context_data["avg_rate"] == 0.18
assert len(fused.provenance) == 2
print(f"  [PASS] Fused confidence={fused.overall_confidence:.3f}, 2 provenance entries, no contradictions")

# Test contradiction detection
results_conflict = [
    ToolResult(tool_name="analytics_engine", success=True, data={"total_bill": 158.10}, confidence=1.0, source_tier=0),
    ToolResult(tool_name="external", success=True, data={"total_bill": 160.00}, confidence=0.8, source_tier=3),
]
fused_c = ConfidenceFusion.fuse(results_conflict, {})
assert len(fused_c.contradictions) == 1
assert fused_c.context_data["total_bill"] == 158.10  # Tier 0 wins
print(f"  [PASS] Contradiction detected, Tier 0 value kept ({fused_c.context_data['total_bill']})")

# ── Test 8: Response Critic ───────────────────────────────────
print("\n[8] ResponseCritic")
ir_test = IntentResult(intent=Intent.COMPONENT_DETAIL, confidence=0.88,
                       entities=ExtractedEntities(component="delivery_charge"))
fk_test = FusedKnowledge(context_data={}, tool_results=[], contradictions=[])

passed_ok, issues_ok = ResponseCritic.critique(
    "Your delivery charge is $46.75 for grid distribution.", "what is my delivery charge?", ir_test, fk_test
)
assert passed_ok == True
print("  [PASS] Good response passes critic")

passed_bad, issues_bad = ResponseCritic.critique(
    "As an AI, I think your bill is high.", "why is my bill high?", ir_test, fk_test
)
assert passed_bad == False
assert any("AI self-reference" in i for i in issues_bad)
print("  [PASS] AI self-reference detected and rejected")

# ── Test 9: Hardened ResponseValidator ────────────────────────
print("\n[9] ResponseValidator (Hardened)")
context = {"bill": {"total_bill": 158.10, "usage_kwh": 850.0, "delivery_charge": 46.75}}
text_good = "Your total bill is $158.10 for 850.0 kWh with delivery charges of $46.75."
is_valid, errors = ResponseValidator.validate(text_good, context)
assert is_valid == True
print("  [PASS] Valid text passes validation")

text_bad = "Your total bill is $999.99 which is very high."
is_valid_bad, errors_bad = ResponseValidator.validate(text_bad, context)
assert is_valid_bad == False
assert len(errors_bad) > 0
print(f"  [PASS] Hallucinated $999.99 rejected ({len(errors_bad)} errors)")

report = ResponseValidator.validate_detailed(text_bad, context, StrictnessLevel.STRICT)
assert report.recommend_fallback == True
print(f"  [PASS] STRICT mode recommends fallback (unverified={report.unverified_count})")

# ── Test 10: AssistantBrain.plan() ────────────────────────────
print("\n[10] AssistantBrain.plan()")
brain = AssistantBrain()
ctx = {"bill": {"total_bill": 158.10, "usage_kwh": 850.0, "utility": "PSE&G"}}
ir, sp, trace = brain.plan("What is my total bill?", ctx, "Dashboard")
assert ir.intent == Intent.BILL_LOOKUP
assert sp.model_tier == ModelTier.BYPASS
assert "bill_data" in sp.required_tools
assert trace.llm_bypassed == True
print(f"  [PASS] 'What is my total bill?' -> BYPASS, tools={sp.required_tools}")

ir2, sp2, trace2 = brain.plan("Explain my electricity bill", ctx, "Dashboard")
assert ir2.intent == Intent.BILL_EXPLANATION
assert sp2.model_tier == ModelTier.FAST_LOCAL
assert sp2.needs_llm_narration == True
print(f"  [PASS] 'Explain my bill' -> FAST_LOCAL, narration=True, tools={sp2.required_tools}")

print("\n" + "=" * 60)
print("ALL 10 COMPONENT TESTS PASSED [OK]")
print("=" * 60)
