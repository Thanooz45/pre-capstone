"""Train and evaluate the local height and weight models.

Run from the backend directory: python -m scripts.train_weight_model
Training images and labels are read from ../model_specification.
Use --model-output-dir to save candidates without replacing backend/models.
"""

import argparse
import csv
import sys
from pathlib import Path

import numpy as np
from joblib import dump
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import GridSearchCV, GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

BACKEND = Path(__file__).resolve().parents[1]
PROJECT = BACKEND.parent
DATASET = PROJECT / "model_specification"
DATASET_CSV = DATASET / "height_weight_dataset.csv"
sys.path.insert(0, str(BACKEND))

from services.height_estimator import estimate_height, load_models
from services.weight_estimator import FEATURE_NAMES

REQUIRED_COLUMNS = {
    "person_id",
    "image_path",
    "subject_distance_cm",
    "camera_height_cm",
    "height_cm",
    "weight_kg",
}


def _new_height_model(group_count: int) -> GridSearchCV:
    if group_count < 2:
        raise ValueError("Grouped height-model tuning requires two person groups.")
    return GridSearchCV(
        estimator=make_pipeline(StandardScaler(), Ridge()),
        param_grid={"ridge__alpha": [0.1, 1.0, 10.0, 100.0]},
        scoring="neg_mean_absolute_error",
        cv=GroupKFold(n_splits=min(5, group_count)),
        refit=True,
        n_jobs=1,
    )


def _fit_height_model(features, heights, groups):
    model = _new_height_model(len(set(groups)))
    model.fit(features, heights, groups=groups)
    return model


def _grouped_height_oof(features, heights, groups):
    features = np.asarray(features, dtype=float)
    heights = np.asarray(heights, dtype=float)
    groups = np.asarray(groups)
    group_count = len(set(groups))
    if group_count < 3:
        raise ValueError(
            "Grouped out-of-fold height predictions require at least three groups."
        )

    predictions = np.full(len(heights), np.nan)
    folds = GroupKFold(n_splits=min(5, group_count))
    for train_indices, test_indices in folds.split(features, heights, groups):
        model = _fit_height_model(
            features[train_indices],
            heights[train_indices],
            groups[train_indices],
        )
        predictions[test_indices] = model.predict(features[test_indices])

    if not np.isfinite(predictions).all():
        raise RuntimeError("Grouped height cross-validation left missing predictions.")
    return predictions


def _new_weight_model():
    return RandomForestRegressor(
        n_estimators=300,
        min_samples_leaf=2,
        max_features=0.8,
        random_state=42,
    )


def _grouped_targets_predictions(targets, predictions, groups):
    unique_groups = sorted(set(groups))
    grouped_targets = np.asarray(
        [np.mean(targets[groups == group]) for group in unique_groups],
        dtype=float,
    )
    grouped_predictions = np.asarray(
        [np.mean(predictions[groups == group]) for group in unique_groups],
        dtype=float,
    )
    return grouped_targets, grouped_predictions


def _group_median(targets, groups):
    group_targets = [
        float(np.mean(targets[groups == group])) for group in sorted(set(groups))
    ]
    return float(np.median(group_targets))


