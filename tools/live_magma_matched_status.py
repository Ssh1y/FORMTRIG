#!/usr/bin/env python3
"""Summarize an in-flight Magma matched FORMTRIG/baseline run.

This is a live-audit helper, not a final comparison gate.  It reads only
existing AFL++ stats, FORMTRIG progress logs, and Magma monitor snapshots so
long runs can be checked without perturbing the fuzzers.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def numeric(value: Any) -> float | int | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        parsed = float(str(value).strip())
    except ValueError:
        return None
    if parsed.is_integer():
        return int(parsed)
    return parsed


def int_value(value: Any, default: int = 0) -> int:
    parsed = numeric(value)
    return int(parsed) if parsed is not None else default


def read_stats(path: Path) -> dict[str, str]:
    stats: dict[str, str] = {}
    if not path.exists():
        return stats
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        stats[key.strip()] = value.strip()
    return stats


def parse_monitor_file(path: Path, target_id: str) -> dict[str, Any] | None:
    try:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
            rows = list(csv.reader(handle))
    except OSError:
        return None
    if len(rows) < 2:
        return None
    row = dict(zip(rows[0], rows[1]))
    reached_key = f"{target_id}_R"
    triggered_key = f"{target_id}_T"
    if reached_key not in row and triggered_key not in row:
        return None
    return {
        "file": str(path),
        "reached": int_value(row.get(reached_key)),
        "triggered": int_value(row.get(triggered_key)),
    }


def monitor_snapshots(path: Path, target_id: str) -> list[dict[str, Any]]:
    if not path.is_dir():
        return []
    snapshots: list[dict[str, Any]] = []
    for child in path.iterdir():
        if not child.is_file() or child.name.startswith("."):
            continue
        record = parse_monitor_file(child, target_id)
        if record is None:
            continue
        if child.name.isdigit():
            record["time_s"] = int(child.name)
            record["kind"] = "poll"
        elif child.name == "final":
            record["time_s"] = None
            record["kind"] = "final"
        else:
            continue
        snapshots.append(record)
    snapshots.sort(
        key=lambda row: (
            0 if numeric(row.get("time_s")) is not None else 1,
            float(numeric(row.get("time_s")) or 0),
        )
    )
    return snapshots


def summarize_progress(path: Path) -> dict[str, Any]:
    summary = {
        "events": 0,
        "saved_triggered": 0,
        "saved_non_trigger": 0,
        "calibrated_non_trigger": 0,
        "first_saved_triggered_execs": None,
        "first_saved_non_trigger_execs": None,
        "last_event_execs": None,
    }
    if not path.exists():
        return summary
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        summary["events"] += 1
        execs = numeric(event.get("execs_done"))
        if execs is not None:
            summary["last_event_execs"] = execs
        triggered = bool(event.get("triggered"))
        event_kind = event.get("event")
        if event_kind == "saved_progress" and triggered:
            summary["saved_triggered"] += 1
            if summary["first_saved_triggered_execs"] is None:
                summary["first_saved_triggered_execs"] = execs
        elif event_kind == "saved_progress" and not triggered:
            summary["saved_non_trigger"] += 1
            if summary["first_saved_non_trigger_execs"] is None:
                summary["first_saved_non_trigger_execs"] = execs
        elif event_kind == "calibrated_frontier" and not triggered:
            summary["calibrated_non_trigger"] += 1
    return summary


def formtrig_runs(run_root: Path, target_id: str) -> list[dict[str, Any]]:
    root = run_root / "formtrig"
    runs: list[dict[str, Any]] = []
    for stats_path in sorted(root.glob(f"*_{target_id}/out/default/fuzzer_stats")):
        default_dir = stats_path.parent
        out_dir = default_dir.parent
        stats = read_stats(stats_path)
        progress = summarize_progress(default_dir / "formtrig_progress.jsonl")
        saved_non_trigger = int_value(stats.get("formtrig_saved_non_trigger_log_seen"))
        saved_triggered = int_value(stats.get("formtrig_saved_triggered_log_seen"))
        if progress["saved_non_trigger"]:
            saved_non_trigger = max(saved_non_trigger, int_value(progress["saved_non_trigger"]))
        if progress["saved_triggered"]:
            saved_triggered = max(saved_triggered, int_value(progress["saved_triggered"]))
        signal_status = "none"
        if saved_non_trigger > 0:
            signal_status = "pretrigger_guidance_seen"
        elif saved_triggered > 0 or int_value(stats.get("formtrig_triggered_execs")) > 0:
            signal_status = "terminal_seen"
        elif int_value(stats.get("formtrig_frontier_updates")) > 0:
            signal_status = "frontier_seen"
        runs.append(
            {
                "run": out_dir.parent.name,
                "out_dir": str(out_dir),
                "run_time_s": numeric(stats.get("run_time")),
                "execs_done": numeric(stats.get("execs_done")),
                "execs_per_sec": numeric(stats.get("execs_per_sec")),
                "reached_execs": int_value(stats.get("formtrig_reached_execs")),
                "triggered_execs": int_value(stats.get("formtrig_triggered_execs")),
                "queued_progress": int_value(stats.get("formtrig_queued_progress")),
                "frontier_updates": int_value(stats.get("formtrig_frontier_updates")),
                "typed_execs": int_value(stats.get("formtrig_typed_execs")),
                "typed_finds": int_value(stats.get("formtrig_typed_finds")),
                "saved_triggered": saved_triggered,
                "saved_non_trigger": saved_non_trigger,
                "best_df": numeric(stats.get("formtrig_best_df")),
                "best_dt": numeric(stats.get("formtrig_best_dt")),
                "progress": progress,
                "signal_status": signal_status,
            }
        )
    return runs


BASELINE_RE = re.compile(r"(?P<baseline>.+)_(?P<duration>\d+)s_rep(?P<rep>\d+)$")


def baseline_runs(baseline_root: Path, target_id: str) -> list[dict[str, Any]]:
    root = baseline_root / "magma"
    runs: list[dict[str, Any]] = []
    for run_dir in sorted(root.iterdir() if root.is_dir() else []):
        if not run_dir.is_dir():
            continue
        match = BASELINE_RE.match(run_dir.name)
        if not match:
            continue
        stats = read_stats(run_dir / "findings" / "default" / "fuzzer_stats")
        snapshots = monitor_snapshots(run_dir / "monitor", target_id)
        latest = next((row for row in snapshots if row.get("kind") == "final"), None)
        if latest is None and snapshots:
            latest = snapshots[-1]
        first_reach = next((row for row in snapshots if int_value(row.get("reached")) > 0), None)
        first_trigger = next(
            (row for row in snapshots if int_value(row.get("triggered")) > 0),
            None,
        )
        reached = int_value(latest.get("reached") if latest else 0)
        triggered = int_value(latest.get("triggered") if latest else 0)
        runs.append(
            {
                "run": run_dir.name,
                "source_root": str(baseline_root),
                "baseline": match.group("baseline"),
                "duration_s": int(match.group("duration")),
                "rep": int(match.group("rep")),
                "run_time_s": numeric(stats.get("run_time")),
                "execs_done": numeric(stats.get("execs_done")),
                "execs_per_sec": numeric(stats.get("execs_per_sec")),
                "reached": reached,
                "triggered": triggered,
                "reached_without_trigger": max(0, reached - triggered),
                "empirical_trigger_rate_per_reach": (
                    triggered / reached if reached > 0 else None
                ),
                "snapshot_count": len(snapshots),
                "latest_monitor_time_s": latest.get("time_s") if latest else None,
                "first_reach_time_s": first_reach.get("time_s") if first_reach else None,
                "first_trigger_time_s": first_trigger.get("time_s") if first_trigger else None,
            }
        )
    return runs


def duplicate_run_names(rows: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for row in rows:
        name = str(row.get("run") or "")
        if not name:
            continue
        if name in seen:
            duplicates.add(name)
        seen.add(name)
    return sorted(duplicates)


def resolve_duplicate_baseline_runs(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Keep the later source-root copy of a duplicate run name.

    Live recovery runs may combine an original baseline root with a sharded
    repair root.  The final merge command uses source order to prefer the shard
    for duplicate run names, so the live snapshot must use the same rule.
    """
    selected: dict[str, dict[str, Any]] = {}
    duplicate_details: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for index, row in enumerate(rows):
        name = str(row.get("run") or "")
        if not name:
            continue
        source_root = str(row.get("source_root") or "")
        if name not in selected:
            selected[name] = row
            order.append(name)
            continue
        previous = selected[name]
        details = duplicate_details.setdefault(
            name,
            {
                "run": name,
                "policy": "prefer-later",
                "sources": [
                    {
                        "source_root": str(previous.get("source_root") or ""),
                        "run_time_s": previous.get("run_time_s"),
                        "reached": previous.get("reached"),
                        "triggered": previous.get("triggered"),
                    }
                ],
            },
        )
        details["sources"].append(
            {
                "source_root": source_root,
                "run_time_s": row.get("run_time_s"),
                "reached": row.get("reached"),
                "triggered": row.get("triggered"),
            }
        )
        details["kept_source_root"] = source_root
        details["discarded_source_root"] = str(previous.get("source_root") or "")
        details["kept_index"] = index
        selected[name] = row
    resolved = [selected[name] for name in order if name in selected]
    duplicates = [duplicate_details[name] for name in sorted(duplicate_details)]
    return resolved, duplicates


