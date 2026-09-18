from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from ..services.mongo_store import DatabaseConnectionError
from ..services.webcam import CaptureError, WebcamCapture

capture_bp = Blueprint("capture", __name__)


@capture_bp.post("/api/capture")
def capture():
    payload = request.get_json(silent=True)
    if payload is None:
        payload = {}
    if not isinstance(payload, dict):
        return jsonify(
            {
                "captured": False,
                "photo_path": None,
                "error": "request body must be a JSON object",
            }
        ), 400
    capture_service = current_app.extensions["p4_capture"]
    if "preview" in payload and not isinstance(payload["preview"], bool):
        return jsonify(
            {
                "captured": False,
                "photo_path": None,
                "error": "preview must be a boolean",
            }
        ), 400
    if "preview" in payload and payload["preview"] != capture_service.preview:
        capture_service = WebcamCapture(
            camera_index=capture_service.camera_index,
            capture_dir=capture_service.capture_dir,
            preview=bool(payload["preview"]),
            timeout_seconds=capture_service.timeout_seconds,
            p3_module=capture_service.p3_module_name,
        )
    try:
        photo_path = capture_service.capture()
    except (CaptureError, OSError) as exc:
        return jsonify({"captured": False, "photo_path": None, "error": str(exc)}), 503
    try:
        current_app.extensions["p4_database"].register_capture(str(photo_path))
    except DatabaseConnectionError:
        current_app.logger.warning("capture retention record could not be created")
    return jsonify({"captured": True, "photo_path": str(photo_path), "error": None})
