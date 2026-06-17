#!/usr/bin/env python3
"""Analyze whether baseline evidence supports a binary-TC no-guidance claim.

This tool is deliberately stricter than a speedup comparison.  A target is a
hard SOTA-pain candidate only when the baseline-visible target-state oracle is
flat before `_T` and the endpoint behavior is late, missing, or high-variance.
Early successful baselines demote the target even if FORMTRIG is faster.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path
from typing import Any


RUN_FIELDS = [
    "source_label",
    "target_id",
    "baseline",
    "budget",
    "rep",
    "success",
    "trigger_time_s",
    "terminal_count",
    "first_reach_time_s",
    "first_reach_count",
    "first_trigger_time_s",
    "latest_reached",
    "latest_triggered",
    "pretrigger_binary_flat",
    "pretrigger_binary_reason",
    "reach_to_trigger_gap_s",
    "run_record",
]


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def numeric(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def int_value(value: Any, default: int = 0) -> int:
    parsed = numeric(value)
    return int(parsed) if parsed is not None else default


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def median(values: list[float]) -> float | None:
    if not values:
        return None
    return float(statistics.median(values))


def parse_labeled_path(value: str) -> tuple[str, Path]:
    if "=" in value:
        label, raw_path = value.split("=", 1)
        if not label:
            raise SystemExit(f"empty label in argument: {value}")
        return label, Path(raw_path)
    path = Path(value)
    return path.stem, path


def split_list(value: str) -> list[str]:
    return [part for part in value.replace(",", " ").split() if part]


def terminal_count(row: dict[str, Any]) -> int:
    for field in ("magma_triggered", "terminal_count", "saved_crashes"):
        if field in row and row.get(field) not in (None, ""):
            return int_value(row.get(field))
    return 0


def load_run_record(path_value: Any) -> dict[str, Any]:
    if not path_value:
        return {}
    path = Path(str(path_value))
    if not path.exists():
        return {}
    try:
        data = read_json(path)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def monitor_snapshot_field(monitor: dict[str, Any], snapshot: str, field: str) -> Any:
    value = monitor.get(snapshot)
    if isinstance(value, dict):
        return value.get(field)
    return None


def pretrigger_binary_flatness(monitor: dict[str, Any]) -> tuple[bool | None, str]:
    """Return whether Magma monitor evidence proves flat binary `_T` before `_T`.

    The monitor only exposes aggregate `_R/_T` counts.  It can prove that the
    binary target-state oracle was uninformative for the reached non-trigger
    region before the first terminal event: every reached non-trigger execution
    has the same binary target-state value, `_T=false`.
    """

    if not monitor:
        return None, "missing_magma_monitor"

    first_reach = monitor.get("first_reach")
    first_trigger = monitor.get("first_trigger")
    latest = monitor.get("latest")

    if isinstance(first_reach, dict):
        reached = int_value(first_reach.get("reached"))
        triggered = int_value(first_reach.get("triggered"))
        if reached > triggered and triggered == 0:
            return True, "first_reach_snapshot_has_R_without_T"

    if isinstance(first_trigger, dict):
        reached = int_value(first_trigger.get("reached"))
        triggered = int_value(first_trigger.get("triggered"))
        if reached > triggered and numeric(first_trigger.get("time_s")) is not None:
            return True, "first_trigger_snapshot_contains_prior_R_not_T_region"

    if isinstance(latest, dict):
        reached = int_value(latest.get("reached"))
        triggered = int_value(latest.get("triggered"))
        if reached > 0 and triggered == 0:
            return True, "run_ended_with_R_without_T"

    return False, "no_R_without_T_monitor_snapshot"


def run_row(source_label: str, raw: dict[str, Any], summary_path: Path) -> dict[str, Any]:
    record = load_run_record(raw.get("run_record"))
    monitor = record.get("magma_monitor") if isinstance(record.get("magma_monitor"), dict) else {}
    if not monitor and isinstance(raw.get("magma_monitor"), dict):
        monitor = raw["magma_monitor"]

    flat, flat_reason = pretrigger_binary_flatness(monitor)
    first_reach_time = monitor_snapshot_field(monitor, "first_reach", "time_s")
    first_trigger_time = monitor_snapshot_field(monitor, "first_trigger", "time_s")
    if first_trigger_time is None:
        first_trigger_time = raw.get("magma_first_trigger_time_s")
    if first_reach_time is None:
        first_reach_time = raw.get("magma_first_reach_time_s")

    trigger_time = numeric(raw.get("trigger_time_s"))
    if trigger_time is None:
        trigger_time = numeric(record.get("trigger_time_s"))

    gap = None
    if numeric(first_reach_time) is not None and trigger_time is not None:
        gap = max(0.0, trigger_time - float(first_reach_time))

    return {
        "source_label": source_label,
        "target_id": str(raw.get("target_id") or record.get("target_id") or ""),
        "baseline": str(raw.get("baseline") or record.get("baseline") or ""),
        "budget": int_value(raw.get("budget") or record.get("budget")),
        "rep": raw.get("rep") or record.get("rep") or "",
        "success": bool_value(raw.get("success") if "success" in raw else record.get("success")),
        "trigger_time_s": trigger_time,
        "terminal_count": terminal_count(raw),
        "first_reach_time_s": numeric(first_reach_time),
        "first_reach_count": int_value(monitor_snapshot_field(monitor, "first_reach", "reached")),
        "first_trigger_time_s": numeric(first_trigger_time),
        "latest_reached": int_value(monitor_snapshot_field(monitor, "latest", "reached")),
        "latest_triggered": int_value(monitor_snapshot_field(monitor, "latest", "triggered")),
        "pretrigger_binary_flat": flat,
        "pretrigger_binary_reason": flat_reason,
        "reach_to_trigger_gap_s": gap,
        "run_record": str(raw.get("run_record") or ""),
        "summary_path": str(summary_path),
    }


def load_baseline_rows(items: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        label, path = parse_labeled_path(item)
        if not path.exists():
            raise SystemExit(f"baseline summary does not exist: {path}")
        data = read_json(path)
        records = data.get("records") if isinstance(data, dict) else None
        if not isinstance(records, list):
            raise SystemExit(f"baseline summary has no records list: {path}")
        for raw in records:
            if isinstance(raw, dict):
                rows.append(run_row(label, raw, path))
    return rows


def group_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    keys = sorted({(row["baseline"], row["budget"]) for row in rows})
    for baseline, budget in keys:
        selected = [row for row in rows if row["baseline"] == baseline and row["budget"] == budget]
        successes = [row for row in selected if row["success"]]
        ttes = [float(row["trigger_time_s"]) for row in successes if row["trigger_time_s"] is not None]
        flat_measured = [row for row in selected if row["pretrigger_binary_flat"] is not None]
        flat_passes = [row for row in selected if row["pretrigger_binary_flat"] is True]
        groups.append(
            {
                "baseline": baseline,
                "budget": budget,
                "reps": len(selected),
                "successes": len(successes),
                "missing": len(selected) - len(successes),
                "success_rate": len(successes) / len(selected) if selected else 0.0,
                "trigger_times_s": ttes,
                "min_trigger_time_s": min(ttes) if ttes else None,
                "median_trigger_time_s": median(ttes),
                "max_trigger_time_s": max(ttes) if ttes else None,
                "trigger_time_range_s": (max(ttes) - min(ttes)) if len(ttes) >= 2 else None,
                "pretrigger_binary_flat_measured_runs": len(flat_measured),
                "pretrigger_binary_flat_pass_runs": len(flat_passes),
                "pretrigger_binary_flat_all_measured": bool(flat_measured)
                and len(flat_measured) == len(selected),
                "pretrigger_binary_flat_all_runs": bool(selected)
                and len(flat_passes) == len(selected),
            }
        )
    return groups


def target_analysis(
    rows: list[dict[str, Any]],
    *,
    required_baselines: list[str],
    min_reps: int,
    acceptable_trigger_s: float,
    hard_trigger_s: float,
    variance_trigger_s: float,
) -> dict[str, Any]:
    groups = group_rows(rows)
    required = set(required_baselines)
    considered = [group for group in groups if not required or group["baseline"] in required]
    missing_required = sorted(required - {group["baseline"] for group in groups})
    low_rep_groups = [
        group["baseline"] for group in considered if int_value(group.get("reps")) < min_reps
    ]

    all_flat = bool(considered) and all(
        group.get("pretrigger_binary_flat_all_runs") for group in considered
    )
    all_flat_measured = bool(considered) and all(
        group.get("pretrigger_binary_flat_all_measured") for group in considered
    )

    successful_ttes = [
        float(tte)
        for group in considered
        for tte in group.get("trigger_times_s", [])
        if tte is not None
    ]
    fastest = min(successful_ttes) if successful_ttes else None
    fastest_disqualifies = fastest is not None and fastest <= acceptable_trigger_s

    any_missing = any(int_value(group.get("missing")) > 0 for group in considered)
    any_late_median = any(
        numeric(group.get("median_trigger_time_s")) is not None
        and float(group["median_trigger_time_s"]) >= hard_trigger_s
        for group in considered
    )
    any_high_variance = any(
        numeric(group.get("trigger_time_range_s")) is not None
        and float(group["trigger_time_range_s"]) >= variance_trigger_s
        for group in considered
    )
    endpoint_cost_pass = (
        not fastest_disqualifies and bool(considered) and (not successful_ttes or any_missing or any_late_median or any_high_variance)
    )

    reasons: list[str] = []
    if missing_required:
        reasons.append("missing_required_baselines")
    if low_rep_groups:
        reasons.append("low_replication")
    if not all_flat_measured:
        reasons.append("pretrigger_binary_flatness_not_measured_for_all_runs")
    elif all_flat:
        reasons.append("pretrigger_binary_oracle_flat_before_T")
    else:
        reasons.append("pretrigger_binary_oracle_not_flat")
    if fastest_disqualifies:
        reasons.append("fast_successful_baseline_within_acceptable_threshold")
    if endpoint_cost_pass:
        reasons.append("baseline_endpoint_cost_late_missing_or_high_variance")
    else:
        reasons.append("baseline_endpoint_cost_not_sufficient_for_hard_pain")

    if missing_required:
        status = "incomplete_required_baselines"
    elif fastest_disqualifies:
        status = "fail_fast_baseline"
    elif low_rep_groups:
        status = "under_replicated"
    elif not all_flat_measured:
        status = "not_measured"
    elif not all_flat:
        status = "fail_not_flat"
    elif endpoint_cost_pass:
        status = "measured_pass"
    else:
        status = "fail_endpoint_cost_not_hard"

    return {
        "required_baselines": required_baselines,
        "missing_required_baselines": missing_required,
        "min_reps": min_reps,
        "acceptable_trigger_threshold_s": acceptable_trigger_s,
        "hard_trigger_threshold_s": hard_trigger_s,
        "variance_trigger_threshold_s": variance_trigger_s,
        "baseline_groups": groups,
        "considered_baseline_count": len(considered),
        "fastest_successful_baseline_trigger_time_s": fastest,
        "pretrigger_binary_flat_pass": all_flat,
        "pretrigger_binary_flat_measured": all_flat_measured,
        "endpoint_cost_pass": endpoint_cost_pass,
        "status": status,
        "reasons": reasons,
        "interpretation": interpretation_for_status(status),
    }


def interpretation_for_status(status: str) -> str:
    return {
        "measured_pass": "baseline evidence supports a hard binary-TC no-guidance candidate",
        "fail_fast_baseline": "a faithful baseline reaches _T within the acceptable threshold, so this is not hard SOTA-pain evidence",
        "fail_endpoint_cost_not_hard": "pre-trigger binary flatness may be present, but endpoint cost is not late, missing, or variable enough",
        "fail_not_flat": "the available monitor evidence does not show a flat pre-_T binary oracle",
        "not_measured": "baseline pre-_T binary flatness is not measured for all required runs",
        "under_replicated": "baseline no-guidance evidence needs more repetitions",
        "incomplete_required_baselines": "one or more required baseline families are missing",
    }.get(status, "unknown baseline guidance-gap status")


def write_run_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=RUN_FIELDS,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({field: tsv_value(row.get(field)) for field in RUN_FIELDS})


def tsv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    analysis = payload["analysis"]
    lines = [
        f"# {payload['analysis_id']}",
        "",
        f"- target: `{payload['target_id']}`",
        f"- status: `{analysis['status']}`",
        f"- interpretation: {analysis['interpretation']}",
        f"- fastest successful baseline `_T`: `{analysis.get('fastest_successful_baseline_trigger_time_s')}`",
        f"- pre-trigger binary flatness measured: `{analysis['pretrigger_binary_flat_measured']}`",
        f"- pre-trigger binary flatness pass: `{analysis['pretrigger_binary_flat_pass']}`",
        f"- endpoint cost pass: `{analysis['endpoint_cost_pass']}`",
        "",
        "## Reasons",
        "",
    ]
    for reason in analysis["reasons"]:
        lines.append(f"- `{reason}`")
    lines.extend(
        [
            "",
            "## Baseline Groups",
            "",
            "| baseline | budget | reps | success rate | min T | median T | max T | missing | flat pre-T runs |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for group in analysis["baseline_groups"]:
        lines.append(
            "| {baseline} | {budget} | {reps} | {success_rate:.3f} | {min_t} | {median_t} | {max_t} | {missing} | {flat}/{reps} |".format(
                baseline=group["baseline"],
                budget=group["budget"],
                reps=group["reps"],
                success_rate=float(group["success_rate"]),
                min_t=cell(group.get("min_trigger_time_s")),
                median_t=cell(group.get("median_trigger_time_s")),
                max_t=cell(group.get("max_trigger_time_s")),
                missing=group["missing"],
                flat=group["pretrigger_binary_flat_pass_runs"],
            )
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "This analysis uses monitor-visible binary `_T` flatness and endpoint timing only.",
            "It does not prove that every internal baseline heuristic is random; it tests whether the current matched evidence is strong enough for a hard binary-TC SOTA-pain claim.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def cell(value: Any) -> str:
    return "" if value is None else str(value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze baseline pre-_T binary flatness and endpoint cost."
    )
    parser.add_argument("--analysis-id", required=True)
    parser.add_argument("--target-id", required=True)
    parser.add_argument(
        "--baseline-summary",
        action="append",
        default=[],
        help="LABEL=path/to/summary.json; repeatable",
    )
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--required-baselines", default="")
    parser.add_argument("--min-reps", type=int, default=3)
    parser.add_argument("--acceptable-trigger-s", type=float, default=600.0)
    parser.add_argument("--hard-trigger-s", type=float, default=1800.0)
    parser.add_argument("--variance-trigger-s", type=float, default=1800.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = [
        row
        for row in load_baseline_rows(args.baseline_summary)
        if row["target_id"] == args.target_id
    ]
    required = split_list(args.required_baselines)
    analysis = target_analysis(
        rows,
        required_baselines=required,
        min_reps=args.min_reps,
        acceptable_trigger_s=args.acceptable_trigger_s,
        hard_trigger_s=args.hard_trigger_s,
        variance_trigger_s=args.variance_trigger_s,
    )
    payload = {
        "analysis_id": args.analysis_id,
        "target_id": args.target_id,
        "baseline_rows": rows,
        "analysis": analysis,
    }
    out_dir = Path(args.out_dir)
    write_json(out_dir / "baseline_guidance_gap.json", payload)
    write_markdown(out_dir / "baseline_guidance_gap.md", payload)
    write_run_tsv(out_dir / "baseline_guidance_gap_runs.tsv", rows)


if __name__ == "__main__":
    main()
