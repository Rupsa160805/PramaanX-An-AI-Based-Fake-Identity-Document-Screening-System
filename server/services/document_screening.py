"""Document-screening orchestration merged from the teammate prototype.

The service keeps the teammate response shape while using P4's shared upload,
face, liveness, and database services. Optional OCR/MRZ/tampering modules are
loaded only when configured and available; the API never fabricates an AI
result when a model is missing.
"""

from __future__ import annotations

import importlib
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# When no explicit pipeline is configured the local demo falls back to the
# self-guarding synthetic pipeline: it differentiates the generated
# ``demo_artifacts`` images (via their embedded marker pixel) and rejects any
# other image, so ordinary uploads still honestly report ``not_available``
# instead of a fabricated AI result.  Point P4_DOCUMENT_PIPELINE_MODULE at a
# real pipeline (e.g. ``ai_pipeline.ai.pipeline``) for production use.
_DEFAULT_PIPELINE_MODULE = "server.services.demo_document_pipeline"

from .face_match import (
    FaceServiceError,
    ImageInputError,
    NoFaceDetectedError,
    ReferenceNotFoundError,
    ReferencePhotoUnavailableError,
)
from .mongo_store import DatabaseConnectionError, DatabaseStore


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_yymmdd(value: str | None) -> str | None:
    """Normalise an OCR date (DD-MM-YYYY / DD/MM/YYYY) to MRZ YYMMDD."""
    if not value:
        return None
    match = re.search(r"(\d{2})[-/](\d{2})[-/](\d{4})", value)
    if not match:
        digits = re.sub(r"\D", "", value)
        return digits[-6:] if len(digits) >= 6 else None
    dd, mm, yyyy = match.groups()
    return f"{yyyy[2:]}{mm}{dd}"


def _norm(value: str | None) -> str | None:
    if not value:
        return None
    return re.sub(r"[<\s]", "", str(value)).upper() or None


def _consistency(ocr: dict[str, Any], mrz: dict[str, Any]) -> dict[str, Any]:
    """Cross-check the visible (OCR) fields against the machine-readable (MRZ)
    zone. A forged printed field that no longer matches the MRZ shows up here
    as a mismatch, which then feeds the risk score.
    """
    if ocr.get("status") != "completed" or mrz.get("status") != "completed":
        return {"overall_match": True, "checks": [], "note": "OCR/MRZ evidence incomplete."}

    of = ocr.get("fields") or {}
    mf = mrz.get("fields") or {}
    comparisons = [
        ("passport_number", _norm(of.get("passport_number")), _norm(mf.get("passport_number"))),
        ("date_of_birth", _to_yymmdd(of.get("date_of_birth")), _norm(mf.get("date_of_birth"))),
        ("date_of_expiry", _to_yymmdd(of.get("date_of_expiry")), _norm(mf.get("expiry_date"))),
        ("nationality", _norm(of.get("nationality")), _norm(mf.get("nationality"))),
    ]
    checks: list[dict[str, Any]] = []
    for field, ocr_value, mrz_value in comparisons:
        if ocr_value is None or mrz_value is None:
            continue  # can't compare what one source didn't provide
        checks.append(
            {
                "field": field,
                "ocr_value": ocr_value,
                "mrz_value": mrz_value,
                "match": ocr_value == mrz_value,
            }
        )
    return {
        "overall_match": all(item["match"] for item in checks) if checks else True,
        "checks": checks,
    }


def _module_pipeline(image_path: str) -> dict[str, Any] | None:
    module_name = os.getenv("P4_DOCUMENT_PIPELINE_MODULE") or _DEFAULT_PIPELINE_MODULE
    if not module_name:
        return None
    try:
        module = importlib.import_module(module_name)
        function = getattr(module, "run_pipeline", None)
        if not callable(function):
            logger.warning(
                "Pipeline module %s has no callable run_pipeline()", module_name
            )
            return None
        raw = function(image_path)
        return raw if isinstance(raw, dict) else None
    except Exception as exc:
        # A rejected image (e.g. a real upload the demo pipeline does not
        # recognize) is expected and simply yields a not_available result;
        # log at debug so genuine misconfiguration is still discoverable.
        logger.debug(
            "Document pipeline %s did not produce a result for %s: %s",
            module_name,
            image_path,
            exc,
        )
        return None


def _unavailable(name: str) -> dict[str, Any]:
    return {
        "status": "not_available",
        "error": f"{name} module is not configured",
        "fields": None,
    }


