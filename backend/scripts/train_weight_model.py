"""Train the local visual weight estimator from the supplied labelled images.

Run from backend: python scripts/train_weight_model.py
"""

import csv
import sys
from pathlib import Path

from joblib import dump
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import RidgeCV
from sklearn.metrics import mean_absolute_error
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

BACKEND = Path(__file__).resolve().parents[1]
PROJECT = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from services.height_estimator import estimate_height, load_models
from services.weight_estimator import FEATURE_NAMES

DATASET_1 = PROJECT / "dataset_of_height_weight_updated"
DATASET_2 = PROJECT / "height_weight_dataset_updated"


def main() -> None:
    # Dataset 1
    rows_1 = list(csv.DictReader((DATASET_1 / "Output_data.csv").open(encoding="utf-8-sig")))
    
    # Dataset 2
    rows_2 = list(csv.DictReader((DATASET_2 / "height_weight_dataset.csv").open(encoding="utf-8-sig")))
    
    x, weights, heights, skipped = [], [], [], []
    x_no_height, weights_no_height = [], []
    
    load_models()

    for row in rows_1:
        image_path = DATASET_1 / "images" / row["Image Name"]
        try:
            result = estimate_height(
                str(image_path),
                camera_height_cm=float(row["Camera height from ground (cm)"]),
                distance_cm=float(row["Distance from camera (cm)"]),
            )
            features = result["_weight_features"]
            x.append([features[name] for name in FEATURE_NAMES])
            weights.append(float(row["Weight (kg)"]))
            heights.append(float(row["Height (cm)"]))
            print(f"Included D1: {row['Image Name']}")
        except Exception as exc:
            skipped.append(f"{row['Image Name']}: {exc}")
            print(f"Skipped D1: {skipped[-1]}")

    for row in rows_2:
        for img_col in ["Image 1 Name", "Image 2 Name"]:
            img_name = row.get(img_col)
            if not img_name:
                continue
            image_path = DATASET_2 / "images" / img_name
            if not image_path.exists():
                continue
            try:
                result = estimate_height(
                    str(image_path),
                    camera_height_cm=float(row["Camera Height from Ground (cm)"]),
                    distance_cm=float(row["Distance from Camera (cm)"]),
                )
                features = result["_weight_features"]
                x_no_height.append([features[name] for name in FEATURE_NAMES])
                weights_no_height.append(float(row["Weight (kg)"]))
                print(f"Included D2: {img_name}")
            except Exception as exc:
                skipped.append(f"{img_name}: {exc}")
                print(f"Skipped D2: {skipped[-1]}")

    if len(x) < 10:
        raise RuntimeError(f"Only {len(x)} usable samples; at least 10 are required.")

    # A regularised calibration keeps the physics-based estimate as the main
    # signal while learning the systematic camera/lens bias in this dataset.
    height_model = make_pipeline(StandardScaler(), RidgeCV(alphas=[0.1, 1.0, 10.0, 100.0]))
    folds = KFold(n_splits=5, shuffle=True, random_state=42)
    oof_heights = cross_val_predict(height_model, x, heights, cv=folds)
    height_mae = mean_absolute_error(heights, oof_heights)
    height_model.fit(x, heights)
    dump(height_model, BACKEND / "models" / "height_calibrator.joblib")

    # Weight prediction uses the calibrated height rather than the raw
    # pinhole estimate. OOF values prevent the training metrics from using
    # its own ground-truth height as a hidden shortcut.
    weight_x = [list(row) for row in x]
    height_index = FEATURE_NAMES.index("estimated_height_cm")
    for row, calibrated in zip(weight_x, oof_heights):
        row[height_index] = calibrated
        
    if x_no_height:
        d2_calibrated = height_model.predict(x_no_height)
        for row, calibrated in zip(x_no_height, d2_calibrated):
            r = list(row)
            r[height_index] = calibrated
            weight_x.append(r)
            
    all_weights = weights + weights_no_height

    model = RandomForestRegressor(
        n_estimators=300, min_samples_leaf=2, max_features=0.8, random_state=42
    )
    model.fit(weight_x, all_weights)
    output = BACKEND / "models" / "weight_regressor.joblib"
    output.parent.mkdir(exist_ok=True)
    dump(model, output)
    print(f"\nSaved {output} using {len(weight_x)} samples; skipped {len(skipped)}.")
    print(f"5-fold height calibration MAE: {height_mae:.1f} cm (small-dataset estimate).")
    if skipped:
        print("Review skipped images before relying on the model.")


if __name__ == "__main__":
    main()
