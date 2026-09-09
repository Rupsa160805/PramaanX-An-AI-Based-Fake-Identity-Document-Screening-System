"""
PramaanX — Risk Scoring Service
---------------------------------
Produces an explainable, weighted risk score from pipeline evidence.

Design principles:
  — Every score contribution is individually labelled and explained.
  — The score is a decision-support signal, NOT a verdict.
  — Missing evidence is not treated as "safe" — it is treated as "unknown".
  — An expired visa contributes to risk differently from tampering evidence.
  — No module can by itself force an automatic rejection.

Risk bands:
   0–29  → LOW    → Normal officer clearance
  30–59  → MEDIUM → Manual document verification
  60–100 → HIGH   → Secondary inspection

Weights (conceptual, modular — adjust per policy):
  Tampering signal       : up to 40 pts
  MRZ check-digit fail   : up to 20 pts
  Cross-source mismatch  : up to 20 pts (severe mismatches)
  Expiry / admin issues  : up to 10 pts
  Database alerts        : up to 10 pts
"""

from __future__ import annotations

from typing import Any, Dict, List

from app.schemas.common import RecommendedAction, RiskLevel
from app.core.logging import get_logger

logger = get_logger(__name__)


def _clamp(v: float) -> float:
    return max(0.0, min(100.0, v))


def compute_risk(
    mrz: Dict[str, Any],
    consistency: Dict[str, Any],
    tampering: Dict[str, Any],
    validation_issues: List[Dict[str, Any]],
    db_alerts: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Compute weighted risk score from available pipeline signals.

    Returns a dict matching the RiskResult schema.
    """
    score = 0.0
    reasons: List[str] = []
    contributions: List[Dict[str, Any]] = []

    # ── Component 1: Tampering (up to 40 pts) ─────────────────────────────────
    if tampering.get("status") == "completed":
        conf = float(tampering.get("confidence") or 0.0)
        component_score = _clamp(conf * 40.0)
        if conf >= 0.5:
            reasons.append(
                f"Tampering classifier flagged the document "
                f"(confidence {conf:.0%})."
            )
        contributions.append({
            "component": "tampering_classifier",
            "weight": 0.40,
            "score_contribution": round(component_score, 2),
            "reason": (
                f"ResNet18 tamper probability: {conf:.4f} × weight 0.40 × 100"
                if tampering.get("status") == "completed"
                else "Tampering model unavailable."
            ),
        })
        score += component_score
    else:
        contributions.append({
            "component": "tampering_classifier",
            "weight": 0.40,
            "score_contribution": 0.0,
            "reason": "Tampering module not available — contribution scored as 0.",
        })

    # ── Component 2: MRZ check-digit failures (up to 20 pts) ─────────────────
    mrz_checks = mrz.get("checks") or {}
    failed_checks = [k for k, v in mrz_checks.items() if v is False]
    if mrz.get("status") == "completed":
        mrz_penalty = len(failed_checks) * 7.0  # up to 21 (clamped at 20)
        mrz_penalty = _clamp(mrz_penalty)
        mrz_penalty = min(mrz_penalty, 20.0)
        if failed_checks:
            reasons.append(
                f"MRZ check-digit failure(s): {', '.join(failed_checks)}."
            )
        contributions.append({
            "component": "mrz_check_digits",
            "weight": 0.20,
            "score_contribution": round(mrz_penalty, 2),
            "reason": (
                f"Failed check digits: {failed_checks}"
                if failed_checks
                else "All MRZ check digits passed."
            ),
        })
        score += mrz_penalty
    else:
        contributions.append({
            "component": "mrz_check_digits",
            "weight": 0.20,
            "score_contribution": 0.0,
            "reason": "MRZ not available — contribution scored as 0.",
        })

    # ── Component 3: Cross-source mismatches (up to 20 pts) ──────────────────
    mismatch_checks = consistency.get("checks") or []
    high_mismatches = [
        c for c in mismatch_checks
        if not c.get("match") and c.get("severity") in ("high", "medium")
    ]
    if mismatch_checks:
        mismatch_penalty = len(high_mismatches) * 8.0
        mismatch_penalty = min(_clamp(mismatch_penalty), 20.0)
        if high_mismatches:
            fields = [c["field"] for c in high_mismatches]
            reasons.append(
                f"Cross-source inconsistency in field(s): {', '.join(fields)}."
            )
        contributions.append({
            "component": "cross_source_consistency",
            "weight": 0.20,
            "score_contribution": round(mismatch_penalty, 2),
            "reason": (
                f"High/medium severity mismatches: {[c['field'] for c in high_mismatches]}"
                if high_mismatches
                else "All compared fields are consistent."
            ),
        })
        score += mismatch_penalty
    else:
        contributions.append({
            "component": "cross_source_consistency",
            "weight": 0.20,
            "score_contribution": 0.0,
            "reason": "No cross-source checks were possible.",
        })

    # ── Component 4: Expiry / administrative issues (up to 10 pts) ───────────
    admin_issues = [
        i for i in validation_issues
        if i.get("severity") in ("high", "medium")
    ]
    admin_penalty = min(len(admin_issues) * 5.0, 10.0)
    if admin_issues:
        reasons.append(
            f"Administrative issue(s) detected: "
            f"{[i['code'] for i in admin_issues]}."
        )
    contributions.append({
        "component": "administrative_validity",
        "weight": 0.10,
        "score_contribution": round(admin_penalty, 2),
        "reason": (
            f"Issues: {[i['code'] for i in admin_issues]}"
            if admin_issues
            else "No administrative issues."
        ),
    })
    score += admin_penalty

    # ── Component 5: Database alerts (up to 10 pts) ───────────────────────────
    high_alerts = [
        a for a in db_alerts
        if a.get("severity") in ("high", "medium")
    ]
    db_penalty = min(len(high_alerts) * 10.0, 10.0)
    if high_alerts:
        reasons.append("Database alert(s) detected. Mandatory manual review.")
    contributions.append({
        "component": "database_alerts",
        "weight": 0.10,
        "score_contribution": round(db_penalty, 2),
        "reason": (
            f"Alert(s): {[a['code'] for a in high_alerts]}"
            if high_alerts
            else "No database alerts (mock check)."
        ),
    })
    score += db_penalty

    # ── Force escalation on database alert ───────────────────────────────────
    force_escalation = bool(high_alerts)

    score = round(_clamp(score), 2)

    if score < 30 and not force_escalation:
        level = RiskLevel.low
        action = RecommendedAction.normal_clearance
        recommendation_reason = (
            "No significant flags detected. "
            "Normal officer processing recommended."
        )
    elif score < 60 and not force_escalation:
        level = RiskLevel.medium
        action = RecommendedAction.manual_verification
        recommendation_reason = (
            "One or more signals warrant closer inspection. "
            "Manual document verification recommended."
        )
    else:
        level = RiskLevel.high
        action = RecommendedAction.secondary_inspection
        recommendation_reason = (
            "Multiple high-severity signals detected. "
            "Secondary inspection required."
        )

    return {
        "score": score,
        "level": level.value,
        "reasons": reasons,
        "contributions": contributions,
        "action": action.value,
        "recommendation_reason": recommendation_reason,
    }
