"""Phase 2 — Forecast Narrative Prompt Template."""
from api.services.llm.prompts.base import PromptTemplate
from api.services.llm.prompts.system.guardrails import MANDATORY_SYSTEM_GUARDRAILS
from api.services.llm.contracts import PromptMetadata

forecast_narrative = PromptTemplate(
    metadata=PromptMetadata(
        prompt_id="forecast_narrative",
        prompt_version="2.0.0",
        created_by="system",
        required_fields=["predicted_kwh", "predicted_cost"]
    ),
    system_prompt=(
        f"{MANDATORY_SYSTEM_GUARDRAILS}\n"
        "Task: Provide a detailed forecast summary explaining weather trends, "
        "seasonal demand adjustments, and prediction confidence intervals."
    ),
    user_template=(
        "Explain the consumption and financial forecast based on the "
        "structured data provided below:\n"
        "Context Data:\n{context_json}"
    )
)
