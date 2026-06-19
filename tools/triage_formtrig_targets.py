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
    "best_formtrig_trigger_time_s",
    "tte_speedup_over_fastest_baseline",
    "main_claim_strength",
    "sota_pain_class",
    "sota_pain_evidence",
    "baseline_guidance_gap_status",
    "baseline_guidance_gap_evidence",
    "max_budget_s",
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
    "fastest_baseline_family_median_trigger_time_s",
    "best_formtrig_trigger_time_s",
    "tte_speedup_over_fastest_baseline",
    "main_claim_strength",
    "max_budget_s",
    "formtrig_terminal",
    "strict_pretrigger_guidance",
    "missing_required_baselines",
    "observed_benefits",
    "blocked_claims",
    "next_steps",
    "source_path",
]

ACCEPTABLE_BASELINE_FASTEST_TTE_S = 600.0

GUIDANCE_GAP_FIELDS = [
    "target_id",
    "analysis_id",
    "status",
    "interpretation",
    "fastest_successful_baseline_trigger_time_s",
    "pretrigger_binary_flat_measured",
    "pretrigger_binary_flat_pass",
    "endpoint_cost_pass",
    "reasons",
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


def baseline_guidance_gap_paths(inputs: list[str]) -> list[Path]:
    paths: list[Path] = []
    for raw in inputs:
        path = Path(raw)
        if path.is_dir():
            if (path / "baseline_guidance_gap.json").exists():
                paths.append(path / "baseline_guidance_gap.json")
            else:
                paths.extend(sorted(path.glob("*/baseline_guidance_gap.json")))
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


def baseline_guidance_gap_row(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
    return {
        "target_id": str(payload.get("target_id") or ""),
        "analysis_id": str(payload.get("analysis_id") or path.parent.name),
        "status": str(analysis.get("status") or ""),
        "interpretation": str(analysis.get("interpretation") or ""),
        "fastest_successful_baseline_trigger_time_s": numeric(
            analysis.get("fastest_successful_baseline_trigger_time_s")
        ),
        "pretrigger_binary_flat_measured": bool_value(
            analysis.get("pretrigger_binary_flat_measured")
        ),
        "pretrigger_binary_flat_pass": bool_value(
            analysis.get("pretrigger_binary_flat_pass")
        ),
        "endpoint_cost_pass": bool_value(analysis.get("endpoint_cost_pass")),
        "reasons": list(analysis.get("reasons") or []),
        "source_path": str(path),
    }


def baseline_guidance_gap_map(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_target: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if row.get("target_id"):
            by_target.setdefault(str(row["target_id"]), []).append(row)
    return {
        target_id: sorted(items, key=baseline_guidance_gap_rank)[0]
        for target_id, items in by_target.items()
    }


def baseline_guidance_gap_rank(row: dict[str, Any]) -> tuple[int, float, str]:
    status_order = {
        "measured_pass": 0,
        "fail_fast_baseline": 1,
        "fail_endpoint_cost_not_hard": 2,
        "under_replicated": 3,
        "not_measured": 4,
        "incomplete_required_baselines": 5,
        "fail_not_flat": 6,
    }
    fastest = numeric(row.get("fastest_successful_baseline_trigger_time_s"))
    return (
        status_order.get(str(row.get("status") or ""), 99),
        fastest if fastest is not None else float("inf"),
        str(row.get("source_path") or ""),
    )


def baseline_guidance_gap_evidence(row: dict[str, Any] | None) -> str:
    if not row:
        return ""
    parts = [
        f"baseline_guidance_gap.status={row.get('status')}",
        f"pre_T_binary_flat={str(row.get('pretrigger_binary_flat_pass')).lower()}",
    ]
    fastest = numeric(row.get("fastest_successful_baseline_trigger_time_s"))
    if fastest is not None:
        parts.append(f"fastest_baseline_T={fastest:g}s")
    interpretation = str(row.get("interpretation") or "")
    if interpretation:
        parts.append(interpretation)
    return "; ".join(parts)


HARD_SOTA_STRENGTHS = {
    "hard_endpoint_gap_candidate": "visible_endpoint_gap",
    "hard_speedup_or_reliability_candidate": "visible_hard_speedup_or_reliability",
    "hard_speedup_variance_candidate": "visible_hard_speedup_variance",
}

WEAK_SOTA_STRENGTHS = {
    "not_hard_pain_baseline_fast_enough": "not_visible_baseline_time_cost_acceptable",
    "moderate_speedup_needs_unacceptable_baseline_cost": "weak_or_moderate_baseline_time_cost",
    "weak_near_seed_or_harness_shaped_speedup": "not_visible_near_seed_or_harness_shaped",
    "moderate_speedup_needs_harder_design": "weak_or_moderate_needs_harder_design",
}


def metric_text(value: Any, suffix: str = "") -> str:
    parsed = numeric(value)
    if parsed is None:
        return ""
    return f"{parsed:g}{suffix}"


def package_metric_evidence(row: dict[str, Any]) -> str:
    parts: list[str] = []
    strength = str(row.get("main_claim_strength") or "")
    if strength:
        parts.append(f"strength={strength}")
    if value := metric_text(row.get("best_formtrig_trigger_time_s"), "s"):
        parts.append(f"FORMTRIG first_T={value}")
    if value := metric_text(row.get("fastest_baseline_trigger_time_s"), "s"):
        parts.append(f"baseline fastest_T={value}")
    if value := metric_text(row.get("fastest_baseline_family_median_trigger_time_s"), "s"):
        parts.append(f"baseline family_median_T={value}")
    if value := metric_text(row.get("tte_speedup_over_fastest_baseline"), "x"):
        parts.append(f"speedup={value}")
    baselines = list(row.get("successful_baselines") or [])
    if baselines:
        parts.append("baseline_visible=" + ",".join(str(name) for name in baselines))
    return "; ".join(parts)


def sota_pain_readout(
    items: list[dict[str, Any]],
    *,
    has_baseline_trigger: bool,
    has_speedup_candidate: bool,
    has_endpoint_candidate: bool,
    has_replicated_endpoint: bool,
    has_terminal_candidate: bool,
    has_mechanism_only: bool,
) -> tuple[str, str]:
    hard_items = [
        row
        for row in items
        if str(row.get("main_claim_strength") or "") in HARD_SOTA_STRENGTHS
    ]
    if hard_items:
        best = sorted(hard_items, key=package_rank)[0]
        strength = str(best.get("main_claim_strength") or "")
        fastest_baseline = numeric(best.get("fastest_baseline_trigger_time_s"))
        if (
            fastest_baseline is not None
            and fastest_baseline <= ACCEPTABLE_BASELINE_FASTEST_TTE_S
        ):
            return (
                "not_visible_baseline_time_cost_acceptable",
                join_values(
                    [
                        "a faithful baseline reaches _T within the acceptable-time threshold, so this is speedup evidence but not hard SOTA-pain evidence",
                        package_metric_evidence(best),
                    ]
                ),
            )
        if strength == "hard_endpoint_gap_candidate":
            detail = "matched baselines do not trigger while FORMTRIG reaches _T"
        elif strength == "hard_speedup_or_reliability_candidate":
            detail = "at least one strong baseline family is unstable or has low success under the matched budget"
        else:
            detail = "baseline families trigger, but their matched-budget R2T tail is long enough for a hard speedup claim"
        return HARD_SOTA_STRENGTHS[strength], join_values(
            [detail, package_metric_evidence(best)]
        )

    weak_items = [
        row
        for row in items
        if str(row.get("main_claim_strength") or "") in WEAK_SOTA_STRENGTHS
    ]
    if weak_items:
        best = sorted(weak_items, key=package_rank)[0]
        strength = str(best.get("main_claim_strength") or "")
        if strength == "not_hard_pain_baseline_fast_enough":
            detail = "a faithful baseline reaches _T within the acceptable-time threshold, so this is speedup/control evidence rather than hard SOTA-pain evidence"
        elif strength == "moderate_speedup_needs_unacceptable_baseline_cost":
            detail = "FORMTRIG speedup exists, but baseline time cost is not yet high enough to support hard SOTA-pain"
        elif strength == "weak_near_seed_or_harness_shaped_speedup":
            detail = "all required baseline families trigger too early, so the current harness/seed does not expose a hard SOTA gap"
        else:
            detail = "FORMTRIG speedup exists, but the baseline R2T is still too short or too under-designed for a main SOTA-gap claim"
        return WEAK_SOTA_STRENGTHS[strength], join_values(
            [detail, package_metric_evidence(best)]
        )

    if has_replicated_endpoint or (
        has_endpoint_candidate and has_terminal_candidate and not has_baseline_trigger
    ):
        endpoint_items = [
            row
            for row in items
            if row.get("verdict")
            in {
                "positive_endpoint_matched_comparison",
                "positive_endpoint_but_under_replicated",
            }
        ]
        best = sorted(endpoint_items or items, key=package_rank)[0]
        return (
            "visible_endpoint_gap_candidate",
            join_values(
                [
                    "FORMTRIG reaches _T while matched baselines have no successful trigger in the selected package",
                    package_metric_evidence(best),
                ]
            ),
        )

    if has_baseline_trigger and not has_speedup_candidate and not has_endpoint_candidate:
        return (
            "not_visible_baseline_visible_no_formtrig_advantage",
            "matched faithful baselines trigger and current evidence has no FORMTRIG first_T/TTE advantage",
        )
    if has_speedup_candidate:
        speedup_items = [
            row
            for row in items
            if row.get("verdict")
            in {"positive_speedup_matched_comparison", "speedup_but_under_replicated"}
            or (
                numeric(row.get("tte_speedup_over_fastest_baseline")) is not None
                and float(row.get("tte_speedup_over_fastest_baseline") or 0.0) > 1.0
            )
        ]
        best = sorted(speedup_items or items, key=package_rank)[0]
        return (
            "partial_speedup_needs_strength_gate",
            join_values(
                [
                    "FORMTRIG is faster, but this package lacks a hard/weak experiment-strength gate",
                    package_metric_evidence(best),
                ]
            ),
        )
    if has_terminal_candidate:
        return (
            "incomplete_endpoint_candidate_needs_baselines",
            "FORMTRIG terminal success is present, but matched required baselines or repetitions are incomplete",
        )
    if has_mechanism_only:
        return (
            "mechanism_only_no_sota_pain_yet",
            "lifted non-trigger guidance exists, but endpoint/TTE evidence against baselines is still missing",
        )
    return "not_assessed", "collect matched FORMTRIG and faithful baseline evidence"


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

    top_level_claim = str(payload.get("benefit_first_claim") or "")
    if top_level_claim:
        return {
            "summary": top_level_claim,
            "observed_benefits": [top_level_claim],
            "blocked_claims": list(payload.get("blocked_claims") or []),
            "design_evidence": list(payload.get("design_evidence") or []),
        }

    analysis = payload.get("analysis", {})
    reasons = set(analysis.get("reasons") or [])
    formtrig_runs = payload.get("formtrig_runs") or []
    terminal = any(int_value(row.get("terminal_count")) > 0 for row in formtrig_runs)
    strict = "formtrig_strict_pretrigger_guidance_present" in reasons
    baseline_groups = analysis.get("baseline_groups") or []
    baseline_triggers = any(float(group.get("success_rate") or 0.0) > 0.0 for group in baseline_groups)
    best_formtrig_tte = numeric(analysis.get("best_formtrig_trigger_time_s"))
    best_baseline_tte = numeric(analysis.get("fastest_baseline_trigger_time_s"))
    speedup = numeric(analysis.get("tte_speedup_over_fastest_baseline"))
    formtrig_faster = (
        best_formtrig_tte is not None
        and best_baseline_tte is not None
        and best_formtrig_tte < best_baseline_tte
    )

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
    if terminal and baseline_triggers and formtrig_faster:
        if speedup is not None:
            observed.append(
                f"FORMTRIG first `_T` is {speedup:.2f}x faster than the fastest matched successful baseline"
            )
        else:
            observed.append("FORMTRIG has a lower first `_T` than matched successful baselines")
    if baseline_triggers and not formtrig_faster:
        blocked.append("matched baselines also trigger, so terminal success alone is not a FORMTRIG advantage")
    if "low_replication" in reasons:
        blocked.append("replication is too low for a final performance claim")
    if analysis.get("missing_required_baselines"):
        blocked.append("required baseline families are still missing")
    if strict and not terminal:
        blocked.append("pre-trigger guidance is not paired with same-oracle FORMTRIG terminal success")

    if baseline_triggers and formtrig_faster:
        summary = "current package supports a matched-budget speedup benefit, subject to replication"
    elif baseline_triggers:
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
    if (
        isinstance(payload.get("formtrig"), dict)
        and isinstance(payload.get("baselines"), dict)
        and isinstance(payload.get("claim_boundary"), dict)
        and isinstance(payload.get("benefit"), dict)
    ):
        formtrig = payload.get("formtrig") or {}
        baselines = payload.get("baselines") or {}
        claim = payload.get("claim_boundary") or {}
        benefit = payload.get("benefit") or {}
        families = baselines.get("families") or []
        successful = [
            str(group.get("baseline"))
            for group in families
            if float(group.get("success_rate") or 0.0) > 0.0
        ]
        verdict = str(claim.get("verdict") or payload.get("verdict") or "")
        fastest_baseline_tte = numeric(baselines.get("fastest_successful_trigger_time_s"))
        fastest_family_median = numeric(
            baselines.get("fastest_family_median_success_tte_s")
        )
        formtrig_tte = numeric(formtrig.get("first_t_exact_time_s_median"))
        speedup = numeric(benefit.get("median_tte_speedup_vs_fastest_baseline_family_median"))
        hard_supported = bool_value(claim.get("hard_sota_pain_supported"))
        main_claim_strength = (
            "hard_speedup_or_reliability_candidate"
            if hard_supported
            else "not_hard_pain_baseline_fast_enough"
        )
        return {
            "comparison_id": payload.get("comparison_id") or path.parent.name,
            "target_id": payload.get("target_id"),
            "package_status": "needs_harder_experiment_design"
            if not hard_supported
            else "promote_or_extend_longruns",
            "verdict": verdict,
            "matched_baselines": int_value(baselines.get("total_runs")),
            "successful_baselines": successful,
            "fastest_baseline_trigger_time_s": fastest_baseline_tte,
            "fastest_baseline_family_median_trigger_time_s": fastest_family_median,
            "best_formtrig_trigger_time_s": formtrig_tte,
            "tte_speedup_over_fastest_baseline": speedup,
            "main_claim_strength": main_claim_strength,
            "max_budget_s": numeric(formtrig.get("budget_s")) or numeric(baselines.get("budget_s")),
            "formtrig_terminal": int_value(formtrig.get("successes")) > 0
            or int_value(formtrig.get("terminal_triggered_execs_total")) > 0,
            "strict_pretrigger_guidance": bool_value(
                formtrig.get("all_pretrigger_lift_guidance_ready")
            )
            or int_value(formtrig.get("saved_non_trigger_progress_events_total")) > 0,
            "longrun_10m_confirmed": False,
            "missing_required_baselines": [],
            "observed_benefits": list(claim.get("supported") or []),
            "blocked_claims": list(claim.get("not_supported") or [])
            + list(claim.get("why_not_hard_pain") or []),
            "next_steps": list(payload.get("next_actions") or []),
            "source_path": str(path),
        }

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
    fastest_baseline_tte = numeric(analysis.get("fastest_baseline_trigger_time_s"))
    fastest_baseline_family_median_tte = numeric(
        analysis.get("fastest_baseline_family_median_trigger_time_s")
    )
    if fastest_baseline_family_median_tte is None and trigger_times:
        fastest_baseline_family_median_tte = min(trigger_times)
    formtrig_runs = payload.get("formtrig_runs") or []
    arms = payload.get("arms") or []
    formtrig_terminal = any(
        int_value(row.get("terminal_count")) > 0 for row in formtrig_runs
    ) or any(
        int_value(row.get("terminal_triggered_execs")) > 0 for row in arms
    )
    strict = any(
        bool_value(row.get("strict_pretrigger_guidance")) for row in formtrig_runs
    ) or any(
        bool_value(row.get("pretrigger_lift_guidance_ready"))
        or bool_value(row.get("non_trigger_candidate_lift_delta"))
        or int_value(row.get("saved_non_trigger_progress_events")) > 0
        for row in arms
    )
    benefit = benefit_readout(payload)
    strength = analysis.get("experiment_strength")
    if isinstance(strength, dict):
        main_claim_strength = str(strength.get("main_claim_strength") or "")
        strength_actions = list(strength.get("recommended_design_actions") or [])
    else:
        main_claim_strength = ""
        strength_actions = []
    longrun_10m_confirmed = isinstance(
        payload.get("longrun_10m_confirmation"), dict
    ) or isinstance(analysis.get("longrun_10m_confirmation"), dict)
    reasons = set(analysis.get("reasons") or [])
    verdict = str(analysis.get("verdict") or payload.get("verdict") or "")
    speedup_verdict = verdict in {
        "positive_speedup_matched_comparison",
        "speedup_but_under_replicated",
    } or "formtrig_faster_than_successful_baselines" in reasons

    endpoint_verdict = verdict in {
        "positive_endpoint_matched_comparison",
        "positive_endpoint_but_under_replicated",
    } or "formtrig_endpoint_where_matched_baselines_do_not_trigger" in reasons
    budgets = [
        numeric(group.get("budget"))
        for group in groups
        if numeric(group.get("budget")) is not None
    ] + [
        numeric(row.get("budget"))
        for row in formtrig_runs
        if numeric(row.get("budget")) is not None
    ]
    max_budget = max(budgets) if budgets else None

    weak_main_claim = main_claim_strength in {
        "not_hard_pain_baseline_fast_enough",
        "moderate_speedup_needs_unacceptable_baseline_cost",
        "weak_near_seed_or_harness_shaped_speedup",
        "moderate_speedup_needs_harder_design",
    }

    if weak_main_claim:
        status = "needs_harder_experiment_design"
    elif verdict == "positive_speedup_matched_comparison":
        status = "promote_or_extend_longruns"
    elif speedup_verdict:
        status = "promote_or_complete_reps"
    elif verdict == "positive_endpoint_matched_comparison":
        status = "promote_or_extend_longruns"
    elif endpoint_verdict:
        status = "promote_or_complete_reps"
    elif successful:
        status = "control_or_negative"
    elif verdict in {"positive_matched_comparison", "positive_but_under_replicated"}:
        status = "promote_or_complete_reps"
    elif formtrig_terminal and strict and groups:
        status = "candidate_needs_required_baselines"
    elif strict and not formtrig_terminal:
        status = "mechanism_only_needs_terminal_oracle"
    elif verdict in {
        "mechanism_benefit_no_endpoint_success",
        "scalar_guidance_repair_no_endpoint_success",
        "pretrigger_guidance_only",
    }:
        status = "mechanism_only_needs_terminal_oracle"
    elif "constant_lift" in verdict or "formtrig_constant_lift_signal" in reasons:
        status = "needs_signal_refinement"
    elif "missing_matched_budget_baselines" in reasons:
        status = "incomparable_needs_matched_budget"
    else:
        status = "insufficient_evidence"

    return {
        "comparison_id": payload.get("comparison_id") or path.parent.name,
        "target_id": payload.get("target_id"),
        "package_status": status,
        "verdict": verdict,
        "matched_baselines": int_value(analysis.get("matched_baseline_count")),
        "successful_baselines": successful,
        "fastest_baseline_trigger_time_s": fastest_baseline_tte,
        "fastest_baseline_family_median_trigger_time_s": fastest_baseline_family_median_tte,
        "best_formtrig_trigger_time_s": numeric(analysis.get("best_formtrig_trigger_time_s")),
        "tte_speedup_over_fastest_baseline": numeric(
            analysis.get("tte_speedup_over_fastest_baseline")
        ),
        "main_claim_strength": main_claim_strength,
        "max_budget_s": max_budget,
        "formtrig_terminal": formtrig_terminal,
        "strict_pretrigger_guidance": strict,
        "longrun_10m_confirmed": longrun_10m_confirmed,
        "missing_required_baselines": list(analysis.get("missing_required_baselines") or []),
        "observed_benefits": list(benefit.get("observed_benefits") or []),
        "blocked_claims": list(benefit.get("blocked_claims") or []),
        "next_steps": unique(
            strength_actions
            + list(analysis.get("next_steps") or payload.get("next_actions") or [])
        ),
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
        "sota_pain_class": "manual",
        "sota_pain_evidence": reason,
        "formtrig_terminal": "",
        "strict_pretrigger_guidance": "",
        "observed_benefits": "",
        "blocked_claims": reason,
        "next_action": next_action,
        "sources": source,
    }


def target_rows(
    packages: list[dict[str, Any]],
    manual_rows: list[dict[str, Any]],
    guidance_gaps: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    guidance_gaps = guidance_gaps or {}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in packages:
        grouped.setdefault(str(row.get("target_id")), []).append(row)

    rows: list[dict[str, Any]] = []
    for target_id, items in sorted(grouped.items()):
        guidance_gap = guidance_gaps.get(target_id)
        guidance_status = str(guidance_gap.get("status") or "") if guidance_gap else ""
        guidance_evidence = baseline_guidance_gap_evidence(guidance_gap)
        has_baseline_trigger = any(row.get("successful_baselines") for row in items)
        has_speedup_candidate = any(
            row.get("verdict")
            in {"positive_speedup_matched_comparison", "speedup_but_under_replicated"}
            or numeric(row.get("tte_speedup_over_fastest_baseline")) is not None
            and float(row.get("tte_speedup_over_fastest_baseline") or 0.0) > 1.0
            for row in items
        )
        has_replicated_speedup = any(
            row.get("verdict") == "positive_speedup_matched_comparison"
            for row in items
        )
        has_replicated_endpoint = any(
            row.get("verdict") == "positive_endpoint_matched_comparison"
            and row.get("formtrig_terminal")
            and row.get("matched_baselines")
            and not row.get("successful_baselines")
            for row in items
        )
        has_endpoint_candidate = any(
            row.get("verdict")
            in {
                "positive_endpoint_matched_comparison",
                "positive_endpoint_but_under_replicated",
                "positive_matched_comparison",
                "positive_but_under_replicated",
            }
            and row.get("formtrig_terminal")
            and row.get("matched_baselines")
            and not row.get("successful_baselines")
            for row in items
        )
        has_10m_confirmation = any(row.get("longrun_10m_confirmed") for row in items)
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
        has_scalar_guidance = any(
            row.get("verdict") == "scalar_guidance_repair_no_endpoint_success"
            for row in items
        )
        has_mid_screen_guidance = any(
            row.get("verdict") == "pretrigger_guidance_improved_no_endpoint_success"
            for row in items
        )
        has_signal_refinement = any(row.get("package_status") == "needs_signal_refinement" for row in items)
        has_incomparable = any(row.get("package_status") == "incomparable_needs_matched_budget" for row in items)
        has_weak_main_claim = any(
            row.get("package_status") == "needs_harder_experiment_design"
            for row in items
        )
        has_acceptable_baseline_cost = any(
            row.get("main_claim_strength") == "not_hard_pain_baseline_fast_enough"
            for row in items
        )

        if guidance_status == "fail_fast_baseline":
            disposition = "demote_to_control_or_negative"
            priority = 90
            next_action = (
                "do not spend main long-run budget here; baseline guidance-gap "
                "analysis shows a faithful baseline reaches _T within the "
                "acceptable threshold"
            )
        elif has_acceptable_baseline_cost:
            disposition = "demote_to_control_or_negative"
            priority = 90
            next_action = (
                "do not spend main long-run budget here; report only as "
                "speedup/control evidence unless a new, harder harness/seed design "
                "makes faithful baseline trigger probability small"
            )
        elif has_weak_main_claim:
            disposition = "needs_harder_experiment_design"
            priority = 12
            next_action = (
                "improve experiment design before spending more main budget: "
                "use a higher-fidelity/raw-format harness or farther RNT seeds, "
                "add no-hook and generic-hook FORMTRIG ablations, and move hard-gap "
                "budget to targets where strong baselines have low success or long R2T tails"
            )
        elif has_replicated_speedup:
            disposition = "candidate_extend_longruns"
            priority = 15
            if has_10m_confirmation:
                next_action = (
                    "run 2h matched repetitions if retained as a paper case; "
                    "otherwise shift main budget to harder Magma/real-CVE targets"
                )
            else:
                next_action = "extend to longer matched-budget runs to test whether the replicated FORMTRIG TTE speedup persists"
        elif has_speedup_candidate:
            disposition = "candidate_complete_baselines_and_reps"
            priority = 20
            next_action = "complete repetitions and longer matched-budget runs to validate the observed FORMTRIG TTE speedup"
        elif has_replicated_endpoint:
            disposition = "candidate_extend_longruns"
            priority = 18
            next_action = "extend to longer matched-budget runs to test whether the replicated FORMTRIG endpoint benefit persists"
        elif has_endpoint_candidate:
            disposition = "candidate_complete_baselines_and_reps"
            priority = 20
            next_action = "complete repetitions and longer matched-budget runs to validate the observed FORMTRIG endpoint benefit"
        elif has_baseline_trigger:
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

        if has_weak_main_claim:
            best = sorted(
                [
                    row
                    for row in items
                    if row.get("package_status") == "needs_harder_experiment_design"
                ],
                key=package_rank,
            )[0]
        else:
            best = sorted(items, key=package_rank)[0]
        sources = unique([str(row.get("source_path")) for row in items])
        observed = unique(
            list(best.get("observed_benefits") or [])
            + [
                benefit
                for row in items
                if row is not best
                for benefit in row.get("observed_benefits", [])
            ]
        )
        blocked = unique(
            list(best.get("blocked_claims") or [])
            + [
                claim
                for row in items
                if row is not best
                for claim in row.get("blocked_claims", [])
            ]
        )
        if has_replicated_speedup:
            metric_items = [
                row for row in items
                if row.get("verdict") == "positive_speedup_matched_comparison"
            ]
        elif has_speedup_candidate:
            metric_items = [
                row for row in items
                if row.get("verdict")
                in {"positive_speedup_matched_comparison", "speedup_but_under_replicated"}
                or numeric(row.get("tte_speedup_over_fastest_baseline")) is not None
                and float(row.get("tte_speedup_over_fastest_baseline") or 0.0) > 1.0
            ]
        elif has_replicated_endpoint:
            metric_items = [
                row for row in items
                if row.get("verdict") == "positive_endpoint_matched_comparison"
            ]
        elif has_endpoint_candidate:
            metric_items = [
                row for row in items
                if row.get("verdict")
                in {
                    "positive_endpoint_matched_comparison",
                    "positive_endpoint_but_under_replicated",
                    "positive_matched_comparison",
                    "positive_but_under_replicated",
                }
                and row.get("formtrig_terminal")
                and row.get("matched_baselines")
                and not row.get("successful_baselines")
            ]
        else:
            metric_items = items

        successful = unique([baseline for row in metric_items for baseline in row.get("successful_baselines", [])])
        sota_pain_class, sota_pain_evidence = sota_pain_readout(
            items,
            has_baseline_trigger=has_baseline_trigger,
            has_speedup_candidate=has_speedup_candidate,
            has_endpoint_candidate=has_endpoint_candidate,
            has_replicated_endpoint=has_replicated_endpoint,
            has_terminal_candidate=has_terminal_candidate,
            has_mechanism_only=has_mechanism_only,
        )
        if guidance_gap:
            if guidance_status == "measured_pass":
                if sota_pain_class in {"not_assessed", "partial_speedup_needs_strength_gate"}:
                    sota_pain_class = "visible_baseline_guidance_gap"
                sota_pain_evidence = join_values([sota_pain_evidence, guidance_evidence])
            elif guidance_status == "fail_fast_baseline":
                sota_pain_class = "not_visible_baseline_time_cost_acceptable"
                sota_pain_evidence = guidance_evidence
            elif guidance_status:
                sota_pain_evidence = join_values([sota_pain_evidence, guidance_evidence])
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
        if has_speedup_candidate:
            stale_fragments = (
                "no endpoint/TTE benefit is established",
                "no arm reaches _T",
                "Redqueen/operand-aware baseline is still missing",
                "no time-to-_T or crash improvement is established",
                "replication is one run per arm and Redqueen/operand baseline is still missing",
                "no terminal _T event was observed",
                "no faithful AFL++/CmpLog/Redqueen performance comparison is made",
            )
            blocked = [
                claim for claim in blocked
                if not any(fragment in claim for fragment in stale_fragments)
            ]
        if has_replicated_endpoint:
            stale_fragments = (
                "replication is too low",
                "FORMTRIG first `_T`/TTE is not recorded",
                "matched baselines also trigger",
                "no strict pre-trigger guidance benefit is established",
                "required baseline families are still missing",
            )
            blocked = [
                claim for claim in blocked
                if not any(fragment in claim for fragment in stale_fragments)
            ]
        if has_scalar_guidance:
            stale_fragments = (
                "scalar D_F_spec_lifted is still constant",
                "D_F and D_F_spec_lifted are constant",
                "constant lifted D_F/D_F_spec_lifted identified",
                "no accepted non-trigger frontier progress is established",
            )
            observed = [
                benefit for benefit in observed
                if not any(fragment in benefit for fragment in stale_fragments)
            ]
            blocked = [
                claim for claim in blocked
                if not any(fragment in claim for fragment in stale_fragments)
            ]
        if has_mid_screen_guidance:
            stale_fragments = (
                "single 60s repetition",
                "single short readiness screen",
                "no terminal _T event was observed in either 60s",
                "no faithful AFL++/CmpLog/Redqueen performance comparison is made",
            )
            blocked = [
                claim for claim in blocked
                if not any(fragment in claim for fragment in stale_fragments)
            ]
        if has_baseline_trigger and not has_speedup_candidate and not has_endpoint_candidate:
            blocked = unique(
                ["matched faithful baselines trigger in the current package set; not a hard SOTA-gap target"]
                + blocked
            )
        if guidance_status and guidance_status != "measured_pass":
            blocked = unique(
                [
                    "baseline guidance-gap gate is not measured_pass: "
                    + guidance_status
                ]
                + blocked
            )
        trigger_times = [
            value
            for row in metric_items
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
                "best_formtrig_trigger_time_s": best.get("best_formtrig_trigger_time_s", ""),
                "tte_speedup_over_fastest_baseline": best.get(
                    "tte_speedup_over_fastest_baseline", ""
                ),
                "main_claim_strength": best.get("main_claim_strength", ""),
                "sota_pain_class": sota_pain_class,
                "sota_pain_evidence": sota_pain_evidence,
                "baseline_guidance_gap_status": guidance_status,
                "baseline_guidance_gap_evidence": guidance_evidence,
                "max_budget_s": best.get("max_budget_s", ""),
                "formtrig_terminal": has_any_terminal,
                "strict_pretrigger_guidance": has_any_strict,
                "observed_benefits": join_values(observed),
                "blocked_claims": join_values(blocked),
                "next_action": next_action,
                "sources": join_values(
                    sources
                    + ([str(guidance_gap.get("source_path"))] if guidance_gap else [])
                ),
            }
        )

    rows.extend(manual_rows)
    return sorted(rows, key=lambda row: (int_value(row.get("priority"), 999), str(row.get("target_id"))))


def status_rank(status: str) -> int:
    ranks = {
        "promote_or_complete_reps": 0,
        "promote_or_extend_longruns": 0,
        "needs_harder_experiment_design": 1,
        "candidate_needs_required_baselines": 1,
        "mechanism_only_needs_terminal_oracle": 2,
        "needs_signal_refinement": 3,
        "control_or_negative": 4,
        "incomparable_needs_matched_budget": 5,
        "insufficient_evidence": 6,
    }
    return ranks.get(status, 99)


def verdict_rank(verdict: str) -> int:
    ranks = {
        "positive_matched_comparison": 0,
        "positive_endpoint_matched_comparison": 0,
        "positive_but_under_replicated": 1,
        "positive_endpoint_but_under_replicated": 1,
        "positive_speedup_matched_comparison": 1,
        "replicated_speedup_control_not_hard_sota_pain": 1,
        "speedup_but_under_replicated": 2,
        "pretrigger_guidance_improved_no_endpoint_success": 3,
        "scalar_guidance_repair_no_endpoint_success": 4,
        "mechanism_benefit_no_endpoint_success": 5,
        "pretrigger_guidance_only": 6,
        "short_gate_no_terminal_constant_lift_signal": 7,
    }
    return ranks.get(verdict, 50)


def package_rank(row: dict[str, Any]) -> tuple[int, int, int, str]:
    return (
        status_rank(str(row.get("package_status"))),
        -int_value(row.get("max_budget_s")),
        verdict_rank(str(row.get("verdict"))),
        str(row.get("comparison_id")),
    )


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
        "oracle gap to close. Targets where matched baselines also trigger but",
        "FORMTRIG is not faster are kept as controls or negative evidence, not",
        "main SOTA-gap cases.",
        "",
        f"Promoted hard-target candidates: `{len(promoted)}`.",
        "",
        "## Target Queue",
        "",
        "| target | disposition | priority | SOTA pain | baseline triggers | FORMTRIG `_T` | fastest baseline `_T` | speedup | next action |",
        "| --- | --- | ---: | --- | --- | ---: | ---: | ---: | --- |",
    ]
    for row in targets:
        lines.append(
            "| {target_id} | `{disposition}` | {priority} | `{sota_pain}` | {baseline_triggers} | "
            "{formtrig_t} | {fastest} | {speedup} | {next_action} |".format(
                target_id=row.get("target_id", ""),
                disposition=row.get("disposition", ""),
                priority=row.get("priority", ""),
                sota_pain=row.get("sota_pain_class", ""),
                baseline_triggers=row.get("baseline_triggers", ""),
                formtrig_t=row.get("best_formtrig_trigger_time_s", ""),
                fastest=row.get("fastest_baseline_trigger_time_s", ""),
                speedup=row.get("tte_speedup_over_fastest_baseline", ""),
                next_action=row.get("next_action", ""),
            )
        )

    lines.extend(
        [
            "",
            "## Baseline Guidance-Gap Gate",
            "",
            "| target | status | evidence |",
            "| --- | --- | --- |",
        ]
    )
    for row in targets:
        if not row.get("baseline_guidance_gap_status"):
            continue
        lines.append(
            "| {target_id} | `{status}` | {evidence} |".format(
                target_id=row.get("target_id", ""),
                status=row.get("baseline_guidance_gap_status", ""),
                evidence=row.get("baseline_guidance_gap_evidence", ""),
            )
        )
    if not any(row.get("baseline_guidance_gap_status") for row in targets):
        lines.append("| none |  |  |")

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
    parser.add_argument(
        "--baseline-guidance-gap",
        action="append",
        default=[],
        help=(
            "baseline_guidance_gap.json, a gap dir, or root containing "
            "*/baseline_guidance_gap.json"
        ),
    )
    parser.add_argument("--out-json", required=True)
    parser.add_argument("--out-csv", required=True)
    parser.add_argument("--out-packages-csv")
    parser.add_argument("--out-md", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    comparison_inputs = args.comparison or ["artifacts/formtrig_native_readiness/comparisons"]
    packages = [
        row
        for path in comparison_paths(comparison_inputs)
        if (row := package_row(path)).get("target_id")
    ]
    gap_inputs = args.baseline_guidance_gap or [
        "artifacts/formtrig_native_readiness/baseline_guidance_gap"
    ]
    guidance_gap_rows = [
        baseline_guidance_gap_row(path)
        for path in baseline_guidance_gap_paths(gap_inputs)
        if path.exists()
    ]
    manuals = [parse_manual_target(value) for value in args.manual_target]
    targets = target_rows(packages, manuals, baseline_guidance_gap_map(guidance_gap_rows))
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "baseline_guidance_gap_count": len(guidance_gap_rows),
        "baseline_guidance_gaps": guidance_gap_rows,
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
