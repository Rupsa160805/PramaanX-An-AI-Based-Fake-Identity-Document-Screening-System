from __future__ import annotations

import os
import secrets
from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from ..services.document_screening import run_document_screening
from ..services.integrity_chain import anchor_chain
from ..services.mongo_store import DatabaseConnectionError
from ..services.uploads import UploadError

screening_bp = Blueprint("screening", __name__)


def _image_is_readable(path: Path) -> bool:
    try:
        import cv2

        return cv2.imread(str(path)) is not None
    except ImportError:
        # UploadStore still enforces extension, size, and non-empty content.
        # Environments without OpenCV can run the API but cannot inspect pixels.
        return True


@screening_bp.get("/api/db/health")
def database_health():
    return jsonify(current_app.extensions["p4_database"].health())


@screening_bp.get("/api/v1/health")
def versioned_health():
    settings = current_app.extensions["p4_settings"]
    database = current_app.extensions["p4_database"].health()
    return jsonify(
        {
            "status": "ok" if database["connected"] else "degraded",
            "app": "PramaanX",
            "version": "p4-merged-1.0",
            "pipeline_version": "p4-merged-1.0",
            "environment": "testing" if current_app.testing else "development",
            "database": database,
            "face_threshold": settings.face_threshold,
        }
    )


@screening_bp.post("/api/v1/verify")
def verify_document():
    upload = request.files.get("document")
    if upload is None or not upload.filename:
        return jsonify({"error": "document image is required"}), 422
    if Path(upload.filename).suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
        return jsonify({"error": "unsupported document image type"}), 415

    try:
        path = current_app.extensions["p4_uploads"].save(upload, prefix="document")
    except UploadError as exc:
        return jsonify({"error": str(exc)}), 422
    if not _image_is_readable(path):
        path.unlink(missing_ok=True)
        return jsonify({"error": "uploaded file is not a readable image"}), 400

    document_number = request.form.get("document_number") or None
    frame_paths = request.form.getlist("frame_paths") or None
    result = run_document_screening(
        path,
        document_number=document_number,
        database=current_app.extensions["p4_database"],
        face_matcher=current_app.extensions["p4_face_matcher"],
        liveness_checker=current_app.extensions["p4_liveness"],
        live_photo_path=request.form.get("live_photo_path") or None,
        frame_paths=frame_paths,
    )

    # Anchor the H1/H2/H3 integrity chain (best-effort — a chain failure must
    # never fail the screening itself). All hashes are computed server-side.
    verification_id = result.get("verification_id") or result.get("request_id")
    result["verification_id"] = verification_id
    try:
        result["integrity"] = anchor_chain(
            verification_id,
            image_path=path,
            analysis_result=result.get("tampering"),
            final_result=result,
        )
    except Exception:  # pragma: no cover - defensive
        current_app.logger.exception("integrity anchoring failed")
        result["integrity"] = {
            "verification_id": verification_id,
            "error": "anchoring_failed",
        }

    try:
        stored = current_app.extensions["p4_database"].record_verification(
            result,
            officer_id=request.headers.get("X-Officer-ID")
            or request.form.get("officer_id"),
            ip_address=request.remote_addr,
        )
    except DatabaseConnectionError as exc:
        return jsonify(
            {
                "error": "verification result could not be persisted",
                "reason": str(exc),
                "result": result,
            }
        ), 503
    result["persistence"] = {
        "stored": True,
        "result_id": stored.get("_id") or stored.get("submission_id"),
    }
    return jsonify(result), 200


@screening_bp.get("/api/v1/dashboard")
def dashboard():
    try:
        return jsonify(current_app.extensions["p4_database"].dashboard())
    except DatabaseConnectionError as exc:
        return jsonify({"error": "database unavailable", "reason": str(exc)}), 503


@screening_bp.get("/api/v1/history")
def history():
    try:
        return jsonify(
            current_app.extensions["p4_database"].list_verifications(
                limit=request.args.get("limit", 25, type=int),
                skip=request.args.get("skip", 0, type=int),
                search=request.args.get("search"),
            )
        )
    except DatabaseConnectionError as exc:
        return jsonify({"error": "database unavailable", "reason": str(exc)}), 503


@screening_bp.get("/api/v1/alerts")
def alerts():
    try:
        return jsonify(
            {
                "items": current_app.extensions["p4_database"].list_alerts(
                    status=request.args.get("status", "open")
                )
            }
        )
    except DatabaseConnectionError as exc:
        return jsonify({"error": "database unavailable", "reason": str(exc)}), 503


@screening_bp.post("/api/v1/alerts/<alert_id>/resolve")
def resolve_alert(alert_id: str):
    try:
        resolved = current_app.extensions["p4_database"].resolve_alert(
            alert_id, actor_id=request.headers.get("X-Officer-ID")
        )
    except DatabaseConnectionError as exc:
        return jsonify({"error": "database unavailable", "reason": str(exc)}), 503
    if not resolved:
        return jsonify({"error": "alert not found"}), 404
    return jsonify({"resolved": True, "alert_id": alert_id})


@screening_bp.post("/api/v1/login")
def login():
    payload = request.get_json(silent=True) or {}
    officer_id = str(payload.get("officer_id", "")).strip()
    password = str(payload.get("password", ""))
    if not officer_id or not password:
        return jsonify({"error": "officer_id and password are required"}), 401

    demo_enabled = os.getenv("P4_DEMO_LOGIN_ENABLED", "false").lower() in {
        "1",
        "true",
        "yes",
    }
    if not demo_enabled:
        try:
            user = current_app.extensions["p4_database"].authenticate_user(
                officer_id, password
            )
        except DatabaseConnectionError as exc:
            return jsonify({"error": "database unavailable", "reason": str(exc)}), 503
        if user:
            return jsonify(
                {
                    "token": secrets.token_urlsafe(24),
                    "officer_id": user["user_id"],
                    "role": user["role"],
                    "user": user,
                }
            )
        return jsonify({"error": "invalid officer ID or password"}), 401
    return jsonify(
        {
            "token": secrets.token_urlsafe(24),
            "officer_id": officer_id,
            "role": "authorized_officer",
            "warning": "Development login only; configure Atlas users and real authentication before deployment.",
        }
    )
