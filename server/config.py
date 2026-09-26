"""Configuration for the P4 biometric microservice."""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path


_DEFAULT_DATABASE_PATH = (
    Path(__file__).resolve().parent / "demo_data" / "reference_records.json"
)


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_or_default(name: str, default: str) -> str:
    value = os.getenv(name)
    return value.strip() if value and value.strip() else default


@dataclass(frozen=True)
class Settings:
    camera_index: int = 0
    capture_dir: Path = Path(tempfile.gettempdir()) / "pramaanx_captures"
    face_threshold: float = 0.45
    face_model_name: str = "buffalo_l"
    face_det_size: int = 640
    insightface_providers: tuple[str, ...] = ("CPUExecutionProvider",)
    database_path: Path = _DEFAULT_DATABASE_PATH
    p3_module: str | None = None
    p3_database_module: str | None = None
    p3_webcam_module: str | None = None
    camera_preview: bool = False
    capture_timeout_seconds: float = 30.0
    max_upload_bytes: int = 10 * 1024 * 1024
    liveness_min_frames: int = 2
    liveness_motion_threshold: float = 2.0
    database_mode: str = "auto"
    mongodb_uri: str | None = None
    mongodb_database: str = "pramaanx"
    mongodb_server_selection_timeout_ms: int = 2500
    local_database_path: Path | None = None
    # Opt-in API key. When set, all /api/* endpoints (except health checks)
    # require a matching X-API-Key header. Empty/unset leaves the API open,
    # which is only appropriate for a trusted localhost demo.
    api_key: str | None = None

    @classmethod
    def from_env(cls) -> "Settings":
        providers = tuple(
            item.strip()
            for item in os.getenv(
                "P4_INSIGHTFACE_PROVIDERS", "CPUExecutionProvider"
            ).split(",")
            if item.strip()
        ) or ("CPUExecutionProvider",)
        return cls(
            camera_index=int(os.getenv("P4_CAMERA_INDEX", "0")),
            capture_dir=Path(
                _env_or_default(
                    "P4_CAPTURE_DIR",
                    str(Path(tempfile.gettempdir()) / "pramaanx_captures"),
                )
            ),
            face_threshold=float(_env_or_default("P4_FACE_THRESHOLD", "0.45")),
            face_model_name=_env_or_default("P4_FACE_MODEL", "buffalo_l"),
            face_det_size=int(os.getenv("P4_FACE_DET_SIZE", "640")),
            insightface_providers=providers,
            database_path=Path(
                _env_or_default("P4_DATABASE_PATH", str(_DEFAULT_DATABASE_PATH))
            ),
            p3_module=os.getenv("P4_P3_FACE_MODULE") or None,
            p3_database_module=os.getenv("P4_P3_DATABASE_MODULE") or None,
            p3_webcam_module=os.getenv("P4_P3_WEBCAM_MODULE") or None,
            camera_preview=_as_bool(os.getenv("P4_CAMERA_PREVIEW"), False),
            capture_timeout_seconds=float(
                os.getenv("P4_CAPTURE_TIMEOUT_SECONDS", "30")
            ),
            max_upload_bytes=int(
                os.getenv("P4_MAX_UPLOAD_BYTES", str(10 * 1024 * 1024))
            ),
            liveness_min_frames=int(os.getenv("P4_LIVENESS_MIN_FRAMES", "2")),
            liveness_motion_threshold=float(
                os.getenv("P4_LIVENESS_MOTION_THRESHOLD", "2.0")
            ),
            database_mode=_env_or_default("P4_DATABASE_MODE", "auto").lower(),
            mongodb_uri=(os.getenv("MONGODB_URI") or "").strip() or None,
            mongodb_database=_env_or_default("MONGODB_DATABASE", "pramaanx"),
            mongodb_server_selection_timeout_ms=int(
                os.getenv("MONGODB_SERVER_SELECTION_TIMEOUT_MS", "2500")
            ),
            local_database_path=(
                Path(os.environ["P4_LOCAL_DATABASE_PATH"])
                if os.getenv("P4_LOCAL_DATABASE_PATH")
                else None
            ),
            api_key=(os.getenv("P4_API_KEY") or "").strip() or None,
        )

    def validate(self) -> None:
        if not 0.0 <= self.face_threshold <= 1.0:
            raise ValueError("P4_FACE_THRESHOLD must be between 0 and 1")
        if self.camera_index < 0:
            raise ValueError("P4_CAMERA_INDEX must be non-negative")
        if self.liveness_min_frames < 2:
            raise ValueError("P4_LIVENESS_MIN_FRAMES must be at least 2")
        if self.max_upload_bytes <= 0:
            raise ValueError("P4_MAX_UPLOAD_BYTES must be positive")
        if self.face_det_size < 64:
            raise ValueError("P4_FACE_DET_SIZE must be at least 64")
        if self.capture_timeout_seconds <= 0:
            raise ValueError("P4_CAPTURE_TIMEOUT_SECONDS must be positive")
        if self.liveness_motion_threshold < 0:
            raise ValueError("P4_LIVENESS_MOTION_THRESHOLD must be non-negative")
        if self.database_mode not in {"auto", "local", "mongo"}:
            raise ValueError("P4_DATABASE_MODE must be auto, local, or mongo")
        if self.mongodb_server_selection_timeout_ms <= 0:
            raise ValueError("MONGODB_SERVER_SELECTION_TIMEOUT_MS must be positive")
        if self.database_mode == "mongo" and not self.mongodb_uri:
            raise ValueError("MONGODB_URI is required when P4_DATABASE_MODE=mongo")
