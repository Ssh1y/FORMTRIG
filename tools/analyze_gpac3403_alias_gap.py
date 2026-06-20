#!/usr/bin/env python3
"""Explain the remaining GPAC_3403 release/reassign/cleanup alias gap."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import gpac3403_alias_relation_audit as alias_audit


def scalar_int(value: Any) -> int | None:
    return alias_audit.intish(value)


def pointer_list(values: set[int]) -> list[int]:
    return sorted(values)


def histogram(counter: Counter[int]) -> list[dict[str, int]]:
    return [
        {"value": int(value), "count": int(count)}
        for value, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def value_distribution(counter: Counter[Any]) -> list[dict[str, Any]]:
    return [
        {"value": value, "count": int(count)}
        for value, count in sorted(counter.items(), key=lambda item: (-item[1], str(item[0])))
    ]


def extract_alias_values(
    record: dict[str, Any],
    bindings: dict[int, alias_audit.Binding],
) -> dict[str, Any]:
    release_values: set[int] = set()
    same_object_values: set[int] = set()
    cleanup_values: set[int] = set()
    release_value_sources: set[int] = set()
    same_object_sources: set[int] = set()
    cleanup_value_sources: set[int] = set()
    release_branch = False
    cleanup_branch = False
    dynamic_root = False
    components, component_count = alias_audit.record_components(record)

    for component in components:
        binding = alias_audit.component_binding(component, bindings)
        role = binding.role if binding else alias_audit.role_name(component.get("role"))
        priority = binding.priority if binding else scalar_int(component.get("priority"))
        value_mode = binding.value_mode if binding else ""
        value = component.get("value")
        ptr = alias_audit.pointer_value(value)
        source_id = scalar_int(component.get("source_id"))

        if role == "lifecycle_event" and priority == 25 and scalar_int(value) == 1:
            release_branch = True
        if role == "use" and priority == 40 and scalar_int(value) == 1:
            cleanup_branch = True
        if role == "root_observe" and priority == 50 and scalar_int(value) == 1:
            dynamic_root = True

        if value_mode != "a" or ptr is None:
            continue
        if role == "lifecycle_event":
            release_values.add(ptr)
            if source_id is not None:
                release_value_sources.add(source_id)
        elif role == "same_object":
            same_object_values.add(ptr)
            if source_id is not None:
                same_object_sources.add(source_id)
        elif role == "use":
            cleanup_values.add(ptr)
            if source_id is not None:
                cleanup_value_sources.add(source_id)

    release_same = release_values & same_object_values
    release_cleanup = release_values & cleanup_values
    same_cleanup = same_object_values & cleanup_values
    complete = bool(release_same and release_cleanup and same_cleanup and cleanup_branch)
    cleanup_minus_alias_deltas = sorted(
        cleanup - alias for alias in release_same for cleanup in cleanup_values
    )

    return {
        "release_values": pointer_list(release_values),
        "same_object_values": pointer_list(same_object_values),
        "cleanup_values": pointer_list(cleanup_values),
        "release_same_object_matches": pointer_list(release_same),
        "release_cleanup_matches": pointer_list(release_cleanup),
        "same_object_cleanup_matches": pointer_list(same_cleanup),
        "cleanup_minus_alias_deltas": cleanup_minus_alias_deltas,
        "min_abs_cleanup_delta": min((abs(delta) for delta in cleanup_minus_alias_deltas), default=None),
        "complete_alias_free_relation": complete,
        "release_branch_observed": release_branch,
        "cleanup_branch_observed": cleanup_branch,
        "dynamic_root_observed": dynamic_root,
        "component_count": component_count,
        "release_value_sources": pointer_list(release_value_sources),
        "same_object_sources": pointer_list(same_object_sources),
        "cleanup_value_sources": pointer_list(cleanup_value_sources),
    }


def record_metadata(record: dict[str, Any], index: int) -> dict[str, Any]:
    return {
        "record_index": index,
        "event": record.get("event"),
        "reason": record.get("reason"),
        "execs_done": record.get("execs_done"),
        "queue_id": record.get("queue_id"),
        "queued_items": record.get("queued_items"),
        "trace_signature": record.get("trace_signature"),
        "stable": record.get("stable"),
        "d_f_spec_lifted": alias_audit.record_d_f_spec_lifted(record),
        "d_f_lifted": record.get("d_f_lifted"),
        "target_hit_count": record.get("target_hit_count"),
        "hot_ranges": record.get("hot_ranges"),
        "actionable_components": record.get("actionable_components"),
        "source_flags": record.get("source_flags"),
        "observed_source_flags": record.get("observed_source_flags"),
    }


def analyze_record(
    record: dict[str, Any],
    index: int,
    bindings: dict[int, alias_audit.Binding],
) -> dict[str, Any]:
    alias_values = extract_alias_values(record, bindings)
    compact_status = alias_audit.collect_record_values(record, bindings)["status"]
    row = {
        **record_metadata(record, index),
        **alias_values,
        "status": compact_status,
    }
    return row


def interesting_records(records: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    candidates = [
        row
        for row in records
        if row["release_same_object_matches"] or row["cleanup_values"] or row["complete_alias_free_relation"]
    ]
    candidates.sort(
        key=lambda row: (
            not row["complete_alias_free_relation"],
            not (row["release_same_object_matches"] and row["cleanup_values"]),
            row["min_abs_cleanup_delta"] is None,
            row["min_abs_cleanup_delta"] if row["min_abs_cleanup_delta"] is not None else 2**63,
            row["execs_done"] if row["execs_done"] is not None else 2**63,
            row["record_index"],
        )
    )
    return candidates[:limit]


def summarize_runtime(
    runtime_jsonl: Path,
    bindings: dict[int, alias_audit.Binding],
    record_limit: int,
) -> dict[str, Any]:
    raw_records = alias_audit.read_runtime_records(runtime_jsonl)
    records = [analyze_record(record, index, bindings) for index, record in enumerate(raw_records)]
    delta_counter: Counter[int] = Counter()
    release_same_counter: Counter[int] = Counter()
    cleanup_value_counter: Counter[int] = Counter()
    d_f_counter: Counter[Any] = Counter()
    status_counter: Counter[str] = Counter()
    event_counter: Counter[Any] = Counter()
    reason_counter: Counter[Any] = Counter()

    for row in records:
        status_counter[str(row["status"])] += 1
        event_counter[row["event"]] += 1
        reason_counter[row["reason"]] += 1
        if row["release_same_object_matches"] and row["cleanup_values"]:
            d_f_counter[row["d_f_spec_lifted"]] += 1
        for value in row["release_same_object_matches"]:
            release_same_counter[value] += 1
        for value in row["cleanup_values"]:
            cleanup_value_counter[value] += 1
        for delta in row["cleanup_minus_alias_deltas"]:
            delta_counter[delta] += 1

    complete_records = [row for row in records if row["complete_alias_free_relation"]]
    release_reassign_records = [row for row in records if row["release_same_object_matches"]]
    cleanup_records = [row for row in records if row["cleanup_values"]]
    alias_cleanup_records = [
        row for row in records if row["release_same_object_matches"] and row["cleanup_values"]
    ]
    nonzero_delta_records = [
        row for row in alias_cleanup_records if any(delta != 0 for delta in row["cleanup_minus_alias_deltas"])
    ]

    unique_deltas = sorted(delta_counter)
    stable_nonzero_delta = (
        len(unique_deltas) == 1
        and bool(nonzero_delta_records)
        and unique_deltas[0] != 0
    )
    single_cleanup_multiple_release_aliases = (
        bool(alias_cleanup_records)
        and len(cleanup_value_counter) == 1
        and len(release_same_counter) > 1
        and not complete_records
    )
    if complete_records:
        status = "alias_free_relation_proven"
    elif single_cleanup_multiple_release_aliases:
        status = "single_cleanup_multiple_release_aliases"
    elif stable_nonzero_delta:
        status = "stable_nonzero_cleanup_offset"
    elif alias_cleanup_records:
        status = "variable_cleanup_alias_gap"
    elif release_reassign_records:
        status = "release_reassign_alias_without_cleanup_value"
    elif cleanup_records:
        status = "cleanup_value_without_release_reassign_alias"
    elif records:
        status = "no_alias_relation_progress"
    else:
        status = "no_runtime_records"

    return {
        "path": str(runtime_jsonl),
        "record_count": len(records),
        "status": status,
        "relation_counts": {
            "complete_alias_free_relation_records": len(complete_records),
            "release_reassign_alias_records": len(release_reassign_records),
            "cleanup_value_records": len(cleanup_records),
            "release_reassign_with_cleanup_records": len(alias_cleanup_records),
            "nonzero_cleanup_delta_records": len(nonzero_delta_records),
        },
        "delta_histogram": histogram(delta_counter),
        "release_same_object_value_histogram": histogram(release_same_counter),
        "cleanup_value_histogram": histogram(cleanup_value_counter),
        "unique_release_same_object_values": len(release_same_counter),
        "unique_cleanup_values": len(cleanup_value_counter),
        "stable_cleanup_offset": {
            "present": stable_nonzero_delta,
            "delta": unique_deltas[0] if stable_nonzero_delta else None,
            "records": len(nonzero_delta_records) if stable_nonzero_delta else 0,
        },
        "d_f_spec_lifted_for_alias_cleanup": value_distribution(d_f_counter),
        "record_status_distribution": value_distribution(status_counter),
        "event_distribution": value_distribution(event_counter),
        "reason_distribution": value_distribution(reason_counter),
        "top_records": interesting_records(records, record_limit),
    }


def aggregate_status(runtimes: list[dict[str, Any]]) -> dict[str, Any]:
    complete = any(runtime["status"] == "alias_free_relation_proven" for runtime in runtimes)
    single_cleanup_multiple_aliases = any(
        runtime["status"] == "single_cleanup_multiple_release_aliases" for runtime in runtimes
    )
    stable_offsets = [
        runtime["stable_cleanup_offset"]["delta"]
        for runtime in runtimes
        if runtime["stable_cleanup_offset"]["present"]
    ]
    alias_cleanup = any(
        runtime["relation_counts"]["release_reassign_with_cleanup_records"] > 0
        for runtime in runtimes
    )
    release_reassign = any(
        runtime["relation_counts"]["release_reassign_alias_records"] > 0 for runtime in runtimes
    )

    if complete:
        status = "alias_free_relation_proven"
        interpretation = "At least one runtime record proves release=reassign=cleanup."
        next_action = "Use this run for endpoint replay or matched-baseline promotion."
    elif single_cleanup_multiple_aliases:
        status = "single_cleanup_multiple_release_aliases"
        interpretation = (
            "Cleanup frees one dynamic bitstream buffer while release/reassign aliases point "
            "to multiple sample buffers. This points to a sample/lifecycle correlation gap: "
            "FORMTRIG reaches the right ownership machinery, but it has not aligned the final "
            "GF_BitStream->original cleanup with the same sample buffer released by "
            "gf_isom_sample_del."
        )
        next_action = (
            "Bias GPAC typed mutation toward lifecycle closure for the last/current rewritten "
            "sample, or add object-context binding so retained seeds are ranked by matching "
            "cleanup object identity rather than by unrelated release/reassign events."
        )
    elif stable_offsets:
        status = "stable_nonzero_cleanup_offset"
        interpretation = (
            "Release and reassign-buffer pointers match, but cleanup consistently frees "
            "a different dynamic bitstream buffer. This narrows the blocker to lifecycle "
            "ownership closure, not HEVC importer routing or retained-candidate selection."
        )
        next_action = (
            "Repair typed mutation or BindingSpec correlation so the final GF_BitStream "
            "cleanup object is the same sample buffer that gf_isom_sample_del releases."
        )
    elif alias_cleanup:
        status = "variable_cleanup_alias_gap"
        interpretation = (
            "Alias and cleanup values are both observed, but their difference is not stable "
            "or zero. More object/lifecycle correlation is needed before endpoint spending."
        )
        next_action = "Add object-context instrumentation or split records by sample/lifecycle context."
    elif release_reassign:
        status = "release_reassign_alias_without_cleanup_value"
        interpretation = "Release=reassign is observed, but cleanup pointer values are not observed."
        next_action = "Repair cleanup value binding or drive the bitstream deletion path."
    elif runtimes:
        status = "no_alias_relation_progress"
        interpretation = "The runtime logs do not show the release/reassign alias relation."
        next_action = "Return to BindingSpec validation before endpoint replay."
    else:
        status = "no_runtime_logs"
        interpretation = "No runtime logs were analyzed."
        next_action = "Run a FORMTRIG GPAC campaign before analyzing alias closure."

    return {
        "status": status,
        "complete_alias_free_relation": complete,
        "stable_nonzero_cleanup_offsets": sorted(set(stable_offsets)),
        "interpretation": interpretation,
        "next_action": next_action,
        "claim_boundary": (
            "Pointer deltas are runtime diagnostics only. They must not be used as "
            "input-level optimization objectives because allocator addresses are not stable "
            "semantic trigger-state features."
        ),
    }


def build_report(
    lift_spec: Path,
    runtime_jsonl: list[Path],
    record_limit: int = 12,
) -> dict[str, Any]:
    bindings = alias_audit.parse_lift_spec(lift_spec)
    runtimes = [summarize_runtime(path, bindings, record_limit) for path in runtime_jsonl]
    return {
        "schema": "formtrig_gpac3403_alias_gap_analysis_v1",
        "lift_spec": str(lift_spec),
        "binding_count": len(bindings),
        "runtime_count": len(runtimes),
        "runtimes": runtimes,
        "verdict": aggregate_status(runtimes),
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    verdict = report.get("verdict", {})
    lines = [
        "# GPAC_3403 Alias Gap Analysis",
        "",
        f"- Lift spec: `{report.get('lift_spec')}`",
        f"- Runtime logs: {report.get('runtime_count')}",
        f"- Verdict: `{verdict.get('status')}`",
        f"- Complete alias/free relation: `{verdict.get('complete_alias_free_relation')}`",
        f"- Stable nonzero cleanup offsets: `{verdict.get('stable_nonzero_cleanup_offsets')}`",
        "",
        "## Interpretation",
        "",
        str(verdict.get("interpretation", "")),
        "",
        f"Next action: {verdict.get('next_action', '')}",
        "",
        f"Claim boundary: {verdict.get('claim_boundary', '')}",
        "",
        "## Runtime Summaries",
        "",
        "| runtime | status | records | release=reassign | cleanup | alias+cleanup | unique release | unique cleanup | nonzero delta | top deltas |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for runtime in report.get("runtimes", []):
        counts = runtime.get("relation_counts", {})
        top_deltas = runtime.get("delta_histogram", [])[:4]
        lines.append(
            "| {path} | `{status}` | {records} | {release} | {cleanup} | {alias_cleanup} | {unique_release} | {unique_cleanup} | {nonzero} | `{deltas}` |".format(
                path=runtime.get("path"),
                status=runtime.get("status"),
                records=runtime.get("record_count"),
                release=counts.get("release_reassign_alias_records"),
                cleanup=counts.get("cleanup_value_records"),
                alias_cleanup=counts.get("release_reassign_with_cleanup_records"),
                unique_release=runtime.get("unique_release_same_object_values"),
                unique_cleanup=runtime.get("unique_cleanup_values"),
                nonzero=counts.get("nonzero_cleanup_delta_records"),
                deltas=top_deltas,
            )
        )
    lines.extend(["", "## Top Records", ""])
    for runtime in report.get("runtimes", []):
        lines.append(f"### {runtime.get('path')}")
        lines.append("")
        lines.append("| idx | event | reason | exec | queue | D_F | release=same | cleanup | deltas | trace |")
        lines.append("|---:|---|---|---:|---:|---:|---|---|---|---|")
        for row in runtime.get("top_records", []):
            lines.append(
                "| {idx} | `{event}` | `{reason}` | {execs} | {queue} | {df} | `{alias}` | `{cleanup}` | `{deltas}` | `{trace}` |".format(
                    idx=row.get("record_index"),
                    event=row.get("event"),
                    reason=row.get("reason"),
                    execs=row.get("execs_done"),
                    queue=row.get("queue_id"),
                    df=row.get("d_f_spec_lifted"),
                    alias=row.get("release_same_object_matches"),
                    cleanup=row.get("cleanup_values"),
                    deltas=row.get("cleanup_minus_alias_deltas"),
                    trace=row.get("trace_signature"),
                )
            )
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lift-spec", required=True, type=Path)
    parser.add_argument("--runtime-jsonl", action="append", required=True, type=Path)
    parser.add_argument("--record-limit", type=int, default=12)
    parser.add_argument("--out-json", type=Path)
    parser.add_argument("--out-md", type=Path)
    args = parser.parse_args(argv)

    report = build_report(args.lift_spec, args.runtime_jsonl, record_limit=args.record_limit)
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        write_markdown(report, args.out_md)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
