"""
Phase 2 AI Data Contracts — Strongly Typed Pydantic Schemas.
Enforces explicit type safety at every module boundary in the AI pipeline:
    AnalyticsResult -> PromptRequest -> ModelSelection -> InferenceResponse -> ValidationResult -> LLMResponse

Every schema is immutable at runtime (frozen=True where appropriate) to prevent
accidental mutation of pipeline state between stages.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class UserTier(str, Enum):
    """User subscription tier determining model routing priority."""
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class ValidationStatus(str, Enum):
    """Output validator verdict."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


# ── Prompt Stage ────────────────────────────────────────────────────────────

class PromptMetadata(BaseModel):
    """Versioned metadata attached to every prompt template."""
    prompt_id: str = Field(..., description="Unique template identifier, e.g. 'bill_explanation_v2'")
    prompt_version: str = Field("1.0.0", description="Semver version string")
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO-8601 creation timestamp"
    )
    created_by: str = Field("system", description="Author or system identifier")
    supported_models: List[str] = Field(default_factory=list, description="List of validated model IDs")
    required_fields: List[str] = Field(default_factory=list, description="Mandatory AnalyticsResult keys")


class PromptRequest(BaseModel):
    """Contract passed from AIOrchestrator to PromptBuilder."""
    task_id: str = Field(..., description="Task type identifier (bill_analysis, impact, forecast, …)")
    analytics_hash: str = Field("", description="SHA-256 of AnalyticsResult.bill_hash for cache keying")
    prompt_version: str = Field("1.0.0", description="Prompt template version")
    user_tier: UserTier = Field(UserTier.FREE, description="Subscription tier for model routing")
    context_data: Dict[str, Any] = Field(default_factory=dict, description="Structured analytics context")
    rag_context: str = Field("", description="Retrieved tariff/policy text from RAG engine")
    user_message: str = Field("", description="Free-text user query for chat tasks")


# ── Model Selection Stage ──────────────────────────────────────────────────

class ModelMetadata(BaseModel):
    """Capability metadata for a registered LLM provider/model pair."""
    model_id: str = Field(..., description="Unique model identifier, e.g. 'claude-3-5-sonnet-20241022'")
    provider_name: str = Field(..., description="Provider class name, e.g. 'ClaudeProvider'")
    supports_streaming: bool = Field(True, description="Whether provider supports token streaming")
    supports_json: bool = Field(True, description="Whether provider supports structured JSON output mode")
    context_window: int = Field(4096, description="Maximum input token context window")
    priority: int = Field(50, description="Routing priority (lower = higher priority)")
    estimated_latency_ms: float = Field(500.0, description="Expected median inference latency (ms)")
    estimated_cost_per_1k: float = Field(0.0, description="Estimated cost per 1K output tokens (USD)")
    tier: UserTier = Field(UserTier.FREE, description="Minimum user tier required to access this model")


class ModelSelection(BaseModel):
    """Result of ModelRouter selecting the best available model."""
    model_id: str
    provider_name: str
    tier: UserTier
    fallback_position: int = Field(0, description="0 = primary, 1 = first fallback, 2 = second, etc.")


# ── Inference Stage ────────────────────────────────────────────────────────

class InferenceResponse(BaseModel):
    """Raw output from a provider inference call."""
    raw_text: str = Field("", description="Raw generated text from LLM")
    model: str = Field("", description="Model identifier used for generation")
    provider: str = Field("", description="Provider class name")
    prompt_tokens: int = Field(0, description="Input prompt token count")
    completion_tokens: int = Field(0, description="Output completion token count")
    latency_ms: float = Field(0.0, description="Inference latency in milliseconds")


# ── Validation Stage ──────────────────────────────────────────────────────

class ValidationResult(BaseModel):
    """7-point output validator audit result."""
    is_valid: bool = Field(True, description="Overall pass/fail verdict")
    numeric_discrepancies: List[str] = Field(default_factory=list, description="Numbers not in AnalyticsResult")
    missing_fields: List[str] = Field(default_factory=list, description="Required fields absent from output")
    json_errors: List[str] = Field(default_factory=list, description="JSON structure violations")
    tone_violations: List[str] = Field(default_factory=list, description="Professional tone violations")
    errors: List[str] = Field(default_factory=list, description="All validation errors aggregated")
    retry_recommended: bool = Field(False, description="Whether a guardrail retry should be attempted")


# ── Final Response ─────────────────────────────────────────────────────────

class LLMResponse(BaseModel):
    """Strongly typed final response contract returned to API routes and frontend."""
    success: bool = Field(True, description="Whether generation succeeded")
    provider: str = Field("", description="Provider that generated the response")
    model: str = Field("", description="Model that generated the response")
    latency_ms: float = Field(0.0, description="Total end-to-end latency in milliseconds")
    prompt_tokens: int = Field(0, description="Input tokens consumed")
    completion_tokens: int = Field(0, description="Output tokens generated")
    cache_hit: bool = Field(False, description="Whether response was served from cache")
    validation_status: ValidationStatus = Field(ValidationStatus.PASSED, description="Validation verdict")
    retry_count: int = Field(0, description="Number of retry attempts executed")
    fallback_used: bool = Field(False, description="Whether deterministic fallback was used")
    fallback_reason: Optional[str] = Field(None, description="Reason for fallback activation")
    response_text: str = Field("", description="Final generated natural language text")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings")
    prompt_version: str = Field("1.0.0", description="Prompt template version used")

    # Backward-compatible dict conversion
    def to_legacy_dict(self) -> Dict[str, Any]:
        """Convert to legacy dict format expected by existing API routes."""
        return {
            "success": self.success,
            "text": self.response_text,
            "explanation": self.response_text,
            "answer": self.response_text,
            "metadata": {
                "model": self.model,
                "provider": self.provider,
                "prompt_version": self.prompt_version,
                "validated": self.validation_status == ValidationStatus.PASSED,
                "cache_hit": self.cache_hit,
                "fallback_used": self.fallback_used,
                "fallback_reason": self.fallback_reason,
                "latency_ms": self.latency_ms,
                "validation_errors": self.warnings,
                "generated_at": datetime.now(timezone.utc).isoformat()
            }
        }
