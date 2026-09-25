"""
PramaanX P1 — independent standalone test / demo for the blockchain core.

Covers the required P1 acceptance flow:
    dummy record -> blockchain -> retrieve -> verify

It anchors dummy INPUT / ANALYSIS / FINAL records (the full H1 -> H2 -> H3
chain), reads them back, verifies each one (expect MATCH), and then performs
a controlled modification to prove a tamper is detected (expect MISMATCH).

Run as a demo (needs a running node + deployed contract):
    # Terminal A:  npx hardhat node
    # Terminal B:  npx hardhat run scripts/deploy.js --network localhost
    python test_blockchain.py

Run as tests:
    pytest test_blockchain.py
The full-chain test auto-skips if no local EVM is reachable; the canonical
hashing tests always run (no node required).
"""

from __future__ import annotations

import sys
import time

# Windows terminals often default to cp1252, which cannot encode the ✓/⚠
# integrity glyphs. Force UTF-8 output where the runtime supports it.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover - best effort only
    pass

from blockchain_service import (
    BlockchainService,
    BlockchainError,
    compute_hash,
    link_hash,
)

CHECK = "✓"   # ✓
WARN = "⚠"    # ⚠


# ---------------------------------------------------------------------------
# Dummy payloads (synthetic — NOT real identity data)
# ---------------------------------------------------------------------------


def _dummy_payloads(verification_id: str):
    input_payload = {
        "verification_id": verification_id,
        "record_type": "INPUT",
        "document_sha256": "b" * 64,      # hash of the uploaded bytes (P2 supplies)
        "filename": "synthetic_sample.png",
    }
    analysis_payload = {
        "verification_id": verification_id,
        "record_type": "ANALYSIS",
        "tampering_score": 0.12,
        "verdict": "LIKELY_GENUINE",       # comes from existing PramaanX AI (P3)
    }
    final_payload = {
        "verification_id": verification_id,
        "record_type": "FINAL",
        "risk_level": "LOW",
        "decision": "CLEARED_FOR_OFFICER_REVIEW",  # existing final result (P4)
    }
    return input_payload, analysis_payload, final_payload


# ---------------------------------------------------------------------------
# Canonical hashing tests (no blockchain needed)
# ---------------------------------------------------------------------------


def test_canonical_hash_is_deterministic_and_order_independent():
    a = {"b": 2, "a": 1}
    b = {"a": 1, "b": 2}
    assert compute_hash(a) == compute_hash(b)
    assert len(compute_hash(a)) == 64


def test_link_hash_folds_previous_hash():
    payload = {"verification_id": "PX001", "record_type": "ANALYSIS", "score": 0.1}
    h_a = link_hash(payload, "H1")
    h_b = link_hash(payload, "DIFFERENT")
    assert h_a != h_b  # changing the previous hash changes the chained hash


# ---------------------------------------------------------------------------
# Full-chain integration test (needs a running node + deployed contract)
# ---------------------------------------------------------------------------


def _make_service():
    try:
        return BlockchainService()
    except BlockchainError as exc:
        return exc


def test_full_chain_save_retrieve_verify():
    import pytest

    service = _make_service()
    if isinstance(service, BlockchainError):
        pytest.skip(f"local EVM not available: {service}")

    verification_id = f"PXTEST{int(time.time())}"
    _run_chain(service, verification_id)


# ---------------------------------------------------------------------------
# Chain runner shared by the test and the __main__ demo
# ---------------------------------------------------------------------------


def _run_chain(service: BlockchainService, verification_id: str) -> None:
    input_p, analysis_p, final_p = _dummy_payloads(verification_id)

    h1 = link_hash(input_p, None)          # H1 = INPUT
    h2 = link_hash(analysis_p, h1)         # H2 = ANALYSIS + H1
    h3 = link_hash(final_p, h2)            # H3 = FINAL + H2

    service.save_record(verification_id, "INPUT", h1, "")
    service.save_record(verification_id, "ANALYSIS", h2, h1)
    service.save_record(verification_id, "FINAL", h3, h2)

    # Read back and verify each checkpoint.
    for record_type, expected in (("INPUT", h1), ("ANALYSIS", h2), ("FINAL", h3)):
        stored = service.get_record(verification_id, record_type)
        assert stored["exists"], f"{record_type} not anchored"
        assert stored["record_hash"] == expected
        assert service.verify_record(verification_id, record_type, expected) is True

    # Chain lineage: each stored previous_hash points at the prior link.
    assert service.get_record(verification_id, "ANALYSIS")["previous_hash"] == h1
    assert service.get_record(verification_id, "FINAL")["previous_hash"] == h2

    # Controlled modification: recompute FINAL from tampered data -> MISMATCH.
    tampered_final = dict(final_p)
    tampered_final["decision"] = "TAMPERED_AFTER_ANCHORING"
    tampered_h3 = link_hash(tampered_final, h2)
    assert service.verify_record(verification_id, "FINAL", tampered_h3) is False


def main() -> int:
    service = _make_service()
    if isinstance(service, BlockchainError):
        print("Cannot run demo:", service)
        print("Start the node (npx hardhat node) and deploy "
              "(npx hardhat run scripts/deploy.js --network localhost) first.")
        return 1

    verification_id = f"PXDEMO{int(time.time())}"
    print(f"Connected to {service.rpc_url}")
    print(f"Contract:    {service.address}")
    print(f"Sender:      {service.account}")
    print(f"Verification id: {verification_id}\n")

    input_p, analysis_p, final_p = _dummy_payloads(verification_id)
    h1 = link_hash(input_p, None)
    h2 = link_hash(analysis_p, h1)
    h3 = link_hash(final_p, h2)

    print("Anchoring H1 -> H2 -> H3 ...")
    print("  INPUT   ", service.save_record(verification_id, "INPUT", h1, "")["tx_hash"])
    print("  ANALYSIS", service.save_record(verification_id, "ANALYSIS", h2, h1)["tx_hash"])
    print("  FINAL   ", service.save_record(verification_id, "FINAL", h3, h2)["tx_hash"])

    print("\nBLOCKCHAIN INTEGRITY (normal)\n")
    all_ok = True
    for record_type, expected in (("INPUT", h1), ("ANALYSIS", h2), ("FINAL", h3)):
        ok = service.verify_record(verification_id, record_type, expected)
        all_ok = all_ok and ok
        print(f"  {record_type:<9} {CHECK} MATCH" if ok else f"  {record_type:<9} {WARN} MISMATCH")
    print(f"\n  Chain Status: {'INTACT' if all_ok else 'WARNING'}")

    print("\nControlled modification of FINAL after anchoring:\n")
    tampered_final = dict(final_p)
    tampered_final["decision"] = "TAMPERED_AFTER_ANCHORING"
    tampered_h3 = link_hash(tampered_final, h2)
    for record_type, expected in (("INPUT", h1), ("ANALYSIS", h2), ("FINAL", tampered_h3)):
        ok = service.verify_record(verification_id, record_type, expected)
        print(f"  {record_type:<9} {CHECK} MATCH" if ok else f"  {record_type:<9} {WARN} MISMATCH")
    print("\n  Chain Status: WARNING (tamper detected)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
