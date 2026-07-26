"""
Phase 2 — Unified Inference Client.

Provider-agnostic wrapper that executes inference calls with telemetry,
timeout handling, and structured InferenceResponse contracts.

Design rationale: Separating the inference execution from the Router and
Orchestrator allows metrics collection and error handling to be centralised
in one location instead of scattered across each provider.
"""
import time
import logging
from typing import AsyncGenerator, Optional, Any
from api.services.llm.providers.base_provider import BaseLLMProvider
from api.services.llm.contracts import InferenceResponse
from api.services.llm.metrics import llm_metrics

logger = logging.getLogger(__name__)


class InferenceClient:
    """
    Wraps a BaseLLMProvider call with telemetry and returns a structured
    InferenceResponse contract.
    """

    @staticmethod
    async def infer(
        provider: BaseLLMProvider,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        **kwargs: Any
    ) -> InferenceResponse:
        """Execute a single inference call and return a structured response."""
        llm_metrics.record_request_start()
        start = time.time()

        try:
            raw_text = await provider.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            latency_ms = round((time.time() - start) * 1000, 2)
            llm_metrics.record_success(latency_ms)

            return InferenceResponse(
                raw_text=raw_text,
                model=provider.model,
                provider=provider.__class__.__name__,
                prompt_tokens=0,  # Providers that report tokens can override
                completion_tokens=0,
                latency_ms=latency_ms
            )
        except Exception as e:
            latency_ms = round((time.time() - start) * 1000, 2)
            llm_metrics.record_failure(
                error_type=type(e).__name__,
                message=str(e)
            )
            logger.error(f"InferenceClient error ({provider.__class__.__name__}): {e}")
            raise

    @staticmethod
    async def infer_stream(
        provider: BaseLLMProvider,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        """Execute a streaming inference call and yield tokens."""
        llm_metrics.record_request_start()
        start = time.time()

        try:
            async for token in provider.generate_stream(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            ):
                yield token
            latency_ms = round((time.time() - start) * 1000, 2)
            llm_metrics.record_success(latency_ms)
        except Exception as e:
            llm_metrics.record_failure(type(e).__name__, str(e))
            logger.error(f"InferenceClient stream error ({provider.__class__.__name__}): {e}")
            raise
