"""
Mock LLM Provider for unit testing and deterministic simulation mode.
Does not require any network connection or background Ollama process.
"""
from typing import AsyncGenerator, Optional, Any
from api.services.llm.base_provider import BaseLLMProvider

class MockLLMProvider(BaseLLMProvider):
    def __init__(self, model: str = "mock-model", base_url: Optional[str] = None):
        super().__init__(model=model, base_url=base_url)

    def is_available(self) -> bool:
        return True

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        **kwargs: Any
    ) -> str:
        # Check if RAG context was retrieved and injected into prompt
        if "Relevant Knowledge Base:" in prompt:
            kb_part = prompt.split("Relevant Knowledge Base:")[1].split("\n\nData Source Notes:")[0].strip()
            return f"Based on verified state energy documentation:\n\n{kb_part}"

        user_lower = prompt.lower()
        if "clean energy" in user_lower or "incentive" in user_lower or "policy" in user_lower:
            return "Under the New Jersey Clean Energy Act, 50% renewable energy is mandated by 2030 and 100% clean energy by 2050. Key customer incentives include net metering for solar generation, community solar subscription credits, energy storage incentives, and utility rebates for ENERGY STAR efficiency upgrades."

        if "User Question:" in prompt or "Task: Act as an interactive AI Copilot" in (system_prompt or ""):
            from api.services.llm.deterministic_fallback import DeterministicFallback
            user_msg = ""
            if "User Question:" in prompt:
                user_msg = prompt.split("User Question:")[1].split("\n")[0].strip()
            return DeterministicFallback.generate_chat_fallback({}, user_msg)

        return (
            "### Executive Summary\n"
            "This is a validated mock response generated for testing purposes. "
            "All numbers match the structured data precisely.\n"
        )

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        tokens = [
            "### Executive Summary\n",
            "This is a validated ",
            "mock response generated ",
            "for testing purposes.\n"
        ]
        for t in tokens:
            yield t
