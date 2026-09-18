"""Empirically calibrate a face threshold from same/different photo pairs."""

from __future__ import annotations

import argparse
import json
import sys
from itertools import combinations
from pathlib import Path

# Support both `python -m p4_biometric_service.scripts.calibrate_threshold`
# and the documented file-path invocation from the repository root.
if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from p4_biometric_service.services.face_match import FaceMatcher, FaceServiceError


def _pairs(directory: Path) -> list[tuple[Path, Path]]:
    files = sorted(
        item
        for item in directory.iterdir()
        if item.suffix.lower() in {".jpg", ".jpeg", ".png"}
    )
    return list(combinations(files, 2))


def _scored_pairs(
    matcher: FaceMatcher, pairs: list[tuple[Path, Path]]
) -> tuple[list[float], list[dict[str, str]]]:
    """Score usable pairs and report bad samples without aborting calibration."""
    scores: list[float] = []
    skipped: list[dict[str, str]] = []
    for first, second in pairs:
        try:
            scores.append(matcher.compare_paths(first, second).similarity)
        except FaceServiceError as exc:
            skipped.append(
                {"pair": f"{first.name} vs {second.name}", "reason": str(exc)}
            )
            print(
                f"  skipped {first.name} vs {second.name}: {exc}",
                file=sys.stderr,
            )
    return scores, skipped


def _best_threshold(
    same: list[float], different: list[float], baseline: float = 0.45
) -> float:
    # A threshold trained on only one class is not calibration.  In
    # particular, including 0.0 would make a sample with no negative pairs
    # look perfect and could accidentally approve every face.
    if not same or not different:
        return baseline
    candidates = sorted({0.0, 1.0, *same, *different})
    best_accuracy, best_threshold = 0.0, baseline
    for threshold in candidates:
        true_positive = sum(score >= threshold for score in same)
        true_negative = sum(score < threshold for score in different)
        total = len(same) + len(different)
        accuracy = (true_positive + true_negative) / total if total else 0.0
        if accuracy > best_accuracy:
            best_accuracy, best_threshold = accuracy, threshold
    return best_threshold


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--same",
        type=Path,
        required=True,
        help="directory containing same-person photos",
    )
    parser.add_argument(
        "--different",
        type=Path,
        required=True,
        help="directory containing different-person photos",
    )
    parser.add_argument(
        "--baseline-threshold",
        type=float,
        default=0.45,
        help="safe fallback when one class has no scorable pairs (default: 0.45)",
    )
    parser.add_argument("--output", type=Path, default=Path("calibration_results.json"))
    args = parser.parse_args()

    if not 0.0 <= args.baseline_threshold <= 1.0:
        parser.error("--baseline-threshold must be between 0 and 1")
    for label, directory in (("--same", args.same), ("--different", args.different)):
        if not directory.is_dir():
            parser.error(f"{label} must point to an existing directory: {directory}")

    matcher = FaceMatcher(threshold=args.baseline_threshold)
    same_scores, same_skipped = _scored_pairs(matcher, _pairs(args.same))
    different_scores, different_skipped = _scored_pairs(matcher, _pairs(args.different))
    calibration_valid = bool(same_scores and different_scores)
    warning = "Calibration is demo evidence, not a production accuracy or liveness evaluation."
    if not calibration_valid:
        warning += (
            " A calibrated threshold was not selected because both same-person "
            "and different-person scores are required; the baseline threshold was kept."
        )
    result = {
        "threshold": _best_threshold(
            same_scores, different_scores, args.baseline_threshold
        ),
        "baseline_threshold": args.baseline_threshold,
        "calibration_valid": calibration_valid,
        "pair_counts": {
            "same_person_scored": len(same_scores),
            "different_person_scored": len(different_scores),
            "skipped": len(same_skipped) + len(different_skipped),
        },
        "same_person_scores": same_scores,
        "different_person_scores": different_scores,
        "same_min": min(same_scores) if same_scores else None,
        "different_max": max(different_scores) if different_scores else None,
        "skipped_pairs": same_skipped + different_skipped,
        "warning": warning,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
