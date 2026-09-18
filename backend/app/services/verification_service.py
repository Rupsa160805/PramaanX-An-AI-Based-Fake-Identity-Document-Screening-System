"""
PramaanX — Verification Orchestration Service
-----------------------------------------------
This is the top-level service called by the API endpoint.

Responsibilities:
  1. Call the AI pipeline (ai/pipeline.py)
  2. Parse and normalise raw pipeline outputs into Pydantic schema objects
  3. Run cross-source consistency checks (validation_service.py)
  4. Build document validity summary (rule-based — no AI needed)
  5. Run mock database check (database_service.py)
  6. Compute explainable risk score (risk_service.py)
  7. Create audit record (audit_service.py)
  8. Assemble and return the full VerificationResponse

The AI pipeline and all AI-related logic live in ai/.
This service is the INTEGRATION/API layer only.
"""

from __future__ import annotations

import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger
from app.schemas.common import (
    IssueCategory,
    ModuleStatus,
    RecommendedAction,
    RiskLevel,
    Severity,
)
from app.schemas.verification import (
    AuditInfo,
    ConsistencyCheck,
    ConsistencyResult,
    DatabaseAlert,
    DatabaseCheckResult,
    DocumentInfo,
    DocumentQuality,
    FaceVerificationResult,
    LivenessResult,
    MrzCheckDigits,
    MrzFields,
    MrzResult,
    OcrFields,
    OcrResult,
    RecommendationResult,
    RiskContribution,
    RiskResult,
    TamperingResult,
    ValidationIssue,
    ValidationResult,
    VerificationResponse,
)
from app.services.audit_service import create_audit
from app.services.database_service import check_document
from app.services.risk_service import compute_risk
from app.services.validation_service import build_consistency_result

logger = get_logger(__name__)

# ── Lazy-import the AI pipeline ───────────────────────────────────────────────
# We import at call time (not module load time) to avoid startup failures
# when AI dependencies (PyTorch, EasyOCR) aren't installed.
def _get_pipeline():
    # sys.path manipulation ensures 'backend/' root is importable
    import os
    backend_root = os.path.join(os.path.dirname(__file__), "..", "..", "..")
    backend_root = os.path.abspath(backend_root)
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    from ai.pipeline import run_pipeline
    return run_pipeline


# ──────────────────────────────────────────────────────────────────────────────
# Normalisation helpers
# ──────────────────────────────────────────────────────────────────────────────

def _normalise_ocr(raw: Dict[str, Any]) -> OcrResult:
    status_str = raw.get("status", "failed")
    try:
        status = ModuleStatus(status_str)
    except ValueError:
        status = ModuleStatus.failed

    if status == ModuleStatus.completed and raw.get("fields"):
        f = raw["fields"]
        fields = OcrFields(
            passport_number=f.get("passport_number"),
            date_of_birth=f.get("date_of_birth"),
            date_of_expiry=f.get("date_of_expiry"),
            nationality=f.get("nationality"),
            raw_text=f.get("raw_text"),
        )
    else:
        fields = None

    return OcrResult(
        status=status,
        fields=fields,
        error=raw.get("error"),
    )


def _normalise_mrz(raw: Dict[str, Any]) -> MrzResult:
    status_str = raw.get("status", "failed")
    try:
        status = ModuleStatus(status_str)
    except ValueError:
        status = ModuleStatus.failed

    fields = None
    checks = None

    if status == ModuleStatus.completed and raw.get("fields"):
        f = raw["fields"]
        fields = MrzFields(
            document_type=f.get("document_type"),
            country=f.get("country"),
            surname=f.get("surname"),
            given_names=f.get("given_names"),
            passport_number=f.get("passport_number"),
            nationality=f.get("nationality"),
            date_of_birth=f.get("date_of_birth"),
            sex=f.get("sex"),
            expiry_date=f.get("expiry_date"),
        )
        if raw.get("checks"):
            c = raw["checks"]
            checks = MrzCheckDigits(
                passport_number=c.get("passport_number"),
                date_of_birth=c.get("date_of_birth"),
                expiry_date=c.get("expiry_date"),
            )

    return MrzResult(
        status=status,
        valid=raw.get("valid"),
        fields=fields,
        checks=checks,
        error=raw.get("error"),
    )


def _normalise_tampering(raw: Dict[str, Any]) -> TamperingResult:
    status_str = raw.get("status", "not_available")
    try:
        status = ModuleStatus(status_str)
    except ValueError:
        status = ModuleStatus.not_available

    return TamperingResult(
        status=status,
        detected=raw.get("detected"),
        confidence=raw.get("confidence"),
        note=raw.get("note"),
        error=raw.get("error"),
    )


