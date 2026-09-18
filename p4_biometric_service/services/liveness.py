"""Lightweight motion-based liveness check for the hackathon MVP."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np


@dataclass(frozen=True)
class LivenessResult:
    is_live: bool
    reason: str
    frames_used: int
    motion_score: float | None


class LivenessChecker:
    def __init__(self, *, min_frames: int = 2, motion_threshold: float = 2.0):
        if min_frames < 2:
            raise ValueError("min_frames must be at least 2")
        if motion_threshold < 0:
            raise ValueError("motion_threshold must be non-negative")
        self.min_frames = min_frames
        self.motion_threshold = motion_threshold

    @staticmethod
    def _read_frame(path: str | Path) -> Any:
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError("OpenCV is required for liveness checks") from exc
        frame = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
        if frame is None:
            raise ValueError(f"could not read liveness frame: {path}")
        return frame

    @staticmethod
    def _motion_score(first: Any, second: Any) -> float:
        try:
            import cv2

            if first.shape != second.shape:
                second = cv2.resize(second, (first.shape[1], first.shape[0]))
        except ImportError:
            if first.shape != second.shape:
                raise ValueError(
                    "liveness frames must have the same shape when OpenCV is unavailable"
                )
        return float(
            np.mean(np.abs(first.astype(np.float32) - second.astype(np.float32)))
        )

    def check_frames(self, frames: Iterable[Any]) -> LivenessResult:
        frame_list = list(frames)
        if len(frame_list) < self.min_frames:
            return LivenessResult(
                False,
                f"at least {self.min_frames} frames are required for motion-based liveness",
                len(frame_list),
                None,
            )
        scores = [
            self._motion_score(first, second)
            for first, second in zip(frame_list, frame_list[1:])
        ]
        score = float(np.mean(scores)) if scores else 0.0
        if score < self.motion_threshold:
            return LivenessResult(
                False,
                "frames are effectively static; a photo or replay cannot be ruled out",
                len(frame_list),
                score,
            )
        return LivenessResult(
            True,
            "motion detected across frames; this basic check is not production-grade anti-spoofing",
            len(frame_list),
            score,
        )

    def check_paths(self, frame_paths: Iterable[str | Path]) -> LivenessResult:
        try:
            paths = [Path(item) for item in frame_paths]
        except TypeError as exc:
            raise ValueError("frame_paths must contain path-like values") from exc
        frames = [self._read_frame(path) for path in paths]
        return self.check_frames(frames)

    def check_video(self, video_path: str | Path) -> LivenessResult:
        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError("OpenCV is required for video liveness checks") from exc
        capture = cv2.VideoCapture(str(video_path))
        if not capture.isOpened():
            capture.release()
            raise ValueError(f"could not open liveness video: {video_path}")
        sampled: list[Any] = []
        index = 0
        try:
            while len(sampled) < 30:
                ok, frame = capture.read()
                if not ok or frame is None:
                    break
                if index < self.min_frames or index % 3 == 0:
                    sampled.append(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
                index += 1
        finally:
            capture.release()
        return self.check_frames(sampled)
