"""
PramaanX — Common / Shared Schema Types
"""

from enum import Enum


class ModuleStatus(str, Enum):
    """
    Generic status for any pipeline module.
    Use 'not_available' for capabilities that do not exist in the
    current repository.  Never fabricate results for unavailable modules.
    """
    completed = "completed"
    failed = "failed"
    not_available = "not_available"
    skipped = "skipped"


class RiskLevel(str, Enum):
    low = "low"          # score 0–29
    medium = "medium"    # score 30–59
    high = "high"        # score 60–100


class RecommendedAction(str, Enum):
    normal_clearance = "normal_clearance"
    manual_verification = "manual_verification"
    secondary_inspection = "secondary_inspection"


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class IssueCategory(str, Enum):
    """
    Distinguishes authenticity/forgery signals from administrative
    rule violations.  An expired visa is NOT a forgery signal.
    """
    authenticity = "authenticity"
    administrative = "administrative"
