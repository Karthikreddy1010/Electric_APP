"""
Phase 2 — Model Router & Tier Routing Policy.

Selects the best available model for a given user tier, builds the deterministic
fallback chain, and instantiates provider instances on demand.

Design rationale: Centralizing model selection in a Router (rather than in LLMService)
keeps provider instantiation, availability checks, and tier policy in a single
maintainable location. The Router never performs inference — it only resolves
which provider + model to use and returns a fallback-ordered list.
"""
import logging
from typing import List, Optional
from api.services.llm.contracts import UserTier, ModelSelection, ModelMetadata
from api.services.llm.model_registry import model_registry
from api.services.llm.providers.base_provider import BaseLLMProvider
from api.services.llm.providers.vllm_provider import VLLMProvider
from api.services.llm.providers.sglang_provider import SGLangProvider
from api.services.llm.providers.claude_provider import ClaudeProvider
from api.services.llm.providers.gpt_provider import GPTProvider
from api.services.llm.providers.gemini_provider import GeminiProvider
from api.services.llm.mock_provider import MockLLMProvider
from api.services.llm.ollama_provider import OllamaProvider
from api.services.llm.security import SecretProvider
from config.settings import llm_settings

logger = logging.getLogger(__name__)

# Provider class name -> factory function
_PROVIDER_FACTORIES = {
    "VLLMProvider": lambda meta: VLLMProvider(model=meta.model_id, base_url=SecretProvider.get_vllm_url()),
    "SGLangProvider": lambda meta: SGLangProvider(model=meta.model_id, base_url=SecretProvider.get_sglang_url()),
    "ClaudeProvider": lambda meta: ClaudeProvider(model=meta.model_id, api_key=SecretProvider.get_anthropic_key()),
    "GPTProvider": lambda meta: GPTProvider(model=meta.model_id, api_key=SecretProvider.get_openai_key()),
    "GeminiProvider": lambda meta: GeminiProvider(model=meta.model_id, api_key=SecretProvider.get_gemini_key()),
    "OllamaProvider": lambda meta: OllamaProvider(model=meta.model_id, base_url=SecretProvider.get_ollama_url()),
    "MockLLMProvider": lambda meta: MockLLMProvider(model=meta.model_id),
}


class ModelRouter:
    """
    Resolves the best available model for a given user tier and returns an ordered
    fallback chain of (ModelSelection, BaseLLMProvider) pairs.

    Fallback Priority:
        1. Local vLLM / SGLang / Ollama (if available)
        2. Cloud API (Claude / GPT / Gemini — based on tier)
        3. MockLLMProvider (always available, will be caught by Orchestrator
           and replaced with deterministic template fallback)
    """

    def __init__(self):
        self.registry = model_registry

    def resolve_chain(
        self,
        user_tier: UserTier = UserTier.FREE,
        require_streaming: bool = False,
        require_json: bool = False,
    ) -> List[tuple]:
        """
        Returns an ordered list of (ModelSelection, BaseLLMProvider) tuples.
        Each entry is a fallback candidate sorted by priority.
        The last entry is always the MockLLMProvider (deterministic fallback safety net).
        """
        candidates = self.registry.list_models(tier=user_tier)

        # Apply capability filters
        if require_streaming:
            candidates = [m for m in candidates if m.supports_streaming]
        if require_json:
            candidates = [m for m in candidates if m.supports_json]

        # Exclude mock from main candidates — it will be appended at the end
        candidates = [m for m in candidates if m.provider_name != "MockLLMProvider"]

        chain = []
        for position, meta in enumerate(candidates):
            provider = self._instantiate(meta)
            if provider is not None and provider.is_available():
                selection = ModelSelection(
                    model_id=meta.model_id,
                    provider_name=meta.provider_name,
                    tier=meta.tier,
                    fallback_position=position
                )
                chain.append((selection, provider))

        # Always append mock as final safety net
        mock_meta = self.registry.get("mock-model")
        if mock_meta:
            mock_provider = MockLLMProvider(model="mock-model")
            mock_selection = ModelSelection(
                model_id="mock-model",
                provider_name="MockLLMProvider",
                tier=UserTier.FREE,
                fallback_position=len(chain)
            )
            chain.append((mock_selection, mock_provider))

        logger.info(
            f"ModelRouter resolved {len(chain)} candidates for tier={user_tier.value}: "
            f"{[s.model_id for s, _ in chain]}"
        )
        return chain

    def _instantiate(self, meta: ModelMetadata) -> Optional[BaseLLMProvider]:
        """Instantiate a provider from registry metadata using the factory map."""
        factory = _PROVIDER_FACTORIES.get(meta.provider_name)
        if factory is None:
            logger.warning(f"No factory registered for provider '{meta.provider_name}'")
            return None
        try:
            return factory(meta)
        except Exception as e:
            logger.warning(f"Failed to instantiate provider '{meta.provider_name}': {e}")
            return None
