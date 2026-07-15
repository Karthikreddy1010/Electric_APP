"""
Ollama LLM Provider implementation.
Production-ready, persistent connection pooling, exponential backoff, pre-flight model validation,
full structured exception logging, and telemetry metrics tracking.
"""
import asyncio
import hashlib
import json
import logging
import socket
import time
import traceback
from typing import AsyncGenerator, Optional, Any, Dict, List
from urllib.parse import urlparse

import httpx
from api.services.llm.base_provider import BaseLLMProvider
from api.services.llm.metrics import llm_metrics
from config.settings import llm_settings

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMProvider):
    _client_instance: Optional[httpx.AsyncClient] = None

    def __init__(self, model: Optional[str] = None, base_url: Optional[str] = None):
        configured_model = model or getattr(llm_settings, "model", "qwen3:4b")
        configured_url = base_url or getattr(llm_settings, "base_url", "http://127.0.0.1:11434")
        super().__init__(model=configured_model, base_url=configured_url)
        
        self.connect_timeout = float(getattr(llm_settings, "connect_timeout", 5.0))
        self.read_timeout = float(getattr(llm_settings, "read_timeout", 30.0))
        self.write_timeout = float(getattr(llm_settings, "write_timeout", 10.0))
        self.total_timeout = float(getattr(llm_settings, "total_timeout", 45.0))
        self.max_retries = int(getattr(llm_settings, "max_retries", 2))
        self.backoff_factor = float(getattr(llm_settings, "backoff_factor", 1.5))

    def _get_timeout_config(self) -> httpx.Timeout:
        return httpx.Timeout(
            connect=self.connect_timeout,
            read=self.read_timeout,
            write=self.write_timeout,
            pool=self.total_timeout
        )

    @classmethod
    def get_client(cls) -> httpx.AsyncClient:
        if cls._client_instance is None or cls._client_instance.is_closed:
            limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
            cls._client_instance = httpx.AsyncClient(limits=limits)
        return cls._client_instance

    @classmethod
    async def close_client(cls):
        if cls._client_instance and not cls._client_instance.is_closed:
            await cls._client_instance.aclose()
            cls._client_instance = None

    @staticmethod
    def compute_prompt_hash(prompt: str) -> str:
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]

    def _check_socket(self) -> bool:
        try:
            parsed = urlparse(self.base_url)
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or 11434
            with socket.create_connection((host, port), timeout=2.0):
                return True
        except Exception:
            return False

    def is_available(self) -> bool:
        return self._check_socket()

    async def is_model_available(self) -> bool:
        """
        Queries GET /api/tags to check if the configured model exists on Ollama server.
        """
        if not self.is_available():
            return False
        
        url = f"{self.base_url.rstrip('/')}/api/tags"
        try:
            client = self.get_client()
            resp = await client.get(url, timeout=httpx.Timeout(4.0))
            if resp.status_code == 200:
                data = resp.json()
                models = [m.get("name", "").lower() for m in data.get("models", [])]
                target = self.model.lower()
                target_base = target.split(":")[0]
                for m in models:
                    if m == target or target_base in m:
                        return True
                logger.warning(f"Ollama server is active, but model '{self.model}' was not found in tags: {models}")
                return False
            return False
        except Exception as e:
            logger.warning(f"Pre-flight model check failed for URL {url}: {e}")
            return False

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 500,
        **kwargs: Any
    ) -> str:
        if not prompt or not prompt.strip():
            raise ValueError("LLM generate requested with empty prompt.")

        temp_val = max(0.0, min(1.0, float(temperature)))
        num_predict = max(1, int(max_tokens))
        prompt_hash = self.compute_prompt_hash(prompt)
        url = f"{self.base_url.rstrip('/')}/api/generate"

        llm_metrics.record_request_start()

        if not self.is_available():
            err_msg = f"Ollama server is unreachable at {self.base_url}"
            llm_metrics.record_failure("ServerUnavailable", err_msg, url, prompt_hash)
            raise RuntimeError(err_msg)

        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt or "",
            "stream": False,
            "options": {
                "temperature": temp_val,
                "num_predict": num_predict
            }
        }
        if kwargs.get("format") == "json":
            payload["format"] = "json"

        timeout_cfg = self._get_timeout_config()
        attempt = 0
        start_time = time.time()

        while attempt <= self.max_retries:
            attempt += 1
            attempt_start = time.time()

            logger.info(
                f"[Ollama Call] Attempt {attempt}/{self.max_retries + 1} | Model: {self.model} | "
                f"Endpoint: {url} | Prompt Length: {len(prompt)} | Hash: {prompt_hash} | "
                f"Timeout Config: connect={self.connect_timeout}s, read={self.read_timeout}s"
            )

            try:
                client = self.get_client()
                resp = await client.post(url, json=payload, timeout=timeout_cfg)
                elapsed_attempt = time.time() - attempt_start

                logger.info(
                    f"[Ollama Response] HTTP {resp.status_code} | Size: {len(resp.content)} bytes | "
                    f"Attempt Time: {elapsed_attempt * 1000:.2f}ms"
                )

                if resp.status_code == 404:
                    err_msg = f"Ollama model '{self.model}' not found (HTTP 404): {resp.text[:200]}"
                    llm_metrics.record_failure("ModelNotFound", err_msg, url, prompt_hash)
                    raise RuntimeError(err_msg)

                if resp.status_code != 200:
                    body_snippet = resp.text[:500]
                    raise RuntimeError(
                        f"Ollama returned unexpected status HTTP {resp.status_code}: {body_snippet}"
                    )

                try:
                    data = resp.json()
                except Exception as parse_err:
                    body_snippet = resp.text[:500]
                    raise ValueError(f"Malformed JSON returned by Ollama: {parse_err}. Content: {body_snippet}")

                response_text = data.get("response", "")
                if response_text is None:
                    response_text = ""
                response_text = response_text.strip()

                if not response_text:
                    logger.warning(f"Ollama returned empty response string for prompt hash {prompt_hash}")

                total_duration = time.time() - start_time
                latency_ms = total_duration * 1000.0
                prompt_tokens = data.get("prompt_eval_count", 0) or 0
                eval_tokens = data.get("eval_count", 0) or 0

                llm_metrics.record_success(latency_ms, prompt_tokens=prompt_tokens, eval_tokens=eval_tokens)

                logger.info(
                    f"✓ [Ollama Success] Hash: {prompt_hash} | Latency: {latency_ms:.2f}ms | "
                    f"Prompt Tokens: {prompt_tokens} | Eval Tokens: {eval_tokens}"
                )
                return response_text

            except Exception as e:
                elapsed_attempt = time.time() - attempt_start
                total_elapsed = time.time() - start_time
                is_read_timeout = isinstance(e, httpx.ReadTimeout)
                is_transient = (isinstance(e, (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError)) or \
                               ("status HTTP 5" in str(e))) and not is_read_timeout

                logger.error(
                    "================================================================================\n"
                    f"❌ Ollama Generation Failure [Attempt {attempt}/{self.max_retries + 1}]\n"
                    f"Exception Type   : {type(e).__name__}\n"
                    f"Exception Message: {str(e)}\n"
                    f"URL              : {url}\n"
                    f"HTTP Method      : POST\n"
                    f"Model            : {self.model}\n"
                    f"Prompt Hash      : {prompt_hash}\n"
                    f"Prompt Length    : {len(prompt)} chars\n"
                    f"Attempt Latency  : {elapsed_attempt:.3f}s\n"
                    f"Total Elapsed    : {total_elapsed:.3f}s\n"
                    f"Transient Error  : {is_transient} (ReadTimeout: {is_read_timeout})\n"
                    f"Traceback:\n{traceback.format_exc()}"
                    "================================================================================="
                )

                if is_read_timeout:
                    logger.warning(
                        f"ReadTimeout reached ({self.read_timeout}s). Failing fast to deterministic fallback "
                        f"to prevent blocking the client for multiple retry cycles."
                    )
                    llm_metrics.record_failure("ReadTimeout", f"Inference exceeded {self.read_timeout}s timeout", url, prompt_hash)
                    raise RuntimeError(f"Ollama generation exceeded {self.read_timeout}s read timeout.") from e

                if not is_transient or attempt > self.max_retries:
                    llm_metrics.record_failure(type(e).__name__, str(e), url, prompt_hash)
                    raise RuntimeError(f"Ollama generation failed after {attempt} attempts: {e}") from e

                backoff_delay = self.backoff_factor * (2 ** (attempt - 1))
                llm_metrics.record_retry()
                logger.info(f"Retrying transient Ollama failure in {backoff_delay:.2f}s...")
                await asyncio.sleep(backoff_delay)

        raise RuntimeError("Ollama generation retries exhausted.")

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 500,
        **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        if not prompt or not prompt.strip():
            raise ValueError("LLM generate_stream requested with empty prompt.")

        if not self.is_available():
            raise RuntimeError(f"Ollama server is unavailable at {self.base_url}")

        prompt_hash = self.compute_prompt_hash(prompt)
        url = f"{self.base_url.rstrip('/')}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt or "",
            "stream": True,
            "options": {
                "temperature": max(0.0, min(1.0, float(temperature))),
                "num_predict": max(1, int(max_tokens))
            }
        }
        if kwargs.get("format") == "json":
            payload["format"] = "json"

        llm_metrics.record_request_start()
        start_time = time.time()
        timeout_cfg = self._get_timeout_config()

        logger.info(f"[Ollama Streaming] Hash: {prompt_hash} | Model: {self.model} | Endpoint: {url}")

        try:
            client = self.get_client()
            async with client.stream("POST", url, json=payload, timeout=timeout_cfg) as response:
                if response.status_code != 200:
                    raise RuntimeError(f"Ollama streaming returned HTTP status {response.status_code}")

                async for line in response.aiter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            token = chunk.get("response", "")
                            if token:
                                yield token
                        except Exception:
                            continue

            duration = time.time() - start_time
            llm_metrics.record_success(duration * 1000.0)
            logger.info(f"✓ [Ollama Streaming Finished] Hash: {prompt_hash} | Duration: {duration:.2f}s")
        except Exception as e:
            logger.error(
                f"Ollama Streaming Failed! Hash: {prompt_hash} | Exception: {e}\n{traceback.format_exc()}"
            )
            llm_metrics.record_failure(type(e).__name__, str(e), url, prompt_hash)
            raise
