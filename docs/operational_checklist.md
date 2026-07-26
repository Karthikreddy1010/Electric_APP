# Production Deployment Operational Checklist

- [x] **Database Initialization**: PostgreSQL DW schema migrated & seed data initialized.
- [x] **Redis Cache**: Redis LRU memory eviction policy configured (`maxmemory 512mb`).
- [x] **API Gateway**: Rate limiting & circuit breaker active on `/llm/*` endpoints.
- [x] **Observability**: Prometheus scraping `/metrics` and structured JSON logs configured.
- [x] **RAG Engine**: Scoped to Tariffs, Policies, and FAQs with zero customer bill data exposure.
- [x] **Deterministic Invariant**: Analytics Engine outputs treated as read-only facts. LLM performs 0 calculations.
- [x] **7-Point Output Validator**: Numeric exact match & zero-hallucination audit active on all narrations.
- [x] **DR Composite Health**: `/health/v2` monitoring API, DB, Redis, and LLM subsystems.
- [x] **Automated Test Verification**: 100% pass rate across test suite (`pytest`).
