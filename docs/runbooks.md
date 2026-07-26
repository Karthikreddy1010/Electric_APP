# ElectricAI Operational Runbooks

## Runbook 1: Upstream LLM Provider Outage
**Symptom**: Prometheus alert `CircuitBreakerOpen` or `HighAIFallbackActivation` firing.

**Procedure**:
1. Check `/health/v2` to identify failing provider.
2. Verify API key validity in `SecretManager` or HashiCorp Vault.
3. The `AIOrchestrator` automatically cascades traffic (Primary $\rightarrow$ Guardrail Retry $\rightarrow$ Cloud Failover $\rightarrow$ Deterministic Fallback).
4. If an entire cloud provider (e.g. Anthropic) is down, update `LLM_PROVIDER` in settings or trigger secret rotation:
   ```python
   from infra.security import secret_manager
   secret_manager.rotate_secret("OPENAI_API_KEY", "new-key-value")
   ```

## Runbook 2: Database Connection Exhaustion
**Symptom**: HTTP 500 errors on database operations or `sqlalchemy.exc.TimeoutError`.

**Procedure**:
1. Inspect PgBouncer connection pool metrics on Grafana.
2. Check active PostgreSQL connections:
   ```sql
   SELECT count(*), state FROM pg_stat_activity GROUP BY state;
   ```
3. Restart FastAPI pods or scale PgBouncer max connections in `values.yaml`.

## Runbook 3: Redis Cache Disconnection
**Symptom**: `redis.exceptions.ConnectionError` in application logs.

**Procedure**:
1. `RedisStreamsEventBus` and `SemanticCacheManager` automatically fall back to in-memory dispatch and execution.
2. Restart Redis container/service:
   ```bash
   docker-compose -f docker-compose.prod.yml restart redis
   ```
