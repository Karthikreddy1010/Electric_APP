"""
Phase 3 — AI Gateway: Circuit Breaker.

Implements the circuit breaker pattern to prevent cascading failures
when downstream LLM providers or inference servers are unhealthy.

States:
  CLOSED  → Normal operation. Failures are counted.
  OPEN    → All requests short-circuited. Deterministic fallback used.
  HALF_OPEN → Limited probe requests to check recovery.
"""
import time
import logging
from enum import Enum
from typing import Dict

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Per-provider circuit breaker with configurable thresholds.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_seconds: float = 30.0,
        half_open_max_calls: int = 2
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout_seconds
        self.half_open_max_calls = half_open_max_calls
        self._circuits: Dict[str, Dict] = {}

    def _get_circuit(self, provider: str) -> Dict:
        if provider not in self._circuits:
            self._circuits[provider] = {
                "state": CircuitState.CLOSED,
                "failure_count": 0,
                "last_failure_time": 0.0,
                "half_open_calls": 0
            }
        return self._circuits[provider]

    def is_allowed(self, provider: str) -> bool:
        """Check whether a request to provider is allowed."""
        circuit = self._get_circuit(provider)

        if circuit["state"] == CircuitState.CLOSED:
            return True

        if circuit["state"] == CircuitState.OPEN:
            elapsed = time.monotonic() - circuit["last_failure_time"]
            if elapsed >= self.recovery_timeout:
                circuit["state"] = CircuitState.HALF_OPEN
                circuit["half_open_calls"] = 0
                logger.info(f"CircuitBreaker[{provider}]: OPEN → HALF_OPEN (recovery probe)")
                return True
            return False

        if circuit["state"] == CircuitState.HALF_OPEN:
            if circuit["half_open_calls"] < self.half_open_max_calls:
                circuit["half_open_calls"] += 1
                return True
            return False

        return False

    def record_success(self, provider: str) -> None:
        """Record a successful call, potentially closing the circuit."""
        circuit = self._get_circuit(provider)
        if circuit["state"] == CircuitState.HALF_OPEN:
            circuit["state"] = CircuitState.CLOSED
            circuit["failure_count"] = 0
            logger.info(f"CircuitBreaker[{provider}]: HALF_OPEN → CLOSED (recovered)")
        elif circuit["state"] == CircuitState.CLOSED:
            circuit["failure_count"] = 0

    def record_failure(self, provider: str) -> None:
        """Record a failed call, potentially opening the circuit."""
        circuit = self._get_circuit(provider)
        circuit["failure_count"] += 1
        circuit["last_failure_time"] = time.monotonic()

        if circuit["state"] == CircuitState.HALF_OPEN:
            circuit["state"] = CircuitState.OPEN
            logger.warning(f"CircuitBreaker[{provider}]: HALF_OPEN → OPEN (probe failed)")
        elif circuit["failure_count"] >= self.failure_threshold:
            circuit["state"] = CircuitState.OPEN
            logger.warning(
                f"CircuitBreaker[{provider}]: CLOSED → OPEN "
                f"(failures={circuit['failure_count']}/{self.failure_threshold})"
            )

    def get_state(self, provider: str) -> CircuitState:
        return self._get_circuit(provider)["state"]


# Global singleton
circuit_breaker = CircuitBreaker()
