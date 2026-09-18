from __future__ import annotations

from io import BytesIO


def test_health_contract(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_browser_landing_page_and_api_index(client):
    page = client.get("/")
    assert page.status_code == 200
    assert page.mimetype == "text/html"
    assert b'<div id="root"></div>' in page.data or b"PramaanX P4" in page.data

    api_index = client.get("/api")
    assert api_index.status_code == 200
    assert api_index.get_json()["endpoints"]["health"] == "/api/health"


def test_verify_face_contract(client):
    response = client.post(
        "/api/verify-face",
        json={"live_photo_path": "/tmp/live.jpg", "document_number": "Q2714253"},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["found_in_database"] is True
    assert body["similarity"] == 0.87
    assert body["is_match"] is True
    assert body["threshold_used"] == 0.45
    assert body["liveness_passed"] is True
    assert body["liveness_performed"] is False
    assert body["confidence_label"] == "HIGH"
    assert body["error"] is None
    assert body["reason"]


def test_verify_requires_inputs(client):
    response = client.post("/api/verify-face", json={})
    assert response.status_code == 400
    body = response.get_json()
    assert body["similarity"] is None
    assert body["is_match"] is False
    assert body["error"] == "live_photo_path is required"


def test_unknown_document_does_not_invent_similarity(client, fake_matcher):
    fake_matcher.not_found = True
    response = client.post(
        "/api/verify-face",
        json={"live_photo_path": "/tmp/live.jpg", "document_number": "UNKNOWN"},
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["found_in_database"] is False
    assert body["similarity"] is None
    assert body["is_match"] is False
    assert body["error"] == "document not found in database"


def test_no_face_is_explicit(client):
    from p4_biometric_service.services.face_match import NoFaceDetectedError

    class NoFaceMatcher:
        def verify_against_database(self, _live_photo_path, _document_number):
            raise NoFaceDetectedError("no face detected in test image")

    client.application.extensions["p4_face_matcher"] = NoFaceMatcher()
    response = client.post(
        "/api/verify-face",
        json={"live_photo_path": "/tmp/blank.jpg", "document_number": "Q2714253"},
    )
    assert response.status_code == 422
    body = response.get_json()
    assert body["similarity"] is None
    assert body["error"] == "no face detected"
    assert "no face" in body["reason"]


def test_no_face_after_database_lookup_preserves_database_state(tmp_path):
    import numpy as np

    from p4_biometric_service.app import create_app
    from p4_biometric_service.config import Settings
    from p4_biometric_service.services.face_match import FaceMatcher
    from conftest import FakeCapture, FakeLiveness

    class Face:
        bbox = np.array([0, 0, 10, 10])

        def __init__(self):
            self.embedding = np.array([1, 0], dtype=np.float32)

    class Model:
        def get(self, image):
            return [] if image == "live.jpg" else [Face()]

    reference = tmp_path / "reference.jpg"
    reference.write_bytes(b"reference")
    matcher = FaceMatcher(
        database_lookup=lambda _document: {"photo_path": str(reference)},
        embedding_model=Model(),
        image_loader=lambda path: str(path),
    )
    app = create_app(
        Settings(),
        face_matcher=matcher,
        capture_service=FakeCapture(),
        liveness_checker=FakeLiveness(),
        testing=True,
    )
    response = app.test_client().post(
        "/api/verify-face",
        json={"live_photo_path": "live.jpg", "document_number": "Q2714253"},
    )
    assert response.status_code == 422
    body = response.get_json()
    assert body["found_in_database"] is True
    assert body["error"] == "no face detected"


def test_calibration_skips_bad_pairs_and_keeps_baseline():
    from pathlib import Path

    from p4_biometric_service.scripts.calibrate_threshold import (
        _best_threshold,
        _scored_pairs,
    )
    from p4_biometric_service.services.face_match import NoFaceDetectedError

    class BrokenMatcher:
        def compare_paths(self, _first, _second):
            raise NoFaceDetectedError("no face detected")

    scores, skipped = _scored_pairs(
        BrokenMatcher(), [(Path("one.jpg"), Path("two.jpg"))]
    )
    assert scores == []
    assert skipped == [{"pair": "one.jpg vs two.jpg", "reason": "no face detected"}]
    assert _best_threshold([0.93], []) == 0.45


def test_liveness_failure_blocks_verification():
    from p4_biometric_service.app import create_app
    from p4_biometric_service.config import Settings
    from conftest import FakeCapture, FakeFaceMatcher, FakeLiveness

    app = create_app(
        Settings(),
        face_matcher=FakeFaceMatcher(),
        capture_service=FakeCapture(),
        liveness_checker=FakeLiveness(is_live=False),
        testing=True,
    )
    response = app.test_client().post(
        "/api/verify-face",
        json={
            "live_photo_path": "/tmp/live.jpg",
            "document_number": "Q2714253",
            "frame_paths": ["/tmp/a.jpg", "/tmp/b.jpg"],
        },
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["liveness_performed"] is True
    assert body["liveness_passed"] is False
    assert body["is_match"] is False
    assert body["error"] == "liveness check failed"


def test_capture_contract(client):
    response = client.post("/api/capture", json={})
    assert response.status_code == 200
    body = response.get_json()
    assert body["captured"] is True
    assert body["photo_path"].replace("\\", "/").endswith("/tmp/test-capture.jpg")
    assert body["error"] is None


def test_browser_photo_upload_contract(client):
    response = client.post(
        "/api/upload-photo",
        data={"photo": (BytesIO(b"browser-image"), "live.jpg")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 201
    body = response.get_json()
    assert body["uploaded"] is True
    assert body["photo_path"]
    assert body["error"] is None


def test_browser_frame_upload_requires_frames(client):
    response = client.post(
        "/api/upload-frames", data={}, content_type="multipart/form-data"
    )
    assert response.status_code == 400
    assert response.get_json()["uploaded"] is False


def test_face_match_keeps_cosine_threshold_scale():
    import numpy as np

    from p4_biometric_service.services.face_match import FaceMatcher

    class Face:
        def __init__(self, embedding):
            self.embedding = np.asarray(embedding, dtype=np.float32)
            self.bbox = np.array([0, 0, 10, 10])

    class Model:
        def get(self, image):
            return [Face([1, 0] if image == "same.jpg" else [-1, 0])]

    matcher = FaceMatcher(
        threshold=0.45,
        embedding_model=Model(),
        image_loader=lambda path: str(path),
    )
    same = matcher.compare_paths("same.jpg", "same.jpg")
    different = matcher.compare_paths("same.jpg", "different.jpg")
    assert same.similarity == 1.0
    assert different.similarity == 0.0
    assert same.is_match is True
    assert different.is_match is False


def test_malformed_json_shapes_are_rejected(client):
    assert client.post("/api/verify-face", json=[]).status_code == 400
    assert client.post("/api/capture", json=[]).status_code == 400
    assert (
        client.post("/api/liveness-check", json={"frame_paths": [None]}).status_code
        == 400
    )


def test_video_liveness_input_is_supported(client):
    response = client.post("/api/liveness-check", json={"video_clip_path": "demo.mp4"})
    assert response.status_code == 200
    body = response.get_json()
    assert body["is_live"] is True
    assert body["frames_used"] == 2


def test_merged_document_api_persists_and_exposes_history(tmp_path):
    import cv2
    import numpy as np

    from p4_biometric_service.app import create_app
    from p4_biometric_service.config import Settings
    from conftest import FakeCapture, FakeFaceMatcher, FakeLiveness

    ok, encoded = cv2.imencode(".png", np.zeros((4, 4, 3), dtype=np.uint8))
    assert ok
    app = create_app(
        Settings(capture_dir=tmp_path, database_path=tmp_path / "missing.json"),
        face_matcher=FakeFaceMatcher(),
        capture_service=FakeCapture(),
        liveness_checker=FakeLiveness(),
        testing=True,
    )
    client = app.test_client()
    response = client.post(
        "/api/v1/verify",
        data={
            "document": (BytesIO(encoded.tobytes()), "passport.png"),
            "document_number": "UNKNOWN",
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "completed"
    assert body["persistence"]["stored"] is True
    assert body["document_number"] == "UNKNOWN"
    assert body["database_checks"]["found"] is False

    dashboard = client.get("/api/v1/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.get_json()["total_screenings"] == 1
    history = client.get("/api/v1/history")
    assert history.status_code == 200
    assert history.get_json()["total"] == 1
    alerts = client.get("/api/v1/alerts")
    assert alerts.status_code == 200
    alert_items = alerts.get_json()["items"]
    assert alert_items
    alert_id = alert_items[0]["_id"]
    resolved = client.post(f"/api/v1/alerts/{alert_id}/resolve")
    assert resolved.status_code == 200
    assert resolved.get_json()["resolved"] is True
    assert (
        client.get("/api/v1/alerts?status=").get_json()["items"][0]["status"]
        == "resolved"
    )
    assert client.get("/api/db/health").get_json()["mode"] == "local"


def test_merged_document_api_rejects_bad_upload(client):
    response = client.post(
        "/api/v1/verify",
        data={"document": (BytesIO(b"not-a-pdf"), "passport.pdf")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 415

    response = client.post(
        "/api/v1/verify",
        data={"document": (BytesIO(b"not-an-image"), "passport.jpg")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400


def test_missing_reference_photo_is_not_reported_as_unknown():
    from pathlib import Path

    from p4_biometric_service.app import create_app
    from p4_biometric_service.config import Settings
    from p4_biometric_service.services.face_match import FaceMatcher
    from conftest import FakeCapture, FakeLiveness

    matcher = FaceMatcher(
        database_lookup=lambda _document: {
            "photo_path": str(Path("missing-reference.jpg"))
        },
    )
    app = create_app(
        Settings(),
        face_matcher=matcher,
        capture_service=FakeCapture(),
        liveness_checker=FakeLiveness(),
        testing=True,
    )
    response = app.test_client().post(
        "/api/verify-face",
        json={"live_photo_path": "live.jpg", "document_number": "Q2714253"},
    )
    assert response.status_code == 503
    body = response.get_json()
    assert body["found_in_database"] is True
    assert body["similarity"] is None
    assert body["error"] == "reference photo unavailable"
