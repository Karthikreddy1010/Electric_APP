"""
Centralized LLM Orchestrator Service.
Handles provider resolution, prompt assembly, response caching, code-level validation,
1-attempt retry strategy, deterministic fallback generation, and telemetry gathering.
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
from api.services.llm.metrics import llm_metrics

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
        bypass_cache: bool = False,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Executes full LLM pipeline:
        Context -> Prompt -> Cache Check -> LLM Provider Call -> Code-level Validation -> Guardrail Retry -> Fallback.
        """
        import json
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

        # Pre-flight Reachability & Model Availability Checks
        if not self.provider.is_available():
            reason = f"Provider {provider_name} is offline or unreachable at base_url."
            logger.info(f"LLM Provider {provider_name} unavailable. Serving deterministic fallback. Reason: {reason}")
            llm_metrics.record_fallback()
            fallback_text = DeterministicFallback.get_fallback(task, context_data, user_message)
            meta = LLMResponseMetadata(
                model=model_name,
                provider=provider_name,
                prompt_version=prompt_ver,
                validated=False,
                cache_hit=False,
                fallback_used=True,
                fallback_reason=reason,
                latency_ms=round((time.time() - start_time) * 1000, 2),
                validation_errors=[reason]
            )
            return {
                "success": True,
                "text": fallback_text,
                "explanation": fallback_text,
                "answer": fallback_text,
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
                temperature=0.2,
                **kwargs
            )
            if task == "ocr":
                try:
                    json.loads(generated_text)
                    is_valid = True
                except Exception as je:
                    is_valid = False
                    val_errors.append(f"Invalid OCR JSON: {je}")
            else:
                is_valid, val_errors = ResponseValidator.validate(generated_text, context_data)
        except Exception as e:
            logger.warning(f"Attempt 1 LLM generation exception: {e}")
            val_errors.append(str(e))

        if not is_valid:
            llm_metrics.record_validation_failure()

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
                    temperature=0.0,
                    **kwargs
                )
                if task == "ocr":
                    try:
                        json.loads(generated_text)
                        is_valid = True
                    except Exception as je:
                        is_valid = False
                        val_errors.append(f"Invalid OCR JSON in retry: {je}")
                else:
                    is_valid, val_errors = ResponseValidator.validate(generated_text, context_data)
            except Exception as e:
                logger.warning(f"Attempt 2 LLM generation exception: {e}")
                val_errors.append(str(e))

        # Handle Final Result / Fallback
        fallback_used = False
        fallback_reason = None
        if not is_valid:
            fallback_reason = f"LLM generation failed validation twice. Errors: {'; '.join(val_errors)}"
            logger.warning(f"LLM validation failed. Falling back to deterministic output. Reason: {fallback_reason}")
            generated_text = DeterministicFallback.get_fallback(task, context_data, user_message)
            fallback_used = True
            llm_metrics.record_fallback()

        latency_ms = round((time.time() - start_time) * 1000, 2)
        meta = LLMResponseMetadata(
            model=model_name,
            provider=provider_name,
            prompt_version=prompt_ver,
            validated=is_valid,
            cache_hit=False,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
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
            llm_metrics.record_fallback()
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
            llm_metrics.record_fallback()
            fallback_text = DeterministicFallback.get_fallback(task, context_data, user_message)
            yield fallback_text

llm_service = LLMService()

