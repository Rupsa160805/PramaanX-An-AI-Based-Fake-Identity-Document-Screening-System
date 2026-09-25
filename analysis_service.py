"""
PramaanX - Person 3: Analysis Service / H2

Responsibilities:
1. Receiving existing AI/tampering-analysis result.
2. Receiving H1 from INPUT layer.
3. Generating H2.
4. Creating ANALYSIS blockchain record.
5. Saving the record through a mock blockchain during independent testing.
6. Verifying the ANALYSIS record.

During final integration, the mock blockchain adapter is being
replaced with Person 1's real blockchain service.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Optional

from analysis_hash import generate_h2


# ============================================================
# MOCK BLOCKCHAIN
# ============================================================

# Temporary in-memory blockchain storage.
#
# This exists only for independent development and testing.
#
# Person 1's real blockchain service will replace this during
# final integration.

_MOCK_BLOCKCHAIN: Dict[
    tuple[str, str],
    Dict[str, Any]
] = {}


def save_to_blockchain(
    record: Dict[str, Any]
) -> bool:
    """
    Development-only mock blockchain function.

    The real implementation will eventually be supplied by
    Person 1.
    """

    key = (
        record["verification_id"],
        record["record_type"],
    )

    _MOCK_BLOCKCHAIN[key] = deepcopy(record)

    print(
        "MOCK BLOCKCHAIN:",
        record
    )

    return True


def get_from_blockchain(
    verification_id: str,
    record_type: str = "ANALYSIS",
) -> Optional[Dict[str, Any]]:
    """
    Retrieve an ANALYSIS record from the mock blockchain.
    """

    key = (
        verification_id,
        record_type,
    )

    record = _MOCK_BLOCKCHAIN.get(key)

    if record is None:
        return None

    return deepcopy(record)


# ============================================================
# CREATE ANALYSIS RECORD
# ============================================================

def create_analysis_record(
    verification_id: str,
    analysis_result: Dict[str, Any],
    previous_hash: str,
) -> Dict[str, Any]:
    """
    Create the fixed ANALYSIS blockchain record.

    Parameters
    ----------
    verification_id:
        PramaanX verification identifier.

    analysis_result:
        Existing AI/tampering-analysis result.

    previous_hash:
        H1 from INPUT layer.

    Returns
    -------
    dict

    {
        "verification_id": "...",
        "record_type": "ANALYSIS",
        "hash": "H2",
        "previous_hash": "H1"
    }
    """

    if not verification_id:
        raise ValueError(
            "verification_id is required"
        )

    if not previous_hash:
        raise ValueError(
            "previous_hash (H1) is required"
        )

    if not isinstance(analysis_result, dict):
        raise TypeError(
            "analysis_result must be a dictionary"
        )

    # --------------------------------------------------------
    # Generate H2
    # --------------------------------------------------------

    h2 = generate_h2(
        verification_id=verification_id,
        analysis_result=analysis_result,
        previous_hash=previous_hash,
    )

    # --------------------------------------------------------
    # Fixed ANALYSIS record
    # --------------------------------------------------------

    record = {
        "verification_id": verification_id,
        "record_type": "ANALYSIS",
        "hash": h2,
        "previous_hash": previous_hash,
    }

    # --------------------------------------------------------
    # Save record
    # --------------------------------------------------------

    success = save_to_blockchain(record)

    if not success:
        raise RuntimeError(
            "Failed to save ANALYSIS record"
        )

    return record


# ============================================================
# VERIFY ANALYSIS RECORD
# ============================================================

def verify_analysis_record(
    verification_id: str,
    analysis_result: Dict[str, Any],
    previous_hash: str,
) -> Dict[str, Any]:
    """
    Recalculate H2 and compare it against the blockchain-stored H2.

    Returns a dictionary containing:

    {
        "verification_id": "...",
        "record_type": "ANALYSIS",
        "status": "MATCH",
        "current_hash": "...",
        "stored_hash": "..."
    }
    """

    stored_record = get_from_blockchain(
        verification_id=verification_id,
        record_type="ANALYSIS",
    )

    if stored_record is None:

        return {
            "verification_id": verification_id,
            "record_type": "ANALYSIS",
            "status": "NOT_FOUND",
            "current_hash": None,
            "stored_hash": None,
        }

    stored_hash = stored_record["hash"]

    # Recalculate H2 using the current analysis result.
    current_hash = generate_h2(
        verification_id=verification_id,
        analysis_result=analysis_result,
        previous_hash=previous_hash,
    )

    is_match = (
        current_hash == stored_hash
    )

    return {
        "verification_id": verification_id,
        "record_type": "ANALYSIS",
        "status": (
            "MATCH"
            if is_match
            else "MISMATCH"
        ),
        "current_hash": current_hash,
        "stored_hash": stored_hash,
    }


# ============================================================
# INDEPENDENT P3 TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 70)
    print("PramaanX — Person 3")
    print("ANALYSIS / H2 Independent Test")
    print("=" * 70)

    verification_id = "PX001"

    # Dummy H1.
    dummy_h1 = (
        "1111111111111111111111111111111111111111111111111111111111111111"
    )

    # Actual normalized tampering-result structure from
    # the existing PramaanX backend.
    analysis_result = {
        "status": "completed",
        "detected": False,
        "confidence": 0.1375,
        "note": (
            "Confidence score from ResNet18 binary classifier "
            "(genuine vs tampered). No heatmap or regional localisation "
            "is available from the current model."
        ),
        "error": None,
    }

    # --------------------------------------------------------
    # TEST 1
    # Create ANALYSIS record.
    # --------------------------------------------------------

    print("\n[TEST 1]")
    print("Creating ANALYSIS record...")

    record = create_analysis_record(
        verification_id=verification_id,
        analysis_result=analysis_result,
        previous_hash=dummy_h1,
    )

    print("\nGenerated record:")
    print(record)

    # --------------------------------------------------------
    # TEST 2
    # Verify unchanged analysis.
    # --------------------------------------------------------

    print("\n[TEST 2]")
    print("Verifying unchanged analysis...")

    verification = verify_analysis_record(
        verification_id=verification_id,
        analysis_result=analysis_result,
        previous_hash=dummy_h1,
    )

    print("\nVerification result:")
    print(verification)

    # --------------------------------------------------------
    # TEST 3
    # Controlled modification.
    # --------------------------------------------------------

    print("\n[TEST 3]")
    print("Testing controlled modification...")

    modified_analysis_result = dict(
        analysis_result
    )

    modified_analysis_result["detected"] = True
    modified_analysis_result["confidence"] = 0.9876

    modified_verification = (
        verify_analysis_record(
            verification_id=verification_id,
            analysis_result=modified_analysis_result,
            previous_hash=dummy_h1,
        )
    )

    print("\nModified verification result:")
    print(modified_verification)

    # --------------------------------------------------------
    # FINAL TEST RESULT
    # --------------------------------------------------------

    print("\n" + "=" * 70)

    if verification["status"] == "MATCH":
        print(
            "Original ANALYSIS: MATCH "
        )
    else:
        print(
            "Original ANALYSIS: MISMATCH "
        )

    if (
        modified_verification["status"]
        == "MISMATCH"
    ):
        print(
            "Modified ANALYSIS: MISMATCH "
        )
    else:
        print(
            "Modified ANALYSIS: MATCH "
        )

    print("=" * 70)