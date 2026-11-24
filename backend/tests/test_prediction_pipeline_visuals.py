import unittest

import numpy as np

from services.height_estimator import (
    _clean_segmentation_mask,
    _draw_pose_overlay,
)


class PredictionPipelineVisualTests(unittest.TestCase):
    def test_segmentation_preview_discards_background_outside_person(self):
        segmentation = np.zeros((100, 100), dtype=np.float32)
        segmentation[25:80, 40:60] = 0.99
        segmentation[12:16, 42:46] = 0.99
        segmentation[0:10, 0:10] = 0.99

        mask = _clean_segmentation_mask(segmentation, (30, 10, 70, 90))

        self.assertTrue(mask[50, 50])
        self.assertFalse(mask[13, 43])
        self.assertFalse(mask[5, 5])

    def test_pose_overlay_marks_both_elbows_and_wrists(self):
        landmarks = {
            "left_shoulder": (30, 20),
            "right_shoulder": (70, 20),
            "left_elbow": (20, 40),
            "right_elbow": (80, 40),
            "left_wrist": (15, 55),
            "right_wrist": (85, 55),
            "left_hip": (35, 60),
            "right_hip": (65, 60),
            "left_knee": (35, 80),
            "right_knee": (65, 80),
            "left_ankle": (35, 100),
            "right_ankle": (65, 100),
            "left_heel": (33, 102),
            "right_heel": (67, 102),
            "left_toe": (30, 105),
            "right_toe": (70, 105),
        }
        image = np.zeros((120, 120, 3), dtype=np.uint8)

        _draw_pose_overlay(image, landmarks, (50, 10), (70, 105), 170, 5, 7.0)

        marker_color = np.array([255, 0, 255], dtype=np.uint8)
        for name in ("left_elbow", "right_elbow", "left_wrist", "right_wrist"):
            x, y = landmarks[name]
            np.testing.assert_array_equal(image[y, x], marker_color)


if __name__ == "__main__":
    unittest.main()
