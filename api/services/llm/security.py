"""
Phase 2 Security — Secret Provider & Prompt Injection Guard.

SecretProvider reads API keys from environment variables or settings without hardcoding.
PromptInjectionGuard strips known prompt injection payloads from user chat queries.
"""
import os
import re
import logging
from typing import Optional
from config.settings import llm_settings

logger = logging.getLogger(__name__)

# ── Prompt Injection Patterns ──────────────────────────────────────────────

_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|rules?)",
    r"you\s+are\s+now\s+(a|an)\s+",
    r"forget\s+(everything|all|your)\s+",
    r"disregard\s+(all\s+)?(previous|above|prior)",
    r"system\s*prompt\s*:",
    r"<\s*system\s*>",
    r"</?\s*prompt\s*>",
    r"act\s+as\s+(a\s+)?different",
    r"override\s+(your|the)\s+(instructions?|rules?|guidelines?)",
    r"pretend\s+(you\s+are|to\s+be)\s+",
]

_COMPILED_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]


class PromptInjectionGuard:
    """Pre-inference sanitizer that strips prompt injection payloads from user queries."""

    @staticmethod
    def sanitize(user_input: str) -> str:
        """Remove detected injection patterns and return cleaned text."""
        if not user_input:
            return user_input

        cleaned = user_input
        for pattern in _COMPILED_PATTERNS:
            match = pattern.search(cleaned)
            if match:
                logger.warning(f"Prompt injection pattern detected and removed: '{match.group()}'")
                cleaned = pattern.sub("", cleaned)

        # Strip excessive whitespace after removal
        cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
        return cleaned

    @staticmethod
    def is_suspicious(user_input: str) -> bool:
        """Check if user input contains any suspicious injection patterns."""
        if not user_input:
            return False
        return any(pattern.search(user_input) for pattern in _COMPILED_PATTERNS)


class SecretProvider:
    """
    Credential provider reading API keys safely from environment or settings.
    Never returns hardcoded credentials. Falls back gracefully to empty string
    when a key is not configured — causing the corresponding provider's
    is_available() check to return False.
    """

    @staticmethod
    def get_anthropic_key() -> str:
        return os.environ.get("ANTHROPIC_API_KEY") or getattr(llm_settings, "anthropic_api_key", "") or ""

    @staticmethod
    def get_openai_key() -> str:
        return os.environ.get("OPENAI_API_KEY") or getattr(llm_settings, "openai_api_key", "") or ""

    @staticmethod
    def get_gemini_key() -> str:
        return os.environ.get("GEMINI_API_KEY") or getattr(llm_settings, "gemini_api_key", "") or ""

    @staticmethod
    def get_vllm_url() -> str:
        return os.environ.get("VLLM_BASE_URL") or getattr(llm_settings, "vllm_base_url", "") or ""

    @staticmethod
    def get_sglang_url() -> str:
        return os.environ.get("SGLANG_BASE_URL") or getattr(llm_settings, "sglang_base_url", "") or ""

    @staticmethod
    def get_ollama_url() -> str:
        return os.environ.get("OLLAMA_BASE_URL") or getattr(llm_settings, "base_url", "http://127.0.0.1:11434")

    @classmethod
    def get_key(cls, provider_name: str) -> str:
        """Generic credential lookup by provider name."""
        lookup = {
            "claude": cls.get_anthropic_key,
            "anthropic": cls.get_anthropic_key,
            "gpt": cls.get_openai_key,
            "openai": cls.get_openai_key,
            "gemini": cls.get_gemini_key,
            "google": cls.get_gemini_key,
        }
        getter = lookup.get(provider_name.lower())
        if getter:
            return getter()
        return ""
