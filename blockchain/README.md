# PramaanX — Blockchain Core (P1)

The **integrity/provenance layer** for PramaanX: one local EVM blockchain, one
Solidity contract, three checkpoints (`INPUT` → `ANALYSIS` → `FINAL`). This
module is self-contained and was built and tested **independently** of the
INPUT (P2), ANALYSIS (P3) and FINAL/UI (P4) layers. Those layers integrate with
it later through the small, stable API documented below.

> Blockchain here is **only** tamper-evidence. It does **not** do OCR, MRZ, AI
> tampering detection, face verification, database validation, risk scoring,
> authentication or encryption — those remain the existing PramaanX pipeline.
> A hash MATCH proves the record is unchanged since anchoring; it does **not**
> prove the AI decision was correct, and a MISMATCH does **not** say who
> changed the data.

## What's in here

| File | Purpose |
|------|---------|
| `contracts/contract.sol` | The single `PramaanXRegistry` Solidity contract |
| `scripts/deploy.js` | Deploys to the local chain, writes ABI + address |
| `hardhat.config.js` | Local-only Hardhat config (no public networks) |
| `contract_abi.json` | Contract ABI (committed deliverable for web3.py) |
| `deployed_address.json` | Address written at deploy time (git-ignored) |
| `blockchain_service.py` | **Shared** Python web3.py client + canonical hashing |
| `test_blockchain.py` | Independent demo + pytest (save → retrieve → verify) |
| `requirements.txt` | Python deps (`web3`, `python-dotenv`) |
| `.env.example` | Config template (copy to `.env`, never commit `.env`) |

## Architecture

```text
P2/P3/P4 backend code
        │  (calls the shared service)
        ▼
blockchain_service.py  ──web3.py──►  Local EVM (Hardhat) @ 127.0.0.1:8545
        │                                    │
   compute_hash / link_hash            PramaanXRegistry
   (canonical SHA-256)                 saveRecord / getRecord / verifyRecord
```

<!-- APPEND_MARKER -->

## Prerequisites

- Node.js 18/20/22 LTS (works on newer versions with a Hardhat warning) + npm
- Python 3.10+

## Quick start

```bash
# 1. Install the toolchain (Node) and the Python client
cd blockchain
npm install
pip install -r requirements.txt        # into your project venv

# 2. Compile the contract
npx hardhat compile

# 3. Start the local blockchain (leave this running in Terminal A)
npx hardhat node

# 4. Deploy the contract (Terminal B) — writes contract_abi.json + deployed_address.json
npx hardhat run scripts/deploy.js --network localhost

# 5. Run the independent demo / tests (Terminal B)
python test_blockchain.py       # pretty integrity dashboard
pytest test_blockchain.py       # 3 tests (hashing always run; chain test needs the node)
```

With a fresh node the contract deploys to the deterministic address
`0x5FbDB2315678afecb367f032d93F642f64180aa3` (first tx from account #0).

## Configuration

Copy `.env.example` to `.env` and adjust if needed:

| Variable | Default | Meaning |
|----------|---------|---------|
| `BLOCKCHAIN_RPC_URL` | `http://127.0.0.1:8545` | Local EVM JSON-RPC endpoint |
| `CONTRACT_ADDRESS` | (from `deployed_address.json`) | Deployed contract address |
| `BLOCKCHAIN_PRIVATE_KEY` | (empty) | Optional signer key; local dev uses the node's first unlocked account |

`.env` is git-ignored. Never commit a private key.

## Canonical hashing (the shared rule)

**Every teammate must hash through this module** so hashes are identical
everywhere. Do not re-implement SHA-256 by hand.

```python
from blockchain_service import compute_hash, link_hash

# canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
h1 = link_hash(input_payload, None)        # H1 = INPUT
h2 = link_hash(analysis_payload, h1)       # H2 = ANALYSIS + H1
h3 = link_hash(final_payload, h2)          # H3 = FINAL + H2
```

`link_hash` injects `previous_hash` into the payload (empty string for INPUT)
and hashes the canonical JSON. The backend computes hashes — never the client.

## Service API

```python
from blockchain_service import BlockchainService

svc = BlockchainService()   # reads .env + deployed_address.json

svc.save_record(verification_id, record_type, record_hash, previous_hash="")
#   record_type ∈ {"INPUT","ANALYSIS","FINAL"}; returns {tx_hash, block_number, ...}

svc.get_record(verification_id, record_type)
#   -> {record_hash, previous_hash, timestamp, exists}

svc.verify_record(verification_id, record_type, record_hash)
#   -> True (MATCH) / False (MISMATCH or never anchored)
```

`saveRecord` is **first-write-wins**: an anchored `(verificationId, recordType)`
cannot be overwritten (re-anchoring reverts), which is what makes it
tamper-evident.

## Fixed record interface

The shared shape passed between layers (do not change without team agreement):

```json
{ "verification_id": "PX001", "record_type": "INPUT",    "hash": "H1", "previous_hash": "" }
{ "verification_id": "PX001", "record_type": "ANALYSIS", "hash": "H2", "previous_hash": "H1" }
{ "verification_id": "PX001", "record_type": "FINAL",    "hash": "H3", "previous_hash": "H2" }
```

## For P2 / P3 / P4 — swapping the mock

During independent development you used:

```python
def save_to_blockchain(record):
    print("MOCK BLOCKCHAIN:", record)
    return True
```

At integration, replace that import with the real one — same signature:

```python
from blockchain_service import save_to_blockchain
save_to_blockchain({"verification_id": "PX001", "record_type": "INPUT",
                    "hash": h1, "previous_hash": ""})
```

## Expected test output

```text
BLOCKCHAIN INTEGRITY (normal)
  INPUT     ✓ MATCH
  ANALYSIS  ✓ MATCH
  FINAL     ✓ MATCH
  Chain Status: INTACT

Controlled modification of FINAL after anchoring:
  INPUT     ✓ MATCH
  ANALYSIS  ✓ MATCH
  FINAL     ⚠ MISMATCH
  Chain Status: WARNING (tamper detected)
```

## Privacy & security

- On-chain data is **hashes + minimal non-sensitive metadata only**. No
  passport/face images, biometric templates, passport numbers, DOB or address.
- Hashes are computed on the backend; a client-supplied hash is never trusted.
- Secrets live in `.env` (git-ignored). This is a local dev chain — no mainnet,
  no paid RPC, no tokens/NFTs/wallets.

## Definition of Done (P1 slice)

- [x] Local blockchain runs (`npx hardhat node`)
- [x] Contract deploys (`PramaanXRegistry`, ABI + address written)
- [x] `saveRecord` / `getRecord` / `verifyRecord` implemented (minimal)
- [x] H1 → H2 → H3 chain anchored, retrieved and verified with dummy records
- [x] Controlled modification produces a MISMATCH
- [x] No sensitive PII stored on-chain
- [x] `.env` git-ignored

## Handover to integrators

- Contract address (fresh local node): `0x5FbDB2315678afecb367f032d93F642f64180aa3`
- ABI: `contract_abi.json`
- Shared client + hashing: `blockchain_service.py`
- Entry points teammates call: `compute_hash`, `link_hash`, `BlockchainService`,
  `save_to_blockchain`

