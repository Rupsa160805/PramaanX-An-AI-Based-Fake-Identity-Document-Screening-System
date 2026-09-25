"""P4 — Standalone tests for final_hash and final_service.

This file is placed outside p4_biometric_service/tests/ to avoid the existing
conftest.py, which imports biometric services requiring numpy/cv2.

Run with:  python -m pytest test_p4_final.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

from p4_biometric_service.services.final_hash import (
    calculate_h3,
    canonical_json,
    compute_hash,
)
from p4_biometric_service.services.final_service import (
    MockBlockchainService,
    build_final_payload,
    create_final_record,
    reset_blockchain,
    verify_all_records,
    verify_final_record,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _fresh_mock():
    """Reset the blockchain singleton before every test."""
    mock = MockBlockchainService()
    reset_blockchain(mock)
    yield
    reset_blockchain(None)


def _sample_result(**overrides):
    """Return a minimal but complete screening-result dict."""
    result = {
        "document_number": "ABC123",
        "status": "completed",
        "risk": {"score": 15.0, "level": "low"},
        "recommendation": {"action": "normal_clearance"},
        "database_checks": {"found": True, "expired": False},
        "tampering": {"status": "not_available", "detected": None, "confidence": None},
        "face_verification": {
            "status": "not_available",
            "is_match": False,
            "similarity": None,
            "liveness_passed": True,
        },
        "ocr": {"status": "not_available"},
        "mrz": {"status": "not_available"},
        "consistency": {"overall_match": True},
        "validation": {"document_valid": True},
        # Transient fields that must NOT affect the hash:
        "request_id": "some-uuid-that-changes",
        "audit": {"processing_time_ms": 42.0, "timestamp": "2025-01-01T00:00:00Z"},
        "persistence": {"stored": True, "result_id": "abc"},
    }
    result.update(overrides)
    return result


# ---------------------------------------------------------------------------
# Test 1 — Deterministic H3
# ---------------------------------------------------------------------------

class TestDeterministicH3:
    def test_same_input_same_h3(self):
        """Same final payload + same H2 must produce identical H3."""
        result = _sample_result()
        TEST_H2 = "a" * 64
        h3_a = calculate_h3(build_final_payload(result), TEST_H2)
        h3_b = calculate_h3(build_final_payload(result), TEST_H2)
        assert h3_a == h3_b
        assert len(h3_a) == 64  # SHA-256 hex

    def test_different_h2_different_h3(self):
        """Different H2 must change H3."""
        result = _sample_result()
        h3_a = calculate_h3(build_final_payload(result), "aaa")
        h3_b = calculate_h3(build_final_payload(result), "bbb")
        assert h3_a != h3_b


# ---------------------------------------------------------------------------
# Test 2 — Changed final result
# ---------------------------------------------------------------------------

class TestChangedResult:
    def test_changed_risk_changes_h3(self):
        """Changing one field in the final payload must change H3."""
        result_a = _sample_result()
        result_b = _sample_result(risk={"score": 85.0, "level": "high"})
        TEST_H2 = "a" * 64
        h3_a = calculate_h3(build_final_payload(result_a), TEST_H2)
        h3_b = calculate_h3(build_final_payload(result_b), TEST_H2)
        assert h3_a != h3_b

    def test_transient_fields_ignored(self):
        """Transient fields (request_id, audit.timestamp, etc.) must NOT affect H3."""
        result_a = _sample_result()
        result_b = _sample_result()
        result_b["request_id"] = "completely-different-uuid"
        result_b["audit"] = {"processing_time_ms": 999.0, "timestamp": "2099-01-01T00:00:00Z"}
        h2 = "fixed"
        h3_a = calculate_h3(build_final_payload(result_a), h2)
        h3_b = calculate_h3(build_final_payload(result_b), h2)
        assert h3_a == h3_b


# ---------------------------------------------------------------------------
# Test 3 — H3 incorporates H2
# ---------------------------------------------------------------------------

class TestH3IncorporatesH2:
    def test_h3_changes_with_h2(self):
        result = _sample_result()
        payload = build_final_payload(result)
        h3_with_h2a = calculate_h3(payload, "h2_value_a")
        h3_with_h2b = calculate_h3(payload, "h2_value_b")
        assert h3_with_h2a != h3_with_h2b

    def test_h3_empty_h2(self):
        result = _sample_result()
        payload = build_final_payload(result)
        h3_empty = calculate_h3(payload, "")
        h3_nonempty = calculate_h3(payload, "abc")
        assert h3_empty != h3_nonempty


# ---------------------------------------------------------------------------
# Test 4 — FINAL record structure
# ---------------------------------------------------------------------------

class TestFinalRecordStructure:
    def test_record_has_required_keys(self):
        result = _sample_result()
        record = create_final_record("PX001", result, "h2-value")
        assert record["verification_id"] == "PX001"
        assert record["record_type"] == "FINAL"
        assert "hash" in record
        assert record["previous_hash"] == "h2-value"
        assert len(record["hash"]) == 64


# ---------------------------------------------------------------------------
# Test 5 — Blockchain save
# ---------------------------------------------------------------------------

class TestBlockchainSave:
    def test_save_returns_stored(self):
        result = _sample_result()
        record = create_final_record("PX002", result, "h2")
        assert record["blockchain_status"] == "stored"

    def test_double_save_returns_already_anchored(self):
        result = _sample_result()
        create_final_record("PX003", result, "h2")
        record2 = create_final_record("PX003", result, "h2")
        assert record2["blockchain_status"] == "already_anchored"


# ---------------------------------------------------------------------------
# Test 6 — Blockchain MATCH
# ---------------------------------------------------------------------------

class TestBlockchainMatch:
    def test_verify_match(self):
        result = _sample_result()
        TEST_H2 = "a" * 64
        create_final_record("PX004", result, TEST_H2)
        status = verify_final_record("PX004", result, TEST_H2)
        assert status["status"] == "MATCH"
        assert status["current_hash"] == status["stored_hash"]


# ---------------------------------------------------------------------------
# Test 7 — Blockchain MISMATCH
# ---------------------------------------------------------------------------

class TestBlockchainMismatch:
    def test_verify_mismatch(self):
        result_orig = _sample_result()
        TEST_H2 = "a" * 64
        create_final_record("PX005", result_orig, TEST_H2)

        # Modify a field → H3 changes → MISMATCH
        result_modified = _sample_result(risk={"score": 99.0, "level": "high"})
        status = verify_final_record("PX005", result_modified, TEST_H2)
        assert status["status"] == "MISMATCH"
        assert status["current_hash"] != status["stored_hash"]


# ---------------------------------------------------------------------------
# Test 8 — Blockchain unavailable / NOT_FOUND
# ---------------------------------------------------------------------------

class TestBlockchainUnavailable:
    def test_verify_not_found(self):
        """Verification for a never-anchored record returns NOT_FOUND, not a crash."""
        result = _sample_result()
        TEST_H2 = "a" * 64
        status = verify_final_record("NEVER_STORED", result, TEST_H2)
        assert status["status"] == "NOT_FOUND"

    def test_verify_all_incomplete(self):
        """verify_all with no records on-chain returns INCOMPLETE, not a crash."""
        result = _sample_result()
        TEST_H2 = "a" * 64
        all_status = verify_all_records("NEVER", result, TEST_H2)
        assert all_status["chain_status"] in ("INCOMPLETE", "UNAVAILABLE")


# ---------------------------------------------------------------------------
# Test 9 — Canonicalization
# ---------------------------------------------------------------------------

class TestCanonicalization:
    def test_insertion_order_irrelevant(self):
        """Different dict insertion order must produce the same canonical hash."""
        dict_a = {"risk": "low", "score": 10}
        dict_b = {"score": 10, "risk": "low"}
        assert canonical_json(dict_a) == canonical_json(dict_b)
        assert compute_hash(dict_a) == compute_hash(dict_b)

    def test_canonical_format(self):
        """Canonical JSON should be compact with sorted keys."""
        payload = {"z": 1, "a": 2}
        expected = '{"a":2,"z":1}'
        assert canonical_json(payload) == expected


# ---------------------------------------------------------------------------
# Test 10 — build_final_payload strips transient fields
# ---------------------------------------------------------------------------

class TestBuildFinalPayload:
    def test_no_transient_fields(self):
        result = _sample_result()
        payload = build_final_payload(result)
        assert "request_id" not in payload
        assert "audit" not in payload
        assert "persistence" not in payload
        assert "warnings" not in payload
        assert "submission_id" not in payload

    def test_deterministic_keys(self):
        result = _sample_result()
        payload = build_final_payload(result)
        expected_keys = {
            "status", "risk", "recommendation",
            "database_checks", "tampering", "face_verification",
            "ocr", "mrz", "consistency", "validation",
        }
        assert set(payload.keys()) == expected_keys


# ---------------------------------------------------------------------------
# Test 11 — verify_all_records integration
# ---------------------------------------------------------------------------

class TestVerifyAll:
    def test_intact_chain_after_final_anchor(self):
        result = _sample_result()
        TEST_H2 = "a" * 64
        # Anchor all three types on the mock
        mock = MockBlockchainService()
        reset_blockchain(mock)
        mock.save_record("PX010", "INPUT", "h1_value", "")
        mock.save_record("PX010", "ANALYSIS", "h2_value", "h1_value")
        create_final_record("PX010", result, TEST_H2)

        all_status = verify_all_records("PX010", result, TEST_H2)
        assert all_status["chain_status"] == "INTACT"
        assert all_status["records"]["INPUT"]["status"] == "VERIFIED"
        assert all_status["records"]["ANALYSIS"]["status"] == "VERIFIED"
        assert all_status["records"]["FINAL"]["status"] == "MATCH"

    def test_warning_on_mismatch(self):
        result = _sample_result()
        TEST_H2 = "a" * 64
        mock = MockBlockchainService()
        reset_blockchain(mock)
        mock.save_record("PX011", "INPUT", "h1_value", "")
        mock.save_record("PX011", "ANALYSIS", "h2_value", "h1_value")
        create_final_record("PX011", result, TEST_H2)

        # Tamper
        tampered = _sample_result(risk={"score": 99.0, "level": "high"})
        all_status = verify_all_records("PX011", tampered, TEST_H2)
        assert all_status["chain_status"] == "WARNING"
        assert all_status["records"]["FINAL"]["status"] == "MISMATCH"
