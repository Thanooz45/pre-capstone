"""Participant-grouped evaluation on the canonical training cohort.

Run from the backend directory with:
    .venv/bin/python ../paper/evaluate_grouped.py

The script writes per-image out-of-fold predictions and evaluation metadata to
paper/evaluation_results. Every fold groups by participant ID so images of one
participant cannot appear in both training and test partitions. Use
--exclude-missing-images to record and omit CSV rows whose image files are absent.
"""

import argparse
import csv
import hashlib
import json
import os
import time
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import ElasticNet, Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

PROJECT = Path(__file__).resolve().parents[1]
BACKEND = PROJECT / "backend"
DATASET = PROJECT / "model_specification"
DEFAULT_CSV = DATASET / "height_weight_dataset.csv"
DEFAULT_OUTPUT = PROJECT / "paper" / "evaluation_results"
sys.path.insert(0, str(BACKEND))

from core.config import settings
from services.height_estimator import estimate_height, load_models
from services.weight_estimator import FEATURE_NAMES

REQUIRED_COLUMNS = {
    "person_id",
    "image_path",
    "height_cm",
    "weight_kg",
    "subject_distance_cm",
    "camera_height_cm",
}
ALPHAS = [0.1, 1.0, 10.0, 100.0]
MAX_CV_FOLDS = 5
FEATURE_VERSION = "visual-proportions-v1"


def _normalize_group(value: str) -> str:
    return value.strip().casefold()


def _assert_group_disjoint(train_groups: np.ndarray, test_groups: np.ndarray, context: str) -> None:
    """Fail evaluation if any participant crosses a train/test boundary."""
    overlap = set(train_groups) & set(test_groups)
    if overlap:
        raise ValueError(
            f"Participant leakage in {context}: {len(overlap)} group(s) occur "
            "in both train and test partitions."
        )


def _load_rows(
    csv_path: Path,
    image_dir: Path,
    exclude_missing_images: bool = False,
) -> tuple[list[dict[str, str]], str, int]:
    with csv_path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise ValueError(f"Dataset CSV has no header: {csv_path}")
        headers = [header.strip() for header in reader.fieldnames]
        if len(headers) != len(set(headers)):
            raise ValueError(f"{csv_path} contains duplicate headers after trimming.")
        reader.fieldnames = headers
        missing_columns = REQUIRED_COLUMNS - set(headers)
        if missing_columns:
            raise ValueError(
                f"{csv_path} is missing required columns: "
                f"{', '.join(sorted(missing_columns))}"
            )
        source_rows = list(reader)

    if not source_rows:
        raise ValueError(f"Dataset CSV contains no image records: {csv_path}")

    resolved_image_dir = image_dir.resolve()
    rows = []
    seen_images: set[Path] = set()
    missing_image_count = 0
    for row_number, source_row in enumerate(source_rows, start=2):
        if None in source_row:
            raise ValueError(f"Malformed CSV row {row_number}: too many fields")
        row = {
            key.strip(): value.strip() if value is not None else ""
            for key, value in source_row.items()
            if key is not None
        }

        image_reference = row["image_path"]
        relative_image_path = Path(image_reference)
        if (
            not image_reference
            or relative_image_path.is_absolute()
            or len(relative_image_path.parts) != 2
            or relative_image_path.parts[0] != "images"
        ):
            raise ValueError(
                f"Invalid image reference on CSV row {row_number}: {image_reference!r}"
            )
        image_name = relative_image_path.name
        image_path = (resolved_image_dir / image_name).resolve()
        if not image_path.is_relative_to(resolved_image_dir):
            raise ValueError(f"Image reference escapes the cohort on row {row_number}.")
        if image_path in seen_images:
            raise ValueError(f"Duplicate image reference on CSV row {row_number}.")
        if not image_path.is_file():
            if exclude_missing_images:
                missing_image_count += 1
                continue
            raise FileNotFoundError(
                f"Image listed on CSV row {row_number} does not exist: {image_name}"
            )
        seen_images.add(image_path)

        participant_id = row["person_id"].strip()
        if not participant_id:
            raise ValueError(f"Missing participant ID on CSV row {row_number}.")
        row["_group"] = _normalize_group(participant_id)
        row["Image Name"] = image_name
        row["Height (cm)"] = row["height_cm"]
        row["Weight (kg)"] = row["weight_kg"]
        row["Distance from camera (cm)"] = row["subject_distance_cm"]
        row["Camera height from ground (cm)"] = row["camera_height_cm"]

        for column in (
            "Height (cm)",
            "Weight (kg)",
            "Distance from camera (cm)",
            "Camera height from ground (cm)",
        ):
            if column == "Weight (kg)" and not row[column]:
                continue
            try:
                value = float(row[column])
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Invalid {column} on CSV row {row_number}: {row[column]!r}"
                ) from error
            if not np.isfinite(value) or value <= 0:
                raise ValueError(
                    f"{column} must be a finite positive value on CSV row "
                    f"{row_number}: {row[column]!r}"
                )
        rows.append(row)

    return rows, "person_id", missing_image_count


