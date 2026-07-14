"""
Abstract base class for LLM Providers.
Supported actions: sync/async text generation and streaming.
"""
from abc import ABC, abstractmethod
from typing import AsyncGenerator, Dict, Any, Optional

class BaseLLMProvider(ABC):
    def __init__(self, model: str, base_url: Optional[str] = None):
        self.model = model
        self.base_url = base_url

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        **kwargs: Any
    ) -> str:
        """Generate a complete text response asynchronously."""
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
        """Check if provider daemon / service is online and reachable."""
        pass
