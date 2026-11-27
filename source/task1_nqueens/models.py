"""Shared data contracts for future N-Queens solvers."""

from dataclasses import dataclass, field
from enum import Enum
import math
from types import MappingProxyType
from typing import Mapping


Position = tuple[int, int]
Statistic = int | float | str | bool


@dataclass(frozen=True)
class NQueensProblem:
    """An N x N board; coordinates use zero-based (row, column) pairs."""

    n: int

    def __post_init__(self) -> None:
        if isinstance(self.n, bool) or not isinstance(self.n, int):
            raise TypeError("n must be an integer, excluding bool")
        if self.n < 1:
            raise ValueError("n must be positive")


class SolveStatus(str, Enum):
    """A search limit does not establish that a problem is unsatisfiable."""

    SAT = "SAT"
    UNSAT = "UNSAT"
    LIMIT_REACHED = "LIMIT_REACHED"
    ERROR = "ERROR"


@dataclass(frozen=True)
class SolveResult:
    """Solver outcome; only SAT carries a candidate solution.

    elapsed_seconds is measured by a future solver, not inferred here.
    Statistics start empty and must contain only actual measurements.
    Board-specific correctness is checked separately by SolutionValidator.
    """

    status: SolveStatus
    elapsed_seconds: float
    solution: tuple[Position, ...] | None = None
    statistics: Mapping[str, Statistic] = field(default_factory=dict)
    message: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, SolveStatus):
            raise TypeError("status must be a SolveStatus")
        if isinstance(self.elapsed_seconds, bool) or not isinstance(
            self.elapsed_seconds, (int, float)
        ):
            raise TypeError("elapsed_seconds must be a number")
        if not math.isfinite(self.elapsed_seconds) or self.elapsed_seconds < 0:
            raise ValueError("elapsed_seconds must be finite and non-negative")
        if self.status is SolveStatus.SAT:
            if self.solution is None:
                raise ValueError("SAT requires a candidate solution")
            # Copy caller-owned containers to keep this outcome stable.
            object.__setattr__(
                self, "solution", tuple(tuple(position) for position in self.solution)
            )
        elif self.solution is not None:
            raise ValueError("only SAT may carry a solution")
        object.__setattr__(self, "statistics", MappingProxyType(dict(self.statistics)))
