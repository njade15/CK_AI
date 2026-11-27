"""Plain ASCII terminal display for complete, validated solutions."""

from typing import Iterable, TextIO

from .models import NQueensProblem, Position
from .validator import SolutionValidator


def render_board(problem: NQueensProblem, queens: Iterable[Position]) -> str:
    """Render row 0 at the top, using Q for a queen and . for an empty cell."""
    try:
        positions = tuple(tuple(queen) for queen in queens)
    except TypeError as error:
        raise ValueError("queens must contain coordinate pairs") from error
    if not SolutionValidator(problem).validate(positions):
        raise ValueError("queens must be a complete valid solution")
    occupied = set(positions)
    return "\n".join(
        " ".join(
            "Q" if (row, column) in occupied else "."
            for column in range(problem.n)
        )
        for row in range(problem.n)
    )


def print_board(
    problem: NQueensProblem,
    queens: Iterable[Position],
    *,
    stream: TextIO | None = None,
) -> None:
    """Print to stdout by default, or to the supplied text stream."""
    print(render_board(problem, queens), file=stream)
