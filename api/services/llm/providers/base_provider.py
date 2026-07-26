"""
Abstract Base Class for modular LLM providers in Phase 2.
"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any, Optional

class BaseLLMProvider(ABC):
    def __init__(self, model: str = "default", base_url: Optional[str] = None, api_key: Optional[str] = None):
        self.model = model
        self.base_url = base_url
        self.api_key = api_key

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        **kwargs: Any
    ) -> str:
        """Generate complete text response asynchronously."""
        pass

    @abstractmethod
    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        """Stream response tokens asynchronously."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider endpoint or API key is accessible and available."""
        pass
