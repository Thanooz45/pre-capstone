"""Local weight-regression model loading and inference."""

import logging
from pathlib import Path

import joblib
import numpy as np

from core.config import settings

logger = logging.getLogger(__name__)

FEATURE_NAMES = (
    "estimated_height_cm",
    "shoulder_width_ratio",
    "hip_width_ratio",
    "silhouette_fill_ratio",
    "silhouette_aspect_ratio",
    "chest_width_ratio",
    "waist_width_ratio",
    "lower_body_width_ratio",
)

_weight_model = None
_height_model = None


def _model_path() -> Path:
    return Path(__file__).resolve().parents[1] / settings.WEIGHT_MODEL_PATH


def _height_model_path() -> Path:
    return Path(__file__).resolve().parents[1] / "models" / "height_calibrator.joblib"


def load_weight_model() -> bool:
    """Load the trained model if it exists. Returns False until training runs."""
    global _weight_model
    if _weight_model is not None:
        return True
    path = _model_path()
    if not path.exists():
        logger.warning("Weight model not found at %s", path)
        return False
    _weight_model = joblib.load(path)
    logger.info("Weight regression model loaded from %s", path)
    return True


def estimate_weight(features: dict) -> dict:
    """Predict kg from the height and visible body-proportion features."""
    if not load_weight_model():
        raise RuntimeError(
            "The weight model has not been trained. Run scripts/train_weight_model.py first."
        )
    values = np.array([[features[name] for name in FEATURE_NAMES]], dtype=float)
    prediction = float(_weight_model.predict(values)[0])

    # Tree spread gives a useful, conservative visual-only uncertainty range.
    trees = getattr(_weight_model, "estimators_", [])
    if trees:
        tree_predictions = np.array([tree.predict(values)[0] for tree in trees], dtype=float)
        spread = max(4.0, float(np.std(tree_predictions)) * 1.5)
    else:
        spread = 8.0

    return {
        "estimated_weight_kg": round(prediction, 1),
        "estimated_weight_lb": round(prediction * 2.20462, 1),
        "weight_estimate_range_kg": [round(max(0.0, prediction - spread), 1), round(prediction + spread, 1)],
        "weight_model_available": True,
    }


def calibrate_height(features: dict) -> float:
    """Correct the geometric estimate using the labelled camera dataset.

    Geometry remains the primary signal.  This learned calibration compensates
    for the actual phone lens/pitch and landmark bias in the training setup.
    """
    global _height_model
    path = _height_model_path()
    if _height_model is None and path.exists():
        _height_model = joblib.load(path)
        logger.info("Height calibration model loaded from %s", path)
    if _height_model is None:
        return float(features["estimated_height_cm"])
    values = np.array([[features[name] for name in FEATURE_NAMES]], dtype=float)
    return float(_height_model.predict(values)[0])
