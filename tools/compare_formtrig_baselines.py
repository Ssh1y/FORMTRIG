#!/usr/bin/env python3
"""Build a FORMTRIG-vs-baseline comparison package from saved evidence.

The tool is intentionally conservative. It treats FORMTRIG pre-trigger
guidance, FORMTRIG terminal success, and baseline terminal success as separate
facts, and it marks unmatched budgets or low replication as non-final evidence.
"""

from __future__ import annotations

import argparse
import csv
import json
import statistics
from pathlib import Path
from typing import Any


TSV_FIELDS = [
    "arm",
    "source_label",
    "target_id",
    "budget",
    "run_time",
    "rep",
    "success",
    "terminal_count",
    "trigger_time_s",
    "trigger_time_kind",
    "execs_done",
    "execs_per_sec",
    "reached",
    "accepted_non_trigger",
    "saved_non_trigger",
    "spec_lifted",
    "heuristic_lifted",
    "manual_lifted",
    "strict_pretrigger_guidance",
    "binding_signal_status",
    "source_path",
]


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


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


def str_value(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value)
    return value if value else None


def median(values: list[float]) -> float | int | None:
    if not values:
        return None
    result = statistics.median(values)
    if float(result).is_integer():
        return int(result)
    return result


def parse_labeled_path(value: str) -> tuple[str, Path]:
    if "=" in value:
        label, path = value.split("=", 1)
        if not label:
            raise SystemExit(f"empty label in argument: {value}")
        return label, Path(path)
    path = Path(value)
    return path.stem, path


def formtrig_gate_csv(path: Path) -> Path:
    if path.is_dir():
        candidate = path / "gate_summary.csv"
        if candidate.exists():
            return candidate
    return path


def strict_pretrigger(row: dict[str, Any]) -> bool:
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


