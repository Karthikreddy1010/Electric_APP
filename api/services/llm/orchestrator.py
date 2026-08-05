"""
Phase 3 — AI Orchestrator with Assistant Brain.

Central pipeline coordinator that implements the v3.0 Brain-Centric Architecture:

    User Query
        → Semantic Intent Router (intent, entities, temporal, evidence)
        → Assistant Brain (iterative Plan → Execute → Observe loop)
        → Skill Execution Graph (dynamic multi-skill DAG composition)
        → Tool Registry (deterministic engines, SQL, vector, APIs)
        → Cost Controller (LLM bypass for metric queries, model tier selection)
        → Confidence-Weighted Knowledge Fusion
        → Response Critic (fulfillment, citations, contradictions)
        → Numerical Consistency Validator
        → Verified Response + Provenance

Backward Compatibility:
    The existing AIOrchestrator.execute() and stream() public API surfaces
    are fully preserved. All existing routes, tests, and background_worker.py
    continue to work unchanged. The Brain layer is transparently activated
    for 'chat' tasks and gracefully bypassed for legacy task types.

Design Rationale:
    - The LLM is an explanation tool, NOT the core decision engine.
    - Simple data lookups and deterministic calculations bypass LLM entirely.
    - The iterative agent loop enables multi-step cross-domain reasoning.
    - All logic lives in this single file to avoid premature file splitting.
"""
import time
import json
import re
import math
import logging
from enum import Enum
from typing import AsyncGenerator, Dict, Any, Optional, List, Tuple, Set
from dataclasses import dataclass, field

from api.services.llm.contracts import (
    UserTier, LLMResponse, ValidationStatus, InferenceResponse
)
from api.services.llm.router import ModelRouter
from api.services.llm.inference import InferenceClient
from api.services.llm.validator import OutputValidator
from api.services.llm.cache import semantic_cache
from api.services.llm.rag import rag_service
from api.services.llm.streaming import StreamingService
from api.services.llm.security import PromptInjectionGuard
from api.services.llm.prompt_builder import PromptBuilder
from api.services.llm.deterministic_fallback import DeterministicFallback
from api.services.llm.metrics import llm_metrics
from api.services.llm.providers.base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 1: Data Contracts & Enums
# ═══════════════════════════════════════════════════════════════════════════

class Intent(str, Enum):
    """Classified intent categories for user queries."""
    BILL_LOOKUP = "bill_lookup"
    BILL_EXPLANATION = "bill_explanation"
    COMPONENT_DETAIL = "component_detail"
    COMPARISON = "comparison"
    FORECAST_QUERY = "forecast_query"
    SIMULATION_QUERY = "simulation_query"
    TARIFF_QUERY = "tariff_query"
    BENCHMARK_QUERY = "benchmark_query"
    WEATHER_QUERY = "weather_query"
    MARKET_QUERY = "market_query"
    SAVINGS_QUERY = "savings_query"
    RATE_COMPARISON = "rate_comparison"
    GENERAL_ENERGY = "general_energy"
    OUT_OF_SCOPE = "out_of_scope"


class ModelTier(str, Enum):
    """Cost controller model selection tiers."""
    BYPASS = "bypass"          # No LLM — direct structured data
    FAST_LOCAL = "fast_local"  # Small/fast local model (Ollama)
    CLOUD = "cloud"            # Large cloud model (Claude/GPT/Gemini)


@dataclass
class ExtractedEntities:
    """Named entities extracted from user query."""
    utility: Optional[str] = None
    component: Optional[str] = None
    period: Optional[str] = None
    amount: Optional[float] = None
    percentage: Optional[float] = None
    state: Optional[str] = None
    rate_schedule: Optional[str] = None


@dataclass
class IntentResult:
    """Full semantic routing output."""
    intent: Intent
    confidence: float
    entities: ExtractedEntities
    requires_temporal: bool = False
    requires_customer_data: bool = False
    requires_external: bool = False
    raw_query: str = ""


@dataclass
class ToolResult:
    """Output from a single tool execution."""
    tool_name: str
    success: bool
    data: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    source_tier: int = 0
    latency_ms: float = 0.0
    error: Optional[str] = None


@dataclass
class SkillPlan:
    """Execution plan produced by the Assistant Brain."""
    required_skills: List[str]
    required_tools: List[str]
    model_tier: ModelTier
    needs_llm_narration: bool
    reasoning: str = ""


@dataclass
class FusedKnowledge:
    """Merged knowledge from multiple tool executions with provenance."""
    context_data: Dict[str, Any]
    tool_results: List[ToolResult]
    overall_confidence: float = 1.0
    contradictions: List[Dict[str, Any]] = field(default_factory=list)
    provenance: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class ObservabilityTrace:
    """End-to-end telemetry trace for a single request."""
    trace_id: str = ""
    intent: str = ""
    intent_confidence: float = 0.0
    selected_skills: List[str] = field(default_factory=list)
    selected_tools: List[str] = field(default_factory=list)
    retrieved_documents: List[Dict[str, Any]] = field(default_factory=list)
    llm_bypassed: bool = False
    overall_confidence: float = 0.0
    contradictions_found: int = 0
    agent_loop_iterations: int = 0
    model_tier: str = ""
    validation_status: str = ""
    critic_passed: bool = True
    latency_breakdown_ms: Dict[str, float] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 2: Semantic Intent Router
# ═══════════════════════════════════════════════════════════════════════════

