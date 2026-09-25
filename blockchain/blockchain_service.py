"""
PramaanX — Shared Blockchain Service (P1: Blockchain Core)
==========================================================

This is the single shared entry point that the INPUT (P2), ANALYSIS (P3) and
FINAL + UI (P4) layers use to talk to the local EVM blockchain. It wraps the
one Solidity contract (``PramaanXRegistry``) with a small, stable Python API.

Design rules honoured here (see ../Rules and ../PRD):
  * ONE local blockchain, ONE contract, THREE record types.
  * Blockchain stores ONLY hashes + non-sensitive metadata. Never PII,
    document bytes, face images or biometric templates.
  * The BACKEND computes every hash with a single canonical serialisation so
    all four teammates produce identical hashes. Never trust a client hash.
  * Hash chain:  H1 = INPUT ,  H2 = ANALYSIS + H1 ,  H3 = FINAL + H2.

Public surface used by teammates:
  * ``compute_hash(payload)``            -> canonical SHA-256 hex
  * ``link_hash(payload, previous_hash)``-> canonical SHA-256 hex, chained
  * ``BlockchainService``                -> save_record / get_record / verify_record
  * ``save_to_blockchain(record)``       -> drop-in replacement for the dev mock
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Mapping, Optional

try:  # optional convenience; the service works without python-dotenv installed
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent / ".env")
except Exception:  # pragma: no cover - dotenv is optional
    pass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RECORD_TYPES = ("INPUT", "ANALYSIS", "FINAL")

_HERE = Path(__file__).resolve().parent
_DEFAULT_RPC_URL = "http://127.0.0.1:8545"
_DEFAULT_ABI_PATH = _HERE / "contract_abi.json"
_DEFAULT_ADDRESS_FILE = _HERE / "deployed_address.json"


class BlockchainError(RuntimeError):
    """Raised for expected blockchain-service failures (config, connection)."""


# ---------------------------------------------------------------------------
# Canonical hashing — the SINGLE source of truth for every teammate.
# ---------------------------------------------------------------------------


def canonical_json(payload: Mapping[str, Any]) -> str:
    """Return the agreed canonical JSON string for ``payload``.

    Sorted keys and compact separators guarantee that the same logical
    content always serialises to the same bytes, on every machine.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def compute_hash(payload: Mapping[str, Any]) -> str:
    """SHA-256 hex of the canonical serialisation of ``payload``."""
    canonical = canonical_json(payload)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def link_hash(payload: Mapping[str, Any], previous_hash: Optional[str]) -> str:
    """Compute a chained hash: fold ``previous_hash`` into ``payload``.

    This is how ``H2 = ANALYSIS + H1`` and ``H3 = FINAL + H2`` are produced.
    The previous hash is injected as a top-level ``previous_hash`` field
    (empty string for the INPUT/H1 link) and the whole object is hashed with
    :func:`compute_hash`. All four layers MUST use this helper so the chain is
    reproducible.
    """
    linked = dict(payload)
    linked["previous_hash"] = previous_hash or ""
    return compute_hash(linked)


# ---------------------------------------------------------------------------
# Blockchain client
# ---------------------------------------------------------------------------


def _resolve_address(explicit: Optional[str]) -> str:
    """Resolve the deployed contract address.

    Priority: explicit arg -> CONTRACT_ADDRESS env -> deployed_address.json.
    """
    if explicit:
        return explicit
    env_addr = os.getenv("CONTRACT_ADDRESS")
    if env_addr:
        return env_addr
    if _DEFAULT_ADDRESS_FILE.exists():
        data = json.loads(_DEFAULT_ADDRESS_FILE.read_text(encoding="utf-8"))
        addr = data.get("address")
        if addr:
            return addr
    raise BlockchainError(
        "No contract address. Set CONTRACT_ADDRESS, pass contract_address=..., "
        "or run scripts/deploy.js to create deployed_address.json."
    )


