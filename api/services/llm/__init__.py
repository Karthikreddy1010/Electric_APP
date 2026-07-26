"""
Phase 2 — Centralized LLM Package for ElectricAI.

Exports the backward-compatible facade (LLMService, llm_service) alongside
all new Phase 2 modules. Every Phase 1 import path is preserved.
"""
# ── Phase 1 Backward Compatibility ─────────────────────────────────────────
from api.services.llm.llm_service import LLMService, llm_service
from api.services.llm.context_builder import ContextBuilder
from api.services.llm.response_validator import ResponseValidator
from api.services.llm.deterministic_fallback import DeterministicFallback
from api.services.llm.metadata import LLMResponseMetadata
from api.services.llm.cache_manager import LLMCacheManager, llm_cache

# ── Phase 2 New Modules ───────────────────────────────────────────────────
from api.services.llm.contracts import (
    UserTier, PromptRequest, ModelMetadata, InferenceResponse,
    ValidationResult, LLMResponse, ValidationStatus
)
from api.services.llm.orchestrator import AIOrchestrator
from api.services.llm.router import ModelRouter
from api.services.llm.model_registry import model_registry
from api.services.llm.inference import InferenceClient
from api.services.llm.validator import OutputValidator
from api.services.llm.cache import SemanticCacheManager, semantic_cache
from api.services.llm.streaming import StreamingService
from api.services.llm.rag import RAGService, rag_service
from api.services.llm.security import SecretProvider, PromptInjectionGuard

__all__ = [
    # Phase 1 backward compat
    "LLMService", "llm_service",
    "ContextBuilder", "ResponseValidator", "DeterministicFallback",
    "LLMResponseMetadata", "LLMCacheManager", "llm_cache",
    # Phase 2
    "UserTier", "PromptRequest", "ModelMetadata", "InferenceResponse",
    "ValidationResult", "LLMResponse", "ValidationStatus",
    "AIOrchestrator", "ModelRouter", "model_registry",
    "InferenceClient", "OutputValidator",
    "SemanticCacheManager", "semantic_cache",
    "StreamingService", "RAGService", "rag_service",
    "SecretProvider", "PromptInjectionGuard",
]
