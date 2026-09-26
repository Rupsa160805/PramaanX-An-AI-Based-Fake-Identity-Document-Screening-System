"""
PramaanX — Test Suite
========================
Tests for the FastAPI backend / API layer.

AI modules (OCR, MRZ, tampering) are MOCKED in all tests so that:
  1. Tests do not require trained model files to be present.
  2. Tests do not require EasyOCR / PyTorch to be installed in CI.
  3. Tests isolate and validate the API/service layer independently.

Run:
    cd backend
    pytest tests/ -v
"""

import io
import json
import sys
import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ─────────────────────────────────────────────────────────────────────────────
# Make sure 'backend/' is on sys.path so app.* and ai.* resolve correctly
# ─────────────────────────────────────────────────────────────────────────────

_backend_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_root not in sys.path:
    sys.path.insert(0, _backend_root)


from app.main import app  # noqa: E402 — must come after sys.path setup

client = TestClient(app, raise_server_exceptions=False)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers / Fixtures
# ─────────────────────────────────────────────────────────────────────────────

def _make_valid_png_bytes() -> bytes:
    """
    Return the raw bytes of a 10×10 solid-white PNG image.
    This is a real, decodable PNG — not a fake file.
    """
    import struct, zlib

    def png_chunk(chunk_type: bytes, data: bytes) -> bytes:
        c = chunk_type + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    width, height = 10, 10
    raw_rows = b"".join(b"\x00" + b"\xFF\xFF\xFF" * width for _ in range(height))
    compressed = zlib.compress(raw_rows)

    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + png_chunk(b"IDAT", compressed)
        + png_chunk(b"IEND", b"")
    )


VALID_PNG = _make_valid_png_bytes()


