# PramaanX — Backend Contribution & Changes

> **Author:** Backend Integration Team  
> **Date:** September 2026  
> **Project:** PramaanX — AI-Based Fake Identity Document Screening System

---

## Table of Contents

1. [What Was Built](#what-was-built)
2. [Complete File Structure](#complete-file-structure)
3. [Each File Explained](#each-file-explained)
4. [How to Run the Backend](#how-to-run-the-backend)
5. [API Endpoints](#api-endpoints)
6. [Why Are Some Statuses Showing `not_available` or `failed`?](#why-are-some-statuses-showing-not_available-or-failed)
7. [Solutions to Fix Each Status](#solutions-to-fix-each-status)
8. [Test Results](#test-results)
9. [What I Did NOT Touch (AI Team Code)](#what-i-did-not-touch-ai-team-code)

---

## What Was Built

The backend is a **FastAPI REST API** that acts as the integration layer between:
- The **React frontend** (other team member)
- The **AI modules** — `ocr.py`, `mrz.py`, `tampering.py`, `preprocessing.py`, `validation.py` (AI team member)

My job was to **connect everything together** into a single working API with:
- Proper request/response contracts (Pydantic schemas)
- File upload validation and security
- Cross-source consistency checking (OCR field values vs MRZ field values)
- Explainable risk scoring
- Audit logging
- Full Swagger documentation
- 25 automated tests

---

## Complete File Structure

```
ai_pipeline/                          ← (formerly backend/) FastAPI + AI pipeline
│
├── ai/                               ← AI team's code (I did NOT modify these)
│   ├── ml/
│   │   └── train.py                  ← ResNet18 training script (AI team)
│   ├── __init__.py                   ← Added package docstring only
│   ├── mrz.py                        ← ICAO MRZ parsing (AI team)
│   ├── ocr.py                        ← EasyOCR text extraction (AI team)
│   ├── pipeline.py                   ← ✅ NEW — my orchestrator calling AI modules
│   ├── preprocessing.py              ← Image preprocessing (AI team)
│   ├── tampering.py                  ← ResNet18 tamper detector (AI team)
│   └── validation.py                 ← Field validation utilities (AI team)
│
├── app/                              ← ✅ NEW — entire FastAPI application (my work)
│   ├── main.py                       ← App entry point, CORS, error handling
│   │
│   ├── api/
│   │   └── v1/
│   │       ├── router.py             ← Routes all v1 endpoints
│   │       └── endpoints/
│   │           ├── health.py         ← GET /api/v1/health
│   │           └── verification.py   ← POST /api/v1/verify
│   │
│   ├── schemas/
│   │   ├── common.py                 ← Shared Enums (status, risk level, severity)
│   │   ├── errors.py                 ← Structured error format
│   │   └── verification.py           ← Full API response schema (Pydantic)
│   │
│   ├── services/
│   │   ├── verification_service.py   ← Master orchestrator (main logic)
│   │   ├── validation_service.py     ← OCR vs MRZ consistency checks
│   │   ├── risk_service.py           ← Weighted, explainable risk scoring
│   │   ├── database_service.py       ← Mock database adapter
│   │   └── audit_service.py          ← Privacy-safe audit record builder
│   │
│   ├── core/
│   │   ├── config.py                 ← Pydantic Settings (reads .env)
│   │   └── logging.py                ← Secure logging (masks sensitive fields)
│   │
│   └── utils/
│       └── file_utils.py             ← File upload validation + temp cleanup
│
├── tests/
│   └── test_backend.py               ← ✅ NEW — 25 automated API tests
│
├── test_ai.py                        ← ✅ NEW — AI module unit tests
├── requirements.txt                  ← ✅ Updated — all dependencies
├── pyproject.toml                    ← ✅ NEW — pytest configuration
├── .env.example                      ← ✅ NEW — environment variable template
├── .gitignore                        ← ✅ Updated
└── README.md                         ← ✅ Updated — full project docs
```

---

## Each File Explained

### `ai/pipeline.py` — AI Pipeline Orchestrator
This is the **bridge between the backend and the AI team's code**. It calls the AI modules in the correct order:

```
preprocessing.py → ocr.py → mrz.py → tampering.py
```

Key design decisions:
- Each step is wrapped in a `try/except` — if one module fails, the rest still run
- Missing modules (ImportError) → status set to `not_available` (not a crash)
- Missing model files (FileNotFoundError) → status set to `not_available`
- All outputs are normalised into a standard dict format

---

### `app/main.py` — FastAPI Application
- Creates the FastAPI app
- Configures **CORS** (only allows frontend origins from `.env`, not `"*"`)
- Registers all routes under `/api/v1`
- Global exception handler — **never sends Python stack traces to the client**
- Sets `sys.path` so AI teammate modules are importable

---

### `app/schemas/verification.py` — API Response Schema
Defines exactly what the API returns. This is the **contract between backend and frontend**. Every field has a type, and FastAPI auto-generates the Swagger docs from these.

Includes schemas for:
- `OcrResult` — extracted visual fields
- `MrzResult` — extracted MRZ machine fields + check digit results
- `ConsistencyResult` — per-field comparison (OCR vs MRZ)
- `TamperingResult` — tampering probability
- `FaceVerificationResult` — face match (not_available)
- `LivenessResult` — liveness check (not_available)
- `ValidationResult` — rule-based checks (expiry, check digits)
- `DatabaseCheckResult` — watchlist/lost document alerts
- `RiskResult` — overall risk score + per-component breakdown
- `RecommendationResult` — suggested officer action
- `AuditInfo` — metadata (request ID, timestamp, checks run, processing time)

---

### `app/services/verification_service.py` — Master Orchestrator
The top-level service that:
1. Calls `ai/pipeline.py`
2. Normalises all raw outputs into Pydantic objects
3. Runs consistency checks
4. Performs rule-based expiry validation
5. Queries mock database
6. Computes risk score
7. Builds audit record
8. Returns the full `VerificationResponse`

---

### `app/services/validation_service.py` — Consistency Checker
Cross-references OCR fields vs MRZ fields.

**Important fix included:** OCR reads dates as `DD-MM-YYYY` (e.g., `15-04-1990`) but MRZ encodes dates as `YYMMDD` (e.g., `900415`). These two formats need to be **normalised** before comparison — without this fix, DOB comparison always fails even when both sources have the same date.

---

### `app/services/risk_service.py` — Risk Scoring
Weighted scoring across 5 components:

| Component | Weight | Trigger |
|---|---|---|
| Tampering detection | 35% | High tamper probability |
| MRZ check digits | 25% | Failed ICAO check digits |
| OCR/MRZ consistency | 20% | Mismatched fields |
| Document validity | 15% | Expired, parse errors |
| Database alerts | 5% | Reported lost/stolen |

Output: a score 0–100, risk level (`low`/`medium`/`high`), and a list of human-readable reasons explaining the score.

---

### `app/utils/file_utils.py` — File Upload Security
Before the AI pipeline runs, every uploaded file is checked:
1. **Extension whitelist** — only jpg, jpeg, png, bmp, tiff, webp allowed → HTTP 415
2. **File size limit** — max 10 MB → HTTP 413
3. **Empty file check** — zero bytes rejected → HTTP 400
4. **OpenCV content check** — file is decoded as an actual image; garbage data rejected → HTTP 400
5. **Temp file cleanup** — file is always deleted after processing (context manager pattern)

---

### `app/services/database_service.py` — Mock Database
**Clearly labelled as MOCK.**  
In a real deployment, this would call a government passport/watchlist API. For this prototype, it checks against a tiny hardcoded dict of fake document numbers. Returns `status: "mock"` so the frontend can display the disclaimer.

---

### `app/core/config.py` — Configuration
All configuration is read from environment variables / `.env` file. No hardcoded values. Settings include:
- `ALLOWED_ORIGINS` — CORS origins
- `MAX_UPLOAD_BYTES` — file size limit
- `LOG_LEVEL` — logging verbosity
- `MOCK_DATABASE` — toggle mock DB
- `TAMPERING_MODEL_PATH` — path to trained model

---

### `tests/test_backend.py` — Automated Tests (25 tests)
All AI modules are **mocked** in tests, so tests pass even without EasyOCR/PyTorch installed.

Test classes:
- `TestHealthEndpoint` — 3 tests
- `TestSwaggerDocs` — 2 tests
- `TestFileValidation` — 5 tests (each validation error path)
- `TestVerificationSuccess` — 8 tests (full pipeline with mocked AI)
- `TestPipelineFailure` — 1 test (503 on AI crash)
- `TestConsistencyChecks` — 2 tests (DOB mismatch, passport match)
- `TestRiskScoring` — 2 tests (high tamper = high risk, no tamper = low risk)
- `TestErrorStructure` — 2 tests

---

## How to Run the Backend

### Step 1 — Create virtual environment
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### Step 2 — Install lightweight dependencies (for API + tests only)
```powershell
pip install fastapi "uvicorn[standard]" python-multipart pydantic-settings httpx pytest pytest-asyncio opencv-python-headless numpy
```

### Step 3 — Install AI dependencies (needed for OCR/MRZ/tampering to work)
```powershell
# Install PyTorch first (CPU version — smaller):
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Then install EasyOCR:
pip install easyocr
```

### Step 4 — Create `.env` file
```powershell
copy .env.example .env
```

### Step 5 — Start the server
```powershell
.\venv\Scripts\uvicorn.exe app.main:app --reload
# OR with venv activated:
uvicorn app.main:app --reload
```

### Step 6 — Open Swagger UI
Go to: **http://localhost:8000/docs**

---

## API Endpoints

| Method | URL | Description |
|---|---|---|
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/verify` | Upload a document image → get verification report |
| `GET` | `/docs` | Swagger UI (interactive) |
| `GET` | `/redoc` | ReDoc documentation |
| `GET` | `/openapi.json` | Raw OpenAPI schema |

### Example: Verify a document
```bash
curl -X POST http://localhost:8000/api/v1/verify \
  -F "document=@/path/to/passport.jpg"
```

---

## Why Are Some Statuses Showing `not_available` or `failed`?

When you run the server and call `POST /api/v1/verify`, some module statuses come back as `not_available` or `failed`. Here is the detailed reason for each:

---

### ❌ `ocr.status: not_available` — EasyOCR Not Installed

**What it means:**  
The OCR module (`ai/ocr.py`) tried to import EasyOCR but the library is not installed in the virtual environment.

**Why it happens:**  
During setup, only the lightweight packages (FastAPI, OpenCV, NumPy) were installed to keep the setup fast. EasyOCR was not included because:
- EasyOCR itself is ~100 MB
- It depends on **PyTorch**, which is 2–4 GB
- It downloads additional language model weights (~600 MB) on first use

The pipeline catches the `ImportError` gracefully and marks the status as `not_available` instead of crashing.

---

### ❌ `mrz.status: failed` — Two Reasons

**Reason 1 — EasyOCR not installed:**  
`ai/mrz.py` also uses EasyOCR internally to read the MRZ text from the bottom of a passport. Same issue as above.

**Reason 2 — No real passport image:**  
Even if EasyOCR were installed, a live test was done using a tiny 10×10 white PNG (programmatically generated). That image has no passport text or MRZ zone. A real passport scan is needed for MRZ to work.

---

### ❌ `tampering.status: not_available` — Model File + PyTorch Missing

**What it means:**  
The tampering detector (`ai/tampering.py`) uses a **ResNet18 deep learning model** that must be trained first and saved as a `.pth` file. Two things are missing:

1. **PyTorch is not installed** in the venv — so even importing the module fails
2. **The trained model file** (`ai/ml/tampering_model.pth`) does not exist — it must be generated by running the training script (`ai/ml/train.py`) on a labelled dataset

The pipeline catches both the `ImportError` and `FileNotFoundError` and marks the result as `not_available`.

---

### ❌ `face_verification.status: not_available` — Module Was Never Built

**What it means:**  
This is **intentional and by design**.

There is **no `ai/face.py` file** in the entire repository. The face verification module (live selfie vs passport photo comparison) was never built by the AI team — it's planned for a future phase.

Rather than returning a fake result like `{"match": true}` (which would be dishonest and dangerous for a security system), the backend honestly reports `not_available` with a note explaining why.

---

### Summary Table

| Module | Status Shown | Root Cause | Category |
|---|---|---|---|
| OCR | `not_available` | EasyOCR library not installed | Dependency missing |
| MRZ | `failed` | EasyOCR missing + no real passport image | Dependency + Input |
| Tampering | `not_available` | PyTorch missing + model not trained | Dependency + Model |
| Face Verify | `not_available` | Module was never built | Feature not implemented |

---

## Solutions to Fix Each Status

### Fix OCR + MRZ → Install EasyOCR + PyTorch

```powershell
# Step 1: Install PyTorch (CPU version — works on any machine)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Step 2: Install EasyOCR
pip install easyocr
```

> ⚠️ First time EasyOCR runs, it will download ~600 MB of model weights automatically.  
> After this, restart the server — OCR and MRZ will start working.

---

### Fix Tampering → Train the Model

```powershell
# You need a dataset of real vs tampered document images first
# Then run:
cd backend
python ai/ml/train.py
# This creates: ai/ml/tampering_model.pth
```

After the `.pth` file exists (and PyTorch is installed), restart the server — tampering will start working.

---

### Fix Face Verification → Build the Module (Future Work)

The AI team needs to build `ai/face.py` with a function `run_face_verification(document_image_path, selfie_image_path)`. The backend is already structured to integrate it — only the module itself is missing.

---

### After Installing Everything — Expected Output

Once EasyOCR, PyTorch, and the trained model are in place, calling `POST /api/v1/verify` with a real passport scan should return:

```json
{
  "status": "completed",
  "ocr": { "status": "completed", "fields": { "passport_number": "...", ... } },
  "mrz": { "status": "completed", "valid": true, "checks": { ... } },
  "tampering": { "status": "completed", "detected": false, "confidence": 0.02 },
  "consistency": { "overall_match": true, "checks": [ ... ] },
  "risk": { "score": 0.0, "level": "low" },
  "recommendation": { "action": "normal_clearance" }
}
```

---

## Test Results

All 25 automated tests pass **without** needing EasyOCR or PyTorch installed. AI modules are mocked in tests.

```
pytest tests/test_backend.py -v

25 passed in 0.67s ✅
```

To run the tests:
```powershell
cd backend
.\venv\Scripts\python.exe -m pytest tests/ -v
```

---

## What I Did NOT Touch (AI Team Code)

The following files were written by the AI team and were **not modified** by me:

| File | Author | Purpose |
|---|---|---|
| `ai/ocr.py` | AI Team | EasyOCR text extraction from document |
| `ai/mrz.py` | AI Team | ICAO TD3 MRZ parsing + check-digit validation |
| `ai/preprocessing.py` | AI Team | OpenCV image loading and enhancement |
| `ai/tampering.py` | AI Team | ResNet18 tamper-detection classifier |
| `ai/validation.py` | AI Team | Cross-field matching utilities |
| `ai/ml/train.py` | AI Team | ResNet18 model training script |

The **only** file I added to the `ai/` folder is `ai/pipeline.py`, which is the orchestration layer that calls the above modules in sequence.

---

*PramaanX Backend — Built with FastAPI | Privacy by Design | Decision Support Only*
