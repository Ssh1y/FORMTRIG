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
import re
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
    "trigger_execs",
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

EARLY_BASELINE_FAMILY_MEDIAN_TTE_S = 60.0
MODERATE_BASELINE_FAMILY_MEDIAN_TTE_S = 300.0
ACCEPTABLE_BASELINE_FASTEST_TTE_S = 600.0
HARD_BASELINE_FASTEST_TTE_S = 1800.0
HARD_SOTA_STRENGTHS = {
    "hard_endpoint_gap_candidate",
    "hard_speedup_or_reliability_candidate",
    "hard_speedup_variance_candidate",
}


def baseline_guidance_gap_requirement(main_strength: str) -> dict[str, Any]:
    required = main_strength in HARD_SOTA_STRENGTHS
    return {
        "required_for_hard_sota_pain": required,
        "status": "not_measured" if required else "not_required_for_current_strength",
        "required_evidence": [
            "baseline-visible TC signal is flat or binary before _T",
            "accepted non-trigger improvement under the baseline-visible signal is absent",
            "matched repeated endpoint runs are late, missing, or high-variance",
        ],
    }


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def baseline_guidance_gap_json(path: Path) -> Path:
    if path.is_dir():
        candidate = path / "baseline_guidance_gap.json"
        if candidate.exists():
            return candidate
    return path


def apply_baseline_guidance_gap(
    analysis: dict[str, Any],
    gap_payload: dict[str, Any],
    source_path: Path,
    target_id: str | None = None,
) -> dict[str, Any]:
    """Attach measured baseline no-guidance evidence to a comparison analysis."""

    payload_target = gap_payload.get("target_id")
    if target_id and payload_target and payload_target != target_id:
        raise SystemExit(
            f"baseline guidance-gap target mismatch: expected {target_id}, got {payload_target}"
        )

    strength = analysis.get("experiment_strength")
    if not isinstance(strength, dict):
        return analysis
    existing_gap = strength.get("baseline_guidance_gap")
    if not isinstance(existing_gap, dict):
        return analysis

    measured = gap_payload.get("analysis", {})
    if not isinstance(measured, dict):
        return analysis

    merged = {
        **existing_gap,
        "analysis_id": gap_payload.get("analysis_id"),
        "source_path": str(source_path),
        "status": measured.get("status", existing_gap.get("status")),
        "interpretation": measured.get("interpretation"),
        "reasons": measured.get("reasons", []),
        "pretrigger_binary_flat_measured": measured.get("pretrigger_binary_flat_measured"),
        "pretrigger_binary_flat_pass": measured.get("pretrigger_binary_flat_pass"),
        "endpoint_cost_pass": measured.get("endpoint_cost_pass"),
        "fastest_successful_baseline_trigger_time_s": measured.get(
            "fastest_successful_baseline_trigger_time_s"
        ),
        "baseline_groups": measured.get("baseline_groups", []),
    }
    strength["baseline_guidance_gap"] = merged
    if merged.get("status") == "measured_pass":
        if "baseline_guidance_gap_measured_pass" not in strength.setdefault("reasons", []):
            strength["reasons"].append("baseline_guidance_gap_measured_pass")
        if "baseline_guidance_gap_measured_pass" not in analysis.setdefault("reasons", []):
            analysis["reasons"].append("baseline_guidance_gap_measured_pass")
    return analysis


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


def first_numeric(*values: Any) -> int | float | None:
    for value in values:
        parsed = numeric(value)
        if parsed is not None:
            return parsed
    return None


def first_int(default: int, *values: Any) -> int:
    parsed = first_numeric(*values)
    return int(parsed) if parsed is not None else default


def first_bool(*values: Any) -> bool:
    for value in values:
        if value is None or value == "":
            continue
        return parse_bool(value)
    return False


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


def split_list(value: str) -> list[str]:
    return [part for part in value.replace(",", " ").split() if part]


def formtrig_gate_csv(path: Path) -> Path:
    if path.is_dir():
        candidate = path / "gate_summary.csv"
        if candidate.exists():
            return candidate
    return path


