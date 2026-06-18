#!/usr/bin/env python3
"""Build a baseline summary from in-flight Magma monitor directories.

The normal Magma baseline runner writes `runs/*/run_record.json` only after each
baseline run exits.  This helper reads the live `magma/<run>/monitor` and AFL++
`fuzzer_stats` directories directly so guidance-gap analysis can be performed
mid-run without perturbing the fuzzers.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from tools.summarize_post_reach_baselines import group_rows, write_tsv


BASELINE_RE = re.compile(r"(?P<baseline>.+)_(?P<duration>\d+)s_rep(?P<rep>\d+)$")


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return default


def numeric(value: Any) -> int | float | None:
    if value is None or value == "":
        return None
    try:
        parsed = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    if parsed.is_integer():
        return int(parsed)
    return parsed


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


def latest_snapshot(snapshots: list[dict[str, Any]]) -> dict[str, Any] | None:
    final = next((row for row in snapshots if row.get("kind") == "final"), None)
    if final is not None:
        return final
    return snapshots[-1] if snapshots else None


def monitor_record(monitor_dir: Path, target_id: str) -> dict[str, Any] | None:
    snapshots = monitor_snapshots(monitor_dir, target_id)
    latest = latest_snapshot(snapshots)
    if latest is None:
        return None
    first_reach = next((row for row in snapshots if int_value(row.get("reached")) > 0), None)
    first_trigger = next(
        (row for row in snapshots if int_value(row.get("triggered")) > 0),
        None,
    )
    return {
        "bug_id": target_id,
        "first_reach": first_reach,
        "first_trigger": first_trigger,
        "latest": latest,
        "monitor_dir": str(monitor_dir),
        "reached": int_value(latest.get("reached")),
        "snapshot_count": len(snapshots),
        "triggered": int_value(latest.get("triggered")),
    }


def run_row(run_dir: Path, target_id: str) -> dict[str, Any] | None:
    match = BASELINE_RE.match(run_dir.name)
    if not match:
        return None

    stats = read_stats(run_dir / "findings" / "default" / "fuzzer_stats")
    monitor = monitor_record(run_dir / "monitor", target_id)
    if monitor is None:
        return None

    first_reach = monitor.get("first_reach") if isinstance(monitor.get("first_reach"), dict) else {}
    first_trigger = (
        monitor.get("first_trigger")
        if isinstance(monitor.get("first_trigger"), dict)
        else {}
    )
    triggered = int_value(monitor.get("triggered"))
    trigger_time = numeric(first_trigger.get("time_s"))
    return {
        "baseline": match.group("baseline"),
        "budget": int(match.group("duration")),
        "corpus_count": numeric(stats.get("corpus_count")),
        "execs_done": numeric(stats.get("execs_done")),
        "execs_per_sec": numeric(stats.get("execs_per_sec")),
        "live_snapshot": True,
        "magma_first_reach_time_s": numeric(first_reach.get("time_s")),
        "magma_first_trigger_time_s": trigger_time,
        "magma_monitor": monitor,
        "magma_reached": int_value(monitor.get("reached")),
        "magma_snapshot_count": int_value(monitor.get("snapshot_count")),
        "magma_triggered": triggered,
        "rep": int(match.group("rep")),
        "run_record": "",
        "run_time": numeric(stats.get("run_time")),
        "saved_crashes": numeric(stats.get("saved_crashes")),
        "saved_hangs": numeric(stats.get("saved_hangs")),
        "success": triggered > 0,
        "target_id": target_id,
        "trigger_time_kind": "magma_monitor_upper_bound" if triggered > 0 else None,
        "trigger_time_s": trigger_time if triggered > 0 else None,
    }


def summarize(run_root: Path, target_id: str) -> dict[str, Any]:
    root = run_root / "magma" if (run_root / "magma").is_dir() else run_root
    rows = [
        row
        for run_dir in sorted(root.iterdir() if root.is_dir() else [])
        if run_dir.is_dir()
        for row in [run_row(run_dir, target_id)]
        if row is not None
    ]
    rows.sort(
        key=lambda row: (
            str(row.get("target_id")),
            str(row.get("baseline")),
            int(row.get("budget") or 0),
            int(row.get("rep") or 0),
        )
    )
    return {
        "analysis_time_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "claim_boundary": (
            "live_snapshot_only; use the normal baseline summary after all runs finish "
            "for final comparison claims"
        ),
        "groups": group_rows(rows),
        "records": rows,
        "run_root": str(run_root),
        "target_id": target_id,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-tsv", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = summarize(args.run_root, args.target_id)
    out_json = Path(args.out_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_tsv(Path(args.out_tsv), payload["records"])


if __name__ == "__main__":
    main()
