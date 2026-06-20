#!/usr/bin/env python3
"""Audit GPAC_3403 post-reassign path closure from FORMTRIG runtime logs.

This is a diagnostic helper for the GPAC_3403 lifecycle TC.  B7 proved that
typed HEVC mutations can reach the import/reassign/cleanup neighborhood, but
many candidates still do not trigger because they fail to close the ownership
path:

  released sample data == reassign buffer == cleanup GF_BitStream original

B8 adds pre-detach error-path events and a normal-detach absence probe.  This
tool keeps those roles visible instead of relying only on the aggregate D_F.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


RELEASE_VALUE_ID = "gpac_sample_release_data_object_value"
REASSIGN_VALUE_ID = "gpac_dynamic_bitstream_external_buffer_same_object"
CLEANUP_VALUE_ID = "gpac_bitstream_original_cleanup_object_value"
FALLBACK_REASSIGN_ID = "gpac_nalu_out_reassign_fallback_lifecycle_event"
NORMAL_DETACH_ABSENT_ID = "gpac_final_normal_get_content_absent"
PRE_DETACH_ERROR_IDS = {
    "gpac_hevc_extractor_error_pre_detach_producer",
    "gpac_invalid_nal_size_pre_detach_producer",
}


@dataclass(frozen=True)
class Binding:
    binding_id: str
    semantic_id: str
    role: str
    site_id: str
    event_id: int
    function: str
    file: str
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
            semantic_id = identify_semantic_binding(row)
            bindings[event_id] = Binding(
                binding_id=row.get("binding_id", ""),
                semantic_id=semantic_id,
                role=row.get("role", ""),
                site_id=row.get("site_id", ""),
                event_id=event_id,
                function=row.get("function", ""),
                file=row.get("file", ""),
                line=row.get("line", ""),
                value_mode=row.get("value_mode", ""),
            )
    return bindings


def identify_semantic_binding(row: dict[str, str]) -> str:
    binding_id = row.get("binding_id", "")
    if binding_id.startswith("gpac_"):
        return binding_id
    site_id = row.get("site_id", "")
    function = row.get("function", "")
    line = row.get("line", "")
    role = row.get("role", "")
    value_mode = row.get("value_mode", "")
    key = (site_id, function, line, role, value_mode)
    semantic_by_key = {
        ("3013921722", "gf_isom_sample_del", "112", "lifecycle_event", "a"): RELEASE_VALUE_ID,
        ("1549213408", "gf_bs_reassign_buffer", "122", "same_object", "a"): REASSIGN_VALUE_ID,
        ("65063371", "gf_bs_del", "372", "use", "a"): CLEANUP_VALUE_ID,
        ("1766076671", "gf_isom_nalu_sample_rewrite", "672", "lifecycle_event", "hit"): FALLBACK_REASSIGN_ID,
        ("3035684152", "gf_isom_nalu_sample_rewrite", "809", "guard", "outcome"): "gpac_hevc_extractor_error_pre_detach_producer",
        ("4008811561", "gf_isom_nalu_sample_rewrite", "844", "guard", "outcome"): "gpac_invalid_nal_size_pre_detach_producer",
        ("3035684152", "gf_isom_nalu_sample_rewrite", "809", "desired_producer", "outcome"): "gpac_hevc_extractor_error_pre_detach_producer",
        ("4008811561", "gf_isom_nalu_sample_rewrite", "844", "desired_producer", "outcome"): "gpac_invalid_nal_size_pre_detach_producer",
        ("224520426", "gf_isom_nalu_sample_rewrite", "912", "opposite_producer", "absent"): NORMAL_DETACH_ABSENT_ID,
    }
    return semantic_by_key.get(key, binding_id)


def load_records(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    records: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            runtime_log = record.get("runtime_log")
            if isinstance(runtime_log, str):
                records[runtime_log] = record
    return records


def iter_runtime_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))
    return records


def source_id_from_component(component: dict[str, Any]) -> int | None:
    raw = component.get("source_id")
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        try:
            return int(raw, 0)
        except ValueError:
            return event_id_to_int(raw)
    return None


def collect_components(record: dict[str, Any], bindings: dict[int, Binding]) -> dict[str, list[dict[str, Any]]]:
    by_binding: dict[str, list[dict[str, Any]]] = {}
    for component in record.get("components") or []:
        if not isinstance(component, dict):
            continue
        source_id = source_id_from_component(component)
        if source_id is None:
            continue
        binding = bindings.get(source_id)
        if binding is None:
            continue
        item = {
            "binding_id": binding.semantic_id,
            "compiled_binding_id": binding.binding_id,
            "role": binding.role,
            "site_id": binding.site_id,
            "line": binding.line,
            "value_mode": binding.value_mode,
            "value": component.get("value"),
            "priority": component.get("priority"),
        }
        by_binding.setdefault(binding.semantic_id, []).append(item)
    return by_binding


def first_value(components: dict[str, list[dict[str, Any]]], binding_id: str) -> int | None:
    for component in components.get(binding_id, []):
        value = component.get("value")
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            try:
                return int(value, 0)
            except ValueError:
                continue
    return None


def binding_has_positive_value(components: dict[str, list[dict[str, Any]]], binding_id: str) -> bool:
    for component in components.get(binding_id, []):
        value = component.get("value")
        if isinstance(value, (int, float)) and value > 0:
            return True
        if isinstance(value, str):
            try:
                if int(value, 0) > 0:
                    return True
            except ValueError:
                continue
    return False


def summarize_runtime(
    path: Path,
    bindings: dict[int, Binding],
    record_metadata: dict[str, dict[str, Any]],
    record_limit: int,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for index, record in enumerate(iter_runtime_records(path)):
        if not record.get("reached"):
            continue
        components = collect_components(record, bindings)
        release = first_value(components, RELEASE_VALUE_ID)
        reassign = first_value(components, REASSIGN_VALUE_ID)
        cleanup = first_value(components, CLEANUP_VALUE_ID)
        pre_detach_observed = sorted(PRE_DETACH_ERROR_IDS.intersection(components))
        pre_detach_satisfied = [
            binding_id
            for binding_id in pre_detach_observed
            if binding_has_positive_value(components, binding_id)
        ]
        rows.append(
            {
                "record_index": index,
                "d_f_spec_lifted": record.get("D_F_spec_lifted")
                if "D_F_spec_lifted" in record
                else record.get("d_f_spec_lifted"),
                "trace_signature": record.get("trace_signature"),
                "release_value": release,
                "reassign_value": reassign,
                "cleanup_value": cleanup,
                "release_reassign_same": bool(release and reassign and release == reassign),
                "reassign_cleanup_same": bool(reassign and cleanup and reassign == cleanup),
                "fallback_reassign_seen": FALLBACK_REASSIGN_ID in components,
                "normal_detach_absent_satisfied": NORMAL_DETACH_ABSENT_ID in components,
                "pre_detach_errors_observed": pre_detach_observed,
                "pre_detach_errors": pre_detach_satisfied,
                "observed_bindings": sorted(components),
            }
        )

    metadata = record_metadata.get(str(path), {})
    return {
        "path": str(path),
        "variant_index": metadata.get("index"),
        "op": metadata.get("op"),
        "sample": metadata.get("sample"),
        "variant_path": metadata.get("path"),
        "reached_records": len(rows),
        "pre_detach_error_records": sum(1 for row in rows if row["pre_detach_errors"]),
        "pre_detach_error_observed_records": sum(
            1 for row in rows if row["pre_detach_errors_observed"]
        ),
        "normal_detach_absent_records": sum(1 for row in rows if row["normal_detach_absent_satisfied"]),
        "fallback_reassign_records": sum(1 for row in rows if row["fallback_reassign_seen"]),
        "release_reassign_same_records": sum(1 for row in rows if row["release_reassign_same"]),
        "reassign_cleanup_same_records": sum(1 for row in rows if row["reassign_cleanup_same"]),
        "top_records": rows[:record_limit],
    }


def diagnose(totals: dict[str, int]) -> dict[str, str]:
    reached = totals.get("reached_records", 0)
    if reached == 0:
        return {
            "status": "no_reached_runtime_records",
            "interpretation": "No reached runtime records were available for post-reassign analysis.",
            "next_action": "Verify FORMTRIG_TARGET_SITE_IDS, lift spec, and runtime log collection.",
        }
    if totals.get("reassign_cleanup_same_records", 0):
        return {
            "status": "alias_cleanup_closure_observed",
            "interpretation": "At least one record closes the reassign-to-cleanup object relation; endpoint replay should be checked for _T or sanitizer evidence.",
            "next_action": "Prioritize retained inputs with same cleanup object and run endpoint/ASAN replay.",
        }
    if totals.get("pre_detach_error_records", 0) == 0:
        return {
            "status": "pre_detach_error_missing",
            "interpretation": "Inputs reach the lifecycle neighborhood but do not hit the modeled pre-detach HEVC error paths at avc_ext.c:809 or avc_ext.c:844.",
            "next_action": "Bias typed mutation toward malformed HEVC extractor or nal_size<2 cases that remain parseable long enough to occur after sample-buffer reassign.",
        }
    if totals.get("normal_detach_absent_records", 0) < reached:
        return {
            "status": "normal_detach_path_observed",
            "interpretation": "Some reached records still take the modeled normal end-of-rewrite detach path, which can clear bs->original before cleanup.",
            "next_action": "Penalize final normal rewrite completion and retain candidates that exit before gf_bs_get_content_no_truncate detaches the sample buffer.",
        }
    return {
        "status": "alias_cleanup_gap_after_pre_detach",
        "interpretation": "Pre-detach error evidence is present, but cleanup still does not free the reassign-owned sample buffer.",
        "next_action": "Inspect the intervening bitstream lifecycle and add the missing ownership transfer/reset event to the BindingSpec.",
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    bindings = load_event_map(args.runtime_event_map)
    metadata = load_records(args.records)
    runtime_reports = [
        summarize_runtime(path, bindings, metadata, args.record_limit)
        for path in args.runtime_jsonl
    ]
    totals: Counter[str] = Counter()
    for report in runtime_reports:
        for key in (
            "reached_records",
            "pre_detach_error_records",
            "pre_detach_error_observed_records",
            "normal_detach_absent_records",
            "fallback_reassign_records",
            "release_reassign_same_records",
            "reassign_cleanup_same_records",
        ):
            totals[key] += int(report.get(key) or 0)
    binding_counts: Counter[str] = Counter()
    for report in runtime_reports:
        for row in report.get("top_records", []):
            binding_counts.update(row.get("observed_bindings", []))

    return {
        "schema": "formtrig_gpac3403_post_reassign_path_audit_v1",
        "runtime_event_map": str(args.runtime_event_map),
        "records": str(args.records) if args.records else None,
        "totals": dict(totals),
        "observed_binding_counts_top_records": dict(sorted(binding_counts.items())),
        "verdict": diagnose(dict(totals)),
        "runtimes": runtime_reports,
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    verdict = report["verdict"]
    totals = report["totals"]
    lines = [
        "# GPAC_3403 Post-Reassign Path Audit",
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
    for key in sorted(totals):
        lines.append(f"| `{key}` | {totals[key]} |")
    lines.extend(["", "## Runtime Records", ""])
    for runtime in report["runtimes"]:
        lines.append(f"### {runtime['path']}")
        lines.append("")
        lines.append(
            "| idx | D_F | pre-detach observed | pre-detach satisfied | normal detach absent | release=reassign | reassign=cleanup | fallback | trace |"
        )
        lines.append("|---:|---:|---|---|---|---|---|---|---|")
        for row in runtime.get("top_records", []):
            lines.append(
                "| {idx} | {df} | `{observed}` | `{errors}` | `{normal}` | `{rr}` | `{rc}` | `{fallback}` | `{trace}` |".format(
                    idx=row.get("record_index"),
                    df=row.get("d_f_spec_lifted"),
                    observed=",".join(row.get("pre_detach_errors_observed", [])),
                    errors=",".join(row.get("pre_detach_errors", [])),
                    normal=row.get("normal_detach_absent_satisfied"),
                    rr=row.get("release_reassign_same"),
                    rc=row.get("reassign_cleanup_same"),
                    fallback=row.get("fallback_reassign_seen"),
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
