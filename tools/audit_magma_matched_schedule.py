#!/usr/bin/env python3
"""Audit matched Magma run scheduling before interpreting wall-clock results."""

from __future__ import annotations

import argparse
import json
import math
import shlex
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}


def split_list(value: Any) -> list[str]:
    if value is None:
        return []
    return [item for item in str(value).replace(",", " ").split() if item]


def option_value(argv: list[str], name: str) -> str | None:
    for index, arg in enumerate(argv):
        if arg == name and index + 1 < len(argv):
            return argv[index + 1]
        prefix = f"{name}="
        if arg.startswith(prefix):
            return arg[len(prefix) :]
    return None


def command_args(record: dict[str, Any]) -> list[str]:
    command = str(record.get("command") or "")
    try:
        return shlex.split(command)
    except ValueError:
        return []


def read_plan_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            records.append(record)
    return records


def find_step(records: list[dict[str, Any]], step: str) -> dict[str, Any]:
    for record in records:
        if record.get("step") == step:
            return record
    return {}


def plan_fields(records: list[dict[str, Any]]) -> dict[str, Any]:
    formtrig = find_step(records, "formtrig_batch")
    baselines = find_step(records, "magma_baselines")
    formtrig_args = command_args(formtrig)
    baseline_args = command_args(baselines)
    return {
        "formtrig_jobs": int_value(option_value(formtrig_args, "--jobs")),
        "baseline_jobs": int_value(option_value(baseline_args, "--jobs")),
        "baselines": option_value(baseline_args, "--baselines"),
        "durations": option_value(baseline_args, "--durations"),
        "reps": int_value(option_value(baseline_args, "--reps") or baselines.get("reps")),
    }


def summarize(run_root: Path) -> dict[str, Any]:
    metadata = read_json(run_root / "run_metadata.json")
    records = read_plan_records(run_root / "run_plan.jsonl")
    planned = plan_fields(records)

    baselines = split_list(metadata.get("baselines") or planned.get("baselines"))
    durations = split_list(planned.get("durations") or metadata.get("duration_s"))
    duration_values = [int_value(value) for value in durations if int_value(value) > 0]
    reps = int_value(metadata.get("reps") or planned.get("reps"), 1)
    formtrig_jobs = int_value(metadata.get("formtrig_jobs") or planned.get("formtrig_jobs"))
    baseline_jobs = int_value(metadata.get("baseline_jobs") or planned.get("baseline_jobs"))
    if baseline_jobs <= 0:
        baseline_jobs = formtrig_jobs

    baseline_count = int_value(metadata.get("baseline_count")) or len(baselines)
    duration_count = max(1, len(duration_values))
    baseline_run_count = (
        int_value(metadata.get("baseline_run_count"))
        or baseline_count * reps * duration_count
    )
    if baseline_jobs > 0:
        baseline_batches = int_value(metadata.get("baseline_batches")) or math.ceil(
            baseline_run_count / baseline_jobs
        )
    else:
        baseline_batches = 0

    total_baseline_budget_s = sum(duration_values) * baseline_count * reps
    ideal_baseline_wall_s = (
        math.ceil(total_baseline_budget_s / baseline_jobs)
        if baseline_jobs > 0 and total_baseline_budget_s > 0
        else None
    )
    longest_duration_s = max(duration_values) if duration_values else None
    one_batch_jobs = baseline_run_count if baseline_run_count > 0 else None

    if baseline_run_count <= 0 or baseline_jobs <= 0:
        verdict = "missing_baseline_schedule"
    elif baseline_batches <= 1:
        verdict = "single_batch_baseline_schedule"
    else:
        verdict = "multi_batch_baseline_schedule"

    return {
        "analysis_time_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run_root": str(run_root),
        "target_id": metadata.get("target_id"),
        "mode": metadata.get("mode"),
        "duration_values_s": duration_values,
        "reps": reps,
        "baselines": baselines,
        "baseline_count": baseline_count,
        "baseline_run_count": baseline_run_count,
        "formtrig_jobs": formtrig_jobs,
        "baseline_jobs": baseline_jobs,
        "baseline_batches": baseline_batches,
        "longest_duration_s": longest_duration_s,
        "total_baseline_budget_s": total_baseline_budget_s,
        "ideal_baseline_wall_s": ideal_baseline_wall_s,
        "recommended_baseline_jobs_for_one_batch": one_batch_jobs,
        "verdict": verdict,
        "claim_boundary": (
            "schedule audit only explains expected wall-clock shape; endpoint and "
            "guidance claims still require gate, guidance-gap, comparison, and evidence"
        ),
    }


def cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def to_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Magma Matched Schedule Audit",
        "",
        f"- analysis: `{payload['analysis_time_utc']}`",
        f"- target: `{cell(payload.get('target_id'))}`",
        f"- verdict: `{payload['verdict']}`",
        f"- claim boundary: {payload['claim_boundary']}",
        "",
        "| metric | value |",
        "| --- | ---: |",
        f"| reps | {payload['reps']} |",
        f"| baselines | {payload['baseline_count']} |",
        f"| baseline runs | {payload['baseline_run_count']} |",
        f"| FORMTRIG jobs | {payload['formtrig_jobs']} |",
        f"| baseline jobs | {payload['baseline_jobs']} |",
        f"| baseline batches | {payload['baseline_batches']} |",
        f"| longest duration s | {cell(payload.get('longest_duration_s'))} |",
        f"| total baseline budget s | {payload['total_baseline_budget_s']} |",
        f"| ideal baseline wall s | {cell(payload.get('ideal_baseline_wall_s'))} |",
        f"| one-batch baseline jobs | {cell(payload.get('recommended_baseline_jobs_for_one_batch'))} |",
        "",
    ]
    if payload["verdict"] == "multi_batch_baseline_schedule":
        lines.extend(
            [
                "## Scheduling Note",
                "",
                (
                    "Baseline wall-clock is expected to expand because the baseline "
                    "run count exceeds `baseline_jobs`. For a 3 baseline x 3 rep "
                    "matched run, use `--baseline-jobs 9` when the machine can "
                    "support that concurrency."
                ),
                "",
            ]
        )
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--format", choices=["json", "md"], default="md")
    parser.add_argument("--out-json")
    parser.add_argument("--out-md")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = summarize(args.run_root)
    if args.out_json:
        out = Path(args.out_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.out_md:
        out = Path(args.out_md)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(to_markdown(payload), encoding="utf-8")
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(to_markdown(payload))


if __name__ == "__main__":
    main()
