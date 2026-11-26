"""Synthetic paired fixtures, never experiment observations."""

from copy import deepcopy
import contextlib
import io
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from source.task1_nqueens.paired_analysis import analyze_pairs, compare_pairs


def pair(seed, left_steps, right_steps, left_status="SAT", right_status="SAT"):
    base = {"method": "min-conflicts", "n": "4", "seed": str(seed),
            "initial_state": "[0,0,0,0]", "max_steps": "100", "timeout_seconds": "5",
            "solution_valid": "True"}
    return [{**base, "strategy": strategy, "status": status, "steps": str(steps),
             "algorithm_total_seconds": str(steps / 1000)}
            for strategy, steps, status in (("random_conflicted", left_steps, left_status),
                                           ("max_conflicted", right_steps, right_status))]


class PairedAnalysisTests(unittest.TestCase):
    def test_cli_analysis_uses_new_destination_and_refuses_overwrite(self):
        source = Path(__file__).resolve().parents[2] / "results/task1/main-20261126"
        with TemporaryDirectory() as temporary, contextlib.redirect_stdout(io.StringIO()):
            output = Path(temporary) / "paired"
            summaries = analyze_pairs(source, output)
            self.assertEqual([r["joint_success_pairs"] for r in summaries], [30, 27, 26, 30, 30])
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            with self.assertRaises(FileExistsError):
                analyze_pairs(source, output)
            self.assertEqual(before, {p.name: p.read_bytes() for p in output.iterdir()})

    def test_joint_subset_and_per_pair_delta_are_distinct_from_marginal_medians(self):
        rows = pair(0, 1, 2) + pair(1, 10, 20) + pair(2, 100, 50)
        original = deepcopy(rows)
        pairs, summaries = compare_pairs(rows)
        summary = summaries[0]
        self.assertEqual(summary["joint_success_pairs"], 3)
        self.assertEqual(summary["median_delta_steps"], 1)
        self.assertEqual(summary["median_max_steps"] - summary["median_random_steps"], 10)
        self.assertEqual(summary["max_lower_steps_pairs"], 1)
        self.assertEqual(summary["max_higher_steps_pairs"], 2)
        self.assertEqual(len(pairs), 3)
        self.assertEqual(rows, original)

    def test_failures_remain_in_pair_inventory_but_not_conditional_metrics(self):
        rows = pair(0, 10, 5) + pair(1, 3, 100, right_status="LIMIT_REACHED")
        pairs, summaries = compare_pairs(rows)
        self.assertEqual(summaries[0]["all_pairs"], 2)
        self.assertEqual(summaries[0]["excluded_pairs"], 1)
        self.assertIsNone(pairs[1]["delta_steps"])
        self.assertEqual(pairs[1]["max_status"], "LIMIT_REACHED")
        self.assertEqual(summaries[0]["median_delta_steps"], -5)

    def test_no_joint_success_leaves_medians_missing(self):
        _, summaries = compare_pairs(pair(0, 100, 100, "LIMIT_REACHED", "LIMIT_REACHED"))
        self.assertEqual(summaries[0]["joint_success_pairs"], 0)
        self.assertIsNone(summaries[0]["median_delta_algorithm_total_seconds"])

    def test_incomplete_duplicate_or_mismatched_pairs_are_rejected(self):
        rows = pair(0, 10, 5)
        cases = [rows[:1], rows + rows[:1]]
        for key, value in (("initial_state", "[1,0,0,0]"), ("max_steps", "101"),
                           ("timeout_seconds", "4")):
            changed = deepcopy(rows)
            changed[1][key] = value
            cases.append(changed)
        for rows in cases:
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                compare_pairs(rows)