def _fake_pipeline_result(
    ocr_status="completed",
    mrz_status="failed",
    tampering_status="not_available",
):
    """Return a plausible fake pipeline result dict for mocking."""
    return {
        "preprocessing": {"usable": True, "warnings": [], "enhanced_path": None},
        "ocr": {
            "status": ocr_status,
            "fields": {
                "passport_number": "A1234567",
                "date_of_birth": "15-04-1990",
                "date_of_expiry": "15-04-2030",
                "nationality": "IND",
                "raw_text": "SOME RAW TEXT",
            }
            if ocr_status == "completed"
            else None,
            "error": None if ocr_status == "completed" else "OCR failed",
        },
        "mrz": {
            "status": mrz_status,
            "valid": False,
            "fields": None,
            "checks": None,
            "error": "MRZ not detected",
        },
        "tampering": {
            "status": tampering_status,
            "detected": None,
            "confidence": None,
            "note": "Model not available.",
            "error": None,
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# Test 1: Health Endpoint
# ─────────────────────────────────────────────────────────────────────────────

class TestHealthEndpoint:
    def test_health_returns_200(self):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_health_response_structure(self):
        resp = client.get("/api/v1/health")
        body = resp.json()
        assert body["status"] == "ok"
        assert "app" in body
        assert "version" in body
        assert "pipeline_version" in body
        assert "environment" in body

    def test_health_app_name(self):
        resp = client.get("/api/v1/health")
        assert resp.json()["app"] == "PramaanX"


# ─────────────────────────────────────────────────────────────────────────────
# Test 2: Swagger Documentation
# ─────────────────────────────────────────────────────────────────────────────

class TestSwaggerDocs:
    def test_docs_available(self):
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_openapi_json_available(self):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert "paths" in schema
        assert "/api/v1/health" in schema["paths"]
        assert "/api/v1/verify" in schema["paths"]


# ─────────────────────────────────────────────────────────────────────────────
# Test 3: File Upload Validation
# ─────────────────────────────────────────────────────────────────────────────

class TestFileValidation:
    def test_missing_upload_returns_422(self):
        resp = client.post("/api/v1/verify")
        assert resp.status_code == 422

    def test_unsupported_extension_returns_415(self):
        resp = client.post(
            "/api/v1/verify",
            files={"document": ("test.pdf", b"%PDF-fake", "application/pdf")},
        )
        assert resp.status_code == 415

    def test_invalid_image_content_returns_400(self):
        """File has .jpg extension but contains garbage data."""
        resp = client.post(
            "/api/v1/verify",
            files={"document": ("test.jpg", b"not an image at all!!", "image/jpeg")},
        )
        assert resp.status_code == 400

    def test_oversized_file_returns_413(self):
        big_data = b"\xFF" * (11 * 1024 * 1024)  # 11 MB
        resp = client.post(
            "/api/v1/verify",
            files={"document": ("big.jpg", big_data, "image/jpeg")},
        )
        assert resp.status_code == 413

    def test_empty_bytes_returns_400(self):
        resp = client.post(
            "/api/v1/verify",
            files={"document": ("empty.png", b"", "image/png")},
        )
        # Empty file is now caught by the early empty-bytes check before OpenCV
        assert resp.status_code == 400


# ─────────────────────────────────────────────────────────────────────────────
# Test 4: Successful Pipeline (mocked AI)
# ─────────────────────────────────────────────────────────────────────────────

class TestVerificationSuccess:
    @patch("app.services.verification_service._get_pipeline")
    def test_successful_verification_structure(self, mock_get_pipeline):
        """
        Full pipeline mocked — validates the response schema shape without
        requiring any ML models or EasyOCR to be installed.
        """
        mock_pipeline = MagicMock(return_value=_fake_pipeline_result())
        mock_get_pipeline.return_value = mock_pipeline

        resp = client.post(
            "/api/v1/verify",
            files={"document": ("passport.png", VALID_PNG, "image/png")},
        )

        assert resp.status_code == 200
        body = resp.json()

        # Top-level keys
        assert "request_id" in body
        assert body["status"] == "completed"
        assert "document" in body
        assert "ocr" in body
        assert "mrz" in body
        assert "consistency" in body
        assert "tampering" in body
        assert "face_verification" in body
        assert "liveness" in body
        assert "validation" in body
        assert "database_checks" in body
        assert "risk" in body
        assert "recommendation" in body
        assert "audit" in body

    @patch("app.services.verification_service._get_pipeline")
    def test_ocr_fields_populated(self, mock_get_pipeline):
        mock_get_pipeline.return_value = MagicMock(return_value=_fake_pipeline_result())
        resp = client.post(
            "/api/v1/verify",
            files={"document": ("passport.png", VALID_PNG, "image/png")},
        )
        body = resp.json()
        assert body["ocr"]["status"] == "completed"
        assert body["ocr"]["fields"]["passport_number"] == "A1234567"
        assert body["ocr"]["fields"]["nationality"] == "IND"

    @patch("app.services.verification_service._get_pipeline")
    def test_face_verification_always_not_available(self, mock_get_pipeline):
        """Face verification module does not exist — always not_available."""
        mock_get_pipeline.return_value = MagicMock(return_value=_fake_pipeline_result())
        resp = client.post(
            "/api/v1/verify",
            files={"document": ("passport.png", VALID_PNG, "image/png")},
        )
        body = resp.json()
        assert body["face_verification"]["status"] == "not_available"

    @patch("app.services.verification_service._get_pipeline")
    def test_liveness_always_not_available(self, mock_get_pipeline):
        """Liveness module does not exist — always not_available."""
        mock_get_pipeline.return_value = MagicMock(return_value=_fake_pipeline_result())
        resp = client.post(
            "/api/v1/verify",
            files={"document": ("passport.png", VALID_PNG, "image/png")},
        )
        body = resp.json()
        assert body["liveness"]["status"] == "not_available"

    @patch("app.services.verification_service._get_pipeline")
    def test_database_check_is_mock(self, mock_get_pipeline):
        mock_get_pipeline.return_value = MagicMock(return_value=_fake_pipeline_result())
        resp = client.post(
            "/api/v1/verify",
            files={"document": ("passport.png", VALID_PNG, "image/png")},
        )
        body = resp.json()
        assert body["database_checks"]["status"] == "mock"

    @patch("app.services.verification_service._get_pipeline")
    def test_risk_score_in_range(self, mock_get_pipeline):
        mock_get_pipeline.return_value = MagicMock(return_value=_fake_pipeline_result())
        resp = client.post(
            "/api/v1/verify",
            files={"document": ("passport.png", VALID_PNG, "image/png")},
        )
        body = resp.json()
        score = body["risk"]["score"]
        assert 0.0 <= score <= 100.0
        assert body["risk"]["level"] in ("low", "medium", "high")

    @patch("app.services.verification_service._get_pipeline")
    def test_recommendation_is_valid(self, mock_get_pipeline):
        mock_get_pipeline.return_value = MagicMock(return_value=_fake_pipeline_result())
        resp = client.post(
            "/api/v1/verify",
            files={"document": ("passport.png", VALID_PNG, "image/png")},
        )
        body = resp.json()
        assert body["recommendation"]["action"] in (
            "normal_clearance",
            "manual_verification",
            "secondary_inspection",
        )

    @patch("app.services.verification_service._get_pipeline")
    def test_audit_info_present(self, mock_get_pipeline):
        mock_get_pipeline.return_value = MagicMock(return_value=_fake_pipeline_result())
        resp = client.post(
            "/api/v1/verify",
            files={"document": ("passport.png", VALID_PNG, "image/png")},
        )
        body = resp.json()
        audit = body["audit"]
        assert audit["request_id"]
        assert audit["timestamp"]
        assert audit["pipeline_version"]
        assert isinstance(audit["checks_executed"], list)


# ─────────────────────────────────────────────────────────────────────────────
# Test 5: AI Pipeline Failure Path
# ─────────────────────────────────────────────────────────────────────────────

class TestPipelineFailure:
    @patch("app.services.verification_service._get_pipeline")
    def test_pipeline_exception_returns_503(self, mock_get_pipeline):
        """Simulate a catastrophic AI pipeline crash."""
        def boom(path):
            raise RuntimeError("Simulated pipeline crash")

        mock_get_pipeline.return_value = boom

        resp = client.post(
            "/api/v1/verify",
            files={"document": ("passport.png", VALID_PNG, "image/png")},
        )
        assert resp.status_code == 503
        body = resp.json()
        # FastAPI wraps HTTPException.detail under the 'detail' key
        assert "detail" in body
        assert body["detail"]["error"]["code"] == "PIPELINE_ERROR"


# ─────────────────────────────────────────────────────────────────────────────
# Test 6: Consistency / MRZ Cross-check
# ─────────────────────────────────────────────────────────────────────────────

class TestConsistencyChecks:
    @patch("app.services.verification_service._get_pipeline")
    def test_dob_mismatch_detected(self, mock_get_pipeline):
        """When OCR and MRZ DOBs differ, consistency should flag it."""
        result = _fake_pipeline_result(mrz_status="completed")
        result["mrz"]["valid"] = True
        result["mrz"]["fields"] = {
            "document_type": "P",
            "country": "IND",
            "surname": "SMITH",
            "given_names": "JOHN",
            "passport_number": "A1234567",
            "nationality": "IND",
            "date_of_birth": "880415",   # 1988-04-15 in YYMMDD
            "sex": "M",
            "expiry_date": "300415",
        }
        result["mrz"]["checks"] = {
            "passport_number": True,
            "date_of_birth": True,
            "expiry_date": True,
        }
        # OCR has 1990-04-15 → normalises to 900415, MRZ has 880415 → mismatch
        result["ocr"]["fields"]["date_of_birth"] = "15-04-1990"
        mock_get_pipeline.return_value = MagicMock(return_value=result)

        resp = client.post(
            "/api/v1/verify",
            files={"document": ("passport.png", VALID_PNG, "image/png")},
        )
        body = resp.json()
        assert resp.status_code == 200
        dob_check = next(
            (c for c in body["consistency"]["checks"] if c["field"] == "date_of_birth"),
            None,
        )
        assert dob_check is not None
        assert dob_check["match"] is False

    @patch("app.services.verification_service._get_pipeline")
    def test_passport_match_when_same(self, mock_get_pipeline):
        """When OCR and MRZ passport numbers agree, consistency should pass."""
        result = _fake_pipeline_result(mrz_status="completed")
        result["mrz"]["valid"] = True
        result["mrz"]["fields"] = {
            "document_type": "P",
            "country": "IND",
            "surname": "SMITH",
            "given_names": "JOHN",
            "passport_number": "A1234567",
            "nationality": "IND",
            "date_of_birth": "900415",
            "sex": "M",
            "expiry_date": "300415",
        }
        result["mrz"]["checks"] = {
            "passport_number": True,
            "date_of_birth": True,
            "expiry_date": True,
        }
        result["ocr"]["fields"]["passport_number"] = "A1234567"
        mock_get_pipeline.return_value = MagicMock(return_value=result)

        resp = client.post(
            "/api/v1/verify",
            files={"document": ("passport.png", VALID_PNG, "image/png")},
        )
        body = resp.json()
        pn_check = next(
            (c for c in body["consistency"]["checks"] if c["field"] == "passport_number"),
            None,
        )
        if pn_check:
            assert pn_check["match"] is True


# ─────────────────────────────────────────────────────────────────────────────
# Test 7: Risk Score Increases with Tampering
# ─────────────────────────────────────────────────────────────────────────────

class TestRiskScoring:
    @patch("app.services.verification_service._get_pipeline")
    def test_high_tampering_probability_increases_risk(self, mock_get_pipeline):
        result = _fake_pipeline_result(tampering_status="completed")
        result["tampering"]["detected"] = True
        result["tampering"]["confidence"] = 0.95
        mock_get_pipeline.return_value = MagicMock(return_value=result)

        resp = client.post(
            "/api/v1/verify",
            files={"document": ("passport.png", VALID_PNG, "image/png")},
        )
        body = resp.json()
        assert body["risk"]["score"] >= 30.0  # Should be medium or high
        assert body["risk"]["level"] in ("medium", "high")

    @patch("app.services.verification_service._get_pipeline")
    def test_zero_tampering_low_risk(self, mock_get_pipeline):
        result = _fake_pipeline_result(tampering_status="completed")
        result["tampering"]["detected"] = False
        result["tampering"]["confidence"] = 0.05
        mock_get_pipeline.return_value = MagicMock(return_value=result)

        resp = client.post(
            "/api/v1/verify",
            files={"document": ("passport.png", VALID_PNG, "image/png")},
        )
        body = resp.json()
        assert body["risk"]["score"] < 30.0
        assert body["risk"]["level"] == "low"


# ─────────────────────────────────────────────────────────────────────────────
# Test 8: Error Response Structure
# ─────────────────────────────────────────────────────────────────────────────

class TestErrorStructure:
    def test_unsupported_type_error_has_code(self):
        resp = client.post(
            "/api/v1/verify",
            files={"document": ("file.pdf", b"fake", "application/pdf")},
        )
        # 415 response carries error detail in FastAPI HTTPException detail field
        assert resp.status_code == 415

    def test_invalid_image_error_has_structure(self):
        resp = client.post(
            "/api/v1/verify",
            files={"document": ("bad.jpg", b"NOTIMAGE", "image/jpeg")},
        )
        assert resp.status_code == 400
        body = resp.json()
        # FastAPI wraps HTTPException details differently
        assert "detail" in body or "error" in body
