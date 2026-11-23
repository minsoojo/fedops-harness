"""Exercise checks for one standalone function, without importing Flower."""

import __future__
import ast
import sys
import unittest
from copy import deepcopy
from pathlib import Path


def load_weighted_average(path):
    """Execute only the selected function definition. This is not a sandbox."""
    tree = ast.parse(path.read_bytes(), filename=str(path))
    matches = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "weighted_average"
    ]
    if len(matches) != 1:
        raise ValueError("Expected one top-level weighted_average function")
    module = ast.Module(body=matches, type_ignores=[])
    code = compile(module, str(path), "exec", flags=__future__.annotations.compiler_flag)
    namespace = {}
    exec(code, namespace)
    return namespace["weighted_average"]


class WeightedAverageTest(unittest.TestCase):
    def test_missing_metric_counts_only_reporting_clients(self):
        result = self.aggregate([(10, {"accuracy": 0.8}), (30, {})])
        self.assertAlmostEqual(result["accuracy"], 0.8)

    def test_each_metric_has_its_own_denominator(self):
        result = self.aggregate([
            (10, {"accuracy": 0.5, "loss": 1}),
            (30, {"accuracy": 1, "recall": 0.5}),
            (10, {"loss": 3, "recall": 1}),
        ])
        self.assertAlmostEqual(result["accuracy"], 0.875)
        self.assertAlmostEqual(result["loss"], 2)
        self.assertAlmostEqual(result["recall"], 0.625)

    def test_reported_zero_counts_toward_average(self):
        result = self.aggregate([(3, {"recall": 0}), (1, {"recall": 1})])
        self.assertAlmostEqual(result["recall"], 0.25)

    def test_empty_round(self):
        self.assertEqual(self.aggregate([]), {"client_performances": []})

    def test_zero_total_weight(self):
        metrics = [(0, {"loss": 2}), (0, {"loss": 8, "accuracy": 1})]
        self.assertEqual(self.aggregate(metrics), {
            "loss": 0, "accuracy": 0, "client_performances": metrics,
        })

    def test_zero_weight_for_one_metric_in_nonempty_round(self):
        result = self.aggregate([(0, {"loss": 2}), (5, {"accuracy": 0.9})])
        self.assertEqual(result["loss"], 0)
        self.assertAlmostEqual(result["accuracy"], 0.9)

    def test_preserves_original_client_performances(self):
        metrics = [(5, {"loss": 1}), (2, {}), (3, {"accuracy": 0.5})]
        original = deepcopy(metrics)
        self.assertEqual(self.aggregate(metrics)["client_performances"], original)
        self.assertEqual(metrics, original)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("Usage: python -I -B check.py path/to/aggregation.py")
    WeightedAverageTest.aggregate = staticmethod(load_weighted_average(Path(sys.argv[1])))
    unittest.main(argv=[sys.argv[0]], verbosity=2)
