#!/usr/bin/env python3
"""Triage FORMTRIG comparison packages into long-run target decisions.

This tool is intentionally benefit-first. It reads generated comparison
packages, summarizes which benefit claims are supported or blocked, and turns
that into a target-level queue for scarce long-run budget.
"""

from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CSV_FIELDS = [
    "target_id",
    "disposition",
    "priority",
    "best_package",
    "best_verdict",
    "baseline_triggers",
    "fastest_baseline_trigger_time_s",
    "formtrig_terminal",
    "strict_pretrigger_guidance",
    "observed_benefits",
    "blocked_claims",
    "next_action",
    "sources",
]


PACKAGE_FIELDS = [
    "comparison_id",
    "target_id",
    "package_status",
    "verdict",
    "matched_baselines",
    "successful_baselines",
    "fastest_baseline_trigger_time_s",
    "formtrig_terminal",
    "strict_pretrigger_guidance",
    "missing_required_baselines",
    "observed_benefits",
    "blocked_claims",
    "next_steps",
    "source_path",
]


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def comparison_paths(inputs: list[str]) -> list[Path]:
    paths: list[Path] = []
    for raw in inputs:
        path = Path(raw)
        if path.is_dir():
            if (path / "comparison.json").exists():
                paths.append(path / "comparison.json")
            else:
                paths.extend(sorted(path.glob("*/comparison.json")))
        else:
            paths.append(path)
    return sorted(dict.fromkeys(paths))