def _normalise_consistency(raw: Dict[str, Any]) -> ConsistencyResult:
    checks = []
    for c in raw.get("checks", []):
        try:
            sev = Severity(c.get("severity", "low"))
        except ValueError:
            sev = Severity.low
        checks.append(
            ConsistencyCheck(
                field=c["field"],
                visual_value=c.get("visual_value"),
                mrz_value=c.get("mrz_value"),
                match=c.get("match", True),
                severity=sev,
                reason=c.get("reason", ""),
            )
        )
    return ConsistencyResult(
        overall_match=raw.get("overall_match", True),
        checks=checks,
    )


def _build_validation(mrz: MrzResult) -> ValidationResult:
    """
    Rule-based document validity checks derived from MRZ data.
    Distinguishes administrative issues from authenticity concerns.
    """
    issues: List[ValidationIssue] = []
    document_valid = True

    if mrz.status == ModuleStatus.completed and mrz.fields:
        # Check expiry
        expiry_yymmdd = mrz.fields.expiry_date
        if expiry_yymmdd and len(expiry_yymmdd) == 6:
            try:
                exp_date = datetime.strptime(expiry_yymmdd, "%y%m%d").date()
                today = datetime.now(timezone.utc).date()
                if exp_date < today:
                    document_valid = False
                    issues.append(
                        ValidationIssue(
                            category=IssueCategory.administrative,
                            code="DOCUMENT_EXPIRED",
                            description=(
                                f"The document expired on "
                                f"{exp_date.strftime('%d %B %Y')}. "
                                "Note: an expired document is an administrative issue, "
                                "not necessarily evidence of forgery."
                            ),
                            severity=Severity.high,
                        )
                    )
            except ValueError:
                issues.append(
                    ValidationIssue(
                        category=IssueCategory.administrative,
                        code="EXPIRY_DATE_PARSE_ERROR",
                        description="Expiry date from MRZ could not be parsed.",
                        severity=Severity.medium,
                    )
                )

        # MRZ check-digit failures
        if mrz.checks:
            if mrz.checks.passport_number is False:
                issues.append(
                    ValidationIssue(
                        category=IssueCategory.authenticity,
                        code="MRZ_PASSPORT_CHECKDIGIT_FAIL",
                        description=(
                            "Passport number ICAO check digit failed. "
                            "Possible OCR error or data alteration."
                        ),
                        severity=Severity.high,
                    )
                )
            if mrz.checks.date_of_birth is False:
                issues.append(
                    ValidationIssue(
                        category=IssueCategory.authenticity,
                        code="MRZ_DOB_CHECKDIGIT_FAIL",
                        description="Date of birth ICAO check digit failed.",
                        severity=Severity.high,
                    )
                )
            if mrz.checks.expiry_date is False:
                issues.append(
                    ValidationIssue(
                        category=IssueCategory.authenticity,
                        code="MRZ_EXPIRY_CHECKDIGIT_FAIL",
                        description="Expiry date ICAO check digit failed.",
                        severity=Severity.high,
                    )
                )

    return ValidationResult(
        document_valid=document_valid,
        issues=issues,
    )


def _normalise_db(raw: Dict[str, Any]) -> DatabaseCheckResult:
    alerts = []
    for a in raw.get("alerts", []):
        try:
            sev = Severity(a.get("severity", "low"))
        except ValueError:
            sev = Severity.low
        alerts.append(
            DatabaseAlert(
                code=a.get("code", "UNKNOWN"),
                description=a.get("description", ""),
                severity=sev,
            )
        )
    return DatabaseCheckResult(
        status=raw.get("status", "mock"),
        alerts=alerts,
        note=raw.get("note", ""),
    )


def _normalise_risk(raw: Dict[str, Any]) -> tuple[RiskResult, RecommendationResult]:
    contributions = [
        RiskContribution(**c)
        for c in raw.get("contributions", [])
    ]
    try:
        level = RiskLevel(raw["level"])
    except (KeyError, ValueError):
        level = RiskLevel.low
    try:
        action = RecommendedAction(raw["action"])
    except (KeyError, ValueError):
        action = RecommendedAction.normal_clearance

    risk = RiskResult(
        score=raw.get("score", 0.0),
        level=level,
        reasons=raw.get("reasons", []),
        contributions=contributions,
    )
    recommendation = RecommendationResult(
        action=action,
        reason=raw.get("recommendation_reason", ""),
    )
    return risk, recommendation


# ──────────────────────────────────────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────────────────────────────────────

