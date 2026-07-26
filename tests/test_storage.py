"""
tests/test_storage.py — Unit tests for Object Storage Manager.
"""
import pytest
from backend.storage.object_storage import object_storage


def test_object_storage_pdf_save_and_retrieve(tmp_path):
    content = b"%PDF-1.4 Mock Test Storage File Payload"
    bill_hash = "11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff"

    file_path = object_storage.store_bill_pdf(content, bill_hash=bill_hash, tenant_id="test_tenant")
    assert file_path is not None

    retrieved = object_storage.get_bill_pdf(file_path)
    assert retrieved == content


def test_object_storage_json_save():
    ocr_data = {"raw_text": "Sample text", "confidence": 0.99}
    bill_hash = "11223344556677889900aabbccddeeff11223344556677889900aabbccddeeff"

    file_path = object_storage.store_ocr_json(ocr_data, bill_hash=bill_hash, tenant_id="test_tenant")
    assert file_path is not None
