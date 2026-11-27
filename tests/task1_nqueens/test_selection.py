import contextlib
import io
import random
import unittest
from unittest.mock import Mock

from source.task1_nqueens import (
    MaxConflictedSelector,
    MinConflictsBoard,
    MinConflictsSolver,
    NQueensProblem,
    RandomConflictedSelector,
    SolutionValidator,
    SolveStatus,
)
from source.task1_nqueens.cli import main


STRATEGIES = ("random_conflicted", "max_conflicted")


def without_time(result):
    return {key: value for key, value in result.statistics.items() if key != "total_seconds"}


class SelectorTests(unittest.TestCase):
    def test_max_selects_unique_most_conflicted_queen(self):
        board = MinConflictsBoard(NQueensProblem(4), (0, 0, 0, 1))
        self.assertEqual([board.conflicts(c) for c in range(4)], [2, 2, 3, 1])
        rng = Mock(spec=random.Random)
        rng.choice.side_effect = lambda candidates: candidates[0]
        column = MaxConflictedSelector().select_column(board, board.conflicted_columns(), rng)
        self.assertEqual(column, 2)
        rng.choice.assert_called_once_with([2])

    def test_max_breaks_ties_only_between_maximum_conflict_queens(self):
        board = MinConflictsBoard(NQueensProblem(4), (0, 0, 1, 1))
        self.assertEqual([board.conflicts(c) for c in range(4)], [1, 2, 2, 1])
        rng = Mock(spec=random.Random)
        rng.choice.side_effect = lambda candidates: candidates[-1]
        self.assertEqual(MaxConflictedSelector().select_column(board, board.conflicted_columns(), rng), 2)
        rng.choice.assert_called_once_with([1, 2])

    def test_random_can_select_a_lower_conflict_queen(self):
        board = MinConflictsBoard(NQueensProblem(4), (0, 0, 0, 1))
        rng = Mock(spec=random.Random)
        rng.choice.side_effect = lambda candidates: candidates[-1]
        self.assertEqual(RandomConflictedSelector().select_column(board, board.conflicted_columns(), rng), 3)
        rng.choice.assert_called_once_with([0, 1, 2, 3])

    def test_solved_board_returns_none_without_consuming_randomness(self):
        board = MinConflictsBoard(NQueensProblem(4), (1, 3, 0, 2))
        for selector in (RandomConflictedSelector(), MaxConflictedSelector()):
            with self.subTest(selector=type(selector).__name__):
                rng = random.Random(42)
                before = rng.getstate()
                self.assertIsNone(selector.select_column(board, board.conflicted_columns(), rng))
                self.assertEqual(before, rng.getstate())
                self.assertEqual(board.rows, (1, 3, 0, 2))

    def test_max_always_selects_a_maximum_on_every_n3_state(self):
        from itertools import product

        selector = MaxConflictedSelector()
        rng = random.Random(0)
        for rows in product(range(3), repeat=3):
            board = MinConflictsBoard(NQueensProblem(3), rows)
            conflicted = board.conflicted_columns()
            selected = selector.select_column(board, conflicted, rng)
            if conflicted:
                self.assertEqual(board.conflicts(selected), max(board.conflicts(c) for c in conflicted))
            else:
                self.assertIsNone(selected)
            self.assertEqual(board.rows, rows)


