"""Glucose3 adapter with explicit timing boundaries and native resource cleanup."""

from dataclasses import dataclass
from time import perf_counter

from pysat.solvers import Glucose3

from .cnf import CNFEncoder
from .models import NQueensProblem, SolveResult, SolveStatus, Statistic
from .validator import SolutionValidator


@dataclass(frozen=True)
class SATNQueensSolver:
    problem: NQueensProblem

    def solve(self) -> SolveResult:
        """Run one unrestricted solve. Total includes cleanup, excludes CLI I/O.

        Phase times measure elapsed wall time using perf_counter. Total starts
        here and ends after native solver deletion, before packing SolveResult.
        Errors preserve completed/attempted phase times; unstarted phases have
        no timing key. None (unknown) is never reported as UNSAT.
        """
        total_start = perf_counter()
        statistics: dict[str, Statistic] = {}
        status = SolveStatus.ERROR
        solution = None
        message = None
        solver = None
        try:
            phase_start = perf_counter()
            try:
                encoder = CNFEncoder(self.problem)
                cnf = encoder.encode()
            finally:
                statistics["cnf_generation_seconds"] = perf_counter() - phase_start
            statistics["num_variables"] = cnf.num_variables
            statistics.update({f"clauses_{name}": count for name, count in cnf.clause_counts.items()})
            statistics["clauses_total"] = len(cnf.clauses)

            phase_start = perf_counter()
            try:
                # Separate construction and loading so loading errors still
                # leave a reference that can be deleted in the outer finally.
                solver = Glucose3()
                solver.append_formula(cnf.clauses)
            finally:
                statistics["solver_initialization_seconds"] = perf_counter() - phase_start

            phase_start = perf_counter()
            try:
                outcome = solver.solve()
            finally:
                statistics["solve_seconds"] = perf_counter() - phase_start
            statistics.update({f"solver_{name}": value for name, value in solver.accum_stats().items()})
            if outcome is True:
                model = solver.get_model()
                if model is None:
                    raise ValueError("SAT solver returned no model")
                solution = encoder.decode_model(model)
                if not SolutionValidator(self.problem).validate(solution):
                    raise ValueError("SAT model failed independent solution validation")
                status = SolveStatus.SAT
            elif outcome is False:
                status = SolveStatus.UNSAT
            elif outcome is None:
                status = SolveStatus.LIMIT_REACHED
                message = "Solver returned unknown; unsatisfiability is not established"
            else:
                raise ValueError("unexpected solver outcome")
        except Exception as error:
            status = SolveStatus.ERROR
            solution = None
            message = f"{type(error).__name__}: {error}"
        finally:
            if solver is not None:
                try:
                    solver.delete()
                except Exception as error:
                    status = SolveStatus.ERROR
                    solution = None
                    cleanup_message = f"Solver cleanup failed: {type(error).__name__}: {error}"
                    message = f"{message}; {cleanup_message}" if message else cleanup_message

        elapsed_seconds = perf_counter() - total_start
        statistics["total_seconds"] = elapsed_seconds
        return SolveResult(status, elapsed_seconds, solution, statistics, message)
