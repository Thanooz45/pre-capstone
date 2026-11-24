import unittest

import numpy as np

from api.routes import _derived_anthropometry, _quality_signal
from services.height_estimator import _mask_band_span_ratio


def measurement(value, y=0.4, valid=True):
    return {
        "value": value,
        "unit": "ratio",
        "valid": valid,
        "relative_height_over_pixel_height": y,
    }


class AnthropometryProxyTests(unittest.TestCase):
    def test_mask_band_span_uses_median_width_and_pixel_height(self):
        mask = np.zeros((9, 12), dtype=bool)
        mask[3, 2:8] = True
        mask[4, 1:9] = True
        mask[5, 3:7] = True
        self.assertEqual(_mask_band_span_ratio(mask, 4, 1, 100), 0.06)

    def test_missing_band_is_not_fabricated(self):
        mask = np.zeros((10, 10), dtype=bool)
        self.assertIsNone(_mask_band_span_ratio(mask, 4, 1, 100))

    def test_paired_views_produce_dimensionless_experimental_indices(self):
        front = {
            "measurements": {
                "shoulder_landmark_span_over_pixel_height": measurement(0.22),
                "hip_landmark_span_over_pixel_height": measurement(0.18),
                "chest_span_over_pixel_height": measurement(0.20, 0.35),
                "waist_span_over_pixel_height": measurement(0.17, 0.45),
                "abdomen_span_over_pixel_height": measurement(0.18, 0.49),
                "hip_span_over_pixel_height": measurement(0.19, 0.55),
            }
        }
        side = {
            "measurements": {
                "chest_span_over_pixel_height": measurement(0.12, 0.35),
                "waist_span_over_pixel_height": measurement(0.11, 0.45),
                "abdomen_span_over_pixel_height": measurement(0.12, 0.49),
                "hip_span_over_pixel_height": measurement(0.13, 0.55),
            }
        }
        result = _derived_anthropometry(front, side)["derived_features"]
        self.assertAlmostEqual(result["shoulder_to_hip_ratio"]["value"], 0.22 / 0.18, places=5)
        self.assertTrue(result["body_volume_proxy_index"]["valid"])
        self.assertEqual(result["body_volume_proxy_index"]["unit"], "dimensionless_index")

    def test_invalid_measurement_leaves_derived_value_missing(self):
        result = _derived_anthropometry({"measurements": {"waist_span_over_pixel_height": measurement(None, valid=False)}}, None)
        waist_height = result["derived_features"]["waist_to_height_ratio"]
        self.assertIsNone(waist_height["value"])
        self.assertFalse(waist_height["valid"])

    def test_quality_signals_are_reported_separately(self):
        quality = _quality_signal({
            "person_count": 1,
            "expected_view": "front",
            "nose_pose_visibility": 0.82,
            "segmentation_fill_ratio": 0.31,
            "quality_gate_enabled": True,
        }, 0.91)
        self.assertEqual(quality["person_detection"]["raw_detector_score"], 0.91)
        self.assertEqual(quality["pose"]["status"], "passed")
        self.assertEqual(quality["segmentation"]["status"], "passed")
        self.assertNotIn("confidence", quality)


if __name__ == "__main__":
    unittest.main()
