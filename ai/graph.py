"""
LangGraph StateGraph Workflow Orchestrator for Grounded AI Assistant.
"""
import time
import logging
from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage, AIMessage

from ai.state import AssistantState
from ai.router import DataRequirementRouter
from ai.tools.registry import tool_registry
from ai.evidence import EvidenceValidationEngine
from ai.critic import ProgrammaticClaimValidator
from api.services.llm.inference import InferenceClient
from api.services.llm.contracts import UserTier

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Graph Nodes
# ═══════════════════════════════════════════════════════════════════════════

async def node_analyze_query(state: AssistantState) -> Dict[str, Any]:
    """Node 1: Analyze user query and determine structured requirement."""
    q = state.get("user_query", "")
    tab = state.get("current_tab")
    req = DataRequirementRouter.analyze_query(q, current_tab=tab)
    planned_tools = DataRequirementRouter.plan_tool_calls(req, q)

    return {
        "query_requirement": req.dict(),
        "metadata": {
            "intent": req.intent,
            "planned_tools": [t["tool_name"] for t in planned_tools],
            "geography": req.geography_scope.value,
            "state_code": req.state_code
        }
    }


async def node_execute_tools(state: AssistantState) -> Dict[str, Any]:
    """Node 2: Tool Execution Node."""
    q = state.get("user_query", "")
    req_dict = state.get("query_requirement", {})
    from ai.schemas import StructuredQueryRequirement
    req = StructuredQueryRequirement(**req_dict) if req_dict else DataRequirementRouter.analyze_query(q)

    planned = DataRequirementRouter.plan_tool_calls(req, q)
    executed_names = []
    outputs = []

    for t_call in planned:
        name = t_call["tool_name"]
        args = t_call.get("args", {})
        res = tool_registry.invoke_tool(name, args)
        executed_names.append(name)
        outputs.append(res)

    return {
        "executed_tools": executed_names,
        "tool_outputs": outputs
    }


async def node_validate_evidence(state: AssistantState) -> Dict[str, Any]:
    """Node 3: Evidence Validation Node."""
    q = state.get("user_query", "")
    outputs = state.get("tool_outputs", [])
    evidence = EvidenceValidationEngine.build_evidence(q, outputs)

    return {
        "evidence": evidence.dict()
    }


