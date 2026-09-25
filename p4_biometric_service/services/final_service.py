"""P4 — FINAL record service.

Responsible for:
  • building a deterministic canonical FINAL payload from the screening result
  • computing H3 (chained with H2)
  • storing the FINAL record on the blockchain
  • verifying a FINAL record against the blockchain

The blockchain back-end is abstracted behind a simple adapter interface so
development can proceed with a mock before P1's real service is available.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from .final_hash import calculate_h3, canonical_json, compute_hash

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mock blockchain adapter (used when BLOCKCHAIN_MODE != "real")
# ---------------------------------------------------------------------------

class MockBlockchainService:
    """In-memory stand-in for testing and solo development.

    Supports the same three operations as BlockchainService:
        save_record, get_record, verify_record
    """

    def __init__(self) -> None:
        self._store: dict[tuple[str, str], dict[str, Any]] = {}

    def save_record(
        self,
        verification_id: str,
        record_type: str,
        record_hash: str,
        previous_hash: str = "",
    ) -> dict[str, Any]:
        key = (verification_id, record_type)
        if key in self._store:
            log.warning("MOCK BLOCKCHAIN: record already anchored for %s", key)
            return {
                "verification_id": verification_id,
                "record_type": record_type,
                "record_hash": self._store[key]["record_hash"],
                "previous_hash": self._store[key]["previous_hash"],
                "status": 0,
                "tx_hash": "0x0000000000000000000000000000000000000000",
                "block_number": 0,
            }
        entry = {
            "record_hash": record_hash,
            "previous_hash": previous_hash,
            "timestamp": int(datetime.now(timezone.utc).timestamp()),
            "exists": True,
        }
        self._store[key] = entry
        log.info("MOCK BLOCKCHAIN: saved %s/%s -> %s", verification_id, record_type, record_hash)
        return {
            "verification_id": verification_id,
            "record_type": record_type,
            "record_hash": record_hash,
            "previous_hash": previous_hash,
            "status": 1,
            "tx_hash": "0xMOCK",
            "block_number": 1,
        }

    def get_record(self, verification_id: str, record_type: str) -> dict[str, Any]:
        key = (verification_id, record_type)
        entry = self._store.get(key)
        if entry is None:
            return {
                "verification_id": verification_id,
                "record_type": record_type,
                "record_hash": "",
                "previous_hash": "",
                "timestamp": 0,
                "exists": False,
            }
        return {
            "verification_id": verification_id,
            "record_type": record_type,
            **entry,
        }

    def verify_record(
        self, verification_id: str, record_type: str, record_hash: str
    ) -> bool:
        stored = self.get_record(verification_id, record_type)
        return stored["exists"] and stored["record_hash"] == record_hash


# ---------------------------------------------------------------------------
# Service singleton helper
# ---------------------------------------------------------------------------

_blockchain: Optional[Any] = None


def _get_blockchain():
    """Return a blockchain adapter (mock or real) based on BLOCKCHAIN_MODE."""
    global _blockchain
    if _blockchain is not None:
        return _blockchain

    mode = os.getenv("BLOCKCHAIN_MODE", "mock").lower()
    if mode == "real":
        try:
            import sys
            from pathlib import Path
            # Add blockchain/ dir to path so we can import the shared service.
            blockchain_dir = str(Path(__file__).resolve().parents[2] / "blockchain")
            if blockchain_dir not in sys.path:
                sys.path.insert(0, blockchain_dir)
            from blockchain_service import BlockchainService  # type: ignore[import]
            _blockchain = BlockchainService()
            log.info("P4: using REAL blockchain service")
        except Exception as exc:
            log.warning("P4: failed to connect real blockchain (%s), falling back to mock", exc)
            _blockchain = MockBlockchainService()
    else:
        _blockchain = MockBlockchainService()
        log.info("P4: using MOCK blockchain service")
    return _blockchain


def reset_blockchain(service=None):
    """Replace the blockchain singleton (useful for tests)."""
    global _blockchain
    _blockchain = service


# ---------------------------------------------------------------------------
# Canonical FINAL payload builder
# ---------------------------------------------------------------------------

def build_final_payload(screening_result: Mapping[str, Any]) -> dict[str, Any]:
    """Extract only the deterministic, meaningful fields from a screening result.

    Excludes transient/unstable fields: request_id, processing_time_ms,
    timestamps, temporary file paths, persistence metadata.  This ensures
    the hash is reproducible when the same logical result is recalculated.
    """
    risk = screening_result.get("risk", {})
    recommendation = screening_result.get("recommendation", {})
    database_checks = screening_result.get("database_checks", {})
    tampering = screening_result.get("tampering", {})
    face = screening_result.get("face_verification", {})
    ocr = screening_result.get("ocr", {})
    mrz = screening_result.get("mrz", {})
    consistency = screening_result.get("consistency", {})
    validation = screening_result.get("validation", {})

    return {
        "status": screening_result.get("status"),
        "risk": {
            "score": risk.get("score"),
            "level": risk.get("level"),
        },
        "recommendation": {
            "action": recommendation.get("action"),
        },
        "database_checks": {
            "found": database_checks.get("found"),
            "expired": database_checks.get("expired"),
        },
        "tampering": {
            "status": tampering.get("status"),
            "detected": tampering.get("detected"),
            "confidence": tampering.get("confidence"),
        },
        "face_verification": {
            "status": face.get("status"),
            "is_match": face.get("is_match"),
            "similarity": face.get("similarity"),
            "liveness_passed": face.get("liveness_passed"),
        },
        "ocr": {
            "status": ocr.get("status"),
        },
        "mrz": {
            "status": mrz.get("status"),
        },
        "consistency": {
            "overall_match": consistency.get("overall_match"),
        },
        "validation": {
            "document_valid": validation.get("document_valid") if isinstance(validation, dict) else None,
        },
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def create_final_record(
    verification_id: str,
    final_result: Mapping[str, Any],
    previous_hash: str,
) -> dict[str, Any]:
    """Build canonical FINAL payload, compute H3, store on blockchain.

    Returns:
        dict with verification_id, record_type, hash, previous_hash,
        blockchain_status, and the canonical final_payload.
    """
    final_payload = build_final_payload(final_result)
    h3 = calculate_h3(final_payload, previous_hash)

    bc = _get_blockchain()
    try:
        bc_result = bc.save_record(
            verification_id=verification_id,
            record_type="FINAL",
            record_hash=h3,
            previous_hash=previous_hash,
        )
        blockchain_status = "stored" if bc_result.get("status") == 1 else "already_anchored"
    except Exception as exc:
        log.error("P4: blockchain save failed: %s", exc)
        blockchain_status = "error"

    return {
        "verification_id": verification_id,
        "record_type": "FINAL",
        "hash": h3,
        "previous_hash": previous_hash,
        "blockchain_status": blockchain_status,
        "final_payload": final_payload,
    }


def verify_final_record(
    verification_id: str,
    final_result: Mapping[str, Any],
    previous_hash: str,
) -> dict[str, Any]:
    """Recalculate H3 and compare with the stored blockchain record.

    Never trusts a client-supplied hash — always recalculates on the backend.

    Returns:
        dict with match status ("MATCH", "MISMATCH", or "NOT_FOUND"),
        current and stored hashes, and the canonical final_payload.
    """
    final_payload = build_final_payload(final_result)
    current_h3 = calculate_h3(final_payload, previous_hash)

    bc = _get_blockchain()
    try:
        stored = bc.get_record(verification_id, "FINAL")
    except Exception as exc:
        log.error("P4: blockchain retrieval failed: %s", exc)
        return {
            "verification_id": verification_id,
            "record_type": "FINAL",
            "status": "UNAVAILABLE",
            "current_hash": current_h3,
            "stored_hash": None,
            "detail": str(exc),
        }

    if not stored.get("exists"):
        return {
            "verification_id": verification_id,
            "record_type": "FINAL",
            "status": "NOT_FOUND",
            "current_hash": current_h3,
            "stored_hash": None,
        }

    stored_hash = stored.get("record_hash", "")
    match = current_h3 == stored_hash
    return {
        "verification_id": verification_id,
        "record_type": "FINAL",
        "status": "MATCH" if match else "MISMATCH",
        "current_hash": current_h3,
        "stored_hash": stored_hash,
    }


def verify_all_records(
    verification_id: str,
    final_result: Mapping[str, Any] | None = None,
    previous_hash: str = "",
) -> dict[str, Any]:
    """Verify INPUT, ANALYSIS, and FINAL integrity in one call.

    For INPUT and ANALYSIS, we only check whether a record exists on-chain
    (the originating layers own re-computation).  For FINAL we recalculate H3.
    """
    bc = _get_blockchain()
    results: dict[str, Any] = {}

    for record_type in ("INPUT", "ANALYSIS", "FINAL"):
        try:
            stored = bc.get_record(verification_id, record_type)
            if not stored.get("exists"):
                results[record_type] = {"status": "NOT_FOUND"}
            elif record_type == "FINAL" and final_result is not None:
                final_payload = build_final_payload(final_result)
                current_h3 = calculate_h3(final_payload, previous_hash)
                match = current_h3 == stored.get("record_hash", "")
                results[record_type] = {
                    "status": "MATCH" if match else "MISMATCH",
                    "current_hash": current_h3,
                    "stored_hash": stored.get("record_hash", ""),
                }
            else:
                # INPUT and ANALYSIS: P4 only reports existence.
                results[record_type] = {
                    "status": "VERIFIED",
                    "stored_hash": stored.get("record_hash", ""),
                }
        except Exception as exc:
            log.error("P4: blockchain check failed for %s: %s", record_type, exc)
            results[record_type] = {"status": "UNAVAILABLE", "detail": str(exc)}

    # Chain status
    statuses = [v["status"] for v in results.values()]
    if "UNAVAILABLE" in statuses:
        chain = "UNAVAILABLE"
    elif "MISMATCH" in statuses:
        chain = "WARNING"
    elif all(s in ("MATCH", "VERIFIED") for s in statuses):
        chain = "INTACT"
    else:
        chain = "INCOMPLETE"

    return {
        "verification_id": verification_id,
        "records": results,
        "chain_status": chain,
    }
