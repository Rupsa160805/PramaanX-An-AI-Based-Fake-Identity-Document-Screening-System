"""
PramaanX — Audit / Event Service
-----------------------------------
Creates safe, privacy-respecting audit records for verification operations.

Privacy principles:
  — Raw passport numbers, DOBs, and biometric data are NEVER stored in audit logs.
  — Only metadata (request ID, timestamp, checks executed, recommendation) is recorded.
  — Audit records support human-in-the-loop accountability.

In this MVP the audit record is returned as part of the API response so the
frontend/officer can review it.  In a production system, audit records would
also be written to a persistent, tamper-evident log store.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List

from app.core.config import settings


def create_audit(
    request_id: str,
    checks_executed: List[str],
    processing_time_ms: float,
) -> Dict[str, Any]:
    """
    Build an audit metadata record for a verification operation.

    Args:
        request_id:         Unique ID for this verification request.
        checks_executed:    List of pipeline steps that ran (e.g. ["ocr", "mrz"]).
        processing_time_ms: Wall-clock time in milliseconds.

    Returns a dict matching the AuditInfo schema.
    """
    return {
        "request_id": request_id,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "pipeline_version": settings.pipeline_version,
        "checks_executed": checks_executed,
        "processing_time_ms": round(processing_time_ms, 2),
    }
