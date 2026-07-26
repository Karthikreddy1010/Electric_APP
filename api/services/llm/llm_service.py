"""
Phase 2 — LLMService Backward Compatibility Facade.

Preserves the exact API surface expected by all existing routes, tests,
and background_worker.py while delegating all work to the new AIOrchestrator.

This file is the ONLY entry point that existing Phase 1 code imports.
No Phase 1 import path is broken.
"""
import logging
from typing import AsyncGenerator, Dict, Any, Optional

from api.services.llm.contracts import UserTier
from api.services.llm.orchestrator import AIOrchestrator
from api.services.llm.providers.base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)


class LLMService:
    """
    Backward-compatible facade forwarding calls to AIOrchestrator.

    Maintains identical __init__(provider=...) signature and the two public
    methods (generate_explanation, stream_explanation) that all routes
    and background_worker use.
    """

    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        self.orchestrator = AIOrchestrator(default_provider=provider)
        # Expose .provider for backward compatibility with background_worker
        # which checks `llm_service.provider.is_available()` and `.provider.model`
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
        Executes the full AI pipeline via the Orchestrator and returns
        the legacy-format dict:
            {success, text, explanation, answer, metadata}
        """
        return await self.orchestrator.execute(
            task=task,
            context_data=context_data,
            user_message=user_message,
            user_tier=user_tier,
            bypass_cache=bypass_cache,
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
        """Stream LLM response tokens. Falls back to deterministic text."""
        async for token in self.orchestrator.stream(
            task=task,
            context_data=context_data,
            user_message=user_message,
            user_tier=user_tier,
            **kwargs
        ):
            yield token


class _FacadeProviderProxy:
    """
    Minimal proxy satisfying `llm_service.provider.model` and
    `llm_service.provider.is_available()` calls in background_worker.py
    without requiring an actual provider instance at import time.
    """

    def __init__(self):
        self.model = "auto"

    def is_available(self) -> bool:
        """
        For the facade, always return True — the Orchestrator's router
        will handle individual provider availability checks internally.
        """
        return True


# Global singleton — matches the Phase 1 import: `from api.services.llm.llm_service import llm_service`
llm_service = LLMService()