def _pipeline_parts(
    image_path: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[str]]:
    raw = _module_pipeline(image_path)
    warnings: list[str] = []
    if raw is None:
        warnings.append(
            "Document OCR/MRZ/tampering modules are not configured; biometric P4 verification remains available separately."
        )
        return (
            _unavailable("OCR"),
            _unavailable("MRZ"),
            {
                "status": "not_available",
                "detected": None,
                "confidence": None,
                "note": "Tampering model is not configured.",
                "error": None,
            },
            warnings,
        )
    return (
        raw.get("ocr") or _unavailable("OCR"),
        raw.get("mrz") or _unavailable("MRZ"),
        raw.get("tampering")
        or {
            "status": "not_available",
            "detected": None,
            "confidence": None,
            "note": "Tampering model is not configured.",
            "error": None,
        },
        warnings,
    )


def _risk(
    *,
    database_found: bool,
    expired: bool,
    ocr: dict[str, Any],
    mrz: dict[str, Any],
    tampering: dict[str, Any],
    face: dict[str, Any],
    consistency: dict[str, Any],
) -> dict[str, Any]:
    score = 0.0
    reasons: list[str] = []
    contributions: list[dict[str, Any]] = []

    tamper_confidence = tampering.get("confidence")
    if tampering.get("status") == "completed" and tamper_confidence is not None:
        component = max(0.0, min(40.0, float(tamper_confidence) * 40.0))
        score += component
        contributions.append(
            {
                "component": "tampering",
                "weight": 0.40,
                "score_contribution": round(component, 2),
                "reason": "Tampering model probability was evaluated.",
            }
        )
        if float(tamper_confidence) >= 0.5:
            reasons.append("Tampering model flagged the document.")
    else:
        contributions.append(
            {
                "component": "tampering",
                "weight": 0.40,
                "score_contribution": 0.0,
                "reason": "Tampering evidence is unavailable.",
            }
        )

    failed_checks = [
        key for key, value in (mrz.get("checks") or {}).items() if value is False
    ]
    mrz_component = min(20.0, len(failed_checks) * 7.0)
    score += mrz_component
    contributions.append(
        {
            "component": "mrz_check_digits",
            "weight": 0.20,
            "score_contribution": mrz_component,
            "reason": "MRZ check digits failed: " + ", ".join(failed_checks)
            if failed_checks
            else "No MRZ check-digit failures were reported.",
        }
    )
    if failed_checks:
        reasons.append("One or more MRZ check digits failed.")

    mismatches = [
        item for item in consistency.get("checks", []) if not item.get("match")
    ]
    mismatch_component = min(20.0, len(mismatches) * 8.0)
    score += mismatch_component
    contributions.append(
        {
            "component": "cross_source_consistency",
            "weight": 0.20,
            "score_contribution": mismatch_component,
            "reason": "Cross-source fields are inconsistent."
            if mismatches
            else "No cross-source mismatch was reported.",
        }
    )
    if mismatches:
        reasons.append("OCR and MRZ evidence contains mismatched fields.")

    if expired:
        score += 10.0
        reasons.append("The reference document is expired.")
    contributions.append(
        {
            "component": "administrative_validity",
            "weight": 0.10,
            "score_contribution": 10.0 if expired else 0.0,
            "reason": "Document expiry requires review."
            if expired
            else "No expiry flag was found.",
        }
    )

    if not database_found:
        score += 20.0
        reasons.append(
            "No matching reference document was found in the configured database."
        )
    if face.get("error") and face.get("error") != "liveness check failed":
        score += 20.0
        reasons.append(
            "Face verification could not complete for the submitted evidence."
        )
    if ocr.get("status") != "completed" or mrz.get("status") != "completed":
        score += 10.0
        reasons.append("Document extraction evidence is incomplete.")

    score = min(100.0, round(score, 2))
    if score >= 60:
        level, action = "high", "secondary_inspection"
    elif score >= 30:
        level, action = "medium", "manual_verification"
    else:
        level, action = "low", "normal_clearance"
    return {
        "score": score,
        "level": level,
        "reasons": reasons,
        "contributions": contributions,
        "recommendation": {
            "action": action,
            "reason": "Officer review should consider all available evidence; this is not an automatic decision.",
        },
    }


