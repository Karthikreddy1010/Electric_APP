"""
Phase 2 — Mock LLM Provider adapter for the providers/ package.
Re-exports the existing MockLLMProvider for consistent package imports.
"""
from api.services.llm.mock_provider import MockLLMProvider

__all__ = ["MockLLMProvider"]
