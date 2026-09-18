from __future__ import annotations

from pathlib import Path

from flask import Blueprint, current_app, jsonify, request

from ..services.mongo_store import DatabaseConnectionError
from ..services.uploads import UploadError

upload_bp = Blueprint("upload", __name__)


@upload_bp.post("/api/upload-photo")
def upload_photo():
    upload = request.files.get("photo")
    try:
        path = current_app.extensions["p4_uploads"].save(upload, prefix="live")
    except UploadError as exc:
        return jsonify({"uploaded": False, "photo_path": None, "error": str(exc)}), 422
    try:
        current_app.extensions["p4_database"].register_capture(str(path))
    except DatabaseConnectionError:
        current_app.logger.warning("capture retention record could not be created")
    return jsonify({"uploaded": True, "photo_path": str(path), "error": None}), 201


@upload_bp.post("/api/upload-frames")
def upload_frames():
    uploads = request.files.getlist("frames")
    if not uploads:
        return jsonify(
            {
                "uploaded": False,
                "frame_paths": [],
                "error": "at least one frame is required",
            }
        ), 400
    paths = []
    try:
        for upload in uploads:
            paths.append(
                str(current_app.extensions["p4_uploads"].save(upload, prefix="frame"))
            )
    except UploadError as exc:
        for path in paths:
            try:
                Path(path).unlink(missing_ok=True)
            except OSError:
                current_app.logger.warning(
                    "could not clean up partial frame upload: %s", path
                )
        return jsonify({"uploaded": False, "frame_paths": [], "error": str(exc)}), 422
    for path in paths:
        try:
            current_app.extensions["p4_database"].register_capture(path)
        except DatabaseConnectionError:
            current_app.logger.warning("frame retention record could not be created")
            break
    return jsonify({"uploaded": True, "frame_paths": paths, "error": None}), 201
