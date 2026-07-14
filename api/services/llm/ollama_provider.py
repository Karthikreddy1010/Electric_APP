"""
Ollama LLM Provider implementation.
Reads configuration dynamically from settings/env vars.
Does not hardcode specific model names or hosts.
"""
import socket
import json
import logging
from typing import AsyncGenerator, Optional, Any
from urllib.parse import urlparse

import httpx
from api.services.llm.base_provider import BaseLLMProvider
from config.settings import llm_settings

logger = logging.getLogger(__name__)

class OllamaProvider(BaseLLMProvider):
    def __init__(self, model: Optional[str] = None, base_url: Optional[str] = None):
        configured_model = model or getattr(llm_settings, "model", "qwen3:8b")
        configured_url = base_url or getattr(llm_settings, "base_url", "http://127.0.0.1:11434")
        super().__init__(model=configured_model, base_url=configured_url)

    def _check_socket(self) -> bool:
        try:
            parsed = urlparse(self.base_url)
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or 11434
            with socket.create_connection((host, port), timeout=0.8):
                return True
        except Exception:
            return False

    def is_available(self) -> bool:
        return self._check_socket()

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        **kwargs: Any
    ) -> str:
        if not self.is_available():
            raise RuntimeError(f"Ollama server is unavailable at {self.base_url}")

        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt or "",
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        url = f"{self.base_url.rstrip('/')}/api/generate"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(f"Ollama returned HTTP {resp.status_code}: {resp.text}")
            data = resp.json()
            return data.get("response", "").strip()

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1500,
        **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        if not self.is_available():
            raise RuntimeError(f"Ollama server is unavailable at {self.base_url}")

        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt or "",
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        url = f"{self.base_url.rstrip('/')}/api/generate"
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    raise RuntimeError(f"Ollama streaming returned HTTP {response.status_code}")
                async for line in response.aiter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            token = chunk.get("response", "")
                            if token:
                                yield token
                        except Exception:
                            continue