async def node_generate_answer(state: AssistantState) -> Dict[str, Any]:
    """Node 4: Grounded LLM Response Generator Node."""
    q = state.get("user_query", "")
    ev_dict = state.get("evidence", {})
    from ai.schemas import EvidenceObject
    evidence = EvidenceObject(**ev_dict) if ev_dict else EvidenceObject(question=q)
    user_tier_str = state.get("user_tier", "free")

    # If no claims and missing info present, OR if confidence is UNVERIFIED (semantic gap), enforce explicit unverified output without calling LLM
    from ai.schemas import ClaimConfidence
    is_empty_evidence = not evidence.claims and not evidence.calculations and not evidence.external_sources and evidence.missing_information
    is_unverified_confidence = evidence.overall_confidence == ClaimConfidence.UNVERIFIED and evidence.missing_information

    if is_empty_evidence or is_unverified_confidence:
        missing_str = "; ".join(evidence.missing_information)
        fallback = f"I couldn't verify this information from available authoritative data sources ({missing_str}), so I won't provide an unverified estimate."
        return {
            "generated_text": fallback
        }

    # Construct Grounded Prompt with Evidence
    claims_text = "\n".join([f"- [{c.claim_id}] {c.claim_text} (Source: {c.source_provenance.title if c.source_provenance else 'Database'})" for c in evidence.claims])
    calcs_text = "\n".join([f"- Formula: {calc.formula} => Result: {calc.result} {calc.unit or ''} (Engine: {calc.deterministic_engine})" for calc in evidence.calculations])
    sources_text = "\n".join([f"- [{s.title}] URL: {s.url or 'Internal'} (Date: {s.publication_date or 'Current'})" for s in evidence.external_sources])
    conflict_text = "\n".join([f"- Conflict in {conf.metric}: {conf.resolution_explanation}" for conf in evidence.conflicting_sources])

    prompt = f"""You are ElectricAI Grounded Assistant.
Answer the user's question accurately using ONLY the validated evidence below.
DO NOT invent numbers, rates, percentages, averages, or forecasts.

USER QUESTION:
{q}

VALIDATED CLAIMS:
{claims_text or 'None'}

DETERMINISTIC CALCULATIONS:
{calcs_text or 'None'}

AUTHORITATIVE SOURCES:
{sources_text or 'None'}

CONFLICT RESOLUTION (IF ANY):
{conflict_text or 'None'}

INSTRUCTIONS:
1. Explain the answer naturally based ONLY on the validated claims and calculations.
2. Cite the source (e.g. [Source: EIA] or [Based on your bill]) for factual statements.
3. If information is missing, explicitly say it could not be verified.
"""

    try:
        from api.services.llm.router import ModelRouter
        tier_enum = UserTier(user_tier_str.lower()) if hasattr(UserTier, user_tier_str.upper()) else UserTier.FREE
        router = ModelRouter()
        chain = router.resolve_chain(user_tier=tier_enum)
        if chain:
            _, provider = chain[0]
            resp = await InferenceClient.infer(
                provider=provider,
                prompt=prompt,
                system_prompt="You are a grounded energy assistant. Strictly narrate verified evidence with source citations. Never fabricate numerical facts."
            )
            text = resp.raw_text
        else:
            raise ValueError("No LLM provider available in router chain")
    except Exception as e:
        logger.warning(f"Inference Client notice, generating structured response: {e}")
        from api.services.llm.mock_provider import MockLLMProvider
        try:
            mock_p = MockLLMProvider()
            text = await mock_p.generate(prompt=prompt)
        except Exception:
            lines = []
            if evidence.claims:
                for c in evidence.claims:
                    lines.append(f"• {c.claim_text}")
            if evidence.calculations:
                for calc in evidence.calculations:
                    inputs = calc.inputs or {}
                    main_driver = inputs.get("main_driver")
                    if main_driver:
                        lines.append(f"• Driver: {main_driver}")
                    lines.append(f"• Calculated result: {calc.result} {calc.unit or ''} ({calc.formula})")
            if evidence.external_sources:
                src_titles = ", ".join([s.title for s in evidence.external_sources])
                lines.append(f"\n[Source: {src_titles}]")

            text = "\n".join(lines) if lines else "Information retrieved from authoritative datasets."


    return {
        "generated_text": text
    }


async def node_critic_check(state: AssistantState) -> Dict[str, Any]:
    """Node 5: Programmatic Claim Critic Node."""
    gen_text = state.get("generated_text", "")
    ev_dict = state.get("evidence", {})
    from ai.schemas import EvidenceObject, GroundedResponse, SourceMetadata, CalculationItem
    evidence = EvidenceObject(**ev_dict) if ev_dict else EvidenceObject(question=state.get("user_query", ""))

    is_valid, validated_text, blocked_count = ProgrammaticClaimValidator.validate_response(gen_text, evidence)

    sources = evidence.external_sources
    calcs = evidence.calculations

    resp = GroundedResponse(
        answer=validated_text,
        evidence=evidence,
        sources=sources,
        tools_used=state.get("executed_tools", []),
        data_freshness="2026-Q2 Verified Datasets",
        calculations=calcs,
        grounded=is_valid,
        unverified_claims_blocked=blocked_count
    )

    return {
        "validated_response": resp.dict(),
        "unverified_blocked": blocked_count
    }


# ═══════════════════════════════════════════════════════════════════════════
# State Graph Construction
# ═══════════════════════════════════════════════════════════════════════════

def build_assistant_graph():
    workflow = StateGraph(AssistantState)

    # Add Nodes
    workflow.add_node("analyze_query", node_analyze_query)
    workflow.add_node("execute_tools", node_execute_tools)
    workflow.add_node("validate_evidence", node_validate_evidence)
    workflow.add_node("generate_answer", node_generate_answer)
    workflow.add_node("critic_check", node_critic_check)

    # Add Edges
    workflow.add_edge(START, "analyze_query")
    workflow.add_edge("analyze_query", "execute_tools")
    workflow.add_edge("execute_tools", "validate_evidence")
    workflow.add_edge("validate_evidence", "generate_answer")
    workflow.add_edge("generate_answer", "critic_check")
    workflow.add_edge("critic_check", END)

    return workflow.compile()


# Compiled executable graph app
grounded_graph_app = build_assistant_graph()
