"""P4 — Blockchain Integrity API endpoints.

Endpoints:
    POST /api/v1/integrity/final
        Anchor the current FINAL screening result on the blockchain.

    POST /api/v1/integrity/final/verify
        Recalculate H3 and compare with the stored blockchain record.

    POST /api/v1/integrity/verify-all
        Return integrity status for INPUT, ANALYSIS, and FINAL in one call.

    POST /api/v1/integrity/demo-mismatch
        Controlled mismatch demo — anchors, then modifies a field, then
        re-verifies to produce an intentional MISMATCH.

All hashes are computed server-side.  React never computes/supplies H3.
"""

from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from ..services.final_service import (
    create_final_record,
    verify_all_records,
    verify_final_record,
)

integrity_bp = Blueprint("integrity", __name__)


def _get_screening_result():
    """Return a screening result dict for integrity operations.

    Accepts either a full JSON body ``{"verification_id": ..., "result": ..., "h2": ...}``
    or falls back to demo/synthetic data when nothing is posted.
    """
    body = request.get_json(silent=True) or {}
    verification_id = body.get("verification_id", "PX-DEMO-001")
    h2 = body.get("h2", body.get("previous_hash", ""))
    result = body.get("result")

    if result is None:
        # Generate a synthetic screening result for demo/testing
        result = _synthetic_result(verification_id)

    return verification_id, result, h2


def _synthetic_result(verification_id):
    """Minimal synthetic screening result for testing when no real result is posted."""
    return {
        "document_number": verification_id,
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
    }


# ──────────────────────────────── Anchor ────────────────────────────────────

@integrity_bp.post("/api/v1/integrity/final")
def anchor_final():
    """Build FINAL payload, compute H3, store on blockchain."""
    verification_id, result, h2 = _get_screening_result()
    try:
        record = create_final_record(verification_id, result, h2)
        return jsonify(record), 200
    except Exception as exc:
        current_app.logger.exception("integrity anchor failed")
        return jsonify({"error": "integrity anchor failed", "detail": str(exc)}), 500


# ──────────────────────────────── Verify ────────────────────────────────────

@integrity_bp.post("/api/v1/integrity/final/verify")
def verify_final():
    """Recalculate H3 and compare with blockchain."""
    verification_id, result, h2 = _get_screening_result()
    try:
        status = verify_final_record(verification_id, result, h2)
        return jsonify(status), 200
    except Exception as exc:
        current_app.logger.exception("integrity verification failed")
        return jsonify({"error": "integrity verification failed", "detail": str(exc)}), 500


# ────────────────────────────── Verify All ──────────────────────────────────

@integrity_bp.post("/api/v1/integrity/verify-all")
def verify_all():
    """Check INPUT + ANALYSIS + FINAL integrity in one call."""
    verification_id, result, h2 = _get_screening_result()
    try:
        status = verify_all_records(verification_id, result, h2)
        return jsonify(status), 200
    except Exception as exc:
        current_app.logger.exception("full integrity check failed")
        return jsonify({"error": "integrity check failed", "detail": str(exc)}), 500


# ─────────────────────── Controlled Mismatch Demo ───────────────────────────

@integrity_bp.post("/api/v1/integrity/demo-mismatch")
def demo_mismatch():
    """Anchor a FINAL record, then intentionally modify risk_level to trigger MISMATCH.

    This endpoint is for development/demo purposes ONLY.
    Uses synthetic data — never real identity documents.
    """
    demo_id = "PX-DEMO-MISMATCH"
    original_result = _synthetic_result(demo_id)
    TEST_H2 = "a" * 64

    # Step 1: Anchor with the original result
    record = create_final_record(demo_id, original_result, TEST_H2)

    # Step 2: Modify a non-sensitive field AFTER anchoring
    tampered_result = dict(original_result)
    tampered_result["risk"] = {"score": 85.0, "level": "high"}
    tampered_result["recommendation"] = {"action": "secondary_inspection"}

    # Step 3: Verify with the modified result — should produce MISMATCH
    verification = verify_final_record(demo_id, tampered_result, TEST_H2)

    return jsonify({
        "demo": "controlled_mismatch",
        "step_1_anchor": record,
        "step_2_modification": {
            "field": "risk.level",
            "original": "low",
            "modified": "high",
        },
        "step_3_verification": verification,
        "explanation": (
            "The FINAL record was anchored with risk_level='low'. "
            "After changing risk_level to 'high', H3 no longer matches "
            "the stored hash — demonstrating tamper detection."
        ),
    }), 200
