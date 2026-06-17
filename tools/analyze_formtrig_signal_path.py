#!/usr/bin/env python3
"""Audit FORMTRIG progress paths without changing the experiment gate.

The gate deliberately requires saved non-trigger progress for strict
pre-trigger guidance.  This helper explains what happened before that gate:
calibrated non-trigger frontier, saved non-trigger progress, saved terminal
progress, spec-lift attribution, and typed mutation activity.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def numeric(value: Any) -> float | int | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        parsed = float(str(value).strip())
    except ValueError:
        return None
    if parsed.is_integer():
        return int(parsed)
    return parsed


def int_value(value: Any, default: int = 0) -> int:
    parsed = numeric(value)
    return int(parsed) if parsed is not None else default


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


def compact_event(event: dict[str, Any]) -> dict[str, Any]:
    first_actionable = event.get("first_actionable")
    if not isinstance(first_actionable, dict):
        first_actionable = {}
    return {
        "event": event.get("event"),
        "reason": event.get("reason"),
        "execs_done": event.get("execs_done"),
        "queue_id": event.get("queue_id"),
        "triggered": bool(event.get("triggered")),
        "stable": event.get("stable"),
        "d_t": event.get("d_t"),
        "d_f": event.get("d_f"),
        "d_f_spec_lifted": event.get("d_f_spec_lifted"),
        "components": event.get("components"),
        "actionable_components": event.get("actionable_components"),
        "atom_signals": event.get("atom_signals"),
        "role_bits": event.get("role_bits"),
        "source_flags": event.get("source_flags"),
        "observed_source_flags": event.get("observed_source_flags"),
        "first_actionable": {
            "kind": first_actionable.get("kind"),
            "role": first_actionable.get("role"),
            "priority": first_actionable.get("priority"),
            "value": first_actionable.get("value"),
            "source_id": first_actionable.get("source_id"),
        }
        if first_actionable
        else None,
    }


def add_unique(values: list[Any], value: Any, limit: int = 16) -> None:
    if value is None:
        return
    if value in values:
        return
    if len(values) < limit:
        values.append(value)


def summarize_progress(progress_path: Path) -> dict[str, Any]:
    event_counts: Counter[str] = Counter()
    reason_counts: Counter[str] = Counter()
    source_flag_counts: Counter[str] = Counter()
    observed_source_flag_counts: Counter[str] = Counter()
    preterminal_nontrigger_df: list[Any] = []
    preterminal_nontrigger_spec_df: list[Any] = []
    first_calibrated_non_trigger: dict[str, Any] | None = None
    first_saved_non_trigger: dict[str, Any] | None = None
    first_saved_trigger: dict[str, Any] | None = None
    latest_event: dict[str, Any] | None = None
    saved_non_trigger = 0
    saved_trigger = 0
    calibrated_non_trigger = 0
    nontrigger_before_first_saved_trigger = 0

    if not progress_path.exists():
        return {
            "missing_progress_log": True,
            "event_counts": {},
            "reason_counts": {},
        }

    for line in progress_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        latest_event = compact_event(event)
        event_name = str(event.get("event") or "unknown")
        reason = str(event.get("reason") or "unknown")
        event_counts[event_name] += 1
        reason_counts[reason] += 1
        source_flag_counts[str(event.get("source_flags"))] += 1
        observed_source_flag_counts[str(event.get("observed_source_flags"))] += 1

        triggered = bool(event.get("triggered"))
        if not triggered and first_saved_trigger is None:
            nontrigger_before_first_saved_trigger += 1
            add_unique(preterminal_nontrigger_df, event.get("d_f"))
            add_unique(preterminal_nontrigger_spec_df, event.get("d_f_spec_lifted"))

        if event_name == "calibrated_frontier" and not triggered:
            calibrated_non_trigger += 1
            if first_calibrated_non_trigger is None:
                first_calibrated_non_trigger = compact_event(event)
        elif event_name == "saved_progress" and triggered:
            saved_trigger += 1
            if first_saved_trigger is None:
                first_saved_trigger = compact_event(event)
        elif event_name == "saved_progress" and not triggered:
            saved_non_trigger += 1
            if first_saved_non_trigger is None:
                first_saved_non_trigger = compact_event(event)

    strict_pretrigger = first_saved_non_trigger is not None and (
        first_saved_trigger is None
        or int_value(first_saved_non_trigger.get("execs_done"), 10**18)
        < int_value(first_saved_trigger.get("execs_done"), -1)
    )
    if strict_pretrigger:
        status = "strict_pretrigger_guidance_seen"
    elif first_saved_trigger is not None and first_calibrated_non_trigger is not None:
        status = "terminal_after_calibrated_frontier"
    elif first_saved_trigger is not None:
        status = "terminal_seen"
    elif first_calibrated_non_trigger is not None:
        status = "calibrated_frontier_only"
    else:
        status = "no_formtrig_signal"

    return {
        "missing_progress_log": False,
        "status": status,
        "event_counts": dict(sorted(event_counts.items())),
        "reason_counts": dict(reason_counts.most_common(12)),
        "source_flag_counts": dict(sorted(source_flag_counts.items())),
        "observed_source_flag_counts": dict(sorted(observed_source_flag_counts.items())),
        "calibrated_non_trigger_events": calibrated_non_trigger,
        "saved_non_trigger_events": saved_non_trigger,
        "saved_trigger_events": saved_trigger,
        "strict_pretrigger_guidance_seen": strict_pretrigger,
        "nontrigger_events_before_first_saved_trigger": nontrigger_before_first_saved_trigger,
        "preterminal_nontrigger_d_f_values": preterminal_nontrigger_df,
        "preterminal_nontrigger_d_f_spec_lifted_values": preterminal_nontrigger_spec_df,
        "first_calibrated_non_trigger": first_calibrated_non_trigger,
        "first_saved_non_trigger": first_saved_non_trigger,
        "first_saved_trigger": first_saved_trigger,
        "latest_event": latest_event,
    }


def summarize_run(run_dir: Path) -> dict[str, Any]:
    out_dir = run_dir / "out"
    default_dir = out_dir / "default"
    stats = read_stats(default_dir / "fuzzer_stats")
    progress = summarize_progress(default_dir / "formtrig_progress.jsonl")
    return {
        "run": run_dir.name,
        "out_dir": str(out_dir),
        "run_time_s": numeric(stats.get("run_time")),
        "execs_done": numeric(stats.get("execs_done")),
        "execs_per_sec": numeric(stats.get("execs_per_sec")),
        "reached_execs": int_value(stats.get("formtrig_reached_execs")),
        "triggered_execs": int_value(stats.get("formtrig_triggered_execs")),
        "queued_progress": int_value(stats.get("formtrig_queued_progress")),
        "frontier_updates": int_value(stats.get("formtrig_frontier_updates")),
        "typed_execs": int_value(stats.get("formtrig_typed_execs")),
        "typed_finds": int_value(stats.get("formtrig_typed_finds")),
        "stats_saved_non_trigger": int_value(stats.get("formtrig_saved_non_trigger_log_seen")),
        "stats_saved_trigger": int_value(stats.get("formtrig_saved_triggered_log_seen")),
        "progress_path": progress,
    }


def summarize(formtrig_dir: Path, target_id: str, run_root: Path | None = None) -> dict[str, Any]:
    runs = [
        summarize_run(path)
        for path in sorted(formtrig_dir.glob(f"*_{target_id}"))
        if path.is_dir()
    ]
    strict_runs = [
        row
        for row in runs
        if row["progress_path"].get("strict_pretrigger_guidance_seen")
    ]
    terminal_runs = [
        row for row in runs if int_value(row["progress_path"].get("saved_trigger_events")) > 0
    ]
    calibrated_runs = [
        row
        for row in runs
        if int_value(row["progress_path"].get("calibrated_non_trigger_events")) > 0
    ]
    if strict_runs:
        verdict = "strict_pretrigger_guidance_observed"
    elif terminal_runs and calibrated_runs:
        verdict = "terminal_after_calibrated_frontier_only"
    elif terminal_runs:
        verdict = "terminal_only"
    elif calibrated_runs:
        verdict = "calibrated_frontier_only"
    else:
        verdict = "no_formtrig_signal_observed"
    return {
        "analysis_time_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target_id": target_id,
        "run_root": str(run_root) if run_root else None,
        "formtrig_dir": str(formtrig_dir),
        "run_count": len(runs),
        "strict_pretrigger_guidance_runs": len(strict_runs),
        "terminal_runs": len(terminal_runs),
        "calibrated_frontier_runs": len(calibrated_runs),
        "verdict": verdict,
        "claim_boundary": (
            "calibrated_frontier is reported for diagnosis only; strict gate "
            "still requires saved non-trigger progress before terminal _T"
        ),
        "runs": runs,
    }


def cell(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def to_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# FORMTRIG Signal Path: {payload['target_id']}",
        "",
        f"- analysis: `{payload['analysis_time_utc']}`",
        f"- verdict: `{payload['verdict']}`",
        f"- claim boundary: {payload['claim_boundary']}",
        "",
        "| run | time | execs | calibrated non-T | saved non-T | saved T | first non-T exec | first T exec | typed finds | status |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for row in payload["runs"]:
        progress = row["progress_path"]
        first_nt = progress.get("first_saved_non_trigger") or {}
        first_t = progress.get("first_saved_trigger") or {}
        lines.append(
            "| {run} | {time} | {execs} | {cal_nt} | {saved_nt} | {saved_t} | {first_nt} | {first_t} | {typed_finds} | {status} |".format(
                run=row["run"],
                time=cell(row.get("run_time_s")),
                execs=cell(row.get("execs_done")),
                cal_nt=progress.get("calibrated_non_trigger_events", 0),
                saved_nt=progress.get("saved_non_trigger_events", 0),
                saved_t=progress.get("saved_trigger_events", 0),
                first_nt=cell(first_nt.get("execs_done")),
                first_t=cell(first_t.get("execs_done")),
                typed_finds=row.get("typed_finds", 0),
                status=progress.get("status", ""),
            )
        )
    lines.extend(["", "## Per-Run First Signals", ""])
    for row in payload["runs"]:
        progress = row["progress_path"]
        lines.append(f"### {row['run']}")
        for label, key in (
            ("first calibrated non-T", "first_calibrated_non_trigger"),
            ("first saved non-T", "first_saved_non_trigger"),
            ("first saved T", "first_saved_trigger"),
        ):
            event = progress.get(key)
            if event:
                lines.append(
                    f"- {label}: exec `{event.get('execs_done')}`, "
                    f"D_F `{event.get('d_f')}`, spec D_F `{event.get('d_f_spec_lifted')}`, "
                    f"reason `{event.get('reason')}`"
                )
            else:
                lines.append(f"- {label}: none")
        lines.append(
            "- preterminal non-T D_F values: `"
            + str(progress.get("preterminal_nontrigger_d_f_values", []))
            + "`"
        )
        lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--formtrig-dir", required=True, type=Path)
    parser.add_argument("--run-root", type=Path)
    parser.add_argument("--format", choices=["json", "md"], default="md")
    parser.add_argument("--out-json")
    parser.add_argument("--out-md")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = summarize(args.formtrig_dir, args.target_id, args.run_root)
    if args.out_json:
        out = Path(args.out_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.out_md:
        out = Path(args.out_md)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(to_markdown(payload), encoding="utf-8")
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(to_markdown(payload))


if __name__ == "__main__":
    main()
