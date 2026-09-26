"""Face matching adapter for P3's implementation and InsightFace fallback."""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np


class FaceServiceError(RuntimeError):
    """Base class for expected biometric-service failures."""

    def __init__(self, message: str, *, found_in_database: bool = False):
        super().__init__(message)
        # Keep database state alongside the failure.  A live image can fail
        # after the document has already been found, and that distinction is
        # important to callers deciding whether to retry capture or search
        # for another record.
        self.found_in_database = found_in_database


class NoFaceDetectedError(FaceServiceError):
    pass


class ReferenceNotFoundError(FaceServiceError):
    pass


class ReferencePhotoUnavailableError(FaceServiceError):
    pass


class ImageInputError(FaceServiceError):
    pass


class ModelUnavailableError(FaceServiceError):
    pass


class InvalidSimilarityError(FaceServiceError):
    pass


@dataclass(frozen=True)
class FaceMatchResult:
    similarity: float
    is_match: bool
    threshold_used: float
    confidence_label: str
    reason: str


def _normalise_document_number(value: str) -> str:
    return str(value).strip().upper()


def _resolve_path(path_value: Any, base_dir: Path | None = None) -> Path | None:
    if not path_value:
        return None
    path = Path(str(path_value))
    return base_dir / path if not path.is_absolute() and base_dir is not None else path


class FaceMatcher:
    """Reusable matcher with dependency injection for deterministic tests."""

    def __init__(
        self,
        *,
        threshold: float = 0.45,
        database_lookup: Callable[[str], dict[str, Any] | None] | None = None,
        p3_module: str | None = None,
        model_name: str = "buffalo_l",
        det_size: int = 640,
        providers: tuple[str, ...] = ("CPUExecutionProvider",),
        embedding_model: Any | None = None,
        image_loader: Callable[[str | Path], Any] | None = None,
    ):
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("face threshold must be between 0 and 1")
        self.threshold = threshold
        self.database_lookup = database_lookup
        self.p3_module_name = p3_module or os.getenv("P4_P3_FACE_MODULE")
        self.model_name = model_name
        self.det_size = det_size
        self.providers = providers
        self._embedding_model = embedding_model
        self._image_loader = image_loader
        self._p3_module: Any | None = None
        self._p3_checked = False

    def _load_p3_module(self) -> Any | None:
        if self._p3_checked:
            return self._p3_module
        self._p3_checked = True
        candidates = [self.p3_module_name] if self.p3_module_name else []
        candidates.extend(["face_match", "p3.face_match"])
        for name in candidates:
            if not name:
                continue
            try:
                module = importlib.import_module(name)
            except (ImportError, ModuleNotFoundError):
                continue
            if getattr(module, "__file__", None) == __file__:
                continue
            self._p3_module = module
            return module
        return None

    def _load_database_record(self, document_number: str) -> dict[str, Any] | None:
        if self.database_lookup is None:
            raise ReferenceNotFoundError("reference database is not configured")
        try:
            return self.database_lookup(_normalise_document_number(document_number))
        except FaceServiceError:
            raise
        except Exception as exc:
            raise FaceServiceError(f"reference database lookup failed: {exc}") from exc

    def _p3_verify(
        self, live_photo_path: str | Path, document_number: str
    ) -> FaceMatchResult | None:
        module = self._load_p3_module()
        function = getattr(module, "verify_against_database", None) if module else None
        if not callable(function):
            return None
        try:
            raw = function(
                str(live_photo_path), _normalise_document_number(document_number)
            )
        except TypeError:
            raw = function(
                live_photo_path=str(live_photo_path),
                document_number=_normalise_document_number(document_number),
            )
        if isinstance(raw, FaceMatchResult):
            return self._result(raw.similarity)
        if isinstance(raw, (int, float, np.floating)):
            return self._result(float(raw))
        if isinstance(raw, (tuple, list)) and len(raw) == 2:
            return self._result(float(raw[0]))
        if not isinstance(raw, dict):
            raise FaceServiceError(
                "P3 face_match.verify_against_database returned an unsupported result"
            )
        if raw.get("found_in_database") is False:
            raise ReferenceNotFoundError(
                "document was not found in the reference database"
            )
        if raw.get("error"):
            error = str(raw["error"])
            lowered = error.lower()
            if "no face" in lowered or (
                "face" in lowered and ("detect" in lowered or "found" in lowered)
            ):
                raise NoFaceDetectedError(error)
            if "document" in lowered and "not found" in lowered:
                raise ReferenceNotFoundError(error)
            raise FaceServiceError(error)
        similarity = raw.get("similarity", raw.get("score"))
        if similarity is None:
            raise InvalidSimilarityError(
                "P3 face matcher did not return a similarity score"
            )
        return self._result(float(similarity))

    def _load_model(self) -> Any:
        if self._embedding_model is not None:
            return self._embedding_model
        try:
            from insightface.app import FaceAnalysis
        except ImportError as exc:
            raise ModelUnavailableError(
                "InsightFace is not installed and P3's face_match adapter is unavailable"
            ) from exc
        try:
            model = FaceAnalysis(name=self.model_name, providers=list(self.providers))
            model.prepare(ctx_id=0, det_size=(self.det_size, self.det_size))
        except Exception as exc:
            raise ModelUnavailableError(
                f"InsightFace model unavailable: {exc}"
            ) from exc
        self._embedding_model = model
        return model

    def _read_image(self, path: str | Path) -> Any:
        if self._image_loader is not None:
            return self._image_loader(path)
        try:
            import cv2
        except ImportError as exc:
            raise ModelUnavailableError(
                "OpenCV is required to read face images"
            ) from exc
        image = cv2.imread(str(path))
        if image is None:
            raise ImageInputError(f"could not read image: {path}")
        return image

    def _embedding(self, path: str | Path) -> np.ndarray:
        image = self._read_image(path)
        try:
            faces = self._load_model().get(image)
        except FaceServiceError:
            raise
        except Exception as exc:
            raise FaceServiceError(f"face detection failed: {exc}") from exc
        if not faces:
            raise NoFaceDetectedError(f"no face detected in {path}")
        face = max(
            faces,
            key=lambda item: float(
                (item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1])
            ),
        )
        embedding = getattr(face, "embedding", None)
        if embedding is None:
            raise FaceServiceError("InsightFace did not return a face embedding")
        vector = np.asarray(embedding, dtype=np.float32).reshape(-1)
        norm = float(np.linalg.norm(vector))
        if norm == 0.0:
            raise FaceServiceError("face embedding has zero magnitude")
        return vector / norm

    def compare_paths(
        self,
        live_photo_path: str | Path,
        reference_photo_path: str | Path,
        *,
        found_in_database: bool = False,
    ) -> FaceMatchResult:
        try:
            live = self._embedding(live_photo_path)
        except (NoFaceDetectedError, ImageInputError) as exc:
            exc.found_in_database = found_in_database
            raise
        try:
            reference = self._embedding(reference_photo_path)
        except (NoFaceDetectedError, ImageInputError) as exc:
            raise ReferencePhotoUnavailableError(
                f"reference face could not be used: {exc}",
                found_in_database=found_in_database,
            ) from exc
        cosine = float(np.dot(live, reference))
        # InsightFace thresholds are calibrated on cosine similarity itself.
        # Keep that scale (rather than shifting it), while clipping the
        # mathematically possible negative tail to satisfy the public 0–1 API.
        similarity = float(np.clip(cosine, 0.0, 1.0))
        try:
            return self._result(similarity)
        except ValueError as exc:
            raise FaceServiceError(
                f"face embeddings could not be compared: {exc}"
            ) from exc

    def _result(
        self, similarity: float, is_match: bool | None = None
    ) -> FaceMatchResult:
        if not np.isfinite(similarity) or not 0.0 <= similarity <= 1.0:
            raise InvalidSimilarityError("face similarity must be between 0 and 1")
        matched = similarity >= self.threshold if is_match is None else bool(is_match)
        if matched and similarity >= min(1.0, self.threshold + 0.15):
            label = "HIGH"
        elif matched:
            label = "MEDIUM"
        else:
            label = "LOW"
        reason = (
            f"similarity {similarity:.3f} is at or above calibrated threshold {self.threshold:.3f}"
            if matched
            else f"similarity {similarity:.3f} is below calibrated threshold {self.threshold:.3f}"
        )
        return FaceMatchResult(similarity, matched, self.threshold, label, reason)

    def verify_against_database(
        self, live_photo_path: str | Path, document_number: str
    ) -> FaceMatchResult:
        p3_result = self._p3_verify(live_photo_path, document_number)
        if p3_result is not None:
            return p3_result
        record = self._load_database_record(document_number)
        if not record:
            raise ReferenceNotFoundError(
                f"document number {_normalise_document_number(document_number)} was not found in the reference database"
            )
        reference_path = (
            record.get("photo_path")
            or record.get("reference_photo_path")
            or record.get("photo")
        )
        resolved = _resolve_path(reference_path)
        if resolved is None or not resolved.exists():
            raise ReferencePhotoUnavailableError(
                "reference photo is missing for this database record",
                found_in_database=True,
            )
        return self.compare_paths(live_photo_path, resolved, found_in_database=True)


