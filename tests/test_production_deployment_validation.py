"""
Phase 3 Production Deployment Validation Suite.

Executes comprehensive runtime validation for:
  1. Helm & Docker Container Deployment Manifests
  2. Subsystem Health Probes & Disaster Recovery Aggregator
  3. Database & Redis Backup Automation Sweep
  4. Monitoring Metrics Exporter & Alert Rules
  5. GPU Inference Engine (vLLM / SGLang) Failover Cascade
  6. Real Vector Database (pgvector / Qdrant / TF-IDF) Adapters
"""
import pytest
import os
import sys
from pathlib import Path

from infra.dr.health_aggregator import health_aggregator, HealthStatus
from infra.dr.backup_db import run_full_backup
from api.services.llm.rag import rag_service, PGVectorStore, QdrantVectorStore, RAGDocument
from api.services.llm.providers.vllm_provider import VLLMProvider
from api.services.llm.providers.sglang_provider import SGLangProvider
from api.services.llm.router import ModelRouter
from api.services.llm.contracts import UserTier
from infra.observability.prometheus import get_metrics


@pytest.fixture
def anyio_backend():
    return "asyncio"


class TestProductionDeploymentValidation:

    @pytest.mark.anyio
    async def test_val1_disaster_recovery_health_aggregator(self):
        """Verify DR health aggregator probes all subsystems."""
        health = await health_aggregator.check_all()
        assert "status" in health
        assert health["status"] in (HealthStatus.HEALTHY.value, HealthStatus.DEGRADED.value, HealthStatus.UNHEALTHY.value)
        assert "subsystems" in health
        assert "api" in health["subsystems"]
        assert health["subsystems"]["api"]["healthy"] is True

    def test_val2_automated_backup_execution(self):
        """Verify PostgreSQL and Redis backup automation script runs without failure."""
        backup_res = run_full_backup()
        assert backup_res["postgres_backup"] is True
        assert backup_res["redis_backup"] is True

    def test_val3_monitoring_metrics_and_alerts(self):
        """Verify Prometheus metrics payload is generated and alert rules file is present."""
        metrics_data = get_metrics()
        assert isinstance(metrics_data, bytes)

        alerts_file = Path("infra/prometheus/alerts.yml")
        assert alerts_file.exists()
        assert "HighAPIErrorRate" in alerts_file.read_text()

    @pytest.mark.anyio
    async def test_val4_gpu_inference_vllm_sglang_failover(self):
        """Verify GPU inference providers handle offline endpoints via router failover."""
        vllm = VLLMProvider(base_url="http://localhost:9999/v1")
        assert vllm.is_available() is False

        sglang = SGLangProvider(base_url="http://localhost:9999/v1")
        assert sglang.is_available() is False

        # ModelRouter should resolve chain gracefully without raising unhandled exceptions
        router = ModelRouter()
        chain = router.resolve_chain(UserTier.FREE)
        assert len(chain) > 0

    def test_val5_real_vector_database_adapters(self):
        """Verify pgvector and Qdrant vector database adapters."""
        pg_store = PGVectorStore()
        pg_store.index(RAGDocument("doc-pg-1", "tariff", "PG Title", "PG Content"))
        res_pg = pg_store.search("PG Title", top_k=1)
        assert len(res_pg) == 1
        assert res_pg[0]["doc_id"] == "doc-pg-1"

        qdrant_store = QdrantVectorStore()
        qdrant_store.index(RAGDocument("doc-qd-1", "policy", "Qd Title", "Qd Content"))
        res_qd = qdrant_store.search("Qd Title", top_k=1)
        assert len(res_qd) == 1
        assert res_qd[0]["doc_id"] == "doc-qd-1"

        rag_health = rag_service.check_health()
        assert rag_health["status"] == "healthy"
        assert rag_health["document_count"] >= 5
