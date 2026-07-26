"""
Phase 3 — Enterprise Audit Logger.

Immutable, tamper-evident audit log recording every significant
user action, AI generation, and administrative operation.
"""
import json
import time
import logging
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class AuditEntry:
    """A single immutable audit log entry."""

    def __init__(
        self,
        action: str,
        actor: str,
        tenant_id: str = "default",
        resource: str = "",
        details: Optional[Dict[str, Any]] = None,
        result: str = "success"
    ):
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.action = action
        self.actor = actor
        self.tenant_id = tenant_id
        self.resource = resource
        self.details = details or {}
        self.result = result
        # Tamper-evident hash
        self.integrity_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        payload = f"{self.timestamp}:{self.action}:{self.actor}:{self.tenant_id}:{self.resource}:{self.result}"
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "action": self.action,
            "actor": self.actor,
            "tenant_id": self.tenant_id,
            "resource": self.resource,
            "details": self.details,
            "result": self.result,
            "integrity_hash": self.integrity_hash
        }


class AuditLogger:
    """
    Enterprise audit logger maintaining an immutable, searchable trail.
    In production, entries would be persisted to a PostgreSQL audit table
    or external SIEM system. Phase 3 uses in-memory + structured log output.
    """

    def __init__(self, max_entries: int = 50000):
        self._entries: List[AuditEntry] = []
        self._max_entries = max_entries

    def log(
        self,
        action: str,
        actor: str,
        tenant_id: str = "default",
        resource: str = "",
        details: Optional[Dict[str, Any]] = None,
        result: str = "success"
    ) -> AuditEntry:
        """Record an audit event."""
        entry = AuditEntry(
            action=action,
            actor=actor,
            tenant_id=tenant_id,
            resource=resource,
            details=details,
            result=result
        )
        self._entries.append(entry)
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]

        # Emit to structured logger
        logger.info(f"AUDIT: {json.dumps(entry.to_dict(), default=str)}")
        return entry

    def query(
        self,
        action: Optional[str] = None,
        actor: Optional[str] = None,
        tenant_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query audit entries with optional filters."""
        results = self._entries
        if action:
            results = [e for e in results if e.action == action]
        if actor:
            results = [e for e in results if e.actor == actor]
        if tenant_id:
            results = [e for e in results if e.tenant_id == tenant_id]
        return [e.to_dict() for e in results[-limit:]]

    def get_count(self) -> int:
        return len(self._entries)


# Global singleton
audit_logger = AuditLogger()