class StrategyIntegrationTests(unittest.TestCase):
    def test_both_strategies_solve_and_validate_on_last_step(self):
        problem = NQueensProblem(4)
        for strategy in STRATEGIES:
            with self.subTest(strategy=strategy):
                result = MinConflictsSolver(
                    problem, seed=0, max_steps=1,
                    initial_state=(1, 3, 0, 0), strategy=strategy,
                ).solve()
                self.assertEqual(result.status, SolveStatus.SAT)
                self.assertTrue(SolutionValidator(problem).validate(result.solution))
                self.assertEqual(result.statistics["steps"], 1)
                self.assertEqual(result.statistics["strategy"], strategy)

    def test_both_strategies_preserve_zero_budget_semantics(self):
        for strategy in STRATEGIES:
            for rows, expected in (((1, 3, 0, 2), SolveStatus.SAT), ((0, 0, 0, 0), SolveStatus.LIMIT_REACHED)):
                with self.subTest(strategy=strategy, rows=rows):
                    result = MinConflictsSolver(
                        NQueensProblem(4), max_steps=0, initial_state=rows, strategy=strategy
                    ).solve()
                    self.assertEqual(result.status, expected)
                    self.assertEqual(result.statistics["steps"], 0)

    def test_both_strategies_reject_a_candidate_if_validator_fails(self):
        from unittest.mock import patch

        for strategy in STRATEGIES:
            with self.subTest(strategy=strategy), patch(
                "source.task1_nqueens.min_conflicts.SolutionValidator"
            ) as validator:
                validator.return_value.validate.return_value = False
                result = MinConflictsSolver(
                    NQueensProblem(4), initial_state=(1, 3, 0, 2), strategy=strategy
                ).solve()
                self.assertEqual(result.status, SolveStatus.ERROR)
                self.assertIsNone(result.solution)

    def test_shared_initial_state_is_copied_and_runs_are_independent(self):
        shared = [1, 3, 0, 0]
        solvers = [
            MinConflictsSolver(NQueensProblem(4), seed=0, max_steps=1,
                               initial_state=shared, strategy=strategy)
            for strategy in STRATEGIES
        ]
        first = solvers[0].solve()
        self.assertEqual(shared, [1, 3, 0, 0])
        self.assertEqual(solvers[1].initial_state, (1, 3, 0, 0))
        shared[0] = 99
        second = solvers[1].solve()
        self.assertEqual(first.statistics["initial_state"], second.statistics["initial_state"])
        self.assertEqual(first.status, SolveStatus.SAT)
        self.assertEqual(second.status, SolveStatus.SAT)
        self.assertEqual(without_time(first), without_time(solvers[0].solve()))

    def test_random_default_preserves_observed_baseline_result(self):
        default = MinConflictsSolver(NQueensProblem(8), seed=42, max_steps=1000).solve()
        explicit = MinConflictsSolver(
            NQueensProblem(8), seed=42, max_steps=1000, strategy="random_conflicted"
        ).solve()
        self.assertEqual(default.status, SolveStatus.SAT)
        self.assertEqual(default.solution, explicit.solution)
        self.assertEqual(without_time(default), without_time(explicit))
        # Regression fixture from the baseline stage on Python 3.12.10.
        self.assertEqual(default.statistics["steps"], 111)
        self.assertEqual(default.statistics["moves"], 76)
        self.assertEqual(default.statistics["final_state"], "(1, 4, 6, 3, 0, 7, 5, 2)")

    def test_max_strategy_is_reproducible_and_preserves_global_rng(self):
        solver = MinConflictsSolver(NQueensProblem(8), seed=42, max_steps=1000, strategy="max_conflicted")
        before = random.getstate()
        first = solver.solve()
        second = solver.solve()
        self.assertEqual(random.getstate(), before)
        self.assertEqual(first.status, second.status)
        self.assertEqual(first.solution, second.solution)
        self.assertEqual(without_time(first), without_time(second))
        self.assertIn(first.status, (SolveStatus.SAT, SolveStatus.LIMIT_REACHED))
        if first.status is SolveStatus.SAT:
            self.assertTrue(SolutionValidator(NQueensProblem(8)).validate(first.solution))

    def test_invalid_strategy_is_rejected(self):
        for strategy in (None, True, [], 1):
            with self.subTest(strategy=strategy), self.assertRaises(TypeError):
                MinConflictsSolver(NQueensProblem(4), strategy=strategy)
        with self.assertRaises(ValueError):
            MinConflictsSolver(NQueensProblem(4), strategy="unknown")


class StrategyCLITests(unittest.TestCase):
    def test_each_strategy_can_be_selected_in_cli(self):
        for strategy in STRATEGIES:
            with self.subTest(strategy=strategy):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    exit_code = main([
                        "4", "--method", "min-conflicts", "--strategy", strategy,
                        "--seed", "0", "--max-steps", "1", "--initial-state", "1,3,0,0",
                    ])
                self.assertEqual(exit_code, 0)
                self.assertIn(f"strategy: {strategy}\n", output.getvalue())
                self.assertIn("Status: SAT", output.getvalue())

    def test_strategy_options_reject_unknown_and_sat_usage(self):
        for arguments in (
            ["4", "--strategy", "max_conflicted"],
            ["4", "--method", "min-conflicts", "--strategy", "unknown"],
        ):
            with self.subTest(arguments=arguments), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    main(arguments)
                self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
