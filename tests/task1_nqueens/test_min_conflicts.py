import contextlib
import io
from itertools import product
import random
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import call, patch

from source.task1_nqueens import (
    MinConflictsBoard,
    MinConflictsSolver,
    NQueensProblem,
    SolutionValidator,
    SolveStatus,
)
from source.task1_nqueens.cli import main


MODULE = "source.task1_nqueens.min_conflicts"
SOLVED_ROWS = (1, 3, 0, 2)


def direct_conflicts(rows, column, target_row):
    return sum(
        row == target_row or abs(row - target_row) == abs(other - column)
        for other, row in enumerate(rows)
        if other != column
    )


class BoardTests(unittest.TestCase):
    def test_hand_counted_rows_and_diagonals(self):
        for rows in ((0, 0, 0, 0), (0, 1, 2, 3), (3, 2, 1, 0)):
            with self.subTest(rows=rows):
                board = MinConflictsBoard(NQueensProblem(4), rows)
                self.assertEqual(board.conflicting_pairs, 6)
                self.assertEqual([board.conflicts(c) for c in range(4)], [3] * 4)
                self.assertEqual(board.conflicted_columns(), [0, 1, 2, 3])

    def test_no_self_conflict(self):
        singleton = MinConflictsBoard(NQueensProblem(1), [0])
        self.assertEqual(singleton.conflicts(0, 0), 0)
        board = MinConflictsBoard(NQueensProblem(4), SOLVED_ROWS)
        self.assertEqual(board.conflicting_pairs, 0)
        self.assertEqual(board.conflicted_columns(), [])

    def test_n4_example_scores_and_update(self):
        board = MinConflictsBoard(NQueensProblem(4), (1, 3, 0, 0))
        self.assertEqual(board.conflicted_columns(), [2, 3])
        self.assertEqual(board.conflicting_pairs, 1)
        self.assertEqual([board.conflicts(3, r) for r in range(4)], [1, 3, 0, 1])
        board.move(3, 2)
        self.assertEqual(board.rows, SOLVED_ROWS)
        self.assertEqual(board.conflicting_pairs, 0)
        self.assertTrue(SolutionValidator(NQueensProblem(4)).validate(board.positions()))

    def test_counters_match_direct_count_for_all_n3_states_and_moves(self):
        for rows in product(range(3), repeat=3):
            board = MinConflictsBoard(NQueensProblem(3), rows)
            for column in range(3):
                for row in range(3):
                    self.assertEqual(board.conflicts(column, row), direct_conflicts(rows, column, row))
                    board.move(column, row)
                    for other in range(3):
                        self.assertEqual(board.conflicts(other), direct_conflicts(board.rows, other, board.rows[other]))
                    board.move(column, rows[column])
            self.assertEqual(board.rows, rows)

    def test_board_copies_input_and_rejects_bad_coordinates(self):
        rows = list(SOLVED_ROWS)
        board = MinConflictsBoard(NQueensProblem(4), rows)
        rows[0] = 0
        self.assertEqual(board.rows, SOLVED_ROWS)
        for column, row in ((-1, 0), (4, 0), (0, -1), (0, 4)):
            with self.subTest(column=column, row=row), self.assertRaises(ValueError):
                board.move(column, row)
        for column, row in ((True, 0), (0, False), (0, 1.0)):
            with self.subTest(column=column, row=row), self.assertRaises(TypeError):
                board.move(column, row)
        self.assertEqual(board.rows, SOLVED_ROWS)