def read_json_if_exists(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = read_json(path)
    return data if isinstance(data, dict) else {}


def manifest_duration_s(path_text: Any) -> int | None:
    path_value = str_value(path_text)
    if not path_value:
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    match = re.search(r"(?:^|[._-])(\d+)s(?:[._-]|$)", path.name)
    if match:
        return int(match.group(1))
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        if key.strip() in {"duration", "duration_s", "budget", "budget_s"}:
            parsed = numeric(value.strip())
            if parsed is not None:
                return int(parsed)
    return None


def label_duration_s(label: str) -> int | None:
    match = re.search(r"(?:^|[._-])(\d+)s(?:[._-]|$)", label)
    return int(match.group(1)) if match else None


def strict_pretrigger(row: dict[str, Any]) -> bool:
    accepted_non_trigger = first_int(
        0,
        row.get("accepted_non_trigger"),
        row.get("accepted_non_trigger_progress"),
        row.get("accepted_non_trigger_progress_events"),
        row.get("non_trigger_progress"),
        row.get("non_trigger_progress_events"),
    )
    saved_non_trigger = first_int(
        0,
        row.get("saved_non_trigger"),
        row.get("saved_non_trigger_progress"),
        row.get("saved_non_trigger_progress_events"),
    )
    return (
        parse_bool(row.get("experiment_ready"))
        and parse_bool(row.get("pretrigger_lift_guidance_ready"))
        and accepted_non_trigger > 0
        and saved_non_trigger > 0
        and not first_bool(
            row.get("lift_delta_only_on_triggered"),
            row.get("lift_delta_only_on_triggered_candidates"),
        )
        and int_value(row.get("spec_lifted")) > 0
        and int_value(row.get("heuristic_lifted")) == 0
        and int_value(row.get("manual_lifted")) == 0
        and str(row.get("binding_signal_status", "")).strip() == "pass"
    )


def resolve_formtrig_default_dir(out_dir: Path) -> Path:
    if (out_dir / "formtrig_progress.jsonl").exists():
        return out_dir
    return out_dir / "default"


def first_formtrig_trigger(default_dir: Path) -> dict[str, Any]:
    progress_path = default_dir / "formtrig_progress.jsonl"
    queue_dir = default_dir / "queue"
    if not progress_path.exists():
        return {}

    for line in progress_path.read_text(encoding="utf-8").splitlines():
        if "triggered" not in line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("reason") != "triggered" and not parse_bool(event.get("triggered")):
            continue
        queue_id = event.get("queue_id")
        queue_path = None
        queue_time_s = None
        queue_execs = None
        if queue_id is not None and queue_dir.is_dir():
            prefix = f"id:{int(queue_id):06d},"
            for candidate in queue_dir.iterdir():
                if candidate.name.startswith(prefix):
                    queue_path = candidate
                    time_match = re.search(r"(?:^|,)time:(\d+)(?:,|$)", candidate.name)
                    exec_match = re.search(r"(?:^|,)execs:(\d+)(?:,|$)", candidate.name)
                    if time_match:
                        queue_time_s = int(time_match.group(1)) / 1000.0
                    if exec_match:
                        queue_execs = int(exec_match.group(1))
                    break
        return {
            "first_formtrig_trigger_event": event,
            "first_formtrig_trigger_queue_id": queue_id,
            "first_formtrig_trigger_queue_path": str(queue_path) if queue_path else None,
            "first_formtrig_trigger_time_s": queue_time_s,
            "first_formtrig_trigger_execs": queue_execs or event.get("execs_done"),
            "first_formtrig_trigger_kind": (
                "formtrig_progress_queue_filename_exact"
                if queue_time_s is not None
                else "formtrig_progress_exec_exact"
            ),
        }
    return {}


def load_formtrig_rows(items: list[str], target_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        label, raw_path = parse_labeled_path(item)
        path = formtrig_gate_csv(raw_path)
        if not path.exists():
            raise SystemExit(f"FORMTRIG gate summary does not exist: {path}")
        with path.open(newline="", encoding="utf-8") as handle:
            for raw in csv.DictReader(handle):
                out_dir = str_value(raw.get("out_dir"))
                default_dir = Path(out_dir) / "default" if out_dir else None
                summary = (
                    read_json_if_exists(default_dir / "formtrig_summary.json")
                    if default_dir is not None
                    else {}
                )
                diagnosis = (
                    read_json_if_exists(default_dir / "formtrig_diagnosis.json")
                    if default_dir is not None
                    else {}
                )
                binding_signal = (
                    read_json_if_exists(default_dir / "formtrig_binding_signal_diagnosis.json")
                    if default_dir is not None
                    else {}
                )
                budget = first_numeric(
                    raw.get("budget"),
                    raw.get("budget_s"),
                    raw.get("duration"),
                    raw.get("duration_s"),
                    raw.get("run_time"),
                    summary.get("budget"),
                    summary.get("duration"),
                    summary.get("run_time"),
                    manifest_duration_s(raw.get("manifest")),
                    label_duration_s(label),
                )
                accepted_non_trigger = first_int(
                    0,
                    raw.get("accepted_non_trigger"),
                    raw.get("accepted_non_trigger_progress"),
                    raw.get("accepted_non_trigger_progress_events"),
                    raw.get("non_trigger_progress"),
                    raw.get("non_trigger_progress_events"),
                    binding_signal.get("accepted_non_trigger_progress_events"),
                    diagnosis.get("non_trigger_progress_events"),
                    summary.get("non_trigger_progress_events"),
                )
                saved_non_trigger = first_int(
                    0,
                    raw.get("saved_non_trigger"),
                    raw.get("saved_non_trigger_progress"),
                    raw.get("saved_non_trigger_progress_events"),
                    diagnosis.get("saved_non_trigger_progress_events"),
                    summary.get("saved_non_trigger_progress_events"),
                )
                terminal_count = first_int(
                    0,
                    raw.get("terminal_triggered"),
                    raw.get("triggered"),
                    diagnosis.get("terminal_triggered_execs"),
                    summary.get("terminal_triggered_execs"),
                    summary.get("formtrig_triggered_execs"),
                )
                normalized = {
                    **raw,
                    "accepted_non_trigger": accepted_non_trigger,
                    "saved_non_trigger": saved_non_trigger,
                    "experiment_ready": raw.get("experiment_ready")
                    or diagnosis.get("experiment_ready"),
                    "pretrigger_lift_guidance_ready": raw.get(
                        "pretrigger_lift_guidance_ready"
                    )
                    or diagnosis.get("pretrigger_lift_guidance_ready"),
                    "lift_delta_only_on_triggered": raw.get(
                        "lift_delta_only_on_triggered"
                    )
                    or diagnosis.get("lift_delta_only_on_triggered_candidates")
                    or binding_signal.get("lift_delta_only_on_triggered_candidates"),
                    "spec_lifted": raw.get("spec_lifted")
                    or diagnosis.get("spec_lifted_events")
                    or summary.get("spec_lifted_events"),
                    "heuristic_lifted": raw.get("heuristic_lifted")
                    or diagnosis.get("heuristic_lifted_events")
                    or summary.get("heuristic_lifted_events"),
                    "manual_lifted": raw.get("manual_lifted")
                    or diagnosis.get("manual_lifted_events")
                    or summary.get("manual_lifted_events"),
                    "binding_signal_status": raw.get("binding_signal_status")
                    or diagnosis.get("binding_signal_status")
                    or binding_signal.get("status"),
                }
                row = {
                    "arm": "formtrig",
                    "source_label": label,
                    "target_id": target_id,
                    "budget": int(budget) if budget is not None else None,
                    "run_time": int_value(
                        raw.get("run_time"),
                        int(budget) if budget is not None else 0,
                    ),
                    "rep": None,
                    "success": terminal_count > 0,
                    "terminal_count": terminal_count,
                    "trigger_time_s": numeric(raw.get("first_terminal_time_s")),
                    "trigger_time_kind": str_value(raw.get("first_terminal_time_kind")),
                    "trigger_execs": numeric(raw.get("first_terminal_execs"))
                    or numeric(raw.get("first_trigger_execs")),
                    "execs_done": first_int(0, raw.get("execs_done"), summary.get("execs_done")),
                    "execs_per_sec": str_value(raw.get("execs_per_sec")),
                    "reached": first_int(
                        0,
                        raw.get("reached"),
                        summary.get("formtrig_reached_execs"),
                        diagnosis.get("formtrig_reached_execs"),
                    ),
                    "accepted_non_trigger": accepted_non_trigger,
                    "saved_non_trigger": saved_non_trigger,
                    "spec_lifted": int_value(normalized.get("spec_lifted")),
                    "heuristic_lifted": int_value(normalized.get("heuristic_lifted")),
                    "manual_lifted": int_value(normalized.get("manual_lifted")),
                    "strict_pretrigger_guidance": strict_pretrigger(normalized),
                    "binding_signal_status": str_value(normalized.get("binding_signal_status")),
                    "binding_signal_diagnosis": str_value(
                        raw.get("binding_signal_diagnosis")
                        or diagnosis.get("binding_signal_diagnosis")
                        or binding_signal.get("diagnosis")
                    ),
                    "gate_status": str_value(raw.get("status")),
                    "gate_reasons": str_value(raw.get("reasons")),
                    "source_path": str(path),
                    "out_dir": out_dir,
                }
                if out_dir:
                    exact = first_formtrig_trigger(resolve_formtrig_default_dir(Path(out_dir)))
                    if exact:
                        row.update(exact)
                        if numeric(exact.get("first_formtrig_trigger_time_s")) is not None:
                            row["trigger_time_s"] = exact["first_formtrig_trigger_time_s"]
                            row["trigger_time_kind"] = exact["first_formtrig_trigger_kind"]
                        if numeric(exact.get("first_formtrig_trigger_execs")) is not None:
                            row["trigger_execs"] = exact["first_formtrig_trigger_execs"]
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
            if raw.get("valid_run") is False:
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
                "trigger_execs": raw.get("trigger_execs"),
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
        trigger_execs = [
            float(value)
            for row in successes
            if (value := numeric(row.get("trigger_execs"))) is not None
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
                "min_trigger_time_s": min(trigger_times) if trigger_times else None,
                "median_trigger_time_s": median(trigger_times),
                "median_trigger_execs": median(trigger_execs),
                "median_terminal_count": median(terminal_counts),
            }
        )
    return summaries


def successful_baseline_family_median_ttes(groups: list[dict[str, Any]]) -> list[float]:
    return [
        float(value)
        for group in groups
        if float(group.get("success_rate") or 0.0) > 0.0
        if (value := numeric(group.get("median_trigger_time_s"))) is not None
    ]


def main_claim_strength(
    groups: list[dict[str, Any]],
    successful_baselines: list[dict[str, Any]],
    terminal_without_successful_baseline: bool,
    speedup_observed: bool,
    required_baselines: list[str],
    min_reps: int,
    best_baseline_tte: float | int | None,
    best_baseline_family_median_tte: float | int | None,
) -> dict[str, Any]:
    """Separate performance benefit from main-claim experiment hardness.

    A speedup can be real while the experiment is too close to the trigger to
    prove that binary TC feedback remains a hard SOTA problem. This gate keeps
    those facts separate so weak harness/near-seed cases drive stronger
    experimental design instead of being silently promoted as hard evidence.
    """

    reasons: list[str] = []
    next_steps: list[str] = []

    complete_groups = [
        group for group in groups if int_value(group.get("reps")) >= min_reps
    ]
    required_group_names = set(required_baselines)
    if required_group_names:
        hardness_groups = [
            group for group in complete_groups if group.get("baseline") in required_group_names
        ]
    else:
        hardness_groups = complete_groups

    all_required_successful = bool(hardness_groups) and all(
        float(group.get("success_rate") or 0.0) >= 1.0 for group in hardness_groups
    )

    if terminal_without_successful_baseline:
        strength = "hard_endpoint_gap_candidate"
        reasons.append("matched_baselines_do_not_trigger")
        next_steps.append(
            "promote to replicated long-run or cross-target confirmation if harness fidelity passes"
        )
    elif speedup_observed:
        baseline_cost_gate_applied = False
        if (
            best_baseline_tte is not None
            and float(best_baseline_tte) <= ACCEPTABLE_BASELINE_FASTEST_TTE_S
        ):
            strength = "not_hard_pain_baseline_fast_enough"
            baseline_cost_gate_applied = True
            reasons.append("baseline_fastest_trigger_time_is_under_acceptable_threshold")
            next_steps.extend(
                [
                    "treat as speedup/control evidence, not hard SOTA-pain evidence",
                    "move main budget to targets where no faithful baseline triggers within the acceptable-time threshold",
                    "if retained, report only FORMTRIG TTE speedup and mechanism attribution",
                ]
            )
        elif (
            best_baseline_tte is not None
            and float(best_baseline_tte) <= HARD_BASELINE_FASTEST_TTE_S
        ):
            strength = "moderate_speedup_needs_unacceptable_baseline_cost"
            baseline_cost_gate_applied = True
            reasons.append("baseline_fastest_trigger_time_is_under_hard_pain_threshold")
            next_steps.extend(
                [
                    "do not use as hard SOTA-pain evidence unless a stricter harness or farther seeds push faithful baselines beyond the hard-pain threshold",
                    "keep as secondary speedup evidence",
                ]
            )
        if all_required_successful:
            if not baseline_cost_gate_applied:
                reasons.append("all_required_baseline_families_trigger_in_replicated_runs")
                if (
                    best_baseline_family_median_tte is not None
                    and float(best_baseline_family_median_tte)
                    <= EARLY_BASELINE_FAMILY_MEDIAN_TTE_S
                ):
                    strength = "weak_near_seed_or_harness_shaped_speedup"
                    reasons.append("baseline_family_median_trigger_time_is_under_60s")
                    next_steps.extend(
                        [
                            "do not spend main hard-evidence budget on this harness shape alone",
                            "rerun with a higher-fidelity/raw-format harness or a farther RNT seed",
                            "add no-hook and generic-hook FORMTRIG ablations to measure target-specific hook contribution",
                            "prioritize targets where at least one strong baseline family has low success rate or long median R2T",
                        ]
                    )
                elif (
                    best_baseline_family_median_tte is not None
                    and float(best_baseline_family_median_tte)
                    <= MODERATE_BASELINE_FAMILY_MEDIAN_TTE_S
                ):
                    strength = "moderate_speedup_needs_harder_design"
                    reasons.append("baseline_family_median_trigger_time_is_under_300s")
                    next_steps.extend(
                        [
                            "keep as secondary speedup evidence",
                            "add ablations and a harder target/harness before using as main SOTA-gap evidence",
                        ]
                    )
                else:
                    strength = "hard_speedup_variance_candidate"
                    reasons.append("baseline_successful_but_not_early_across_families")
                    next_steps.append(
                        "use as candidate hard speedup evidence after harness fidelity and ablation checks"
                    )
        else:
            if not baseline_cost_gate_applied:
                strength = "hard_speedup_or_reliability_candidate"
                reasons.append("some_required_baseline_families_fail_or_are_unstable")
                next_steps.append(
                    "quantify success-rate and TTE-tail improvement with additional repetitions"
                )
    else:
        strength = "not_supporting_main_claim"
        reasons.append("no_endpoint_or_speedup_advantage_for_formtrig")
        next_steps.append("repair BindingSpec/mutation design or move budget to a harder target")

    return {
        "best_baseline_family_median_trigger_time_s": best_baseline_family_median_tte,
        "acceptable_baseline_fastest_trigger_threshold_s": ACCEPTABLE_BASELINE_FASTEST_TTE_S,
        "hard_baseline_fastest_trigger_threshold_s": HARD_BASELINE_FASTEST_TTE_S,
        "early_baseline_family_median_threshold_s": EARLY_BASELINE_FAMILY_MEDIAN_TTE_S,
        "main_claim_strength": strength,
        "baseline_guidance_gap": baseline_guidance_gap_requirement(strength),
        "reasons": reasons,
        "recommended_design_actions": next_steps,
    }


def classify_evidence(
    formtrig_rows: list[dict[str, Any]],
    baseline_rows: list[dict[str, Any]],
    tolerance: int,
    min_reps: int,
    required_baselines: list[str],
) -> dict[str, Any]:
    reasons: list[str] = []
    matched_baselines = [
        baseline
        for baseline in baseline_rows
        if any(budget_matches(baseline.get("budget"), formtrig.get("budget"), tolerance) for formtrig in formtrig_rows)
    ]
    if not matched_baselines:
        reasons.append("missing_matched_budget_baselines")

    matched_baseline_names = {
        str(row.get("baseline"))
        for row in matched_baselines
        if row.get("baseline") is not None
    }
    missing_required = [
        baseline
        for baseline in required_baselines
        if baseline not in matched_baseline_names
    ]
    if missing_required:
        reasons.append("missing_required_baselines")

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
    formtrig_successes = [
        row for row in formtrig_rows if int_value(row.get("terminal_count")) > 0
    ]
    formtrig_ttes = numeric_values(formtrig_successes, "trigger_time_s")
    best_formtrig_tte = min(formtrig_ttes) if formtrig_ttes else None
    successful_baseline_rows = [row for row in matched_baselines if row.get("success")]
    baseline_run_ttes = numeric_values(successful_baseline_rows, "trigger_time_s")
    best_baseline_tte = min(baseline_run_ttes) if baseline_run_ttes else None
    baseline_family_median_ttes = successful_baseline_family_median_ttes(groups)
    best_baseline_family_median_tte = (
        min(baseline_family_median_ttes) if baseline_family_median_ttes else None
    )
    tte_speedup = (
        best_baseline_tte / best_formtrig_tte
        if best_formtrig_tte and best_baseline_tte and best_formtrig_tte > 0
        else None
    )
    family_median_tte_speedup = (
        best_baseline_family_median_tte / best_formtrig_tte
        if best_formtrig_tte
        and best_baseline_family_median_tte
        and best_formtrig_tte > 0
        else None
    )
    low_rep_groups = [group for group in groups if int_value(group.get("reps")) < min_reps]
    if low_rep_groups:
        reasons.append("low_replication")

    successful_baselines = [group for group in groups if float(group.get("success_rate") or 0.0) > 0.0]
    terminal_without_successful_baseline = terminal_formtrig and matched_baselines and not successful_baselines
    if terminal_without_successful_baseline:
        reasons.append("formtrig_endpoint_where_matched_baselines_do_not_trigger")
    if successful_baselines:
        reasons.append("matched_baseline_also_triggers")
        if best_formtrig_tte is not None and best_baseline_tte is not None:
            if best_formtrig_tte < best_baseline_tte:
                reasons.append("formtrig_faster_than_successful_baselines")
            else:
                reasons.append("matched_successful_baseline_no_later_than_formtrig")

    if not matched_baselines:
        verdict = "not_comparable_missing_matched_budget"
    elif missing_required:
        verdict = "incomplete_required_baseline_set"
    elif successful_baselines and "formtrig_faster_than_successful_baselines" in reasons and not low_rep_groups:
        verdict = "positive_speedup_matched_comparison"
    elif successful_baselines and "formtrig_faster_than_successful_baselines" in reasons:
        verdict = "speedup_but_under_replicated"
    elif successful_baselines:
        verdict = "baseline_also_triggers_not_sota_advantage"
    elif terminal_without_successful_baseline and not low_rep_groups:
        verdict = "positive_endpoint_matched_comparison"
    elif terminal_without_successful_baseline:
        verdict = "positive_endpoint_but_under_replicated"
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
    if missing_required:
        next_steps.append("run missing required baselines: " + ",".join(missing_required))
    if successful_baselines:
        if "formtrig_faster_than_successful_baselines" in reasons:
            next_steps.append("treat this as a speedup claim and complete repetitions/longer runs before final performance claims")
        else:
            next_steps.append("do not claim SOTA advantage on this target without harder targets or stronger statistics")
    if strict_formtrig and not terminal_formtrig:
        next_steps.append("pair pre-trigger guidance with a same-oracle terminal run before terminal TTE claims")

    strength = main_claim_strength(
        groups=groups,
        successful_baselines=successful_baselines,
        terminal_without_successful_baseline=terminal_without_successful_baseline,
        speedup_observed="formtrig_faster_than_successful_baselines" in reasons,
        required_baselines=required_baselines,
        min_reps=min_reps,
        best_baseline_tte=best_baseline_tte,
        best_baseline_family_median_tte=best_baseline_family_median_tte,
    )
    if (missing_required or low_rep_groups) and strength["main_claim_strength"] in HARD_SOTA_STRENGTHS:
        incomplete_reasons = list(strength["reasons"])
        incomplete_actions = list(strength["recommended_design_actions"])
        if missing_required:
            incomplete_reasons.append("required_baseline_families_missing")
            incomplete_actions.append(
                "complete the required faithful baseline set before hard SOTA-pain claims"
            )
        if low_rep_groups:
            incomplete_reasons.append("matched_baseline_replication_incomplete")
            incomplete_actions.append(
                "complete the requested repetitions before hard SOTA-pain claims"
            )
        strength = {
            **strength,
            "main_claim_strength": "incomplete_matched_evidence",
            "baseline_guidance_gap": baseline_guidance_gap_requirement(
                "incomplete_matched_evidence"
            ),
            "reasons": incomplete_reasons,
            "recommended_design_actions": incomplete_actions,
        }
    if strength["main_claim_strength"] in {
        "not_hard_pain_baseline_fast_enough",
        "moderate_speedup_needs_unacceptable_baseline_cost",
    }:
        next_steps = [
            step
            for step in next_steps
            if step
            != "treat this as a speedup claim and complete repetitions/longer runs before final performance claims"
        ]
    if strength["main_claim_strength"] in {
        "not_hard_pain_baseline_fast_enough",
        "moderate_speedup_needs_unacceptable_baseline_cost",
        "weak_near_seed_or_harness_shaped_speedup",
        "moderate_speedup_needs_harder_design",
    }:
        reasons.append(strength["main_claim_strength"])
        next_steps.extend(strength["recommended_design_actions"])

    return {
        "baseline_groups": groups,
        "experiment_strength": strength,
        "matched_baseline_count": len(matched_baselines),
        "missing_required_baselines": missing_required,
        "next_steps": next_steps,
        "reasons": reasons,
        "best_formtrig_trigger_time_s": best_formtrig_tte,
        "fastest_baseline_trigger_time_s": best_baseline_tte,
        "fastest_baseline_family_median_trigger_time_s": best_baseline_family_median_tte,
        "tte_speedup_over_fastest_baseline": tte_speedup,
        "tte_speedup_over_fastest_baseline_family_median": family_median_tte_speedup,
        "verdict": verdict,
    }


def numeric_values(rows: list[dict[str, Any]], field: str) -> list[float]:
    values = []
    for row in rows:
        value = numeric(row.get(field))
        if value is not None:
            values.append(float(value))
    return values


def benefit_readout(
    formtrig_rows: list[dict[str, Any]],
    analysis: dict[str, Any],
) -> dict[str, Any]:
    strict_formtrig = any(row.get("strict_pretrigger_guidance") for row in formtrig_rows)
    terminal_formtrig = any(int_value(row.get("terminal_count")) > 0 for row in formtrig_rows)
    formtrig_ttes = numeric_values(formtrig_rows, "trigger_time_s")
    baseline_groups = analysis.get("baseline_groups", [])
    successful_baseline_groups = [
        group
        for group in baseline_groups
        if float(group.get("success_rate") or 0.0) > 0.0
    ]
    fastest_baseline_tte = numeric(analysis.get("fastest_baseline_trigger_time_s"))
    fastest_family_median_tte = numeric(
        analysis.get("fastest_baseline_family_median_trigger_time_s")
    )

    primary_benefits: list[str] = []
    endpoint_observations: list[str] = []
    mechanism_benefits: list[str] = []
    blocked_claims: list[str] = []
    design_evidence: list[str] = []

    if strict_formtrig:
        mechanism_benefits.append(
            "binary or sparse trigger feedback was lifted into accepted non-trigger search progress"
        )
        design_evidence.append("strict_pretrigger_guidance")
    else:
        blocked_claims.append("no strict pre-trigger guidance benefit is established")

    if terminal_formtrig:
        endpoint_observations.append("FORMTRIG terminal oracle success is observed")
        design_evidence.append("formtrig_terminal_oracle_success")
    else:
        blocked_claims.append("no FORMTRIG terminal success is established")

    if formtrig_ttes:
        endpoint_observations.append(
            f"FORMTRIG first `_T` upper bound is recorded at {min(formtrig_ttes):g}s"
        )
    else:
        blocked_claims.append("FORMTRIG first `_T`/TTE is not recorded for this run")

    if not baseline_groups:
        blocked_claims.append("no matched-budget baseline benefit comparison is available")
    elif successful_baseline_groups:
        if formtrig_ttes and fastest_baseline_tte is not None:
            if min(formtrig_ttes) < fastest_baseline_tte:
                speedup = (
                    fastest_baseline_tte / min(formtrig_ttes)
                    if min(formtrig_ttes) > 0
                    else None
                )
                primary_benefits.append(
                    "FORMTRIG has a lower observed first-`_T` upper bound than every matched successful baseline run"
                )
                if speedup is not None:
                    primary_benefits.append(
                        f"FORMTRIG observed first-`_T` is {speedup:.2f}x faster than the fastest matched successful baseline run"
                    )
                endpoint_observations.append(
                    f"fastest matched successful baseline-run first `_T` upper bound is {fastest_baseline_tte:g}s"
                )
                if fastest_family_median_tte is not None:
                    endpoint_observations.append(
                        "fastest matched successful baseline-family median first `_T` "
                        f"upper bound is {fastest_family_median_tte:g}s"
                    )
            else:
                blocked_claims.append(
                    "matched successful baseline first-`_T` is no later than FORMTRIG on current evidence"
                )
        else:
            blocked_claims.append(
                "matched baselines also trigger, so terminal success alone is not a FORMTRIG advantage"
            )
    elif terminal_formtrig:
        primary_benefits.append(
            "FORMTRIG reaches terminal success where matched baselines do not trigger in this budget"
        )
        design_evidence.append("matched_budget_endpoint_success")

    if analysis.get("missing_required_baselines"):
        blocked_claims.append("required baseline families are still missing")
    if "low_replication" in analysis.get("reasons", []):
        blocked_claims.append("replication is too low for a final performance claim")
    strength = analysis.get("experiment_strength")
    if isinstance(strength, dict):
        main_strength = strength.get("main_claim_strength")
        gap = strength.get("baseline_guidance_gap")
        if (
            isinstance(gap, dict)
            and gap.get("required_for_hard_sota_pain")
            and gap.get("status") != "measured_pass"
        ):
            blocked_claims.append(
                "baseline no-guidance proof is not measured: hard SOTA-pain claims require flat/binary pre-_T baseline TC signal and late, missing, or high-variance baseline _T"
            )
            design_evidence.append("baseline_guidance_gap_required")
        elif (
            isinstance(gap, dict)
            and gap.get("required_for_hard_sota_pain")
            and gap.get("status") == "measured_pass"
        ):
            design_evidence.append("baseline_guidance_gap_measured")
        if main_strength == "not_hard_pain_baseline_fast_enough":
            blocked_claims.append(
                "a matched faithful baseline reaches the trigger within the acceptable-time threshold, so this is not hard SOTA-pain evidence"
            )
            design_evidence.append("experiment_strength_gate")
        elif main_strength == "moderate_speedup_needs_unacceptable_baseline_cost":
            blocked_claims.append(
                "matched faithful baseline time is not yet high enough to show unacceptable SOTA R2T cost"
            )
            design_evidence.append("experiment_strength_gate")
        elif main_strength == "weak_near_seed_or_harness_shaped_speedup":
            blocked_claims.append(
                "current experiment is too near-trigger or harness-shaped to serve as main SOTA-gap evidence"
            )
            design_evidence.append("experiment_strength_gate")
        elif main_strength == "moderate_speedup_needs_harder_design":
            blocked_claims.append(
                "current experiment needs harder harness/target design or ablations before main-claim use"
            )
            design_evidence.append("experiment_strength_gate")

    observed_benefits = primary_benefits + endpoint_observations + mechanism_benefits

    low_replication = "low_replication" in analysis.get("reasons", [])
    if primary_benefits:
        if low_replication and successful_baseline_groups:
            summary = "current package supports a matched-budget speedup benefit, subject to replication"
        elif low_replication:
            summary = "current package supports a matched-budget primary benefit, subject to replication"
        elif successful_baseline_groups:
            summary = "current package supports a matched-budget speedup benefit"
        else:
            summary = "current package supports a matched-budget primary endpoint benefit"
    elif not observed_benefits:
        summary = "no benefit claim is supported by the current package"
    elif any("no later than FORMTRIG" in claim or "also trigger" in claim for claim in blocked_claims):
        summary = "mechanism benefit is present, but performance advantage is not established on this target"
    elif endpoint_observations and not baseline_groups:
        summary = "FORMTRIG endpoint success is observed, but matched-budget benefit is not comparable yet"
    else:
        summary = "current package supports mechanism/search-guidance benefit, subject to remaining blockers"

    return {
        "blocked_claims": blocked_claims,
        "design_evidence": design_evidence,
        "endpoint_observations": endpoint_observations,
        "mechanism_benefits": mechanism_benefits,
        "observed_benefits": observed_benefits,
        "primary_benefits": primary_benefits,
        "summary": summary,
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
        "- main claim strength: "
        f"`{payload['analysis'].get('experiment_strength', {}).get('main_claim_strength', 'unknown')}`",
        f"- matched baselines: `{payload['analysis']['matched_baseline_count']}`",
        "",
        "## Benefit Readout",
        "",
        f"- summary: {payload['benefit_readout']['summary']}",
        "",
        "Primary benefit statements:",
    ]
    for benefit in payload["benefit_readout"].get("primary_benefits", []):
        lines.append(f"- {benefit}")
    if not payload["benefit_readout"].get("primary_benefits", []):
        lines.append("- none")
    lines.extend(["", "Endpoint observations:"])
    for observation in payload["benefit_readout"].get("endpoint_observations", []):
        lines.append(f"- {observation}")
    if not payload["benefit_readout"].get("endpoint_observations", []):
        lines.append("- none")
    lines.extend(["", "Mechanism benefits:"])
    for benefit in payload["benefit_readout"].get("mechanism_benefits", []):
        lines.append(f"- {benefit}")
    if not payload["benefit_readout"].get("mechanism_benefits", []):
        lines.append("- none")
    lines.extend(["", "Blocked or not-yet-supported statements:"])
    for claim in payload["benefit_readout"]["blocked_claims"]:
        lines.append(f"- {claim}")
    if not payload["benefit_readout"]["blocked_claims"]:
        lines.append("- none")
    lines.extend(
        [
            "",
            "Design evidence used for attribution:",
        ]
    )
    for evidence in payload["benefit_readout"]["design_evidence"]:
        lines.append(f"- `{evidence}`")
    if not payload["benefit_readout"]["design_evidence"]:
        lines.append("- none")

    strength = payload["analysis"].get("experiment_strength", {})
    lines.extend(
        [
            "",
            "## Experiment Strength",
            "",
            f"- main claim strength: `{strength.get('main_claim_strength', 'unknown')}`",
            "- reasons:",
        ]
    )
    for reason in strength.get("reasons", []):
        lines.append(f"  - `{reason}`")
    if not strength.get("reasons"):
        lines.append("  - none")
    lines.append("- required design actions:")
    for action in strength.get("recommended_design_actions", []):
        lines.append(f"  - {action}")
    if not strength.get("recommended_design_actions"):
        lines.append("  - none")
    gap = strength.get("baseline_guidance_gap") if isinstance(strength, dict) else {}
    if isinstance(gap, dict):
        lines.extend(
            [
                "- baseline no-guidance proof:",
                f"  - required for hard SOTA-pain: `{cell(gap.get('required_for_hard_sota_pain'))}`",
                f"  - status: `{cell(gap.get('status'))}`",
            ]
        )
        for item in gap.get("required_evidence", []):
            lines.append(f"  - required evidence: {item}")
        if gap.get("source_path"):
            lines.append(f"  - source: `{gap.get('source_path')}`")
        if gap.get("interpretation"):
            lines.append(f"  - interpretation: {gap.get('interpretation')}")
    lines.extend(
        [
            "",
            "## FORMTRIG Runs",
            "",
            "| label | budget | terminal | strict pre-trigger | execs | reached | spec lifted |",
            "| --- | ---: | ---: | --- | ---: | ---: | ---: |",
        ]
    )
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
            "| baseline | budget | reps | success rate | median trigger time | median trigger execs | median terminal count |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for group in payload["analysis"]["baseline_groups"]:
        lines.append(
            "| {baseline} | {budget} | {reps} | {success_rate:.3f} | {median_trigger_time_s} | "
            "{median_trigger_execs} | "
            "{median_terminal_count} |".format(
                baseline=cell(group.get("baseline")),
                budget=cell(group.get("budget")),
                reps=int_value(group.get("reps")),
                success_rate=float(group.get("success_rate") or 0.0),
                median_trigger_time_s=cell(group.get("median_trigger_time_s")),
                median_trigger_execs=cell(group.get("median_trigger_execs")),
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
    parser.add_argument(
        "--baseline-guidance-gap",
        help="path/to/baseline_guidance_gap.json or a directory containing it",
    )
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--budget-tolerance-sec", type=int, default=5)
    parser.add_argument("--min-reps", type=int, default=3)
    parser.add_argument(
        "--required-baselines",
        default="",
        help="comma/space-separated baseline ids required for a complete comparison",
    )
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
        split_list(args.required_baselines),
    )
    if args.baseline_guidance_gap:
        gap_path = baseline_guidance_gap_json(Path(args.baseline_guidance_gap))
        if not gap_path.exists():
            raise SystemExit(f"baseline guidance-gap JSON does not exist: {gap_path}")
        apply_baseline_guidance_gap(
            analysis,
            read_json(gap_path),
            gap_path,
            target_id=args.target_id,
        )
    payload = {
        "analysis": analysis,
        "baseline_rows": baseline_rows,
        "benefit_readout": benefit_readout(formtrig_rows, analysis),
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
