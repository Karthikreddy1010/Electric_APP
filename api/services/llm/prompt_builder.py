"""
Prompt Builder module.
Assembles versioned prompts using templates from prompt_registry.py.
Applies additional strict constraints during retry passes.
"""
import json
from typing import Dict, Any, Tuple
from api.services.llm.prompt_registry import PROMPT_TEMPLATES, MANDATORY_SYSTEM_GUARDRAILS

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

        context_json_str = json.dumps(context_data, indent=2, default=str)
        history_json_str = json.dumps(
            context_data.get("metadata", {}).get("conversation_history", []),
            indent=2,
            default=str
        )

        user_prompt = user_template.format(
            context_json=context_json_str,
            history_json=history_json_str,
            user_message=user_message
        )

        return system_prompt, user_prompt, version
