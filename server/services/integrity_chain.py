"""P4 — Blockchain integrity chain orchestration (H1 -> H2 -> H3).

This module wires the three checkpoints into the live document-screening flow
and centralises the canonical hash rule so INPUT, ANALYSIS and FINAL all use
the same convention as the shared P1 service (``blockchain/blockchain_service.py``)
and ``final_hash.calculate_h3``:

    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    H1 = SHA-256(INPUT    payload + "")   # previous_hash="" folded in
    H2 = SHA-256(ANALYSIS payload + H1)
    H3 = SHA-256(FINAL    payload + H2)

Payload shapes intentionally match P2's ``create_input_payload`` and P3's
``generate_h2`` so a record anchored here verifies identically across layers.
All hashes are computed server-side; a client never supplies a hash.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any, Mapping

from .final_hash import calculate_h3, compute_hash
from .final_service import _get_blockchain, build_final_payload

log = logging.getLogger(__name__)

_READ_CHUNK = 1 << 16


def link_hash(payload: Mapping[str, Any], previous_hash: str | None) -> str:
    """Fold ``previous_hash`` into ``payload`` and hash canonically (P1 rule)."""
    linked = dict(payload)
    linked["previous_hash"] = previous_hash or ""
    return compute_hash(linked)


def sha256_file(path: str | Path) -> str:
    """SHA-256 of the raw file bytes (the INPUT ``file_hash``)."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(_READ_CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()

def build_input_payload(verification_id: str, file_hash: str) -> dict[str, Any]:
    """INPUT payload — shape matches P2's ``create_input_payload``."""
    return {
        "verification_id": verification_id,
        "record_type": "INPUT",
        "file_hash": file_hash,
    }


def build_analysis_payload(
    verification_id: str, analysis_result: Mapping[str, Any] | None
) -> dict[str, Any]:
    """ANALYSIS payload — the deterministic subset of the tampering result.

    Only stable fields are folded in so transient metadata (timings, model
    versions) can never change H2. Shape matches P3's ``generate_h2`` input.
    """
    source = analysis_result or {}
    return {
        "verification_id": verification_id,
        "record_type": "ANALYSIS",
        "analysis_result": {
            "status": source.get("status"),
            "detected": source.get("detected"),
            "confidence": source.get("confidence"),
        },
    }


def _anchor(bc, verification_id: str, record_type: str, record_hash: str,
            previous_hash: str) -> str:
    """Anchor one record; first-write-wins. Never raises into the caller."""
    try:
        outcome = bc.save_record(
            verification_id=verification_id,
            record_type=record_type,
            record_hash=record_hash,
            previous_hash=previous_hash,
        )
    except Exception as exc:  # pragma: no cover - defensive, chain is best-effort
        log.error("anchor failed %s/%s: %s", verification_id, record_type, exc)
        return "error"
    status = outcome.get("status") if isinstance(outcome, Mapping) else outcome
    if status in (1, "stored", True):
        return "stored"
    if status in (0, "already_anchored", "exists"):
        return "already_anchored"
    return str(status)


def anchor_chain(
    verification_id: str,
    *,
    image_path: str | Path,
    analysis_result: Mapping[str, Any] | None,
    final_result: Mapping[str, Any],
) -> dict[str, Any]:
    """Compute and anchor H1/H2/H3 for one screening (best-effort).

    Returns the ``integrity`` block that is persisted alongside the screening
    result and echoed to the client. All three hashes are computed here on the
    server; nothing is taken from the request.
    """
    bc = _get_blockchain()

    file_hash = sha256_file(image_path)
    h1 = link_hash(build_input_payload(verification_id, file_hash), None)
    input_status = _anchor(bc, verification_id, "INPUT", h1, "")

    h2 = link_hash(build_analysis_payload(verification_id, analysis_result), h1)
    analysis_status = _anchor(bc, verification_id, "ANALYSIS", h2, h1)

    h3 = calculate_h3(build_final_payload(final_result), h2)
    final_status = _anchor(bc, verification_id, "FINAL", h3, h2)

    return {
        "verification_id": verification_id,
        "file_hash": file_hash,
        "h1": h1,
        "h2": h2,
        "h3": h3,
        "records": {
            "INPUT": input_status,
            "ANALYSIS": analysis_status,
            "FINAL": final_status,
        },
    }


def _compare(bc, verification_id: str, record_type: str,
             current_hash: str | None) -> dict[str, Any]:
    """Recompute-vs-stored comparison for one record."""
    try:
        stored = bc.get_record(verification_id, record_type)
    except Exception as exc:  # pragma: no cover - defensive
        return {"status": "UNAVAILABLE", "detail": str(exc)}
    if not (stored and stored.get("exists")):
        return {"status": "NOT_FOUND", "current_hash": current_hash, "stored_hash": None}
    stored_hash = stored.get("record_hash") or stored.get("hash") or ""
    if current_hash is None:
        return {"status": "NOT_FOUND", "current_hash": None, "stored_hash": stored_hash}
    matched = current_hash == stored_hash
    return {
        "status": "MATCH" if matched else "MISMATCH",
        "current_hash": current_hash,
        "stored_hash": stored_hash,
    }


def verify_chain(
    verification_id: str,
    *,
    file_hash: str | None,
    analysis_result: Mapping[str, Any] | None,
    final_result: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Re-derive H1/H2/H3 from persisted state and compare against the chain.

    This is the server-driven verification: hashes are recomputed from the
    stored ``file_hash`` and screening ``result``, never supplied by a client.
    """
    bc = _get_blockchain()
    records: dict[str, Any] = {}

    h1 = h2 = None
    if file_hash:
        h1 = link_hash(build_input_payload(verification_id, file_hash), None)
    records["INPUT"] = _compare(bc, verification_id, "INPUT", h1)

    if h1 is not None:
        h2 = link_hash(build_analysis_payload(verification_id, analysis_result), h1)
    records["ANALYSIS"] = _compare(bc, verification_id, "ANALYSIS", h2)

    h3 = None
    if h2 is not None and final_result is not None:
        h3 = calculate_h3(build_final_payload(final_result), h2)
    records["FINAL"] = _compare(bc, verification_id, "FINAL", h3)

    statuses = [r["status"] for r in records.values()]
    if "UNAVAILABLE" in statuses:
        chain_status = "UNAVAILABLE"
    elif "MISMATCH" in statuses:
        chain_status = "WARNING"
    elif all(s == "MATCH" for s in statuses):
        chain_status = "INTACT"
    else:
        chain_status = "INCOMPLETE"

    return {
        "verification_id": verification_id,
        "records": records,
        "chain_status": chain_status,
    }
