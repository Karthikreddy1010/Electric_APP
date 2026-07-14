"""
Centralized LLM Orchestrator Service.
Handles provider resolution, prompt assembly, response caching, code-level validation,
1-attempt retry strategy, and deterministic fallback generation.
"""
import time
import logging
from typing import AsyncGenerator, Dict, Any, Optional

from config.settings import llm_settings
from api.services.llm.base_provider import BaseLLMProvider
from api.services.llm.ollama_provider import OllamaProvider
from api.services.llm.mock_provider import MockLLMProvider
from api.services.llm.context_builder import ContextBuilder
from api.services.llm.prompt_builder import PromptBuilder
from api.services.llm.response_validator import ResponseValidator
from api.services.llm.cache_manager import llm_cache
from api.services.llm.deterministic_fallback import DeterministicFallback
from api.services.llm.metadata import LLMResponseMetadata

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self, provider: Optional[BaseLLMProvider] = None):
        if provider:
            self.provider = provider
        else:
            provider_type = getattr(llm_settings, "provider", "ollama").lower()
            if provider_type == "mock":
                self.provider = MockLLMProvider()
            else:
                self.provider = OllamaProvider()

    def _get_provider_name(self) -> str:
        return self.provider.__class__.__name__

    async def generate_explanation(
        self,
        task: str,
        context_data: Dict[str, Any],
        user_message: str = "",
        bypass_cache: bool = False
    ) -> Dict[str, Any]:
        """
        Executes full LLM pipeline:
        Context -> Prompt -> Cache Check -> LLM Provider Call -> Code-level Validation -> 1 Retry -> Fallback.
        """
        start_time = time.time()
        model_name = self.provider.model
        provider_name = self._get_provider_name()

        # Build prompts
        system_prompt, user_prompt, prompt_ver = PromptBuilder.build_prompt(
            task=task,
            context_data=context_data,
            user_message=user_message,
            tighter_constraints=False
        )

        # Check cache
        if not bypass_cache:
            cached = llm_cache.get(task, context_data, model_name, prompt_ver)
            if cached:
                cached["metadata"]["cache_hit"] = True
                return cached

        # Check if provider is reachable
        if not self.provider.is_available():
            logger.info(f"LLM Provider {provider_name} unavailable. Serving deterministic fallback.")
            fallback_text = DeterministicFallback.get_fallback(task, context_data, user_message)
            meta = LLMResponseMetadata(
                model=model_name,
                provider=provider_name,
                prompt_version=prompt_ver,
                validated=True,
                cache_hit=False,
                fallback_used=True,
                latency_ms=round((time.time() - start_time) * 1000, 2),
                validation_errors=["Provider offline. Used deterministic fallback."]
            )
            return {
                "success": True,
                "text": fallback_text,
                "explanation": fallback_text,
                "metadata": meta.to_dict()
            }

        # Attempt 1: Call Provider
        generated_text = ""
        is_valid = False
        val_errors = []

        try:
            generated_text = await self.provider.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.2
            )
            is_valid, val_errors = ResponseValidator.validate(generated_text, context_data)
        except Exception as e:
            logger.warning(f"Attempt 1 LLM generation error: {e}")
            val_errors.append(str(e))

        # Attempt 2: Retry with Tighter Constraints & Lower Temperature (if Attempt 1 invalid)
        if not is_valid:
            logger.info("Attempt 1 validation failed. Retrying with tighter prompt guardrails & temp=0.0...")
            retry_sys, retry_user, _ = PromptBuilder.build_prompt(
                task=task,
                context_data=context_data,
                user_message=user_message,
                tighter_constraints=True
            )
            try:
                generated_text = await self.provider.generate(
                    prompt=retry_user,
                    system_prompt=retry_sys,
                    temperature=0.0
                )
                is_valid, val_errors = ResponseValidator.validate(generated_text, context_data)
            except Exception as e:
                logger.warning(f"Attempt 2 LLM generation error: {e}")
                val_errors.append(str(e))

        # Handle Final Result
        fallback_used = False
        if not is_valid:
            logger.warning("LLM response validation failed twice. Using deterministic fallback text.")
            generated_text = DeterministicFallback.get_fallback(task, context_data, user_message)
            fallback_used = True

        latency_ms = round((time.time() - start_time) * 1000, 2)
        meta = LLMResponseMetadata(
            model=model_name,
            provider=provider_name,
            prompt_version=prompt_ver,
            validated=is_valid,
            cache_hit=False,
            fallback_used=fallback_used,
            latency_ms=latency_ms,
            validation_errors=val_errors
        )

        response_payload = {
            "success": True,
            "text": generated_text,
            "explanation": generated_text,
            "answer": generated_text,
            "metadata": meta.to_dict()
        }

        # Cache valid or fallback outputs
        llm_cache.set(task, context_data, model_name, prompt_ver, response_payload)
        return response_payload

    async def stream_explanation(
        self,
        task: str,
        context_data: Dict[str, Any],
        user_message: str = ""
    ) -> AsyncGenerator[str, None]:
        """Stream LLM response tokens directly."""
        system_prompt, user_prompt, _ = PromptBuilder.build_prompt(
            task=task,
            context_data=context_data,
            user_message=user_message
        )

        if not self.provider.is_available():
            fallback_text = DeterministicFallback.get_fallback(task, context_data, user_message)
            yield fallback_text
            return

        try:
            async for token in self.provider.generate_stream(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.2
            ):
                yield token
        except Exception as e:
            logger.error(f"Error streaming from LLM provider: {e}")
            fallback_text = DeterministicFallback.get_fallback(task, context_data, user_message)
            yield fallback_text

llm_service = LLMService()
