"""Command-line entry point for a single N-Queens SAT solve."""

import argparse
from typing import Sequence

from .display import print_board
from .models import NQueensProblem, SolveStatus
from .sat_solver import SATNQueensSolver


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Solve N-Queens using pairwise CNF and Glucose3")
    parser.add_argument("n", type=int, help="positive board size N")
    args = parser.parse_args(argv)
    try:
        problem = NQueensProblem(args.n)
    except (TypeError, ValueError) as error:
        parser.error(str(error))

    result = SATNQueensSolver(problem).solve()
    print(f"N: {problem.n}")
    print(f"Status: {result.status.value}")
    for name, value in result.statistics.items():
        formatted = f"{value:.9f}" if isinstance(value, float) else str(value)
        print(f"{name}: {formatted}")
    if result.message:
        print(f"Message: {result.message}")
    if result.status is SolveStatus.SAT:
        print(f"Queens (row, column; zero-based): {result.solution}")
        print_board(problem, result.solution)
    if result.status is SolveStatus.ERROR:
        return 1
    if result.status is SolveStatus.LIMIT_REACHED:
        return 3
    return 0
