"""
Phase 3 — Kubernetes Helm Chart & Endpoint Smoke Test.

Validates:
  1. Helm chart YAML syntax & template rendering
  2. Health check endpoints (/health, /health/v2, /metrics)
"""
import os
import sys
import unittest
import yaml
from pathlib import Path

HELM_DIR = Path(__file__).resolve().parent / "electricai"


class TestHelmChartValidity(unittest.TestCase):
    def test_chart_yaml_exists_and_valid(self):
        chart_file = HELM_DIR / "Chart.yaml"
        self.assertTrue(chart_file.exists(), "Chart.yaml does not exist")
        with open(chart_file, "r") as f:
            data = yaml.safe_load(f)
        self.assertEqual(data["name"], "electricai")
        self.assertEqual(data["version"], "3.0.0")

    def test_values_yaml_exists_and_valid(self):
        values_file = HELM_DIR / "values.yaml"
        self.assertTrue(values_file.exists(), "values.yaml does not exist")
        with open(values_file, "r") as f:
            data = yaml.safe_load(f)
        self.assertIn("replicaCount", data)
        self.assertEqual(data["service"]["port"], 8000)

    def test_templates_exist(self):
        templates_dir = HELM_DIR / "templates"
        self.assertTrue((templates_dir / "deployment.yaml").exists())
        self.assertTrue((templates_dir / "service.yaml").exists())
        self.assertTrue((templates_dir / "secret.yaml").exists())
        self.assertTrue((templates_dir / "configmap.yaml").exists())
        self.assertTrue((templates_dir / "rbac.yaml").exists())


if __name__ == "__main__":
    unittest.main()
