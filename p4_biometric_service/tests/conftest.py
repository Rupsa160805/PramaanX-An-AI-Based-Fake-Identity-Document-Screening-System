from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest  # noqa: E402

from p4_biometric_service.app import create_app  # noqa: E402
from p4_biometric_service.config import Settings  # noqa: E402
from p4_biometric_service.services.face_match import (  # noqa: E402
    FaceMatchResult,
    ReferenceNotFoundError,
)


class FakeFaceMatcher:
    def __init__(self, result: FaceMatchResult | None = None):
        self.result = result or FaceMatchResult(0.87, True, 0.45, "HIGH", "test match")
        self.not_found = False

    def verify_against_database(self, _live_photo_path: str, _document_number: str):
        if self.not_found:
            raise ReferenceNotFoundError("test record missing")
        return self.result


class FakeCapture:
    camera_index = 0
    capture_dir = Path(".")
    preview = False
    timeout_seconds = 1
    p3_module_name = None

    def capture(self):
        return Path("/tmp/test-capture.jpg")


class FakeLiveness:
    def __init__(self, is_live: bool = True):
        self.is_live = is_live

    def check_paths(self, _paths):
        from p4_biometric_service.services.liveness import LivenessResult

        return LivenessResult(
            self.is_live, "test liveness", 2, 3.0 if self.is_live else 0.0
        )

    def check_video(self, _path):
        return self.check_paths([] if not self.is_live else ["frame-a", "frame-b"])


@pytest.fixture
def fake_matcher():
    return FakeFaceMatcher()


@pytest.fixture
def client(fake_matcher, tmp_path):
    settings = Settings(capture_dir=tmp_path, database_path=Path("missing.json"))
    app = create_app(
        settings,
        face_matcher=fake_matcher,
        capture_service=FakeCapture(),
        liveness_checker=FakeLiveness(),
        testing=True,
    )
    return app.test_client()
