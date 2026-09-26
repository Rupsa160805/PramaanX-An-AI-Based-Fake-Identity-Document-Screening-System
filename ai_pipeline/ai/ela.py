"""Error Level Analysis (ELA) — deterministic localized-forgery detector.

The trained ResNet18 classifier makes a single global genuine/tampered decision
and reliably catches the tamper styles in its training distribution, but a small
*localized* forgery — e.g. a photo region recompressed at low quality then pasted
into an otherwise high-quality document — can leave no global signature for a
224x224 RGB classifier to see. ELA targets exactly that case, with no model:

  1. Re-save the image at a fixed JPEG quality and diff against the original.
  2. A region that was already heavily recompressed sits near its compression
     floor and barely changes on re-save (anomalously LOW error), while a freshly
     pasted/overwritten region has sharp edges that change a lot (anomalously
     HIGH error). A genuine single-compression image has a fairly uniform error
     level across all blocks.
  3. We score the image by how strongly its worst blocks deviate from the robust
     centre of the block-error distribution (median / MAD).

This is a complementary signal to the ML classifier, never a replacement: it is
combined conservatively so it can only *raise* tamper confidence when the local
evidence is strong, and cannot turn a confident-genuine result into tampered on
weak evidence.
"""
from __future__ import annotations

import io
import logging
from typing import Any, Dict

import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

_RESAVE_QUALITY = 90
_GRID = 16                 # analysis grid (GRID x GRID blocks)
_MIN_BLOCKS = 24           # need enough blocks for robust statistics
_CONTENT_PCTL = 55         # gradient percentile above which a block has content
_DEV_SATURATE = 6.0        # block ratio deviation (in MADs) mapped to score ~1.0
_MAX_ANOMALY_FRAC = 0.30   # a localized tamper flags a minority of content blocks
_SCORE_THRESHOLD = 0.55    # ELA-only "detected" threshold


def _block_maps(image_path: str) -> tuple[np.ndarray, np.ndarray] | None:
    """Return (residual, gradient) GRID x GRID per-block mean maps, or None.

    ``residual`` is the JPEG-resave error; ``gradient`` is local edge energy.
    Their ratio normalises out the fact that text/edges naturally carry high
    resave error, isolating the double-compression signature: a region already
    quantised at a lower quality has high edge energy but anomalously LOW resave
    error, while a fresh paste has error inconsistent with its neighbours.
    """
    try:
        original = Image.open(image_path).convert("RGB")
    except Exception as exc:  # noqa: BLE001
        logger.debug("ELA could not open %s: %s", image_path, exc)
        return None

    buf = io.BytesIO()
    original.save(buf, format="JPEG", quality=_RESAVE_QUALITY)
    buf.seek(0)
    resaved = Image.open(buf).convert("RGB")

    a = np.asarray(original, dtype=np.float32)
    b = np.asarray(resaved, dtype=np.float32)
    if a.shape != b.shape:
        return None
    residual = np.abs(a - b).max(axis=2)          # per-pixel resave error
    gray = a.mean(axis=2)
    gy, gx = np.gradient(gray)
    gradient = np.hypot(gx, gy)                    # per-pixel edge energy

    h, w = residual.shape
    if h < _GRID or w < _GRID:
        return None
    ys = np.linspace(0, h, _GRID + 1, dtype=int)
    xs = np.linspace(0, w, _GRID + 1, dtype=int)
    res_b = np.zeros((_GRID, _GRID), dtype=np.float32)
    grad_b = np.zeros((_GRID, _GRID), dtype=np.float32)
    for by in range(_GRID):
        for bx in range(_GRID):
            r = residual[ys[by]:ys[by + 1], xs[bx]:xs[bx + 1]]
            g = gradient[ys[by]:ys[by + 1], xs[bx]:xs[bx + 1]]
            res_b[by, bx] = float(r.mean()) if r.size else 0.0
            grad_b[by, bx] = float(g.mean()) if g.size else 0.0
    return res_b, grad_b


def run_ela(image_path: str) -> Dict[str, Any]:
    """Score localized recompression/splice anomalies in [0, 1]."""
    result: Dict[str, Any] = {
        "status": "not_available",
        "score": None,
        "detected": None,
        "note": None,
    }

    maps = _block_maps(image_path)
    if maps is None:
        result["note"] = "ELA could not build a reliable block map for this image."
        return result
    res_b, grad_b = maps
    res_f = res_b.reshape(-1)
    grad_f = grad_b.reshape(-1)

    # Only blocks with real content (edges/text) carry a usable compression
    # signature; flat background resave error is uninformative.
    content = grad_f >= np.percentile(grad_f, _CONTENT_PCTL)
    if int(content.sum()) < _MIN_BLOCKS:
        result["status"] = "completed"
        result["score"] = 0.0
        result["detected"] = False
        result["note"] = "Too little textured content for a reliable ELA decision."
        return result

    ratio = res_f[content] / (grad_f[content] + 1e-3)
    median = float(np.median(ratio))
    mad = float(np.median(np.abs(ratio - median))) or 1e-6
    deviations = np.abs(ratio - median) / mad

    anomalous = deviations > 3.0
    anomaly_frac = float(anomalous.mean())

    # Strongest localized deviation, but only credited when the anomaly is a
    # MINORITY of content blocks — a whole-image deviation is normal content
    # variation, not a localized forgery.
    peak = float(np.sort(deviations)[-max(1, int(round(0.05 * deviations.size))):].mean())
    localized = anomaly_frac <= _MAX_ANOMALY_FRAC and anomalous.any()
    score = float(min(1.0, peak / _DEV_SATURATE)) if localized else 0.0

    result["status"] = "completed"
    result["score"] = round(score, 4)
    result["detected"] = score >= _SCORE_THRESHOLD
    result["note"] = (
        f"Block-wise ELA/texture ratio: peak {peak:.1f} MADs over "
        f"{anomaly_frac * 100:.0f}% anomalous content blocks (resave "
        f"q{_RESAVE_QUALITY}, {_GRID}x{_GRID} grid). High values indicate a "
        "locally recompressed or spliced region."
    )
    return result

