"""
backend.storage.object_storage — Structured Multi-Bucket Object Storage Engine.

Organizes binary payload storage into tenant and date-partitioned folder hierarchies:
bills/{tenant_id}/{year}/{month}/{bill_hash}.pdf
ocr/{tenant_id}/{bill_hash}_v{ocr_version}.json
analytics/{tenant_id}/{bill_hash}_v{analytics_version}.json
reports/{tenant_id}/{year}/{month}/{bill_hash}_report.pdf
logs/{year}/{month}/{day}/pipeline_{correlation_id}.log

Supports local filesystem persistence with S3 compatibility.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Union, Optional, Dict, Any

from backend.config.settings import storage_settings
from backend.utils.exceptions import StorageException

logger = logging.getLogger(__name__)


class ObjectStorageManager:
    """Structured Object Storage Manager supporting local disk and S3 interfaces."""

    def __init__(self, root_dir: Optional[Union[str, Path]] = None) -> None:
        self.root_dir = Path(root_dir or storage_settings.local_root)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_buckets()

    def _ensure_buckets(self) -> None:
        """Create structured bucket directories."""
        for bucket in ["bills", "ocr", "analytics", "reports", "logs"]:
            (self.root_dir / bucket).mkdir(parents=True, exist_ok=True)

    def store_bill_pdf(
        self,
        file_bytes: bytes,
        bill_hash: str,
        tenant_id: str = "default_tenant",
    ) -> str:
        """Store original bill PDF binary in bills/{tenant_id}/{year}/{month}/{hash}.pdf."""
        now = datetime.now(timezone.utc)
        subpath = f"bills/{tenant_id}/{now.year}/{now.month:02d}/{bill_hash}.pdf"
        full_path = self.root_dir / subpath
        full_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            full_path.write_bytes(file_bytes)
            logger.info(f"Stored bill PDF payload: {subpath}")
            return str(full_path)
        except Exception as e:
            raise StorageException(f"Failed to store bill PDF: {e}", cause=e)

    def store_ocr_json(
        self,
        ocr_data: Dict[str, Any],
        bill_hash: str,
        tenant_id: str = "default_tenant",
        ocr_version: str = "1.0.0",
    ) -> str:
        """Store raw OCR output JSON artifact in ocr/{tenant_id}/{hash}_v{version}.json."""
        subpath = f"ocr/{tenant_id}/{bill_hash}_v{ocr_version}.json"
        full_path = self.root_dir / subpath
        full_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            full_path.write_text(json.dumps(ocr_data, indent=2, default=str), encoding="utf-8")
            logger.info(f"Stored OCR JSON artifact: {subpath}")
            return str(full_path)
        except Exception as e:
            raise StorageException(f"Failed to store OCR JSON: {e}", cause=e)

    def store_analytics_json(
        self,
        analytics_data: Dict[str, Any],
        bill_hash: str,
        tenant_id: str = "default_tenant",
        analytics_version: str = "1.0.0",
    ) -> str:
        """Store AnalyticsResult JSON in analytics/{tenant_id}/{hash}_v{version}.json."""
        subpath = f"analytics/{tenant_id}/{bill_hash}_v{analytics_version}.json"
        full_path = self.root_dir / subpath
        full_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            full_path.write_text(json.dumps(analytics_data, indent=2, default=str), encoding="utf-8")
            logger.info(f"Stored Analytics Result JSON artifact: {subpath}")
            return str(full_path)
        except Exception as e:
            raise StorageException(f"Failed to store Analytics JSON: {e}", cause=e)

    def get_bill_pdf(self, file_path_or_subpath: str) -> bytes:
        """Retrieve stored PDF binary."""
        path = Path(file_path_or_subpath)
        if not path.is_absolute():
            path = self.root_dir / file_path_or_subpath
        if not path.exists():
            raise StorageException(f"PDF file not found: {path}")
        return path.read_bytes()


# Singleton instance
object_storage = ObjectStorageManager()
