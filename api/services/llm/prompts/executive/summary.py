"""Phase 2 — Executive Summary Prompt Template."""
from api.services.llm.prompts.base import PromptTemplate
from api.services.llm.prompts.system.guardrails import MANDATORY_SYSTEM_GUARDRAILS
from api.services.llm.contracts import PromptMetadata

executive_summary = PromptTemplate(
    metadata=PromptMetadata(
        prompt_id="executive_summary",
        prompt_version="2.0.0",
        created_by="system",
        required_fields=["total_bill", "usage_kwh"]
    ),
    system_prompt=(
        f"{MANDATORY_SYSTEM_GUARDRAILS}\n"
        "Task: Summarize executive facility dashboard telemetry, key monthly alerts, "
        "and top-line KPIs for C-level stakeholders."
    ),
    user_template=(
        "Generate an executive dashboard summary based strictly on the metrics below:\n"
        "Context Data:\n{context_json}"
    )
)