class BlockchainService:
    """Thin, stable wrapper around the PramaanXRegistry contract.

    Parameters are all optional; sensible values are read from the environment
    and the files produced by ``scripts/deploy.js``.
    """

    def __init__(
        self,
        rpc_url: Optional[str] = None,
        contract_address: Optional[str] = None,
        abi_path: Optional[os.PathLike[str] | str] = None,
        private_key: Optional[str] = None,
    ) -> None:
        try:
            from web3 import Web3
        except ImportError as exc:  # pragma: no cover - import guard
            raise BlockchainError(
                "web3 is not installed. Run: pip install -r requirements.txt"
            ) from exc

        self._Web3 = Web3
        self.rpc_url = rpc_url or os.getenv("BLOCKCHAIN_RPC_URL", _DEFAULT_RPC_URL)
        self.private_key = private_key or os.getenv("BLOCKCHAIN_PRIVATE_KEY") or None

        self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
        if not self.w3.is_connected():
            raise BlockchainError(
                f"Cannot reach a local EVM at {self.rpc_url}. "
                "Start it with: npx hardhat node"
            )

        abi_file = Path(abi_path) if abi_path else _DEFAULT_ABI_PATH
        if not abi_file.exists():
            raise BlockchainError(f"ABI file not found: {abi_file}")
        abi = json.loads(abi_file.read_text(encoding="utf-8"))

        self.address = Web3.to_checksum_address(_resolve_address(contract_address))
        self.contract = self.w3.eth.contract(address=self.address, abi=abi)

        # Pick the transaction sender. With a Hardhat/Ganache node the first
        # unlocked account can sign server-side, so no private key is needed
        # for local development. A private key (from .env) is used when set.
        if self.private_key:
            self.account = self.w3.eth.account.from_key(self.private_key).address
        else:
            accounts = self.w3.eth.accounts
            if not accounts:
                raise BlockchainError(
                    "No unlocked accounts on the node and no BLOCKCHAIN_PRIVATE_KEY set."
                )
            self.account = accounts[0]

    # -- read-only ---------------------------------------------------------

    def is_connected(self) -> bool:
        return bool(self.w3.is_connected())

    def get_record(self, verification_id: str, record_type: str) -> dict[str, Any]:
        """Return the anchored record as a dict (``exists=False`` if absent)."""
        record_hash, previous_hash, timestamp, exists = self.contract.functions.getRecord(
            verification_id, record_type
        ).call()
        return {
            "verification_id": verification_id,
            "record_type": record_type,
            "record_hash": record_hash,
            "previous_hash": previous_hash,
            "timestamp": int(timestamp),
            "exists": bool(exists),
        }

    def verify_record(
        self, verification_id: str, record_type: str, record_hash: str
    ) -> bool:
        """True == MATCH (record exists and hashes are identical)."""
        return bool(
            self.contract.functions.verifyRecord(
                verification_id, record_type, record_hash
            ).call()
        )

    # -- state-changing ----------------------------------------------------

    def save_record(
        self,
        verification_id: str,
        record_type: str,
        record_hash: str,
        previous_hash: str = "",
    ) -> dict[str, Any]:
        """Anchor a hash on-chain and wait for the receipt.

        Returns a small dict with the transaction hash, block number and the
        anchored fields. Raises :class:`BlockchainError` on invalid input.
        """
        if record_type not in RECORD_TYPES:
            raise BlockchainError(
                f"record_type must be one of {RECORD_TYPES}, got {record_type!r}"
            )
        if not verification_id or not record_hash:
            raise BlockchainError("verification_id and record_hash are required")

        fn = self.contract.functions.saveRecord(
            verification_id, record_type, record_hash, previous_hash or ""
        )

        if self.private_key:
            tx = fn.build_transaction(
                {
                    "from": self.account,
                    "nonce": self.w3.eth.get_transaction_count(self.account),
                    "gas": 500_000,
                    "gasPrice": self.w3.eth.gas_price,
                }
            )
            signed = self.w3.eth.account.sign_transaction(tx, self.private_key)
            raw = getattr(signed, "raw_transaction", None)
            if raw is None:  # older eth-account naming
                raw = signed.rawTransaction
            tx_hash = self.w3.eth.send_raw_transaction(raw)
        else:
            tx_hash = fn.transact({"from": self.account})

        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        return {
            "verification_id": verification_id,
            "record_type": record_type,
            "record_hash": record_hash,
            "previous_hash": previous_hash or "",
            "tx_hash": tx_hash.hex(),
            "block_number": int(receipt["blockNumber"]),
            "status": int(receipt["status"]),
        }

    def save_to_blockchain(self, record: Mapping[str, Any]) -> dict[str, Any]:
        """Drop-in replacement for the development mock.

        Accepts the fixed shared record shape::

            {"verification_id": "PX001", "record_type": "INPUT",
             "hash": "H1", "previous_hash": ""}

        so a teammate can swap their mock ``save_to_blockchain(record)`` for
        this real one without changing call sites.
        """
        return self.save_record(
            verification_id=record["verification_id"],
            record_type=record["record_type"],
            record_hash=record.get("hash") or record["record_hash"],
            previous_hash=record.get("previous_hash", ""),
        )


# ---------------------------------------------------------------------------
# Module-level convenience (lazy singleton) for the "swap the mock" workflow
# ---------------------------------------------------------------------------

_default_service: Optional[BlockchainService] = None


def get_service() -> BlockchainService:
    """Return a process-wide :class:`BlockchainService`, creating it once."""
    global _default_service
    if _default_service is None:
        _default_service = BlockchainService()
    return _default_service


def save_to_blockchain(record: Mapping[str, Any]) -> dict[str, Any]:
    """Module-level mock replacement — see :meth:`BlockchainService.save_to_blockchain`."""
    return get_service().save_to_blockchain(record)

