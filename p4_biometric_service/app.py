"""Flask application factory for the PramaanX P4 service."""

from __future__ import annotations

import sys
from pathlib import Path

from flask import Flask, jsonify

if __package__ in {None, ""}:
    # Permit `python p4_biometric_service/app.py` as well as module startup.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from p4_biometric_service.config import Settings
    from p4_biometric_service.routes.capture import capture_bp
    from p4_biometric_service.routes.health import health_bp
    from p4_biometric_service.routes.index import index_bp
    from p4_biometric_service.routes.liveness import liveness_bp
    from p4_biometric_service.routes.screening import screening_bp
    from p4_biometric_service.routes.upload import upload_bp
    from p4_biometric_service.routes.verify import verify_bp
    from p4_biometric_service.services.face_match import (
        FaceMatcher,
    )
    from p4_biometric_service.services.liveness import LivenessChecker
    from p4_biometric_service.services.mongo_store import DatabaseStore
    from p4_biometric_service.services.uploads import UploadStore
    from p4_biometric_service.services.webcam import WebcamCapture
else:
    from .config import Settings
    from .routes.capture import capture_bp
    from .routes.health import health_bp
    from .routes.index import index_bp
    from .routes.liveness import liveness_bp
    from .routes.screening import screening_bp
    from .routes.upload import upload_bp
    from .routes.verify import verify_bp
    from .services.face_match import FaceMatcher
    from .services.liveness import LivenessChecker
    from .services.mongo_store import DatabaseStore
    from .services.uploads import UploadStore
    from .services.webcam import WebcamCapture


def create_app(
    settings: Settings | None = None,
    *,
    face_matcher: FaceMatcher | None = None,
    capture_service: WebcamCapture | None = None,
    liveness_checker: LivenessChecker | None = None,
    database_store: DatabaseStore | None = None,
    testing: bool = False,
) -> Flask:
    settings = settings or Settings.from_env()
    settings.validate()
    app = Flask(__name__)
    app.config.update(TESTING=testing, MAX_CONTENT_LENGTH=settings.max_upload_bytes)

    if database_store is None:
        database_store = DatabaseStore(settings)

    if face_matcher is None:
        face_matcher = FaceMatcher(
            threshold=settings.face_threshold,
            database_lookup=database_store.lookup_document,
            p3_module=settings.p3_module,
            model_name=settings.face_model_name,
            det_size=settings.face_det_size,
            providers=settings.insightface_providers,
        )
    if capture_service is None:
        capture_service = WebcamCapture(
            camera_index=settings.camera_index,
            capture_dir=settings.capture_dir,
            preview=settings.camera_preview,
            timeout_seconds=settings.capture_timeout_seconds,
            p3_module=settings.p3_webcam_module,
        )
    if liveness_checker is None:
        liveness_checker = LivenessChecker(
            min_frames=settings.liveness_min_frames,
            motion_threshold=settings.liveness_motion_threshold,
        )
    upload_store = UploadStore(
        settings.capture_dir, max_bytes=settings.max_upload_bytes
    )

    app.extensions["p4_settings"] = settings
    app.extensions["p4_face_matcher"] = face_matcher
    app.extensions["p4_capture"] = capture_service
    app.extensions["p4_liveness"] = liveness_checker
    app.extensions["p4_uploads"] = upload_store
    app.extensions["p4_database"] = database_store

    try:
        from flask_cors import CORS
    except ImportError:
        pass
    else:
        CORS(app)

    app.register_blueprint(health_bp)
    app.register_blueprint(index_bp)
    app.register_blueprint(capture_bp)
    app.register_blueprint(verify_bp)
    app.register_blueprint(liveness_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(screening_bp)

    @app.errorhandler(413)
    def request_too_large(_error):
        return jsonify({"error": "request body too large"}), 413

    @app.errorhandler(500)
    def internal_server_error(_error):
        # Keep unexpected failures machine-readable for P2. Detailed stack
        # traces stay in Flask's server logs rather than crossing the API.
        return jsonify(
            {
                "error": "internal service error",
                "reason": "the biometric service could not complete the request",
            }
        ), 500

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=False)
