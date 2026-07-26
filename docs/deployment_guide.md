# ElectricAI Enterprise Production Deployment Guide

## 1. Prerequisites
- Docker Engine 24.0+ & Docker Compose v2.20+
- Kubernetes 1.28+ Cluster (AWS EKS / GCP GKE / Azure AKS)
- Helm 3.12+
- Python 3.11+ / 3.13+

## 2. Local Docker Production Deployment
To deploy the full production stack locally with PostgreSQL, Redis, Prometheus, Grafana, and Jaeger:

```bash
# 1. Clone repository
git clone https://github.com/Karthikreddy1010/Electric_APP.git
cd Electric_APP

# 2. Configure production environment
cp .env.example .env

# 3. Launch full production compose stack
docker-compose -f docker-compose.prod.yml up -d

# 4. Verify running services
docker-compose -f docker-compose.prod.yml ps
```

## 3. Kubernetes Deployment via Helm Chart
To deploy to a Kubernetes cluster using the ElectricAI Helm 3 chart:

```bash
# 1. Validate Helm templates
python infra/helm/smoke_test.py

# 2. Deploy Helm release
helm install electricai ./infra/helm/electricai \
  --set env.ANTHROPIC_API_KEY="sk-ant-..." \
  --set env.OPENAI_API_KEY="sk-..." \
  --set env.GEMINI_API_KEY="AIza..."

# 3. Verify deployment status
kubectl get pods -l app.kubernetes.io/name=electricai
kubectl get svc
```

## 4. Health Verification
- Composite Health Check: `http://<host>:8000/health/v2`
- Prometheus Metrics: `http://<host>:8000/metrics`
- RAG Engine Health: `http://<host>:8000/llm/rag/health`
- Model Catalog: `http://<host>:8000/llm/models?tier=free`
