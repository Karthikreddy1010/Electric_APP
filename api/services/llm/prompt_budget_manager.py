"""
Prompt Budget Manager module.
Allocates, tracks, and dynamically rebalances token budgets across prompt components.
Target max token allocation <= 3,500 tokens (well within 4,096 num_ctx limit).
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Default Section Token Budgets (Total Target <= 3,500 Tokens)
DEFAULT_SECTION_BUDGETS: Dict[str, int] = {
    "system_guardrails": 200,
    "system_task": 300,
    "bill_data": 500,
    "analytics_data": 500,
    "rag_context": 1000,
    "conversation_history": 600,
    "recommendations_weather": 400,
}

MAX_TOTAL_BUDGET = 3500

class PromptBudgetManager:
    """
    Centralized manager for prompt component token budgeting and estimation.
    """

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estimates token count for text snippet using character ratio fallback (~4 chars/token).
        """
        if not text:
            return 0
        return max(1, len(text) // 4)

    @classmethod
    def calculate_budget_allocation(
        cls,
        active_sections: Dict[str, str],
        custom_budgets: Optional[Dict[str, int]] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        Calculates token allocation per section, performing dynamic budget rebalancing.
        Reallocates unused budget from inactive sections to active sections.
        """
        budgets = dict(DEFAULT_SECTION_BUDGETS)
        if custom_budgets:
            budgets.update(custom_budgets)

        usage: Dict[str, Dict[str, Any]] = {}
        total_used = 0
        unused_pool = 0

        # Step 1: Calculate raw usage per section
        for section_name, section_text in active_sections.items():
            allocated = budgets.get(section_name, 300)
            est_tokens = cls.estimate_tokens(section_text)
            
            if est_tokens <= allocated:
                unused_pool += (allocated - est_tokens)
                usage[section_name] = {
                    "allocated": allocated,
                    "tokens": est_tokens,
                    "status": "within_budget"
                }
            else:
                usage[section_name] = {
                    "allocated": allocated,
                    "tokens": est_tokens,
                    "status": "exceeds_budget"
                }
            total_used += est_tokens

        # Step 2: Dynamic Rebalancing if any section exceeded budget
        if unused_pool > 0:
            for section_name, info in usage.items():
                if info["status"] == "exceeds_budget":
                    overage = info["tokens"] - info["allocated"]
                    grant = min(overage, unused_pool)
                    info["allocated"] += grant
                    unused_pool -= grant
                    if info["tokens"] <= info["allocated"]:
                        info["status"] = "rebalanced_fit"

        budget_summary = {
            "total_tokens": total_used,
            "max_budget": MAX_TOTAL_BUDGET,
            "budget_usage_pct": round((total_used / MAX_TOTAL_BUDGET) * 100.0, 1),
            "section_breakdown": usage
        }

        logger.info(
            f"[Prompt Budget Audit] Total Tokens: {total_used} / {MAX_TOTAL_BUDGET} "
            f"({budget_summary['budget_usage_pct']}%)"
        )
        return budget_summary

    @classmethod
    def trim_text_to_token_limit(cls, text: str, max_tokens: int) -> str:
        """
        Trims text string so it does not exceed the target max token budget.
        """
        est_tokens = cls.estimate_tokens(text)
        if est_tokens <= max_tokens:
            return text
        max_chars = max_tokens * 4
        logger.warning(f"Trimming section text from {len(text)} chars to {max_chars} chars ({max_tokens} tokens)")
        return text[:max_chars] + "..."

    @classmethod
    def enforce_prompt_budget(
        cls,
        system_prompt: str,
        user_prompt: str,
        max_budget: int = 3500
    ) -> tuple[str, str]:
        """
        Enforces global token limit immediately prior to firing LLM inference.
        If combined tokens exceed max_budget, safely trims user_prompt.
        """
        total_tokens = cls.estimate_tokens(system_prompt) + cls.estimate_tokens(user_prompt)
        if total_tokens <= max_budget:
            return system_prompt, user_prompt

        logger.warning(
            f"[Prompt Budget Exceeded] Combined prompt tokens ({total_tokens}) exceed max budget ({max_budget}). "
            "Applying budget truncation to user prompt."
        )
        sys_tokens = cls.estimate_tokens(system_prompt)
        allowed_user_tokens = max(100, max_budget - sys_tokens)
        trimmed_user = cls.trim_text_to_token_limit(user_prompt, allowed_user_tokens)
        return system_prompt, trimmed_user
