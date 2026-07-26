"""Phase 2 — PDF Report Prompt Template."""
from api.services.llm.prompts.base import PromptTemplate
from api.services.llm.prompts.system.guardrails import MANDATORY_SYSTEM_GUARDRAILS
from api.services.llm.contracts import PromptMetadata

pdf_report = PromptTemplate(
    metadata=PromptMetadata(
        prompt_id="pdf_report",
        prompt_version="2.0.0",
        created_by="system",
        required_fields=["total_bill", "usage_kwh"]
    ),
    system_prompt=(
        f"{MANDATORY_SYSTEM_GUARDRAILS}\n"
        "Task: Explain the user's billing breakdown in simple, practical language "
        "focusing on controllability, drivers, weather vs behavioral loads, and "
        "next steps. Do NOT mention SHAP, machine learning models, or AI."
    ),
    user_template=(
        "Explain this bill context:\n{context_json}"
    )
)
