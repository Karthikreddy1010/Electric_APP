"""
Phase 2 — Modular Prompt Architecture: Base Module.

Provides versioned prompt metadata structures and the PromptTemplate base
contract used by all domain-specific prompt files.
"""
from typing import Dict, Any, List, Optional
from api.services.llm.contracts import PromptMetadata


class PromptTemplate:
    """Base container for a versioned prompt template with metadata."""

    def __init__(
        self,
        metadata: PromptMetadata,
        system_prompt: str,
        user_template: str
    ):
        self.metadata = metadata
        self.system_prompt = system_prompt
        self.user_template = user_template

    @property
    def prompt_id(self) -> str:
        return self.metadata.prompt_id

    @property
    def version(self) -> str:
        return self.metadata.prompt_version
