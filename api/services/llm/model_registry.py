"""
Phase 2 — Enterprise Model Registry.

Registers all available provider/model pairs with their capability metadata.
The ModelRouter queries this registry to select the best model for a given
user tier and required capabilities.

Design rationale: Decoupling model metadata from provider instances allows
dynamic failover, cost-aware routing, and capability-based filtering without
modifying provider code.
"""
import logging
from typing import Dict, List, Optional
from api.services.llm.contracts import ModelMetadata, UserTier
from api.services.llm.security import SecretProvider

logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Central catalog of all registered LLM models with their provider metadata,
    capability flags, and tier requirements.
    """

    def __init__(self):
        self._models: Dict[str, ModelMetadata] = {}
        self._register_defaults()

    def _register_defaults(self):
        """Register all built-in providers with default capability metadata."""

        # ── Local Providers (Free / Pro tier) ──────────────────────────────
        self.register(ModelMetadata(
            model_id="vllm-local",
            provider_name="VLLMProvider",
            supports_streaming=True,
            supports_json=True,
            context_window=8192,
            priority=10,
            estimated_latency_ms=200.0,
            estimated_cost_per_1k=0.0,
            tier=UserTier.FREE
        ))

        self.register(ModelMetadata(
            model_id="sglang-local",
            provider_name="SGLangProvider",
            supports_streaming=True,
            supports_json=True,
            context_window=8192,
            priority=15,
            estimated_latency_ms=180.0,
            estimated_cost_per_1k=0.0,
            tier=UserTier.FREE
        ))

        self.register(ModelMetadata(
            model_id="ollama-local",
            provider_name="OllamaProvider",
            supports_streaming=True,
            supports_json=True,
            context_window=4096,
            priority=20,
            estimated_latency_ms=500.0,
            estimated_cost_per_1k=0.0,
            tier=UserTier.FREE
        ))

        # ── Cloud Providers (Pro / Enterprise tier) ────────────────────────
        self.register(ModelMetadata(
            model_id="gpt-4o-mini",
            provider_name="GPTProvider",
            supports_streaming=True,
            supports_json=True,
            context_window=128000,
            priority=30,
            estimated_latency_ms=800.0,
            estimated_cost_per_1k=0.15,
            tier=UserTier.PRO
        ))

        self.register(ModelMetadata(
            model_id="claude-3-haiku-20240307",
            provider_name="ClaudeProvider",
            supports_streaming=True,
            supports_json=True,
            context_window=200000,
            priority=35,
            estimated_latency_ms=600.0,
            estimated_cost_per_1k=0.25,
            tier=UserTier.PRO
        ))

        self.register(ModelMetadata(
            model_id="gpt-4o",
            provider_name="GPTProvider",
            supports_streaming=True,
            supports_json=True,
            context_window=128000,
            priority=40,
            estimated_latency_ms=1200.0,
            estimated_cost_per_1k=2.50,
            tier=UserTier.ENTERPRISE
        ))

        self.register(ModelMetadata(
            model_id="claude-3-5-sonnet-20241022",
            provider_name="ClaudeProvider",
            supports_streaming=True,
            supports_json=True,
            context_window=200000,
            priority=45,
            estimated_latency_ms=1000.0,
            estimated_cost_per_1k=3.00,
            tier=UserTier.ENTERPRISE
        ))

        self.register(ModelMetadata(
            model_id="gemini-1.5-pro",
            provider_name="GeminiProvider",
            supports_streaming=True,
            supports_json=True,
            context_window=2000000,
            priority=50,
            estimated_latency_ms=900.0,
            estimated_cost_per_1k=1.25,
            tier=UserTier.ENTERPRISE
        ))

        # ── Testing Provider ───────────────────────────────────────────────
        self.register(ModelMetadata(
            model_id="mock-model",
            provider_name="MockLLMProvider",
            supports_streaming=True,
            supports_json=False,
            context_window=4096,
            priority=999,
            estimated_latency_ms=1.0,
            estimated_cost_per_1k=0.0,
            tier=UserTier.FREE
        ))

    def register(self, metadata: ModelMetadata) -> None:
        """Register a model in the catalog."""
        self._models[metadata.model_id] = metadata
        logger.debug(f"ModelRegistry: registered '{metadata.model_id}' ({metadata.provider_name})")

    def get(self, model_id: str) -> Optional[ModelMetadata]:
        """Retrieve metadata for a specific model."""
        return self._models.get(model_id)

    def list_models(self, tier: Optional[UserTier] = None) -> List[ModelMetadata]:
        """Return registered models, optionally filtered by maximum tier."""
        models = list(self._models.values())
        if tier is not None:
            tier_order = {UserTier.FREE: 0, UserTier.PRO: 1, UserTier.ENTERPRISE: 2}
            max_level = tier_order.get(tier, 0)
            models = [m for m in models if tier_order.get(m.tier, 0) <= max_level]
        return sorted(models, key=lambda m: m.priority)

    def get_by_provider(self, provider_name: str) -> List[ModelMetadata]:
        """Return all models registered for a given provider class name."""
        return [m for m in self._models.values() if m.provider_name == provider_name]


# Global singleton
model_registry = ModelRegistry()
