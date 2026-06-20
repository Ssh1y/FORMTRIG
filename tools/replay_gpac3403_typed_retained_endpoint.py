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
import shutil
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
DEFAULT_STRUCTURE_HOOK = REPO_ROOT / "scripts" / "formtrig_hooks" / "hevc_annexb_structure_hook.py"
ENDPOINT_RELEVANT_TYPES = {0, 1, 5, 14, 16, 19, 20, 21, 32, 33, 34, 49}
STRUCTURE_SELECTIONS = {"structure-best", "df-structure", "df-structure-op-diverse"}


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


def load_structure_hook(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("gpac3403_retained_structure_hook", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load GPAC structure hook: {path}")
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


def record_op(record: dict[str, Any]) -> int:
    value = record.get("op")
    if value is None:
        return -1
    return int(value)


def d_f_sort_key(record: dict[str, Any]) -> tuple[float, int]:
    d_f = record_d_f(record)
    return (
        d_f if d_f is not None else 1.0e300,
        int(record.get("index") or 0),
    )


def evenly_spaced_values(values: list[int], count: int) -> list[int]:
    if count <= 0 or count >= len(values):
        return values
    if count == 1:
        return [values[0]]
    chosen: list[int] = []
    seen: set[int] = set()
    last = len(values) - 1
    for index in range(count):
        value = values[round(index * last / (count - 1))]
        if value in seen:
            continue
        chosen.append(value)
        seen.add(value)
    for value in values:
        if len(chosen) >= count:
            break
        if value not in seen:
            chosen.append(value)
            seen.add(value)
    return chosen


def select_op_diverse(records: list[dict[str, Any]], max_records: int) -> list[dict[str, Any]]:
    groups: dict[int, list[dict[str, Any]]] = {}
    for record in records:
        groups.setdefault(record_op(record), []).append(record)
    for group in groups.values():
        group.sort(key=d_f_sort_key)
    ops = sorted(groups)
    if max_records > 0:
        ops = evenly_spaced_values(ops, min(max_records, len(ops)))
    selected: list[dict[str, Any]] = []
    depth = 0
    while True:
        added = False
        for op in ops:
            group = groups[op]
            if depth >= len(group):
                continue
            selected.append(group[depth])
            added = True
            if max_records > 0 and len(selected) >= max_records:
                return selected
        if not added:
            return selected
        depth += 1


def structure_profile(record: dict[str, Any], hook: ModuleType) -> dict[str, Any]:
    path = Path(str(record.get("path") or ""))
    if not path.is_file():
        return {
            "available": False,
            "score": 0,
            "nalu_count": 0,
            "unique_types": [],
            "unique_layers": [],
            "size": 0,
        }

    data = path.read_bytes()
    nalus = hook.parse_nalus(data)
    types = [hook.nalu_type(data, nalu) for nalu in nalus]
    layers = [hook.layer_id(data, nalu) for nalu in nalus]
    unique_types = sorted({value for value in types if value >= 0})
    unique_layers = sorted(set(layers))
    parameter_count = sum(1 for value in types if value in {32, 33, 34})
    vcl_count = sum(1 for value in types if 0 <= value <= 31)
    extractor_count = sum(1 for value in types if value == 49)
    endpoint_type_count = sum(1 for value in types if value in ENDPOINT_RELEVANT_TYPES)
    high_layer_count = sum(1 for value in layers if value > 4)
    max_layer = max(layers) if layers else None
    score = (
        len(nalus) * 16
        + len(unique_types) * 24
        + len(unique_layers) * 16
        + endpoint_type_count * 8
        + parameter_count * 10
        + vcl_count * 8
        + extractor_count * 80
        + high_layer_count * 6
        + min(len(data), 65536) // 128
    )
    return {
        "available": True,
        "score": score,
        "nalu_count": len(nalus),
        "unique_types": unique_types,
        "unique_layers": unique_layers,
        "max_layer": max_layer,
        "parameter_count": parameter_count,
        "vcl_count": vcl_count,
        "extractor_count": extractor_count,
        "endpoint_type_count": endpoint_type_count,
        "high_layer_count": high_layer_count,
        "size": len(data),
    }


def select_structure_best(
    records: list[dict[str, Any]],
    max_records: int,
    hook: ModuleType,
    *,
    d_f_first: bool = False,
) -> list[dict[str, Any]]:
    scored: list[dict[str, Any]] = []
    for record in records:
        profile = structure_profile(record, hook)
        enriched = dict(record)
        enriched["endpoint_selection_profile"] = profile
        scored.append(enriched)

    if d_f_first:
        scored.sort(
            key=lambda record: (
                record_d_f(record) if record_d_f(record) is not None else 1.0e300,
                -int(record["endpoint_selection_profile"].get("score") or 0),
                -int(record["endpoint_selection_profile"].get("nalu_count") or 0),
                -int(record["endpoint_selection_profile"].get("size") or 0),
                int(record.get("index") or 0),
            )
        )
    else:
        scored.sort(
            key=lambda record: (
                -int(record["endpoint_selection_profile"].get("score") or 0),
                -int(record["endpoint_selection_profile"].get("nalu_count") or 0),
                -int(record["endpoint_selection_profile"].get("size") or 0),
                record_d_f(record) if record_d_f(record) is not None else 1.0e300,
                int(record.get("index") or 0),
            )
        )
    if max_records > 0:
        scored = scored[:max_records]
    return scored


def structure_sort_key(record: dict[str, Any]) -> tuple[int, int, int, float, int]:
    profile = record.get("endpoint_selection_profile") or {}
    return (
        -int(profile.get("score") or 0),
        -int(profile.get("nalu_count") or 0),
        -int(profile.get("size") or 0),
        record_d_f(record) if record_d_f(record) is not None else 1.0e300,
        int(record.get("index") or 0),
    )


def order_bucket_by_op_coverage(records: list[dict[str, Any]], budget: int) -> list[dict[str, Any]]:
    groups: dict[int, list[dict[str, Any]]] = {}
    for record in records:
        groups.setdefault(record_op(record), []).append(record)
    for group in groups.values():
        group.sort(key=structure_sort_key)

    ordered_ops = sorted(groups)
    representative_ops = ordered_ops
    if budget > 0 and budget < len(ordered_ops):
        representative_ops = evenly_spaced_values(ordered_ops, budget)

    selected: list[dict[str, Any]] = []
    selected_ids: set[int] = set()
    for op in representative_ops:
        record = groups[op][0]
        selected.append(record)
        selected_ids.add(id(record))
        if budget > 0 and len(selected) >= budget:
            return selected

    leftovers = [record for record in records if id(record) not in selected_ids]
    leftovers.sort(key=structure_sort_key)
    for record in leftovers:
        selected.append(record)
        if budget > 0 and len(selected) >= budget:
            break
    return selected


def select_df_structure_op_diverse(
    records: list[dict[str, Any]],
    max_records: int,
    hook: ModuleType,
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for record in records:
        copy = dict(record)
        copy["endpoint_selection_profile"] = structure_profile(record, hook)
        enriched.append(copy)

    buckets: dict[float, list[dict[str, Any]]] = {}
    for record in enriched:
        d_f = record_d_f(record)
        key = d_f if d_f is not None else 1.0e300
        buckets.setdefault(key, []).append(record)

    selected: list[dict[str, Any]] = []
    for d_f in sorted(buckets):
        if max_records > 0 and len(selected) >= max_records:
            break
        remaining = max_records - len(selected) if max_records > 0 else 0
        bucket_order = order_bucket_by_op_coverage(buckets[d_f], remaining)
        selected.extend(bucket_order)
        if max_records > 0 and len(selected) >= max_records:
            selected = selected[:max_records]
            break
    return selected


def select_records(
    records: list[dict[str, Any]],
    max_records: int,
    d_f_max: float | None,
    selection: str,
    structure_hook: ModuleType | None = None,
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
    elif selection == "op-diverse":
        selected = select_op_diverse(selected, max_records)
        return selected
    elif selection == "structure-best":
        if structure_hook is None:
            raise ValueError("structure-best selection requires a structure hook")
        selected = select_structure_best(selected, max_records, structure_hook)
        return selected
    elif selection == "df-structure":
        if structure_hook is None:
            raise ValueError("df-structure selection requires a structure hook")
        selected = select_structure_best(selected, max_records, structure_hook, d_f_first=True)
        return selected
    elif selection == "df-structure-op-diverse":
        if structure_hook is None:
            raise ValueError("df-structure-op-diverse selection requires a structure hook")
        selected = select_df_structure_op_diverse(selected, max_records, structure_hook)
        return selected
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


def endpoint_variant_input_path(record: dict[str, Any], run_dir: Path, suffix: str) -> Path:
    source = Path(str(record["path"]))
    if not suffix:
        return source
    index = int(record.get("index") or 0)
    inputs_dir = run_dir / "endpoint_inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    staged = inputs_dir / f"variant_{index:06d}{suffix}"
    shutil.copy2(source, staged)
    return staged


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
    structure_profiles = [
        record.get("endpoint_selection_profile")
        for record in enriched
        if isinstance(record.get("endpoint_selection_profile"), dict)
    ]
    structure_scores = [
        int(profile.get("score") or 0)
        for profile in structure_profiles
        if profile.get("available")
    ]
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
        "endpoint_variant_suffix": args.endpoint_variant_suffix,
        "endpoint_variant_inputs_dir": str(args.run_dir.resolve() / "endpoint_inputs")
        if args.endpoint_variant_suffix
        else None,
        "selection": args.selection,
        "max_records": args.max_records,
        "d_f_max": args.d_f_max,
        "structure_hook": str(args.structure_hook) if args.selection in STRUCTURE_SELECTIONS else None,
        "structure_profiled_records": len(structure_profiles),
        "structure_score_min": min(structure_scores) if structure_scores else None,
        "structure_score_max": max(structure_scores) if structure_scores else None,
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
    structure_hook = (
        load_structure_hook(args.structure_hook)
        if args.selection in STRUCTURE_SELECTIONS
        else None
    )
    selected = select_records(
        all_records,
        args.max_records,
        args.d_f_max,
        args.selection,
        structure_hook,
    )
    started = time.time()
    enriched: list[dict[str, Any]] = []

    for record in selected:
        index = int(record.get("index") or 0)
        endpoint_input = endpoint_variant_input_path(record, run_dir, args.endpoint_variant_suffix)
        probes = sweep.run_endpoint_probes(
            input_path=str(endpoint_input),
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
        if endpoint_input != Path(str(record["path"])):
            enriched_record["endpoint_input_path"] = str(endpoint_input)
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
    parser.add_argument(
        "--endpoint-variant-suffix",
        default="",
        help="Optional suffix used when staging retained variant inputs before endpoint replay.",
    )
    parser.add_argument("--endpoint-positive-control", type=Path)
    parser.add_argument("--max-records", type=int, default=0, help="0 means replay every selected record.")
    parser.add_argument("--d-f-max", type=float)
    parser.add_argument(
        "--selection",
        choices=(
            "input-order",
            "best-d-f",
            "op-diverse",
            "structure-best",
            "df-structure",
            "df-structure-op-diverse",
        ),
        default="input-order",
    )
    parser.add_argument("--structure-hook", type=Path, default=DEFAULT_STRUCTURE_HOOK)
    parser.add_argument("--out-summary", type=Path)
    parser.add_argument("--out-records-jsonl", type=Path)
    args = parser.parse_args(argv)

    if args.endpoint_timeout <= 0:
        parser.error("--endpoint-timeout must be positive")
    if args.endpoint_replays <= 0:
        parser.error("--endpoint-replays must be positive")
    if args.max_records < 0:
        parser.error("--max-records must be non-negative")
    if args.endpoint_variant_suffix and not args.endpoint_variant_suffix.startswith("."):
        parser.error("--endpoint-variant-suffix must be empty or start with '.'")

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
