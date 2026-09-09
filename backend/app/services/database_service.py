"""
PramaanX — Mock Database Service
-----------------------------------
Because real government passport/watchlist databases are unavailable to this
student prototype, this module provides a clearly labelled MOCK implementation.

Design intention:
  — The interface is identical in shape to what a real government API would return.
  — A future authorised integrator can replace this module's implementation
    without changing any caller code.
  — Mock data is clearly labelled at every level.

DO NOT connect this to real identity databases.
DO NOT call unknown third-party "passport lookup" APIs.
DO NOT hardcode fake government credentials.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


# Mock "document status" records — purely synthetic, no real data
_MOCK_FLAGGED_DOCUMENTS: Dict[str, Dict[str, str]] = {
    # Format: passport_number (uppercased, no fillers) → alert record
    # These are fictional document numbers for demonstration only
    "DEMO1234X": {
        "code": "REPORTED_LOST",
        "description": "This document has been reported lost. (MOCK DATA — NOT REAL)",
        "severity": "high",
    },
    "TEST9999Z": {
        "code": "REPORTED_STOLEN",
        "description": "This document has been reported stolen. (MOCK DATA — NOT REAL)",
        "severity": "high",
    },
}


def check_document(passport_number: Optional[str]) -> Dict[str, Any]:
    """
    Perform a mock document status check.

    In a real deployment, this function would call an authorised government
    passport/watchlist API with appropriate authentication and data-sharing
    agreements.

    Returns a dict matching the DatabaseCheckResult schema.
    Always includes a note clearly identifying the result as MOCK/SYNTHETIC.
    """
    alerts: List[Dict[str, str]] = []

    if passport_number:
        pn_clean = passport_number.upper().replace("<", "").replace(" ", "")
        if pn_clean in _MOCK_FLAGGED_DOCUMENTS:
            alerts.append(_MOCK_FLAGGED_DOCUMENTS[pn_clean])

    return {
        "status": "mock",
        "alerts": alerts,
        "note": (
            "Database checks are performed against mock/synthetic data only. "
            "No real government database has been queried. "
            "Replace with an authorised government API in production."
        ),
    }
