#!/usr/bin/env python3
"""Replay GPAC_3403 typed-retained candidates through an endpoint command.

This tool is the endpoint half of the typed-retained evidence loop.  It reads
typed_retained_records.jsonl, runs each retained input through a GPAC endpoint
command, emits endpoint logs using the same variant_XXXXXX.endpoint_N naming
used by the GPAC frontier sweep, and writes an enriched records JSONL that can
be fed back into the structure/package audit.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shlex
import sys
import time
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from types import ModuleType
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTIER_SWEEP = REPO_ROOT / "tools" / "gpac3403_hevc_frontier_sweep.py"


def load_frontier_sweep() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "gpac3403_hevc_frontier_sweep_for_typed_retained_endpoint",
        FRONTIER_SWEEP,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load GPAC frontier sweep helper: {FRONTIER_SWEEP}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def read_records(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"records JSONL not found: {path}")
    records: list[dict[str, Any]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        record = json.loads(raw)
        record.setdefault("index", len(records))
        record["_source_line"] = line_no
        records.append(record)
    return records


def record_d_f(record: dict[str, Any]) -> float | None:
    value = record.get("d_f_spec_lifted")
    if value is None:
        return None
    return float(value)


def select_records(
    records: list[dict[str, Any]],
    max_records: int,
    d_f_max: float | None,
    selection: str,
) -> list[dict[str, Any]]:
    selected = []
    for record in records:
        path = Path(str(record.get("path") or ""))
        if not path.is_file():
            continue
        d_f = record_d_f(record)
        if d_f_max is not None and (d_f is None or d_f > d_f_max):
            continue
        selected.append(record)
    if selection == "best-d-f":
        selected.sort(
            key=lambda record: (
                record_d_f(record) if record_d_f(record) is not None else 1.0e300,
                int(record.get("index") or 0),
            )
        )
    elif selection != "input-order":
        raise ValueError(f"unknown selection policy: {selection}")
    if max_records > 0:
        selected = selected[:max_records]
    return selected


def exit_counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for record in records:
        for probe in record.get("endpoint_probes") or []:
            key = "timeout" if probe.get("timed_out") else str(probe.get("exit_code"))
            counts[key] += 1
    return dict(sorted(counts.items()))


def summarize(
    *,
    records_path: Path,
    logs_dir: Path,
    endpoint_cmd: list[str],
    endpoint_env_keys: list[str],
    all_records: list[dict[str, Any]],
    selected: list[dict[str, Any]],
    enriched: list[dict[str, Any]],
    positive_control: list[dict[str, Any]],
    started: float,
    args: argparse.Namespace,
) -> dict[str, Any]:
    endpoint_probe_runs = sum(len(record.get("endpoint_probes") or []) for record in enriched)
    endpoint_sanitizer_crashes = sum(
        1
        for record in enriched
        if any(probe.get("sanitizer_crash") for probe in record.get("endpoint_probes") or [])
    )
    endpoint_native_crashes = sum(
        1
        for record in enriched
        if any(probe.get("native_crash") for probe in record.get("endpoint_probes") or [])
    )
    endpoint_timeouts = sum(
        1
        for record in enriched
        for probe in record.get("endpoint_probes") or []
        if probe.get("timed_out")
    )
    d_f_values = [record_d_f(record) for record in enriched if record_d_f(record) is not None]
    return {
        "schema": "formtrig_gpac3403_typed_retained_endpoint_replay_v1",
        "records_jsonl": str(records_path),
        "logs_dir": str(logs_dir),
        "duration_s": round(time.time() - started, 3),
        "input_records": len(all_records),
        "existing_inputs": sum(1 for record in all_records if Path(str(record.get("path") or "")).is_file()),
        "selected_records": len(selected),
        "replayed_records": len(enriched),
        "endpoint_replayed_variants": len(enriched),
        "skipped_missing_inputs": sum(
            1 for record in all_records if not Path(str(record.get("path") or "")).is_file()
        ),
        "d_f_spec_lifted_min": min(d_f_values) if d_f_values else None,
        "d_f_spec_lifted_max": max(d_f_values) if d_f_values else None,
        "endpoint_cmd": endpoint_cmd,
        "endpoint_env_keys": endpoint_env_keys,
        "endpoint_replays": args.endpoint_replays,
        "endpoint_timeout": args.endpoint_timeout,
        "endpoint_sanitizer_exit_code": args.endpoint_sanitizer_exit_code,
        "selection": args.selection,
        "max_records": args.max_records,
        "d_f_max": args.d_f_max,
        "endpoint_probe_runs": endpoint_probe_runs,
        "endpoint_sanitizer_crashes": endpoint_sanitizer_crashes,
        "endpoint_native_crashes": endpoint_native_crashes,
        "endpoint_timeouts": endpoint_timeouts,
        "endpoint_exit_code_counts": exit_counts(enriched),
        "positive_control_probe_runs": len(positive_control),
        "positive_control_sanitizer_crashes": sum(1 for probe in positive_control if probe.get("sanitizer_crash")),
        "positive_control_native_crashes": sum(1 for probe in positive_control if probe.get("native_crash")),
        "positive_control": positive_control,
    }


def build_replay(args: argparse.Namespace) -> dict[str, Any]:
    sweep = load_frontier_sweep()
    run_dir = args.run_dir.resolve()
    records_path = args.records_jsonl or run_dir / "typed_retained_records.jsonl"
    logs_dir = run_dir / "logs"
    endpoint_cmd = shlex.split(args.endpoint_cmd)
    if not endpoint_cmd:
        raise SystemExit("--endpoint-cmd must not be empty")
    endpoint_env = sweep.parse_env_pairs(args.endpoint_env)
    all_records = read_records(records_path)
    selected = select_records(all_records, args.max_records, args.d_f_max, args.selection)
    started = time.time()
    enriched: list[dict[str, Any]] = []

    for record in selected:
        index = int(record.get("index") or 0)
        probes = sweep.run_endpoint_probes(
            input_path=str(record["path"]),
            kind="variant",
            log_prefix=f"variant_{index:06d}",
            endpoint_cmd=endpoint_cmd,
            out_dir=run_dir,
            endpoint_env=endpoint_env,
            timeout_s=args.endpoint_timeout,
            reps=args.endpoint_replays,
            sanitizer_exit_code=args.endpoint_sanitizer_exit_code,
        )
        enriched_record = dict(record)
        enriched_record["endpoint_probes"] = [asdict(probe) for probe in probes]
        enriched_record["endpoint_replay_source"] = "FORMTRIG_TYPED_RETAIN"
        enriched.append(enriched_record)

    positive_control: list[dict[str, Any]] = []
    if args.endpoint_positive_control:
        probes = sweep.run_endpoint_probes(
            input_path=str(args.endpoint_positive_control),
            kind="positive_control",
            log_prefix="positive_control",
            endpoint_cmd=endpoint_cmd,
            out_dir=run_dir,
            endpoint_env=endpoint_env,
            timeout_s=args.endpoint_timeout,
            reps=args.endpoint_replays,
            sanitizer_exit_code=args.endpoint_sanitizer_exit_code,
        )
        positive_control = [asdict(probe) for probe in probes]

    summary = summarize(
        records_path=records_path,
        logs_dir=logs_dir,
        endpoint_cmd=endpoint_cmd,
        endpoint_env_keys=sorted(endpoint_env),
        all_records=all_records,
        selected=selected,
        enriched=enriched,
        positive_control=positive_control,
        started=started,
        args=args,
    )
    return {
        "summary": summary,
        "records": enriched,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--records-jsonl", type=Path)
    parser.add_argument("--endpoint-cmd", required=True, help="Shell-like command; use @@ for the retained input path.")
    parser.add_argument("--endpoint-env", action="append", default=[])
    parser.add_argument("--endpoint-timeout", type=float, default=5.0)
    parser.add_argument("--endpoint-replays", type=int, default=1)
    parser.add_argument("--endpoint-sanitizer-exit-code", type=int, default=86)
    parser.add_argument("--endpoint-positive-control", type=Path)
    parser.add_argument("--max-records", type=int, default=0, help="0 means replay every selected record.")
    parser.add_argument("--d-f-max", type=float)
    parser.add_argument("--selection", choices=("input-order", "best-d-f"), default="input-order")
    parser.add_argument("--out-summary", type=Path)
    parser.add_argument("--out-records-jsonl", type=Path)
    args = parser.parse_args(argv)

    if args.endpoint_timeout <= 0:
        parser.error("--endpoint-timeout must be positive")
    if args.endpoint_replays <= 0:
        parser.error("--endpoint-replays must be positive")
    if args.max_records < 0:
        parser.error("--max-records must be non-negative")

    result = build_replay(args)
    run_dir = args.run_dir.resolve()
    summary_path = args.out_summary or run_dir / "typed_retained_endpoint_replay_summary.json"
    records_path = args.out_records_jsonl or run_dir / "typed_retained_endpoint_records.jsonl"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    records_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(result["summary"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with records_path.open("w", encoding="utf-8") as handle:
        for record in result["records"]:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    print(json.dumps(result["summary"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
