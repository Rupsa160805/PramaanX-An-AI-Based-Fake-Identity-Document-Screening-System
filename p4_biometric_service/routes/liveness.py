from __future__ import annotations

from flask import Blueprint, current_app, jsonify, request

liveness_bp = Blueprint("liveness", __name__)


@liveness_bp.post("/api/liveness-check")
def liveness_check():
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(
            {
                "is_live": False,
                "reason": "request body must be a JSON object",
                "frames_used": 0,
                "motion_score": None,
            }
        ), 400
    frame_paths = payload.get("frame_paths", payload.get("frames"))
    video_clip_path = payload.get("video_clip_path")
    if frame_paths is None and video_clip_path is not None:
        if not isinstance(video_clip_path, str) or not video_clip_path.strip():
            return jsonify(
                {
                    "is_live": False,
                    "reason": "video_clip_path must be a non-empty string",
                    "frames_used": 0,
                    "motion_score": None,
                }
            ), 400
        try:
            result = current_app.extensions["p4_liveness"].check_video(
                video_clip_path.strip()
            )
        except (OSError, RuntimeError, TypeError, ValueError) as exc:
            return jsonify(
                {
                    "is_live": False,
                    "reason": str(exc),
                    "frames_used": 0,
                    "motion_score": None,
                }
            ), 422
        except Exception as exc:
            current_app.logger.exception("unexpected video liveness failure")
            return jsonify(
                {
                    "is_live": False,
                    "reason": f"liveness video processing failed: {exc}",
                    "frames_used": 0,
                    "motion_score": None,
                }
            ), 422
        return jsonify(
            {
                "is_live": result.is_live,
                "reason": result.reason,
                "frames_used": result.frames_used,
                "motion_score": result.motion_score,
            }
        )
    if not isinstance(frame_paths, list):
        return jsonify(
            {
                "is_live": False,
                "reason": "request must include a frame_paths array",
                "frames_used": 0,
                "motion_score": None,
            }
        ), 400
    if any(not isinstance(path, str) or not path.strip() for path in frame_paths):
        return jsonify(
            {
                "is_live": False,
                "reason": "every frame path must be a non-empty string",
                "frames_used": 0,
                "motion_score": None,
            }
        ), 400
    try:
        result = current_app.extensions["p4_liveness"].check_paths(frame_paths)
    except (OSError, RuntimeError, TypeError, ValueError) as exc:
        return jsonify(
            {
                "is_live": False,
                "reason": str(exc),
                "frames_used": len(frame_paths),
                "motion_score": None,
            }
        ), 422
    except Exception as exc:
        current_app.logger.exception("unexpected frame liveness failure")
        return jsonify(
            {
                "is_live": False,
                "reason": f"liveness frame processing failed: {exc}",
                "frames_used": len(frame_paths),
                "motion_score": None,
            }
        ), 422
    return jsonify(
        {
            "is_live": result.is_live,
            "reason": result.reason,
            "frames_used": result.frames_used,
            "motion_score": result.motion_score,
        }
    )
