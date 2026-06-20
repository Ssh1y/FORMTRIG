#!/usr/bin/env python3
"""Summarize harvested post-reach baseline run records."""

from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from pathlib import Path
from typing import Any


FIELDS = [
    "target_id",
    "baseline",
    "budget",
    "rep",
    "valid_run",
    "returncode",
    "success",
    "trigger_time_s",
    "trigger_time_kind",
    "run_time",
    "execs_done",
    "execs_per_sec",
    "corpus_count",
    "saved_crashes",
    "saved_hangs",
    "magma_reached",
    "magma_triggered",
    "magma_first_reach_time_s",
    "magma_first_trigger_time_s",
    "magma_snapshot_count",
]


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def read_json_if_exists(path: Path) -> Any:
    if not path.is_file():
        return {}
    try:
        return read_json(path)
    except json.JSONDecodeError:
        return {}


def numeric(value: Any) -> int | float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            parsed = float(value)
        except ValueError:
            return None
        if parsed.is_integer():
            return int(parsed)
        return parsed
    return None


def infer_rep(record: dict[str, Any]) -> int | None:
    config_path = record.get("config_path")
    if isinstance(config_path, str) and config_path:
        path = Path(config_path)
        if path.exists():
            try:
                config = read_json(path)
            except json.JSONDecodeError:
                config = {}
            rep = numeric(config.get("rep"))
            if isinstance(rep, int):
                return rep

    run_id = record.get("run_id")
    if isinstance(run_id, str):
        match = re.search(r":rep(\d+)$", run_id)
        if match:
            return int(match.group(1))
    return None


def flatten_record(path: Path) -> dict[str, Any]:
    record = read_json(path)
    status = read_json_if_exists(path.parent / "status.json")
    returncode = numeric(status.get("returncode")) if isinstance(status, dict) else None
    valid_run = returncode is None or returncode in (0, 124)
    stats = record.get("stats") if isinstance(record.get("stats"), dict) else {}
    monitor = (
        record.get("magma_monitor")
        if isinstance(record.get("magma_monitor"), dict)
        else {}
    )
    first_reach = (
        monitor.get("first_reach")
        if isinstance(monitor.get("first_reach"), dict)
        else {}
    )
    first_trigger = (
        monitor.get("first_trigger")
        if isinstance(monitor.get("first_trigger"), dict)
        else {}
    )
    row = {
        "target_id": record.get("target_id"),
        "baseline": record.get("baseline"),
        "budget": record.get("budget"),
        "rep": infer_rep(record),
        "valid_run": valid_run,
        "returncode": returncode,
        "success": bool(record.get("success")) and valid_run,
        "trigger_time_s": record.get("trigger_time_s"),
        "trigger_time_kind": record.get("trigger_time_kind"),
        "run_time": stats.get("run_time"),
        "execs_done": stats.get("execs_done"),
        "execs_per_sec": stats.get("execs_per_sec"),
        "corpus_count": stats.get("corpus_count"),
        "saved_crashes": stats.get("saved_crashes"),
        "saved_hangs": stats.get("saved_hangs"),
        "magma_reached": stats.get("magma_reached"),
        "magma_triggered": stats.get("magma_triggered"),
        "magma_first_reach_time_s": first_reach.get("time_s"),
        "magma_first_trigger_time_s": first_trigger.get("time_s"),
        "magma_snapshot_count": monitor.get("snapshot_count"),
        "run_record": str(path),
    }
    return row


def median(values: list[float]) -> float | int | None:
    if not values:
        return None
    result = statistics.median(values)
    if float(result).is_integer():
        return int(result)
    return result


def summarize_group(rows: list[dict[str, Any]]) -> dict[str, Any]:
    valid_rows = [row for row in rows if row.get("valid_run", True)]
    successes = [row for row in valid_rows if row["success"]]
    trigger_times = [
        float(value)
        for row in successes
        if (value := numeric(row.get("trigger_time_s"))) is not None
    ]
    magma_t = [
        int(value)
        for row in valid_rows
        if isinstance(value := numeric(row.get("magma_triggered")), int)
    ]
    execs = [
        int(value)
        for row in valid_rows
        if isinstance(value := numeric(row.get("execs_done")), int)
    ]
    return {
        "baseline": rows[0].get("baseline"),
        "budget": rows[0].get("budget"),
        "target_id": rows[0].get("target_id"),
        "attempted_reps": len(rows),
        "invalid_reps": len(rows) - len(valid_rows),
        "reps": len(valid_rows),
        "successes": len(successes),
        "success_rate": len(successes) / len(valid_rows) if valid_rows else 0.0,
        "min_trigger_time_s": median([min(trigger_times)]) if trigger_times else None,
        "median_trigger_time_s": median(trigger_times),
        "max_magma_triggered": max(magma_t) if magma_t else None,
        "median_magma_triggered": median([float(value) for value in magma_t]),
        "median_execs_done": median([float(value) for value in execs]),
    }


def group_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, Any, Any], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row.get("target_id"), row.get("baseline"), row.get("budget"))
        groups.setdefault(key, []).append(row)
    return [summarize_group(group) for _, group in sorted(groups.items())]


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=FIELDS,
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({field: tsv_value(row.get(field)) for field in FIELDS})


def tsv_value(value: Any) -> Any:
    if value is None:
        return "NA"
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def write_json(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "records": rows,
        "groups": group_rows(rows),
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, help="directory containing run_record.json files")
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-tsv", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.root)
    if not root.is_dir():
        raise SystemExit(f"summary root is not a directory: {root}")
    rows = [flatten_record(path) for path in sorted(root.rglob("run_record.json"))]
    rows.sort(
        key=lambda row: (
            str(row.get("target_id")),
            str(row.get("baseline")),
            int(row.get("budget") or 0),
            int(row.get("rep") or 0),
        )
    )
    write_json(Path(args.out_json), rows)
    write_tsv(Path(args.out_tsv), rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
