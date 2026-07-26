"""
vLLM Local Inference Provider.
Exposes OpenAI-compatible vLLM API (/v1/chat/completions) with async streaming support.
"""
import logging
import httpx
from typing import AsyncGenerator, Dict, Any, Optional
from api.services.llm.providers.base_provider import BaseLLMProvider
from config.settings import llm_settings

logger = logging.getLogger(__name__)

class VLLMProvider(BaseLLMProvider):
    def __init__(self, model: Optional[str] = None, base_url: Optional[str] = None):
        model_name = model or llm_settings.free_tier_model
        url = base_url or llm_settings.vllm_base_url
        super().__init__(model=model_name, base_url=url)
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=llm_settings.connect_timeout,
                    read=llm_settings.read_timeout,
                    write=llm_settings.write_timeout,
                    pool=llm_settings.total_timeout
                )
            )
        return self._client

    def is_available(self) -> bool:
        if not self.base_url:
            return False
        try:
            with httpx.Client(timeout=2.0) as client:
                res = client.get(f"{self.base_url.rstrip('/')}/models")
                return res.status_code == 200
        except Exception:
            return False

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        **kwargs: Any
    ) -> str:
        client = self._get_client()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        try:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"vLLM generation error: {e}")
            raise RuntimeError(f"vLLM generation failed: {e}")

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        client = self._get_client()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True
        }

        url = f"{self.base_url.rstrip('/')}/chat/completions"
        try:
            async with client.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:].strip()
                        if data_str == "[DONE]":
                            break
                        import json
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk["choices"][0]["delta"].get("content", "")
                            if delta:
                                yield delta
                        except Exception:
                            continue
        except Exception as e:
            logger.error(f"vLLM stream error: {e}")
            raise RuntimeError(f"vLLM stream failed: {e}")
