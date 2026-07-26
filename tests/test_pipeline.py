"""
tests/test_pipeline.py — Unit tests for PipelineOrchestrator and Multi-Stage Validation.
"""
import pytest
from backend.pipeline.orchestrator import pipeline_orchestrator
from backend.pipeline.stage_validation import validate_ocr_stage, validate_parser_stage, validate_analytics_stage


def test_pipeline_orchestrator_end_to_end():
    content = b"%PDF-1.4 Mock Electricity Bill PSE&G Usage 750 kWh Total $138.90"
    states_visited = []

    def status_cb(status, pct, msg):
        states_visited.append(status)

    analytics = pipeline_orchestrator.process_file_bytes(
        file_bytes=content,
        filename="test_pipeline_bill.pdf",
        status_callback=status_cb,
    )

    assert analytics is not None
    assert analytics.component_breakdown.total_bill > 0
    assert "COMPLETED" in states_visited
