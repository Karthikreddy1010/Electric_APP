"""
Phase 2 — Ollama Provider adapter for new provider base class.
Wraps the existing production-grade OllamaProvider from Phase 1 into the Phase 2
providers/ package interface for backward compatibility while maintaining all existing
retry logic, metrics, and telemetry.
"""
from typing import AsyncGenerator, Optional, Any
from api.services.llm.providers.base_provider import BaseLLMProvider

# Re-export the existing production OllamaProvider from its original location.
# This file exists so that `api.services.llm.providers.ollama_provider` resolves
# cleanly alongside the other Phase 2 providers, while all logic remains in the
# Phase 1 module that tests and background_worker already import.
from api.services.llm.ollama_provider import OllamaProvider

__all__ = ["OllamaProvider"]
