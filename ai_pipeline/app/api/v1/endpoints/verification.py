"""
PramaanX — Document Verification Endpoint
-------------------------------------------
POST /api/v1/verify

Accepts a document image upload and returns a structured verification report
including:
  - OCR field extraction
  - MRZ parsing and ICAO check-digit validation
  - Cross-source consistency checks (visual vs MRZ)
  - Tampering detection (when model is available)
  - Document rule-based validation (expiry, etc.)
  - Mock database alert check
  - Explainable risk score
  - Recommended action for the officer

IMPORTANT:
  This endpoint does NOT make decisions on behalf of the officer.
  The 'recommendation' field is a support signal only.
  All final decisions remain with the authorised human officer.
"""

import traceback

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from app.core.logging import get_logger
from app.schemas.verification import VerificationResponse
from app.services.verification_service import run_verification
from app.utils.file_utils import saved_temp_image

logger = get_logger(__name__)
router = APIRouter()


@router.post(
    "/verify",
    response_model=VerificationResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify a Document",
    description=(
        "Upload a passport or identity document image for AI-assisted screening. "
        "\n\n"
        "**Supported formats:** JPEG, PNG, BMP, TIFF, WebP  \n"
        "**Maximum file size:** 10 MB  \n\n"
        "The response contains evidence from multiple independent sources "
        "(visual OCR, MRZ machine data) and an explainable risk assessment. "
        "The final decision remains with the authorised officer."
    ),
    responses={
        400: {"description": "Invalid or unreadable image file"},
        413: {"description": "Uploaded file exceeds maximum allowed size"},
        415: {"description": "Unsupported file type"},
        422: {"description": "Request validation error"},
        500: {"description": "Unexpected server error"},
        503: {"description": "AI processing module unavailable"},
    },
    tags=["Verification"],
)
async def verify_document(
    document: UploadFile = File(
        ...,
        description=(
            "Document image to verify. "
            "Must be a valid image file (JPEG, PNG, BMP, TIFF, or WebP) "
            "under 10 MB."
        ),
    ),
) -> VerificationResponse:
    """
    Main verification endpoint.

    1. Validates the uploaded file (type, size, image integrity).
    2. Saves it to a temporary file (deleted after processing).
    3. Runs the PramaanX AI pipeline.
    4. Returns the structured verification report.
    """
    logger.info("Received verification request (filename masked for privacy)")

    # File validation + temp file creation are handled by the context manager.
    # The file is ALWAYS deleted when the block exits.
    with saved_temp_image(document) as tmp_path:
        try:
            result = run_verification(tmp_path)
            return result

        except RuntimeError as exc:
            logger.error("Verification pipeline error: %s", exc)
            raise HTTPException(
                status_code=503,
                detail={
                    "error": {
                        "code": "PIPELINE_ERROR",
                        "message": (
                            "The AI processing pipeline encountered an error. "
                            "Please try again or contact support."
                        ),
                    }
                },
            ) from exc

        except Exception as exc:  # noqa: BLE001
            # Log the full traceback server-side; never send it to the client
            logger.error(
                "Unexpected verification error: %s\n%s",
                exc,
                traceback.format_exc(),
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "An unexpected error occurred during verification.",
                    }
                },
            ) from exc