class MinConflictsTests(unittest.TestCase):
    def test_valid_initial_state_needs_no_update_even_with_zero_budget(self):
        for max_steps in (0, 10):
            with self.subTest(max_steps=max_steps):
                result = MinConflictsSolver(
                    NQueensProblem(4), seed=0, max_steps=max_steps, initial_state=SOLVED_ROWS
                ).solve()
                self.assertEqual(result.status, SolveStatus.SAT)
                self.assertEqual(result.statistics["steps"], 0)
                self.assertEqual(result.statistics["moves"], 0)
                self.assertEqual(result.statistics["final_conflicting_pairs"], 0)
                self.assertTrue(SolutionValidator(NQueensProblem(4)).validate(result.solution))

    def test_invalid_initial_state_with_zero_budget_is_limit_reached(self):
        result = MinConflictsSolver(
            NQueensProblem(4), seed=0, max_steps=0, initial_state=(0, 0, 0, 0)
        ).solve()
        self.assertEqual(result.status, SolveStatus.LIMIT_REACHED)
        self.assertIsNone(result.solution)
        self.assertEqual(result.statistics["steps"], 0)
        self.assertEqual(result.statistics["final_conflicting_pairs"], 6)

    def test_solution_on_last_allowed_update_is_found(self):
        result = MinConflictsSolver(
            NQueensProblem(4), seed=0, max_steps=1, initial_state=(1, 3, 0, 0)
        ).solve()
        self.assertEqual(result.status, SolveStatus.SAT)
        self.assertEqual(result.statistics["steps"], 1)
        self.assertEqual(result.statistics["moves"], 1)
        self.assertEqual(result.statistics["final_state"], str(SOLVED_ROWS))

    def test_equal_seed_and_configuration_reproduce_result(self):
        solver = MinConflictsSolver(NQueensProblem(8), seed=42, max_steps=1000)
        first = solver.solve()
        second = solver.solve()
        self.assertEqual(first.status, SolveStatus.SAT)
        self.assertTrue(SolutionValidator(NQueensProblem(8)).validate(first.solution))
        self.assertEqual(first.status, second.status)
        self.assertEqual(first.solution, second.solution)
        self.assertEqual(
            {k: v for k, v in first.statistics.items() if k != "total_seconds"},
            {k: v for k, v in second.statistics.items() if k != "total_seconds"},
        )

    def test_rng_is_private_and_initial_rows_are_independent_draws(self):
        global_state = random.getstate()
        try:
            solver = MinConflictsSolver(NQueensProblem(4), seed=5, max_steps=0)
            first = solver.solve()
            self.assertEqual(random.getstate(), global_state)
            expected_rng = random.Random(5)
            expected_rows = tuple(expected_rng.randrange(4) for _ in range(4))
            self.assertEqual(first.statistics["initial_state"], str(expected_rows))
            random.seed(999)
            for _ in range(20):
                random.random()
            second = solver.solve()
            self.assertEqual(first.statistics["initial_state"], second.statistics["initial_state"])
            self.assertEqual(first.status, second.status)
        finally:
            random.setstate(global_state)

    def test_selection_uses_all_conflicted_queens_and_minimum_row_ties(self):
        with patch(f"{MODULE}.Random") as rng_constructor:
            rng = rng_constructor.return_value
            rng.choice.side_effect = [0, 2]
            result = MinConflictsSolver(
                NQueensProblem(4), seed=7, max_steps=1, initial_state=(0, 0, 0, 0)
            ).solve()
            rng_constructor.assert_called_once_with(7)
            self.assertEqual(rng.choice.call_args_list, [call([0, 1, 2, 3]), call([1, 2, 3])])
            self.assertEqual(result.statistics["final_state"], "(2, 0, 0, 0)")
            self.assertEqual(result.status, SolveStatus.LIMIT_REACHED)

    def test_same_row_assignment_counts_as_step_and_there_is_no_restart(self):
        with patch(f"{MODULE}.Random") as rng_constructor:
            rng = rng_constructor.return_value
            rng.randrange.side_effect = [0, 0]
            rng.choice.return_value = 0
            result = MinConflictsSolver(NQueensProblem(2), seed=1, max_steps=3).solve()
            self.assertEqual(rng.randrange.call_count, 2)
            self.assertEqual(rng.choice.call_count, 6)
            self.assertEqual(result.statistics["steps"], 3)
            self.assertEqual(result.statistics["moves"], 0)
            self.assertEqual(result.status, SolveStatus.LIMIT_REACHED)

    def test_n2_and_n3_never_claim_unsat(self):
        for n in (2, 3):
            with self.subTest(n=n):
                result = MinConflictsSolver(NQueensProblem(n), seed=0, max_steps=20).solve()
                self.assertEqual(result.status, SolveStatus.LIMIT_REACHED)
                self.assertEqual(result.statistics["steps"], 20)
                self.assertIsNone(result.solution)

    def test_singleton_random_initialization_succeeds_without_updates(self):
        result = MinConflictsSolver(NQueensProblem(1), seed=1, max_steps=0).solve()
        self.assertEqual(result.status, SolveStatus.SAT)
        self.assertEqual(result.solution, ((0, 0),))
        self.assertEqual(result.statistics["steps"], 0)

    def test_validator_rejection_prevents_success_initial_and_after_update(self):
        for rows, max_steps in ((SOLVED_ROWS, 0), ((1, 3, 0, 0), 1)):
            with self.subTest(rows=rows), patch(f"{MODULE}.SolutionValidator") as validator:
                validator.return_value.validate.return_value = False
                result = MinConflictsSolver(
                    NQueensProblem(4), seed=0, max_steps=max_steps, initial_state=rows
                ).solve()
                self.assertEqual(result.status, SolveStatus.ERROR)
                self.assertIsNone(result.solution)
                validator.return_value.validate.assert_called_once()
                self.assertIn("independent validation", result.message)

    def test_invalid_configuration_is_rejected_before_search(self):
        problem = NQueensProblem(4)
        for max_steps in (True, 1.0, "1", None):
            with self.subTest(max_steps=max_steps), self.assertRaises(TypeError):
                MinConflictsSolver(problem, max_steps=max_steps)
        with self.assertRaises(ValueError):
            MinConflictsSolver(problem, max_steps=-1)
        for seed in (True, 1.0, "1"):
            with self.subTest(seed=seed), self.assertRaises(TypeError):
                MinConflictsSolver(problem, seed=seed)
        for rows in ((), (0, 1), (0, 1, 2, 4), (0, 1, 2, -1)):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                MinConflictsSolver(problem, initial_state=rows)
        for rows in ((True, 1, 2, 3), (0, 1.0, 2, 3), (0, "1", 2, 3)):
            with self.subTest(rows=rows), self.assertRaises(TypeError):
                MinConflictsSolver(problem, initial_state=rows)

    def test_caller_initial_state_is_copied_and_time_is_measured(self):
        rows = list(SOLVED_ROWS)
        solver = MinConflictsSolver(NQueensProblem(4), initial_state=rows, max_steps=0)
        rows[0] = 0
        result = solver.solve()
        self.assertEqual(result.status, SolveStatus.SAT)
        self.assertEqual(solver.initial_state, SOLVED_ROWS)
        self.assertGreaterEqual(result.elapsed_seconds, 0)
        self.assertEqual(result.elapsed_seconds, result.statistics["total_seconds"])


