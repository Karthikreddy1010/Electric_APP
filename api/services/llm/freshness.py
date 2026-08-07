"""
Phase 4 — Per-Connector Freshness Manager.

Manages knowledge freshness with configurable TTLs per source connector.
Calculates dynamic freshness_score based on document age relative to TTL.

Connector TTLs (configurable):
    PJM:              5 minutes
    NOAA:             15 minutes
    EIA:              24 hours
    Tariffs:          7 days
    Government:       1 day
    Utility:          7 days
    Research Papers:  30 days
    Utility Manuals:  90 days
    News:             6 hours
    Trusted Search:   5 minutes

Does NOT modify retrieval logic — only annotates knowledge with freshness metadata.
"""
import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


# ── Default Per-Connector TTL Configuration (seconds) ──────────────────────

DEFAULT_CONNECTOR_TTLS: Dict[str, int] = {
    # Official APIs (real-time / near-real-time)
    "pjm": 5 * 60,              # 5 minutes
    "noaa": 15 * 60,             # 15 minutes
    "eia": 24 * 60 * 60,         # 24 hours
    "utility_api": 60 * 60,      # 1 hour

    # Document-based knowledge
    "tariff": 7 * 24 * 60 * 60,              # 7 days
    "government": 24 * 60 * 60,              # 1 day
    "utility": 7 * 24 * 60 * 60,             # 7 days
    "research_papers": 30 * 24 * 60 * 60,    # 30 days
    "utility_manuals": 90 * 24 * 60 * 60,    # 90 days

    # Live retrieval
    "news": 6 * 60 * 60,          # 6 hours
    "trusted_search": 5 * 60,     # 5 minutes

    # RAG knowledge base
    "rag_knowledge": 7 * 24 * 60 * 60,  # 7 days
    "faq": 30 * 24 * 60 * 60,           # 30 days
    "policy": 7 * 24 * 60 * 60,         # 7 days
}


class ConnectorFreshnessManager:
    """
    Manages knowledge freshness with configurable per-connector TTLs.

    Calculates a dynamic freshness_score (0.0 to 1.0) based on:
        - Document timestamp (last_updated)
        - Connector-specific TTL from configuration
        - Exponential decay curve

    freshness_score = max(0.0, 1.0 - (age / ttl))

    Score Interpretation:
        1.0  = Fresh (just retrieved / within TTL)
        0.5  = Aging (halfway through TTL)
        0.0  = Stale (TTL expired)
    """

    def __init__(self, custom_ttls: Optional[Dict[str, int]] = None):
        self._ttls = dict(DEFAULT_CONNECTOR_TTLS)
        if custom_ttls:
            self._ttls.update(custom_ttls)
        # Track last refresh timestamps per connector
        self._last_refresh: Dict[str, float] = {}

    def get_ttl(self, connector: str) -> int:
        """Get TTL in seconds for a connector."""
        return self._ttls.get(connector, 7 * 24 * 60 * 60)  # Default 7 days

    def set_ttl(self, connector: str, ttl_seconds: int) -> None:
        """Override TTL for a connector."""
        self._ttls[connector] = ttl_seconds
        logger.info(f"ConnectorFreshness: TTL for '{connector}' set to {ttl_seconds}s")

    def calculate_freshness_score(
        self,
        connector: str,
        last_updated_epoch: Optional[float] = None,
    ) -> float:
        """
        Calculate freshness score for a piece of knowledge.

        Args:
            connector: Source connector identifier (e.g. 'pjm', 'eia', 'rag_knowledge')
            last_updated_epoch: Unix epoch of when the data was last updated/retrieved.
                               If None, assumes data is fresh (score=1.0).

        Returns:
            freshness_score: 0.0 (stale) to 1.0 (fresh)
        """
        if last_updated_epoch is None:
            return 1.0

        ttl = self.get_ttl(connector)
        age = time.time() - last_updated_epoch

        if age <= 0:
            return 1.0
        if age >= ttl:
            return 0.0

        # Linear decay within TTL window
        score = max(0.0, 1.0 - (age / ttl))
        return round(score, 4)

    def is_fresh(self, connector: str, last_updated_epoch: Optional[float] = None) -> bool:
        """Check if knowledge from a connector is still within its TTL."""
        score = self.calculate_freshness_score(connector, last_updated_epoch)
        return score > 0.0

    def record_refresh(self, connector: str) -> None:
        """Record that a connector's data was refreshed."""
        self._last_refresh[connector] = time.time()
        logger.debug(f"ConnectorFreshness: '{connector}' refreshed at {self._last_refresh[connector]}")

    def get_last_refresh(self, connector: str) -> Optional[float]:
        """Get last refresh epoch for a connector."""
        return self._last_refresh.get(connector)

    def needs_refresh(self, connector: str) -> bool:
        """Check if a connector needs a data refresh."""
        last = self._last_refresh.get(connector)
        if last is None:
            return True
        return not self.is_fresh(connector, last)

    def get_all_ttls(self) -> Dict[str, int]:
        """Return all configured TTLs."""
        return dict(self._ttls)

    def get_status(self) -> Dict[str, Any]:
        """Return freshness status for all tracked connectors."""
        now = time.time()
        status = {}
        for connector, last in self._last_refresh.items():
            ttl = self.get_ttl(connector)
            age = now - last
            status[connector] = {
                "last_refresh_epoch": last,
                "age_seconds": round(age, 1),
                "ttl_seconds": ttl,
                "is_fresh": age < ttl,
                "freshness_score": self.calculate_freshness_score(connector, last),
            }
        return status


# Global singleton
freshness_manager = ConnectorFreshnessManager()
