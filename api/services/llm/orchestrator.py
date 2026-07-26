"""
Phase 2 — AI Orchestrator.

Central pipeline coordinator that sequences:
    PromptBuilder -> RAG -> ModelRouter -> InferenceClient -> OutputValidator
    -> SemanticCache -> StreamingService -> ReportGenerator -> LLMResponse

Implements the 4-step deterministic failover cascade:
    1. Primary model (temp=0.2)
    2. Guardrail retry (temp=0.0, strict prompt)
    3. Cloud provider failover
    4. Deterministic template renderer (always succeeds)

Design rationale: Orchestrating through a central coordinator eliminates
scattered control flow, ensures consistent telemetry, and makes the full
pipeline testable as a single unit while each sub-component remains
independently unit-testable.
"""
import time
import json
import logging
from typing import AsyncGenerator, Dict, Any, Optional

from api.services.llm.contracts import (
    UserTier, LLMResponse, ValidationStatus, InferenceResponse
)
from api.services.llm.router import ModelRouter
from api.services.llm.inference import InferenceClient
from api.services.llm.validator import OutputValidator
from api.services.llm.cache import semantic_cache
from api.services.llm.rag import rag_service
from api.services.llm.streaming import StreamingService
from api.services.llm.security import PromptInjectionGuard
from api.services.llm.prompt_builder import PromptBuilder
from api.services.llm.deterministic_fallback import DeterministicFallback
from api.services.llm.metrics import llm_metrics
from api.services.llm.providers.base_provider import BaseLLMProvider

logger = logging.getLogger(__name__)


