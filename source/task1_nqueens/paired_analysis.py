"""Supplementary matched-success analysis; never runs solvers or edits raw trials."""

import argparse
from collections import defaultdict
import csv
import hashlib
import json
import os
from pathlib import Path
from statistics import median

from .benchmark import STRATEGIES
from .benchmark_analysis import _table, audit, success


def compare_pairs(rows):
    """Keep every MC pair; compute max-minus-random deltas only for joint success."""
    groups = defaultdict(dict)
    for row in rows:
        if row["method"] != "min-conflicts":
            continue
        key = (int(row["n"]), int(row["seed"]))
        strategy = row["strategy"]
        if strategy not in STRATEGIES or strategy in groups[key]:
            raise ValueError("unknown or duplicate strategy in pair")
        groups[key][strategy] = row
    pairs = []
    for (n, seed), group in sorted(groups.items()):
        if set(group) != set(STRATEGIES):
            raise ValueError("incomplete pair")
        left, right = (group[strategy] for strategy in STRATEGIES)
        if (json.loads(left["initial_state"]) != json.loads(right["initial_state"])
                or int(left["max_steps"]) != int(right["max_steps"])
                or left["timeout_seconds"] != right["timeout_seconds"]):
            raise ValueError("pair configuration mismatch")
        joint = success(left) and success(right)
        pair = {"n": n, "seed": seed, "random_status": left["status"],
                "max_status": right["status"], "joint_success": joint}
        for key, convert in (("steps", int), ("algorithm_total_seconds", float)):
            pair[f"random_{key}"] = convert(left[key]) if joint else None
            pair[f"max_{key}"] = convert(right[key]) if joint else None
            pair[f"delta_{key}"] = convert(right[key]) - convert(left[key]) if joint else None
        pairs.append(pair)
    summaries = []
    for n in sorted({pair["n"] for pair in pairs}):
        all_pairs = [pair for pair in pairs if pair["n"] == n]
        joint = [pair for pair in all_pairs if pair["joint_success"]]
        summary = {"n": n, "all_pairs": len(all_pairs), "joint_success_pairs": len(joint),
                   "excluded_pairs": len(all_pairs) - len(joint)}
        for key in ("steps", "algorithm_total_seconds"):
            for prefix in ("random", "max", "delta"):
                name = f"{prefix}_{key}"
                summary[f"median_{name}"] = median(pair[name] for pair in joint) if joint else None
            for label, predicate in (("lower", lambda x: x < 0), ("equal", lambda x: x == 0),
                                     ("higher", lambda x: x > 0)):
                summary[f"max_{label}_{key}_pairs"] = sum(predicate(pair[f"delta_{key}"]) for pair in joint)
        summaries.append(summary)
    return pairs, summaries


def analyze_pairs(source, output):
    source, output = Path(source), Path(output)
    # Validate everything before creating a new destination. Never overwrite.
    config = json.loads((source / "config.json").read_text(encoding="utf-8"))
    metadata = json.loads((source / "metadata.json").read_text(encoding="utf-8"))
    with (source / "trials.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    audit(rows, config, metadata)
    pairs, summaries = compare_pairs(rows)
    if not summaries:
        raise ValueError("no Min-Conflicts pairs")
    output.mkdir(parents=True, exist_ok=False)
    for name, values in (("pairs.csv", pairs), ("summary.csv", summaries)):
        with (output / name).open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(values[0]))
            writer.writeheader()
            writer.writerows(values)
    provenance = {"benchmark_source_commit": metadata["source_commit"],
                  "benchmark_working_tree_dirty": metadata["working_tree_dirty"],
                  "input_sha256": {name: hashlib.sha256((source / name).read_bytes()).hexdigest()
                                   for name in ("trials.csv", "config.json", "metadata.json")},
                  "analysis_module_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    (output / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    table = _table(summaries, [("n", "N"), ("all_pairs", "All pairs"),
        ("joint_success_pairs", "Joint successes"), ("excluded_pairs", "Excluded"),
        ("median_random_steps", "Random median steps"), ("median_max_steps", "Max median steps"),
        ("median_delta_steps", "Median paired delta steps"),
        ("median_random_algorithm_total_seconds", "Random median (s)"),
        ("median_max_algorithm_total_seconds", "Max median (s)"),
        ("median_delta_algorithm_total_seconds", "Median paired delta (s)")])
    try:
        source_link = Path(os.path.relpath(source, output)).as_posix()
    except ValueError:  # Windows source/output can be on different drives.
        source_link = source.resolve().as_uri()
    text = f"""# Supplementary paired Min-Conflicts analysis

Input: [official trials]({source_link}/trials.csv) and its config/metadata.
Benchmark source commit: `{metadata['source_commit']}`.
Exact input hashes and analysis module hash: [provenance.json](provenance.json).
All MC pairs and exclusion statuses: [pairs.csv](pairs.csv). Full precision: [summary.csv](summary.csv).

Pair by (N, seed), verify the same initial state, max_steps and timeout.
Use only pairs where BOTH strategies returned independently validated SAT for these conditional comparisons.
Delta = max_conflicted minus random_conflicted, per pair, then median of deltas.
A negative delta means fewer steps or less algorithm time for max on that pair.
The median paired delta generally differs from the difference of marginal medians.
Time includes variable selection and every other part of MinConflictsSolver.solve().
No solvers were rerun. No original trials, summaries, reports or figures were replaced.

{table}

This is a descriptive, success-conditioned subset. Exclusions can bias the comparison.
Read alongside the [all-trial report]({source_link}/REPORT.md), its success rates,
all seven LIMIT_REACHED trials and costs over ALL runs. LIMIT_REACHED does not establish UNSAT.
No significance test, confidence interval or claim of general superiority is made.
At N=8 and N=16 the two marginal success populations differ; paired values here use identical subsets.
Blank CSV metrics / N/A mean no joint successes, never a zero measurement.

Reproduce from repository root into a NEW directory:
`python -m source.task1_nqueens.paired_analysis results/task1/main-20261126 NEW_DIRECTORY`
"""
    (output / "REPORT.md").write_text(text, encoding="utf-8")
    files = sorted(output.iterdir())
    (output / "SHA256SUMS.txt").write_text("".join(
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n" for path in files), encoding="utf-8")
    print(f"Paired analysis: {len(pairs)} pairs; {output}")
    return summaries


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    analyze_pairs(args.source, args.output)
