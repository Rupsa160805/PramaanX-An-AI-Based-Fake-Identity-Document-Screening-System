"""Generate the clearly labeled synthetic images used by the demo pipeline."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "demo_artifacts"


def _case(path: Path, *, fake: bool, document_number: str, name: str) -> None:
    canvas = np.full((800, 1200, 3), (245, 249, 252), dtype=np.uint8)
    cv2.rectangle(canvas, (0, 0), (1199, 110), (24, 54, 78), -1)
    cv2.rectangle(canvas, (0, 110), (1199, 118), (34, 185, 145), -1)
    cv2.putText(
        canvas,
        "PRAAMAANX - SYNTHETIC DEMO DOCUMENT",
        (42, 68),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.05,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    cv2.putText(
        canvas,
        "EXPECTED: TAMPERED / HIGHER RISK" if fake else "EXPECTED: CLEAN REFERENCE / LOW RISK",
        (55, 205),
        cv2.FONT_HERSHEY_SIMPLEX,
        1.0,
        (30, 60, 210) if fake else (20, 135, 80),
        2,
        cv2.LINE_AA,
    )
    lines = [
        f"Document number: {document_number}",
        f"Name: {name}",
        "Document type: SYNTHETIC PASSPORT",
        "Nationality: IND (synthetic)",
        "Date of birth: 1994-05-17",
        "Expiry: 2031-05-16",
    ]
    for index, line in enumerate(lines):
        cv2.putText(
            canvas,
            line,
            (70, 290 + index * 62),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.82,
            (35, 45, 55),
            2,
            cv2.LINE_AA,
        )
    cv2.putText(
        canvas,
        "NOT A REAL IDENTITY DOCUMENT - FOR LOCAL TESTING ONLY",
        (70, 700),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.72,
        (80, 80, 80),
        2,
        cv2.LINE_AA,
    )
    canvas[0, 0] = (0, 0, 255) if fake else (0, 255, 0)
    canvas[0, 1] = canvas[0, 0]
    cv2.imwrite(str(path), canvas)


def _stamp(canvas: np.ndarray, *, fake: bool, document_type: str) -> None:
    """Add the private machine-readable demo marker used by the test pipeline."""
    canvas[0, 0] = (0, 0, 255) if fake else (0, 255, 0)
    canvas[0, 1] = canvas[0, 0]
    canvas[0, 10] = (255, 0, 0) if document_type == "passport" else (0, 165, 255)
    canvas[0, 11] = canvas[0, 10]


def _passport_case(path: Path, *, fake: bool) -> None:
    canvas = np.full((760, 1200, 3), (236, 241, 246), dtype=np.uint8)
    cv2.rectangle(canvas, (0, 0), (420, 759), (52, 45, 86), -1)
    cv2.rectangle(canvas, (420, 0), (1199, 759), (244, 248, 250), -1)
    cv2.putText(canvas, "PRAAMAANX", (60, 110), cv2.FONT_HERSHEY_SIMPLEX, 1.4, (245, 220, 130), 3, cv2.LINE_AA)
    cv2.putText(canvas, "TEST PASSPORT", (60, 165), cv2.FONT_HERSHEY_SIMPLEX, 0.95, (245, 220, 130), 2, cv2.LINE_AA)
    cv2.rectangle(canvas, (78, 235), (340, 535), (194, 205, 218), 2)
    cv2.putText(canvas, "SYNTHETIC", (96, 390), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (90, 105, 120), 2, cv2.LINE_AA)
    cv2.putText(canvas, "NOT VALID", (96, 440), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (90, 105, 120), 2, cv2.LINE_AA)
    title_color = (30, 60, 210) if fake else (25, 125, 75)
    cv2.putText(canvas, "TAMPERED TEST CASE" if fake else "CLEAN TEST CASE", (470, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.86, title_color, 2, cv2.LINE_AA)
    fields = [
        "Document type: PASSPORT-STYLE DEMO",
        "Document number: DEMO-PAS-001",
        "Name: Synthetic Demo Person A",
        "Nationality: IND (fictional)",
        "Date of birth: 1994-05-17",
        "Expiry: 2031-05-16",
    ]
    for index, line in enumerate(fields):
        cv2.putText(canvas, line, (470, 175 + index * 62), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (38, 48, 60), 2, cv2.LINE_AA)
    if fake:
        cv2.line(canvas, (680, 288), (1070, 315), (25, 35, 230), 8)
        cv2.putText(canvas, "EDITED FIELD", (850, 355), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (25, 35, 230), 2, cv2.LINE_AA)
    cv2.putText(canvas, "SYNTHETIC DEMO - NOT A GOVERNMENT DOCUMENT", (470, 675), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (80, 80, 80), 2, cv2.LINE_AA)
    _stamp(canvas, fake=fake, document_type="passport")
    cv2.imwrite(str(path), canvas)


def _aadhaar_case(path: Path, *, fake: bool) -> None:
    canvas = np.full((720, 1200, 3), (247, 249, 248), dtype=np.uint8)
    cv2.rectangle(canvas, (0, 0), (1199, 88), (226, 142, 38), -1)
    cv2.rectangle(canvas, (0, 88), (1199, 104), (46, 148, 92), -1)
    cv2.putText(canvas, "PRAAMAANX TEST ID CARD", (45, 60), cv2.FONT_HERSHEY_SIMPLEX, 1.03, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.putText(canvas, "AADHAAR-STYLE SYNTHETIC DEMO", (60, 175), cv2.FONT_HERSHEY_SIMPLEX, 0.82, (30, 80, 120), 2, cv2.LINE_AA)
    cv2.rectangle(canvas, (70, 240), (320, 545), (210, 220, 225), 2)
    cv2.putText(canvas, "NO REAL PHOTO", (93, 395), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (95, 105, 110), 2, cv2.LINE_AA)
    title_color = (30, 60, 210) if fake else (25, 125, 75)
    cv2.putText(canvas, "TAMPERED TEST CASE" if fake else "CLEAN TEST CASE", (400, 245), cv2.FONT_HERSHEY_SIMPLEX, 0.9, title_color, 2, cv2.LINE_AA)
    fields = [
        "ID number: DEMO-AAD-001",
        "Name: Synthetic Demo Person C",
        "Date of birth: 1994-05-17",
        "Address: Fictional Demo District",
        "Status: SAMPLE DATA ONLY",
    ]
    for index, line in enumerate(fields):
        cv2.putText(canvas, line, (400, 320 + index * 56), cv2.FONT_HERSHEY_SIMPLEX, 0.72, (38, 48, 60), 2, cv2.LINE_AA)
    if fake:
        cv2.rectangle(canvas, (385, 295), (775, 345), (30, 40, 220), 5)
        cv2.putText(canvas, "ALTERED", (820, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (30, 40, 220), 2, cv2.LINE_AA)
    cv2.putText(canvas, "SYNTHETIC / NOT VALID / NO OFFICIAL EMBLEM OR QR", (400, 650), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (80, 80, 80), 2, cv2.LINE_AA)
    _stamp(canvas, fake=fake, document_type="national_id")
    cv2.imwrite(str(path), canvas)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    _case(
        OUT / "synthetic_original_Q2714253.png",
        fake=False,
        document_number="Q2714253",
        name="Synthetic Demo Person A",
    )
    _case(
        OUT / "synthetic_original_P8841207.png",
        fake=False,
        document_number="P8841207",
        name="Synthetic Demo Person B",
    )
    _case(
        OUT / "synthetic_tampered_unknown_X9000001.png",
        fake=True,
        document_number="X9000001",
        name="Synthetic Demo Person A",
    )
    _case(
        OUT / "synthetic_tampered_known_Q2714253.png",
        fake=True,
        document_number="Q2714253",
        name="Synthetic Demo Person A",
    )
    _passport_case(OUT / "synthetic_passport_original_DEMO-PAS-001.png", fake=False)
    _passport_case(OUT / "synthetic_passport_tampered_DEMO-PAS-001.png", fake=True)
    _aadhaar_case(OUT / "synthetic_aadhaar_original_DEMO-AAD-001.png", fake=False)
    _aadhaar_case(OUT / "synthetic_aadhaar_tampered_DEMO-AAD-001.png", fake=True)
    _aadhaar_case(OUT / "synthetic_aadhaar_tampered_unknown_AAD-FAKE-901.png", fake=True)
    reference = np.full((480, 640, 3), (210, 220, 230), dtype=np.uint8)
    cv2.putText(
        reference,
        "NO FACE - SYNTHETIC REFERENCE",
        (55, 245),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (60, 70, 80),
        2,
        cv2.LINE_AA,
    )
    cv2.imwrite(str(OUT / "synthetic_reference_no_face.png"), reference)
    print(f"Generated {len(list(OUT.glob('*.png')))} PNG demo artifacts in {OUT}")


if __name__ == "__main__":
    main()