def numeric(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def int_value(value: Any, default: int = 0) -> int:
    parsed = numeric(value)
    return int(parsed) if parsed is not None else default


def bool_value(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def join_values(values: list[Any]) -> str:
    return "; ".join(str(value) for value in values if value not in (None, ""))


def unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out


def benefit_readout(payload: dict[str, Any]) -> dict[str, list[str] | str]:
    existing = payload.get("benefit_readout")
    if isinstance(existing, dict):
        return {
            "summary": str(existing.get("summary") or ""),
            "observed_benefits": list(existing.get("observed_benefits") or []),
            "blocked_claims": list(existing.get("blocked_claims") or []),
            "design_evidence": list(existing.get("design_evidence") or []),
        }

    analysis = payload.get("analysis", {})
    reasons = set(analysis.get("reasons") or [])
    formtrig_runs = payload.get("formtrig_runs") or []
    terminal = any(int_value(row.get("terminal_count")) > 0 for row in formtrig_runs)
    strict = "formtrig_strict_pretrigger_guidance_present" in reasons
    baseline_groups = analysis.get("baseline_groups") or []
    baseline_triggers = any(float(group.get("success_rate") or 0.0) > 0.0 for group in baseline_groups)

    observed: list[str] = []
    blocked: list[str] = []
    design: list[str] = []
    if strict:
        observed.append("binary or sparse trigger feedback was lifted into accepted non-trigger search progress")
        design.append("strict_pretrigger_guidance")
    if terminal:
        design.append("formtrig_terminal_oracle_success")
    if terminal and baseline_groups and not baseline_triggers:
        observed.append("FORMTRIG reaches terminal success where matched baselines do not trigger in this budget")
    if baseline_triggers:
        blocked.append("matched baselines also trigger, so terminal success alone is not a FORMTRIG advantage")
    if "low_replication" in reasons:
        blocked.append("replication is too low for a final performance claim")
    if analysis.get("missing_required_baselines"):
        blocked.append("required baseline families are still missing")
    if strict and not terminal:
        blocked.append("pre-trigger guidance is not paired with same-oracle FORMTRIG terminal success")

    if baseline_triggers:
        summary = "mechanism benefit is present, but performance advantage is not established on this target"
    elif terminal and observed:
        summary = "current package supports a matched-budget terminal-success benefit, subject to blockers"
    elif strict:
        summary = "current package supports mechanism/search-guidance benefit only"
    else:
        summary = "no benefit claim is supported by the current package"
    return {
        "summary": summary,
        "observed_benefits": observed,
        "blocked_claims": blocked,
        "design_evidence": design,
    }


def package_row(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    analysis = payload.get("analysis", {})
    groups = analysis.get("baseline_groups") or []
    successful = [
        str(group.get("baseline"))
        for group in groups
        if float(group.get("success_rate") or 0.0) > 0.0
    ]
    trigger_times = [
        value
        for group in groups
        if float(group.get("success_rate") or 0.0) > 0.0
        if (value := numeric(group.get("median_trigger_time_s"))) is not None
    ]
    formtrig_runs = payload.get("formtrig_runs") or []
    formtrig_terminal = any(int_value(row.get("terminal_count")) > 0 for row in formtrig_runs)
    strict = any(bool_value(row.get("strict_pretrigger_guidance")) for row in formtrig_runs)
    benefit = benefit_readout(payload)
    reasons = set(analysis.get("reasons") or [])
    verdict = str(analysis.get("verdict") or "")

    if successful:
        status = "control_or_negative"
    elif verdict in {"positive_matched_comparison", "positive_but_under_replicated"}:
        status = "promote_or_complete_reps"
    elif formtrig_terminal and strict and groups:
        status = "candidate_needs_required_baselines"
    elif strict and not formtrig_terminal:
        status = "mechanism_only_needs_terminal_oracle"
    elif "constant_lift" in verdict or "formtrig_constant_lift_signal" in reasons:
        status = "needs_signal_refinement"
    elif "missing_matched_budget_baselines" in reasons:
        status = "incomparable_needs_matched_budget"
    else:
        status = "insufficient_evidence"

    return {
        "comparison_id": payload.get("comparison_id"),
        "target_id": payload.get("target_id"),
        "package_status": status,
        "verdict": verdict,
        "matched_baselines": int_value(analysis.get("matched_baseline_count")),
        "successful_baselines": successful,
        "fastest_baseline_trigger_time_s": min(trigger_times) if trigger_times else None,
        "formtrig_terminal": formtrig_terminal,
        "strict_pretrigger_guidance": strict,
        "missing_required_baselines": list(analysis.get("missing_required_baselines") or []),
        "observed_benefits": list(benefit.get("observed_benefits") or []),
        "blocked_claims": list(benefit.get("blocked_claims") or []),
        "next_steps": list(analysis.get("next_steps") or []),
        "source_path": str(path),
    }


def parse_manual_target(value: str) -> dict[str, Any]:
    parts = value.split("|")
    if len(parts) != 5:
        raise SystemExit(
            "--manual-target must be TARGET|DISPOSITION|REASON|NEXT_ACTION|SOURCE"
        )
    target, disposition, reason, next_action, source = parts
    return {
        "target_id": target,
        "manual": True,
        "disposition": disposition,
        "priority": 99 if disposition.startswith("demote") else 50,
        "best_package": "",
        "best_verdict": disposition,
        "baseline_triggers": "",
        "fastest_baseline_trigger_time_s": "",
        "formtrig_terminal": "",
        "strict_pretrigger_guidance": "",
        "observed_benefits": "",
        "blocked_claims": reason,
        "next_action": next_action,
        "sources": source,
    }


def target_rows(packages: list[dict[str, Any]], manual_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in packages:
        grouped.setdefault(str(row.get("target_id")), []).append(row)

    rows: list[dict[str, Any]] = []
    for target_id, items in sorted(grouped.items()):
        has_baseline_trigger = any(row.get("successful_baselines") for row in items)
        has_terminal_candidate = any(
            row.get("formtrig_terminal")
            and row.get("strict_pretrigger_guidance")
            and not row.get("successful_baselines")
            and row.get("matched_baselines")
            for row in items
        )
        has_mechanism_only = any(
            row.get("strict_pretrigger_guidance") and not row.get("formtrig_terminal")
            for row in items
        )
        has_signal_refinement = any(row.get("package_status") == "needs_signal_refinement" for row in items)
        has_incomparable = any(row.get("package_status") == "incomparable_needs_matched_budget" for row in items)

        if has_baseline_trigger:
            disposition = "demote_to_control_or_negative"
            priority = 90
            next_action = "do not spend main long-run budget here; use as control/evidence plumbing and search harder targets"
        elif has_terminal_candidate:
            disposition = "candidate_complete_baselines_and_reps"
            priority = 20
            next_action = "complete required baselines, add repetitions, and rerun FORMTRIG with first-T monitoring"
        elif has_mechanism_only:
            disposition = "mechanism_only_needs_terminal_oracle"
            priority = 40
            next_action = "pair pre-trigger guidance with same-oracle terminal run before performance claims"
        elif has_signal_refinement:
            disposition = "short_gate_needs_signal_refinement"
            priority = 35
            next_action = "refine BindingSpec/root-state guidance until non-trigger D_F variability appears, then rerun 10-30m FORMTRIG/baseline screen"
        elif has_incomparable:
            disposition = "needs_matched_budget_baselines"
            priority = 50
            next_action = "generate matched-budget faithful baseline package"
        else:
            disposition = "insufficient_evidence"
            priority = 70
            next_action = "collect FORMTRIG gate evidence and matched baseline package"

        best = sorted(items, key=lambda row: status_rank(str(row.get("package_status"))))[0]
        sources = unique([str(row.get("source_path")) for row in items])
        observed = unique([benefit for row in items for benefit in row.get("observed_benefits", [])])
        blocked = unique([claim for row in items for claim in row.get("blocked_claims", [])])
        successful = unique([baseline for row in items for baseline in row.get("successful_baselines", [])])
        has_any_terminal = any(row.get("formtrig_terminal") for row in items)
        has_any_strict = any(row.get("strict_pretrigger_guidance") for row in items)
        if has_any_strict:
            blocked = [
                claim for claim in blocked
                if claim != "no strict pre-trigger guidance benefit is established"
            ]
        if has_any_terminal:
            blocked = [
                claim for claim in blocked
                if claim != "no FORMTRIG terminal success is established"
            ]
        if has_baseline_trigger:
            blocked = unique(
                ["matched faithful baselines trigger in the current package set; not a hard SOTA-gap target"]
                + blocked
            )
        trigger_times = [
            value
            for row in items
            if (value := numeric(row.get("fastest_baseline_trigger_time_s"))) is not None
        ]

        rows.append(
            {
                "target_id": target_id,
                "disposition": disposition,
                "priority": priority,
                "best_package": best.get("comparison_id"),
                "best_verdict": best.get("verdict"),
                "baseline_triggers": ",".join(successful),
                "fastest_baseline_trigger_time_s": min(trigger_times) if trigger_times else "",
                "formtrig_terminal": has_any_terminal,
                "strict_pretrigger_guidance": has_any_strict,
                "observed_benefits": join_values(observed),
                "blocked_claims": join_values(blocked),
                "next_action": next_action,
                "sources": join_values(sources),
            }
        )

    rows.extend(manual_rows)
    return sorted(rows, key=lambda row: (int_value(row.get("priority"), 999), str(row.get("target_id"))))


def status_rank(status: str) -> int:
    ranks = {
        "promote_or_complete_reps": 0,
        "candidate_needs_required_baselines": 1,
        "mechanism_only_needs_terminal_oracle": 2,
        "needs_signal_refinement": 3,
        "control_or_negative": 4,
        "incomparable_needs_matched_budget": 5,
        "insufficient_evidence": 6,
    }
    return ranks.get(status, 99)


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
            lineterminator="\n",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({field: csv_value(row.get(field)) for field in fields})


def csv_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return ",".join(str(item) for item in value)
    if value is None:
        return ""
    return str(value)


def write_markdown(path: Path, targets: list[dict[str, Any]], packages: list[dict[str, Any]]) -> None:
    promoted = [
        row for row in targets
        if str(row.get("disposition", "")).startswith("candidate")
        or str(row.get("disposition", "")).startswith("promote")
    ]
    lines = [
        "# FORMTRIG Hard-Target Triage",
        "",
        "This report is benefit-first. A target is promoted only when current",
        "evidence supports a terminal/TTE benefit against matched faithful",
        "baselines, or when it has mechanism evidence and a concrete terminal",
        "oracle gap to close. Targets where matched baselines also trigger are",
        "kept as controls or negative evidence, not main SOTA-gap cases.",
        "",
        f"Promoted hard-target candidates: `{len(promoted)}`.",
        "",
        "## Target Queue",
        "",
        "| target | disposition | priority | baseline triggers | fastest baseline `_T` | next action |",
        "| --- | --- | ---: | --- | ---: | --- |",
    ]
    for row in targets:
        lines.append(
            "| {target_id} | `{disposition}` | {priority} | {baseline_triggers} | "
            "{fastest} | {next_action} |".format(
                target_id=row.get("target_id", ""),
                disposition=row.get("disposition", ""),
                priority=row.get("priority", ""),
                baseline_triggers=row.get("baseline_triggers", ""),
                fastest=row.get("fastest_baseline_trigger_time_s", ""),
                next_action=row.get("next_action", ""),
            )
        )

    lines.extend(
        [
            "",
            "## Package Evidence",
            "",
            "| comparison | target | status | verdict | successful baselines | benefits | blocked claims |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in sorted(packages, key=lambda item: (str(item.get("target_id")), str(item.get("comparison_id")))):
        lines.append(
            "| {comparison_id} | {target_id} | `{status}` | `{verdict}` | {successful} | {benefits} | {blocked} |".format(
                comparison_id=row.get("comparison_id", ""),
                target_id=row.get("target_id", ""),
                status=row.get("package_status", ""),
                verdict=row.get("verdict", ""),
                successful=",".join(row.get("successful_baselines") or []),
                benefits=join_values(row.get("observed_benefits") or []),
                blocked=join_values(row.get("blocked_claims") or []),
            )
        )

    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--comparison",
        action="append",
        default=[],
        help="comparison.json, comparison dir, or root containing */comparison.json",
    )
    parser.add_argument(
        "--manual-target",
        action="append",
        default=[],
        help="TARGET|DISPOSITION|REASON|NEXT_ACTION|SOURCE",
    )
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-csv", required=True)
    parser.add_argument("--out-packages-csv")
    parser.add_argument("--out-md", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    comparison_inputs = args.comparison or ["artifacts/formtrig_native_readiness/comparisons"]
    packages = [package_row(path) for path in comparison_paths(comparison_inputs)]
    manuals = [parse_manual_target(value) for value in args.manual_target]
    targets = target_rows(packages, manuals)
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "package_count": len(packages),
        "packages": packages,
        "target_count": len(targets),
        "targets": targets,
    }
    write_json(Path(args.out_json), payload)
    write_csv(Path(args.out_csv), targets, CSV_FIELDS)
    if args.out_packages_csv:
        write_csv(Path(args.out_packages_csv), packages, PACKAGE_FIELDS)
    write_markdown(Path(args.out_md), targets, packages)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
