# ElectricAI Incident Response Playbook

## 1. Incident Severity Definitions
- **Sev-1 (Critical)**: Whole system offline, database unrecoverable, or 100% API error rate.
- **Sev-2 (High)**: Core feature degraded (e.g. AI narration failing, fallback active for all users).
- **Sev-3 (Medium)**: Single non-critical service offline (e.g. Jaeger tracing down, high rate limit blocks).
- **Sev-4 (Low)**: Minor non-impacting issue or metric collection anomaly.

## 2. Escalation & Communication Flow
1. **Detection**: Alert triggered on Prometheus/Grafana or PagerDuty notification.
2. **Triaging**: SRE On-Call inspects `/health/v2` and Grafana dashboards (`http://localhost:3001`).
3. **Mitigation**: Trigger deterministic fallback mode or execute operational runbook.
4. **Post-Mortem**: Document root cause, timeline, and corrective actions within 24 hours.
