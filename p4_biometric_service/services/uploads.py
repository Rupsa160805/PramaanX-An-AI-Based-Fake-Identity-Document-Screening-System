"""Safe local storage for browser-captured biometric images."""

from __future__ import annotations

import secrets
from pathlib import Path

from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename


class UploadError(RuntimeError):
    """Raised when an uploaded image cannot be accepted."""


class UploadStore:
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
    MIME_EXTENSIONS = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/webp": ".webp",
    }

    def __init__(self, root: str | Path, *, max_bytes: int = 10 * 1024 * 1024):
        self.root = Path(root)
        self.max_bytes = max_bytes

    def save(self, upload: FileStorage, *, prefix: str = "browser") -> Path:
        if upload is None or not upload.filename:
            raise UploadError("an image file is required")
        safe_name = secure_filename(upload.filename)
        extension = Path(safe_name).suffix.lower()
        if extension not in self.ALLOWED_EXTENSIONS:
            extension = self.MIME_EXTENSIONS.get(upload.mimetype or "", "")
        if extension not in self.ALLOWED_EXTENSIONS:
            raise UploadError("supported image types are JPG, PNG, and WEBP")

        upload.stream.seek(0, 2)
        size = upload.stream.tell()
        upload.stream.seek(0)
        if size <= 0:
            raise UploadError("the uploaded image is empty")
        if size > self.max_bytes:
            raise UploadError(
                f"the uploaded image exceeds the {self.max_bytes // (1024 * 1024)} MB limit"
            )

        self.root.mkdir(parents=True, exist_ok=True)
        filename = f"{prefix}_{secrets.token_urlsafe(12)}{extension}"
        destination = self.root / filename
        try:
            upload.save(destination)
        except OSError as exc:
            raise UploadError("the uploaded image could not be saved") from exc
        return destination
