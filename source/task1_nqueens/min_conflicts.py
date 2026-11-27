"""Shared Min-Conflicts loop with interchangeable variable selection."""

from dataclasses import dataclass
from random import Random
from time import perf_counter
from typing import Iterable, Sequence

from .models import NQueensProblem, Position, SolveResult, SolveStatus, Statistic
from .validator import SolutionValidator


class MinConflictsBoard:
    """Mutable column-to-row assignment with row and diagonal counters."""

    def __init__(self, problem: NQueensProblem, rows: Iterable[int]) -> None:
        self.problem = problem
        self._rows = list(rows)
        if len(self._rows) != problem.n:
            raise ValueError("initial_state must contain exactly N rows")
        for row in self._rows:
            self._check_coordinate(row)
        self._row_counts = [0] * problem.n
        self._descending_counts = [0] * (2 * problem.n - 1)
        self._ascending_counts = [0] * (2 * problem.n - 1)
        for column, row in enumerate(self._rows):
            self._adjust(column, row, 1)

    def _check_coordinate(self, value: int) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError("rows and columns must be integers, excluding bool")
        if not 0 <= value < self.problem.n:
            raise ValueError("row or column outside board")

    def _adjust(self, column: int, row: int, delta: int) -> None:
        self._row_counts[row] += delta
        self._descending_counts[row - column + self.problem.n - 1] += delta
        self._ascending_counts[row + column] += delta

    @property
    def rows(self) -> tuple[int, ...]:
        return tuple(self._rows)

    def conflicts(self, column: int, row: int | None = None) -> int:
        """Count other attacking queens if column's queen were at row.

        With row omitted, score its current square. Each other queen can share
        at most one counted line because each column contains exactly one queen.
        """
        self._check_coordinate(column)
        current_row = self._rows[column]
        target_row = current_row if row is None else row
        self._check_coordinate(target_row)
        count = (
            self._row_counts[target_row]
            + self._descending_counts[target_row - column + self.problem.n - 1]
            + self._ascending_counts[target_row + column]
        )
        # Self appears in all three counters only when scoring its current row.
        return count - 3 if target_row == current_row else count

    def conflicted_columns(self) -> list[int]:
        return [column for column in range(self.problem.n) if self.conflicts(column) > 0]

    @property
    def conflicting_pairs(self) -> int:
        return sum(self.conflicts(column) for column in range(self.problem.n)) // 2

    def move(self, column: int, row: int) -> None:
        self._check_coordinate(column)
        self._check_coordinate(row)
        self._adjust(column, self._rows[column], -1)
        self._rows[column] = row
        self._adjust(column, row, 1)

    def positions(self) -> tuple[Position, ...]:
        return tuple((row, column) for column, row in enumerate(self._rows))


class RandomConflictedSelector:
    """Uniformly choose from the loop's current conflicted columns."""

    def select_column(
        self, board: MinConflictsBoard, conflicted: Sequence[int], rng: Random
    ) -> int | None:
        return rng.choice(conflicted) if conflicted else None


class MaxConflictedSelector:
    """Choose a maximum-conflict queen, breaking ties uniformly at random."""

    def select_column(
        self, board: MinConflictsBoard, conflicted: Sequence[int], rng: Random
    ) -> int | None:
        if not conflicted:
            return None
        scored = [(column, board.conflicts(column)) for column in conflicted]
        maximum = max(score for _, score in scored)
        candidates = [column for column, score in scored if score == maximum]
        return rng.choice(candidates)


_VARIABLE_SELECTORS = {
    "random_conflicted": RandomConflictedSelector(),
    "max_conflicted": MaxConflictedSelector(),
}


@dataclass(frozen=True)
class MinConflictsSolver:
    problem: NQueensProblem
    seed: int | None = None
    max_steps: int = 10000
    initial_state: tuple[int, ...] | None = None
    strategy: str = "random_conflicted"

    def __post_init__(self) -> None:
        if not isinstance(self.strategy, str):
            raise TypeError("strategy must be a string")
        if self.strategy not in _VARIABLE_SELECTORS:
            raise ValueError("strategy must be random_conflicted or max_conflicted")
        if isinstance(self.max_steps, bool) or not isinstance(self.max_steps, int):
            raise TypeError("max_steps must be an integer, excluding bool")
        if self.max_steps < 0:
            raise ValueError("max_steps must be non-negative")
        if self.seed is not None and (
            isinstance(self.seed, bool) or not isinstance(self.seed, int)
        ):
            raise TypeError("seed must be an integer or None, excluding bool")
        if self.initial_state is not None:
            rows = tuple(self.initial_state)
            MinConflictsBoard(self.problem, rows)  # Validate before starting search.
            object.__setattr__(self, "initial_state", rows)

    def solve(self) -> SolveResult:
        """Check before moving and after every update, including the last one.

        One step is one assignment after selecting a conflicted column and a
        minimum-conflict row. Assigning the current row still consumes a step.
        A fresh private RNG per call makes repeated seeded calls reproducible.
        """
        start = perf_counter()
        statistics: dict[str, Statistic] = {
            "strategy": self.strategy,
            "seed": self.seed if self.seed is not None else "system",
            "max_steps": self.max_steps,
            "steps": 0,
            "moves": 0,
        }
        status = SolveStatus.ERROR
        solution = None
        message = None
        try:
            selector = _VARIABLE_SELECTORS[self.strategy]
            rng = Random(self.seed)
            rows = self.initial_state
            if rows is None:
                rows = tuple(rng.randrange(self.problem.n) for _ in range(self.problem.n))
            board = MinConflictsBoard(self.problem, rows)
            statistics["initial_state"] = str(board.rows)
            statistics["initial_conflicting_pairs"] = board.conflicting_pairs
            for step in range(self.max_steps + 1):
                conflicted = board.conflicted_columns()
                if not conflicted:
                    candidate = board.positions()
                    if not SolutionValidator(self.problem).validate(candidate):
                        raise ValueError("Min-Conflicts candidate failed independent validation")
                    solution = candidate
                    status = SolveStatus.SAT
                    break
                if step == self.max_steps:
                    status = SolveStatus.LIMIT_REACHED
                    message = "Step budget exhausted; unsatisfiability is not established"
                    break
                column = selector.select_column(board, conflicted, rng)
                if column is None:
                    raise ValueError("selector returned no column for a conflicted board")
                scores = [board.conflicts(column, row) for row in range(self.problem.n)]
                minimum = min(scores)
                best_rows = [row for row, score in enumerate(scores) if score == minimum]
                row = rng.choice(best_rows)
                changed = row != board.rows[column]
                board.move(column, row)
                statistics["steps"] += 1
                statistics["moves"] += int(changed)
            statistics["final_state"] = str(board.rows)
            statistics["final_conflicting_pairs"] = board.conflicting_pairs
        except Exception as error:
            status = SolveStatus.ERROR
            solution = None
            message = f"{type(error).__name__}: {error}"
        elapsed_seconds = perf_counter() - start
        statistics["total_seconds"] = elapsed_seconds
        return SolveResult(status, elapsed_seconds, solution, statistics, message)