def _evaluate_by_person(features, heights, weights, groups):
    """Evaluate with nested splits and equal weight for each held-out person."""
    person_count = len(set(groups))
    if person_count < 5:
        raise RuntimeError(
            f"Only {person_count} distinct people have usable images; "
            "at least 5 are required for grouped evaluation."
        )

    features = np.asarray(features, dtype=float)
    heights = np.asarray(heights, dtype=float)
    weights = np.asarray(weights, dtype=float)
    groups = np.asarray(groups)
    height_index = FEATURE_NAMES.index("estimated_height_cm")
    height_predictions = np.empty(len(features), dtype=float)
    weight_predictions = np.empty(len(features), dtype=float)
    height_baseline_predictions = np.empty(len(features), dtype=float)
    weight_baseline_predictions = np.empty(len(features), dtype=float)
    outer_folds = GroupKFold(n_splits=min(5, person_count))

    for train_indices, test_indices in outer_folds.split(features, heights, groups):
        train_groups = groups[train_indices]
        inner_height_predictions = _grouped_height_oof(
            features[train_indices],
            heights[train_indices],
            train_groups,
        )

        height_model = _fit_height_model(
            features[train_indices], heights[train_indices], train_groups
        )
        held_out_heights = height_model.predict(features[test_indices])
        height_predictions[test_indices] = held_out_heights
        height_baseline_predictions[test_indices] = _group_median(
            heights[train_indices], train_groups
        )

        weight_train_features = features[train_indices].copy()
        weight_train_features[:, height_index] = inner_height_predictions
        weight_test_features = features[test_indices].copy()
        weight_test_features[:, height_index] = held_out_heights
        weight_model = _new_weight_model()
        weight_model.fit(weight_train_features, weights[train_indices])
        weight_predictions[test_indices] = weight_model.predict(weight_test_features)
        weight_baseline_predictions[test_indices] = _group_median(
            weights[train_indices], train_groups
        )

    grouped_heights, grouped_height_predictions = _grouped_targets_predictions(
        heights, height_predictions, groups
    )
    grouped_weights, grouped_weight_predictions = _grouped_targets_predictions(
        weights, weight_predictions, groups
    )
    grouped_height_baseline = _grouped_targets_predictions(
        heights, height_baseline_predictions, groups
    )[1]
    grouped_weight_baseline = _grouped_targets_predictions(
        weights, weight_baseline_predictions, groups
    )[1]
    return {
        "height_mae_cm": mean_absolute_error(
            grouped_heights, grouped_height_predictions
        ),
        "height_median_baseline_mae_cm": mean_absolute_error(
            grouped_heights, grouped_height_baseline
        ),
        "weight_mae_kg": mean_absolute_error(
            grouped_weights, grouped_weight_predictions
        ),
        "weight_median_baseline_mae_kg": mean_absolute_error(
            grouped_weights, grouped_weight_baseline
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model-output-dir",
        type=Path,
        default=BACKEND / "models",
        help="Directory for trained artifacts (defaults to backend/models).",
    )
    args = parser.parse_args()

    if not DATASET_CSV.is_file():
        raise FileNotFoundError(f"Training CSV not found: {DATASET_CSV}")

    with DATASET_CSV.open(newline="", encoding="utf-8-sig") as dataset_file:
        reader = csv.DictReader(dataset_file)
        normalized_headers = [
            header.strip() for header in reader.fieldnames or []
        ]
        if len(normalized_headers) != len(set(normalized_headers)):
            raise ValueError(f"{DATASET_CSV} contains duplicate headers after trimming.")
        reader.fieldnames = normalized_headers
        missing_columns = REQUIRED_COLUMNS - set(normalized_headers)
        if missing_columns:
            raise ValueError(
                f"{DATASET_CSV} is missing required columns: "
                f"{', '.join(sorted(missing_columns))}"
            )
        rows = [
            {
                key.strip(): value.strip() if value is not None else ""
                for key, value in row.items()
                if key is not None
            }
            for row in reader
        ]

    if not rows:
        raise ValueError(f"Training CSV contains no image records: {DATASET_CSV}")

    features, heights, weights, groups = [], [], [], []
    for row in rows:
        image_path = (DATASET / row["image_path"]).resolve()
        if not image_path.is_relative_to(DATASET.resolve()):
            raise ValueError(f"Image path must be inside {DATASET}: {row['image_path']}")
        if not image_path.is_file():
            raise FileNotFoundError(f"Image listed in the CSV does not exist: {image_path}")

        camera_height = float(row["camera_height_cm"])
        distance = float(row["subject_distance_cm"])
        height = float(row["height_cm"])
        weight = float(row["weight_kg"])
        if camera_height <= 0 or distance <= 0 or height <= 0 or weight <= 0:
            raise ValueError(f"Measurements must be positive for image {row['image_path']}")

    load_models()
    for row in rows:
        image_path = DATASET / row["image_path"]
        result = estimate_height(
            str(image_path),
            camera_height_cm=float(row["camera_height_cm"]),
            distance_cm=float(row["subject_distance_cm"]),
        )
        image_features = result["_weight_features"]
        feature_row = [image_features[name] for name in FEATURE_NAMES]
        if not np.isfinite(feature_row).all():
            raise ValueError(f"Non-finite image features extracted from {image_path}")
        features.append(feature_row)
        heights.append(float(row["height_cm"]))
        weights.append(float(row["weight_kg"]))
        groups.append(row["person_id"])
        print(f"Processed {row['image_path']}")

    if len(set(groups)) < 5:
        raise RuntimeError(
            f"Only {len(set(groups))} distinct people are represented; "
            "at least 5 are required for grouped training."
        )

    evaluation = _evaluate_by_person(
        features,
        heights,
        weights,
        groups,
    )

    feature_array = np.asarray(features, dtype=float)
    height_array = np.asarray(heights, dtype=float)
    group_array = np.asarray(groups)
    out_of_fold_heights = _grouped_height_oof(
        feature_array, height_array, group_array
    )

    height_model = _fit_height_model(feature_array, height_array, group_array)

    weight_features = feature_array.copy()
    height_index = FEATURE_NAMES.index("estimated_height_cm")
    weight_features[:, height_index] = out_of_fold_heights
    weight_model = _new_weight_model()
    weight_model.fit(weight_features, weights)

    model_directory = args.model_output_dir.resolve()
    model_directory.mkdir(parents=True, exist_ok=True)
    dump(height_model, model_directory / "height_calibrator.joblib")
    dump(weight_model, model_directory / "weight_regressor.joblib")

    print(f"\nTrained on {len(features)} images from {len(set(groups))} people.")
    print(
        "Camera heights represented: "
        f"{min(float(row['camera_height_cm']) for row in rows):g}–"
        f"{max(float(row['camera_height_cm']) for row in rows):g} cm."
    )
    print(
        "Participant-averaged nested grouped height MAE: "
        f"{evaluation['height_mae_cm']:.2f} cm "
        f"(median baseline: "
        f"{evaluation['height_median_baseline_mae_cm']:.2f} cm)."
    )
    print(
        "Participant-averaged nested grouped weight MAE: "
        f"{evaluation['weight_mae_kg']:.2f} kg "
        f"(median baseline: "
        f"{evaluation['weight_median_baseline_mae_kg']:.2f} kg)."
    )
    print(f"Saved height and weight models to {model_directory}.")


if __name__ == "__main__":
    main()
