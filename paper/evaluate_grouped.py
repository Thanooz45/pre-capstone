"""Participant-grouped evaluation of the height and weight estimators.

Run from the backend directory with:
    .venv/bin/python ../paper/evaluate_grouped.py

The script writes per-image out-of-fold predictions and evaluation metadata to
paper/evaluation_results by default. If the CSV has a participant_id column,
that column is used for grouping; otherwise normalized names are used.
"""

import argparse
import csv
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

PROJECT = Path(__file__).resolve().parents[1]
BACKEND = PROJECT / "backend"
DATASET = PROJECT / "dataset_of_height_weight_updated"
DEFAULT_CSV = DATASET / "Output_data.csv"
DEFAULT_OUTPUT = PROJECT / "paper" / "evaluation_results"
sys.path.insert(0, str(BACKEND))

from services.height_estimator import estimate_height, load_models
from services.weight_estimator import FEATURE_NAMES

REQUIRED_COLUMNS = {
    "Image Name",
    "Height (cm)",
    "Weight (kg)",
    "Distance from camera (cm)",
    "Camera height from ground (cm)",
}
ALPHAS = [0.1, 1.0, 10.0, 100.0]
MAX_CV_FOLDS = 5


def _normalize_group(value: str) -> str:
    return value.strip().casefold()


