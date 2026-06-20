#!/usr/bin/env python3
"""Audit GPAC_3403 HEVC extractor subpath from FORMTRIG runtime logs."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SEMANTIC_BY_SITE = {
    ("gf_isom_nalu_sample_rewrite", "809", "guard"): "outer_hevc_extractor_error",
    ("gf_isom_nalu_sample_rewrite", "844", "guard"): "outer_invalid_nal_size",
    ("process_extractor", "119", "lifecycle_event"): "extractor_loop_entry",
    ("process_extractor", "123", "guard"): "constructor_mode",
    ("process_extractor", "151", "guard"): "reference_track_present",
    ("process_extractor", "154", "opposite_producer"): "no_reference_track_ok_return",
    ("process_extractor", "181", "guard"): "missing_reference_sample_error",
    ("process_extractor", "182", "guard"): "negative_sample_offset_error",
    ("process_extractor", "207", "guard"): "referred_size_ok",
    ("process_extractor", "248", "opposite_producer"): "referred_size_too_large_ok_path",
}

ERROR_SEMANTICS = {
    "outer_hevc_extractor_error",
    "outer_invalid_nal_size",
    "missing_reference_sample_error",
    "negative_sample_offset_error",
}

OK_BARRIER_SEMANTICS = {
    "no_reference_track_ok_return",
    "referred_size_too_large_ok_path",
}


@dataclass(frozen=True)
class Binding:
    semantic: str
    role: str
    event_id: int
    function: str
    line: str
    value_mode: str


def event_id_to_int(raw: str) -> int | None:
    text = (raw or "").strip().lower()
    if not text:
        return None
    if text.startswith("0x"):
        text = text[2:]
    try:
        return int(text, 16)
    except ValueError:
        return None


def load_event_map(path: Path) -> dict[int, Binding]:
    bindings: dict[int, Binding] = {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            event_id = event_id_to_int(row.get("event_id", ""))
            if event_id is None:
                continue
            function = row.get("function", "")
            line = row.get("line", "")
            role = row.get("role", "")
            semantic = SEMANTIC_BY_SITE.get((function, line, role))
            if not semantic:
                continue
            bindings[event_id] = Binding(
                semantic=semantic,
                role=role,
                event_id=event_id,
                function=function,
                line=line,
                value_mode=row.get("value_mode", ""),
            )
    return bindings


def source_id_from_component(component: dict[str, Any]) -> int | None:
    raw = component.get("source_id")
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        parsed = event_id_to_int(raw)
        if parsed is not None:
            return parsed
        try:
            return int(raw, 0)
        except ValueError:
            return None
    return None


def positive_value(component: dict[str, Any]) -> bool:
    value = component.get("value")
    if isinstance(value, (int, float)):
        return value > 0
    if isinstance(value, str):
        try:
            return int(value, 0) > 0
        except ValueError:
            return False
    return False


def load_records(path: Path | None) -> dict[str, dict[str, Any]]:
    if not path:
        return {}
    records: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            record = json.loads(line)
            runtime_log = record.get("runtime_log")
            if isinstance(runtime_log, str):
                records[runtime_log] = record
    return records


def runtime_records(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def summarize_runtime(
    path: Path,
    bindings: dict[int, Binding],
    metadata: dict[str, dict[str, Any]],
    record_limit: int,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for index, record in enumerate(runtime_records(path)):
        if not record.get("reached"):
            continue
        observed: Counter[str] = Counter()
        satisfied: Counter[str] = Counter()
        for component in record.get("components") or []:
            if not isinstance(component, dict):
                continue
            source_id = source_id_from_component(component)
            if source_id is None or source_id not in bindings:
                continue
            semantic = bindings[source_id].semantic
            observed[semantic] += 1
            if positive_value(component):
                satisfied[semantic] += 1
        if observed:
            rows.append(
                {
                    "record_index": index,
                    "d_f_spec_lifted": record.get("D_F_spec_lifted")
                    if "D_F_spec_lifted" in record
                    else record.get("d_f_spec_lifted"),
                    "trace_signature": record.get("trace_signature"),
                    "observed": sorted(observed),
                    "satisfied": sorted(satisfied),
                    "error_semantics_satisfied": sorted(ERROR_SEMANTICS.intersection(satisfied)),
                    "ok_barriers_satisfied": sorted(OK_BARRIER_SEMANTICS.intersection(satisfied)),
                }
            )

    meta = metadata.get(str(path), {})
    totals = Counter()
    for row in rows:
        for name in row["observed"]:
            totals[f"{name}_observed_records"] += 1
        for name in row["satisfied"]:
            totals[f"{name}_satisfied_records"] += 1
    return {
        "path": str(path),
        "variant_index": meta.get("index"),
        "op": meta.get("op"),
        "sample": meta.get("sample"),
        "variant_path": meta.get("path"),
        "records_with_extractor_components": len(rows),
        "totals": dict(sorted(totals.items())),
        "top_records": rows[:record_limit],
    }


def diagnose(totals: Counter[str]) -> dict[str, str]:
    if totals.get("extractor_loop_entry_observed_records", 0) == 0:
        return {
            "status": "extractor_not_reached",
            "interpretation": "Reached lifecycle records did not enter process_extractor.",
            "next_action": "Preserve HEVC type49 NALUs through import into gf_isom_nalu_sample_rewrite.",
        }
    if any(totals.get(f"{name}_satisfied_records", 0) for name in ERROR_SEMANTICS):
        return {
            "status": "extractor_error_path_satisfied",
            "interpretation": "At least one modeled extractor error path is satisfied before normal rewrite completion.",
            "next_action": "Prioritize these candidates for endpoint/ASAN replay and same-object cleanup closure.",
        }
    if totals.get("no_reference_track_ok_return_satisfied_records", 0):
        return {
            "status": "extractor_returns_ok_without_reference_track",
            "interpretation": "process_extractor is reached, but the reference-track lookup fails and returns GF_OK.",
            "next_action": "Mutate toward an imported L-HEVC/SCAL reference relation that gives type49 a valid target track.",
        }
    if totals.get("constructor_mode_satisfied_records", 0):
        return {
            "status": "extractor_constructor_mode_only",
            "interpretation": "process_extractor reaches constructor mode but no modeled error branch is satisfied.",
            "next_action": "Bias malformed constructor lengths so the resulting sample rewrite exits before get_content.",
        }
    return {
        "status": "extractor_path_incomplete",
        "interpretation": "process_extractor is partially observed, but no modeled OK barrier or error path explains the return.",
        "next_action": "Add the next internal return point or operand-distance binding on the observed extractor path.",
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    bindings = load_event_map(args.runtime_event_map)
    metadata = load_records(args.records)
    runtimes = [
        summarize_runtime(path, bindings, metadata, args.record_limit)
        for path in args.runtime_jsonl
    ]
    totals: Counter[str] = Counter()
    for runtime in runtimes:
        for key, value in runtime["totals"].items():
            totals[key] += value
        totals["records_with_extractor_components"] += runtime["records_with_extractor_components"]

    return {
        "schema": "formtrig_gpac3403_extractor_path_audit_v1",
        "runtime_event_map": str(args.runtime_event_map),
        "records": str(args.records) if args.records else None,
        "totals": dict(sorted(totals.items())),
        "verdict": diagnose(totals),
        "runtimes": runtimes,
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    verdict = report["verdict"]
    lines = [
        "# GPAC_3403 Extractor Path Audit",
        "",
        f"- status: `{verdict['status']}`",
        f"- interpretation: {verdict['interpretation']}",
        f"- next_action: {verdict['next_action']}",
        "",
        "## Totals",
        "",
        "| metric | value |",
        "|---|---:|",
    ]
    for key, value in report["totals"].items():
        lines.append(f"| `{key}` | {value} |")
    lines.extend(["", "## Runtime Records", ""])
    for runtime in report["runtimes"]:
        lines.append(f"### {runtime['path']}")
        lines.append("")
        lines.append("| idx | D_F | observed | satisfied | error | ok barrier | trace |")
        lines.append("|---:|---:|---|---|---|---|---|")
        for row in runtime.get("top_records", []):
            lines.append(
                "| {idx} | {df} | `{observed}` | `{satisfied}` | `{error}` | `{ok}` | `{trace}` |".format(
                    idx=row.get("record_index"),
                    df=row.get("d_f_spec_lifted"),
                    observed=",".join(row.get("observed", [])),
                    satisfied=",".join(row.get("satisfied", [])),
                    error=",".join(row.get("error_semantics_satisfied", [])),
                    ok=",".join(row.get("ok_barriers_satisfied", [])),
                    trace=row.get("trace_signature"),
                )
            )
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-event-map", required=True, type=Path)
    parser.add_argument("--runtime-jsonl", action="append", required=True, type=Path)
    parser.add_argument("--records", type=Path)
    parser.add_argument("--record-limit", type=int, default=3)
    parser.add_argument("--out-json", type=Path)
    parser.add_argument("--out-md", type=Path)
    args = parser.parse_args(argv)

    report = build_report(args)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(rendered, encoding="utf-8")
    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        write_markdown(report, args.out_md)
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
