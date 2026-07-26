"""
Phase 3 — Enterprise Secret Manager Abstraction.

Provides a pluggable interface for secret retrieval:
  - EnvironmentSecretProvider (default — reads from os.environ / .env)
  - VaultSecretProvider (HashiCorp Vault — interface-ready)

Centralizes all credential access behind a single SecretManager.get() call.
"""
import os
import logging
from abc import ABC, abstractmethod
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class SecretBackend(ABC):
    """Abstract secret backend interface."""

    @abstractmethod
    def get_secret(self, key: str) -> Optional[str]:
        ...

    @abstractmethod
    def list_secrets(self) -> list:
        ...


class EnvironmentSecretBackend(SecretBackend):
    """Reads secrets from environment variables and .env files."""

    def get_secret(self, key: str) -> Optional[str]:
        return os.environ.get(key)

    def list_secrets(self) -> list:
        secret_keys = [
            "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY",
            "DATABASE_URL", "REDIS_URL", "SECRET_KEY",
        ]
        return [k for k in secret_keys if os.environ.get(k)]


class VaultSecretBackend(SecretBackend):
    """
    HashiCorp Vault secret backend (interface-ready).
    Requires hvac package: pip install hvac
    """

    def __init__(self, vault_url: str = "", vault_token: str = "", mount_point: str = "secret"):
        self._vault_url = vault_url or os.environ.get("VAULT_ADDR", "http://localhost:8200")
        self._vault_token = vault_token or os.environ.get("VAULT_TOKEN", "")
        self._mount_point = mount_point
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import hvac
                self._client = hvac.Client(url=self._vault_url, token=self._vault_token)
                if not self._client.is_authenticated():
                    logger.error("Vault authentication failed")
                    self._client = None
            except ImportError:
                logger.warning("hvac not installed. Vault backend unavailable.")
        return self._client

    def get_secret(self, key: str) -> Optional[str]:
        client = self._get_client()
        if client is None:
            return os.environ.get(key)  # Fallback to env
        try:
            response = client.secrets.kv.v2.read_secret_version(path=key, mount_point=self._mount_point)
            data = response.get("data", {}).get("data", {})
            return data.get("value")
        except Exception as e:
            logger.warning(f"Vault secret retrieval failed for '{key}': {e}")
            return os.environ.get(key)

    def list_secrets(self) -> list:
        return []


class SecretManager:
    """
    Unified secret manager with pluggable backends and secret rotation support.
    """

    def __init__(self, backend: Optional[SecretBackend] = None):
        self._backend = backend or EnvironmentSecretBackend()

    def get(self, key: str, default: str = "") -> str:
        """Retrieve a secret by key, returning default if not found."""
        value = self._backend.get_secret(key)
        return value if value is not None else default

    def get_required(self, key: str) -> str:
        """Retrieve a required secret, raising if not found."""
        value = self._backend.get_secret(key)
        if value is None:
            raise ValueError(f"Required secret '{key}' not found")
        return value

    def set_secret(self, key: str, new_value: str) -> None:
        """Dynamically update a secret value in the active environment/backend."""
        os.environ[key] = new_value
        logger.info(f"SecretManager: Updated secret key '{key}'")

    def rotate_secret(self, key: str, new_value: str) -> str:
        """Rotate a secret key with a new value and return audit message."""
        old_val = self.get(key)
        self.set_secret(key, new_value)
        logger.info(f"SecretManager: Rotated secret key '{key}'")
        return f"Rotated '{key}' successfully"


# Global singleton
secret_manager = SecretManager()