def run_verification(image_path: str) -> VerificationResponse:
    """
    Orchestrate the full PramaanX verification pipeline for one document image.

    Args:
        image_path: Path to the (already validated) temporary document image file.

    Returns:
        Complete VerificationResponse Pydantic object.
    """
    request_id = uuid.uuid4().hex
    t_start = time.monotonic()
    checks_executed: List[str] = []
    warnings: List[str] = []

    logger.info("Verification started — request_id=%s", request_id)

    # ── Run AI Pipeline ───────────────────────────────────────────────────────
    try:
        run_pipeline = _get_pipeline()
        pipeline_result = run_pipeline(image_path)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Pipeline execution failed: %s", exc)
        raise RuntimeError("AI pipeline encountered an unexpected error.") from exc

    raw_preprocessing = pipeline_result.get("preprocessing", {})
    raw_ocr = pipeline_result.get("ocr", {})
    raw_mrz = pipeline_result.get("mrz", {})
    raw_tampering = pipeline_result.get("tampering", {})

    # ── Document quality from preprocessing ───────────────────────────────────
    quality_warnings = list(raw_preprocessing.get("warnings", []))
    document_usable = bool(raw_preprocessing.get("usable", True))
    if quality_warnings:
        warnings.extend(quality_warnings)
    if not document_usable:
        warnings.append("Image quality may be insufficient for reliable analysis.")

    document_info = DocumentInfo(
        type="passport",
        quality=DocumentQuality(
            usable=document_usable,
            warnings=quality_warnings,
        ),
    )

    # ── Normalise AI outputs ──────────────────────────────────────────────────
    ocr_result = _normalise_ocr(raw_ocr)
    mrz_result = _normalise_mrz(raw_mrz)
    tampering_result = _normalise_tampering(raw_tampering)

    if ocr_result.status == ModuleStatus.completed:
        checks_executed.append("ocr")
    if mrz_result.status == ModuleStatus.completed:
        checks_executed.append("mrz")
    if tampering_result.status == ModuleStatus.completed:
        checks_executed.append("tampering")
    else:
        warnings.append(
            "Tampering detection was not performed. "
            + (tampering_result.note or "")
        )

    # ── Consistency check ─────────────────────────────────────────────────────
    raw_consistency = build_consistency_result(raw_ocr, raw_mrz)
    consistency_result = _normalise_consistency(raw_consistency)
    if raw_ocr.get("status") == "completed" and raw_mrz.get("status") == "completed":
        checks_executed.append("consistency")

    # ── Rule-based validation ────────────────────────────────────────────────
    validation_result = _build_validation(mrz_result)
    checks_executed.append("validation")

    # ── Database check ────────────────────────────────────────────────────────
    passport_number_for_db = (
        (mrz_result.fields.passport_number if mrz_result.fields else None)
        or (ocr_result.fields.passport_number if ocr_result.fields else None)
    )
    raw_db = check_document(passport_number_for_db)
    db_result = _normalise_db(raw_db)
    checks_executed.append("database_mock")

    # ── Risk scoring ──────────────────────────────────────────────────────────
    validation_issues_raw = [
        {
            "code": i.code,
            "severity": i.severity.value,
            "category": i.category.value,
        }
        for i in validation_result.issues
    ]
    db_alerts_raw = [
        {"code": a.code, "severity": a.severity.value}
        for a in db_result.alerts
    ]
    raw_risk = compute_risk(
        mrz=raw_mrz,
        consistency=raw_consistency,
        tampering=raw_tampering,
        validation_issues=validation_issues_raw,
        db_alerts=db_alerts_raw,
    )
    risk_result, recommendation_result = _normalise_risk(raw_risk)
    checks_executed.append("risk")

    # ── Always-unavailable modules ────────────────────────────────────────────
    face_result = FaceVerificationResult()
    liveness_result = LivenessResult()

    # ── Audit ─────────────────────────────────────────────────────────────────
    t_end = time.monotonic()
    processing_ms = (t_end - t_start) * 1000
    raw_audit = create_audit(
        request_id=request_id,
        checks_executed=checks_executed,
        processing_time_ms=processing_ms,
    )
    audit_info = AuditInfo(**raw_audit)

    logger.info(
        "Verification complete — request_id=%s risk=%s action=%s time=%.0fms",
        request_id,
        risk_result.level.value,
        recommendation_result.action.value,
        processing_ms,
    )

    return VerificationResponse(
        request_id=request_id,
        status="completed",
        document=document_info,
        ocr=ocr_result,
        mrz=mrz_result,
        consistency=consistency_result,
        tampering=tampering_result,
        face_verification=face_result,
        liveness=liveness_result,
        validation=validation_result,
        database_checks=db_result,
        risk=risk_result,
        recommendation=recommendation_result,
        warnings=warnings,
        audit=audit_info,
    )
