import sys
import unittest
from pathlib import Path

import numpy as np

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT / "paper"))

from evaluate_grouped import _assert_group_disjoint, _new_weight_candidate


class GroupedSplitTests(unittest.TestCase):
    def test_disjoint_participant_partitions_pass(self):
        _assert_group_disjoint(np.array(["p1", "p1", "p2"]), np.array(["p3"]), "test")

    def test_participant_leakage_fails(self):
        with self.assertRaisesRegex(ValueError, "Participant leakage"):
            _assert_group_disjoint(np.array(["p1", "p2"]), np.array(["p2", "p3"]), "test")

    def test_weight_candidates_tune_with_grouped_training_folds(self):
        groups = np.repeat(np.arange(8), 2)
        features = np.column_stack((groups.astype(float), np.tile([0.2, 0.7], 8)))
        targets = 45.0 + groups * 2 + np.tile([0.0, 1.0], 8)
        for name in ("ridge_tuned", "elasticnet_tuned"):
            model = _new_weight_candidate(name, len(np.unique(groups)))
            model.fit(features, targets, groups=groups)
            predictions = model.predict(features[:4])
            self.assertTrue(np.isfinite(predictions).all())
            for train_idx, test_idx in model.cv.split(features, targets, groups):
                _assert_group_disjoint(groups[train_idx], groups[test_idx], name)


if __name__ == "__main__":
    unittest.main()
