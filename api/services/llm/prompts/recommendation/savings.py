"""Phase 2 — Savings Recommendations Prompt Template."""
from api.services.llm.prompts.base import PromptTemplate
from api.services.llm.prompts.system.guardrails import MANDATORY_SYSTEM_GUARDRAILS
from api.services.llm.contracts import PromptMetadata

savings = PromptTemplate(
    metadata=PromptMetadata(
        prompt_id="savings_recommendations",
        prompt_version="2.0.0",
        created_by="system",
        required_fields=["total_bill", "usage_kwh"]
    ),
    system_prompt=(
        f"{MANDATORY_SYSTEM_GUARDRAILS}\n"
        "Task: Provide prioritized clean energy and load-shifting recommendations "
        "with estimated savings potential."
    ),
    user_template=(
        "Synthesize actionable energy optimization recommendations based "
        "strictly on the context below:\n"
        "Context Data:\n{context_json}"
    )
)
