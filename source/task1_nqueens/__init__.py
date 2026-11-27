"""N-Queens domain models, validation, and terminal display."""

from .display import print_board, render_board
from .cnf import CNFEncoder, EncodedCNF
from .models import NQueensProblem, Position, SolveResult, SolveStatus
from .min_conflicts import (
    MaxConflictedSelector,
    MinConflictsBoard,
    MinConflictsSolver,
    RandomConflictedSelector,
)
from .sat_solver import SATNQueensSolver
from .validator import SolutionValidator

__all__ = [
    "CNFEncoder",
    "EncodedCNF",
    "NQueensProblem",
    "MinConflictsBoard",
    "MinConflictsSolver",
    "MaxConflictedSelector",
    "RandomConflictedSelector",
    "Position",
    "SolveResult",
    "SolveStatus",
    "SolutionValidator",
    "SATNQueensSolver",
    "print_board",
    "render_board",
]