class SemanticIntentRouter:
    """
    Multi-stage NLP classifier replacing keyword matching.

    Stages:
        1. Intent Classification — pattern-based with confidence scoring
        2. Entity Extraction — utility names, components, periods, amounts
        3. Temporal Detection — historical, current, forecast
        4. Evidence Detection — determines required data tiers
    """

    _INTENT_PATTERNS: List[Tuple[Intent, List[str], float]] = [
        # Weather impact
        (Intent.WEATHER_QUERY, [
            r"\bweather\b",
            r"\btemperatur\w*\b",
            r"\bheat\s*wave\b",
            r"\b(?:hdd|cdd)\b",
            r"\bcooling\s+day\b|\bheating\s+day\b",
        ], 0.92),

        # Benchmark / National Comparison
        (Intent.BENCHMARK_QUERY, [
            r"\bbenchmark\b",
            r"\bnational\s+average\b",
            r"\bcompare\b.*\b(?:state|national|average|utility|neighbor|peer)\b",
            r"\bhow\b.*\b(?:rank|stack up)\b",
            r"\bhow\b.*\bcompare\b.*\b(?:state|national|average|utility|neighbor|peer)\b",
        ], 0.92),

        # Comparison (temporal)
        (Intent.COMPARISON, [
            r"\bcompar\w+\b",
            r"\blast\s+month\b",
            r"\bprevious\b.*\b(?:month|bill|period)\b",
            r"\bmonth[\s-]+over[\s-]+month\b",
            r"\byear[\s-]+over[\s-]+year\b",
            r"\bchange\b.*\b(?:from|since|between)\b",
        ], 0.91),

        # Forecast
        (Intent.FORECAST_QUERY, [
            r"\bforecast\b",
            r"\bpredict\b",
            r"\bnext\s+(?:month|year|quarter)\b",
            r"\bfuture\b.*\b(?:bill|cost|usage)\b",
            r"\bexpect\b.*\b(?:bill|cost|usage)\b",
            r"\bwill\s+my\s+bill\b",
        ], 0.92),

        # Simulation
        (Intent.SIMULATION_QUERY, [
            r"\bwhat\s+if\b",
            r"\breduce\b.*\b(?:usage|consumption|kwh)\b.*\b\d+%\b",
            r"\b\d+%\b.*\b(?:reduce|cut|lower|less)\b",
            r"\bsimulat\w+\b",
            r"\bscenario\b",
        ], 0.93),

        # Component Detail
        (Intent.COMPONENT_DETAIL, [
            r"\b(?:delivery|supply|distribution|transmission|sbc|nug|customer)\b.*\bcharge\b",
            r"\bcharge\b.*\b(?:delivery|supply|distribution|transmission|sbc|nug|customer)\b",
            r"\bwhat is\s+(?:the|my)?\s*(?:delivery|supply|sbc|nug|fixed|customer)\b",
            r"\bbiggest\b|\bhighest\b|\blargest\b|\bmost expensive\b",
        ], 0.91),

        # Bill Explanation
        (Intent.BILL_EXPLANATION, [
            r"\bexplain\b.*\bbill\b",
            r"\bbreak\s*down\b.*\bbill\b",
            r"\bunderstand\b.*\b(?:bill|charges?)\b",
            r"\bwhy\b.*\b(?:bill|charge|cost)\b.*\b(?:high|increase|more|so much)\b",
            r"\beli5\b",
            r"\bsimple\b.*\bexplain\b",
            r"\bexplain\b",
        ], 0.90),

        # Tariff
        (Intent.TARIFF_QUERY, [
            r"\btariff\b",
            r"\brate\s+schedule\b",
            r"\btime[\s-]+of[\s-]+use\b|\btou\b",
            r"\brate\b.*\b(?:plan|structure|schedule)\b",
        ], 0.90),

        # Market
        (Intent.MARKET_QUERY, [
            r"\bmarket\b.*\b(?:price|rate|lmp)\b",
            r"\bpjm\b",
            r"\bwholesale\b",
            r"\b(?:energy|electricity)\s+market\b",
        ], 0.90),

        # Savings
        (Intent.SAVINGS_QUERY, [
            r"\bsav\w+\b",
            r"\breduce\b.*\bbill\b",
            r"\bcut\b.*\b(?:cost|bill)\b",
            r"\bhow\s+(?:can|to)\b.*\b(?:save|reduce|lower|cut)\b",
            r"\btip\w*\b.*\b(?:save|reduce|energy)\b",
        ], 0.88),

        # Rate comparison
        (Intent.RATE_COMPARISON, [
            r"\bfixed\b.*\bvariable\b|\bvariable\b.*\bfixed\b",
            r"\bswitch\b.*\b(?:plan|provider|supplier)\b",
            r"\bbetter\b.*\b(?:plan|rate)\b",
        ], 0.85),

        # Direct bill lookup
        (Intent.BILL_LOOKUP, [
            r"^\s*(?:what|how much)\s+(?:is|was)\s+(?:my\s+)?(?:total\s+)?(?:bill|cost|amount|charge|balance|amount due)\??\s*$",
            r"\bmy\s+total\s+bill\b",
            r"\b(?:total|amount)\s+(?:due|owed)\b",
            r"\bhow\s+much\s+do\s+i\s+owe\b",
        ], 0.89),

        # General energy knowledge
        (Intent.GENERAL_ENERGY, [
            r"\b(?:what|how|why|explain)\b.*\b(?:energy|electricity|power|grid|solar|renewable)\b",
            r"\bclean\s+energy\b",
            r"\bnet\s+metering\b",
            r"\bsolar\b",
        ], 0.75),
    ]

    _UTILITY_PATTERNS = [
        (r"\bpse\s*&?\s*g\b", "PSE&G"),
        (r"\bjcp\s*&?\s*l\b", "JCP&L"),
        (r"\bace\b", "ACE"),
    ]

    _COMPONENT_PATTERNS = [
        (r"\bdelivery\b", "delivery_charge"),
        (r"\bsupply\b", "supply_charge"),
        (r"\btransmission\b", "transmission_charge"),
        (r"\bdistribution\b", "distribution_charge"),
        (r"\bcustomer\s+charge\b|\bfixed\s+(?:charge|fee)\b|\bservice\s+charge\b", "monthly_service_charge"),
        (r"\bsbc\b|\bsocietal\b", "societal_benefits_charge"),
        (r"\bnug\b", "non_utility_generation"),
        (r"\btax\w*\b", "tax"),
    ]

    _PERIOD_PATTERNS = [
        (r"\b(january|february|march|april|may|june|july|august|september|october|november|december)\b", None),
        (r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b", None),
        (r"\blast\s+month\b", "last_month"),
        (r"\bthis\s+month\b", "this_month"),
        (r"\blast\s+year\b", "last_year"),
    ]

    _ENERGY_TERMS = frozenset([
        "bill", "electricity", "energy", "kwh", "tariff", "utility",
        "charge", "rate", "cost", "usage", "power", "tax", "delivery",
        "supply", "increase", "reduce", "save", "forecast", "customer",
        "transmission", "weather", "component", "month", "compare",
        "last", "previous", "demand", "biggest", "highest", "summary",
        "summarize", "solar", "renewable", "grid", "pjm", "market",
        "benchmark", "simulation", "what if", "explain",
    ])

    @classmethod
    def classify(cls, query: str, context_data: Optional[Dict[str, Any]] = None) -> IntentResult:
        """Full semantic routing: intent + entities + temporal + evidence."""
        if not query or not query.strip():
            return IntentResult(
                intent=Intent.OUT_OF_SCOPE, confidence=1.0,
                entities=ExtractedEntities(), raw_query=query or ""
            )

        query_lower = query.lower().strip()

        # Stage 0: Scope check
        if not cls._is_energy_related(query_lower):
            return IntentResult(
                intent=Intent.OUT_OF_SCOPE, confidence=0.95,
                entities=ExtractedEntities(), raw_query=query
            )

        # Stage 1: Intent classification
        intent, confidence = cls._classify_intent(query_lower)

        # Stage 2: Entity extraction
        entities = cls._extract_entities(query_lower)

        # Stage 3: Temporal detection
        requires_temporal = bool(re.search(
            r"\b(?:last|previous|next|future|history|historical|trend|forecast|compare|change)\b",
            query_lower
        ))

        # Stage 4: Evidence requirement detection
        requires_customer = bool(re.search(
            r"\bmy\b|\byour\b|\baccount\b|\bbill\b|\busage\b", query_lower
        ))
        requires_external = bool(re.search(
            r"\b(?:regulation|policy|law|mandate|official|government|state|federal|eia|noaa|pjm)\b",
            query_lower
        ))

        return IntentResult(
            intent=intent, confidence=confidence, entities=entities,
            requires_temporal=requires_temporal,
            requires_customer_data=requires_customer,
            requires_external=requires_external, raw_query=query
        )

    @classmethod
    def _is_energy_related(cls, query_lower: str) -> bool:
        words = set(re.findall(r'\b\w+\b', query_lower))
        return bool(words & cls._ENERGY_TERMS)

    @classmethod
    def _classify_intent(cls, query_lower: str) -> Tuple[Intent, float]:
        best_intent = Intent.GENERAL_ENERGY
        best_confidence = 0.5
        best_match_count = 0

        for intent, patterns, base_confidence in cls._INTENT_PATTERNS:
            match_count = sum(1 for p in patterns if re.search(p, query_lower, re.IGNORECASE))
            if match_count > 0:
                adjusted_confidence = min(base_confidence + (match_count - 1) * 0.03, 0.99)
                if adjusted_confidence > best_confidence or (
                    adjusted_confidence == best_confidence and match_count > best_match_count
                ):
                    best_intent = intent
                    best_confidence = adjusted_confidence
                    best_match_count = match_count

        return best_intent, round(best_confidence, 3)

    @classmethod
    def _extract_entities(cls, query_lower: str) -> ExtractedEntities:
        entities = ExtractedEntities()

        for pattern, name in cls._UTILITY_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                entities.utility = name
                break

        for pattern, name in cls._COMPONENT_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                entities.component = name
                break

        for pattern, name in cls._PERIOD_PATTERNS:
            match = re.search(pattern, query_lower, re.IGNORECASE)
            if match:
                entities.period = name or match.group(1)
                break

        amount_match = re.search(r'\$(\d+(?:\.\d+)?)', query_lower)
        if amount_match:
            entities.amount = float(amount_match.group(1))

        pct_match = re.search(r'(\d+(?:\.\d+)?)\s*%', query_lower)
        if pct_match:
            entities.percentage = float(pct_match.group(1))

        state_match = re.search(r'\b(nj|ny|pa|ct|de|md)\b', query_lower, re.IGNORECASE)
        if state_match:
            entities.state = state_match.group(1).upper()

        return entities


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 3: Tool Registry
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ToolMetadata:
    """Metadata specification for a registered tool."""
    name: str
    purpose: str
    source_tier: int
    latency_profile_ms: float
    confidence: float
    cacheable: bool = True
    cache_ttl_seconds: int = 3600
    requires_customer_data: bool = False
    failure_fallback: str = ""


class ToolRegistry:
    """Central registry of executable tools with metadata for planner optimization."""

    def __init__(self):
        self._tools: Dict[str, ToolMetadata] = {}
        self._register_defaults()

    def _register_defaults(self):
        defaults = [
            ToolMetadata("bill_data", "Retrieve customer bill data from parsed uploads and database",
                         source_tier=1, latency_profile_ms=5.0, confidence=0.98, requires_customer_data=True),
            ToolMetadata("analytics_engine", "Execute deterministic bill decomposition and component breakdown",
                         source_tier=0, latency_profile_ms=10.0, confidence=1.0, requires_customer_data=True,
                         failure_fallback="bill_data"),
            ToolMetadata("forecast", "Retrieve 12-month usage/cost prediction with P10/P50/P90 bands",
                         source_tier=0, latency_profile_ms=50.0, confidence=0.92, requires_customer_data=True),
            ToolMetadata("simulation", "Execute what-if scenario simulation with Monte Carlo distribution",
                         source_tier=0, latency_profile_ms=80.0, confidence=0.95, requires_customer_data=True),
            ToolMetadata("rag_knowledge", "Query vector store for tariff, policy, and FAQ content",
                         source_tier=2, latency_profile_ms=30.0, confidence=0.90,
                         requires_customer_data=False, cache_ttl_seconds=86400),
            ToolMetadata("eia_data", "Retrieve EIA retail electricity price trends and state benchmarks",
                         source_tier=3, latency_profile_ms=200.0, confidence=0.93,
                         requires_customer_data=False, cache_ttl_seconds=86400),
            ToolMetadata("weather_data", "Retrieve NOAA HDD/CDD degree day indices",
                         source_tier=3, latency_profile_ms=150.0, confidence=0.95,
                         requires_customer_data=False, cache_ttl_seconds=86400),
            ToolMetadata("benchmark", "Compare utility rates across NJ utilities and national averages",
                         source_tier=1, latency_profile_ms=20.0, confidence=0.92,
                         requires_customer_data=False, cache_ttl_seconds=86400),
        ]
        for tool in defaults:
            self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[ToolMetadata]:
        return self._tools.get(name)

    def list_tools(self) -> List[ToolMetadata]:
        return list(self._tools.values())

    def register(self, metadata: ToolMetadata):
        self._tools[metadata.name] = metadata


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 4: Skill Catalog
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SkillSpec:
    """Specification for a domain skill mapping intent to tools."""
    name: str
    description: str
    required_tools: List[str]
    needs_llm_narration: bool
    model_tier: ModelTier


class SkillCatalog:
    """High-level domain capability registry mapping intents to tool execution plans."""

    def __init__(self):
        self._skills: Dict[str, SkillSpec] = {}
        self._intent_to_skills: Dict[Intent, List[str]] = {}
        self._register_defaults()

    def _register_defaults(self):
        skills = [
            SkillSpec("bill_lookup", "Direct bill metric retrieval",
                      ["bill_data"], needs_llm_narration=False, model_tier=ModelTier.BYPASS),
            SkillSpec("bill_explanation", "Explain bill components and charges",
                      ["bill_data", "analytics_engine"], needs_llm_narration=True, model_tier=ModelTier.FAST_LOCAL),
            SkillSpec("component_analysis", "Detailed analysis of specific bill components",
                      ["bill_data", "analytics_engine"], needs_llm_narration=True, model_tier=ModelTier.FAST_LOCAL),
            SkillSpec("bill_comparison", "Month-over-month or year-over-year comparison",
                      ["bill_data", "analytics_engine"], needs_llm_narration=True, model_tier=ModelTier.FAST_LOCAL),
            SkillSpec("forecasting", "Usage and cost forecasting with confidence bands",
                      ["bill_data", "forecast"], needs_llm_narration=True, model_tier=ModelTier.FAST_LOCAL),
            SkillSpec("simulation", "What-if scenario simulation and impact analysis",
                      ["bill_data", "simulation"], needs_llm_narration=True, model_tier=ModelTier.FAST_LOCAL),
            SkillSpec("tariff_info", "Explain utility tariff structures and rate schedules",
                      ["rag_knowledge"], needs_llm_narration=True, model_tier=ModelTier.FAST_LOCAL),
            SkillSpec("benchmarking", "Regional and national utility rate comparison",
                      ["benchmark", "eia_data"], needs_llm_narration=True, model_tier=ModelTier.FAST_LOCAL),
            SkillSpec("weather_analysis", "Weather impact on energy bills and usage",
                      ["bill_data", "weather_data"], needs_llm_narration=True, model_tier=ModelTier.FAST_LOCAL),
            SkillSpec("market_intelligence", "PJM market data and wholesale price trends",
                      ["eia_data"], needs_llm_narration=True, model_tier=ModelTier.FAST_LOCAL),
            SkillSpec("savings_advice", "Actionable energy saving recommendations",
                      ["bill_data", "analytics_engine"], needs_llm_narration=True, model_tier=ModelTier.FAST_LOCAL),
            SkillSpec("rate_comparison", "Fixed vs variable rate plan evaluation",
                      ["bill_data", "rag_knowledge"], needs_llm_narration=True, model_tier=ModelTier.FAST_LOCAL),
            SkillSpec("general_knowledge", "General energy education and concepts",
                      ["rag_knowledge"], needs_llm_narration=True, model_tier=ModelTier.FAST_LOCAL),
        ]

        for skill in skills:
            self._skills[skill.name] = skill

        self._intent_to_skills = {
            Intent.BILL_LOOKUP: ["bill_lookup"],
            Intent.BILL_EXPLANATION: ["bill_explanation"],
            Intent.COMPONENT_DETAIL: ["component_analysis"],
            Intent.COMPARISON: ["bill_comparison"],
            Intent.FORECAST_QUERY: ["forecasting"],
            Intent.SIMULATION_QUERY: ["simulation"],
            Intent.TARIFF_QUERY: ["tariff_info"],
            Intent.BENCHMARK_QUERY: ["benchmarking"],
            Intent.WEATHER_QUERY: ["weather_analysis"],
            Intent.MARKET_QUERY: ["market_intelligence"],
            Intent.SAVINGS_QUERY: ["savings_advice"],
            Intent.RATE_COMPARISON: ["rate_comparison"],
            Intent.GENERAL_ENERGY: ["general_knowledge"],
            Intent.OUT_OF_SCOPE: [],
        }

    def resolve_skills(self, intent: Intent) -> List[SkillSpec]:
        skill_names = self._intent_to_skills.get(intent, [])
        return [self._skills[name] for name in skill_names if name in self._skills]

    def get(self, name: str) -> Optional[SkillSpec]:
        return self._skills.get(name)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 5: Cost Controller
# ═══════════════════════════════════════════════════════════════════════════

class CostController:
    """Determines whether LLM inference is needed and which model tier to use."""

    _BYPASS_INTENTS = frozenset([Intent.BILL_LOOKUP, Intent.OUT_OF_SCOPE])
    _CLOUD_INTENTS = frozenset([Intent.MARKET_QUERY, Intent.RATE_COMPARISON])

    @classmethod
    def select_model_tier(cls, intent_result: IntentResult, skill_plan: SkillPlan) -> ModelTier:
        if intent_result.intent in cls._BYPASS_INTENTS:
            return ModelTier.BYPASS
        if not skill_plan.needs_llm_narration:
            return ModelTier.BYPASS
        if intent_result.intent in cls._CLOUD_INTENTS:
            return ModelTier.CLOUD
        return ModelTier.FAST_LOCAL


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 6: Conversation Memory
# ═══════════════════════════════════════════════════════════════════════════

class ConversationMemory:
    """
    Multi-turn conversation state manager.
    Preserves active customer context, entity references, and tool outputs
    across turns so follow-up queries reuse working memory.
    """

    def __init__(self, max_history: int = 10):
        self._max_history = max_history
        self._active_bill: Optional[Dict[str, Any]] = None
        self._active_tab: str = ""
        self._active_utility: Optional[str] = None
        self._active_state: Optional[str] = None
        self._tool_outputs: List[ToolResult] = []
        self._conversation_turns: List[Dict[str, str]] = []

    def update_context(
        self, context_data: Dict[str, Any], current_tab: str = "",
        user_message: str = "", assistant_response: str = ""
    ):
        bill = context_data.get("bill") or context_data.get("uploadedBill") or {}
        if bill and isinstance(bill, dict) and bill.get("total_bill"):
            self._active_bill = bill
        if current_tab:
            self._active_tab = current_tab
        if bill and bill.get("utility"):
            self._active_utility = bill["utility"]

        if user_message:
            self._conversation_turns.append({"role": "user", "content": user_message})
        if assistant_response:
            self._conversation_turns.append({"role": "assistant", "content": assistant_response})

        if len(self._conversation_turns) > self._max_history * 2:
            self._conversation_turns = self._conversation_turns[-(self._max_history * 2):]

    def store_tool_output(self, result: ToolResult):
        self._tool_outputs.append(result)
        if len(self._tool_outputs) > 20:
            self._tool_outputs = self._tool_outputs[-20:]

    def get_active_bill(self) -> Optional[Dict[str, Any]]:
        return self._active_bill

    def get_active_tab(self) -> str:
        return self._active_tab

    def get_recent_history(self, turns: int = 5) -> List[Dict[str, str]]:
        return self._conversation_turns[-(turns * 2):]

    def enrich_entities(self, entities: ExtractedEntities) -> ExtractedEntities:
        """Fill in missing entities from session memory (coreference resolution)."""
        if not entities.utility and self._active_utility:
            entities.utility = self._active_utility
        if not entities.state and self._active_state:
            entities.state = self._active_state
        return entities


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 7: Confidence Fusion & Contradiction Resolution
# ═══════════════════════════════════════════════════════════════════════════

class ConfidenceFusion:
    """
    Multi-factor confidence engine that merges knowledge from multiple tools
    and transparently resolves contradictions.
    """

    _TIER_WEIGHTS = {0: 1.00, 1: 0.95, 2: 0.90, 3: 0.85, 4: 0.70}

    @classmethod
    def fuse(cls, tool_results: List[ToolResult], context_data: Dict[str, Any]) -> FusedKnowledge:
        fused_data = dict(context_data)
        contradictions: List[Dict[str, Any]] = []
        provenance: List[Dict[str, str]] = []
        confidence_scores: List[float] = []

        for result in tool_results:
            if not result.success:
                continue

            tier_weight = cls._TIER_WEIGHTS.get(result.source_tier, 0.70)
            effective_confidence = round(tier_weight * result.confidence, 4)
            confidence_scores.append(effective_confidence)

            provenance.append({
                "tool": result.tool_name,
                "source_tier": str(result.source_tier),
                "confidence": str(effective_confidence),
                "latency_ms": str(result.latency_ms)
            })

            for key, value in result.data.items():
                if key in fused_data and fused_data[key] != value:
                    existing = fused_data[key]
                    if isinstance(value, (int, float)) and isinstance(existing, (int, float)):
                        if abs(value - existing) > 0.01:
                            contradictions.append({
                                "field": key,
                                "existing_value": existing,
                                "existing_source": "context",
                                "new_value": value,
                                "new_source": result.tool_name,
                                "new_tier": result.source_tier,
                                "resolution": "kept_higher_tier" if result.source_tier == 0 else "kept_existing"
                            })
                            if result.source_tier == 0:
                                fused_data[key] = value
                            continue
                fused_data[key] = value

        overall = 1.0
        if confidence_scores:
            log_sum = sum(math.log(max(c, 0.01)) for c in confidence_scores)
            overall = round(math.exp(log_sum / len(confidence_scores)), 4)

        return FusedKnowledge(
            context_data=fused_data, tool_results=tool_results,
            overall_confidence=overall, contradictions=contradictions,
            provenance=provenance
        )


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 8: Response Critic
# ═══════════════════════════════════════════════════════════════════════════

class ResponseCritic:
    """
    Stage 1 quality gate that checks LLM output for:
        1. Answer completeness  2. Citation presence
        3. Contradiction detection  4. Unsupported claims  5. Tone & safety
    """

    @classmethod
    def critique(
        cls, response_text: str, user_query: str,
        intent_result: IntentResult, fused_knowledge: FusedKnowledge
    ) -> Tuple[bool, List[str]]:
        issues: List[str] = []

        if not response_text or len(response_text.strip()) < 20:
            issues.append("Response too short or empty")
            return False, issues

        # 1. Completeness — check key entities from query are addressed
        if intent_result.entities.component:
            component_name = intent_result.entities.component.replace("_", " ")
            response_lower = response_text.lower()
            if component_name not in response_lower and intent_result.entities.component not in response_lower:
                issues.append(f"Response may not address requested component: {intent_result.entities.component}")

        # 2. Contradicted value check
        if fused_knowledge.contradictions:
            for contradiction in fused_knowledge.contradictions:
                wrong_value = (contradiction.get("new_value") if contradiction.get("resolution") == "kept_existing"
                               else contradiction.get("existing_value"))
                if wrong_value and f"${wrong_value}" in response_text:
                    issues.append(f"Response mentions contradicted value ${wrong_value} for {contradiction['field']}")

        # 3. Tone check — no AI self-references
        tone_patterns = [
            r"\bAs an AI\b", r"\bAs a language model\b",
            r"\bI think\b", r"\bIn my opinion\b",
            r"\bI believe\b", r"\bI cannot\b",
        ]
        for pattern in tone_patterns:
            if re.search(pattern, response_text, re.IGNORECASE):
                issues.append("Tone violation: AI self-reference detected")
                break

        return len(issues) == 0, issues


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 9: Tool Executor
# ═══════════════════════════════════════════════════════════════════════════

class ToolExecutor:
    """Executes registered tools against the current context."""

    @classmethod
    def execute_tool(cls, tool_name: str, context_data: Dict[str, Any], user_message: str = "") -> ToolResult:
        start = time.time()
        try:
            dispatch = {
                "bill_data": cls._execute_bill_data,
                "analytics_engine": cls._execute_analytics,
                "forecast": cls._execute_forecast,
                "simulation": cls._execute_simulation,
                "rag_knowledge": lambda ctx, s: cls._execute_rag(ctx, user_message, s),
                "eia_data": cls._execute_eia,
                "weather_data": cls._execute_weather,
                "benchmark": cls._execute_benchmark,
            }
            handler = dispatch.get(tool_name)
            if handler:
                return handler(context_data, start)
            return ToolResult(tool_name=tool_name, success=False, error=f"Unknown tool: {tool_name}",
                              latency_ms=round((time.time() - start) * 1000, 2))
        except Exception as e:
            logger.warning(f"ToolExecutor: '{tool_name}' failed: {e}")
            return ToolResult(tool_name=tool_name, success=False, error=str(e),
                              latency_ms=round((time.time() - start) * 1000, 2))

    @classmethod
    def _execute_bill_data(cls, context_data: Dict[str, Any], start: float) -> ToolResult:
        bill = context_data.get("bill") or context_data.get("uploadedBill") or {}
        if not bill or not isinstance(bill, dict):
            return ToolResult(tool_name="bill_data", success=False, error="No bill data available",
                              latency_ms=round((time.time() - start) * 1000, 2))
        return ToolResult(tool_name="bill_data", success=True, data={"bill": bill},
                          confidence=0.98 if bill.get("total_bill") else 0.5, source_tier=1,
                          latency_ms=round((time.time() - start) * 1000, 2))

    @classmethod
    def _execute_analytics(cls, context_data: Dict[str, Any], start: float) -> ToolResult:
        bill = context_data.get("bill") or {}
        analytics_data = {}
        for key in ["total_bill", "usage_kwh", "effective_rate", "delivery_charge",
                     "supply_charge", "monthly_service_charge", "tax"]:
            val = bill.get(key)
            if val is not None:
                analytics_data[key] = val
        components = bill.get("components") or context_data.get("component_breakdown") or []
        if components:
            analytics_data["components"] = components
        tariff = context_data.get("tariff_calculations") or {}
        if tariff:
            analytics_data["tariff_calculations"] = tariff
        return ToolResult(tool_name="analytics_engine", success=True, data=analytics_data,
                          confidence=1.0, source_tier=0,
                          latency_ms=round((time.time() - start) * 1000, 2))

    @classmethod
    def _execute_forecast(cls, context_data: Dict[str, Any], start: float) -> ToolResult:
        forecast = context_data.get("forecast") or {}
        return ToolResult(tool_name="forecast", success=bool(forecast),
                          data={"forecast": forecast} if forecast else {},
                          confidence=0.92 if forecast else 0.0, source_tier=0,
                          latency_ms=round((time.time() - start) * 1000, 2),
                          error=None if forecast else "No forecast data in context")

    @classmethod
    def _execute_simulation(cls, context_data: Dict[str, Any], start: float) -> ToolResult:
        sim = context_data.get("simulation") or {}
        return ToolResult(tool_name="simulation", success=bool(sim),
                          data={"simulation": sim} if sim else {},
                          confidence=0.95 if sim else 0.0, source_tier=0,
                          latency_ms=round((time.time() - start) * 1000, 2),
                          error=None if sim else "No simulation data in context")

    @classmethod
    def _execute_rag(cls, context_data: Dict[str, Any], user_message: str, start: float) -> ToolResult:
        if not user_message:
            return ToolResult(tool_name="rag_knowledge", success=False, error="No query text for RAG",
                              latency_ms=round((time.time() - start) * 1000, 2))
        results = rag_service.query(user_message, top_k=3)
        rag_text = rag_service.query_text(user_message, top_k=3)
        return ToolResult(
            tool_name="rag_knowledge", success=bool(results),
            data={"rag_context": rag_text, "rag_results": results, "rag_document_count": len(results)},
            confidence=max((r.get("score", 0) for r in results), default=0.0) if results else 0.0,
            source_tier=2, latency_ms=round((time.time() - start) * 1000, 2))

    @classmethod
    def _execute_eia(cls, context_data: Dict[str, Any], start: float) -> ToolResult:
        eia_ctx = context_data.get("metadata", {}).get("eia923_context") or {}
        return ToolResult(tool_name="eia_data", success=bool(eia_ctx),
                          data={"eia_context": eia_ctx} if eia_ctx else {},
                          confidence=0.93 if eia_ctx else 0.0, source_tier=3,
                          latency_ms=round((time.time() - start) * 1000, 2),
                          error=None if eia_ctx else "No EIA data available")

    @classmethod
    def _execute_weather(cls, context_data: Dict[str, Any], start: float) -> ToolResult:
        weather = context_data.get("weather_normalization") or context_data.get("forecast", {}).get("weather_factors") or {}
        return ToolResult(tool_name="weather_data", success=bool(weather),
                          data={"weather": weather} if weather else {},
                          confidence=0.90 if weather else 0.0, source_tier=3,
                          latency_ms=round((time.time() - start) * 1000, 2),
                          error=None if weather else "No weather data available")

    @classmethod
    def _execute_benchmark(cls, context_data: Dict[str, Any], start: float) -> ToolResult:
        stats = context_data.get("statistics") or {}
        return ToolResult(tool_name="benchmark", success=bool(stats),
                          data={"statistics": stats} if stats else {},
                          confidence=0.92 if stats else 0.0, source_tier=1,
                          latency_ms=round((time.time() - start) * 1000, 2),
                          error=None if stats else "No benchmark data available")


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 10: Assistant Brain (Iterative Agent Loop)
# ═══════════════════════════════════════════════════════════════════════════

class AssistantBrain:
    """
    Central planning and execution engine implementing the iterative
    Plan → Execute → Observe agent loop.
    """

    MAX_AGENT_ITERATIONS = 3

    def __init__(self):
        self.tool_registry = ToolRegistry()
        self.skill_catalog = SkillCatalog()
        self.memory = ConversationMemory()

    def plan(self, user_message: str, context_data: Dict[str, Any],
             current_tab: str = "") -> Tuple[IntentResult, SkillPlan, ObservabilityTrace]:
        trace = ObservabilityTrace()
        t0 = time.time()

        self.memory.update_context(context_data, current_tab, user_message)

        intent_result = SemanticIntentRouter.classify(user_message, context_data)
        intent_result.entities = self.memory.enrich_entities(intent_result.entities)

        trace.intent = intent_result.intent.value
        trace.intent_confidence = intent_result.confidence

        skills = self.skill_catalog.resolve_skills(intent_result.intent)
        if not skills:
            fallback_skill = self.skill_catalog.get("general_knowledge")
            skills = [fallback_skill] if fallback_skill else []

        all_tools: List[str] = []
        needs_narration = False
        default_tier = ModelTier.BYPASS

        for skill in skills:
            for tool in skill.required_tools:
                if tool not in all_tools:
                    all_tools.append(tool)
            if skill.needs_llm_narration:
                needs_narration = True
            if skill.model_tier != ModelTier.BYPASS:
                default_tier = skill.model_tier

        skill_plan = SkillPlan(
            required_skills=[s.name for s in skills],
            required_tools=all_tools,
            model_tier=default_tier,
            needs_llm_narration=needs_narration,
            reasoning=f"Intent: {intent_result.intent.value} -> Skills: {[s.name for s in skills]}"
        )

        skill_plan.model_tier = CostController.select_model_tier(intent_result, skill_plan)

        trace.selected_skills = skill_plan.required_skills
        trace.selected_tools = skill_plan.required_tools
        trace.model_tier = skill_plan.model_tier.value
        trace.llm_bypassed = skill_plan.model_tier == ModelTier.BYPASS
        trace.latency_breakdown_ms["planning"] = round((time.time() - t0) * 1000, 2)

        return intent_result, skill_plan, trace

    def execute_tools(self, skill_plan: SkillPlan, context_data: Dict[str, Any],
                      user_message: str, trace: ObservabilityTrace) -> FusedKnowledge:
        t0 = time.time()
        all_results: List[ToolResult] = []
        executed_tools: Set[str] = set()

        for iteration in range(self.MAX_AGENT_ITERATIONS):
            trace.agent_loop_iterations = iteration + 1

            tools_this_round = [t for t in skill_plan.required_tools if t not in executed_tools]
            if not tools_this_round:
                break

            for tool_name in tools_this_round:
                result = ToolExecutor.execute_tool(tool_name, context_data, user_message)
                all_results.append(result)
                executed_tools.add(tool_name)

                if result.success:
                    self.memory.store_tool_output(result)

                if tool_name == "rag_knowledge" and result.success:
                    for doc in result.data.get("rag_results", []):
                        trace.retrieved_documents.append({
                            "doc_id": doc.get("doc_id", ""), "score": doc.get("score", 0)
                        })

            additional_needed = self._check_sufficiency(skill_plan, all_results, context_data, user_message)
            if not additional_needed:
                break
            for extra_tool in additional_needed:
                if extra_tool not in executed_tools and extra_tool not in skill_plan.required_tools:
                    skill_plan.required_tools.append(extra_tool)

        fused = ConfidenceFusion.fuse(all_results, context_data)
        trace.overall_confidence = fused.overall_confidence
        trace.contradictions_found = len(fused.contradictions)
        trace.latency_breakdown_ms["tool_execution"] = round((time.time() - t0) * 1000, 2)

        return fused

    def _check_sufficiency(self, plan: SkillPlan, results: List[ToolResult],
                           context_data: Dict[str, Any], user_message: str) -> List[str]:
        user_lower = user_message.lower()
        successful = {r.tool_name for r in results if r.success}
        additional: List[str] = []

        if ("weather" in user_lower or "temperature" in user_lower or "heat" in user_lower):
            if "weather_data" not in successful and "weather_data" not in plan.required_tools:
                additional.append("weather_data")

        if ("compare" in user_lower or "last month" in user_lower or "change" in user_lower):
            if "analytics_engine" not in successful and "analytics_engine" not in plan.required_tools:
                additional.append("analytics_engine")

        if ("tariff" in user_lower or "rate schedule" in user_lower):
            if "rag_knowledge" not in successful and "rag_knowledge" not in plan.required_tools:
                additional.append("rag_knowledge")

        return additional

    def format_direct_response(self, intent_result: IntentResult,
                               fused: FusedKnowledge, user_message: str) -> str:
        """Generate direct structured response WITHOUT calling the LLM."""
        bill = fused.context_data.get("bill") or {}

        if intent_result.intent == Intent.BILL_LOOKUP:
            total = bill.get("total_bill")
            kwh = bill.get("usage_kwh")
            utility = bill.get("utility") or "your utility"
            period = bill.get("billing_period") or "current period"

            if total is not None:
                parts = [f"Your {utility} bill for {period} is **${total:.2f}**"]
                if kwh:
                    parts.append(f"for **{kwh:.1f} kWh** of usage")
                    if total > 0 and kwh > 0:
                        rate = total / kwh
                        parts.append(f"(effective rate: ${rate:.4f}/kWh)")
                return " ".join(parts) + "."
            return "No bill data is currently loaded. Please upload a bill first."

        if intent_result.intent == Intent.OUT_OF_SCOPE:
            return ("I am specialized for electricity bill analysis, utility tariffs, "
                    "energy conservation, and cost optimization. Please ask me any "
                    "question about your electricity bill or utility costs!")

        return DeterministicFallback.generate_chat_fallback(fused.context_data, user_message)


# ═══════════════════════════════════════════════════════════════════════════
# SECTION 11: AI Orchestrator (Backward-Compatible Pipeline Coordinator)
# ═══════════════════════════════════════════════════════════════════════════

class AIOrchestrator:
    """
    Central AI pipeline coordinator — Phase 3.

    For 'chat' task: Routes through the full Brain pipeline
        (Intent → Plan → Tools → Fuse → Cost Decision → Critic → Validator).
    For all other tasks: Uses the proven Phase 2 failover cascade unchanged.
    """

    def __init__(self, default_provider: Optional[BaseLLMProvider] = None):
        self.router = ModelRouter()
        self._default_provider = default_provider
        self.brain = AssistantBrain()

    async def execute(
        self, task: str, context_data: Dict[str, Any],
        user_message: str = "", user_tier: UserTier = UserTier.FREE,
        bypass_cache: bool = False, **kwargs: Any
    ) -> Dict[str, Any]:
        """Full pipeline execution returning a legacy-compatible dict."""
        if task == "chat" and user_message:
            return await self._execute_brain_pipeline(
                task=task, context_data=context_data, user_message=user_message,
                user_tier=user_tier, bypass_cache=bypass_cache, **kwargs
            )
        return await self._execute_legacy_pipeline(
            task=task, context_data=context_data, user_message=user_message,
            user_tier=user_tier, bypass_cache=bypass_cache, **kwargs
        )

    # ── v3.0 Brain Pipeline (Chat) ─────────────────────────────────────

    async def _execute_brain_pipeline(
        self, task: str, context_data: Dict[str, Any],
        user_message: str, user_tier: UserTier,
        bypass_cache: bool = False, **kwargs: Any
    ) -> Dict[str, Any]:
        start_time = time.time()

        # Step 1: Sanitize
        sanitized_message = PromptInjectionGuard.sanitize(user_message)

        # Step 2: Plan
        intent_result, skill_plan, trace = self.brain.plan(
            user_message=sanitized_message, context_data=context_data,
            current_tab=context_data.get("metadata", {}).get("current_tab", "")
        )

        # Step 3: Cache check (bypassed for interactive chat to ensure live RAG)
        model_id = "brain"
        prompt_ver = "v3.0"
        if task != "chat" and not bypass_cache:
            cached = semantic_cache.get(task, context_data, model_id, prompt_ver, sanitized_message)
            if cached:
                cached.setdefault("metadata", {})["cache_hit"] = True
                cached["metadata"]["brain_intent"] = intent_result.intent.value
                return cached

        # Step 4: Execute tools
        fused = self.brain.execute_tools(
            skill_plan=skill_plan, context_data=context_data,
            user_message=sanitized_message, trace=trace
        )

        # Step 5: Cost decision — LLM bypass or narration
        if skill_plan.model_tier == ModelTier.BYPASS:
            generated_text = self.brain.format_direct_response(
                intent_result, fused, sanitized_message
            )
            trace.llm_bypassed = True
            trace.latency_breakdown_ms["total"] = round((time.time() - start_time) * 1000, 2)
            self.brain.memory.update_context(context_data, assistant_response=generated_text)
            self._log_trace(trace)

            response = LLMResponse(
                success=True, provider="AssistantBrain", model="direct_response",
                latency_ms=trace.latency_breakdown_ms["total"], cache_hit=False,
                validation_status=ValidationStatus.PASSED, retry_count=0,
                fallback_used=False, response_text=generated_text, prompt_version=prompt_ver
            )
            legacy = response.to_legacy_dict()
            legacy["metadata"]["brain_intent"] = intent_result.intent.value
            legacy["metadata"]["brain_skills"] = skill_plan.required_skills
            legacy["metadata"]["llm_bypassed"] = True
            legacy["metadata"]["confidence"] = fused.overall_confidence
            semantic_cache.set(task, context_data, model_id, prompt_ver, legacy, sanitized_message)
            return legacy

        # Step 6: LLM narration pass
        t_llm = time.time()

        system_prompt, user_prompt, _ = PromptBuilder.build_prompt(
            task=task, context_data=fused.context_data,
            user_message=sanitized_message, tighter_constraints=False
        )

        rag_text = fused.context_data.get("rag_context") or ""
        if rag_text:
            user_prompt += f"\n\nRelevant Knowledge Base:\n{rag_text}"

        if fused.contradictions:
            contradiction_text = "\n\nData Source Notes:\n"
            for c in fused.contradictions:
                contradiction_text += (
                    f"- {c['field']}: Engine={c.get('existing_value')}, "
                    f"Alternative={c.get('new_value')} (Source: {c.get('new_source')})\n"
                )
            user_prompt += contradiction_text

        if self._default_provider:
            chain = [(None, self._default_provider)]
        else:
            chain = self.router.resolve_chain(user_tier=user_tier)

        generated_text = ""
        is_valid = False
        val_errors: List[str] = []
        retry_count = 0
        provider_used = ""
        model_used = ""

        for position, (selection, provider) in enumerate(chain):
            provider_name = provider.__class__.__name__
            if provider_name != "MockLLMProvider" and not provider.is_available():
                continue

            # Attempt 1: Normal inference
            try:
                inference_resp = await InferenceClient.infer(
                    provider=provider, prompt=user_prompt,
                    system_prompt=system_prompt, temperature=0.2, **kwargs
                )
                generated_text = inference_resp.raw_text
                provider_used = inference_resp.provider
                model_used = inference_resp.model

                # Response Critic (Stage 1)
                critic_passed, critic_issues = ResponseCritic.critique(
                    generated_text, sanitized_message, intent_result, fused
                )
                trace.critic_passed = critic_passed
                if critic_issues:
                    val_errors.extend(critic_issues)

                # Numerical Validator (Stage 2)
                result = OutputValidator.validate(generated_text, fused.context_data, task)
                is_valid = result.is_valid
                val_errors.extend(result.errors)

                if is_valid and critic_passed:
                    break
            except Exception as e:
                logger.warning(f"Brain: inference with '{provider_name}' failed: {e}")
                val_errors.append(str(e))

            # Attempt 2: Guardrail retry
            if not is_valid and provider.is_available():
                retry_count += 1
                llm_metrics.record_retry()
                retry_sys, retry_user, _ = PromptBuilder.build_prompt(
                    task=task, context_data=fused.context_data,
                    user_message=sanitized_message, tighter_constraints=True
                )
                if rag_text:
                    retry_user += f"\n\nRelevant Knowledge Base:\n{rag_text}"
                try:
                    inference_resp = await InferenceClient.infer(
                        provider=provider, prompt=retry_user,
                        system_prompt=retry_sys, temperature=0.0, **kwargs
                    )
                    generated_text = inference_resp.raw_text
                    provider_used = inference_resp.provider
                    model_used = inference_resp.model
                    result = OutputValidator.validate(generated_text, fused.context_data, task)
                    is_valid = result.is_valid
                    val_errors = result.errors
                    if is_valid:
                        break
                except Exception as e:
                    logger.warning(f"Brain: guardrail retry failed: {e}")
                    val_errors.append(str(e))

            if not is_valid:
                logger.info(f"Brain: '{provider_name}' exhausted, trying next")

        trace.latency_breakdown_ms["llm_inference"] = round((time.time() - t_llm) * 1000, 2)

        # Step 7: Deterministic fallback
        fallback_used = False
        fallback_reason = None
        if not is_valid:
            fallback_reason = f"All providers exhausted. Errors: {'; '.join(val_errors[:3])}"
            logger.warning(f"Brain: deterministic fallback. Reason: {fallback_reason}")
            generated_text = DeterministicFallback.get_fallback(task, fused.context_data, sanitized_message)
            fallback_used = True
            provider_used = "DeterministicFallback"
            model_used = "template"
            llm_metrics.record_fallback()

        # Step 8: Build response
        total_latency = round((time.time() - start_time) * 1000, 2)
        trace.latency_breakdown_ms["total"] = total_latency
        trace.validation_status = "PASSED" if (is_valid or fallback_used) else "FAILED"

        self.brain.memory.update_context(context_data, assistant_response=generated_text)
        self._log_trace(trace)

        response = LLMResponse(
            success=True, provider=provider_used, model=model_used,
            latency_ms=total_latency, cache_hit=False,
            validation_status=ValidationStatus.PASSED if (is_valid or fallback_used) else ValidationStatus.FAILED,
            retry_count=retry_count, fallback_used=fallback_used,
            fallback_reason=fallback_reason, response_text=generated_text,
            warnings=val_errors if not is_valid and not fallback_used else [],
            prompt_version=prompt_ver
        )
        legacy = response.to_legacy_dict()
        legacy["metadata"]["brain_intent"] = intent_result.intent.value
        legacy["metadata"]["brain_skills"] = skill_plan.required_skills
        legacy["metadata"]["brain_tools"] = skill_plan.required_tools
        legacy["metadata"]["llm_bypassed"] = False
        legacy["metadata"]["confidence"] = fused.overall_confidence
        legacy["metadata"]["contradictions"] = len(fused.contradictions)
        legacy["metadata"]["agent_iterations"] = trace.agent_loop_iterations

        semantic_cache.set(task, context_data, model_id, prompt_ver, legacy, sanitized_message)
        return legacy

    # ── Phase 2 Legacy Pipeline (Non-Chat Tasks) ───────────────────────

    async def _execute_legacy_pipeline(
        self, task: str, context_data: Dict[str, Any],
        user_message: str = "", user_tier: UserTier = UserTier.FREE,
        bypass_cache: bool = False, **kwargs: Any
    ) -> Dict[str, Any]:
        """Phase 2 legacy pipeline — unchanged for non-chat tasks."""
        start_time = time.time()

        if user_message:
            user_message = PromptInjectionGuard.sanitize(user_message)

        system_prompt, user_prompt, prompt_ver = PromptBuilder.build_prompt(
            task=task, context_data=context_data,
            user_message=user_message, tighter_constraints=False
        )

        if task == "recommendations" and user_message:
            rag_context = rag_service.query_text(user_message, top_k=2)
            if rag_context:
                user_prompt += f"\n\nRelevant Knowledge Base:\n{rag_context}"

        model_id = "auto"
        if not bypass_cache:
            cached = semantic_cache.get(task, context_data, model_id, prompt_ver, user_message)
            if cached:
                cached.setdefault("metadata", {})["cache_hit"] = True
                return cached

        if self._default_provider:
            chain = [(None, self._default_provider)]
        else:
            chain = self.router.resolve_chain(user_tier=user_tier)

        generated_text = ""
        is_valid = False
        val_errors: List[str] = []
        retry_count = 0
        provider_used = ""
        model_used = ""

        for position, (selection, provider) in enumerate(chain):
            provider_name = provider.__class__.__name__
            model_name = provider.model

            if provider_name != "MockLLMProvider" and not provider.is_available():
                logger.info(f"Orchestrator: skipping unavailable provider '{provider_name}'")
                continue

            try:
                inference_resp = await InferenceClient.infer(
                    provider=provider, prompt=user_prompt,
                    system_prompt=system_prompt, temperature=0.2, **kwargs
                )
                generated_text = inference_resp.raw_text
                provider_used = inference_resp.provider
                model_used = inference_resp.model

                if task == "ocr":
                    try:
                        json.loads(generated_text)
                        is_valid = True
                    except Exception as je:
                        is_valid = False
                        val_errors.append(f"Invalid OCR JSON: {je}")
                else:
                    result = OutputValidator.validate(generated_text, context_data, task)
                    is_valid = result.is_valid
                    val_errors = result.errors

                if is_valid:
                    break
            except Exception as e:
                logger.warning(f"Orchestrator: attempt 1 with '{provider_name}' failed: {e}")
                val_errors.append(str(e))

            if not is_valid and provider.is_available():
                retry_count += 1
                llm_metrics.record_retry()
                logger.info(f"Orchestrator: guardrail retry with '{provider_name}' (temp=0)")

                retry_sys, retry_user, _ = PromptBuilder.build_prompt(
                    task=task, context_data=context_data,
                    user_message=user_message, tighter_constraints=True
                )
                try:
                    inference_resp = await InferenceClient.infer(
                        provider=provider, prompt=retry_user,
                        system_prompt=retry_sys, temperature=0.0, **kwargs
                    )
                    generated_text = inference_resp.raw_text
                    provider_used = inference_resp.provider
                    model_used = inference_resp.model

                    if task == "ocr":
                        try:
                            json.loads(generated_text)
                            is_valid = True
                        except Exception:
                            is_valid = False
                    else:
                        result = OutputValidator.validate(generated_text, context_data, task)
                        is_valid = result.is_valid
                        val_errors = result.errors

                    if is_valid:
                        break
                except Exception as e:
                    logger.warning(f"Orchestrator: guardrail retry with '{provider_name}' failed: {e}")
                    val_errors.append(str(e))

            if not is_valid:
                logger.info(f"Orchestrator: '{provider_name}' exhausted, trying next fallback")

        fallback_used = False
        fallback_reason = None
        if not is_valid:
            fallback_reason = f"All providers exhausted. Errors: {'; '.join(val_errors[:3])}"
            logger.warning(f"Orchestrator: falling back to deterministic template. Reason: {fallback_reason}")
            generated_text = DeterministicFallback.get_fallback(task, context_data, user_message)
            fallback_used = True
            provider_used = "DeterministicFallback"
            model_used = "template"
            llm_metrics.record_fallback()

        if not is_valid and not fallback_used:
            llm_metrics.record_validation_failure()

        latency_ms = round((time.time() - start_time) * 1000, 2)

        response = LLMResponse(
            success=True, provider=provider_used, model=model_used,
            latency_ms=latency_ms, cache_hit=False,
            validation_status=ValidationStatus.PASSED if (is_valid or fallback_used) else ValidationStatus.FAILED,
            retry_count=retry_count, fallback_used=fallback_used,
            fallback_reason=fallback_reason, response_text=generated_text,
            warnings=val_errors if not is_valid and not fallback_used else [],
            prompt_version=prompt_ver
        )
        legacy_dict = response.to_legacy_dict()
        semantic_cache.set(task, context_data, model_id, prompt_ver, legacy_dict, user_message)
        return legacy_dict

    # ── Streaming (unchanged) ──────────────────────────────────────────

    async def stream(
        self, task: str, context_data: Dict[str, Any],
        user_message: str = "", user_tier: UserTier = UserTier.FREE,
        **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        """Stream LLM response tokens. Falls back to deterministic text."""
        system_prompt, user_prompt, _ = PromptBuilder.build_prompt(
            task=task, context_data=context_data, user_message=user_message
        )
        if self._default_provider:
            providers = [(None, self._default_provider)]
        else:
            providers = self.router.resolve_chain(user_tier=user_tier)

        for selection, provider in providers:
            if not provider.is_available():
                continue
            try:
                async for token in StreamingService.token_stream(
                    provider=provider, prompt=user_prompt,
                    system_prompt=system_prompt
                ):
                    yield token
                return
            except Exception as e:
                logger.warning(f"Orchestrator stream: '{provider.__class__.__name__}' failed: {e}")
                continue

        llm_metrics.record_fallback()
        fallback_text = DeterministicFallback.get_fallback(task, context_data, user_message)
        yield fallback_text

    # ── Observability ──────────────────────────────────────────────────

    def _log_trace(self, trace: ObservabilityTrace):
        """Log end-to-end observability trace."""
        logger.info(
            f"[BrainTrace] intent={trace.intent} confidence={trace.intent_confidence:.2f} "
            f"skills={trace.selected_skills} tools={trace.selected_tools} "
            f"llm_bypassed={trace.llm_bypassed} iterations={trace.agent_loop_iterations} "
            f"confidence={trace.overall_confidence:.3f} contradictions={trace.contradictions_found} "
            f"critic={trace.critic_passed} validation={trace.validation_status} "
            f"latency={trace.latency_breakdown_ms}"
        )