def load_formtrig_rows(items: list[str], target_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        label, raw_path = parse_labeled_path(item)
        path = formtrig_gate_csv(raw_path)
        if not path.exists():
            raise SystemExit(f"FORMTRIG gate summary does not exist: {path}")
        with path.open(newline="", encoding="utf-8") as handle:
            for raw in csv.DictReader(handle):
                run_time = numeric(raw.get("run_time"))
                row = {
                    "arm": "formtrig",
                    "source_label": label,
                    "target_id": target_id,
                    "budget": int(run_time) if run_time is not None else None,
                    "run_time": int_value(raw.get("run_time")),
                    "rep": None,
                    "success": int_value(raw.get("terminal_triggered")) > 0,
                    "terminal_count": int_value(raw.get("terminal_triggered")),
                    "trigger_time_s": None,
                    "trigger_time_kind": None,
                    "execs_done": int_value(raw.get("execs_done")),
                    "execs_per_sec": str_value(raw.get("execs_per_sec")),
                    "reached": int_value(raw.get("reached")),
                    "accepted_non_trigger": int_value(raw.get("accepted_non_trigger")),
                    "saved_non_trigger": int_value(raw.get("saved_non_trigger")),
                    "spec_lifted": int_value(raw.get("spec_lifted")),
                    "heuristic_lifted": int_value(raw.get("heuristic_lifted")),
                    "manual_lifted": int_value(raw.get("manual_lifted")),
                    "strict_pretrigger_guidance": strict_pretrigger(raw),
                    "binding_signal_status": str_value(raw.get("binding_signal_status")),
                    "binding_signal_diagnosis": str_value(raw.get("binding_signal_diagnosis")),
                    "gate_status": str_value(raw.get("status")),
                    "gate_reasons": str_value(raw.get("reasons")),
                    "source_path": str(path),
                    "out_dir": str_value(raw.get("out_dir")),
                }
                rows.append(row)
    return rows


def baseline_terminal_count(row: dict[str, Any]) -> int:
    magma_triggered = int_value(row.get("magma_triggered"), -1)
    if magma_triggered >= 0:
        return magma_triggered
    return int_value(row.get("saved_crashes"))


def baseline_trigger_kind(row: dict[str, Any]) -> str | None:
    kind = str_value(row.get("trigger_time_kind"))
    if kind:
        return kind
    if row.get("trigger_time_s") not in (None, "") and int_value(row.get("saved_crashes")) > 0:
        return "first_saved_crash_filename_time_upper_bound"
    return None


def load_baseline_rows(items: list[str], target_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        label, path = parse_labeled_path(item)
        if not path.exists():
            raise SystemExit(f"baseline summary does not exist: {path}")
        data = read_json(path)
        for raw in data.get("records", []):
            if raw.get("target_id") != target_id:
                continue
            row = {
                "arm": "baseline",
                "source_label": label,
                "target_id": raw.get("target_id"),
                "baseline": raw.get("baseline"),
                "budget": int_value(raw.get("budget")),
                "run_time": int_value(raw.get("run_time")),
                "rep": raw.get("rep"),
                "success": parse_bool(raw.get("success")),
                "terminal_count": baseline_terminal_count(raw),
                "trigger_time_s": raw.get("trigger_time_s"),
                "trigger_time_kind": baseline_trigger_kind(raw),
                "execs_done": int_value(raw.get("execs_done")),
                "execs_per_sec": str_value(raw.get("execs_per_sec")),
                "reached": int_value(raw.get("magma_reached")),
                "accepted_non_trigger": None,
                "saved_non_trigger": None,
                "spec_lifted": None,
                "heuristic_lifted": None,
                "manual_lifted": None,
                "strict_pretrigger_guidance": False,
                "binding_signal_status": None,
                "source_path": raw.get("run_record", str(path)),
                "magma_triggered": raw.get("magma_triggered"),
                "saved_crashes": raw.get("saved_crashes"),
                "saved_hangs": raw.get("saved_hangs"),
            }
            rows.append(row)
    return rows


def budget_matches(a: Any, b: Any, tolerance: int) -> bool:
    na = numeric(a)
    nb = numeric(b)
    if na is None or nb is None:
        return False
    return abs(float(na) - float(nb)) <= tolerance


def summarize_baseline_groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[Any, Any, Any], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row.get("source_label"), row.get("baseline"), row.get("budget"))
        groups.setdefault(key, []).append(row)

    summaries = []
    for (_, baseline, budget), group in sorted(groups.items()):
        successes = [row for row in group if row.get("success")]
        trigger_times = [
            float(value)
            for row in successes
            if (value := numeric(row.get("trigger_time_s"))) is not None
        ]
        terminal_counts = [
            float(value)
            for row in group
            if (value := numeric(row.get("terminal_count"))) is not None
        ]
        summaries.append(
            {
                "baseline": baseline,
                "budget": budget,
                "reps": len(group),
                "successes": len(successes),
                "success_rate": len(successes) / len(group) if group else 0.0,
                "median_trigger_time_s": median(trigger_times),
                "median_terminal_count": median(terminal_counts),
            }
        )
    return summaries


def classify_evidence(
    formtrig_rows: list[dict[str, Any]],
    baseline_rows: list[dict[str, Any]],
    tolerance: int,
    min_reps: int,
) -> dict[str, Any]:
    reasons: list[str] = []
    matched_baselines = [
        baseline
        for baseline in baseline_rows
        if any(budget_matches(baseline.get("budget"), formtrig.get("budget"), tolerance) for formtrig in formtrig_rows)
    ]
    if not matched_baselines:
        reasons.append("missing_matched_budget_baselines")

    strict_formtrig = any(row.get("strict_pretrigger_guidance") for row in formtrig_rows)
    terminal_formtrig = any(int_value(row.get("terminal_count")) > 0 for row in formtrig_rows)
    if strict_formtrig:
        reasons.append("formtrig_strict_pretrigger_guidance_present")
    else:
        reasons.append("formtrig_strict_pretrigger_guidance_missing")
    if terminal_formtrig:
        reasons.append("formtrig_terminal_oracle_present")
    else:
        reasons.append("formtrig_terminal_oracle_missing")

    groups = summarize_baseline_groups(matched_baselines)
    low_rep_groups = [group for group in groups if int_value(group.get("reps")) < min_reps]
    if low_rep_groups:
        reasons.append("low_replication")

    successful_baselines = [group for group in groups if float(group.get("success_rate") or 0.0) > 0.0]
    if successful_baselines:
        reasons.append("matched_baseline_also_triggers")

    if not matched_baselines:
        verdict = "not_comparable_missing_matched_budget"
    elif successful_baselines:
        verdict = "baseline_also_triggers_not_sota_advantage"
    elif strict_formtrig and terminal_formtrig and not low_rep_groups:
        verdict = "positive_matched_comparison"
    elif strict_formtrig and terminal_formtrig:
        verdict = "positive_but_under_replicated"
    elif strict_formtrig:
        verdict = "pretrigger_guidance_only"
    else:
        verdict = "insufficient_formtrig_guidance_evidence"

    next_steps = []
    if not matched_baselines:
        budgets = sorted({row.get("budget") for row in formtrig_rows if row.get("budget") is not None})
        next_steps.append(f"run faithful baselines at FORMTRIG budget(s): {budgets}")
    if low_rep_groups or (matched_baselines and not groups):
        next_steps.append(f"collect at least {min_reps} repetitions per matched baseline/budget")
    if successful_baselines:
        next_steps.append("do not claim SOTA advantage on this target without harder targets or stronger statistics")
    if strict_formtrig and not terminal_formtrig:
        next_steps.append("pair pre-trigger guidance with a same-oracle terminal run before terminal TTE claims")

    return {
        "baseline_groups": groups,
        "matched_baseline_count": len(matched_baselines),
        "next_steps": next_steps,
        "reasons": reasons,
        "verdict": verdict,
    }


def tsv_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def write_tsv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=TSV_FIELDS,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({field: tsv_value(row.get(field)) for field in TSV_FIELDS})


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    def cell(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    lines = [
        f"# {payload['comparison_id']}",
        "",
        f"- target: `{payload['target_id']}`",
        f"- verdict: `{payload['analysis']['verdict']}`",
        f"- matched baselines: `{payload['analysis']['matched_baseline_count']}`",
        "",
        "## FORMTRIG Runs",
        "",
        "| label | budget | terminal | strict pre-trigger | execs | reached | spec lifted |",
        "| --- | ---: | ---: | --- | ---: | ---: | ---: |",
    ]
    for row in payload["formtrig_runs"]:
        lines.append(
            "| {source_label} | {budget} | {terminal_count} | {strict_pretrigger_guidance} | "
            "{execs_done} | {reached} | {spec_lifted} |".format(
                source_label=cell(row.get("source_label")),
                budget=cell(row.get("budget")),
                terminal_count=cell(row.get("terminal_count")),
                strict_pretrigger_guidance=cell(row.get("strict_pretrigger_guidance")),
                execs_done=cell(row.get("execs_done")),
                reached=cell(row.get("reached")),
                spec_lifted=cell(row.get("spec_lifted")),
            )
        )

    lines.extend(
        [
            "",
            "## Matched Baseline Groups",
            "",
            "| baseline | budget | reps | success rate | median trigger time | median terminal count |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for group in payload["analysis"]["baseline_groups"]:
        lines.append(
            "| {baseline} | {budget} | {reps} | {success_rate:.3f} | {median_trigger_time_s} | "
            "{median_terminal_count} |".format(
                baseline=cell(group.get("baseline")),
                budget=cell(group.get("budget")),
                reps=int_value(group.get("reps")),
                success_rate=float(group.get("success_rate") or 0.0),
                median_trigger_time_s=cell(group.get("median_trigger_time_s")),
                median_terminal_count=cell(group.get("median_terminal_count")),
            )
        )

    lines.extend(["", "## Reasons", ""])
    for reason in payload["analysis"]["reasons"]:
        lines.append(f"- `{reason}`")

    if payload["analysis"]["next_steps"]:
        lines.extend(["", "## Required Next Steps", ""])
        for step in payload["analysis"]["next_steps"]:
            lines.append(f"- {step}")

    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--comparison-id", required=True)
    parser.add_argument("--target-id", required=True)
    parser.add_argument(
        "--formtrig-gate",
        action="append",
        required=True,
        help="LABEL=path/to/gate_summary.csv or LABEL=gate_dir; repeatable",
    )
    parser.add_argument(
        "--baseline-summary",
        action="append",
        default=[],
        help="LABEL=path/to/summary.json; repeatable",
    )
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--budget-tolerance-sec", type=int, default=5)
    parser.add_argument("--min-reps", type=int, default=3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    formtrig_rows = load_formtrig_rows(args.formtrig_gate, args.target_id)
    baseline_rows = load_baseline_rows(args.baseline_summary, args.target_id)
    if not formtrig_rows:
        raise SystemExit("no FORMTRIG rows loaded")

    rows = formtrig_rows + baseline_rows
    analysis = classify_evidence(
        formtrig_rows,
        baseline_rows,
        args.budget_tolerance_sec,
        args.min_reps,
    )
    payload = {
        "analysis": analysis,
        "baseline_rows": baseline_rows,
        "comparison_id": args.comparison_id,
        "formtrig_runs": formtrig_rows,
        "target_id": args.target_id,
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "comparison.json", payload)
    write_tsv(out_dir / "comparison.tsv", rows)
    write_markdown(out_dir / "comparison.md", payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
