"""Audit raw trials and derive tables/figures without discarding unsuccessful trials."""

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
import os
from pathlib import Path
from statistics import mean, median

from .benchmark import COUNT_FIELDS, ROOT, STRATEGIES, plan_trials
from .models import NQueensProblem
from .validator import SolutionValidator


def numbers(rows, key):
    return [float(row[key]) for row in rows if row.get(key) not in (None, "")]


def success(row):
    return row["status"] == "SAT" and str(row.get("solution_valid")) == "True"


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[(row["method"], row["strategy"], int(row["n"]))].append(row)
    summaries = []
    for (method, strategy, n), group in sorted(groups.items()):
        statuses = Counter(row["status"] for row in group)
        successful = [row for row in group if success(row)]
        executed = len(group) - statuses["NOT_RUN"]
        result = {"method": method, "strategy": strategy, "n": n,
                  "total_runs": len(group), "executed_runs": executed,
                  "successful_runs": len(successful), "success_rate": len(successful) / len(group),
                  "success_rate_executed": len(successful) / executed if executed else None}
        for status in ("SAT", "UNSAT", "LIMIT_REACHED", "TIMEOUT", "ERROR", "NOT_RUN"):
            result[f"count_{status}"] = statuses[status]
        for key in COUNT_FIELDS:
            values = numbers(group, key)
            result[key] = median(values) if values else None
        for key in ("cnf_generation_seconds", "solver_initialization_seconds", "solve_seconds"):
            values = numbers(group, key)
            result[f"{key}_samples"] = len(values)
            result[f"median_{key}"] = median(values) if values else None
        for key, label, subset in (
            ("steps", "steps_success", successful),
            ("algorithm_total_seconds", "algorithm_seconds_success", successful),
            ("steps", "steps_all_recorded", group),
            ("algorithm_total_seconds", "algorithm_seconds_completed", group),
            ("observed_wall_seconds", "observed_wall_seconds_all", group),
        ):
            values = numbers(subset, key)
            result[f"{label}_samples"] = len(values)
            result[f"median_{label}"] = median(values) if values else None
            result[f"mean_{label}"] = mean(values) if values else None
            result[f"sum_{label}"] = sum(values) if values else None
        summaries.append(result)
    return summaries


