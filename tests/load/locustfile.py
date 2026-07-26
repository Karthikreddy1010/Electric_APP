"""
Production Load Testing Suite using Locust.

Simulates 10, 50, 100, 250, 500 concurrent virtual users hitting:
  - GET  /health/v2          (DR Health Check Aggregator)
  - GET  /metrics            (Prometheus Metrics Exporter)
  - GET  /llm/models         (Model Catalog)
  - POST /llm/explain        (AI Bill Narration)
  - POST /llm/chat           (Interactive Copilot Chat)

Usage:
  locust -f tests/load/locustfile.py --host=http://localhost:8000 --users=50 --spawn-rate=5
"""
from locust import HttpUser, task, between
import json


class ElectricAILoadUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def check_health_v2(self):
        self.client.get("/health/v2", name="GET /health/v2")

    @task(2)
    def check_metrics(self):
        self.client.get("/metrics", name="GET /metrics")

    @task(2)
    def list_models(self):
        self.client.get("/llm/models?tier=free", name="GET /llm/models")

    @task(4)
    def post_llm_explain(self):
        payload = {
            "task": "bill_analysis",
            "context_data": {
                "bill_hash": "locust_test_hash",
                "customer_id": "CUST-LOCUST",
                "utility": "PSE&G",
                "total_bill": 175.50,
                "usage_kwh": 800.0,
                "supply_charge": 88.00,
                "delivery_charge": 45.00
            },
            "user_tier": "free"
        }
        headers = {
            "Content-Type": "application/json",
            "X-Tenant-ID": "tenant-locust",
            "X-User-Tier": "free"
        }
        self.client.post("/llm/explain", json=payload, headers=headers, name="POST /llm/explain")

    @task(2)
    def post_llm_chat(self):
        payload = {
            "task": "chat",
            "message": "How can I reduce my electricity bill?",
            "history": [],
            "context_data": {
                "total_bill": 175.50,
                "usage_kwh": 800.0
            },
            "current_tab": "Impact",
            "user_tier": "free"
        }
        headers = {
            "Content-Type": "application/json",
            "X-Tenant-ID": "tenant-locust",
            "X-User-Tier": "free"
        }
        self.client.post("/llm/chat", json=payload, headers=headers, name="POST /llm/chat")
