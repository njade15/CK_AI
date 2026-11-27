"""Read-only checks of committed observations, distinct from synthetic fixtures."""

from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
from statistics import median
import unittest

from source.task1_nqueens.benchmark_analysis import audit, summarize
from source.task1_nqueens.paired_analysis import compare_pairs


ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT / "results/task1/main-20261126"


def read_csv(path):
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


class RecordedResultsTests(unittest.TestCase):
    def test_original_main_and_smoke_checksums(self):
        count = 0
        for directory in (MAIN, MAIN.parent / "smoke-20261126"):
            for line in (directory / "SHA256SUMS.txt").read_text().splitlines():
                expected, name = line.split("  ", 1)
                with self.subTest(directory=directory.name, name=name):
                    self.assertEqual(hashlib.sha256((directory / name).read_bytes()).hexdigest(), expected)
                count += 1
        self.assertEqual(count, 19)

    def test_official_inventory_and_independent_solution_audit(self):
        rows = read_csv(MAIN / "trials.csv")
        checked = audit(rows, json.loads((MAIN / "config.json").read_text()),
                        json.loads((MAIN / "metadata.json").read_text()))
        self.assertEqual(checked["trials"], 325)
        self.assertEqual(checked["paired_mc_initial_states"], 150)
        self.assertEqual(Counter(row["method"] for row in rows), {"sat": 25, "min-conflicts": 300})
        self.assertEqual(checked["statuses"], {"SAT": 318, "LIMIT_REACHED": 7})
        failures = {(int(r["n"]), r["strategy"], int(r["seed"])) for r in rows if r["status"] == "LIMIT_REACHED"}
        expected = {(8, "max_conflicted", seed) for seed in (1, 6, 16)}
        expected |= {(16, "max_conflicted", seed) for seed in (8, 19)}
        expected |= {(16, "random_conflicted", seed) for seed in (14, 28)}
        self.assertEqual(failures, expected)
        self.assertTrue(all(r["steps"] == "5000" for r in rows if r["status"] == "LIMIT_REACHED"))
        pairs, summaries = compare_pairs(rows)
        self.assertEqual(len(pairs), 150)
        self.assertEqual([r["joint_success_pairs"] for r in summaries], [30, 27, 26, 30, 30])

    def test_every_summary_field_recomputes_from_raw_trials(self):
        saved = read_csv(MAIN / "summary.csv")
        computed = summarize(read_csv(MAIN / "trials.csv"))
        self.assertEqual(len(saved), len(computed))
        for actual, expected in zip(saved, computed):
            for key, value in expected.items():
                with self.subTest(method=expected["method"], n=expected["n"], key=key):
                    self.assertEqual(actual[key], "" if value is None else str(value))

    def test_all_numeric_analysis_table_cells_match_raw_trials(self):
        rows = read_csv(MAIN / "trials.csv")
        def check_number(cell, value):
            normalized = cell.replace(",", ".")
            places = len(normalized.split(".")[1]) if "." in normalized else 0
            self.assertEqual(normalized, f"{value:.{places}f}")

        tables_checked = Counter()
        for line in (MAIN / "ANALYSIS.md").read_text(encoding="utf-8").splitlines():
            if not line.startswith("| "):
                continue
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if not cells[0].isdigit():
                continue
            n = int(cells[0])
            if len(cells) == 7 and "/" not in cells[1]:
                subset = [r for r in rows if r["method"] == "sat" and int(r["n"]) == n]
                self.assertEqual(cells[1:3], [subset[0]["num_variables"], subset[0]["clauses_total"]])
                for cell, key in zip(cells[3:], ("cnf_generation_seconds", "solver_initialization_seconds",
                                              "solve_seconds", "algorithm_total_seconds")):
                    check_number(cell, 1000 * median(float(r[key]) for r in subset))
                tables_checked["sat"] += 1
            elif len(cells) == 7:
                for offset, strategy in enumerate(("random_conflicted", "max_conflicted")):
                    subset = [r for r in rows if r["strategy"] == strategy and int(r["n"]) == n]
                    successful = [r for r in subset if r["status"] == "SAT"]
                    self.assertEqual(cells[1 + offset], f"{len(successful)}/{len(subset)}")
                    check_number(cells[3 + offset], median(int(r["steps"]) for r in successful))
                    check_number(cells[5 + offset], 1000 * median(float(r["algorithm_total_seconds"]) for r in successful))
                tables_checked["mc"] += 1
            elif len(cells) == 4:
                failed = [r for r in rows if int(r["n"]) == n and r["strategy"] == cells[1]
                          and r["status"] == "LIMIT_REACHED"]
                self.assertEqual(cells[2], ", ".join(r["seed"] for r in failed))
                self.assertTrue(all(cells[3] == r["steps"] for r in failed))
                tables_checked["limits"] += 1
        self.assertEqual(tables_checked, {"sat": 5, "mc": 5, "limits": 3})