def audit(rows, config, metadata):
    planned = {task["trial_id"]: task for task in plan_trials(config)}
    if len(rows) != len(planned) or {row["trial_id"] for row in rows} != set(planned):
        raise ValueError("missing, extra, or duplicate trial rows")
    for row in rows:
        task = planned[row["trial_id"]]
        if row["source_commit"] != metadata["source_commit"]:
            raise ValueError("source commit mismatch")
        if row["working_tree_dirty"] != str(metadata["working_tree_dirty"]):
            raise ValueError("dirty-state mismatch")
        for key in ("method", "strategy"):
            if row[key] != task[key]:
                raise ValueError(f"trial {key} mismatch")
        if int(row["n"]) != task["n"] or int(row["repeat"]) != task["repeat"]:
            raise ValueError("trial size/repeat mismatch")
        if row["status"] not in {"SAT", "UNSAT", "LIMIT_REACHED", "TIMEOUT", "ERROR", "NOT_RUN"}:
            raise ValueError("unknown status")
        if row["status"] == "SAT":
            if not success(row) or not SolutionValidator(NQueensProblem(task["n"])).validate(json.loads(row["solution"])):
                raise ValueError("invalid claimed solution")
        for key, value in row.items():
            if key.endswith("seconds") and value:
                if not math.isfinite(float(value)) or float(value) < 0:
                    raise ValueError("invalid measured duration")
        if row["status"] == "NOT_RUN" and row["observed_wall_seconds"]:
            raise ValueError("unexecuted trial cannot claim a wall measurement")
        if row["status"] == "TIMEOUT" and row["algorithm_total_seconds"]:
            raise ValueError("interrupted trial cannot claim a completed algorithm total")
        if row["status"] != "NOT_RUN":
            if not row["timeout_seconds"] or not 0 < float(row["timeout_seconds"]) <= task["timeout_seconds"]:
                raise ValueError("invalid effective timeout")
        completed = row["status"] in {"SAT", "UNSAT", "LIMIT_REACHED"}
        required = ["algorithm_total_seconds", "observed_wall_seconds"] if completed else []
        if completed:
            required += (COUNT_FIELDS + ["cnf_generation_seconds", "solver_initialization_seconds", "solve_seconds"]
                         if task["method"] == "sat" else ["steps"])
        if any(row.get(key) in (None, "") for key in required):
            raise ValueError("completed trial is missing required measurements")
        if completed and task["method"] == "sat" and sum(float(row[key]) for key in (
            "cnf_generation_seconds", "solver_initialization_seconds", "solve_seconds"
        )) > float(row["algorithm_total_seconds"]) + 1e-9:
            raise ValueError("phase times exceed algorithm total")
        if task["method"] == "sat":
            n = task["n"]
            expected = [n*n, n, n*n*(n-1)//2, n*n*(n-1)//2,
                        n*(n-1)*(2*n-1)//6, n*(n-1)*(2*n-1)//6,
                        n + n*n*(n-1) + n*(n-1)*(2*n-1)//3]
            for key, count in zip(COUNT_FIELDS, expected):
                if row[key] and int(row[key]) != count:
                    raise ValueError(f"generated clause count mismatch: {key}")
        else:
            if int(row["seed"]) != task["seed"] or json.loads(row["initial_state"]) != task["initial_state"]:
                raise ValueError("paired seed/initial-state mismatch")
            if int(row["max_steps"]) != task["max_steps"]:
                raise ValueError("step budget mismatch")
            if row["steps"] and not 0 <= int(row["steps"]) <= task["max_steps"]:
                raise ValueError("invalid steps")
            if row["status"] == "LIMIT_REACHED" and int(row["steps"]) != task["max_steps"]:
                raise ValueError("Min-Conflicts limit must exhaust the step budget")
            if row["status"] == "UNSAT":
                raise ValueError("Min-Conflicts cannot prove UNSAT")
    return {"passed": True, "trials": len(rows), "valid_solutions": sum(success(row) for row in rows),
            "paired_mc_initial_states": len(config["mc_ns"]) * len(config["mc_seeds"]),
            "statuses": dict(Counter(row["status"] for row in rows)),
            "source_commit": metadata["source_commit"]}


def _fmt(value):
    if value is None or value == "":
        return "N/A"
    return f"{value:.6g}" if isinstance(value, float) else str(value)


def _table(items, columns):
    lines = ["| " + " | ".join(label for _, label in columns) + " |",
             "| " + " | ".join("---" for _ in columns) + " |"]
    lines.extend("| " + " | ".join(_fmt(item[key]) for key, _ in columns) + " |" for item in items)
    return "\n".join(lines)


def write_report(output, summaries, config, metadata, checked):
    sat = [row for row in summaries if row["method"] == "sat"]
    mc = [row for row in summaries if row["method"] == "min-conflicts"]
    text = f"""# Benchmark Task 1 — {config['label']}

Nguồn dữ liệu: [trials.csv](trials.csv). Bảng tổng hợp: [summary.csv](summary.csv).
Cấu hình: [config.json](config.json). Môi trường và provenance: [metadata.json](metadata.json).
Commit mã nguồn: `{metadata['source_commit']}`; working tree dirty khi bắt đầu: `{metadata['working_tree_dirty']}`.
Máy: {metadata['cpu']}; {metadata['os']}; Python {metadata['python'].split()[0]}.
Kiểm tra dữ liệu: {checked['trials']} lượt theo kế hoạch, {checked['valid_solutions']} nghiệm hợp lệ; audit đạt.

Chưa chạy (NOT_RUN): {checked['statuses'].get('NOT_RUN', 0)} lượt, lý do nếu có là hết ngân sách toàn phiên.
Đã bắt đầu nhưng bị dừng bởi deadline (TIMEOUT): {checked['statuses'].get('TIMEOUT', 0)} lượt.
Lỗi (ERROR): {checked['statuses'].get('ERROR', 0)} lượt. Lý do từng lượt nằm ở cột message của trials.csv;
timeout không phải kết luận vô nghiệm và không có tổng thời gian thuật toán hoàn tất.

## Thiết kế

SAT: {config['sat_repeats']} lượt/N, không warmup, timeout {config['sat_timeout_seconds']} s/lượt.
Min-Conflicts: {len(config['mc_seeds'])} seed/N/chiến lược, max_steps={config['mc_max_steps']},
timeout {config['mc_timeout_seconds']} s/lượt, không restart. Mỗi cặp dùng cùng seed và bản sao cùng trạng thái đầu;
thứ tự hai chiến lược luân phiên theo lượt. Một worker tại một thời điểm, ngân sách toàn phiên {config['total_budget_seconds']} s.

## SAT

Trung vị solve chỉ đo lời gọi Glucose3.solve(), đơn vị giây; không gồm sinh CNF/nạp solver.
n solve là số lượt có phép đo solve hoàn tất, kể cả nếu giai đoạn sau bị lỗi/timeout.
Timeout trong solve không có thời gian solve hoàn tất và không được thay bằng thời gian timeout.

{_table(sat, [('n','N'), ('num_variables','Biến'), ('clauses_total','Mệnh đề'), ('median_solve_seconds','Median solve (s)'), ('solve_seconds_samples','n solve'), ('count_SAT','SAT hợp lệ'), ('count_TIMEOUT','Timeout'), ('count_ERROR','Lỗi'), ('count_NOT_RUN','Chưa chạy')])}

![Số mệnh đề và thời gian SAT solve](sat.png)

## Min-Conflicts

Tỷ lệ thành công = SAT hợp lệ / tổng lượt được lên kế hoạch. Bảng luôn giữ số lượt chưa chạy nếu có.
Trung vị bước/thời gian bên dưới chỉ trên các lượt thành công, có số mẫu đi kèm; không có thành công dùng N/A.
Thời gian thuật toán tính cả chọn biến, chọn hàng, cập nhật, khởi tạo RNG/board, kiểm tra và thống kê.

{_table(mc, [('n','N'), ('strategy','Chiến lược'), ('successful_runs','Thành công'), ('total_runs','Tổng lượt'), ('success_rate','Tỷ lệ'), ('median_steps_success','Median bước'), ('steps_success_samples','n bước'), ('median_algorithm_seconds_success','Median thuật toán (s)'), ('algorithm_seconds_success_samples','n thời gian')])}

![Min-Conflicts: tỷ lệ và các trung vị có điều kiện thành công](min_conflicts.png)

## Chi phí trên mọi lượt và thất bại

Wall quan sát bao gồm spawn/import, thuật toán, IPC và teardown, tính cả TIMEOUT và lỗi.
Đây không phải thời gian solve hoặc tổng thuật toán. Tổng thuật toán hoàn tất chỉ cộng các số đo có sẵn;
lượt timeout không có tổng thuật toán hoàn tất, nên báo số mẫu riêng và dùng wall để biểu diễn chi phí toàn bộ.
Số bước đã ghi có thể thiếu khi tiến trình bị dừng; không suy đoán bước chưa được báo.

{_table(summaries, [('method','Phương pháp'), ('strategy','Chiến lược'), ('n','N'), ('count_LIMIT_REACHED','Hết bước/unknown'), ('count_TIMEOUT','Timeout'), ('count_ERROR','Lỗi'), ('count_NOT_RUN','Chưa chạy'), ('sum_steps_all_recorded','Tổng bước đã ghi'), ('steps_all_recorded_samples','n bước'), ('sum_algorithm_seconds_completed','Tổng thuật toán hoàn tất (s)'), ('algorithm_seconds_completed_samples','n thuật toán'), ('sum_observed_wall_seconds_all','Tổng wall mọi lượt (s)'), ('observed_wall_seconds_all_samples','n wall')])}

![Chi phí mọi lượt Min-Conflicts](costs.png)

## Phạm vi và giới hạn

Timeout được parent thực thi từ trước spawn đến khi nhận kết quả, terminate/kill worker khi hết hạn;
wall quan sát còn gồm tối đa hai lần join 1 s và độ trễ lập lịch. Không chỉ kiểm tra thời gian sau khi solver trả về.
SAT gửi snapshot các pha hoàn tất để giữ số đếm và thời gian trước timeout; tổng SAT bao gồm chi phí callback/IPC,
còn từng pha CNF/nạp/solve không tính callback đó. Min-Conflicts total bao gồm chi phí chọn biến.
Các ô trống trong CSV là không có phép đo, không phải 0; summary.csv giữ ô trống, báo cáo hiển thị N/A.
Mọi TIMEOUT, ERROR, LIMIT_REACHED, NOT_RUN còn nguyên trong CSV. Xem audit.json và SHA256SUMS.txt để kiểm tra.
Đây là kết quả mô tả trên một máy, tập N/seed và ngân sách đã công bố. Không suy ra chiến lược tốt hơn nói chung;
trung vị trên lượt thành công chịu ảnh hưởng chọn mẫu, cần đọc cùng tỷ lệ thành công và chi phí toàn bộ.
Không so trực tiếp SAT solve với tổng thuật toán Min-Conflicts hoặc wall pipeline. Chưa kiểm tra macOS/Linux.
"""
    (output / "REPORT.md").write_text(text, encoding="utf-8")


def make_plots(output, summaries):
    os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".venv" / "matplotlib-cache"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    def values(items, key):
        return [float("nan") if row[key] is None else row[key] for row in items]

    sat = [row for row in summaries if row["method"] == "sat"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5), layout="constrained")
    for ax, key, title, ylabel in (
        (axes[0], "clauses_total", "Input CNF clauses", "Clauses (count)"),
        (axes[1], "median_solve_seconds", "Glucose3 solve() only", "Median solve time (s)"),
    ):
        ax.plot([row["n"] for row in sat], values(sat, key), "o-", label="SAT")
        ax.set(xlabel="Board size N", ylabel=ylabel, title=title)
        ax.set_xscale("log", base=2)
        ax.set_xticks([row["n"] for row in sat], labels=[str(row["n"]) for row in sat])
        ax.margins(y=0.15)
        ax.legend(); ax.grid(alpha=0.25)
    for row in sat:
        if row["median_solve_seconds"] is not None:
            axes[1].annotate(f"n={row['solve_seconds_samples']}", (row["n"], row["median_solve_seconds"]), xytext=(0, 8), textcoords="offset points", ha="center")
    fig.suptitle("Source: trials.csv → summary.csv; missing values omitted")
    fig.savefig(output / "sat.png", dpi=160); plt.close(fig)

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.6), layout="constrained")
    fig_cost, cost_axes = plt.subplots(1, 2, figsize=(11, 4.5), layout="constrained")
    for strategy, color in zip(STRATEGIES, ("#0072B2", "#D55E00")):
        subset = [row for row in summaries if row["strategy"] == strategy]
        ns = [row["n"] for row in subset]
        for ax, key in zip(axes, ("success_rate", "median_steps_success", "median_algorithm_seconds_success")):
            ys = values(subset, key)
            if key == "success_rate":
                ys = [100 * value for value in ys]
            ax.plot(ns, ys, "o-", color=color, label=strategy)
        for row in subset:
            axes[0].annotate(f"{row['successful_runs']}/{row['total_runs']}", (row["n"], 100*row["success_rate"]), xytext=(0, 8 if strategy == STRATEGIES[0] else -16), textcoords="offset points", ha="center", color=color, fontsize=8)
        for ax, key in zip(cost_axes, ("sum_steps_all_recorded", "sum_observed_wall_seconds_all")):
            ax.plot(ns, values(subset, key), "o-", color=color, label=strategy)
    for ax, title, ylabel in zip(axes, ("Valid SAT / all planned trials", "Successful trials only", "Successful trials only"), ("Success rate (%)", "Median updates (steps)", "Median algorithm total (s)")):
        ax.set(xlabel="Board size N", ylabel=ylabel, title=title)
        ax.set_xscale("log", base=2)
        ax.set_xticks(ns, labels=[str(n) for n in ns])
        ax.legend(fontsize=8); ax.grid(alpha=0.25)
    axes[0].set_ylim(-8, 112)
    fig.suptitle("Source: trials.csv → summary.csv; successful sample counts in REPORT.md")
    fig.savefig(output / "min_conflicts.png", dpi=160); plt.close(fig)
    for ax, title, ylabel in zip(cost_axes, ("All recorded steps, including failures", "All executed trials, including timeouts/errors"), ("Total recorded updates (steps)", "Total observed process wall time (s)")):
        ax.set(xlabel="Board size N", ylabel=ylabel, title=title)
        ax.set_xscale("log", base=2)
        ax.set_xticks(ns, labels=[str(n) for n in ns])
        ax.legend(fontsize=8); ax.grid(alpha=0.25)
    fig_cost.suptitle("Source: trials.csv → summary.csv; timeout steps unavailable, never imputed")
    fig_cost.savefig(output / "costs.png", dpi=160); plt.close(fig_cost)


def analyze(output):
    output = Path(output)
    config = json.loads((output / "config.json").read_text(encoding="utf-8"))
    metadata = json.loads((output / "metadata.json").read_text(encoding="utf-8"))
    with (output / "trials.csv").open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    checked = audit(rows, config, metadata)
    (output / "audit.json").write_text(json.dumps(checked, indent=2) + "\n", encoding="utf-8")
    summaries = summarize(rows)
    with (output / "summary.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(summaries[0]))
        writer.writeheader(); writer.writerows(summaries)
    make_plots(output, summaries)
    write_report(output, summaries, config, metadata, checked)
    files = sorted(path for path in output.iterdir() if path.is_file() and path.name != "SHA256SUMS.txt")
    (output / "SHA256SUMS.txt").write_text(
        "".join(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n" for path in files), encoding="utf-8"
    )
    print(f"Audit passed: {len(rows)} rows; report and plots: {output}", flush=True)
    return summaries


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    analyze(parser.parse_args().output)