def group_baselines(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for baseline in sorted({str(row["baseline"]) for row in rows}):
        selected = [row for row in rows if row["baseline"] == baseline]
        total_reached = sum(int_value(row.get("reached")) for row in selected)
        total_triggered = sum(int_value(row.get("triggered")) for row in selected)
        groups.append(
            {
                "baseline": baseline,
                "runs": len(selected),
                "triggered_runs": sum(1 for row in selected if int_value(row.get("triggered")) > 0),
                "total_reached": total_reached,
                "total_triggered": total_triggered,
                "total_reached_without_trigger": sum(
                    int_value(row.get("reached_without_trigger")) for row in selected
                ),
                "empirical_trigger_rate_per_reach": (
                    total_triggered / total_reached if total_reached > 0 else None
                ),
                "zero_trigger_runs": sum(
                    1
                    for row in selected
                    if int_value(row.get("reached")) > 0
                    and int_value(row.get("triggered")) == 0
                ),
                "zero_trigger_rule_of_three_95_upper_bound_per_reach": (
                    3.0 / total_reached
                    if total_reached > 0 and total_triggered == 0
                    else None
                ),
            }
        )
    return groups


def read_json_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def schedule_status(
    run_root: Path,
    metadata: dict[str, Any],
    baselines: list[dict[str, Any]],
) -> dict[str, Any]:
    audit = read_json_dict(run_root / "schedule_audit.json")
    expected = int_value(audit.get("baseline_run_count") or metadata.get("baseline_run_count"))
    observed = len(baselines)
    missing = max(0, expected - observed) if expected > 0 else None
    return {
        "audit_present": bool(audit),
        "verdict": audit.get("verdict") or "missing_schedule_audit",
        "baseline_run_count": expected,
        "observed_baseline_runs": observed,
        "missing_baseline_runs": missing,
        "baseline_jobs": int_value(audit.get("baseline_jobs") or metadata.get("baseline_jobs")),
        "baseline_batches": int_value(
            audit.get("baseline_batches") or metadata.get("baseline_batches")
        ),
        "formtrig_jobs": int_value(audit.get("formtrig_jobs") or metadata.get("formtrig_jobs")),
        "recommended_baseline_jobs_for_one_batch": (
            audit.get("recommended_baseline_jobs_for_one_batch")
            or metadata.get("baseline_run_count")
        ),
        "ideal_baseline_wall_s": audit.get("ideal_baseline_wall_s"),
    }


def summarize(
    run_root: Path,
    target_id: str,
    baseline_dirs: list[Path] | None = None,
) -> dict[str, Any]:
    formtrig = formtrig_runs(run_root, target_id)
    baseline_roots = baseline_dirs if baseline_dirs else [run_root / "baselines"]
    baselines = [
        row
        for baseline_root in baseline_roots
        for row in baseline_runs(baseline_root, target_id)
    ]
    raw_baselines = baselines
    baselines, duplicate_runs = resolve_duplicate_baseline_runs(raw_baselines)
    metadata_path = run_root / "run_metadata.json"
    metadata = {}
    if metadata_path.exists():
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            metadata = {}
    return {
        "snapshot_time_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target_id": target_id,
        "run_root": str(run_root),
        "baseline_root": str(baseline_roots[0]),
        "baseline_roots": [str(root) for root in baseline_roots],
        "metadata": metadata,
        "formtrig": {
            "runs": formtrig,
            "run_count": len(formtrig),
            "terminal_seen_runs": sum(
                1 for row in formtrig if row["signal_status"] == "terminal_seen"
            ),
            "pretrigger_guidance_seen_runs": sum(
                1 for row in formtrig if row["signal_status"] == "pretrigger_guidance_seen"
            ),
            "total_saved_triggered": sum(int_value(row.get("saved_triggered")) for row in formtrig),
            "total_saved_non_trigger": sum(
                int_value(row.get("saved_non_trigger")) for row in formtrig
            ),
        },
        "baselines": {
            "runs": baselines,
            "groups": group_baselines(baselines),
            "run_count": len(baselines),
            "raw_run_count": len(raw_baselines),
            "triggered_runs": sum(1 for row in baselines if int_value(row.get("triggered")) > 0),
            "duplicate_run_names": duplicate_run_names(raw_baselines),
            "duplicate_runs": duplicate_runs,
        },
        "schedule": schedule_status(run_root, metadata, baselines),
        "status_boundary": (
            "live_snapshot_only; final claims require formtrig_gate, "
            "baseline_guidance_gap, comparison, and evidence packaging"
        ),
    }


def cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def rate(value: Any) -> str:
    parsed = numeric(value)
    if parsed is None:
        return ""
    return f"{float(parsed):.6g}"


def to_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Live Matched Status: {payload['target_id']}",
        "",
        f"- snapshot: `{payload['snapshot_time_utc']}`",
        f"- run root: `{payload['run_root']}`",
        f"- baseline roots: `{', '.join(payload['baseline_roots'])}`",
        f"- boundary: {payload['status_boundary']}",
        "",
        "## Schedule",
        "",
        "| verdict | expected baseline runs | observed baseline runs | missing | baseline jobs | batches | one-batch jobs |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        (
            "| {verdict} | {expected} | {observed} | {missing} | {jobs} | {batches} | {one_batch} |".format(
                verdict=payload["schedule"].get("verdict", ""),
                expected=cell(payload["schedule"].get("baseline_run_count")),
                observed=cell(payload["schedule"].get("observed_baseline_runs")),
                missing=cell(payload["schedule"].get("missing_baseline_runs")),
                jobs=cell(payload["schedule"].get("baseline_jobs")),
                batches=cell(payload["schedule"].get("baseline_batches")),
                one_batch=cell(
                    payload["schedule"].get("recommended_baseline_jobs_for_one_batch")
                ),
            )
        ),
        "",
    ]
    duplicate_runs = payload["baselines"].get("duplicate_runs") or []
    if duplicate_runs:
        lines.extend(
            [
                "## Duplicate Baseline Runs",
                "",
                (
                    "Duplicate live run names were resolved with `prefer-later`, "
                    "matching the final shard merge policy."
                ),
                "",
                "| run | kept source | discarded source |",
                "| --- | --- | --- |",
            ]
        )
        for duplicate in duplicate_runs:
            lines.append(
                "| {run} | {kept} | {discarded} |".format(
                    run=cell(duplicate.get("run")),
                    kept=cell(duplicate.get("kept_source_root")),
                    discarded=cell(duplicate.get("discarded_source_root")),
                )
            )
        lines.append("")
    lines.extend(
        [
            "## FORMTRIG",
            "",
            "| run | time | execs | reached | triggered execs | saved T | saved non-T | frontier | typed finds | status |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for row in payload["formtrig"]["runs"]:
        lines.append(
            "| {run} | {time} | {execs} | {reached} | {triggered} | {saved_t} | {saved_nt} | {frontier} | {typed_finds} | {status} |".format(
                run=row["run"],
                time=cell(row.get("run_time_s")),
                execs=cell(row.get("execs_done")),
                reached=row.get("reached_execs", 0),
                triggered=row.get("triggered_execs", 0),
                saved_t=row.get("saved_triggered", 0),
                saved_nt=row.get("saved_non_trigger", 0),
                frontier=row.get("frontier_updates", 0),
                typed_finds=row.get("typed_finds", 0),
                status=row.get("signal_status", ""),
            )
        )
    lines.extend(
        [
            "",
            "## Baselines",
            "",
            "| baseline | runs | triggered runs | total R | total T | R without T | empirical T/R | zero-T 95% ub |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for group in payload["baselines"]["groups"]:
        lines.append(
            "| {baseline} | {runs} | {triggered_runs} | {total_r} | {total_t} | {without_t} | {rate} | {upper_bound} |".format(
                baseline=group["baseline"],
                runs=group["runs"],
                triggered_runs=group["triggered_runs"],
                total_r=group["total_reached"],
                total_t=group["total_triggered"],
                without_t=group["total_reached_without_trigger"],
                rate=rate(group.get("empirical_trigger_rate_per_reach")),
                upper_bound=rate(
                    group.get("zero_trigger_rule_of_three_95_upper_bound_per_reach")
                ),
            )
        )
    lines.extend(
        [
            "",
            (
                "The zero-T upper bound is a descriptive rule-of-three proxy for "
                "matched live runs with reached executions but no trigger events; "
                "it is not a proof that baseline mutations are independent."
            ),
        ]
    )
    lines.extend(["", "## Baseline Runs", ""])
    lines.extend(
        [
            "| run | time | execs | first R | latest monitor | R | T |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in payload["baselines"]["runs"]:
        lines.append(
            "| {run} | {time} | {execs} | {first_r} | {latest} | {r} | {t} |".format(
                run=row["run"],
                time=cell(row.get("run_time_s")),
                execs=cell(row.get("execs_done")),
                first_r=cell(row.get("first_reach_time_s")),
                latest=cell(row.get("latest_monitor_time_s")),
                r=row.get("reached", 0),
                t=row.get("triggered", 0),
            )
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize live Magma matched-run status.")
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--run-root", required=True)
    parser.add_argument(
        "--baseline-dir",
        action="append",
        help="baseline root containing magma/; may be repeated for sharded live runs",
    )
    parser.add_argument("--format", choices=["json", "md"], default="md")
    parser.add_argument("--out-json")
    parser.add_argument("--out-md")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = summarize(
        Path(args.run_root),
        args.target_id,
        [Path(path) for path in args.baseline_dir] if args.baseline_dir else None,
    )
    if args.out_json:
        Path(args.out_json).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_json).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if args.out_md:
        Path(args.out_md).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out_md).write_text(to_markdown(payload), encoding="utf-8")
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(to_markdown(payload), end="")


if __name__ == "__main__":
    main()
