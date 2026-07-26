"""
Phase 2 — Multi-Channel Streaming Service.

Provides three distinct stream channels:
  1. Token Stream — real-time LLM token generator for typing animation
  2. Progress Stream — step-by-step pipeline progress events
  3. Message Stream — structured JSON SSE payload stream

Supports Server-Sent Events (SSE) and WebSocket protocols.
"""
import json
import logging
from typing import AsyncGenerator, Dict, Any
from api.services.llm.providers.base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)


class StreamingService:
    """Multi-channel streaming response handler."""

    @staticmethod
    async def token_stream(
        provider: BaseLLMProvider,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.2
    ) -> AsyncGenerator[str, None]:
        """Yield raw text tokens for typing animation."""
        async for token in provider.generate_stream(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature
        ):
            yield token

    @staticmethod
    async def progress_stream(steps: list) -> AsyncGenerator[str, None]:
        """Yield progress step messages as SSE data events."""
        for step in steps:
            event = json.dumps({"type": "progress", "step": step})
            yield f"data: {event}\n\n"

    @staticmethod
    async def sse_token_stream(
        provider: BaseLLMProvider,
        prompt: str,
        system_prompt: str = "",
        temperature: float = 0.2
    ) -> AsyncGenerator[str, None]:
        """
        Yield tokens formatted as SSE data events:
            data: {"type": "token", "content": "..."}
        Ends with:
            data: {"type": "done"}
        """
        # Send initial progress event
        start_event = json.dumps({"type": "progress", "step": "Generating response..."})
        yield f"data: {start_event}\n\n"

        try:
            async for token in provider.generate_stream(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature
            ):
                event = json.dumps({"type": "token", "content": token})
                yield f"data: {event}\n\n"

            done_event = json.dumps({"type": "done"})
            yield f"data: {done_event}\n\n"

        except Exception as e:
            logger.error(f"StreamingService SSE error: {e}")
            error_event = json.dumps({"type": "error", "message": str(e)})
            yield f"data: {error_event}\n\n"

    @staticmethod
    async def fallback_sse_stream(text: str) -> AsyncGenerator[str, None]:
        """Yield deterministic fallback text as a single SSE message event."""
        event = json.dumps({"type": "message", "content": text, "fallback": True})
        yield f"data: {event}\n\n"
        done_event = json.dumps({"type": "done"})
        yield f"data: {done_event}\n\n"
