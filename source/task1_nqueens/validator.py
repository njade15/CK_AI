"""Independent validation using queen coordinates, without a search algorithm."""

from dataclasses import dataclass
from typing import Iterable

from .models import NQueensProblem, Position


@dataclass(frozen=True)
class SolutionValidator:
    problem: NQueensProblem

    def validate(self, queens: Iterable[Position]) -> bool:
        """Return whether queens form a complete solution for this board.

        Malformed coordinates return False. Input iterables are consumed once.
        Rows, columns, and diagonals are checked in O(N) time and space.
        """
        try:
            positions = tuple(tuple(queen) for queen in queens)
        except TypeError:
            return False
        if len(positions) != self.problem.n:
            return False

        occupied: set[Position] = set()
        rows: set[int] = set()
        columns: set[int] = set()
        descending: set[int] = set()
        ascending: set[int] = set()
        for position in positions:
            if len(position) != 2:
                return False
            row, column = position
            if any(
                isinstance(value, bool) or not isinstance(value, int)
                for value in position
            ):
                return False
            if not (0 <= row < self.problem.n and 0 <= column < self.problem.n):
                return False
            if (
                position in occupied
                or row in rows
                or column in columns
                or row - column in descending
                or row + column in ascending
            ):
                return False
            occupied.add(position)
            rows.add(row)
            columns.add(column)
            descending.add(row - column)
            ascending.add(row + column)
        return True
