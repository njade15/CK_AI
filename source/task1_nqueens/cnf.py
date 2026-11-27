"""Pairwise CNF encoding with one Boolean variable per board square."""

from dataclasses import dataclass
from itertools import combinations
from types import MappingProxyType
from typing import Iterable, Mapping

from .models import NQueensProblem, Position


Clause = tuple[int, ...]


@dataclass(frozen=True)
class EncodedCNF:
    num_variables: int
    clauses: tuple[Clause, ...]
    clause_counts: Mapping[str, int]


@dataclass(frozen=True)
class CNFEncoder:
    problem: NQueensProblem

    def variable_id(self, row: int, column: int) -> int:
        """Map a zero-based square to a positive DIMACS variable identifier."""
        for coordinate in (row, column):
            if isinstance(coordinate, bool) or not isinstance(coordinate, int):
                raise TypeError("coordinates must be integers, excluding bool")
            if not 0 <= coordinate < self.problem.n:
                raise ValueError("coordinate outside board")
        return row * self.problem.n + column + 1

    def decode_variable(self, identifier: int) -> Position:
        """Invert a positive identifier; signed literals are not identifiers."""
        if isinstance(identifier, bool) or not isinstance(identifier, int):
            raise TypeError("identifier must be an integer, excluding bool")
        if not 1 <= identifier <= self.problem.n ** 2:
            raise ValueError("identifier outside board variables")
        return divmod(identifier - 1, self.problem.n)

    def decode_model(self, model: Iterable[int]) -> tuple[Position, ...]:
        """Decode a complete signed model; reject missing or repeated variables."""
        assignments: dict[int, bool] = {}
        for literal in model:
            if isinstance(literal, bool) or not isinstance(literal, int):
                raise TypeError("model literals must be integers, excluding bool")
            identifier = abs(literal)
            self.decode_variable(identifier)
            if identifier in assignments:
                raise ValueError("model contains a repeated variable")
            assignments[identifier] = literal > 0
        if len(assignments) != self.problem.n ** 2:
            raise ValueError("model must assign every board variable")
        return tuple(
            self.decode_variable(identifier)
            for identifier in sorted(assignments)
            if assignments[identifier]
        )

    @staticmethod
    def _at_most_one(variables: Iterable[int]) -> list[Clause]:
        return [(-left, -right) for left, right in combinations(variables, 2)]

    def encode(self) -> EncodedCNF:
        """Generate only row exactly-one and column/diagonal at-most-one."""
        n = self.problem.n
        groups: dict[str, list[Clause]] = {
            "row_at_least_one": [],
            "row_at_most_one": [],
            "column_at_most_one": [],
            "descending_diagonal_at_most_one": [],
            "ascending_diagonal_at_most_one": [],
        }
        descending: dict[int, list[int]] = {}
        ascending: dict[int, list[int]] = {}
        for row in range(n):
            row_variables = tuple(self.variable_id(row, column) for column in range(n))
            groups["row_at_least_one"].append(row_variables)
            groups["row_at_most_one"].extend(self._at_most_one(row_variables))
            for column, identifier in enumerate(row_variables):
                descending.setdefault(row - column, []).append(identifier)
                ascending.setdefault(row + column, []).append(identifier)
        for column in range(n):
            groups["column_at_most_one"].extend(
                self._at_most_one(self.variable_id(row, column) for row in range(n))
            )
        for diagonal in descending.values():
            groups["descending_diagonal_at_most_one"].extend(self._at_most_one(diagonal))
        for diagonal in ascending.values():
            groups["ascending_diagonal_at_most_one"].extend(self._at_most_one(diagonal))

        # All counts come from generated clauses, not from a closed-form formula.
        return EncodedCNF(
            num_variables=n * n,
            clauses=tuple(clause for group in groups.values() for clause in group),
            clause_counts=MappingProxyType({name: len(group) for name, group in groups.items()}),
        )
