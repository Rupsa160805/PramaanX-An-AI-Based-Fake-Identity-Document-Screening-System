"""
PramaanX — FastAPI Application
================================
Entry point for the PramaanX backend API.

Run locally with:
    cd backend
    uvicorn app.main:app --reload

Swagger UI:   http://localhost:8000/docs
ReDoc:        http://localhost:8000/redoc
OpenAPI JSON: http://localhost:8000/openapi.json
"""

import sys
import os

# Ensure the backend/ directory is on sys.path so that 'ai.*' modules
# (developed by the AI teammate) can be imported by the pipeline.
_backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import router as v1_router
from app.core.config import settings
from app.core.logging import setup_logging, get_logger

# Initialise logging before anything else
setup_logging()
logger = get_logger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Application factory
# ──────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="PramaanX API",
    description=(
        "## PramaanX — AI-Powered Border Document Intelligence\n\n"
        "**Tagline:** *Scan. Verify. Explain.*\n\n"
        "---\n\n"
        "PramaanX is a multimodal, AI-assisted document screening and identity "
        "verification platform designed for authorized border/immigration officers.\n\n"
        "### Important\n"
        "PramaanX is a **decision-support system**, not an automated decision-maker. "
        "The final decision on every traveller remains with the authorized human officer.\n\n"
        "### Identity Evidence Triangle\n"
        "The system cross-references three independent evidence sources:\n"
        "1. **Visual Evidence** — OCR of printed document data\n"
        "2. **Machine Evidence** — MRZ / barcode / QR data\n"
        "3. **Live Evidence** — Live face (module planned; not yet available)\n\n"
        "### Limitations\n"
        "- Face verification and liveness detection are **not yet implemented**.\n"
        "- Tampering detection requires a trained model file.\n"
        "- Database checks use **mock/synthetic data** (no real government API).\n"
        "- AI outputs are probabilistic — they are **not** legal proof.\n\n"
        "---\n\n"
        "**Backend API / Integration:** PramaanX backend team\n"
        "**AI Models:** PramaanX AI team\n"
    ),
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    contact={
        "name": "PramaanX Team",
    },
    license_info={
        "name": "For academic / demonstration use only",
    },
)


# ──────────────────────────────────────────────────────────────────────────────
# CORS — controlled, configurable, NOT "*"
# ──────────────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

logger.info(
    "CORS configured for origins: %s",
    settings.cors_origins,
)


# ──────────────────────────────────────────────────────────────────────────────
# Global exception handler — never expose stack traces to clients
# ──────────────────────────────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": (
                    "An unexpected error occurred. "
                    "Please try again or contact support."
                ),
            }
        },
    )


# ──────────────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────────────

app.include_router(v1_router, prefix="/api/v1")


# ──────────────────────────────────────────────────────────────────────────────
# Root redirect
# ──────────────────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root():
    return {
        "message": "PramaanX API is running.",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


logger.info(
    "PramaanX %s started — environment: %s",
    settings.app_version,
    settings.environment,
)
