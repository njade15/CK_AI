"""Sequential reproducible trials in killable spawn processes; never drop failures."""

import argparse
import csv
from datetime import datetime, timezone
from importlib.metadata import distributions
import json
import math
import multiprocessing as mp
import os
from pathlib import Path
import platform
from random import Random
import subprocess
import sys
from time import perf_counter

from .models import NQueensProblem
from .validator import SolutionValidator


ROOT = Path(__file__).resolve().parents[2]
STRATEGIES = ("random_conflicted", "max_conflicted")
COUNT_FIELDS = [
    "num_variables", "clauses_row_at_least_one", "clauses_row_at_most_one",
    "clauses_column_at_most_one", "clauses_descending_diagonal_at_most_one",
    "clauses_ascending_diagonal_at_most_one", "clauses_total",
]
METRIC_FIELDS = COUNT_FIELDS + [
    "cnf_generation_seconds", "solver_initialization_seconds", "solve_seconds",
    "steps", "moves", "initial_conflicting_pairs", "final_conflicting_pairs",
    "solver_restarts", "solver_conflicts", "solver_decisions", "solver_propagations",
]
FIELDS = [
    "trial_id", "method", "strategy", "n", "repeat", "seed", "initial_state",
    "max_steps", "timeout_seconds", "status", "solver_status", "solution_valid",
    "solution", "message", "algorithm_total_seconds", "observed_wall_seconds",
    "source_commit", "working_tree_dirty",
] + METRIC_FIELDS


def validate_config(config):
    for key in ("sat_ns", "mc_ns"):
        if not isinstance(config[key], list) or not config[key]:
            raise ValueError(f"{key} must be a nonempty list")
        for n in config[key]:
            NQueensProblem(n)
        if len(set(config[key])) != len(config[key]):
            raise ValueError(f"{key} must not contain duplicates")
    for key in ("sat_repeats", "mc_max_steps"):
        value = config[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < (1 if key == "sat_repeats" else 0):
            raise ValueError(f"invalid {key}")
    seeds = config["mc_seeds"]
    if not isinstance(seeds, list) or not seeds or any(
        isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds
    ) or len(set(seeds)) != len(seeds):
        raise ValueError("mc_seeds must contain distinct integer seeds")
    for key in ("sat_timeout_seconds", "mc_timeout_seconds", "total_budget_seconds"):
        value = config[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{key} must be positive and finite")
    if config.get("restart") is not False:
        raise ValueError("this experiment requires restart=false")


def plan_trials(config):
    validate_config(config)
    trials = []
    for n in config["sat_ns"]:
        for repeat in range(config["sat_repeats"]):
            trials.append({"trial_id": f"sat-n{n}-r{repeat}", "method": "sat",
                           "strategy": "", "n": n, "repeat": repeat, "seed": None,
                           "initial_state": None, "max_steps": None,
                           "timeout_seconds": config["sat_timeout_seconds"]})
    for n in config["mc_ns"]:
        for repeat, seed in enumerate(config["mc_seeds"]):
            rng = Random(seed)
            initial = [rng.randrange(n) for _ in range(n)]
            # Alternate order without changing either solver's private RNG.
            order = STRATEGIES if repeat % 2 == 0 else STRATEGIES[::-1]
            for strategy in order:
                trials.append({"trial_id": f"mc-n{n}-r{repeat}-{strategy}", "method": "min-conflicts",
                               "strategy": strategy, "n": n, "repeat": repeat, "seed": seed,
                               "initial_state": initial.copy(), "max_steps": config["mc_max_steps"],
                               "timeout_seconds": config["mc_timeout_seconds"]})
    return trials


def _worker(sender, task):
    try:
        from .min_conflicts import MinConflictsSolver
        from .sat_solver import SATNQueensSolver

        problem = NQueensProblem(task["n"])
        if task["method"] == "sat":
            def progress(statistics):
                sender.send({"kind": "progress", "statistics": dict(statistics)})
            result = SATNQueensSolver(problem).solve(progress=progress)
        else:
            result = MinConflictsSolver(
                problem, seed=task["seed"], max_steps=task["max_steps"],
                initial_state=task["initial_state"].copy(), strategy=task["strategy"],
            ).solve()
        sender.send({"kind": "result", "status": result.status.value,
                     "solution": result.solution, "elapsed_seconds": result.elapsed_seconds,
                     "statistics": dict(result.statistics), "message": result.message})
    except Exception as error:
        sender.send({"kind": "result", "status": "ERROR", "solution": None,
                     "statistics": {}, "message": f"{type(error).__name__}: {error}"})
    finally:
        sender.close()


def execute_isolated(task, timeout_seconds, worker=_worker):
    """Deadline starts before spawn, stops waiting at deadline, then kills child.

    observed_wall_seconds also includes bounded process teardown. Complete phase
    snapshots survive timeout; no duration is invented for an interrupted phase.
    """
    context = mp.get_context("spawn")
    receiver, sender = context.Pipe(duplex=False)
    process = context.Process(target=worker, args=(sender, task))
    started = perf_counter()
    deadline = started + timeout_seconds
    statistics = {}
    payload = None
    timed_out = False
    try:
        process.start()
        sender.close()
        while True:
            remaining = deadline - perf_counter()
            if remaining <= 0:
                timed_out = True
                break
            if receiver.poll(min(remaining, 0.05)):
                try:
                    event = receiver.recv()
                except EOFError:
                    break
                statistics.update(event.get("statistics", {}))
                if event["kind"] == "result":
                    payload = event
                    break
            elif not process.is_alive():
                break
    except Exception as error:
        payload = {"kind": "result", "status": "ERROR", "solution": None,
                   "message": f"{type(error).__name__}: {error}"}
    finally:
        if process.pid is not None:
            if timed_out and process.is_alive():
                process.terminate()
            process.join(timeout=1)
            if process.is_alive():
                process.kill()
                process.join(timeout=1)
            if process.is_alive():
                raise RuntimeError("worker could not be stopped")
            process.close()
        receiver.close()
        sender.close()
    wall = perf_counter() - started
    if timed_out:
        return {"status": "TIMEOUT", "solver_status": "", "statistics": statistics,
                "observed_wall_seconds": wall, "message": "parent deadline; worker terminated"}
    if payload is None:
        return {"status": "ERROR", "solver_status": "", "statistics": statistics,
                "observed_wall_seconds": wall, "message": "worker exited without a result"}
    payload["solver_status"] = payload["status"]
    payload["statistics"] = statistics
    payload["observed_wall_seconds"] = wall
    payload["solution_valid"] = None
    if payload["status"] == "SAT":
        valid = SolutionValidator(NQueensProblem(task["n"])).validate(payload.get("solution"))
        payload["solution_valid"] = valid
        if not valid:
            payload["status"] = "ERROR"
            payload["message"] = "benchmark validator rejected claimed SAT solution"
    return payload


def repository_state():
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    status = git("status", "--porcelain=v1", "--untracked-files=all")
    return {"source_commit": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
            "working_tree_dirty": bool(status), "working_tree_status": status.splitlines()}


def environment_metadata():
    cpu = platform.processor() or "unavailable"
    if os.name == "nt":
        try:
            query = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).Name"],
                capture_output=True, text=True, timeout=5, check=True,
            )
            cpu = query.stdout.strip() or cpu
        except (OSError, subprocess.SubprocessError):
            pass
    return {"python": sys.version, "os": platform.platform(), "machine": platform.machine(),
            "cpu": cpu, "logical_cpu_count": os.cpu_count(),
            "packages": dict(sorted((d.metadata["Name"], d.version) for d in distributions()))}


