#!/usr/bin/env python3
"""Audit GPAC_3403 object-alias relation values in FORMTRIG runtime logs."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROLE_NAMES = {
    1: "root_observe",
    2: "guard",
    3: "producer",
    4: "desired_producer",
    5: "opposite_producer",
    6: "use",
    7: "lifecycle_event",
    8: "same_object",
    9: "input_influence",
    10: "repair_hook",
}


@dataclass(frozen=True)
class Binding:
    event_kind: int
    site_id: int
    role: str
    component_kind: int
    atom_id: int
    priority: int
    direction: str
    value_mode: str
    source_id: int | None


def intish(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    try:
        text = str(value).strip()
        return int(text, 16) if text.startswith("0x") else int(text)
    except (TypeError, ValueError):
        return None


def role_name(value: Any) -> str:
    parsed = intish(value)
    if parsed is None:
        return "unknown"
    return ROLE_NAMES.get(parsed, f"role_{parsed}")


def parse_lift_spec(path: Path) -> dict[int, Binding]:
    bindings: dict[int, Binding] = {}
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 11 or parts[0] != "role_component":
            continue
        event_kind = intish(parts[1])
        site_id = intish(parts[2])
        component_kind = intish(parts[4])
        atom_id = intish(parts[5])
        priority = intish(parts[6])
        source_id = intish(parts[11]) if len(parts) > 11 else None
        if None in {event_kind, site_id, component_kind, atom_id, priority}:
            continue
        binding = Binding(
            event_kind=event_kind or 0,
            site_id=site_id or 0,
            role=parts[3],
            component_kind=component_kind or 0,
            atom_id=atom_id or 0,
            priority=priority or 0,
            direction=parts[7] if len(parts) > 7 else "",
            value_mode=parts[8] if len(parts) > 8 else "",
            source_id=source_id,
        )
        if source_id is not None:
            bindings[source_id] = binding
    return bindings


def read_runtime_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                records.append(payload)
    return records


def pointer_value(value: Any) -> int | None:
    parsed = intish(value)
    if parsed is None or parsed <= 4096:
        return None
    return parsed


def compact_values(values: set[int]) -> list[int]:
    return sorted(values)[:16]


def component_binding(component: dict[str, Any], bindings: dict[int, Binding]) -> Binding | None:
    source_id = intish(component.get("source_id"))
    if source_id is not None and source_id in bindings:
        return bindings[source_id]
    return None


def collect_record_values(
    record: dict[str, Any],
    bindings: dict[int, Binding],
) -> dict[str, Any]:
    release_values: set[int] = set()
    same_object_values: set[int] = set()
    cleanup_values: set[int] = set()
    release_branch = False
    cleanup_branch = False
    dynamic_root = False
    components = record.get("components") if isinstance(record.get("components"), list) else []

    for component in components:
        if not isinstance(component, dict):
            continue
        binding = component_binding(component, bindings)
        role = binding.role if binding else role_name(component.get("role"))
        priority = binding.priority if binding else intish(component.get("priority"))
        value_mode = binding.value_mode if binding else ""
        value = component.get("value")
        ptr = pointer_value(value)

        if role == "lifecycle_event" and priority == 25 and intish(value) == 1:
            release_branch = True
        if role == "use" and priority == 40 and intish(value) == 1:
            cleanup_branch = True
        if role == "root_observe" and priority == 50 and intish(value) == 1:
            dynamic_root = True

        if value_mode == "a" and ptr is not None:
            if role == "lifecycle_event":
                release_values.add(ptr)
            elif role == "same_object":
                same_object_values.add(ptr)
            elif role == "use":
                cleanup_values.add(ptr)

    release_same = release_values & same_object_values
    same_cleanup = same_object_values & cleanup_values
    release_cleanup = release_values & cleanup_values
    complete = bool(release_cleanup and same_cleanup and release_same and cleanup_branch)

    if complete:
        status = "alias_free_relation_proven"
    elif release_same and cleanup_values and not same_cleanup:
        status = "release_reassign_alias_without_cleanup_free_alias"
    elif release_same and not cleanup_values:
        status = "release_reassign_alias_without_cleanup_value"
    elif same_cleanup and not release_values:
        status = "cleanup_alias_without_release_value"
    elif cleanup_values and same_object_values and not same_cleanup:
        status = "cleanup_original_differs_from_reassigned_buffer"
    elif not same_object_values:
        status = "missing_same_object_value"
    elif not release_values:
        status = "missing_release_value"
    elif not cleanup_values:
        status = "missing_cleanup_value"
    else:
        status = "alias_relation_not_proven"

    return {
        "status": status,
        "complete_alias_free_relation": complete,
        "release_branch_observed": release_branch,
        "cleanup_branch_observed": cleanup_branch,
        "dynamic_root_observed": dynamic_root,
        "release_values": compact_values(release_values),
        "same_object_values": compact_values(same_object_values),
        "cleanup_values": compact_values(cleanup_values),
        "release_same_object_matches": compact_values(release_same),
        "same_object_cleanup_matches": compact_values(same_cleanup),
        "release_cleanup_matches": compact_values(release_cleanup),
        "component_count": len(components),
        "d_f_spec_lifted": record.get("D_F_spec_lifted"),
        "reached": bool(record.get("reached")),
        "target_hit_count": record.get("target_hit_count"),
    }


def summarize_runtime(path: Path, bindings: dict[int, Binding]) -> dict[str, Any]:
    records = read_runtime_records(path)
    record_summaries = [collect_record_values(record, bindings) for record in records]
    complete_records = [row for row in record_summaries if row["complete_alias_free_relation"]]
    release_reassign_records = [
        row for row in record_summaries if row["release_same_object_matches"]
    ]
    cleanup_value_records = [row for row in record_summaries if row["cleanup_values"]]
    statuses = sorted({str(row["status"]) for row in record_summaries})

    if complete_records:
        status = "alias_free_relation_proven"
    elif release_reassign_records and cleanup_value_records:
        status = "release_reassign_alias_observed_cleanup_differs"
    elif release_reassign_records:
        status = "release_reassign_alias_observed_no_cleanup_value"
    elif record_summaries:
        status = record_summaries[0]["status"]
    else:
        status = "no_runtime_records"

    best = sorted(
        record_summaries,
        key=lambda row: (
            not row["complete_alias_free_relation"],
            not bool(row["release_same_object_matches"]),
            not bool(row["cleanup_values"]),
            -(row["component_count"] or 0),
        ),
    )

    return {
        "path": str(path),
        "record_count": len(records),
        "status": status,
        "complete_alias_free_relation_records": len(complete_records),
        "release_reassign_alias_records": len(release_reassign_records),
        "cleanup_value_records": len(cleanup_value_records),
        "record_statuses": statuses,
        "best_record": best[0] if best else None,
    }


def build_report(lift_spec: Path, runtime_logs: list[Path]) -> dict[str, Any]:
    bindings = parse_lift_spec(lift_spec)
    runtimes = [summarize_runtime(path, bindings) for path in runtime_logs]
    complete = [row for row in runtimes if row["status"] == "alias_free_relation_proven"]
    release_reassign = [
        row for row in runtimes if str(row["status"]).startswith("release_reassign_alias")
    ]
    if complete:
        verdict = "alias_free_relation_proven"
    elif release_reassign:
        verdict = "release_reassign_alias_observed_terminal_cleanup_missing"
    elif runtimes:
        verdict = "alias_relation_not_proven"
    else:
        verdict = "no_runtime_logs"
    return {
        "schema": "formtrig_gpac3403_alias_relation_audit_v1",
        "lift_spec": str(lift_spec),
        "binding_count": len(bindings),
        "runtime_count": len(runtimes),
        "runtimes": runtimes,
        "verdict": {
            "status": verdict,
            "complete_alias_free_relation": bool(complete),
            "release_reassign_alias_observed": bool(release_reassign),
            "interpretation": (
                "The sample release and reassign-buffer values match, but no "
                "runtime record proves the later GF_BitStream->original cleanup "
                "free uses the same pointer."
                if verdict == "release_reassign_alias_observed_terminal_cleanup_missing"
                else "The relation is fully proven by runtime values."
                if verdict == "alias_free_relation_proven"
                else "Runtime values do not yet prove the declared same-object relation."
            ),
        },
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        "# GPAC_3403 Alias Relation Audit",
        "",
        f"- Lift spec: `{report.get('lift_spec')}`",
        f"- Runtime logs: {report.get('runtime_count')}",
        f"- Verdict: `{report.get('verdict', {}).get('status')}`",
        f"- Complete alias/free relation: `{report.get('verdict', {}).get('complete_alias_free_relation')}`",
        f"- Release->reassign alias observed: `{report.get('verdict', {}).get('release_reassign_alias_observed')}`",
        "",
        "## Runtime Summary",
        "",
        "| runtime | status | records | release=reassign | cleanup values | best release | best same_object | best cleanup |",
        "|---|---:|---:|---:|---:|---|---|---|",
    ]
    for runtime in report.get("runtimes", []):
        best = runtime.get("best_record") or {}
        lines.append(
            "| {path} | `{status}` | {records} | {release_records} | {cleanup_records} | `{release}` | `{same}` | `{cleanup}` |".format(
                path=runtime.get("path"),
                status=runtime.get("status"),
                records=runtime.get("record_count"),
                release_records=runtime.get("release_reassign_alias_records"),
                cleanup_records=runtime.get("cleanup_value_records"),
                release=best.get("release_values"),
                same=best.get("same_object_values"),
                cleanup=best.get("cleanup_values"),
            )
        )
    lines.extend(["", report.get("verdict", {}).get("interpretation", "")])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lift-spec", required=True, type=Path)
    parser.add_argument("--runtime-jsonl", action="append", required=True, type=Path)
    parser.add_argument("--out-json", type=Path)
    parser.add_argument("--out-md", type=Path)
    args = parser.parse_args(argv)

    report = build_report(args.lift_spec, args.runtime_jsonl)
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
