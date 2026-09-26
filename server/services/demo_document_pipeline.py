"""Deterministic synthetic document pipeline for the local demo.

This module is intentionally not an authenticity model.  It recognizes the
marker embedded in the generated files under ``demo_artifacts`` so the team
can exercise the complete UI -> API -> Atlas persistence flow without using
real identity documents or pretending that a production OCR/tampering model
is installed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _completed_fields(*, tampered: bool, document_type: str) -> dict[str, Any]:
    if document_type == "national_id":
        clean_number = "DEMO-AAD-001"
        tampered_number = "AAD-FAKE-901"
    elif document_type == "passport":
        clean_number = "DEMO-PAS-001"
        tampered_number = "PAS-FAKE-901"
    else:
        clean_number = "Q2714253"
        tampered_number = "X9000001"
    if tampered:
        return {
            "name": "Synthetic Demo Person A" if document_type != "national_id" else "Synthetic Demo Person C",
            "dob": "1994-05-17",
            "passport_number": tampered_number,
            "nationality": "IND",
            "expiry": "2031-05-16",
        }
    return {
        "name": "Synthetic Demo Person A" if document_type != "national_id" else "Synthetic Demo Person C",
        "dob": "1994-05-17",
        "passport_number": clean_number,
        "nationality": "IND",
        "expiry": "2031-05-16",
    }


def run_pipeline(image_path: str) -> dict[str, Any]:
    """Return explainable synthetic OCR/MRZ/tampering evidence.

    Generated demo images carry a one-pixel marker in the top-left corner:
    green means the clean reference case and red means the tampered case.
    Any other image is rejected so ordinary uploads do not silently receive a
    fabricated AI result.
    """

    try:
        import cv2

        image = cv2.imread(str(Path(image_path)))
    except ImportError as exc:  # pragma: no cover - OpenCV is a runtime dep
        raise RuntimeError("OpenCV is required for the synthetic demo pipeline") from exc

    if image is None or image.shape[0] < 1 or image.shape[1] < 1:
        raise ValueError("synthetic demo image could not be read")

    blue, green, red = (int(value) for value in image[0, 0])
    is_clean = green > 180 and red < 100 and blue < 100
    is_tampered = red > 180 and green < 100 and blue < 100
    if not (is_clean or is_tampered):
        raise ValueError("image is not one of the generated synthetic demo cases")

    type_blue, type_green, type_red = (int(value) for value in image[0, 10])
    if type_blue > 180 and type_green < 100 and type_red < 100:
        document_type = "passport"
    elif type_blue < 100 and 100 < type_green < 220 and type_red > 180:
        document_type = "national_id"
    else:
        document_type = "legacy"

    fields = _completed_fields(tampered=is_tampered, document_type=document_type)
    if is_clean:
        return {
            "ocr": {
                "status": "completed",
                "fields": fields,
                "confidence": 0.99,
                "source": "synthetic_demo_marker",
            },
            "mrz": {
                "status": "completed",
                "fields": fields,
                "checks": {
                    "document_number": True,
                    "date_of_birth": True,
                    "expiry": True,
                },
                "source": "synthetic_demo_marker",
            },
            "tampering": {
                "status": "completed",
                "detected": False,
                "confidence": 0.02,
                "note": "Synthetic clean-demo marker; not a production model.",
            },
        }

    return {
        "ocr": {
            "status": "completed",
            "fields": fields,
            "confidence": 0.72,
            "source": "synthetic_demo_marker",
        },
        "mrz": {
            "status": "completed",
            "fields": fields,
            "checks": {
                "document_number": False,
                "date_of_birth": True,
                "expiry": False,
            },
            "source": "synthetic_demo_marker",
        },
        "tampering": {
            "status": "completed",
            "detected": True,
            "confidence": 0.96,
            "note": "Synthetic tampered-demo marker; not a production model.",
        },
    }