def run_benchmark(config, output, allow_dirty=False):
    trials = plan_trials(config)
    state = repository_state()  # Capture BEFORE output creation dirties the tree.
    if state["working_tree_dirty"] and not allow_dirty:
        raise ValueError("commit source changes first; --allow-dirty is only for smoke tests")
    output = Path(output)
    if output.exists():
        raise FileExistsError("refusing to overwrite an existing benchmark directory")
    metadata = {**state, **environment_metadata(), "started_utc": datetime.now(timezone.utc).isoformat(),
                "argv": sys.argv, "planned_trials": len(trials), "execution": "sequential spawn, one worker",
                "timeout_scope": "before spawn until result receipt; bounded teardown included in observed wall",
                "restart": False, "sat_warmups": 0}
    output.mkdir(parents=True)
    (output / "config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    started = perf_counter()
    with (output / "trials.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for index, task in enumerate(trials):
            remaining = config["total_budget_seconds"] - (perf_counter() - started)
            if remaining <= 0:
                result = {"status": "NOT_RUN", "statistics": {}, "message": "total execution budget exhausted"}
                effective_timeout = None
            else:
                effective_timeout = min(task["timeout_seconds"], remaining)
                result = execute_isolated(task, effective_timeout)
            row = {**task, "initial_state": json.dumps(task["initial_state"]) if task["initial_state"] is not None else "",
                   "timeout_seconds": effective_timeout, "source_commit": state["source_commit"],
                   "working_tree_dirty": state["working_tree_dirty"],
                   "status": result["status"], "solver_status": result.get("solver_status", ""),
                   "solution_valid": result.get("solution_valid"),
                   "solution": json.dumps(result["solution"]) if result.get("solution") is not None else "",
                   "message": result.get("message") or "",
                   "algorithm_total_seconds": result.get("elapsed_seconds"),
                   "observed_wall_seconds": result.get("observed_wall_seconds")}
            row.update({name: result["statistics"].get(name) for name in METRIC_FIELDS})
            writer.writerow(row)
            stream.flush()
            print(f"[{index + 1}/{len(trials)}] {task['trial_id']}: {row['status']}", flush=True)
    metadata.update({"finished_utc": datetime.now(timezone.utc).isoformat(),
                     "execution_seconds": perf_counter() - started})
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--allow-dirty", action="store_true", help="smoke pipeline only")
    args = parser.parse_args(argv)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    output = run_benchmark(config, args.output, args.allow_dirty)
    from .benchmark_analysis import analyze
    analyze(output)


if __name__ == "__main__":
    mp.freeze_support()
    main()
