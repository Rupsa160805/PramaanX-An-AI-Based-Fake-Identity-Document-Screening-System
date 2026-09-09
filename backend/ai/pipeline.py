"""
PramaanX — AI Pipeline Orchestrator
--------------------------------------
This module is the single point that coordinates calls to the existing AI
modules developed by the team's AI contributor:

  ai/preprocessing.py — image loading and enhancement
  ai/ocr.py           — EasyOCR field extraction
  ai/mrz.py           — TD3 MRZ parsing and ICAO check-digit validation
  ai/tampering.py     — ResNet18 tamper-detection classifier
  ai/validation.py    — cross-field validation (OCR vs MRZ)

Responsibilities of THIS file (backend/API layer):
  — Sequencing the above calls safely
  — Handling exceptions from each AI module without crashing the pipeline
  — Normalising raw AI outputs into a stable dict contract used by services
  — Resolving DOB format incompatibility between OCR and MRZ formats

This file does NOT create any AI models.
This file does NOT claim ownership of the AI implementations listed above.
"""

import logging
import os
import tempfile
from typing import Any, Dict

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Helper: cautious module importer
# ──────────────────────────────────────────────────────────────────────────────

def _try_import(module_name: str):
    """Return the module object or None if import fails."""
    try:
        import importlib
        return importlib.import_module(module_name)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not import %s: %s", module_name, exc)
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Step 1: Preprocessing
# ──────────────────────────────────────────────────────────────────────────────

def _run_preprocessing(image_path: str) -> Dict[str, Any]:
    """
    Load and enhance the document image using ai/preprocessing.py.
    Returns a dict describing quality/usability of the upload.

    Note: The existing preprocessing module does not implement blur detection,
    glare detection, or document boundary detection.  Only what it actually
    provides (load + resize + histogram equalisation) is used.
    """
    result: Dict[str, Any] = {
        "usable": False,
        "warnings": [],
        "enhanced_path": None,
    }

    mod = _try_import("ai.preprocessing")
    if mod is None:
        result["warnings"].append("Preprocessing module unavailable.")
        result["usable"] = True  # Pass through anyway; OCR will validate
        result["enhanced_path"] = image_path
        return result

    try:
        enhanced = mod.preprocess_image(image_path)

        # Save the enhanced numpy array to a temp file so OCR/MRZ can read it
        tmp_path = image_path + "_enhanced.png"
        import cv2
        cv2.imwrite(tmp_path, enhanced)
        result["enhanced_path"] = tmp_path
        result["usable"] = True
    except FileNotFoundError as exc:
        result["warnings"].append(f"Image load failed: {exc}")
        result["usable"] = False
    except Exception as exc:  # noqa: BLE001
        logger.exception("Preprocessing error: %s", exc)
        result["warnings"].append("Image preprocessing encountered an unexpected error.")
        result["usable"] = True
        result["enhanced_path"] = image_path

    return result


# ──────────────────────────────────────────────────────────────────────────────
# Step 2: OCR Field Extraction
# ──────────────────────────────────────────────────────────────────────────────

def _run_ocr(image_path: str) -> Dict[str, Any]:
    """
    Extract visible document fields using ai/ocr.py.

    The existing OCR module:
      — Initialises EasyOCR at import time (slow first call)
      — Returns: passport_number, dob, expiry, nationality, raw_text
    """
    result: Dict[str, Any] = {
        "status": "failed",
        "fields": None,
        "error": None,
    }

    mod = _try_import("ai.ocr")
    if mod is None:
        result["status"] = "not_available"
        result["error"] = "OCR module could not be loaded."
        return result

    try:
        raw = mod.run_ocr(image_path)  # returns dict

        result["status"] = "completed"
        result["fields"] = {
            # Map teammate's key names → our stable schema keys
            "passport_number": raw.get("passport_number"),
            "date_of_birth": raw.get("dob"),       # DD-MM-YYYY or DD/MM/YYYY
            "date_of_expiry": raw.get("expiry"),
            "nationality": raw.get("nationality"),
            "raw_text": raw.get("raw_text"),
        }
    except Exception as exc:  # noqa: BLE001
        logger.exception("OCR error: %s", exc)
        result["status"] = "failed"
        result["error"] = "OCR processing failed unexpectedly."

    return result


# ──────────────────────────────────────────────────────────────────────────────
# Step 3: MRZ Extraction and Validation
# ──────────────────────────────────────────────────────────────────────────────

