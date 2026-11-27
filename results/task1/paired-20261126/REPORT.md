# Supplementary paired Min-Conflicts analysis

Input: [official trials](../main-20261126/trials.csv) and its config/metadata.
Benchmark source commit: `2781502d6e92eefda54fdb6c772c8d65a40c0330`.
Exact input hashes and analysis module hash: [provenance.json](provenance.json).
All MC pairs and exclusion statuses: [pairs.csv](pairs.csv). Full precision: [summary.csv](summary.csv).

Pair by (N, seed), verify the same initial state, max_steps and timeout.
Use only pairs where BOTH strategies returned independently validated SAT for these conditional comparisons.
Delta = max_conflicted minus random_conflicted, per pair, then median of deltas.
A negative delta means fewer steps or less algorithm time for max on that pair.
The median paired delta generally differs from the difference of marginal medians.
Time includes variable selection and every other part of MinConflictsSolver.solve().
No solvers were rerun. No original trials, summaries, reports or figures were replaced.

| N | All pairs | Joint successes | Excluded | Random median steps | Max median steps | Median paired delta steps | Random median (s) | Max median (s) | Median paired delta (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 4 | 30 | 30 | 0 | 11 | 5.5 | -2.5 | 0.00010115 | 8.345e-05 | -3.4e-06 |
| 8 | 30 | 27 | 3 | 40 | 21 | -15 | 0.0002931 | 0.0002289 | -3.61e-05 |
| 16 | 30 | 26 | 4 | 73.5 | 64 | -14 | 0.00087315 | 0.00085385 | -1.55e-05 |
| 32 | 30 | 30 | 0 | 79.5 | 76.5 | 8 | 0.00157595 | 0.0018007 | 0.0003417 |
| 64 | 30 | 30 | 0 | 112 | 92 | -15.5 | 0.00408235 | 0.00384305 | -0.00014455 |

This is a descriptive, success-conditioned subset. Exclusions can bias the comparison.
Read alongside the [all-trial report](../main-20261126/REPORT.md), its success rates,
all seven LIMIT_REACHED trials and costs over ALL runs. LIMIT_REACHED does not establish UNSAT.
No significance test, confidence interval or claim of general superiority is made.
At N=8 and N=16 the two marginal success populations differ; paired values here use identical subsets.
Blank CSV metrics / N/A mean no joint successes, never a zero measurement.

Reproduce from repository root into a NEW directory:
`python -m source.task1_nqueens.paired_analysis results/task1/main-20261126 NEW_DIRECTORY`
