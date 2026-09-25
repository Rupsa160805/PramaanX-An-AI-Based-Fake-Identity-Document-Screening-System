"""P4 — Deterministic FINAL hashing (H3).

Uses exactly the same canonical JSON rule as the shared blockchain service
(``blockchain/blockchain_service.py``):

    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    hash     = hashlib.sha256(canonical.encode("utf-8")).hexdigest()

Hash-chain rule:
    H1 = SHA-256(INPUT payload)
    H2 = SHA-256(ANALYSIS payload  + H1)
    H3 = SHA-256(FINAL payload     + H2)

P4 does NOT calculate H1 or H2.  P4 receives H2 and computes H3.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping


# ---------------------------------------------------------------------------
# Canonical serialisation — must match blockchain/blockchain_service.py
# ---------------------------------------------------------------------------

def canonical_json(payload: Mapping[str, Any]) -> str:
    """Deterministic JSON string: sorted keys, compact separators."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def compute_hash(payload: Mapping[str, Any]) -> str:
    """SHA-256 hex digest of the canonical JSON for *payload*."""
    return hashlib.sha256(
        canonical_json(payload).encode("utf-8")
    ).hexdigest()


# ---------------------------------------------------------------------------
# H3 calculation
# ---------------------------------------------------------------------------

def calculate_h3(final_payload: Mapping[str, Any], previous_hash: str) -> str:
    """Compute H3 = SHA-256(FINAL_payload + H2).

    ``previous_hash`` is H2 (from the analysis layer).  It is folded into the
    payload as a top-level ``"previous_hash"`` key before hashing — the same
    convention used by ``link_hash`` in the shared blockchain service.
    """
    linked: dict[str, Any] = dict(final_payload)
    linked["previous_hash"] = previous_hash or ""
    return compute_hash(linked)
