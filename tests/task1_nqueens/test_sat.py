import contextlib
import io
from itertools import product
import math
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from source.task1_nqueens import (
    CNFEncoder,
    NQueensProblem,
    SATNQueensSolver,
    SolutionValidator,
    SolveStatus,
)
from source.task1_nqueens.cli import main


N4_SOLUTION = ((0, 1), (1, 3), (2, 0), (3, 2))
SOLVER_PATH = "source.task1_nqueens.sat_solver.Glucose3"


def satisfies(clauses, true_variables):
    """Independent evaluation: unlisted variables are assigned False."""
    return all(
        any((literal > 0) == (abs(literal) in true_variables) for literal in clause)
        for clause in clauses
    )


class EncoderTests(unittest.TestCase):
    def test_variable_mapping_round_trip(self):
        for n in (1, 2, 4, 8):
            encoder = CNFEncoder(NQueensProblem(n))
            identifiers = set()
            for row in range(n):
                for column in range(n):
                    identifier = encoder.variable_id(row, column)
                    self.assertEqual(identifier, row * n + column + 1)
                    self.assertEqual(encoder.decode_variable(identifier), (row, column))
                    identifiers.add(identifier)
            self.assertEqual(identifiers, set(range(1, n * n + 1)))

    def test_mapping_rejects_bad_coordinates_and_identifiers(self):
        encoder = CNFEncoder(NQueensProblem(4))
        for position in ((-1, 0), (4, 0), (0, -1), (0, 4)):
            with self.subTest(position=position), self.assertRaises(ValueError):
                encoder.variable_id(*position)
        for position in ((True, 0), (0, False), (0.0, 1), (0, "1")):
            with self.subTest(position=position), self.assertRaises(TypeError):
                encoder.variable_id(*position)
        for identifier in (-1, 0, 17):
            with self.subTest(identifier=identifier), self.assertRaises(ValueError):
                encoder.decode_variable(identifier)
        for identifier in (True, 1.0, "1", None):
            with self.subTest(identifier=identifier), self.assertRaises(TypeError):
                encoder.decode_variable(identifier)

    def test_decode_complete_signed_model(self):
        encoder = CNFEncoder(NQueensProblem(4))
        true_variables = {encoder.variable_id(*position) for position in N4_SOLUTION}
        model = [i if i in true_variables else -i for i in range(16, 0, -1)]
        self.assertEqual(encoder.decode_model(model), N4_SOLUTION)

    def test_decode_rejects_missing_repeated_and_invalid_literals(self):
        encoder = CNFEncoder(NQueensProblem(1))
        for model in ([], [1, 1], [1, -1], [0], [2]):
            with self.subTest(model=model), self.assertRaises(ValueError):
                encoder.decode_model(model)
        for model in ([True], [1.0], ["1"]):
            with self.subTest(model=model), self.assertRaises(TypeError):
                encoder.decode_model(model)

    def test_n4_group_counts_and_no_extra_variables(self):
        cnf = CNFEncoder(NQueensProblem(4)).encode()
        self.assertEqual(cnf.num_variables, 16)
        self.assertEqual(dict(cnf.clause_counts), {
            "row_at_least_one": 4,
            "row_at_most_one": 24,
            "column_at_most_one": 24,
            "descending_diagonal_at_most_one": 14,
            "ascending_diagonal_at_most_one": 14,
        })
        self.assertEqual(len(cnf.clauses), 80)
        self.assertEqual({abs(lit) for clause in cnf.clauses for lit in clause}, set(range(1, 17)))

    def test_generated_counts_match_closed_form(self):
        for n in range(1, 13):
            with self.subTest(n=n):
                cnf = CNFEncoder(NQueensProblem(n)).encode()
                expected = n + n * n * (n - 1) + n * (n - 1) * (2 * n - 1) // 3
                self.assertEqual(len(cnf.clauses), expected)
                self.assertEqual(sum(cnf.clause_counts.values()), len(cnf.clauses))
                self.assertEqual(len(set(cnf.clauses)), len(cnf.clauses))

    def test_only_required_row_clauses_and_attack_pairs_are_present(self):
        encoder = CNFEncoder(NQueensProblem(4))
        cnf = encoder.encode()
        actual = {frozenset(clause) for clause in cnf.clauses}
        expected = {
            frozenset(encoder.variable_id(row, column) for column in range(4))
            for row in range(4)
        }
        # Enumerate all square pairs independently of encoder group generation.
        for left in range(1, 17):
            r1, c1 = divmod(left - 1, 4)
            for right in range(left + 1, 17):
                r2, c2 = divmod(right - 1, 4)
                if r1 == r2 or c1 == c2 or abs(r1 - r2) == abs(c1 - c2):
                    expected.add(frozenset((-left, -right)))
        self.assertEqual(actual, expected)

    def test_known_solution_satisfies_every_clause(self):
        encoder = CNFEncoder(NQueensProblem(4))
        true_variables = {encoder.variable_id(*position) for position in N4_SOLUTION}
        self.assertTrue(satisfies(encoder.encode().clauses, true_variables))

    def test_wrong_placements_violate_cnf(self):
        encoder = CNFEncoder(NQueensProblem(4))
        cnf = encoder.encode()
        wrong_placements = {
            "missing_row": N4_SOLUTION[:3],
            "duplicate_row": ((0, 1), (0, 3), (2, 0), (3, 2)),
            "duplicate_column": ((0, 1), (1, 1), (2, 0), (3, 2)),
            "descending_diagonal": ((0, 0), (1, 1), (2, 2), (3, 3)),
            "ascending_diagonal": ((0, 3), (1, 2), (2, 1), (3, 0)),
            "empty_board": (),
        }
        for reason, queens in wrong_placements.items():
            with self.subTest(reason=reason):
                true_variables = {encoder.variable_id(*position) for position in queens}
                self.assertFalse(satisfies(cnf.clauses, true_variables))

    def test_exhaustive_small_boards_match_independent_validator(self):
        for n in (1, 2, 3):
            problem = NQueensProblem(n)
            encoder = CNFEncoder(problem)
            cnf = encoder.encode()
            validator = SolutionValidator(problem)
            for bits in product((False, True), repeat=n * n):
                true_variables = {i + 1 for i, value in enumerate(bits) if value}
                queens = tuple(divmod(i - 1, n) for i in true_variables)
                self.assertEqual(satisfies(cnf.clauses, true_variables), validator.validate(queens))


