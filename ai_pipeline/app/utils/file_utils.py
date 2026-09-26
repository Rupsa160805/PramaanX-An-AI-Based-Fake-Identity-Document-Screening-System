"""
PramaanX — File Upload Utilities
----------------------------------
Handles safe acceptance, validation, and cleanup of uploaded document images.

Security principles applied:
  - Extension whitelist
  - File size limit
  - Image content validation (not just extension)
  - Temporary file cleanup after processing
  - Sensitive filenames are not logged
"""

import os
import tempfile
import uuid
from contextlib import contextmanager
from typing import Generator

from fastapi import UploadFile, HTTPException
import cv2
import numpy as np

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

ALLOWED_MIME_PREFIXES = {"image/"}


def _check_extension(filename: str) -> None:
    """Raise 415 if the file extension is not in the whitelist."""
    if not filename:
        raise HTTPException(
            status_code=415,
            detail={
                "error": {
                    "code": "MISSING_FILENAME",
                    "message": "Uploaded file has no filename.",
                }
            },
        )
    ext = os.path.splitext(filename)[1].lower()
    if ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=415,
            detail={
                "error": {
                    "code": "UNSUPPORTED_FILE_TYPE",
                    "message": (
                        f"File type '{ext}' is not supported. "
                        f"Accepted types: {', '.join(settings.allowed_extensions)}"
                    ),
                }
            },
        )


def _check_content_type(content_type: str | None) -> None:
    """Raise 415 if the MIME type does not begin with 'image/'."""
    if content_type and not content_type.startswith("image/"):
        raise HTTPException(
            status_code=415,
            detail={
                "error": {
                    "code": "UNSUPPORTED_CONTENT_TYPE",
                    "message": f"Content-Type '{content_type}' is not an image type.",
                }
            },
        )


def _check_size(data: bytes) -> None:
    """Raise 413 if the raw file data exceeds the configured limit."""
    if len(data) > settings.max_upload_bytes:
        mb = settings.max_upload_bytes / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail={
                "error": {
                    "code": "FILE_TOO_LARGE",
                    "message": f"Uploaded file exceeds the maximum allowed size of {mb:.0f} MB.",
                }
            },
        )


def _check_image_content(data: bytes) -> None:
    """
    Attempt to decode the raw bytes with OpenCV.
    This catches files that have a valid extension but invalid image content.
    Works with both OpenCV 4.x (returns None) and OpenCV 5.x (raises cv2.error)
    when the input buffer is empty or not a valid image.
    """
    if not data:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_DOCUMENT_IMAGE",
                    "message": "The uploaded file is empty and cannot be processed.",
                }
            },
        )
    arr = np.frombuffer(data, dtype=np.uint8)
    try:
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    except cv2.error:
        img = None
    if img is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "INVALID_DOCUMENT_IMAGE",
                    "message": "The uploaded file could not be decoded as a valid image.",
                }
            },
        )


@contextmanager
def saved_temp_image(upload: UploadFile) -> Generator[str, None, None]:
    """
    Context manager that:
      1. Reads and validates the uploaded file.
      2. Writes it to a uniquely-named temporary file.
      3. Yields the path to the temporary file.
      4. Deletes the temporary file on exit — always.

    Usage:
        with saved_temp_image(upload) as path:
            result = some_ai_function(path)
    """
    _check_extension(upload.filename or "")
    _check_content_type(upload.content_type)

    data = upload.file.read()
    _check_size(data)
    _check_image_content(data)

    ext = os.path.splitext(upload.filename or ".jpg")[1].lower()
    tmp_name = f"pramaanx_{uuid.uuid4().hex}{ext}"
    tmp_path = os.path.join(settings.tmp_dir, tmp_name)

    try:
        with open(tmp_path, "wb") as f:
            f.write(data)
        logger.debug("Temporary document file created (path masked for privacy)")
        yield tmp_path
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
                logger.debug("Temporary document file deleted")
        except OSError as exc:
            logger.warning("Could not delete temporary file: %s", exc)
