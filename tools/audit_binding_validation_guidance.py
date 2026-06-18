#!/usr/bin/env python3
"""Audit BindingSpec validation results for pre-trigger FORMTRIG guidance.

This audit is deliberately stricter than `ready_for_short_gate`: a validation
can compile, map to native sites, and even trigger `_T` while still providing no
accepted non-trigger frontier progress. Such cases are controls, not evidence
that FORMTRIG solved the R-to-T guidance problem.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CSV_FIELDS = [
    "target_id",
    "disposition",
    "strict_pretrigger_guidance",
    "soft_pretrigger_signal",
    "terminal_triggered",
    "ready_for_short_gate",
    "accepted_non_trigger_progress_events",
    "saved_non_trigger_progress_events",
    "non_trigger_progress_events",
    "candidate_events",
    "execs_done",
    "status",
    "next_action",
    "source_path",
]


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def intish(value: Any) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def validation_paths(inputs: list[str]) -> list[Path]:
    paths: list[Path] = []
    for raw in inputs:
        path = Path(raw)
        if path.is_dir():
            paths.extend(sorted(path.glob("*.validation.json")))
        elif path.exists():
            paths.append(path)
    return sorted(dict.fromkeys(paths))


def nested_dict(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    return value if isinstance(value, dict) else {}


def source_path(payload: dict[str, Any], path: Path) -> str:
    source = nested_dict(payload, "source")
    return str(source.get("summary_jsonl") or source.get("candidate_out_dir") or path)


def audit_record(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    benefit = nested_dict(payload, "benefit_readout")
    signal = nested_dict(payload, "binding_signal")
    checks = nested_dict(payload, "checks")
    target_id = str(payload.get("target_id") or "")
    accepted_non_trigger = intish(signal.get("accepted_non_trigger_progress_events"))
    saved_non_trigger = intish(benefit.get("saved_non_trigger_progress_events"))
    non_trigger_progress = intish(benefit.get("non_trigger_progress_events"))
    candidate_events = intish(signal.get("candidate_events"))
    execs_done = intish(benefit.get("execs_done"))
    terminal = boolish(benefit.get("terminal_triggered")) or boolish(
        checks.get("terminal_triggered")
    )
    ready = boolish(payload.get("ready_for_short_gate")) or str(payload.get("status") or "") == "native_binding_validated"
    non_trigger_delta = boolish(checks.get("non_trigger_candidate_lift_delta"))
    pretrigger_ready = boolish(benefit.get("pretrigger_lift_guidance_ready")) or boolish(
        checks.get("pretrigger_lift_guidance_ready")
    )
    strict = (
        accepted_non_trigger > 0
        or saved_non_trigger > 0
        or non_trigger_progress > 0
        or boolish(benefit.get("has_non_trigger_progress"))
    )
    soft = pretrigger_ready or non_trigger_delta or strict
    if strict and terminal:
        disposition = "mechanism_and_endpoint_candidate"
        next_action = "run matched baselines and baseline-guidance-gap analysis; promote only if baselines are late, missing, or high variance"
    elif strict:
        disposition = "mechanism_only_needs_endpoint"
        next_action = "run endpoint short screen against faithful AFL++ family baselines"
    elif terminal:
        disposition = "terminal_only_control"
        next_action = "keep as control or revise BindingSpec/seed distance; do not claim R-to-T guidance benefit"
    elif soft and ready:
        disposition = "soft_signal_needs_frontier_evidence"
        next_action = "collect accepted non-trigger frontier progress or a replayable signal path before efficacy claims"
    elif ready:
        disposition = "native_binding_validated_no_guidance_readout"
        next_action = "run or regenerate binding-signal diagnosis with benefit readout before endpoint spending"
    else:
        disposition = "validation_not_ready"
        next_action = "fix validation blockers before performance experiments"
    return {
        "target_id": target_id,
        "disposition": disposition,
        "strict_pretrigger_guidance": strict,
        "soft_pretrigger_signal": soft,
        "terminal_triggered": terminal,
        "ready_for_short_gate": ready,
        "accepted_non_trigger_progress_events": accepted_non_trigger,
        "saved_non_trigger_progress_events": saved_non_trigger,
        "non_trigger_progress_events": non_trigger_progress,
        "candidate_events": candidate_events,
        "execs_done": execs_done,
        "status": str(payload.get("status") or ""),
        "next_action": next_action,
        "source_path": str(path),
        "raw_source": source_path(payload, path),
    }


def record_rank(record: dict[str, Any]) -> tuple[int, int, int, int, int, str]:
    disposition_score = {
        "mechanism_and_endpoint_candidate": 6,
        "mechanism_only_needs_endpoint": 5,
        "soft_signal_needs_frontier_evidence": 4,
        "native_binding_validated_no_guidance_readout": 3,
        "terminal_only_control": 2,
        "validation_not_ready": 1,
    }
    return (
        disposition_score.get(str(record.get("disposition") or ""), 0),
        int(boolish(record.get("strict_pretrigger_guidance"))),
        int(boolish(record.get("ready_for_short_gate"))),
        intish(record.get("accepted_non_trigger_progress_events")),
        intish(record.get("execs_done")),
        str(record.get("source_path") or ""),
    )


def best_by_target(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        target_id = str(record.get("target_id") or "")
        if target_id:
            grouped[target_id].append(record)
    return [
        max(items, key=record_rank)
        for _target_id, items in sorted(grouped.items())
    ]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})


def write_md(path: Path, payload: dict[str, Any]) -> None:
    counts = payload["summary"]["target_disposition_counts"]
    rows = payload["targets"]
    lines = [
        "# Binding Validation Guidance Audit",
        "",
        f"Generated UTC: {payload['generated_at_utc']}",
        "",
        "This audit separates native BindingSpec validity from evidence that FORMTRIG produced accepted pre-trigger frontier guidance.",
        "",
        "## Summary",
        "",
        "| disposition | targets |",
        "|---|---:|",
    ]
    for key, value in sorted(counts.items()):
        lines.append(f"| `{key}` | {value} |")
    lines.extend(
        [
            "",
            "## Target Triage",
            "",
            "| target | disposition | strict pre-trigger | terminal | accepted non-trigger | next action |",
            "|---|---|---:|---:|---:|---|",
        ]
    )
    for row in sorted(rows, key=lambda item: (-record_rank(item)[0], str(item.get("target_id")))):
        lines.append(
            "| {target} | `{disp}` | {strict} | {terminal} | {accepted} | {action} |".format(
                target=row.get("target_id", ""),
                disp=row.get("disposition", ""),
                strict=str(row.get("strict_pretrigger_guidance")).lower(),
                terminal=str(row.get("terminal_triggered")).lower(),
                accepted=row.get("accepted_non_trigger_progress_events", 0),
                action=row.get("next_action", ""),
            )
        )
    lines.extend(
        [
            "",
            "## Claim Boundary",
            "",
            "- `terminal_only_control` means `_T` appeared without accepted non-trigger guidance; it must not be used as R-to-T guidance evidence.",
            "- `soft_signal_needs_frontier_evidence` means lifted signal moved before `_T`, but the current artifact lacks accepted/saved non-trigger frontier progress.",
            "- `mechanism_*` targets are candidates for matched baseline experiments, not final efficacy claims by themselves.",
            "",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def build_audit(inputs: list[str]) -> dict[str, Any]:
    records = []
    for path in validation_paths(inputs):
        try:
            records.append(audit_record(path))
        except (OSError, json.JSONDecodeError):
            continue
    targets = best_by_target(records)
    return {
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "schema": "formtrig_binding_validation_guidance_audit_v1",
        "record_count": len(records),
        "target_count": len(targets),
        "summary": {
            "record_disposition_counts": dict(Counter(row["disposition"] for row in records)),
            "target_disposition_counts": dict(Counter(row["disposition"] for row in targets)),
            "strict_pretrigger_target_count": sum(
                1 for row in targets if row["strict_pretrigger_guidance"]
            ),
            "terminal_only_target_count": sum(
                1 for row in targets if row["disposition"] == "terminal_only_control"
            ),
        },
        "records": records,
        "targets": targets,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--validation-root",
        action="append",
        default=[],
        help="validation JSON, validation dir, or root containing *.validation.json",
    )
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-csv", required=True)
    parser.add_argument("--out-md", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    roots = args.validation_root or ["artifacts/formtrig_native_readiness/binding_validation"]
    payload = build_audit(roots)
    write_json(Path(args.out_json), payload)
    write_csv(Path(args.out_csv), payload["targets"])
    write_md(Path(args.out_md), payload)


if __name__ == "__main__":
    main()