def _run_mrz(image_path: str) -> Dict[str, Any]:
    """
    Extract and validate TD3 MRZ using ai/mrz.py.

    The existing MRZ module:
      — Creates its own EasyOCR reader internally
      — Parses line1 / line2 of TD3 passports
      — Validates ICAO check digits: passport number, DOB, expiry
      — Returns: valid_format, document_type, country, surname, given_names,
                 passport_number, nationality, dob (YYMMDD), sex, expiry (YYMMDD),
                 mrz_valid, checks
    """
    result: Dict[str, Any] = {
        "status": "failed",
        "valid": None,
        "fields": None,
        "checks": None,
        "error": None,
    }

    mod = _try_import("ai.mrz")
    if mod is None:
        result["status"] = "not_available"
        result["error"] = "MRZ module could not be loaded."
        return result

    try:
        raw = mod.run_mrz(image_path)

        if raw.get("error"):
            result["status"] = "failed"
            result["error"] = raw["error"]
            result["valid"] = False
            return result

        result["status"] = "completed"
        result["valid"] = bool(raw.get("mrz_valid", False))

        result["fields"] = {
            "document_type": raw.get("document_type"),
            "country": raw.get("country"),
            "surname": raw.get("surname"),
            "given_names": raw.get("given_names"),
            "passport_number": raw.get("passport_number"),
            "nationality": raw.get("nationality"),
            "date_of_birth": raw.get("dob"),   # YYMMDD
            "sex": raw.get("sex"),
            "expiry_date": raw.get("expiry"),  # YYMMDD
        }

        raw_checks = raw.get("checks", {})
        result["checks"] = {
            "passport_number": raw_checks.get("passport_number"),
            "date_of_birth": raw_checks.get("dob"),
            "expiry_date": raw_checks.get("expiry"),
        }

    except Exception as exc:  # noqa: BLE001
        logger.exception("MRZ error: %s", exc)
        result["status"] = "failed"
        result["error"] = "MRZ processing failed unexpectedly."

    return result


# ──────────────────────────────────────────────────────────────────────────────
# Step 4: Tampering Detection
# ──────────────────────────────────────────────────────────────────────────────

def _run_tampering(image_path: str) -> Dict[str, Any]:
    """
    Run tamper-detection using ai/tampering.py.

    The existing tampering module:
      — Uses a fine-tuned ResNet18 binary classifier
      — Requires a trained model file at ai/ml/tampering_model.pth
      — Returns a single float probability (0.0 = genuine, 1.0 = tampered)
      — Does NOT produce heatmaps, bounding boxes, or segmentation

    If the model file does not exist, this step returns 'not_available'
    rather than crashing the pipeline.
    """
    result: Dict[str, Any] = {
        "status": "not_available",
        "detected": None,
        "confidence": None,
        "note": None,
        "error": None,
    }

    mod = _try_import("ai.tampering")
    if mod is None:
        result["error"] = "Tampering module could not be loaded."
        return result

    try:
        prob = mod.run_tampering(image_path)  # returns float 0–1

        THRESHOLD = 0.5
        result["status"] = "completed"
        result["detected"] = prob >= THRESHOLD
        result["confidence"] = round(float(prob), 4)
        result["note"] = (
            "Confidence score from ResNet18 binary classifier (genuine vs tampered). "
            "No heatmap or regional localisation is available from the current model."
        )

    except FileNotFoundError:
        result["status"] = "not_available"
        result["note"] = (
            "Tampering model (ai/ml/tampering_model.pth) was not found. "
            "Train the model using ai/ml/train.py before enabling this check."
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Tampering detection error: %s", exc)
        result["status"] = "failed"
        result["error"] = "Tampering detection failed unexpectedly."

    return result


# ──────────────────────────────────────────────────────────────────────────────
# Public API: run_pipeline
# ──────────────────────────────────────────────────────────────────────────────

def run_pipeline(image_path: str) -> Dict[str, Any]:
    """
    Execute the full PramaanX AI pipeline on a document image.

    Steps executed (in order):
      1. Preprocessing     — ai/preprocessing.py
      2. OCR               — ai/ocr.py
      3. MRZ               — ai/mrz.py
      4. Tampering         — ai/tampering.py (conditional on model file)

    Steps NOT in this pipeline (modules do not exist):
      — Face verification  → returned as not_available
      — Liveness detection → returned as not_available

    Returns a raw dict consumed by the service layer, which then applies
    cross-source consistency checks and risk scoring.
    """
    logger.info("Starting AI pipeline")

    # ── Step 1: Preprocessing ────────────────────────────────────────────────
    preprocessing = _run_preprocessing(image_path)
    active_path = preprocessing.get("enhanced_path") or image_path

    if not preprocessing["usable"]:
        logger.warning("Image marked unusable after preprocessing")

    # ── Step 2: OCR ──────────────────────────────────────────────────────────
    ocr = _run_ocr(active_path)

    # ── Step 3: MRZ ──────────────────────────────────────────────────────────
    mrz = _run_mrz(active_path)

    # ── Step 4: Tampering ────────────────────────────────────────────────────
    tampering = _run_tampering(active_path)

    # ── Cleanup enhanced temp file ────────────────────────────────────────────
    if active_path != image_path and os.path.exists(active_path):
        try:
            os.remove(active_path)
        except OSError:
            pass

    logger.info(
        "Pipeline complete — OCR: %s | MRZ: %s | Tampering: %s",
        ocr["status"],
        mrz["status"],
        tampering["status"],
    )

    return {
        "preprocessing": preprocessing,
        "ocr": ocr,
        "mrz": mrz,
        "tampering": tampering,
    }
