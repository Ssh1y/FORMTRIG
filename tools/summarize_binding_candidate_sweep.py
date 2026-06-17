#!/usr/bin/env python3
"""Summarize a BindingSpec candidate sweep as a validation record."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def number(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def best_row(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise ValueError("candidate sweep summary contains no rows")
    return max(rows, key=lambda row: (number(row.get("score"), -10**12), -number(row.get("index"), 10**9)))


def status_for(row: dict[str, Any]) -> str:
    exit_code = number(row.get("exit_code"))
    pretrigger = boolish(row.get("pretrigger_lift_guidance_ready"))
    experiment_ready = boolish(row.get("experiment_ready"))
    binding_signal_pass = str(row.get("binding_signal_status") or "") == "pass"
    terminal_triggered = number(row.get("triggered_execs")) > 0
    semantic_variable_roles = number(row.get("semantic_candidate_variable_roles")) > 0
    if exit_code == 0 and experiment_ready and pretrigger and binding_signal_pass:
        return "native_binding_validated"
    if terminal_triggered and not pretrigger:
        if semantic_variable_roles:
            return "terminal_only_variable_semantic_roles_no_pretrigger_guidance"
        return "terminal_only_no_pretrigger_guidance"
    if exit_code != 0:
        return "validation_failed"
    if not experiment_ready:
        return "not_experiment_ready"
    if not binding_signal_pass:
        return "binding_signal_failed"
    return "needs_binding_repair"


def build_record(
    *,
    row: dict[str, Any],
    target_id: str,
    binding_spec: str,
    site_map: str,
    summary_jsonl: Path,
) -> dict[str, Any]:
    status = status_for(row)
    ready = status == "native_binding_validated"
    exit_code = number(row.get("exit_code"))
    pretrigger = boolish(row.get("pretrigger_lift_guidance_ready"))
    terminal_triggered = number(row.get("triggered_execs")) > 0
    binding_signal_pass = str(row.get("binding_signal_status") or "") == "pass"
    native_static_pass = exit_code == 0

    return {
        "schema": "formtrig_binding_candidate_validation_v1",
        "target_id": target_id,
        "binding_spec": binding_spec or str(row.get("candidate") or ""),
        "status": status,
        "ready_for_short_gate": ready,
        "native_site_map_validated": native_static_pass,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "checks": {
            "tool_compile_pass": native_static_pass,
            "binding_spec_compile_pass": native_static_pass,
            "lift_audit_pass": native_static_pass,
            "native_site_map_validated": native_static_pass,
            "runtime_event_map_pass": native_static_pass,
            "dynamic_binding_signal_pass": binding_signal_pass,
            "pretrigger_lift_guidance_ready": pretrigger,
            "non_trigger_candidate_lift_delta": boolish(row.get("non_trigger_candidate_lift_delta")),
            "lift_delta_only_on_triggered": boolish(row.get("lift_delta_only_on_triggered_candidates")),
            "terminal_triggered": terminal_triggered,
        },
        "native_site_map": {
            "path": site_map,
            "native_runtime_evidence": bool(site_map) and native_static_pass,
        },
        "dynamic_seed_readiness": {
            "status": "pass" if native_static_pass else "fail",
            "diagnosis": row.get("diagnosis") or "",
            "seed_count": None,
            "reached": number(row.get("reached_execs")),
            "triggered": number(row.get("triggered_execs")),
            "spec_lifted": None,
            "components": None,
            "atom_signals": None,
            "role_signals": None,
        },
        "binding_signal": {
            "status": row.get("binding_signal_status") or "",
            "diagnosis": row.get("binding_signal_diagnosis") or "",
            "candidate_events": number(row.get("candidate_events")),
            "accepted_non_trigger_progress_events": number(row.get("accepted_non_trigger_progress_events")),
            "semantic_candidate_variable_roles": number(row.get("semantic_candidate_variable_roles")),
        },
        "benefit_readout": {
            "terminal_triggered": terminal_triggered,
            "pretrigger_lift_guidance_ready": pretrigger,
            "has_non_trigger_progress": boolish(row.get("has_non_trigger_progress")),
            "non_trigger_progress_events": number(row.get("non_trigger_progress_events")),
            "saved_non_trigger_progress_events": number(row.get("saved_non_trigger_progress_events")),
            "saved_triggered_progress_events": number(row.get("saved_triggered_progress_events")),
            "execs_done": number(row.get("execs_done")),
            "score": number(row.get("score")),
        },
        "source": {
            "summary_jsonl": str(summary_jsonl),
            "candidate_out_dir": str(row.get("out_dir") or ""),
            "candidate_index": number(row.get("index")),
        },
        "blockers": blockers_for(status, row),
        "remaining_limitations": limitations_for(status, row),
        "next_action": next_action_for(status),
    }


def blockers_for(status: str, row: dict[str, Any]) -> list[str]:
    if status == "native_binding_validated":
        return []
    blockers: list[str] = []
    if number(row.get("exit_code")) != 0:
        blockers.append(f"candidate sweep exited with {number(row.get('exit_code'))}")
    if str(row.get("binding_signal_status") or "") != "pass":
        blockers.append(
            "binding-signal diagnosis is "
            f"{row.get('binding_signal_status') or 'missing'}/"
            f"{row.get('binding_signal_diagnosis') or 'missing'}"
        )
    if not boolish(row.get("pretrigger_lift_guidance_ready")):
        blockers.append("pre-trigger lift guidance is not ready")
    if status in {
        "terminal_only_no_pretrigger_guidance",
        "terminal_only_variable_semantic_roles_no_pretrigger_guidance",
    }:
        blockers.append("terminal signal appeared without non-trigger guidance")
    if status == "terminal_only_variable_semantic_roles_no_pretrigger_guidance":
        blockers.append(
            "semantic BindingSpec roles varied, but no accepted non-trigger frontier progress was observed"
        )
    return blockers


def limitations_for(status: str, row: dict[str, Any]) -> list[str]:
    limitations = [
        "candidate sweep is a validation gate, not a matched baseline comparison",
        "short-gate and long-run endpoint evidence are still required before efficacy claims",
    ]
    if status == "native_binding_validated" and number(row.get("accepted_non_trigger_progress_events")) == 0:
        limitations.append("binding-signal pass has no accepted non-trigger progress events in this summary")
    return limitations


def next_action_for(status: str) -> str:
    if status == "native_binding_validated":
        return "run the benefit-first short endpoint screen against faithful AFL++ family baselines"
    if status in {
        "terminal_only_no_pretrigger_guidance",
        "terminal_only_variable_semantic_roles_no_pretrigger_guidance",
    }:
        return "keep as negative/control evidence or revise the BindingSpec to expose non-trigger guidance"
    return "repair BindingSpec/native assets and rerun the candidate sweep"


def write_markdown(path: Path, record: dict[str, Any]) -> None:
    checks = record.get("checks") if isinstance(record.get("checks"), dict) else {}
    benefit = record.get("benefit_readout") if isinstance(record.get("benefit_readout"), dict) else {}
    lines = [
        f"# Binding Validation: {record['target_id']}",
        "",
        f"- Status: `{record['status']}`",
        f"- Ready for short gate: `{record['ready_for_short_gate']}`",
        f"- BindingSpec: `{record['binding_spec']}`",
        f"- Site map: `{record['native_site_map'].get('path', '')}`",
        f"- Dynamic signal pass: `{checks.get('dynamic_binding_signal_pass')}`",
        f"- Pre-trigger guidance ready: `{checks.get('pretrigger_lift_guidance_ready')}`",
        f"- Accepted non-trigger progress: `{record['binding_signal'].get('accepted_non_trigger_progress_events')}`",
        f"- Terminal triggered: `{benefit.get('terminal_triggered')}`",
        "",
        "## Blockers",
        "",
    ]
    blockers = record.get("blockers") or []
    if blockers:
        lines.extend(f"- {blocker}" for blocker in blockers)
    else:
        lines.append("- none")
    lines.extend(["", "## Next Action", "", record["next_action"], ""])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--summary-jsonl", type=Path, required=True)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--binding-spec", default="")
    parser.add_argument("--site-map", default="")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--out-md", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    row = best_row(read_jsonl(args.summary_jsonl))
    record = build_record(
        row=row,
        target_id=args.target_id,
        binding_spec=args.binding_spec,
        site_map=args.site_map,
        summary_jsonl=args.summary_jsonl,
    )
    write_json(args.out, record)
    if args.out_md:
        write_markdown(args.out_md, record)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