class SATSolverTests(unittest.TestCase):
    def test_progress_preserves_outcome_and_returns_independent_phase_snapshots(self):
        for n in (2, 4, 8):
            with self.subTest(n=n):
                solver = SATNQueensSolver(NQueensProblem(n))
                plain = solver.solve()
                snapshots = []
                observed = solver.solve(progress=snapshots.append)
                self.assertEqual(observed.status, plain.status)
                self.assertEqual(observed.solution, plain.solution)
                self.assertEqual(observed.message, plain.message)
                self.assertEqual(len(snapshots), 3)
                for index, key in enumerate(("cnf_generation_seconds",
                                             "solver_initialization_seconds", "solve_seconds")):
                    self.assertIn(key, snapshots[index])
                    if index:
                        self.assertNotIn(key, snapshots[index - 1])
                self.assertNotIn("total_seconds", snapshots[-1])
                snapshots[-1]["clauses_total"] = -1
                self.assertEqual(observed.statistics["clauses_total"], plain.statistics["clauses_total"])
                self.assertGreaterEqual(observed.elapsed_seconds, sum(
                    observed.statistics[key] for key in ("cnf_generation_seconds",
                    "solver_initialization_seconds", "solve_seconds")))

    def test_progress_exception_after_loading_reports_error_and_cleans_up(self):
        calls = []

        def failing_callback(snapshot):
            calls.append(snapshot)
            if "solver_initialization_seconds" in snapshot:
                raise RuntimeError("injected callback failure")

        with patch(SOLVER_PATH) as constructor:
            native = constructor.return_value
            result = SATNQueensSolver(NQueensProblem(4)).solve(progress=failing_callback)
            self.assertEqual(result.status, SolveStatus.ERROR)
            self.assertIn("injected callback failure", result.message)
            self.assertIsNone(result.solution)
            native.solve.assert_not_called()
            native.delete.assert_called_once_with()
            self.assertNotIn("solve_seconds", result.statistics)
            self.assertEqual(len(calls), 2)

    def test_real_glucose_sat_and_unsat(self):
        for n in (1, 2, 3, 4, 8):
            with self.subTest(n=n):
                problem = NQueensProblem(n)
                result = SATNQueensSolver(problem).solve()
                self.assertIsNone(result.message)
                if n in (2, 3):
                    self.assertEqual(result.status, SolveStatus.UNSAT)
                    self.assertIsNone(result.solution)
                else:
                    self.assertEqual(result.status, SolveStatus.SAT)
                    self.assertTrue(SolutionValidator(problem).validate(result.solution))
                    encoder = CNFEncoder(problem)
                    true_variables = {encoder.variable_id(*p) for p in result.solution}
                    self.assertTrue(satisfies(encoder.encode().clauses, true_variables))
                statistics = result.statistics
                self.assertEqual(statistics["num_variables"], n * n)
                self.assertEqual(statistics["clauses_total"], len(CNFEncoder(problem).encode().clauses))
                phase_total = 0.0
                for name in ("cnf_generation_seconds", "solver_initialization_seconds", "solve_seconds"):
                    self.assertTrue(math.isfinite(statistics[name]))
                    self.assertGreaterEqual(statistics[name], 0)
                    phase_total += statistics[name]
                self.assertGreaterEqual(result.elapsed_seconds, phase_total)
                self.assertEqual(result.elapsed_seconds, statistics["total_seconds"])
                for name in ("restarts", "conflicts", "decisions", "propagations"):
                    self.assertGreaterEqual(statistics[f"solver_{name}"], 0)

    def test_solver_releases_native_resource_after_success(self):
        with patch(SOLVER_PATH) as constructor:
            native = constructor.return_value
            native.solve.return_value = True
            native.get_model.return_value = [1]
            native.accum_stats.return_value = {}
            result = SATNQueensSolver(NQueensProblem(1)).solve()
            self.assertEqual(result.status, SolveStatus.SAT)
            native.delete.assert_called_once_with()

    def test_unknown_is_limit_reached_and_resource_is_released(self):
        with patch(SOLVER_PATH) as constructor:
            native = constructor.return_value
            native.solve.return_value = None
            native.accum_stats.return_value = {}
            result = SATNQueensSolver(NQueensProblem(4)).solve()
            self.assertEqual(result.status, SolveStatus.LIMIT_REACHED)
            self.assertIsNone(result.solution)
            native.delete.assert_called_once_with()

    def test_load_or_solve_error_is_error_and_releases_resource(self):
        for failing_method in ("append_formula", "solve"):
            with self.subTest(method=failing_method), patch(SOLVER_PATH) as constructor:
                native = constructor.return_value
                getattr(native, failing_method).side_effect = RuntimeError("injected test failure")
                result = SATNQueensSolver(NQueensProblem(4)).solve()
                self.assertEqual(result.status, SolveStatus.ERROR)
                self.assertIsNone(result.solution)
                self.assertIn("injected test failure", result.message)
                native.delete.assert_called_once_with()
                if failing_method == "append_formula":
                    native.solve.assert_not_called()
                    self.assertNotIn("solve_seconds", result.statistics)

    def test_invalid_sat_model_is_error_and_releases_resource(self):
        # Complete assignment with four queens in one column; not a solution.
        invalid_model = [i if i in (1, 5, 9, 13) else -i for i in range(1, 17)]
        for model in (None, invalid_model, [2, 8, 9, 15]):
            with self.subTest(model=model), patch(SOLVER_PATH) as constructor:
                native = constructor.return_value
                native.solve.return_value = True
                native.get_model.return_value = model
                native.accum_stats.return_value = {}
                result = SATNQueensSolver(NQueensProblem(4)).solve()
                self.assertEqual(result.status, SolveStatus.ERROR)
                self.assertIsNone(result.solution)
                native.delete.assert_called_once_with()

    def test_cleanup_failure_is_reported(self):
        with patch(SOLVER_PATH) as constructor:
            native = constructor.return_value
            native.solve.return_value = False
            native.accum_stats.return_value = {}
            native.delete.side_effect = RuntimeError("injected cleanup failure")
            result = SATNQueensSolver(NQueensProblem(2)).solve()
            self.assertEqual(result.status, SolveStatus.ERROR)
            self.assertIn("cleanup failed", result.message)

    def test_constructor_failure_is_error_without_claiming_solve_time(self):
        with patch(SOLVER_PATH, side_effect=RuntimeError("injected constructor failure")):
            result = SATNQueensSolver(NQueensProblem(4)).solve()
            self.assertEqual(result.status, SolveStatus.ERROR)
            self.assertNotIn("solve_seconds", result.statistics)


