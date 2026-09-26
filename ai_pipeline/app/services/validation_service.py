"""
PramaanX — Consistency / Cross-Source Evidence Service
---------------------------------------------------------
Compares visible (OCR) document fields against machine-readable (MRZ) values
and produces structured mismatch reports.

Key design principle:
  A mismatch is reported as "suspicious inconsistency requiring manual
  verification" — NOT as automatic proof of forgery.

DOB normalisation note:
  OCR extracts dates as DD-MM-YYYY or DD/MM/YYYY.
  MRZ stores dates as YYMMDD.
  These are normalised to YYMMDD for comparison.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from app.core.logging import get_logger
from app.schemas.common import Severity

logger = get_logger(__name__)


def _normalise_dob_ocr(raw: str | None) -> str | None:
    """
    Convert OCR date string DD-MM-YYYY or DD/MM/YYYY → YYMMDD.
    Returns None if the format is unrecognised.
    """
    if not raw:
        return None
    m = re.match(r"(\d{2})[-/](\d{2})[-/](\d{4})", raw.strip())
    if not m:
        return None
    dd, mm, yyyy = m.groups()
    yy = yyyy[2:]  # last two digits of year
    return f"{yy}{mm}{dd}"


def _normalise_passport_number(raw: str | None) -> str | None:
    """Strip filler characters and normalise to uppercase."""
    if not raw:
        return None
    return raw.upper().replace("<", "").replace(" ", "").strip()


def _normalise_nationality(raw: str | None) -> str | None:
    """Uppercase 3-letter country code."""
    if not raw:
        return None
    return raw.upper().replace("<", "").replace(" ", "").strip()


def build_consistency_result(
    ocr: Dict[str, Any],
    mrz: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Compare OCR fields against MRZ fields and return a structured consistency
    report.

    Args:
        ocr: Raw OCR pipeline output (step 2 of pipeline).
        mrz: Raw MRZ pipeline output (step 3 of pipeline).

    Returns a dict matching the ConsistencyResult schema.
    """
    checks: List[Dict[str, Any]] = []

    ocr_fields = (ocr.get("fields") or {})
    mrz_fields = (mrz.get("fields") or {})

    if mrz.get("status") not in ("completed",) or not mrz_fields:
        # Cannot cross-check if MRZ extraction failed
        return {"overall_match": True, "checks": []}

    # ── Passport Number ───────────────────────────────────────────────────────
    ocr_pn = _normalise_passport_number(ocr_fields.get("passport_number"))
    mrz_pn = _normalise_passport_number(mrz_fields.get("passport_number"))

    if ocr_pn and mrz_pn:
        match = ocr_pn == mrz_pn
        checks.append({
            "field": "passport_number",
            "visual_value": ocr_pn,
            "mrz_value": mrz_pn,
            "match": match,
            "severity": "low" if match else "high",
            "reason": (
                "Passport numbers match."
                if match
                else "Printed passport number differs from MRZ passport number. "
                     "Suspicious inconsistency — manual verification recommended."
            ),
        })

    # ── Date of Birth ─────────────────────────────────────────────────────────
    ocr_dob_raw = ocr_fields.get("date_of_birth")
    mrz_dob = mrz_fields.get("date_of_birth")  # already YYMMDD

    ocr_dob_norm = _normalise_dob_ocr(ocr_dob_raw)

    if ocr_dob_norm and mrz_dob:
        match = ocr_dob_norm == mrz_dob
        checks.append({
            "field": "date_of_birth",
            "visual_value": ocr_dob_raw,
            "mrz_value": mrz_dob,
            "match": match,
            "severity": "low" if match else "high",
            "reason": (
                "Dates of birth match."
                if match
                else "Printed date of birth differs from MRZ date of birth. "
                     "Suspicious inconsistency — possible alteration detected."
            ),
        })

    # ── Nationality ───────────────────────────────────────────────────────────
    ocr_nat = _normalise_nationality(ocr_fields.get("nationality"))
    mrz_nat = _normalise_nationality(mrz_fields.get("nationality"))

    if ocr_nat and mrz_nat:
        match = ocr_nat == mrz_nat
        checks.append({
            "field": "nationality",
            "visual_value": ocr_nat,
            "mrz_value": mrz_nat,
            "match": match,
            "severity": "low" if match else "medium",
            "reason": (
                "Nationality codes match."
                if match
                else "Printed nationality differs from MRZ nationality. "
                     "Manual verification recommended."
            ),
        })

    # ── Overall ───────────────────────────────────────────────────────────────
    overall_match = all(c["match"] for c in checks) if checks else True

    return {"overall_match": overall_match, "checks": checks}
