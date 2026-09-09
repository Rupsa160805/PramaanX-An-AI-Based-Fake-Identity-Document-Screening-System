"""
PramaanX — Verification Request & Response Schemas
----------------------------------------------------
These schemas define the stable API contract between the FastAPI backend
and any frontend consumer (React, etc.).

IMPORTANT:
  Only fields that are ACTUALLY populated by existing AI modules are
  returned with real data.  Features that do not yet exist in the
  repository (face verification, liveness detection) are represented
  with status="not_available" and null payloads rather than fabricated values.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.common import (
    IssueCategory,
    ModuleStatus,
    RecommendedAction,
    RiskLevel,
    Severity,
)


# ──────────────────────────────────────────────────────────────────────────────
# Sub-schemas: Document / Quality
# ──────────────────────────────────────────────────────────────────────────────

class DocumentQuality(BaseModel):
    usable: bool
    warnings: List[str] = []


class DocumentInfo(BaseModel):
    type: str = "passport"
    quality: DocumentQuality


# ──────────────────────────────────────────────────────────────────────────────
# Sub-schemas: OCR
# ──────────────────────────────────────────────────────────────────────────────

class OcrFields(BaseModel):
    """
    Fields that the existing OCR module (ai/ocr.py) actually extracts.
    Only fields supported by the existing implementation are included here.
    """
    passport_number: Optional[str] = None
    date_of_birth: Optional[str] = None
    date_of_expiry: Optional[str] = None
    nationality: Optional[str] = None
    raw_text: Optional[str] = None


class OcrResult(BaseModel):
    status: ModuleStatus
    fields: Optional[OcrFields] = None
    error: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# Sub-schemas: MRZ
# ──────────────────────────────────────────────────────────────────────────────

class MrzCheckDigits(BaseModel):
    passport_number: Optional[bool] = None
    date_of_birth: Optional[bool] = None
    expiry_date: Optional[bool] = None


class MrzFields(BaseModel):
    document_type: Optional[str] = None
    country: Optional[str] = None
    surname: Optional[str] = None
    given_names: Optional[str] = None
    passport_number: Optional[str] = None
    nationality: Optional[str] = None
    date_of_birth: Optional[str] = None   # YYMMDD (MRZ format)
    sex: Optional[str] = None
    expiry_date: Optional[str] = None      # YYMMDD (MRZ format)


class MrzResult(BaseModel):
    status: ModuleStatus
    valid: Optional[bool] = None
    fields: Optional[MrzFields] = None
    checks: Optional[MrzCheckDigits] = None
    error: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# Sub-schemas: Consistency (Cross-Source Evidence Comparison)
# ──────────────────────────────────────────────────────────────────────────────

class ConsistencyCheck(BaseModel):
    field: str
    visual_value: Optional[str] = None
    mrz_value: Optional[str] = None
    match: bool
    severity: Severity
    reason: str


class ConsistencyResult(BaseModel):
    overall_match: bool
    checks: List[ConsistencyCheck] = []


# ──────────────────────────────────────────────────────────────────────────────
# Sub-schemas: Tampering
# ──────────────────────────────────────────────────────────────────────────────

class TamperingResult(BaseModel):
    """
    The existing tampering module (ai/tampering.py) produces only a single
    float probability value from a ResNet18 binary classifier.
    It does NOT produce heatmaps, bounding boxes, or region segmentation.
    Only what the model actually produces is returned here.
    """
    status: ModuleStatus
    detected: Optional[bool] = None
    confidence: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Probability that the document has been tampered (0–1). "
                    "Only available when the trained model file exists.",
    )
    note: Optional[str] = None
    error: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# Sub-schemas: Face Verification
# ──────────────────────────────────────────────────────────────────────────────

class FaceVerificationResult(BaseModel):
    """
    The face verification module does NOT exist in the current repository.
    Status is always 'not_available'.
    """
    status: ModuleStatus = ModuleStatus.not_available
    match: Optional[bool] = None
    reason: str = "Face verification module is not currently configured."


# ──────────────────────────────────────────────────────────────────────────────
# Sub-schemas: Liveness
# ──────────────────────────────────────────────────────────────────────────────

class LivenessResult(BaseModel):
    """
    Liveness detection does NOT exist in the current repository.
    Status is always 'not_available'.
    """
    status: ModuleStatus = ModuleStatus.not_available
    passed: Optional[bool] = None
    reason: str = "Liveness detection module is not currently configured."


# ──────────────────────────────────────────────────────────────────────────────
# Sub-schemas: Document Validation
# ──────────────────────────────────────────────────────────────────────────────

class ValidationIssue(BaseModel):
    category: IssueCategory
    code: str
    description: str
    severity: Severity


class ValidationResult(BaseModel):
    document_valid: bool
    issues: List[ValidationIssue] = []


# ──────────────────────────────────────────────────────────────────────────────
# Sub-schemas: Mock Database
# ──────────────────────────────────────────────────────────────────────────────

class DatabaseAlert(BaseModel):
    code: str
    description: str
    severity: Severity


class DatabaseCheckResult(BaseModel):
    """
    MOCK / SYNTHETIC DATA.
    Real government passport/watchlist databases are unavailable to this
    student prototype.  The mock layer is clearly labelled.
    """
    status: str = "mock"
    alerts: List[DatabaseAlert] = []
    note: str = (
        "Database checks are performed against mock/synthetic data only. "
        "Replace with an authorised government API in production."
    )


# ──────────────────────────────────────────────────────────────────────────────
# Sub-schemas: Risk Scoring
# ──────────────────────────────────────────────────────────────────────────────

class RiskContribution(BaseModel):
    component: str
    weight: float
    score_contribution: float
    reason: str


class RiskResult(BaseModel):
    score: float = Field(ge=0.0, le=100.0)
    level: RiskLevel
    reasons: List[str] = []
    contributions: List[RiskContribution] = []


# ──────────────────────────────────────────────────────────────────────────────
# Sub-schemas: Recommendation
# ──────────────────────────────────────────────────────────────────────────────

class RecommendationResult(BaseModel):
    action: RecommendedAction
    reason: str


# ──────────────────────────────────────────────────────────────────────────────
# Sub-schemas: Audit
# ──────────────────────────────────────────────────────────────────────────────

class AuditInfo(BaseModel):
    request_id: str
    timestamp: str
    pipeline_version: str
    checks_executed: List[str] = []
    processing_time_ms: Optional[float] = None


# ──────────────────────────────────────────────────────────────────────────────
# Top-level Verification Response
# ──────────────────────────────────────────────────────────────────────────────

class VerificationResponse(BaseModel):
    request_id: str
    status: str  # "completed" | "failed"

    document: DocumentInfo
    ocr: OcrResult
    mrz: MrzResult
    consistency: ConsistencyResult
    tampering: TamperingResult
    face_verification: FaceVerificationResult
    liveness: LivenessResult
    validation: ValidationResult
    database_checks: DatabaseCheckResult
    risk: RiskResult
    recommendation: RecommendationResult
    warnings: List[str] = []
    audit: AuditInfo

    model_config = {
        "json_schema_extra": {
            "example": {
                "request_id": "abc123",
                "status": "completed",
                "document": {
                    "type": "passport",
                    "quality": {"usable": True, "warnings": []},
                },
                "ocr": {"status": "completed", "fields": {"passport_number": "A1234567"}},
                "mrz": {
                    "status": "completed",
                    "valid": True,
                    "checks": {
                        "passport_number": True,
                        "date_of_birth": True,
                        "expiry_date": True,
                    },
                },
                "consistency": {"overall_match": True, "checks": []},
                "tampering": {"status": "not_available", "detected": None},
                "face_verification": {"status": "not_available"},
                "liveness": {"status": "not_available"},
                "validation": {"document_valid": True, "issues": []},
                "database_checks": {"status": "mock", "alerts": []},
                "risk": {"score": 12.0, "level": "low", "reasons": []},
                "recommendation": {
                    "action": "normal_clearance",
                    "reason": "No significant flags detected.",
                },
                "warnings": [],
                "audit": {
                    "request_id": "abc123",
                    "timestamp": "2026-09-09T20:47:41+05:30",
                    "pipeline_version": "1.0.0",
                    "checks_executed": ["ocr", "mrz", "validation", "consistency", "risk"],
                },
            }
        }
    }
