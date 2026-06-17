#!/usr/bin/env python3
"""Summarize FORMTRIG hook-ablation arms from gate outputs.

The summary is attribution evidence, not a cross-tool performance comparison:
it answers whether a target-specific external typed hook adds endpoint benefit
over FORMTRIG's built-in typed stage and over a generic external hook.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


TSV_FIELDS = [
    "label",
    "run",
    "hook_source",
    "hook_enabled",
    "run_time",
    "execs_done",
    "terminal_count",
    "first_terminal_time_s",
    "first_terminal_execs",
    "accepted_non_trigger",
    "saved_non_trigger",
    "spec_lifted",
    "strict_pretrigger_guidance",
    "typed_execs",
    "typed_finds",
    "source_path",
]


def parse_labeled_path(value: str) -> tuple[str, Path]:
    if "=" not in value:
        path = Path(value)
        return path.stem, path
    label, path = value.split("=", 1)
    if not label:
        raise SystemExit(f"empty label in argument: {value}")
    return label, Path(path)


def numeric(value: Any) -> int | float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        parsed = float(str(value))
    except ValueError:
        return None
    if parsed.is_integer():
        return int(parsed)
    return parsed


def int_value(value: Any, default: int = 0) -> int:
    parsed = numeric(value)
    return int(parsed) if parsed is not None else default


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise SystemExit(f"expected JSON object: {path}")
    return data


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def gate_csv(path: Path) -> Path:
    if path.is_dir():
        candidate = path / "gate_summary.csv"
        if candidate.exists():
            return candidate
    return path


def stats_path_from_gate_row(row: dict[str, str]) -> Path | None:
    out_dir = row.get("out_dir")
    if not out_dir:
        return None
    path = Path(out_dir) / "fuzzer_stats"
    return path if path.exists() else None


def stats_field(path: Path | None, key: str) -> int | float | None:
    if path is None or not path.exists():
        return None
    with path.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if ":" not in line:
                continue
            raw_key, raw_value = line.split(":", 1)
            if raw_key.strip() == key:
                return numeric(raw_value.strip())
    return None


def strict_pretrigger(row: dict[str, str]) -> bool:
    return (
        parse_bool(row.get("experiment_ready"))
        and parse_bool(row.get("pretrigger_lift_guidance_ready"))
        and int_value(row.get("accepted_non_trigger")) > 0
        and int_value(row.get("saved_non_trigger")) > 0
        and parse_bool(row.get("non_trigger_candidate_lift_delta"))
        and not parse_bool(row.get("lift_delta_only_on_triggered"))
        and int_value(row.get("spec_lifted")) > 0
        and int_value(row.get("heuristic_lifted")) == 0
        and int_value(row.get("manual_lifted")) == 0
        and str(row.get("binding_signal_status", "")).strip() == "pass"
    )


def load_gate_rows(items: list[str], hook_metadata: dict[str, Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        label, raw_path = parse_labeled_path(item)
        path = gate_csv(raw_path)
        if not path.exists():
            raise SystemExit(f"gate summary does not exist: {path}")
        hook = read_json(hook_metadata[label]) if label in hook_metadata else {}
        with path.open(newline="", encoding="utf-8") as handle:
            for raw in csv.DictReader(handle):
                stats_path = stats_path_from_gate_row(raw)
                rows.append(
                    {
                        "label": label,
                        "run": raw.get("run"),
                        "hook": hook,
                        "hook_enabled": parse_bool(hook.get("enabled")),
                        "hook_source": hook.get("source"),
                        "hook_path": hook.get("path"),
                        "hook_sha256": hook.get("sha256"),
                        "run_time": int_value(raw.get("run_time")),
                        "execs_done": int_value(raw.get("execs_done")),
                        "execs_per_sec": numeric(raw.get("execs_per_sec")),
                        "terminal_count": int_value(raw.get("terminal_triggered")),
                        "first_terminal_time_s": numeric(raw.get("first_terminal_time_s")),
                        "first_terminal_time_kind": raw.get("first_terminal_time_kind"),
                        "first_terminal_execs": numeric(raw.get("first_terminal_execs")),
                        "accepted_non_trigger": int_value(raw.get("accepted_non_trigger")),
                        "saved_non_trigger": int_value(raw.get("saved_non_trigger")),
                        "spec_lifted": int_value(raw.get("spec_lifted")),
                        "strict_pretrigger_guidance": strict_pretrigger(raw),
                        "binding_signal_status": raw.get("binding_signal_status"),
                        "binding_signal_diagnosis": raw.get("binding_signal_diagnosis"),
                        "typed_execs": stats_field(stats_path, "formtrig_typed_execs"),
                        "typed_finds": stats_field(stats_path, "formtrig_typed_finds"),
                        "typed_skips": stats_field(stats_path, "formtrig_typed_skips"),
                        "source_path": str(path),
                    }
                )
    return rows


def first_success(rows: list[dict[str, Any]], label: str) -> dict[str, Any] | None:
    successes = [
        row
        for row in rows
        if row.get("label") == label
        and int_value(row.get("terminal_count")) > 0
        and numeric(row.get("first_terminal_time_s")) is not None
    ]
    if not successes:
        return None
    return min(successes, key=lambda row: float(row["first_terminal_time_s"]))


def compute_speedup(primary: dict[str, Any] | None, control: dict[str, Any] | None, field: str) -> float | None:
    if not primary or not control:
        return None
    primary_value = numeric(primary.get(field))
    control_value = numeric(control.get(field))
    if primary_value is None or control_value is None or float(primary_value) <= 0:
        return None
    return float(control_value) / float(primary_value)


def analyze(
    rows: list[dict[str, Any]],
    primary_label: str,
    nohook_label: str,
    generic_label: str,
    min_reps: int,
) -> dict[str, Any]:
    primary = first_success(rows, primary_label)
    nohook = first_success(rows, nohook_label)
    generic = first_success(rows, generic_label)
    primary_reps = sum(1 for row in rows if row.get("label") == primary_label)
    control_reps = {
        nohook_label: sum(1 for row in rows if row.get("label") == nohook_label),
        generic_label: sum(1 for row in rows if row.get("label") == generic_label),
    }
    reasons: list[str] = []
    blocked_claims: list[str] = []

    if primary:
        reasons.append("primary_hook_terminal_success")
    else:
        reasons.append("primary_hook_no_terminal_success")
    if nohook:
        reasons.append("nohook_control_also_triggers")
    if generic:
        reasons.append("generic_hook_control_also_triggers")
    if primary_reps < min_reps or any(reps < min_reps for reps in control_reps.values()):
        reasons.append("low_replication")
        blocked_claims.append("ablation evidence is a smoke result until replicated")

    nohook_time_speedup = compute_speedup(primary, nohook, "first_terminal_time_s")
    generic_time_speedup = compute_speedup(primary, generic, "first_terminal_time_s")
    nohook_exec_speedup = compute_speedup(primary, nohook, "first_terminal_execs")
    generic_exec_speedup = compute_speedup(primary, generic, "first_terminal_execs")

    if primary and nohook and generic and nohook_time_speedup and generic_time_speedup:
        if nohook_time_speedup > 1.0 and generic_time_speedup > 1.0:
            verdict = "target_specific_hook_accelerates_ablation_controls"
            reasons.append("primary_hook_faster_than_nohook_and_generic")
        else:
            verdict = "ablation_controls_not_slower_than_primary"
            blocked_claims.append("target-specific hook acceleration is not established")
    elif primary:
        verdict = "primary_hook_success_controls_incomplete"
        blocked_claims.append("one or more ablation controls did not produce comparable endpoint timing")
    else:
        verdict = "no_primary_hook_endpoint"
        blocked_claims.append("primary hook did not produce terminal endpoint evidence")

    if nohook or generic:
        blocked_claims.append(
            "controls also trigger, so this target remains weak SOTA-gap evidence"
        )

    return {
        "blocked_claims": blocked_claims,
        "control_reps": control_reps,
        "generic_exec_speedup": generic_exec_speedup,
        "generic_time_speedup": generic_time_speedup,
        "min_reps": min_reps,
        "nohook_exec_speedup": nohook_exec_speedup,
        "nohook_time_speedup": nohook_time_speedup,
        "primary_label": primary_label,
        "primary_reps": primary_reps,
        "reasons": reasons,
        "verdict": verdict,
    }


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TSV_FIELDS, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in TSV_FIELDS})


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    analysis = payload["analysis"]
    lines = [
        f"# {payload['ablation_id']}",
        "",
        f"- target: `{payload['target_id']}`",
        f"- verdict: `{analysis['verdict']}`",
        f"- primary hook label: `{analysis['primary_label']}`",
        "",
        "## Attribution Readout",
        "",
    ]
    if analysis.get("nohook_time_speedup") is not None:
        lines.append(
            "- target-specific hook is "
            f"{analysis['nohook_time_speedup']:.2f}x faster than no-hook by first `_T`"
        )
    if analysis.get("generic_time_speedup") is not None:
        lines.append(
            "- target-specific hook is "
            f"{analysis['generic_time_speedup']:.2f}x faster than generic-hook by first `_T`"
        )
    if not any(line.startswith("- target-specific") for line in lines):
        lines.append("- no target-specific hook speedup is established")
    lines.extend(["", "Blocked or limited claims:"])
    for claim in analysis["blocked_claims"]:
        lines.append(f"- {claim}")
    if not analysis["blocked_claims"]:
        lines.append("- none")
    lines.extend(["", "## Arms", "", "| label | hook source | terminal | first _T | execs | strict pre-trigger | typed finds |", "| --- | --- | ---: | ---: | ---: | --- | ---: |"])
    for row in payload["runs"]:
        lines.append(
            "| {label} | {hook_source} | {terminal} | {tte} | {execs} | {strict} | {finds} |".format(
                label=row.get("label"),
                hook_source=row.get("hook_source") or "",
                terminal=row.get("terminal_count"),
                tte="" if row.get("first_terminal_time_s") is None else f"{float(row['first_terminal_time_s']):g}",
                execs="" if row.get("first_terminal_execs") is None else f"{float(row['first_terminal_execs']):g}",
                strict=str(row.get("strict_pretrigger_guidance")).lower(),
                finds="" if row.get("typed_finds") is None else row.get("typed_finds"),
            )
        )
    lines.extend(["", "## Reasons", ""])
    for reason in analysis["reasons"]:
        lines.append(f"- `{reason}`")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ablation-id", required=True)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--gate", action="append", default=[], help="LABEL=gate_summary.csv")
    parser.add_argument("--hook-metadata", action="append", default=[], help="LABEL=formtrig_mutation_hook.json")
    parser.add_argument("--primary-label", default="hooked")
    parser.add_argument("--nohook-label", default="nohook")
    parser.add_argument("--generic-label", default="generic")
    parser.add_argument("--min-reps", type=int, default=3)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    if not args.gate:
        raise SystemExit("at least one --gate is required")
    hook_metadata = dict(parse_labeled_path(item) for item in args.hook_metadata)
    rows = load_gate_rows(args.gate, hook_metadata)
    analysis = analyze(
        rows,
        primary_label=args.primary_label,
        nohook_label=args.nohook_label,
        generic_label=args.generic_label,
        min_reps=args.min_reps,
    )
    payload = {
        "ablation_id": args.ablation_id,
        "analysis": analysis,
        "runs": rows,
        "target_id": args.target_id,
    }
    out_dir = Path(args.out_dir)
    write_json(out_dir / "ablation_summary.json", payload)
    write_tsv(out_dir / "ablation_summary.tsv", rows)
    write_markdown(out_dir / "ablation_summary.md", payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
