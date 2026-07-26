"""
tests/test_parser.py — Unit tests for OCR Engine and Bill Parser.
"""
import pytest
from backend.ocr.engine import ocr_engine
from backend.bill_parser.parser import bill_parser


def test_ocr_engine_extraction():
    content = b"%PDF-1.4 Mock Electricity Bill PSE&G Usage 750 kWh Total $138.90"
    ocr_res = ocr_engine.extract_from_bytes(content, filename="test_bill.pdf")

    assert ocr_res.bill_hash is not None
    assert len(ocr_res.bill_hash) == 64
    assert ocr_res.ocr_version == "1.0.0"
    assert ocr_res.confidence_score > 0


def test_bill_parser_extraction():
    content = b"%PDF-1.4 Mock Electricity Bill PSE&G Usage 750 kWh Total $138.90"
    ocr_res = ocr_engine.extract_from_bytes(content, filename="test_bill.pdf")
    parsed_bill = bill_parser.parse(ocr_res)

    assert parsed_bill.utility in ["PSE&G", "JCP&L", "Atlantic City Electric", "RECO"]
    assert parsed_bill.usage_kwh > 0
    assert parsed_bill.total_bill > 0
    assert parsed_bill.parser_version == "1.0.0"
