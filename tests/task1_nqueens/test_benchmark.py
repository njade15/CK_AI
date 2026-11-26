"""Pipeline test fixtures below are not experiment observations."""

from copy import deepcopy
import json
import multiprocessing
from pathlib import Path
from time import perf_counter, sleep
import unittest

from source.task1_nqueens.benchmark import (
    FIELDS, execute_isolated, plan_trials, validate_config,
)
from source.task1_nqueens.benchmark_analysis import audit, summarize


def sleeping_worker(sender, task):
    sender.send({"kind": "progress", "statistics": {"test_marker": 1}})
    sleep(10)
    sender.close()


def invalid_solution_worker(sender, task):
    sender.send({"kind": "result", "status": "SAT", "solution": [[0, 0]], "statistics": {}})
    sender.close()


def empty_worker(sender, task):
    sender.close()


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        root = Path(__file__).resolve().parents[2]
        self.config = json.loads((root / "docs/task1/benchmark_smoke.json").read_text())
        self.task = plan_trials(self.config)[0]

    def test_paired_initial_states_are_equal_but_separate_lists(self):
        tasks = plan_trials(self.config)
        mc = [task for task in tasks if task["method"] == "min-conflicts"]
        for left, right in zip(mc[::2], mc[1::2]):
            self.assertEqual(left["seed"], right["seed"])
            self.assertEqual(left["initial_state"], right["initial_state"])
            self.assertIsNot(left["initial_state"], right["initial_state"])
            self.assertEqual(left["max_steps"], right["max_steps"])
            self.assertNotEqual(left["strategy"], right["strategy"])
        self.assertEqual(mc[0]["strategy"], "random_conflicted")
        self.assertEqual(mc[2]["strategy"], "max_conflicted")

    def test_full_plan_declares_325_trials_and_30_mc_seeds(self):
        root = Path(__file__).resolve().parents[2]
        config = json.loads((root / "docs/task1/benchmark_full.json").read_text())
        self.assertEqual(len(plan_trials(config)), 325)
        self.assertEqual(config["mc_seeds"], list(range(30)))
        self.assertEqual(config["mc_max_steps"], 5000)

    def test_invalid_budgets_seeds_and_restart_rejected(self):
        for key, value in (("sat_timeout_seconds", 0), ("mc_timeout_seconds", float("nan")),
                           ("mc_seeds", [0, 0]), ("restart", True), ("sat_repeats", False)):
            with self.subTest(key=key):
                config = deepcopy(self.config); config[key] = value
                with self.assertRaises(ValueError):
                    validate_config(config)

    def test_deadline_really_stops_worker_and_preserves_progress(self):
        before = {child.pid for child in multiprocessing.active_children()}
        started = perf_counter()
        result = execute_isolated(self.task, 2, worker=sleeping_worker)
        elapsed = perf_counter() - started
        self.assertEqual(result["status"], "TIMEOUT")
        self.assertEqual(result["statistics"]["test_marker"], 1)
        self.assertNotIn("elapsed_seconds", result)
        self.assertLess(elapsed, 6)  # Worker would otherwise sleep for 10 seconds.
        self.assertEqual({child.pid for child in multiprocessing.active_children()}, before)

    def test_real_sat_worker_phase_metrics_and_validated_solution(self):
        result = execute_isolated(self.task, 5)
        self.assertEqual(result["status"], "SAT")
        self.assertTrue(result["solution_valid"])
        self.assertEqual(result["statistics"]["clauses_total"], 80)
        for key in ("cnf_generation_seconds", "solver_initialization_seconds", "solve_seconds"):
            self.assertGreaterEqual(result["statistics"][key], 0)

    def test_invalid_claimed_sat_is_an_error(self):
        result = execute_isolated(self.task, 5, worker=invalid_solution_worker)
        self.assertEqual(result["status"], "ERROR")
        self.assertFalse(result["solution_valid"])
        self.assertEqual(result["solver_status"], "SAT")

    def test_worker_without_result_is_recorded_as_error(self):
        result = execute_isolated(self.task, 5, worker=empty_worker)
        self.assertEqual(result["status"], "ERROR")
        self.assertNotIn("elapsed_seconds", result)

    def test_summary_keeps_failure_cost_and_success_sample_count(self):
        # Synthetic contract fixtures, never saved as benchmark data.
        base = {"method": "min-conflicts", "strategy": "random_conflicted", "n": "4"}
        rows = [
            {**base, "status": "SAT", "solution_valid": "True", "steps": "2",
             "algorithm_total_seconds": "0.1", "observed_wall_seconds": "0.2"},
            {**base, "status": "LIMIT_REACHED", "steps": "10",
             "algorithm_total_seconds": "0.4", "observed_wall_seconds": "0.5"},
            {**base, "status": "TIMEOUT", "observed_wall_seconds": "1.1"},
        ]
        result = summarize(rows)[0]
        self.assertEqual(result["successful_runs"], 1)
        self.assertEqual(result["success_rate"], 1/3)
        self.assertEqual(result["median_steps_success"], 2)
        self.assertEqual(result["steps_success_samples"], 1)
        self.assertEqual(result["sum_steps_all_recorded"], 12)
        self.assertAlmostEqual(result["sum_observed_wall_seconds_all"], 1.8)
        self.assertEqual(result["algorithm_seconds_completed_samples"], 2)

    def test_no_success_uses_missing_median_instead_of_zero(self):
        result = summarize([{"method": "min-conflicts", "strategy": "max_conflicted",
                             "n": "4", "status": "LIMIT_REACHED", "steps": "10"}])[0]
        self.assertIsNone(result["median_steps_success"])
        self.assertIsNone(result["median_algorithm_seconds_success"])
        self.assertEqual(result["steps_success_samples"], 0)

    def _unexecuted_fixture(self):
        metadata = {"source_commit": "f"*40, "working_tree_dirty": False}
        rows = []
        for task in plan_trials(self.config):
            row = dict.fromkeys(FIELDS, "")
            row.update({key: "" if value is None else str(value) for key, value in task.items()})
            row["initial_state"] = json.dumps(task["initial_state"]) if task["initial_state"] is not None else ""
            row.update({"status": "NOT_RUN", "source_commit": "f"*40, "working_tree_dirty": "False"})
            rows.append(row)
        return rows, metadata

    def test_audit_requires_every_planned_trial_even_if_unexecuted(self):
        rows, metadata = self._unexecuted_fixture()
        self.assertTrue(audit(rows, self.config, metadata)["passed"])
        with self.assertRaises(ValueError):
            audit(rows[:-1], self.config, metadata)

    def test_audit_rejects_broken_pair_and_imputed_timeout_total(self):
        rows, metadata = self._unexecuted_fixture()
        rows[-1]["initial_state"] = "[0,0,0,0]"
        with self.assertRaises(ValueError):
            audit(rows, self.config, metadata)
        rows, metadata = self._unexecuted_fixture()
        rows[0].update({"status": "TIMEOUT", "algorithm_total_seconds": "5"})
        with self.assertRaises(ValueError):
            audit(rows, self.config, metadata)


if __name__ == "__main__":
    unittest.main()
