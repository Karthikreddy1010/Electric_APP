"""
Phase 2 — LLMService Backward Compatibility Facade.

Preserves the exact API surface expected by all existing routes, tests,
and background_worker.py while delegating work to GroundedAgent and AIOrchestrator.

This file is the ONLY entry point that existing code imports.
No import path is broken.
"""
import logging
from typing import AsyncGenerator, Dict, Any, Optional

from api.services.llm.contracts import UserTier
from api.services.llm.orchestrator import AIOrchestrator
from api.services.llm.providers.base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)



class LLMService:
    """
    Backward-compatible facade forwarding calls to GroundedAgent & AIOrchestrator.
    """

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        self.orchestrator = AIOrchestrator(default_provider=provider)
        if provider:
            self.provider = provider
        else:
            self.provider = _FacadeProviderProxy()

    async def generate_explanation(
        self,
        task: str,
        context_data: Dict[str, Any],
        user_message: str = "",
        bypass_cache: bool = False,
        user_tier: UserTier = UserTier.FREE,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Executes the AI orchestration pipeline and returns the structured dict:
            {success, text, explanation, answer, metadata}
        """
        if task == "grounded_chat":
            from ai.agent import grounded_agent
            query = user_message or context_data.get("user_message") or context_data.get("prompt") or task or "Explain bill details"
            tier_str = user_tier.value if hasattr(user_tier, "value") else str(user_tier)
            return await grounded_agent.execute(
                user_query=query,
                context_data=context_data,
                current_tab=context_data.get("current_tab"),
                user_tier=tier_str
            )

        return await self.orchestrator.execute(
            task=task,
            context_data=context_data,
            user_message=user_message,
            bypass_cache=bypass_cache,
            user_tier=user_tier,
            **kwargs
        )

    async def stream_explanation(
        self,
        task: str,
        context_data: Dict[str, Any],
        user_message: str = "",
        user_tier: UserTier = UserTier.FREE,
        **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        """Stream LLM response tokens from AIOrchestrator."""
        if task == "grounded_chat":
            from ai.agent import grounded_agent
            query = user_message or context_data.get("user_message") or task or "Explain bill details"
            tier_str = user_tier.value if hasattr(user_tier, "value") else str(user_tier)
            async for token in grounded_agent.stream(user_query=query, user_tier=tier_str):
                yield token
            return

        async for token in self.orchestrator.stream(
            task=task,
            context_data=context_data,
            user_message=user_message,
            user_tier=user_tier,
            **kwargs
        ):
            yield token



class _FacadeProviderProxy:
    def __init__(self):
        self.model = "auto"
        self.base_url = "http://localhost:11434"

    def is_available(self) -> bool:
        import httpx
        try:
            r = httpx.get(f"{self.base_url}/api/tags", timeout=1.5)
            return r.status_code == 200
        except Exception:
            return False


# Global singleton — matches existing import: `from api.services.llm.llm_service import llm_service`
llm_service = LLMService()

