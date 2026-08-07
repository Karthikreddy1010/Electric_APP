"""
Prompt Builder module.
Assembles versioned prompts using templates from prompt_registry.py.
Applies additional strict constraints during retry passes.
"""
import json
from typing import Dict, Any, Tuple
from api.services.llm.prompt_registry import PROMPT_TEMPLATES, MANDATORY_SYSTEM_GUARDRAILS

from api.services.llm.context_builder import ContextBuilder
from api.services.llm.prompt_budget_manager import PromptBudgetManager

class PromptBuilder:
    @classmethod
    def build_prompt(
        cls,
        task: str,
        context_data: Dict[str, Any],
        user_message: str = "",
        tighter_constraints: bool = False
    ) -> Tuple[str, str, str]:
        """
        Builds (system_prompt, user_prompt, prompt_version).
        """
        template_info = PROMPT_TEMPLATES.get(task, PROMPT_TEMPLATES["bill_analysis"])
        version = template_info["version"]
        system_prompt = template_info["system"]
        user_template = template_info["user_template"]

        if tighter_constraints:
            system_prompt += (
                "\nSTRICT RETRY ENFORCEMENT: Response failed initial numeric validation.\n"
                "You must output ONLY numbers present in the JSON context.\n"
                "Do NOT perform any calculations or estimate numbers."
            )

        filtered_context = ContextBuilder.filter_by_intent(task, context_data)
        pruned_context = ContextBuilder.prune_empty_fields(filtered_context)
        context_json_str = json.dumps(pruned_context, separators=(',', ':'), default=str)

        history_list = context_data.get("metadata", {}).get("conversation_history", [])
        if isinstance(history_list, list) and len(history_list) > 3:
            history_list = history_list[-3:]
        history_json_str = json.dumps(history_list, separators=(',', ':'), default=str)

        user_prompt = user_template.format(
            context_json=context_json_str,
            history_json=history_json_str,
            user_message=user_message
        )

        # Audit and enforce prompt section token budget (target <= 3500 tokens)
        PromptBudgetManager.calculate_budget_allocation({
            "system_guardrails": MANDATORY_SYSTEM_GUARDRAILS,
            "system_task": system_prompt,
            "bill_data": context_json_str,
            "conversation_history": history_json_str
        })

        system_prompt, user_prompt = PromptBudgetManager.enforce_prompt_budget(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_budget=3500
        )

        return system_prompt, user_prompt, version