def make_database_lookup(
    json_path: str | Path, p3_database_module: str | None = None
) -> Callable[[str], dict[str, Any] | None]:
    """Prefer P3's database module, falling back to the local JSON adapter."""
    candidates = [p3_database_module] if p3_database_module else []
    candidates.extend(["database", "p3.database"])
    for name in candidates:
        if not name:
            continue
        try:
            module = importlib.import_module(name)
        except (ImportError, ModuleNotFoundError):
            continue
        function = getattr(module, "lookup_by_document_number", None)
        if not callable(function):
            continue

        def lookup(
            document_number: str, function: Callable[..., Any] = function
        ) -> dict[str, Any] | None:
            try:
                return function(document_number)
            except TypeError:
                return function(document_number=document_number)

        return lookup
    from .database import ReferenceDatabase

    database = ReferenceDatabase(json_path)
    database_root = Path(json_path).resolve().parent

    def lookup(document_number: str) -> dict[str, Any] | None:
        record = database.lookup_by_document_number(document_number)
        if not record:
            return None
        # Demo JSON stores paths relative to its own directory.  Resolve only
        # this local adapter's paths; P3 records are passed through unchanged.
        result = dict(record)
        photo_key = next(
            (
                key
                for key in ("photo_path", "reference_photo_path", "photo")
                if result.get(key)
            ),
            None,
        )
        if photo_key:
            photo_path = Path(str(result[photo_key]))
            if not photo_path.is_absolute():
                candidates = [
                    database_root / photo_path,
                    database_root.parent / photo_path,
                ]
                existing = next(
                    (candidate for candidate in candidates if candidate.exists()),
                    candidates[0],
                )
                result[photo_key] = str(existing.resolve())
        return result

    return lookup
