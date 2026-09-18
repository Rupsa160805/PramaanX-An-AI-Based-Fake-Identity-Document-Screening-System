from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

from ..services.face_match import (
    FaceServiceError,
    ImageInputError,
    NoFaceDetectedError,
    ReferenceNotFoundError,
    ReferencePhotoUnavailableError,
)

verify_bp = Blueprint("verify", __name__)


def _base_response(
    *, threshold: float, liveness_passed: bool = True, liveness_performed: bool = False
) -> dict:
    return {
        "found_in_database": False,
        "similarity": None,
        "is_match": False,
        "threshold_used": threshold,
        "liveness_passed": liveness_passed,
        "liveness_performed": liveness_performed,
        "confidence_label": "NOT_AVAILABLE",
        "reason": None,
        "error": None,
    }


@verify_bp.post("/api/verify-face")
def verify_face():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        response = _base_response(
            threshold=current_app.extensions["p4_settings"].face_threshold
        )
        response.update(
            {
                "error": "request body must be a JSON object",
                "reason": "invalid request body",
            }
        )
        return jsonify(response), 400
    live_photo_path = payload.get("live_photo_path")
    document_number = payload.get("document_number")
    settings = current_app.extensions["p4_settings"]
    response = _base_response(threshold=settings.face_threshold)
    if not isinstance(live_photo_path, str) or not live_photo_path.strip():
        response.update(
            {
                "error": "live_photo_path is required",
                "reason": "no live photo path was supplied",
            }
        )
        return jsonify(response), 400
    if not isinstance(document_number, str) or not document_number.strip():
        response.update(
            {
                "error": "document_number is required",
                "reason": "no document number was supplied",
            }
        )
        return jsonify(response), 400

    frame_paths = payload.get("frame_paths")
    video_clip_path = payload.get("video_clip_path")
    if frame_paths is not None and video_clip_path is not None:
        response.update(
            {
                "error": "send either frame_paths or video_clip_path, not both",
                "reason": "ambiguous liveness input",
            }
        )
        return jsonify(response), 400
    if frame_paths is not None or video_clip_path is not None:
        if video_clip_path is not None:
            if not isinstance(video_clip_path, str) or not video_clip_path.strip():
                response.update(
                    {
                        "error": "video_clip_path must be a non-empty string",
                        "reason": "invalid liveness input",
                    }
                )
                return jsonify(response), 400

            def liveness_operation():
                return current_app.extensions["p4_liveness"].check_video(
                    video_clip_path.strip()
                )
        else:
            if not isinstance(frame_paths, list):
                response.update(
                    {
                        "error": "frame_paths must be an array",
                        "reason": "invalid liveness input",
                    }
                )
                return jsonify(response), 400
            if any(
                not isinstance(path, str) or not path.strip() for path in frame_paths
            ):
                response.update(
                    {
                        "error": "frame_paths must contain non-empty strings",
                        "reason": "invalid liveness input",
                    }
                )
                return jsonify(response), 400

            def liveness_operation():
                return current_app.extensions["p4_liveness"].check_paths(frame_paths)

        try:
            liveness_result = liveness_operation()
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            response.update(
                {
                    "liveness_passed": False,
                    "liveness_performed": True,
                    "error": str(exc),
                    "reason": "liveness could not be evaluated",
                }
            )
            return jsonify(response), 422
        except Exception as exc:
            current_app.logger.exception("unexpected verify liveness failure")
            response.update(
                {
                    "liveness_passed": False,
                    "liveness_performed": True,
                    "error": "liveness could not be evaluated",
                    "reason": str(exc),
                }
            )
            return jsonify(response), 422
        response["liveness_passed"] = liveness_result.is_live
        response["liveness_performed"] = True
        if not liveness_result.is_live:
            response.update(
                {"error": "liveness check failed", "reason": liveness_result.reason}
            )
            return jsonify(response), 200

    try:
        result = current_app.extensions["p4_face_matcher"].verify_against_database(
            live_photo_path.strip(), document_number.strip()
        )
    except ReferenceNotFoundError as exc:
        response.update({"error": "document not found in database", "reason": str(exc)})
        return jsonify(response), 200
    except ReferencePhotoUnavailableError as exc:
        response.update(
            {
                "found_in_database": True,
                "error": "reference photo unavailable",
                "reason": str(exc),
            }
        )
        return jsonify(response), 503
    except NoFaceDetectedError as exc:
        response.update(
            {
                "found_in_database": getattr(exc, "found_in_database", False),
                "error": "no face detected",
                "reason": str(exc),
            }
        )
        return jsonify(response), 422
    except ImageInputError as exc:
        response.update(
            {
                "found_in_database": getattr(exc, "found_in_database", False),
                "error": str(exc),
                "reason": "face verification image input was invalid",
            }
        )
        return jsonify(response), 422
    except FaceServiceError as exc:
        response.update(
            {"error": str(exc), "reason": "face verification could not be completed"}
        )
        return jsonify(response), 503
    except (OSError, ValueError) as exc:
        response.update(
            {"error": str(exc), "reason": "face verification input was invalid"}
        )
        return jsonify(response), 422

    match_reason = result.reason
    if not response["liveness_performed"]:
        match_reason += (
            "; liveness not evaluated because no frames or video clip was supplied"
        )
    response.update(
        {
            "found_in_database": True,
            "similarity": round(float(result.similarity), 6),
            "is_match": bool(result.is_match) and response["liveness_passed"],
            "threshold_used": result.threshold_used,
            "confidence_label": result.confidence_label
            if response["liveness_passed"]
            else "LOW",
            "reason": match_reason
            if response["liveness_passed"]
            else "face matched but liveness did not pass",
            "error": None if response["liveness_passed"] else "liveness check failed",
        }
    )
    return jsonify(response)