def _grouped_values(
    targets: np.ndarray, predictions: np.ndarray, groups: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    target_by_group = []
    prediction_by_group = []
    for group in sorted(set(groups)):
        indices = groups == group
        target_by_group.append(float(np.mean(targets[indices])))
        prediction_by_group.append(float(np.mean(predictions[indices])))
    return np.asarray(target_by_group), np.asarray(prediction_by_group)


def _group_median(targets: np.ndarray, groups: np.ndarray) -> float:
    group_targets = [
        float(np.mean(targets[groups == group])) for group in sorted(set(groups))
    ]
    return float(np.median(group_targets))


def _metrics(targets: np.ndarray, predictions: np.ndarray) -> dict[str, float | int]:
    return {
        "n_groups": int(len(targets)),
        "mae": float(mean_absolute_error(targets, predictions)),
        "rmse": float(mean_squared_error(targets, predictions) ** 0.5),
        "r2": float(r2_score(targets, predictions)),
        "bias": float(np.mean(predictions - targets)),
    }


def _report(
    name: str, targets: np.ndarray, predictions: np.ndarray, unit: str
) -> dict[str, float | int]:
    result = _metrics(targets, predictions)
    print(
        f"{name}: n={result['n_groups']}, "
        f"MAE={result['mae']:.2f} {unit}, "
        f"RMSE={result['rmse']:.2f} {unit}, "
        f"R2={result['r2']:.3f}, bias={result['bias']:.2f} {unit}"
    )
    return result


def _new_calibrator(group_count: int) -> GridSearchCV:
    if group_count < 2:
        raise ValueError(
            "Grouped Ridge tuning needs at least two training participant groups."
        )
    return GridSearchCV(
        estimator=make_pipeline(StandardScaler(), Ridge()),
        param_grid={"ridge__alpha": ALPHAS},
        scoring="neg_mean_absolute_error",
        cv=GroupKFold(n_splits=min(MAX_CV_FOLDS, group_count)),
        refit=True,
        n_jobs=1,
    )


def _fit_calibrator(
    features: np.ndarray, targets: np.ndarray, groups: np.ndarray
) -> GridSearchCV:
    calibrator = _new_calibrator(len(set(groups)))
    calibrator.fit(features, targets, groups=groups)
    return calibrator


def _new_weight_candidate(name: str, group_count: int) -> GridSearchCV:
    """Create a grouped-CV weight search that is fitted only on outer train data."""
    if group_count < 2:
        raise ValueError("Grouped weight tuning needs at least two training participants.")
    folds = GroupKFold(n_splits=min(MAX_CV_FOLDS, group_count))
    if name == "ridge_tuned":
        return GridSearchCV(
            estimator=make_pipeline(StandardScaler(), Ridge()),
            param_grid={"ridge__alpha": ALPHAS},
            scoring="neg_mean_absolute_error",
            cv=folds,
            n_jobs=1,
        )
    if name == "elasticnet_tuned":
        return GridSearchCV(
            estimator=make_pipeline(
                StandardScaler(), ElasticNet(max_iter=10000, random_state=0)
            ),
            param_grid={
                "elasticnet__alpha": [0.01, 0.1, 1.0],
                "elasticnet__l1_ratio": [0.1, 0.5, 0.9],
            },
            scoring="neg_mean_absolute_error",
            cv=folds,
            n_jobs=1,
        )
    raise ValueError(f"Unknown grouped weight candidate: {name}")


def _package_version(package: str) -> str | None:
    try:
        return version(package)
    except PackageNotFoundError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--folds", type=int, default=MAX_CV_FOLDS)
    parser.add_argument("--yolo-model", default=None, help="Detector weights to evaluate (default: configured baseline).")
    parser.add_argument("--pose-complexity", type=int, choices=(0, 1, 2), default=None, help="MediaPipe Pose model: 0 lite, 1 full, 2 heavy.")
    parser.add_argument(
        "--pause-between-images",
        type=float,
        default=0.0,
        help="Seconds to yield between image extractions (useful for CPU-heavy candidates).",
    )
    parser.add_argument(
        "--low-priority",
        action="store_true",
        help="Lower this process's scheduling priority where supported.",
    )
    parser.add_argument(
        "--exclude-missing-images",
        action="store_true",
        help="Exclude and report CSV rows whose referenced image is unavailable.",
    )
    args = parser.parse_args()
    if args.folds < 2:
        parser.error("--folds must be at least 2")
    if args.pause_between_images < 0:
        parser.error("--pause-between-images cannot be negative")
    if args.low_priority and hasattr(os, "nice"):
        try:
            os.nice(10)
        except OSError:
            pass

    csv_path = DEFAULT_CSV.resolve()
    image_dir = (DATASET / "images").resolve()
    output_dir = args.output_dir.resolve()
    if args.yolo_model:
        settings.YOLO_MODEL_PATH = args.yolo_model
    if args.pose_complexity is not None:
        settings.MP_MODEL_COMPLEXITY = args.pose_complexity
    rows, grouping_column, missing_image_count = _load_rows(
        csv_path,
        image_dir,
        exclude_missing_images=args.exclude_missing_images,
    )
    groups = np.asarray([row["_group"] for row in rows])
    group_count = len(set(groups))
    if group_count < 4:
        raise ValueError(
            "Nested grouped evaluation requires at least four distinct groups; "
            f"found {group_count}."
        )
    weights = np.asarray(
        [
            float(row["Weight (kg)"]) if row["Weight (kg)"] else np.nan
            for row in rows
        ],
        dtype=float,
    )
    weight_mask = np.isfinite(weights)
    weight_group_count = len(set(groups[weight_mask]))
    if weight_group_count < 5:
        raise ValueError(
            "Nested weight evaluation requires at least five participant groups "
            f"with measured weights; found {weight_group_count}."
        )
    outer_fold_count = min(args.folds, group_count)
    outer_splits = list(
        GroupKFold(n_splits=outer_fold_count).split(
            np.zeros(len(rows)), np.zeros(len(rows)), groups
        )
    )
    for fold_number, (train_indices, _) in enumerate(outer_splits, start=1):
        if len(set(groups[train_indices])) < 3:
            raise ValueError(
                f"Outer fold {fold_number} leaves fewer than three training groups; "
                "nested grouped calibration cannot be performed. Use more groups "
                "or a larger --folds value."
            )

    os.chdir(BACKEND)
    load_models()
    feature_rows = []
    heights = []
    extraction_seconds = []
    extraction_failures = []
    for row_number, row in enumerate(rows, start=1):
        extraction_started = time.perf_counter()
        try:
            result = estimate_height(
                str(image_dir / row["Image Name"]),
                camera_height_cm=float(row["Camera height from ground (cm)"]),
                distance_cm=float(row["Distance from camera (cm)"]),
            )
        except Exception as error:
            extraction_failures.append({"image_name": row["Image Name"], "error": str(error)})
        else:
            extraction_seconds.append(time.perf_counter() - extraction_started)
            feature_row = [
                result["_weight_features"][feature] for feature in FEATURE_NAMES
            ]
            if len(feature_row) != len(FEATURE_NAMES) or not np.isfinite(feature_row).all():
                raise ValueError(
                    f"Invalid or non-finite features extracted for {row['Image Name']}"
                )
            feature_rows.append(feature_row)
            heights.append(float(row["Height (cm)"]))
        if row_number % 10 == 0 or row_number == len(rows):
            print(
                f"Feature extraction: {row_number}/{len(rows)} images; "
                f"failures: {len(extraction_failures)}",
                flush=True,
            )
        if args.pause_between_images and row_number < len(rows):
            time.sleep(args.pause_between_images)

    if extraction_failures:
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "extraction_benchmark.json").write_text(
            json.dumps({
                "detector_model": settings.YOLO_MODEL_PATH,
                "pose_complexity": settings.MP_MODEL_COMPLEXITY,
                "input_images": len(rows),
                "successful_extractions": len(extraction_seconds),
                "failed_extractions": len(extraction_failures),
                "failure_rate": len(extraction_failures) / len(rows),
                "failures": extraction_failures,
            }, indent=2) + "\n",
            encoding="utf-8",
        )
        raise RuntimeError(
            f"Feature extraction failed for {len(extraction_failures)}/{len(rows)} images; "
            f"details saved to {output_dir / 'extraction_benchmark.json'}; no partial MAE reported."
        )

    features = np.asarray(feature_rows, dtype=float)
    heights = np.asarray(heights, dtype=float)
    if features.shape != (len(rows), len(FEATURE_NAMES)):
        raise ValueError(
            f"Expected feature matrix shape {(len(rows), len(FEATURE_NAMES))}, "
            f"got {features.shape}"
        )
    if not (
        np.isfinite(features).all()
        and np.isfinite(heights).all()
    ):
        raise ValueError("Features and height targets must all be finite.")

    height_oof = np.full(len(heights), np.nan)
    weight_oof = np.full(len(weights), np.nan)
    height_median_oof = np.full(len(heights), np.nan)
    weight_median_oof = np.full(len(weights), np.nan)
    weight_candidate_oof = {
        "ridge_tuned": np.full(len(weights), np.nan),
        "elasticnet_tuned": np.full(len(weights), np.nan),
    }
    fold_assignments = np.full(len(rows), -1, dtype=int)
    height_index = FEATURE_NAMES.index("estimated_height_cm")

    for fold_number, (train_indices, test_indices) in enumerate(outer_splits, start=1):
        _assert_group_disjoint(
            groups[train_indices], groups[test_indices], f"outer fold {fold_number}"
        )
        train_groups = groups[train_indices]
        train_height_oof = np.full(len(train_indices), np.nan)
        inner_folds = GroupKFold(
            n_splits=min(MAX_CV_FOLDS, len(set(train_groups)))
        )
        for inner_train, inner_test in inner_folds.split(
            features[train_indices], heights[train_indices], train_groups
        ):
            inner_train_indices = train_indices[inner_train]
            inner_test_indices = train_indices[inner_test]
            _assert_group_disjoint(
                groups[inner_train_indices], groups[inner_test_indices],
                f"inner fold in outer fold {fold_number}",
            )
            if len(set(groups[inner_train_indices])) < 2:
                raise ValueError(
                    f"Inner fold in outer fold {fold_number} leaves fewer than two "
                    "training groups for Ridge tuning."
                )
            calibrator = _fit_calibrator(
                features[inner_train_indices],
                heights[inner_train_indices],
                groups[inner_train_indices],
            )
            train_height_oof[inner_test] = calibrator.predict(
                features[inner_test_indices]
            )

        if not np.isfinite(train_height_oof).all():
            raise RuntimeError(
                f"Height OOF predictions are incomplete in outer fold {fold_number}"
            )

        calibrator = _fit_calibrator(
            features[train_indices], heights[train_indices], train_groups
        )
        height_oof[test_indices] = calibrator.predict(features[test_indices])
        height_median_oof[test_indices] = _group_median(
            heights[train_indices], train_groups
        )
        fold_assignments[test_indices] = fold_number

        train_weight_mask = weight_mask[train_indices]
        test_weight_mask = weight_mask[test_indices]
        train_weight_indices = train_indices[train_weight_mask]
        test_weight_indices = test_indices[test_weight_mask]
        if not len(test_weight_indices):
            continue
        if len(set(groups[train_weight_indices])) < 2:
            raise ValueError(
                f"Outer fold {fold_number} leaves fewer than two weight-labelled "
                "training groups."
            )

        weight_train_features = features[train_weight_indices].copy()
        weight_train_features[:, height_index] = train_height_oof[train_weight_mask]
        weight_test_features = features[test_weight_indices].copy()
        weight_test_features[:, height_index] = height_oof[test_weight_indices]

        regressor = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
        regressor.fit(weight_train_features, weights[train_weight_indices])
        weight_oof[test_weight_indices] = regressor.predict(weight_test_features)

        candidate_groups = groups[train_weight_indices]
        ridge_candidate = _new_weight_candidate(
            "ridge_tuned", len(set(candidate_groups))
        )
        ridge_candidate.fit(
            weight_train_features,
            weights[train_weight_indices],
            groups=candidate_groups,
        )
        weight_candidate_oof["ridge_tuned"][test_weight_indices] = ridge_candidate.predict(
            weight_test_features
        )

        elastic_candidate = _new_weight_candidate(
            "elasticnet_tuned", len(set(candidate_groups))
        )
        elastic_candidate.fit(
            weight_train_features,
            weights[train_weight_indices],
            groups=candidate_groups,
        )
        weight_candidate_oof["elasticnet_tuned"][test_weight_indices] = elastic_candidate.predict(
            weight_test_features
        )
        weight_median_oof[test_weight_indices] = _group_median(
            weights[train_weight_indices], groups[train_weight_indices]
        )

    if not (
        np.isfinite(height_oof).all()
        and np.isfinite(height_median_oof).all()
        and np.isfinite(weight_oof[weight_mask]).all()
        and np.isfinite(weight_median_oof[weight_mask]).all()
        and all(np.isfinite(values[weight_mask]).all() for values in weight_candidate_oof.values())
    ):
        raise RuntimeError(
            "Evaluation did not produce finite predictions for every row."
        )

    height_targets, height_predictions = _grouped_values(heights, height_oof, groups)
    raw_height_targets, raw_height_predictions = _grouped_values(
        heights, features[:, height_index], groups
    )
    height_baseline_targets, height_baseline_predictions = _grouped_values(
        heights, height_median_oof, groups
    )
    weight_targets, weight_predictions = _grouped_values(
        weights[weight_mask], weight_oof[weight_mask], groups[weight_mask]
    )
    weight_baseline_targets, weight_baseline_predictions = _grouped_values(
        weights[weight_mask],
        weight_median_oof[weight_mask],
        groups[weight_mask],
    )

    metrics: dict[str, dict[str, float | int]] = {
        "raw_geometric_height_cm": _report(
            "Raw geometric height", raw_height_targets, raw_height_predictions, "cm"
        ),
        "calibrated_height_cm": _report(
            "Calibrated height (nested grouped OOF)",
            height_targets,
            height_predictions,
            "cm",
        ),
        "training_fold_median_height_cm": _report(
            "Training-fold median height baseline",
            height_baseline_targets,
            height_baseline_predictions,
            "cm",
        ),
        "weight_kg": _report(
            "Weight (nested grouped OOF)", weight_targets, weight_predictions, "kg"
        ),
        "training_fold_median_weight_kg": _report(
            "Training-fold median weight baseline",
            weight_baseline_targets,
            weight_baseline_predictions,
            "kg",
        ),
    }
    for candidate_name, candidate_predictions in weight_candidate_oof.items():
        candidate_targets, grouped_candidate_predictions = _grouped_values(
            weights[weight_mask],
            candidate_predictions[weight_mask],
            groups[weight_mask],
        )
        metrics[f"{candidate_name}_weight_kg"] = _report(
            f"{candidate_name} (nested grouped OOF)",
            candidate_targets,
            grouped_candidate_predictions,
            "kg",
        )
    grouping_description = "normalized participant_id values"
    print(
        f"Images: {len(rows)}; height groups: {group_count}; "
        f"weight labels: {int(weight_mask.sum())} across {weight_group_count} groups; "
        f"groups from {grouping_description}; outer folds: {outer_fold_count}"
    )
    if missing_image_count:
        print(f"Excluded CSV rows with missing images: {missing_image_count}")

    prediction_path = output_dir / "grouped_predictions.csv"
    metadata_path = output_dir / "evaluation_metadata.json"
    output_dir.mkdir(parents=True, exist_ok=True)
    with prediction_path.open("w", encoding="utf-8", newline="") as file:
        fieldnames = [
            "image_name",
            "group_id",
            "outer_fold",
            "height_true_cm",
            "height_raw_geometric_cm",
            "height_oof_cm",
            "height_fold_median_cm",
            "weight_true_kg",
            "weight_oof_kg",
            "weight_fold_median_kg",
            "weight_ridge_tuned_kg",
            "weight_elasticnet_tuned_kg",
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for index, row in enumerate(rows):
            writer.writerow(
                {
                    "image_name": row["Image Name"],
                    "group_id": groups[index],
                    "outer_fold": int(fold_assignments[index]),
                    "height_true_cm": heights[index],
                    "height_raw_geometric_cm": features[index, height_index],
                    "height_oof_cm": height_oof[index],
                    "height_fold_median_cm": height_median_oof[index],
                    "weight_true_kg": weights[index] if weight_mask[index] else "",
                    "weight_oof_kg": weight_oof[index] if weight_mask[index] else "",
                    "weight_fold_median_kg": (
                        weight_median_oof[index] if weight_mask[index] else ""
                    ),
                    "weight_ridge_tuned_kg": (
                        weight_candidate_oof["ridge_tuned"][index]
                        if weight_mask[index] else ""
                    ),
                    "weight_elasticnet_tuned_kg": (
                        weight_candidate_oof["elasticnet_tuned"][index]
                        if weight_mask[index] else ""
                    ),
                }
            )

    metadata: dict[str, Any] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_csv": str(csv_path.relative_to(PROJECT)) if csv_path.is_relative_to(PROJECT) else csv_path.name,
        "dataset_csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "excluded_missing_image_count": missing_image_count,
        "image_count": len(rows),
        "group_count": group_count,
        "weight_label_count": int(weight_mask.sum()),
        "weight_group_count": weight_group_count,
        "vision_candidate": {
            "detector_model": settings.YOLO_MODEL_PATH,
            "ultralytics_version": _package_version("ultralytics"),
            "pose_complexity": settings.MP_MODEL_COMPLEXITY,
            "segmentation_model": "MediaPipe Selfie Segmentation (unchanged)",
            "extraction_images": len(rows),
            "extraction_failures": 0,
            "failure_rate": 0.0,
            "mean_extraction_seconds": float(np.mean(extraction_seconds)),
            "median_extraction_seconds": float(np.median(extraction_seconds)),
            "total_extraction_seconds": float(np.sum(extraction_seconds)),
        },
        "grouping_column": grouping_column,
        "grouping_rule": grouping_description,
        "feature_version": FEATURE_VERSION,
        "random_seed": None,
        "split_method": "GroupKFold (deterministic; participant_id groups)",
        "split_assignments": {
            str(group): int(fold_assignments[np.flatnonzero(groups == group)[0]])
            for group in sorted(set(groups))
        },
        "outer_folds": outer_fold_count,
        "inner_folds_max": MAX_CV_FOLDS,
        "ridge_alpha_candidates": ALPHAS,
        "weight_model": {
            "type": "StandardScaler + Ridge",
            "alpha": 1.0,
        },
        "candidate_weight_models": {
            "ridge_tuned": {
                "type": "StandardScaler + Ridge",
                "alpha_candidates": ALPHAS,
                "tuning": "GroupKFold inside each outer training partition",
            },
            "elasticnet_tuned": {
                "type": "StandardScaler + ElasticNet",
                "alpha_candidates": [0.01, 0.1, 1.0],
                "l1_ratio_candidates": [0.1, 0.5, 0.9],
                "tuning": "GroupKFold inside each outer training partition",
                "random_seed": 0,
            },
        },
        "weight_height_feature": {
            "evaluation": "out-of-fold calibrated height",
            "saved_model_training": "out-of-fold calibrated height",
            "inference": "calibrated height",
        },
        "feature_names": list(FEATURE_NAMES),
        "versions": {
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scikit_learn": version("scikit-learn"),
            "opencv_python": _package_version("opencv-python"),
            "mediapipe": _package_version("mediapipe"),
        },
        "metrics_group_aggregated": metrics,
        "predictions_csv": prediction_path.name,
    }
    metadata_path.write_text(
        json.dumps(metadata, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    print(f"Saved per-image predictions to {prediction_path}")
    print(f"Saved evaluation metadata to {metadata_path}")


if __name__ == "__main__":
    main()