class MinConflictsCLITests(unittest.TestCase):
    def test_module_cli_solution_on_last_update(self):
        completed = subprocess.run(
            [sys.executable, "-m", "source.task1_nqueens", "4", "--method", "min-conflicts",
             "--seed", "0", "--max-steps", "1", "--initial-state", "1,3,0,0"],
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True, text=True, timeout=30,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Status: SAT\n", completed.stdout)
        self.assertIn("steps: 1\n", completed.stdout)
        # rows[column] is not the column-per-row representation used by SAT fixtures.
        self.assertIn(". . Q .\nQ . . .\n. . . Q\n. Q . .\n", completed.stdout)

    def test_zero_budget_cli_limit_has_no_solution(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            exit_code = main(["4", "--method", "min-conflicts", "--max-steps", "0",
                              "--initial-state", "0,0,0,0"])
        self.assertEqual(exit_code, 3)
        self.assertIn("Status: LIMIT_REACHED", output.getvalue())
        self.assertNotIn("Queens (row, column", output.getvalue())

    def test_invalid_cli_options_are_rejected(self):
        argument_lists = [
            ["4", "--seed", "0"],
            ["4", "--max-steps", "0"],
            ["4", "--initial-state", "1,3,0,2"],
            ["4", "--method", "min-conflicts", "--max-steps", "-1"],
            ["4", "--method", "min-conflicts", "--initial-state", "1,2"],
            ["4", "--method", "min-conflicts", "--initial-state", "0,1,2,4"],
            ["4", "--method", "min-conflicts", "--initial-state", "0,1,x,2"],
        ]
        for arguments in argument_lists:
            with self.subTest(arguments=arguments), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    main(arguments)
                self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
