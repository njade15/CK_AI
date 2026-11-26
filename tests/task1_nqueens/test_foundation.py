import io
import unittest

from source.task1_nqueens import (
    NQueensProblem,
    SolutionValidator,
    SolveResult,
    SolveStatus,
    print_board,
    render_board,
)


N4_SOLUTION = ((0, 1), (1, 3), (2, 0), (3, 2))


class ProblemTests(unittest.TestCase):
    def test_positive_sizes_are_valid_even_when_no_solution_exists(self):
        for n in (1, 2, 3, 4, 100):
            with self.subTest(n=n):
                self.assertEqual(NQueensProblem(n).n, n)

    def test_nonpositive_sizes_are_rejected(self):
        for n in (0, -1, -100):
            with self.subTest(n=n), self.assertRaises(ValueError):
                NQueensProblem(n)

    def test_noninteger_sizes_and_booleans_are_rejected(self):
        for n in (True, False, 4.0, 4.5, "4", None, [], float("nan")):
            with self.subTest(n=n), self.assertRaises(TypeError):
                NQueensProblem(n)


class ValidatorTests(unittest.TestCase):
    def setUp(self):
        self.validator = SolutionValidator(NQueensProblem(4))

    def test_known_n4_solution(self):
        self.assertTrue(self.validator.validate(N4_SOLUTION))

    def test_other_n4_solution_and_unordered_input(self):
        self.assertTrue(self.validator.validate(((3, 1), (1, 0), (0, 2), (2, 3))))

    def test_single_queen_board(self):
        self.assertTrue(SolutionValidator(NQueensProblem(1)).validate(((0, 0),)))

    def test_list_coordinates_and_generator_are_supported(self):
        self.assertTrue(self.validator.validate([list(p) for p in N4_SOLUTION]))
        self.assertTrue(self.validator.validate(p for p in N4_SOLUTION))

    def test_duplicate_square(self):
        self.assertFalse(self.validator.validate(((0, 1), (0, 1), (2, 0), (3, 2))))

    def test_duplicate_row(self):
        self.assertFalse(self.validator.validate(((0, 1), (0, 3), (2, 0), (3, 2))))

    def test_duplicate_column(self):
        self.assertFalse(self.validator.validate(((0, 1), (1, 1), (2, 0), (3, 2))))

    def test_descending_diagonal(self):
        # Distinct rows and columns isolate the diagonal constraint.
        self.assertFalse(self.validator.validate(((0, 0), (1, 1), (2, 2), (3, 3))))

    def test_ascending_diagonal(self):
        self.assertFalse(self.validator.validate(((0, 3), (1, 2), (2, 1), (3, 0))))

    def test_wrong_queen_count(self):
        for queens in ((), N4_SOLUTION[:3], N4_SOLUTION + ((0, 0),)):
            with self.subTest(queens=queens):
                self.assertFalse(self.validator.validate(queens))

    def test_out_of_range_coordinates(self):
        for position in ((-1, 1), (4, 1), (0, -1), (0, 4)):
            with self.subTest(position=position):
                self.assertFalse(self.validator.validate((position,) + N4_SOLUTION[1:]))

    def test_malformed_coordinates(self):
        for position in ((0,), (0, 1, 2), (True, 1), (0, False), (0.0, 1),
                         (0, "1"), ([], 1), None, 1):
            with self.subTest(position=position):
                self.assertFalse(self.validator.validate((position,) + N4_SOLUTION[1:]))
        self.assertFalse(self.validator.validate(None))


class SolveResultTests(unittest.TestCase):
    def test_sat_candidate_and_measured_statistics(self):
        # These are test fixtures for the data contract, not benchmark results.
        result = SolveResult(SolveStatus.SAT, 0.25, N4_SOLUTION, {"steps": 2})
        self.assertEqual(result.solution, N4_SOLUTION)
        self.assertEqual(result.elapsed_seconds, 0.25)
        self.assertEqual(result.statistics["steps"], 2)

    def test_unsat_limit_and_error_remain_distinct(self):
        statuses = (SolveStatus.UNSAT, SolveStatus.LIMIT_REACHED, SolveStatus.ERROR)
        self.assertEqual(len(set(statuses)), 3)
        for status in statuses:
            with self.subTest(status=status):
                result = SolveResult(status, 0.0, message="test fixture")
                self.assertEqual(result.status, status)
                self.assertIsNone(result.solution)
                self.assertEqual(dict(result.statistics), {})

    def test_sat_requires_solution(self):
        with self.assertRaises(ValueError):
            SolveResult(SolveStatus.SAT, 0.0)

    def test_non_sat_cannot_claim_solution(self):
        for status in (SolveStatus.UNSAT, SolveStatus.LIMIT_REACHED, SolveStatus.ERROR):
            with self.subTest(status=status), self.assertRaises(ValueError):
                SolveResult(status, 0.0, N4_SOLUTION)

    def test_elapsed_time_must_be_finite_and_nonnegative(self):
        for elapsed in (-0.1, float("nan"), float("inf"), -float("inf")):
            with self.subTest(elapsed=elapsed), self.assertRaises(ValueError):
                SolveResult(SolveStatus.ERROR, elapsed)

    def test_elapsed_time_rejects_wrong_types(self):
        for elapsed in (True, "0.1", None):
            with self.subTest(elapsed=elapsed), self.assertRaises(TypeError):
                SolveResult(SolveStatus.ERROR, elapsed)

    def test_status_requires_enum(self):
        with self.assertRaises(TypeError):
            SolveResult("SAT", 0.0, N4_SOLUTION)

    def test_caller_mutations_do_not_change_result(self):
        queens = [list(position) for position in N4_SOLUTION]
        statistics = {"steps": 2}
        result = SolveResult(SolveStatus.SAT, 0.0, queens, statistics)
        queens[0][0] = 99
        statistics["steps"] = 99
        self.assertEqual(result.solution, N4_SOLUTION)
        self.assertEqual(result.statistics["steps"], 2)
        with self.assertRaises(TypeError):
            result.statistics["steps"] = 3


class DisplayTests(unittest.TestCase):
    def test_n4_board_orientation(self):
        self.assertEqual(
            render_board(NQueensProblem(4), N4_SOLUTION),
            ". Q . .\n. . . Q\nQ . . .\n. . Q .",
        )

    def test_single_queen_board(self):
        self.assertEqual(render_board(NQueensProblem(1), ((0, 0),)), "Q")

    def test_print_to_text_stream(self):
        stream = io.StringIO()
        print_board(NQueensProblem(4), iter(N4_SOLUTION), stream=stream)
        self.assertEqual(stream.getvalue(), ". Q . .\n. . . Q\nQ . . .\n. . Q .\n")

    def test_invalid_solution_is_not_rendered(self):
        for queens in (N4_SOLUTION[:3], ((4, 1),) + N4_SOLUTION[1:], None):
            with self.subTest(queens=queens), self.assertRaises(ValueError):
                render_board(NQueensProblem(4), queens)


if __name__ == "__main__":
    unittest.main()
