# PramaanX — AI-Powered Border Document Intelligence

> **Scan. Verify. Explain.**

PramaanX is a multimodal, AI-assisted document screening and identity verification platform designed for authorized border/immigration officers.

> **This is a decision-support system.** The final decision on every traveller remains with the authorised human officer. PramaanX does not automatically accept or reject anyone.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Directory Structure](#directory-structure)
4. [Backend Contribution](#backend-contribution)
5. [Setup](#setup)
6. [Running the Server](#running-the-server)
7. [API Endpoints](#api-endpoints)
8. [Swagger Documentation](#swagger-documentation)
9. [Example Request & Response](#example-request--response)
10. [Running Tests](#running-tests)
11. [Environment Variables](#environment-variables)
12. [AI Integration Explanation](#ai-integration-explanation)
13. [Known Limitations](#known-limitations)

---

## Project Overview

PramaanX cross-references three independent evidence sources — the **Identity Evidence Triangle**:

| Source | Description |
|---|---|
| **Visual Evidence** | OCR of printed document fields (name, DOB, passport number, etc.) |
| **Machine Evidence** | MRZ / barcode / QR data parsed from the document image |
| **Live Evidence** | Live traveller face + liveness *(planned — not yet available)* |

The system flags cases where independent evidence sources **disagree** and produces an explainable risk score, leaving the final decision to the officer.

---

## Architecture

```
Frontend (React — separate team)
         ↓
    FastAPI Backend  ← my contribution
         ↓
 Verification Service
         ↓
    AI Pipeline ← orchestration (my contribution) calling:
       ├── ai/preprocessing.py   (AI team)
       ├── ai/ocr.py             (AI team)
       ├── ai/mrz.py             (AI team)
       └── ai/tampering.py       (AI team)
         ↓
 Result Normalisation, Consistency Checks, Risk Scoring
         ↓
    Structured JSON Response
```

---

## Directory Structure

```
backend/
│
├── ai/                          # AI modules (AI team contribution)
│   ├── ml/
│   │   └── train.py             # ResNet18 training script
│   ├── __init__.py
│   ├── mrz.py                   # TD3 MRZ parsing + ICAO check-digit validation
│   ├── ocr.py                   # EasyOCR field extraction
│   ├── pipeline.py              # AI orchestrator (backend contribution)
│   ├── preprocessing.py         # OpenCV image preprocessing
│   ├── tampering.py             # ResNet18 tamper-detection classifier
│   └── validation.py            # Cross-field validation utilities
│
├── app/                         # FastAPI application (backend contribution)
│   ├── main.py                  # Application entry point
│   │
│   ├── api/v1/
│   │   ├── router.py
│   │   └── endpoints/
│   │       ├── health.py        # GET /api/v1/health
│   │       └── verification.py  # POST /api/v1/verify
│   │
│   ├── schemas/
│   │   ├── common.py            # Shared enums
│   │   ├── errors.py            # Error response schema
│   │   └── verification.py      # Full verification response schema
│   │
│   ├── services/
│   │   ├── verification_service.py   # Main orchestration
│   │   ├── validation_service.py     # Consistency / cross-source checks
│   │   ├── risk_service.py           # Explainable risk scoring
│   │   ├── database_service.py       # Mock database adapter
│   │   └── audit_service.py          # Audit record builder
│   │
│   ├── core/
│   │   ├── config.py            # Pydantic Settings (env-driven)
│   │   └── logging.py           # Logging setup
│   │
│   └── utils/
│       └── file_utils.py        # File upload validation + temp file management
│
├── tests/
│   └── test_backend.py          # FastAPI / service layer tests
│
├── test_ai.py                   # AI module unit tests
├── requirements.txt
├── pyproject.toml               # pytest configuration
├── .env.example                 # Environment variable template
└── README.md
```

---

## Backend Contribution

The backend / API / integration layer is my contribution to this team project.

It includes:

- FastAPI application architecture with API versioning (`/api/v1`)
- Verification endpoint with file upload handling
- Pydantic request/response schemas (stable API contract for the React frontend)
- File validation (type, size, image integrity, temp file cleanup)
- Service layer (verification orchestration, consistency checks, risk scoring, mock database, audit)
- AI pipeline orchestrator (`ai/pipeline.py`) — calls existing AI teammate modules in sequence
- DOB format normalisation fixing OCR (DD-MM-YYYY) vs MRZ (YYMMDD) comparison
- Explainable risk scoring with per-component contributions
- CORS configuration (origin-controlled, not `allow_origins=["*"]`)
- Structured error handling (no stack traces sent to frontend)
- Comprehensive test suite
- README / API documentation

**I do NOT claim ownership of:**
- `ai/ocr.py` — EasyOCR integration (AI team)
- `ai/mrz.py` — MRZ parsing (AI team)
- `ai/preprocessing.py` — image preprocessing (AI team)
- `ai/tampering.py` — ResNet18 tamper classifier (AI team)
- `ai/validation.py` — field validation utilities (AI team)
- `ai/ml/train.py` — model training script (AI team)

---

## Setup

### Prerequisites

- Python 3.10 or newer
- pip

### 1. Create a virtual environment

```bash
cd backend
python -m venv venv
```

Activate it:

- **Windows PowerShell:** `.\venv\Scripts\Activate.ps1`
- **Windows CMD:** `venv\Scripts\activate.bat`
- **macOS/Linux:** `source venv/bin/activate`

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> **PyTorch note:** The `requirements.txt` pins `torch==2.3.0`. If you need CPU-only or a specific CUDA version, install PyTorch separately first using the command from [pytorch.org](https://pytorch.org/get-started/locally/), then run `pip install -r requirements.txt`.

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env as needed
```

---

## Running the Server

From the `backend/` directory:

```bash
uvicorn app.main:app --reload
```

The server starts at `http://localhost:8000`.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/verify` | Verify a document image |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/redoc` | ReDoc documentation |
| `GET` | `/openapi.json` | OpenAPI schema |

---

## Swagger Documentation

Open `http://localhost:8000/docs` after starting the server.

The Swagger UI allows you to:
- Read full endpoint descriptions
- Try the verification endpoint with a real document image upload
- Inspect the complete request/response schema

---

## Example Request & Response

### Request

```bash
curl -X POST http://localhost:8000/api/v1/verify \
  -F "document=@/path/to/passport.jpg"
```

### Response (abbreviated)

```json
{
  "request_id": "a4f1b2c3d4e5f6a7",
  "status": "completed",

  "document": {
    "type": "passport",
    "quality": { "usable": true, "warnings": [] }
  },

  "ocr": {
    "status": "completed",
    "fields": {
      "passport_number": "A1234567",
      "date_of_birth": "15-04-1990",
      "date_of_expiry": "15-04-2030",
      "nationality": "IND"
    }
  },

  "mrz": {
    "status": "completed",
    "valid": true,
    "fields": {
      "surname": "SMITH",
      "given_names": "JOHN",
      "passport_number": "A1234567",
      "nationality": "IND",
      "date_of_birth": "900415",
      "expiry_date": "300415",
      "sex": "M"
    },
    "checks": {
      "passport_number": true,
      "date_of_birth": true,
      "expiry_date": true
    }
  },

  "consistency": {
    "overall_match": true,
    "checks": [
      {
        "field": "passport_number",
        "visual_value": "A1234567",
        "mrz_value": "A1234567",
        "match": true,
        "severity": "low",
        "reason": "Passport numbers match."
      }
    ]
  },

  "tampering": {
    "status": "not_available",
    "detected": null,
    "confidence": null,
    "note": "Tampering model (ai/ml/tampering_model.pth) was not found. Train the model using ai/ml/train.py before enabling this check."
  },

  "face_verification": {
    "status": "not_available",
    "match": null,
    "reason": "Face verification module is not currently configured."
  },

  "liveness": {
    "status": "not_available",
    "passed": null,
    "reason": "Liveness detection module is not currently configured."
  },

  "validation": {
    "document_valid": true,
    "issues": []
  },

  "database_checks": {
    "status": "mock",
    "alerts": [],
    "note": "Database checks are performed against mock/synthetic data only. No real government database has been queried."
  },

  "risk": {
    "score": 0.0,
    "level": "low",
    "reasons": [],
    "contributions": [...]
  },

  "recommendation": {
    "action": "normal_clearance",
    "reason": "No significant flags detected. Normal officer processing recommended."
  },

  "warnings": [
    "Tampering detection was not performed. Tampering model (ai/ml/tampering_model.pth) was not found."
  ],

  "audit": {
    "request_id": "a4f1b2c3d4e5f6a7",
    "timestamp": "2026-09-09T15:17:41+00:00",
    "pipeline_version": "1.0.0",
    "checks_executed": ["ocr", "mrz", "consistency", "validation", "database_mock", "risk"],
    "processing_time_ms": 4281.3
  }
}
```

---

## Running Tests

### Backend / API tests (no AI dependencies needed)

```bash
cd backend
pytest tests/ -v
```

### AI module unit tests

```bash
cd backend
pytest test_ai.py -v
```

### All tests

```bash
cd backend
pytest -v
```

> Tests mock all AI modules — they do not require EasyOCR, PyTorch, or trained model files to pass.

---

## Environment Variables

See `.env.example` for all available options.

| Variable | Default | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | `development` or `production` |
| `ALLOWED_ORIGINS` | `http://localhost:3000,...` | Comma-separated frontend origins for CORS |
| `MAX_UPLOAD_BYTES` | `10485760` | Maximum upload size (bytes) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `MOCK_DATABASE` | `true` | Use mock database (keep `true` for prototype) |
| `TAMPERING_MODEL_PATH` | *(auto)* | Override path to trained tampering model |

---

## AI Integration Explanation

The backend integration layer (`ai/pipeline.py`) calls the AI team's modules in this sequence:

1. **Preprocessing** (`ai/preprocessing.py`) — loads and enhances the image
2. **OCR** (`ai/ocr.py`) — extracts visible text fields
3. **MRZ** (`ai/mrz.py`) — parses and validates MRZ check digits
4. **Tampering** (`ai/tampering.py`) — runs ResNet18 classifier *(requires trained model)*

Each step is fault-tolerant: if a module fails, the pipeline continues and marks that module as `failed` or `not_available` rather than crashing.

The backend service layer then:
- Cross-references OCR and MRZ fields (passport number, DOB, nationality)
- Applies rule-based document validity checks (expiry)
- Queries mock database
- Computes weighted explainable risk score

---

## Known Limitations

| Limitation | Detail |
|---|---|
| Face verification | Module does not exist — always `not_available` |
| Liveness detection | Module does not exist — always `not_available` |
| Tampering detection | Requires trained model at `ai/ml/tampering_model.pth` |
| Database checks | Mock/synthetic only — no real government API |
| MRZ support | TD3 (passport, 44-char × 2 lines) only |
| OCR field extraction | Regex-based — may fail on non-standard layouts |
| DOB normalisation | Assumes OCR date is DD-MM-YYYY or DD/MM/YYYY |
| AI confidence | Probabilistic — not legal proof |
| UV/hologram features | Cannot be verified from RGB images |

---

*PramaanX — AI-Powered Border Document Intelligence and Identity Verification Platform*
