"""Phase 2 — Bill Explanation Prompt Template."""
from api.services.llm.prompts.base import PromptTemplate
from api.services.llm.prompts.system.guardrails import MANDATORY_SYSTEM_GUARDRAILS
from api.services.llm.contracts import PromptMetadata

bill_explanation = PromptTemplate(
    metadata=PromptMetadata(
        prompt_id="bill_explanation",
        prompt_version="2.0.0",
        created_by="system",
        required_fields=["total_bill", "usage_kwh", "supply_charge", "delivery_charge"]
    ),
    system_prompt=(
        f"{MANDATORY_SYSTEM_GUARDRAILS}\n"
        "Task: Generate an executive bill interpretation audit report covering: "
        "Bill Summary, Charge Breakdown & Controllability, Why Your Bill Changed, "
        "and Savings Opportunities."
    ),
    user_template=(
        "Provide a narrative explanation based strictly on the following bill context:\n"
        "Context Data:\n{context_json}"
    )
)
