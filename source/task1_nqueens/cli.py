"""Command-line entry point for one SAT or Min-Conflicts solve."""

import argparse
from typing import Sequence

from .display import print_board
from .models import NQueensProblem, SolveStatus
from .min_conflicts import MinConflictsSolver
from .sat_solver import SATNQueensSolver


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Solve N-Queens using SAT or baseline Min-Conflicts")
    parser.add_argument("n", type=int, help="positive board size N")
    parser.add_argument("--method", choices=("sat", "min-conflicts"), default="sat")
    parser.add_argument("--seed", type=int, help="Min-Conflicts private RNG seed")
    parser.add_argument("--max-steps", type=int, help="Min-Conflicts update budget (default: 10000)")
    parser.add_argument("--initial-state", help="Min-Conflicts comma-separated rows, one per column")
    args = parser.parse_args(argv)
    try:
        problem = NQueensProblem(args.n)
        if args.method == "sat":
            if any(value is not None for value in (args.seed, args.max_steps, args.initial_state)):
                parser.error("--seed, --max-steps and --initial-state require --method min-conflicts")
            solver = SATNQueensSolver(problem)
        else:
            initial_state = None
            if args.initial_state is not None:
                initial_state = tuple(int(row) for row in args.initial_state.split(","))
            solver = MinConflictsSolver(
                problem,
                seed=args.seed,
                max_steps=args.max_steps if args.max_steps is not None else 10000,
                initial_state=initial_state,
            )
    except (TypeError, ValueError) as error:
        parser.error(str(error))

    result = solver.solve()
    print(f"N: {problem.n}")
    print(f"Method: {args.method}")
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