class AIOrchestrator:
    """
    Central AI pipeline coordinator.
    """

    def __init__(self, default_provider: Optional[BaseLLMProvider] = None):
        self.router = ModelRouter()
        self._default_provider = default_provider

    async def execute(
        self,
        task: str,
        context_data: Dict[str, Any],
        user_message: str = "",
        user_tier: UserTier = UserTier.FREE,
        bypass_cache: bool = False,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Full pipeline execution returning a legacy-compatible dict.
        """
        start_time = time.time()

        # ── Step 0: Sanitize user input ────────────────────────────────
        if user_message:
            user_message = PromptInjectionGuard.sanitize(user_message)

        # ── Step 1: Build prompts ──────────────────────────────────────
        system_prompt, user_prompt, prompt_ver = PromptBuilder.build_prompt(
            task=task,
            context_data=context_data,
            user_message=user_message,
            tighter_constraints=False
        )

        # ── Step 2: RAG retrieval (chat/recommendation tasks only) ─────
        if task in ("chat", "recommendations") and user_message:
            rag_context = rag_service.query_text(user_message, top_k=2)
            if rag_context:
                user_prompt += f"\n\nRelevant Knowledge Base:\n{rag_context}"

        # ── Step 3: Check cache ────────────────────────────────────────
        model_id = "auto"
        if not bypass_cache:
            cached = semantic_cache.get(task, context_data, model_id, prompt_ver)
            if cached:
                cached.setdefault("metadata", {})["cache_hit"] = True
                return cached

        # ── Step 4: Resolve model chain ────────────────────────────────
        if self._default_provider:
            # Use injected provider (e.g. MockLLMProvider in tests)
            chain = [(None, self._default_provider)]
        else:
            chain = self.router.resolve_chain(user_tier=user_tier)

        # ── Step 5: 4-Step Failover Cascade ────────────────────────────
        generated_text = ""
        is_valid = False
        val_errors = []
        retry_count = 0
        provider_used = ""
        model_used = ""

        for position, (selection, provider) in enumerate(chain):
            provider_name = provider.__class__.__name__
            model_name = provider.model

            # Skip unavailable providers (but always try mock)
            if provider_name != "MockLLMProvider" and not provider.is_available():
                logger.info(f"Orchestrator: skipping unavailable provider '{provider_name}'")
                continue

            # ── Attempt 1: Normal inference ────────────────────────────
            try:
                inference_resp = await InferenceClient.infer(
                    provider=provider,
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                    temperature=0.2,
                    **kwargs
                )
                generated_text = inference_resp.raw_text
                provider_used = inference_resp.provider
                model_used = inference_resp.model

                if task == "ocr":
                    try:
                        json.loads(generated_text)
                        is_valid = True
                    except Exception as je:
                        is_valid = False
                        val_errors.append(f"Invalid OCR JSON: {je}")
                else:
                    result = OutputValidator.validate(generated_text, context_data, task)
                    is_valid = result.is_valid
                    val_errors = result.errors

                if is_valid:
                    break

            except Exception as e:
                logger.warning(f"Orchestrator: attempt 1 with '{provider_name}' failed: {e}")
                val_errors.append(str(e))

            # ── Attempt 2: Guardrail retry (temp=0, strict) ────────────
            if not is_valid and provider.is_available():
                retry_count += 1
                llm_metrics.record_retry()
                logger.info(f"Orchestrator: guardrail retry with '{provider_name}' (temp=0)")

                retry_sys, retry_user, _ = PromptBuilder.build_prompt(
                    task=task,
                    context_data=context_data,
                    user_message=user_message,
                    tighter_constraints=True
                )
                try:
                    inference_resp = await InferenceClient.infer(
                        provider=provider,
                        prompt=retry_user,
                        system_prompt=retry_sys,
                        temperature=0.0,
                        **kwargs
                    )
                    generated_text = inference_resp.raw_text
                    provider_used = inference_resp.provider
                    model_used = inference_resp.model

                    if task == "ocr":
                        try:
                            json.loads(generated_text)
                            is_valid = True
                        except Exception:
                            is_valid = False
                    else:
                        result = OutputValidator.validate(generated_text, context_data, task)
                        is_valid = result.is_valid
                        val_errors = result.errors

                    if is_valid:
                        break

                except Exception as e:
                    logger.warning(f"Orchestrator: guardrail retry with '{provider_name}' failed: {e}")
                    val_errors.append(str(e))

            # If this was a cloud failover attempt and it failed, continue to next
            if not is_valid:
                logger.info(f"Orchestrator: '{provider_name}' exhausted, trying next fallback")

        # ── Step 6: Deterministic Template Fallback ────────────────────
        fallback_used = False
        fallback_reason = None
        if not is_valid:
            fallback_reason = f"All providers exhausted. Errors: {'; '.join(val_errors[:3])}"
            logger.warning(f"Orchestrator: falling back to deterministic template. Reason: {fallback_reason}")
            generated_text = DeterministicFallback.get_fallback(task, context_data, user_message)
            fallback_used = True
            provider_used = "DeterministicFallback"
            model_used = "template"
            llm_metrics.record_fallback()

        if not is_valid and not fallback_used:
            llm_metrics.record_validation_failure()

        # ── Step 7: Build response ─────────────────────────────────────
        latency_ms = round((time.time() - start_time) * 1000, 2)

        response = LLMResponse(
            success=True,
            provider=provider_used,
            model=model_used,
            latency_ms=latency_ms,
            cache_hit=False,
            validation_status=ValidationStatus.PASSED if (is_valid or fallback_used) else ValidationStatus.FAILED,
            retry_count=retry_count,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            response_text=generated_text,
            warnings=val_errors if not is_valid and not fallback_used else [],
            prompt_version=prompt_ver
        )

        legacy_dict = response.to_legacy_dict()

        # ── Step 8: Cache the result ───────────────────────────────────
        semantic_cache.set(task, context_data, model_id, prompt_ver, legacy_dict)

        return legacy_dict

    async def stream(
        self,
        task: str,
        context_data: Dict[str, Any],
        user_message: str = "",
        user_tier: UserTier = UserTier.FREE,
        **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        """
        Stream LLM response tokens via the first available provider.
        Falls back to deterministic text if no provider is available.
        """
        system_prompt, user_prompt, _ = PromptBuilder.build_prompt(
            task=task,
            context_data=context_data,
            user_message=user_message
        )

        if self._default_provider:
            providers = [(None, self._default_provider)]
        else:
            providers = self.router.resolve_chain(user_tier=user_tier)

        for selection, provider in providers:
            if not provider.is_available():
                continue
            try:
                async for token in StreamingService.token_stream(
                    provider=provider,
                    prompt=user_prompt,
                    system_prompt=system_prompt
                ):
                    yield token
                return
            except Exception as e:
                logger.warning(f"Orchestrator stream: '{provider.__class__.__name__}' failed: {e}")
                continue

        # Final fallback
        llm_metrics.record_fallback()
        fallback_text = DeterministicFallback.get_fallback(task, context_data, user_message)
        yield fallback_text