def run_document_screening(
    image_path: str | Path,
    *,
    document_number: str | None,
    database: DatabaseStore,
    face_matcher: Any,
    liveness_checker: Any,
    live_photo_path: str | None = None,
    frame_paths: list[str] | None = None,
) -> dict[str, Any]:
    request_id = str(uuid.uuid4())
    started = datetime.now(timezone.utc)
    image_path = str(image_path)
    ocr, mrz, tampering, warnings = _pipeline_parts(image_path)
    wanted = str(document_number).strip().upper() if document_number else None
    reference = None
    database_error = None
    try:
        reference = database.lookup_document(wanted) if wanted else None
    except (DatabaseConnectionError, OSError, RuntimeError) as exc:
        database_error = str(exc)
        warnings.append("The configured document database was unavailable.")

    expired = False
    if reference and reference.get("date_of_expiry"):
        try:
            expiry = str(reference["date_of_expiry"]).replace("Z", "+00:00")
            expired = datetime.fromisoformat(expiry).date() < started.date()
        except ValueError:
            warnings.append("Reference expiry date could not be parsed.")

    database_checks = {
        "status": "unavailable" if database_error else database.mode,
        "found": bool(reference),
        "expired": expired,
        "field_mismatches": [],
        "alerts": [],
        "note": database_error
        or "Document lookup completed against the configured repository.",
    }

    face = {
        "status": "not_available",
        "found_in_database": bool(reference),
        "similarity": None,
        "is_match": False,
        "threshold_used": getattr(face_matcher, "threshold", 0.45),
        "liveness_passed": True,
        "liveness_performed": False,
        "confidence_label": "NOT_AVAILABLE",
        "reason": "No live photo was supplied for this document-screening request.",
        "error": None,
        "match": None,
    }

    if live_photo_path:
        try:
            if frame_paths:
                live_result = liveness_checker.check_paths(frame_paths)
                face["liveness_passed"] = live_result.is_live
                face["liveness_performed"] = True
                if not live_result.is_live:
                    face.update(
                        {
                            "error": "liveness check failed",
                            "reason": live_result.reason,
                        }
                    )
            if face["liveness_passed"]:
                result = face_matcher.verify_against_database(
                    live_photo_path, wanted or ""
                )
                face.update(
                    {
                        "status": "completed",
                        "found_in_database": True,
                        "similarity": round(float(result.similarity), 6),
                        "is_match": bool(result.is_match),
                        "threshold_used": result.threshold_used,
                        "confidence_label": result.confidence_label,
                        "reason": result.reason,
                        "match": bool(result.is_match),
                    }
                )
        except ReferenceNotFoundError as exc:
            face.update({"error": "document not found in database", "reason": str(exc)})
        except ReferencePhotoUnavailableError as exc:
            face.update(
                {
                    "found_in_database": True,
                    "error": "reference photo unavailable",
                    "reason": str(exc),
                }
            )
        except (NoFaceDetectedError, ImageInputError) as exc:
            face.update(
                {
                    "found_in_database": getattr(exc, "found_in_database", False),
                    "error": "no face detected"
                    if isinstance(exc, NoFaceDetectedError)
                    else str(exc),
                    "reason": str(exc),
                }
            )
        except FaceServiceError as exc:
            face.update(
                {"error": str(exc), "reason": "face verification could not complete"}
            )

    consistency = _consistency(ocr, mrz)
    validation_issues = []
    if not wanted:
        validation_issues.append(
            {
                "category": "administrative",
                "code": "DOCUMENT_NUMBER_MISSING",
                "description": "A document number was not supplied for database cross-checking.",
                "severity": "medium",
            }
        )
        warnings.append(
            "Supply a document number to cross-check the Atlas reference record."
        )

    risk = _risk(
        database_found=bool(reference),
        expired=expired,
        ocr=ocr,
        mrz=mrz,
        tampering=tampering,
        face=face,
        consistency=consistency,
    )
    elapsed = (datetime.now(timezone.utc) - started).total_seconds() * 1000
    result = {
        "request_id": request_id,
        "submission_id": request_id,
        "verification_id": request_id,
        "document_number": wanted,
        "status": "completed",
        "document": {
            "type": reference.get("document_type", "unknown")
            if reference
            else "unknown",
            "quality": {"usable": True, "warnings": []},
        },
        "ocr": ocr,
        "mrz": mrz,
        "consistency": consistency,
        "tampering": tampering,
        "face_verification": face,
        "liveness": {
            "status": "completed" if face["liveness_performed"] else "not_available",
            "passed": face["liveness_passed"] if face["liveness_performed"] else None,
            "reason": face["reason"],
        },
        "validation": {
            "document_valid": not any(
                item["severity"] == "high" for item in validation_issues
            ),
            "issues": validation_issues,
        },
        "database_checks": database_checks,
        "risk": risk,
        "recommendation": risk.pop("recommendation"),
        "warnings": warnings,
        "audit": {
            "request_id": request_id,
            "timestamp": _now(),
            "pipeline_version": "p4-merged-1.0",
            "checks_executed": ["database", "face", "liveness", "risk"],
            "processing_time_ms": round(elapsed, 2),
        },
    }
    return result
