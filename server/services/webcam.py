"""Webcam capture adapter that reuses P3 when available."""

from __future__ import annotations

import importlib
import os
import time
from datetime import datetime, timezone
from pathlib import Path


class CaptureError(RuntimeError):
    pass


class WebcamCapture:
    def __init__(
        self,
        *,
        camera_index: int = 0,
        capture_dir: str | Path,
        preview: bool = False,
        timeout_seconds: float = 30.0,
        p3_module: str | None = None,
    ):
        self.camera_index = camera_index
        self.capture_dir = Path(capture_dir)
        self.preview = preview
        self.timeout_seconds = timeout_seconds
        self.p3_module_name = p3_module or os.getenv("P4_P3_WEBCAM_MODULE")

    def _p3_capture(self, output_path: Path) -> Path | None:
        candidates = [self.p3_module_name] if self.p3_module_name else []
        candidates.extend(["webcam_capture", "p3.webcam_capture"])
        for name in candidates:
            if not name:
                continue
            try:
                module = importlib.import_module(name)
            except (ImportError, ModuleNotFoundError):
                continue
            except Exception:
                # A partially installed P3 module must not prevent the local
                # capture fallback from being attempted.
                continue
            function = next(
                (
                    getattr(module, name, None)
                    for name in (
                        "capture_photo",
                        "capture",
                        "capture_from_webcam",
                        "capture_frame",
                    )
                    if callable(getattr(module, name, None))
                ),
                None,
            )
            if not callable(function):
                continue
            try:
                result = function(
                    camera_index=self.camera_index,
                    output_path=str(output_path),
                    preview=self.preview,
                )
            except TypeError:
                try:
                    result = function(self.camera_index, str(output_path), self.preview)
                except TypeError:
                    try:
                        result = function(self.camera_index)
                    except TypeError:
                        result = function()
            except Exception:
                continue
            if isinstance(result, dict):
                result = (
                    result.get("photo_path")
                    or result.get("path")
                    or result.get("captured_path")
                )
            if result is False or result is None:
                path = output_path
            else:
                path = (
                    Path(str(result))
                    if isinstance(result, (str, Path))
                    else output_path
                )
            if path.exists():
                return path
        return None

    def capture(self) -> Path:
        try:
            self.capture_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise CaptureError(
                f"capture directory is not writable: {self.capture_dir}"
            ) from exc
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        output_path = self.capture_dir / f"live_{timestamp}.jpg"
        p3_path = self._p3_capture(output_path)
        if p3_path is not None:
            return p3_path
        try:
            import cv2
        except ImportError as exc:
            raise CaptureError("OpenCV is required for webcam capture") from exc
        try:
            camera = cv2.VideoCapture(self.camera_index)
        except Exception as exc:
            raise CaptureError(
                f"could not initialize webcam at camera index {self.camera_index}: {exc}"
            ) from exc
        if not camera.isOpened():
            camera.release()
            raise CaptureError(
                f"could not open webcam at camera index {self.camera_index}"
            )
        started = time.monotonic()
        captured = False
        try:
            while time.monotonic() - started < self.timeout_seconds:
                ok, frame = camera.read()
                if not ok or frame is None:
                    continue
                if self.preview:
                    try:
                        cv2.imshow(
                            "PramaanX — press SPACE to capture, ESC to cancel", frame
                        )
                    except cv2.error as exc:
                        raise CaptureError(
                            "preview mode requires a GUI-enabled OpenCV build"
                        ) from exc
                    key = cv2.waitKey(1) & 0xFF
                    if key == 27:
                        raise CaptureError("capture cancelled by operator")
                    if key != 32:
                        continue
                if not cv2.imwrite(str(output_path), frame):
                    raise CaptureError(f"could not write capture to {output_path}")
                captured = True
                break
        finally:
            camera.release()
            if self.preview:
                cv2.destroyAllWindows()
        if not captured:
            raise CaptureError("webcam capture timed out before a frame was captured")
        return output_path