class CLITests(unittest.TestCase):
    def test_module_entry_point_sat_and_unsat(self):
        for n, expected_status in ((1, "SAT"), (2, "UNSAT"), (3, "UNSAT"), (4, "SAT"), (8, "SAT")):
            with self.subTest(n=n):
                completed = subprocess.run(
                    [sys.executable, "-m", "source.task1_nqueens", str(n)],
                    cwd=Path(__file__).resolve().parents[2],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                self.assertEqual(completed.returncode, 0, completed.stderr)
                self.assertIn(f"Status: {expected_status}\n", completed.stdout)
                self.assertIn("clauses_total:", completed.stdout)
                self.assertEqual("Queens (row, column" in completed.stdout, expected_status == "SAT")

    def test_invalid_n_exits_with_argument_error(self):
        for argument in ("0", "-1", "abc", "4.0"):
            with self.subTest(argument=argument), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    main([argument])
                self.assertEqual(error.exception.code, 2)

    def test_error_and_limit_exit_codes(self):
        from source.task1_nqueens import SolveResult

        for status, exit_code in ((SolveStatus.ERROR, 1), (SolveStatus.LIMIT_REACHED, 3)):
            with self.subTest(status=status), patch("source.task1_nqueens.cli.SATNQueensSolver") as solver:
                solver.return_value.solve.return_value = SolveResult(status, 0.0)
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(main(["4"]), exit_code)


if __name__ == "__main__":
    unittest.main()