def _load_rows(csv_path: Path, image_dir: Path) -> tuple[list[dict[str, str]], str]:
    with csv_path.open(encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        if reader.fieldnames is None:
            raise ValueError(f"Dataset CSV has no header: {csv_path}")
        missing_columns = REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing_columns:
            raise ValueError(
                f"{csv_path} is missing required columns: "
                f"{', '.join(sorted(missing_columns))}"
            )
        grouping_column = (
            "participant_id"
            if "participant_id" in reader.fieldnames
            else "Name"
        )
        if grouping_column not in reader.fieldnames:
            raise ValueError(
                f"{csv_path} must contain either participant_id or Name for grouping"
            )
        rows = list(reader)

    if not rows:
        raise ValueError(f"Dataset CSV contains no image records: {csv_path}")

    resolved_image_dir = image_dir.resolve()
    seen_images: set[Path] = set()
    for row_number, row in enumerate(rows, start=2):
        if None in row:
            raise ValueError(f"Malformed CSV row {row_number}: too many fields")

        image_name = (row.get("Image Name") or "").strip()
        if not image_name:
            raise ValueError(f"Missing image name on CSV row {row_number}")
        row["Image Name"] = image_name
        image_path = (resolved_image_dir / image_name).resolve()
        if not image_path.is_relative_to(resolved_image_dir):
            raise ValueError(
                f"Image path must be inside {resolved_image_dir}: {image_name}"
            )
        if image_path in seen_images:
            raise ValueError(
                f"Duplicate image path on CSV row {row_number}: {image_name}"
            )
        if not image_path.is_file():
            raise FileNotFoundError(
                f"Image listed on CSV row {row_number} does not exist: {image_path}"
            )
        seen_images.add(image_path)

        group_value = (row.get(grouping_column) or "").strip()
        if not group_value:
            raise ValueError(
                f"Missing {grouping_column} on CSV row {row_number} ({image_name})"
            )
        row["_group"] = _normalize_group(group_value)

        for column in (
            "Height (cm)",
            "Weight (kg)",
            "Distance from camera (cm)",
            "Camera height from ground (cm)",
        ):
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

    return rows, grouping_column


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


def _package_version(package: str) -> str | None:
    try:
        return version(package)
    except PackageNotFoundError:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--images", type=Path, default=DATASET / "images")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--folds", type=int, default=MAX_CV_FOLDS)
    args = parser.parse_args()
    if args.folds < 2:
        parser.error("--folds must be at least 2")

    csv_path = args.csv.resolve()
    image_dir = args.images.resolve()
    output_dir = args.output_dir.resolve()
    rows, grouping_column = _load_rows(csv_path, image_dir)
    groups = np.asarray([row["_group"] for row in rows])
    group_count = len(set(groups))
    if group_count < 4:
        raise ValueError(
            "Nested grouped evaluation requires at least four distinct groups; "
            f"found {group_count}."
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
    weights = []
    for row in rows:
        result = estimate_height(
            str(image_dir / row["Image Name"]),
            camera_height_cm=float(row["Camera height from ground (cm)"]),
            distance_cm=float(row["Distance from camera (cm)"]),
        )
        feature_row = [
            result["_weight_features"][feature] for feature in FEATURE_NAMES
        ]
        if len(feature_row) != len(FEATURE_NAMES) or not np.isfinite(feature_row).all():
            raise ValueError(
                f"Invalid or non-finite features extracted for {row['Image Name']}"
            )
        feature_rows.append(feature_row)
        heights.append(float(row["Height (cm)"]))
        weights.append(float(row["Weight (kg)"]))

    features = np.asarray(feature_rows, dtype=float)
    heights = np.asarray(heights, dtype=float)
    weights = np.asarray(weights, dtype=float)
    if features.shape != (len(rows), len(FEATURE_NAMES)):
        raise ValueError(
            f"Expected feature matrix shape {(len(rows), len(FEATURE_NAMES))}, "
            f"got {features.shape}"
        )
    if not (
        np.isfinite(features).all()
        and np.isfinite(heights).all()
        and np.isfinite(weights).all()
    ):
        raise ValueError("Features and target values must all be finite.")

    height_oof = np.full(len(heights), np.nan)
    weight_oof = np.full(len(weights), np.nan)
    height_median_oof = np.full(len(heights), np.nan)
    weight_median_oof = np.full(len(weights), np.nan)
    fold_assignments = np.full(len(rows), -1, dtype=int)
    height_index = FEATURE_NAMES.index("estimated_height_cm")

    for fold_number, (train_indices, test_indices) in enumerate(outer_splits, start=1):
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

        weight_train_features = features[train_indices].copy()
        weight_test_features = features[test_indices].copy()
        weight_train_features[:, height_index] = train_height_oof
        weight_test_features[:, height_index] = height_oof[test_indices]

        regressor = RandomForestRegressor(
            n_estimators=300,
            min_samples_leaf=2,
            max_features=0.8,
            random_state=42,
        )
        regressor.fit(weight_train_features, weights[train_indices])
        weight_oof[test_indices] = regressor.predict(weight_test_features)
        weight_median_oof[test_indices] = _group_median(
            weights[train_indices], train_groups
        )
        fold_assignments[test_indices] = fold_number

    oof_arrays = (
        height_oof,
        weight_oof,
        height_median_oof,
        weight_median_oof,
    )
    if any(not np.isfinite(values).all() for values in oof_arrays):
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
    weight_targets, weight_predictions = _grouped_values(weights, weight_oof, groups)
    weight_baseline_targets, weight_baseline_predictions = _grouped_values(
        weights, weight_median_oof, groups
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
    grouping_description = (
        "normalized participant_id values"
        if grouping_column == "participant_id"
        else "normalized Name values (identity not independently verified)"
    )
    print(
        f"Images: {len(rows)}; unique groups: {group_count}; "
        f"groups from {grouping_description}; outer folds: {outer_fold_count}"
    )

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
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)
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
                    "weight_true_kg": weights[index],
                    "weight_oof_kg": weight_oof[index],
                    "weight_fold_median_kg": weight_median_oof[index],
                }
            )

    metadata: dict[str, Any] = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "dataset_csv": str(csv_path),
        "dataset_csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "image_count": len(rows),
        "group_count": group_count,
        "grouping_column": grouping_column,
        "grouping_rule": grouping_description,
        "outer_folds": outer_fold_count,
        "inner_folds_max": MAX_CV_FOLDS,
        "ridge_alpha_candidates": ALPHAS,
        "random_forest": {
            "n_estimators": 300,
            "min_samples_leaf": 2,
            "max_features": 0.8,
            "random_state": 42,
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
