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
        "queued_items": event.get("queued_items"),
        "frontier_count": event.get("frontier_count"),
        "triggered": bool(event.get("triggered")),
        "lifted": bool(event.get("lifted")),
        "stable": event.get("stable"),
        "d_t": event.get("d_t"),
        "d_f": event.get("d_f"),
        "d_f_lifted": event.get("d_f_lifted"),
        "d_f_spec_lifted": event.get("d_f_spec_lifted"),
        "components": event.get("components"),
        "actionable_components": event.get("actionable_components"),
        "atom_signals": event.get("atom_signals"),
        "role_bits": event.get("role_bits"),
        "hot_ranges": event.get("hot_ranges"),
        "target_hit_count": event.get("target_hit_count"),
        "source_flags": event.get("source_flags"),
        "observed_source_flags": event.get("observed_source_flags"),
        "aux": event.get("aux"),
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


def is_lifted_nontrigger(event: dict[str, Any]) -> bool:
    if bool(event.get("triggered")):
        return False
    if bool(event.get("lifted")):
        return True
    spec_df = numeric(event.get("d_f_spec_lifted"))
    return spec_df is not None and spec_df >= 0


def distinct_numeric_count(values: list[Any]) -> int:
    seen: set[float] = set()
    for value in values:
        parsed = numeric(value)
        if parsed is not None:
            seen.add(float(parsed))
    return len(seen)


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
    first_typed_stage_start: dict[str, Any] | None = None
    first_typed_stage_end: dict[str, Any] | None = None
    first_typed_stage_start_before_trigger: dict[str, Any] | None = None
    first_typed_lifted_nontrigger_before_trigger: dict[str, Any] | None = None
    latest_event: dict[str, Any] | None = None
    saved_non_trigger = 0
    saved_trigger = 0
    calibrated_non_trigger = 0
    nontrigger_before_first_saved_trigger = 0
    typed_stage_starts = 0
    typed_stage_ends = 0
    typed_stage_nontrigger_starts = 0
    typed_stage_starts_before_trigger = 0
    typed_lifted_nontrigger_starts_before_trigger = 0

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
        if event_name == "typed_stage_start":
            typed_stage_starts += 1
            compact = compact_event(event)
            if first_typed_stage_start is None:
                first_typed_stage_start = compact
            if not triggered:
                typed_stage_nontrigger_starts += 1
            if first_saved_trigger is None:
                typed_stage_starts_before_trigger += 1
                if first_typed_stage_start_before_trigger is None:
                    first_typed_stage_start_before_trigger = compact
                if is_lifted_nontrigger(event):
                    typed_lifted_nontrigger_starts_before_trigger += 1
                    if first_typed_lifted_nontrigger_before_trigger is None:
                        first_typed_lifted_nontrigger_before_trigger = compact
        elif event_name == "typed_stage_end":
            typed_stage_ends += 1
            if first_typed_stage_end is None:
                first_typed_stage_end = compact_event(event)

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

    first_saved_trigger_after_typed_stage = (
        first_saved_trigger is not None
        and first_typed_stage_start_before_trigger is not None
    )
    typed_lifted_nontrigger_before_saved_trigger = (
        first_saved_trigger is not None
        and first_typed_lifted_nontrigger_before_trigger is not None
    )
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
    stable_frontier = (
        first_calibrated_non_trigger is not None
        and int_value(first_calibrated_non_trigger.get("stable")) > 0
    )
    sortable_lifted_df = distinct_numeric_count(preterminal_nontrigger_spec_df) >= 2
    actionable_typed_nontrigger = first_typed_lifted_nontrigger_before_trigger is not None

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
        "typed_stage_start_events": typed_stage_starts,
        "typed_stage_end_events": typed_stage_ends,
        "typed_stage_nontrigger_start_events": typed_stage_nontrigger_starts,
        "typed_stage_starts_before_first_saved_trigger": typed_stage_starts_before_trigger,
        "typed_lifted_nontrigger_starts_before_first_saved_trigger": typed_lifted_nontrigger_starts_before_trigger,
        "strict_pretrigger_guidance_seen": strict_pretrigger,
        "first_saved_trigger_after_typed_stage": first_saved_trigger_after_typed_stage,
        "typed_lifted_nontrigger_before_first_saved_trigger": typed_lifted_nontrigger_before_saved_trigger,
        "stable_frontier_before_first_saved_trigger": stable_frontier,
        "sortable_lifted_df_before_first_saved_trigger": sortable_lifted_df,
        "actionable_typed_nontrigger_before_first_saved_trigger": actionable_typed_nontrigger,
        "nontrigger_events_before_first_saved_trigger": nontrigger_before_first_saved_trigger,
        "preterminal_nontrigger_d_f_values": preterminal_nontrigger_df,
        "preterminal_nontrigger_d_f_spec_lifted_values": preterminal_nontrigger_spec_df,
        "first_calibrated_non_trigger": first_calibrated_non_trigger,
        "first_saved_non_trigger": first_saved_non_trigger,
        "first_saved_trigger": first_saved_trigger,
        "first_typed_stage_start": first_typed_stage_start,
        "first_typed_stage_end": first_typed_stage_end,
        "first_typed_stage_start_before_first_saved_trigger": first_typed_stage_start_before_trigger,
        "first_typed_lifted_nontrigger_before_first_saved_trigger": first_typed_lifted_nontrigger_before_trigger,
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
    typed_before_terminal_runs = [
        row
        for row in runs
        if row["progress_path"].get("first_saved_trigger_after_typed_stage")
    ]
    typed_lifted_before_terminal_runs = [
        row
        for row in runs
        if row["progress_path"].get("typed_lifted_nontrigger_before_first_saved_trigger")
    ]
    stable_frontier_runs = [
        row
        for row in runs
        if row["progress_path"].get("stable_frontier_before_first_saved_trigger")
    ]
    sortable_lifted_df_runs = [
        row
        for row in runs
        if row["progress_path"].get("sortable_lifted_df_before_first_saved_trigger")
    ]
    actionable_typed_runs = [
        row
        for row in runs
        if row["progress_path"].get("actionable_typed_nontrigger_before_first_saved_trigger")
    ]
    mutable_typed_runs = [row for row in runs if int_value(row.get("typed_finds")) > 0]
    total_typed_execs = sum(int_value(row.get("typed_execs")) for row in runs)
    total_typed_finds = sum(int_value(row.get("typed_finds")) for row in runs)
    typed_find_rate = (
        total_typed_finds / total_typed_execs if total_typed_execs > 0 else None
    )
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
        "typed_stage_before_terminal_runs": len(typed_before_terminal_runs),
        "typed_lifted_nontrigger_before_terminal_runs": len(typed_lifted_before_terminal_runs),
        "guidance_capability": {
            "stable_frontier_runs": len(stable_frontier_runs),
            "sortable_lifted_df_runs": len(sortable_lifted_df_runs),
            "actionable_typed_nontrigger_runs": len(actionable_typed_runs),
            "mutable_typed_find_runs": len(mutable_typed_runs),
            "total_typed_execs": total_typed_execs,
            "total_typed_finds": total_typed_finds,
            "typed_find_rate": typed_find_rate,
            "strict_saved_pretrigger_runs": len(strict_runs),
            "interpretation": (
                "FORMTRIG exposed stable/sortable/actionable/mutable intermediate "
                "signals before terminal _T, but strict saved non-trigger progress "
                "was not observed"
                if runs
                and len(stable_frontier_runs) == len(runs)
                and len(sortable_lifted_df_runs) == len(runs)
                and len(actionable_typed_runs) == len(runs)
                and len(mutable_typed_runs) == len(runs)
                and not strict_runs
                else "see per-run capability counts"
            ),
        },
        "verdict": verdict,
        "typed_attribution": (
            "terminal_after_typed_lifted_nontrigger_stage"
            if typed_lifted_before_terminal_runs
            else "terminal_after_typed_stage"
            if typed_before_terminal_runs
            else "no_typed_preterminal_attribution"
        ),
        "claim_boundary": (
            "calibrated_frontier is reported for diagnosis only; strict gate "
            "still requires saved non-trigger progress before terminal _T; "
            "typed-stage attribution explains mutation activity but does not "
            "upgrade the strict gate"
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
        f"- typed attribution: `{payload['typed_attribution']}`",
        f"- claim boundary: {payload['claim_boundary']}",
        "",
        "## Guidance Capability",
        "",
    ]
    capability = payload.get("guidance_capability", {})
    lines.extend(
        [
            f"- stable frontier runs: `{capability.get('stable_frontier_runs', 0)}/{payload['run_count']}`",
            f"- sortable lifted D_F runs: `{capability.get('sortable_lifted_df_runs', 0)}/{payload['run_count']}`",
            f"- actionable typed non-T runs: `{capability.get('actionable_typed_nontrigger_runs', 0)}/{payload['run_count']}`",
            f"- mutable typed-find runs: `{capability.get('mutable_typed_find_runs', 0)}/{payload['run_count']}`",
            f"- total typed finds: `{capability.get('total_typed_finds', 0)}` / typed execs `{capability.get('total_typed_execs', 0)}`",
            f"- strict saved pre-trigger runs: `{capability.get('strict_saved_pretrigger_runs', 0)}/{payload['run_count']}`",
            f"- interpretation: {capability.get('interpretation', 'see per-run capability counts')}",
            "",
            "## Runs",
            "",
        ]
    )
    lines.extend(
        [
        "| run | time | execs | calibrated non-T | saved non-T | saved T | first non-T exec | first T exec | typed starts | typed before T | typed lifted non-T before T | typed finds | status |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- | ---: | --- |",
        ]
    )
    for row in payload["runs"]:
        progress = row["progress_path"]
        first_nt = progress.get("first_saved_non_trigger") or {}
        first_t = progress.get("first_saved_trigger") or {}
        lines.append(
            "| {run} | {time} | {execs} | {cal_nt} | {saved_nt} | {saved_t} | {first_nt} | {first_t} | {typed_starts} | {typed_before_t} | {typed_lift_before_t} | {typed_finds} | {status} |".format(
                run=row["run"],
                time=cell(row.get("run_time_s")),
                execs=cell(row.get("execs_done")),
                cal_nt=progress.get("calibrated_non_trigger_events", 0),
                saved_nt=progress.get("saved_non_trigger_events", 0),
                saved_t=progress.get("saved_trigger_events", 0),
                first_nt=cell(first_nt.get("execs_done")),
                first_t=cell(first_t.get("execs_done")),
                typed_starts=progress.get("typed_stage_start_events", 0),
                typed_before_t="yes"
                if progress.get("first_saved_trigger_after_typed_stage")
                else "no",
                typed_lift_before_t="yes"
                if progress.get("typed_lifted_nontrigger_before_first_saved_trigger")
                else "no",
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
            ("first typed stage", "first_typed_stage_start"),
            (
                "first typed lifted non-T before T",
                "first_typed_lifted_nontrigger_before_first_saved_trigger",
            ),
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
