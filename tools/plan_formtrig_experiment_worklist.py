#!/usr/bin/env python3
"""Generate a benefit-first FORMTRIG experiment worklist.

The hard-target queue ranks opportunities. This tool turns that queue into a
run-oriented worklist: what endpoint benefit each target must prove, which
mechanism evidence is required only for attribution, and which blockers prevent
spending long-run fuzzing budget.
"""

from __future__ import annotations

import argparse
import csv
import json
import shlex
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TASK_FIELDS = [
    "priority",
    "rank",
    "target_id",
    "source",
    "project",
    "lane",
    "sota_pain_class",
    "sota_pain_evidence",
    "action",
    "duration_s",
    "repetitions",
    "runnable_now",
    "benefit_to_prove",
    "primary_endpoint_metrics",
    "mechanism_evidence_required",
    "blocking_issue",
    "claim_boundary",
    "command",
    "post_unblock_commands",
    "evidence_paths",
    "active_run_status",
    "active_run_root",
]

DEMOTE_DISPOSITIONS = {
    "demote_to_control_or_negative",
    "demote_harness_artifact",
}

DEMOTED_CONTROL_LANES = {
    "control_or_negative",
}

NON_MAIN_BUDGET_LANES = {
    "control_or_negative",
    "control_or_low_priority",
    "real_cve_control_or_audit",
}

CONTROL_STATUSES = {
    "do_not_promote",
}

LONGRUN_PROMOTION_VERDICTS = {
    "positive_endpoint_matched_comparison",
    "positive_speedup_matched_comparison",
}

COMPLETE_REPS_VERDICTS = {
    "positive_endpoint_but_under_replicated",
    "positive_but_under_replicated",
    "speedup_but_under_replicated",
}

WEAK_MAIN_CLAIM_STRENGTHS = {
    "weak_near_seed_or_harness_shaped_speedup",
    "moderate_speedup_needs_harder_design",
}

SOTA_PAIN_SKIP_CLASSES = {
    "not_visible_baseline_time_cost_acceptable",
    "not_visible_baseline_visible_no_formtrig_advantage",
}

SOTA_PAIN_DESIGN_CLASSES = {
    "not_visible_near_seed_or_harness_shaped",
    "weak_or_moderate_baseline_time_cost",
    "weak_or_moderate_needs_harder_design",
}

BASELINE_FAMILY = "aflplusplus_vanilla,aflplusplus_cmplog,redqueen_operand"
DEFAULT_NATIVE_BUILD_ROOT = Path("artifacts/formtrig_native_readiness/magma_native_builds")
DEFAULT_BINDING_VALIDATION_ROOT = Path("artifacts/formtrig_native_readiness/binding_validation")
DEFAULT_MANIFEST_ROOT = Path("artifacts/formtrig_native_readiness/manifests")


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def queue_rows(payload: dict[str, Any], use_all_targets: bool = False) -> list[dict[str, Any]]:
    key = "all_targets" if use_all_targets else "top_targets"
    rows = payload.get(key)
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]
    fallback_key = "top_targets" if use_all_targets else "all_targets"
    rows = payload.get(fallback_key)
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]
    raise ValueError("queue JSON must contain top_targets or all_targets")


def comparison_paths(root: Path) -> list[Path]:
    if root.is_file() and root.name == "comparison.json":
        return [root]
    if not root.exists():
        return []
    return sorted(root.glob("*/comparison.json"))


def comparison_map(root: Path) -> dict[str, list[dict[str, Any]]]:
    by_target: dict[str, list[dict[str, Any]]] = {}
    for path in comparison_paths(root):
        try:
            payload = read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        target_id = str(payload.get("target_id") or "")
        if not target_id:
            continue
        payload["_comparison_path"] = str(path)
        by_target.setdefault(target_id, []).append(payload)
    return by_target


def triage_map(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    try:
        payload = read_json(path)
    except (OSError, json.JSONDecodeError):
        return {}
    rows = payload.get("targets")
    if not isinstance(rows, list):
        return {}
    return {
        str(row.get("target_id")): row
        for row in rows
        if isinstance(row, dict) and row.get("target_id")
    }


def active_run_rows(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    try:
        payload = read_json(path)
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    rows = payload.get("runs") if isinstance(payload, dict) else None
    if isinstance(rows, list):
        return [row for row in rows if isinstance(row, dict)]
    return []


def active_run_score(row: dict[str, Any]) -> tuple[int, str, str]:
    status = str(row.get("status") or "")
    status_score = {
        "running": 3,
        "in_progress": 3,
        "collecting": 2,
        "complete": 1,
    }.get(status, 0)
    return (
        status_score,
        str(row.get("launched_at_utc") or row.get("generated_at_utc") or ""),
        str(row.get("run_root") or ""),
    )


def active_run_map(path: Path | None) -> dict[str, dict[str, Any]]:
    active: dict[str, dict[str, Any]] = {}
    for row in active_run_rows(path):
        target_id = str(row.get("target_id") or "")
        if not target_id:
            continue
        current = active.get(target_id)
        if current is None or active_run_score(row) >= active_run_score(current):
            active[target_id] = row
    return active


def matching_active_run(
    active_runs: dict[str, dict[str, Any]],
    target_id: str,
    *,
    duration_s: int,
    reps: int,
) -> dict[str, Any] | None:
    run = active_runs.get(target_id)
    if not run:
        return None
    recorded_duration = int_value(run.get("duration_s"))
    recorded_reps = int_value(run.get("repetitions") or run.get("reps"))
    if recorded_duration and recorded_duration != duration_s:
        return None
    if recorded_reps and recorded_reps != reps:
        return None
    return run


def native_build_plan_map(root: Path | None) -> dict[str, dict[str, Any]]:
    if root is None or not root.exists():
        return {}
    plans: dict[str, dict[str, Any]] = {}
    for path in sorted(root.glob("*/build_plan.json")):
        try:
            payload = read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        target_id = str(payload.get("target_id") or path.parent.name)
        if not target_id:
            continue
        payload["_build_plan_path"] = str(path)
        plans[target_id] = payload
    return plans


def binding_validation_paths(root: Path | None) -> list[Path]:
    if root is None or not root.exists():
        return []
    if root.is_file() and root.name.endswith(".validation.json"):
        return [root]
    return sorted(root.glob("*.validation.json"))


def binding_validation_ready(payload: dict[str, Any] | None) -> bool:
    if not payload:
        return False
    if payload.get("ready_for_short_gate") is True:
        return True
    return str(payload.get("status") or "") == "native_binding_validated"


def binding_validation_score(payload: dict[str, Any]) -> tuple[int, str, str]:
    return (
        int(binding_validation_ready(payload)),
        str(payload.get("generated_at_utc") or ""),
        str(payload.get("_binding_validation_path") or ""),
    )


def binding_validation_map(root: Path | None) -> dict[str, dict[str, Any]]:
    validations: dict[str, dict[str, Any]] = {}
    for path in binding_validation_paths(root):
        try:
            payload = read_json(path)
        except (OSError, json.JSONDecodeError):
            continue
        target_id = str(payload.get("target_id") or "")
        if not target_id:
            continue
        payload["_binding_validation_path"] = str(path)
        current = validations.get(target_id)
        if current is None or binding_validation_score(payload) >= binding_validation_score(current):
            validations[target_id] = payload
    return validations


def sota_pain_class(triage: dict[str, Any] | None) -> str:
    if not triage:
        return ""
    return str(triage.get("sota_pain_class") or "")


def sota_pain_evidence(triage: dict[str, Any] | None) -> str:
    if not triage:
        return ""
    return str(triage.get("sota_pain_evidence") or "")


def attach_sota_pain(
    task: dict[str, Any],
    triage: dict[str, Any] | None,
) -> dict[str, Any]:
    task["sota_pain_class"] = sota_pain_class(triage)
    task["sota_pain_evidence"] = sota_pain_evidence(triage)
    return task


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def comparison_verdict(comparison: dict[str, Any] | None) -> str:
    if not comparison:
        return ""
    analysis = comparison.get("analysis") if isinstance(comparison.get("analysis"), dict) else {}
    return str(analysis.get("verdict") or comparison.get("verdict") or "")


def comparison_main_claim_strength(comparison: dict[str, Any] | None) -> str:
    if not comparison:
        return ""
    analysis = comparison.get("analysis") if isinstance(comparison.get("analysis"), dict) else {}
    strength = (
        analysis.get("experiment_strength")
        if isinstance(analysis.get("experiment_strength"), dict)
        else {}
    )
    return str(strength.get("main_claim_strength") or "")


def comparison_max_budget(comparison: dict[str, Any] | None) -> int:
    if not comparison:
        return 0
    analysis = comparison.get("analysis") if isinstance(comparison.get("analysis"), dict) else {}
    budgets = [
        int_value(group.get("budget"))
        for group in analysis.get("baseline_groups", [])
        if int_value(group.get("budget")) > 0
    ]
    budgets.extend(
        int_value(row.get("budget"))
        for row in comparison.get("formtrig_runs", [])
        if int_value(row.get("budget")) > 0
    )
    return max(budgets) if budgets else 0


def comparison_min_baseline_reps(comparison: dict[str, Any] | None) -> int:
    if not comparison:
        return 0
    analysis = comparison.get("analysis") if isinstance(comparison.get("analysis"), dict) else {}
    reps = [
        int_value(group.get("reps"))
        for group in analysis.get("baseline_groups", [])
        if int_value(group.get("reps")) > 0
    ]
    return min(reps) if reps else 0


def comparison_formtrig_reps_at_budget(
    comparison: dict[str, Any] | None,
    duration_s: int,
) -> int:
    if not comparison:
        return 0
    return sum(
        1
        for row in comparison.get("formtrig_runs", [])
        if int_value(row.get("budget")) >= duration_s
        or int_value(row.get("run_time")) >= duration_s
    )


def comparison_longrun_complete(
    comparison: dict[str, Any] | None,
    *,
    duration_s: int,
    reps: int,
) -> bool:
    return (
        comparison_max_budget(comparison) >= duration_s
        and comparison_min_baseline_reps(comparison) >= reps
        and comparison_formtrig_reps_at_budget(comparison, duration_s) >= reps
    )


def comparison_promotes_longrun(comparison: dict[str, Any] | None) -> bool:
    if comparison_main_claim_strength(comparison) in WEAK_MAIN_CLAIM_STRENGTHS:
        return False
    return comparison_verdict(comparison) in LONGRUN_PROMOTION_VERDICTS


def strongest_comparison(comparisons: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not comparisons:
        return None

    def score(payload: dict[str, Any]) -> tuple[int, int, int, int, int, str]:
        analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
        benefit = payload.get("benefit_readout") if isinstance(payload.get("benefit_readout"), dict) else {}
        verdict = comparison_verdict(payload)
        strength = comparison_main_claim_strength(payload)
        if strength in WEAK_MAIN_CLAIM_STRENGTHS:
            verdict_score = 1
        elif verdict in LONGRUN_PROMOTION_VERDICTS:
            verdict_score = 4
        elif verdict in COMPLETE_REPS_VERDICTS:
            verdict_score = 3
        elif "positive" in verdict:
            verdict_score = 2
        else:
            verdict_score = 0
        has_longrun = int(bool(analysis.get("longrun_10m_confirmation") or payload.get("longrun_10m_confirmation")))
        benefit_count = len(benefit.get("primary_benefits") or [])
        matched_baselines = int_value(analysis.get("matched_baseline_count"))
        return (
            verdict_score,
            has_longrun,
            comparison_max_budget(payload),
            matched_baselines,
            benefit_count,
            str(payload.get("_comparison_path") or ""),
        )

    return max(comparisons, key=score)


def weak_design_comparison(comparisons: list[dict[str, Any]]) -> dict[str, Any] | None:
    weak = [
        comparison
        for comparison in comparisons
        if comparison_main_claim_strength(comparison) in WEAK_MAIN_CLAIM_STRENGTHS
    ]
    if not weak:
        return None
    hard = [
        comparison
        for comparison in comparisons
        if comparison_main_claim_strength(comparison)
        and comparison_main_claim_strength(comparison) not in WEAK_MAIN_CLAIM_STRENGTHS
    ]
    if hard:
        return None
    return max(weak, key=lambda payload: str(payload.get("_comparison_path") or ""))


def is_demoted_control(row: dict[str, Any]) -> bool:
    lane = str(row.get("lane") or "")
    status = str(row.get("status") or "")
    disposition = str(row.get("existing_disposition") or "")
    return lane in DEMOTED_CONTROL_LANES or status in CONTROL_STATUSES or disposition in DEMOTE_DISPOSITIONS


def is_non_main_budget(row: dict[str, Any]) -> bool:
    lane = str(row.get("lane") or "")
    return is_demoted_control(row) or lane in NON_MAIN_BUDGET_LANES


def target_id_for(row: dict[str, Any]) -> str:
    return str(row.get("target_id") or "")


def is_sota_pain_skip(
    row: dict[str, Any],
    target_triage: dict[str, dict[str, Any]],
) -> bool:
    return sota_pain_class(target_triage.get(target_id_for(row))) in SOTA_PAIN_SKIP_CLASSES


def priority_for(row: dict[str, Any]) -> str:
    if str(row.get("existing_disposition") or "") == "candidate_extend_longruns":
        return "P0"
    rank = int(row.get("rank") or 999)
    if row.get("source") == "real_cve" and rank <= 4:
        return "P0"
    if rank <= 8:
        return "P1"
    if rank <= 20:
        return "P2"
    return "P3"


def category_text(row: dict[str, Any]) -> str:
    primary = str(row.get("primary_category") or "")
    secondary = str(row.get("secondary_category") or "")
    return "+".join([part for part in [primary, secondary] if part])


def as_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    if value in (None, ""):
        return []
    return [str(value)]


def evidence_paths(row: dict[str, Any], comparison: dict[str, Any] | None) -> list[str]:
    paths: list[str] = []
    if row.get("source_evidence"):
        paths.append(str(row.get("source_evidence")))
    if comparison and comparison.get("_comparison_path"):
        paths.append(str(comparison["_comparison_path"]))
        analysis = comparison.get("analysis") if isinstance(comparison.get("analysis"), dict) else {}
        for key in ("repetition_summary",):
            value = analysis.get(key)
            if value:
                base = Path(str(comparison["_comparison_path"])).parent
                paths.append(str(base / str(value)))
    return sorted(dict.fromkeys(paths))


def evidence_paths_with_active_run(
    row: dict[str, Any],
    comparison: dict[str, Any] | None,
    active_run: dict[str, Any] | None,
) -> list[str]:
    paths = evidence_paths(row, comparison)
    if not active_run:
        return paths
    for key in ("run_root", "guidance_out", "comparison_out", "live_status"):
        value = active_run.get(key)
        if value:
            paths.append(str(value))
    for value in active_run.get("baseline_roots") or []:
        if value:
            paths.append(str(value))
    return sorted(dict.fromkeys(paths))


def evidence_paths_with_validation(
    row: dict[str, Any],
    comparison: dict[str, Any] | None,
    validation: dict[str, Any] | None,
) -> list[str]:
    paths = evidence_paths(row, comparison)
    if validation and validation.get("_binding_validation_path"):
        paths.append(str(validation["_binding_validation_path"]))
    source = validation.get("source") if isinstance(validation, dict) else {}
    if isinstance(source, dict) and source.get("summary_jsonl"):
        paths.append(str(source["summary_jsonl"]))
    return sorted(dict.fromkeys(paths))


def add_unique(values: list[str], additions: list[str]) -> list[str]:
    seen = set(values)
    for value in additions:
        if value and value not in seen:
            values.append(value)
            seen.add(value)
    return values


def apply_native_build_plan_blockers(
    task: dict[str, Any],
    build_plan: dict[str, Any] | None,
) -> dict[str, Any]:
    if not build_plan:
        return task
    if build_plan.get("_build_plan_path"):
        task["evidence_paths"] = add_unique(
            list(task.get("evidence_paths") or []),
            [str(build_plan["_build_plan_path"])],
        )

    preflight = (
        build_plan.get("dependency_preflight")
        if isinstance(build_plan.get("dependency_preflight"), dict)
        else {}
    )
    if preflight.get("status") != "missing":
        return task

    apt_hints = [str(item) for item in preflight.get("apt_package_hints") or [] if str(item)]
    blockers = [
        "native build dependencies missing: " + " ".join(apt_hints)
        if apt_hints
        else "native build dependencies missing"
    ]
    for check in preflight.get("checks") or []:
        if not isinstance(check, dict) or check.get("status") != "missing":
            continue
        detail = str(check.get("id") or check.get("kind") or "dependency")
        hints = " ".join(str(item) for item in check.get("apt_package_hints") or [])
        if hints:
            detail = f"{detail} apt={hints}"
        blockers.append(detail)
    task["blocking_issue"] = add_unique(list(task.get("blocking_issue") or []), blockers)
    if apt_hints:
        task["post_unblock_commands"] = add_unique(
            [f"sudo apt-get install -y {' '.join(apt_hints)}"],
            list(task.get("post_unblock_commands") or []),
        )
    task["runnable_now"] = False
    return task


def comparison_summary(comparison: dict[str, Any] | None) -> dict[str, Any]:
    if not comparison:
        return {
            "verdict": "",
            "primary_benefits": [],
            "design_evidence": [],
            "blocked_claims": [],
            "longrun_10m_confirmation": None,
            "main_claim_strength": "",
            "recommended_design_actions": [],
        }
    analysis = comparison.get("analysis") if isinstance(comparison.get("analysis"), dict) else {}
    benefit = comparison.get("benefit_readout") if isinstance(comparison.get("benefit_readout"), dict) else {}
    strength = (
        analysis.get("experiment_strength")
        if isinstance(analysis.get("experiment_strength"), dict)
        else {}
    )
    return {
        "verdict": str(analysis.get("verdict") or ""),
        "primary_benefits": as_list(benefit.get("primary_benefits"))[:4],
        "design_evidence": as_list(benefit.get("design_evidence"))[:6],
        "blocked_claims": as_list(benefit.get("blocked_claims"))[:4],
        "longrun_10m_confirmation": analysis.get("longrun_10m_confirmation")
        or comparison.get("longrun_10m_confirmation"),
        "main_claim_strength": str(strength.get("main_claim_strength") or ""),
        "recommended_design_actions": as_list(strength.get("recommended_design_actions")),
    }


def shell_join(args: list[str]) -> str:
    return " ".join(shlex.quote(arg) for arg in args)


def manifest_key_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return values
    for raw in lines:
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    return values


def manifest_list_paths(path: Path) -> list[Path]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    paths: list[Path] = []
    for raw in lines:
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        paths.append(Path(line))
    return paths


def afl_args_for_manifest_list(manifest_list: str) -> list[str]:
    for manifest in manifest_list_paths(Path(manifest_list)):
        values = manifest_key_values(manifest)
        raw = values.get("afl_args", "")
        if not raw:
            continue
        try:
            return shlex.split(raw)
        except ValueError:
            return []
    return []


def magma_baseline_command(
    target_id: str,
    duration_s: int,
    jobs: int,
    reps: int,
    *,
    out_dir: str | None = None,
    afl_args: list[str] | None = None,
) -> str:
    args = [
        "scripts/run_magma_baselines.sh",
        "--target-id",
        target_id,
        "--durations",
        str(duration_s),
        "--jobs",
        str(jobs),
    ]
    if out_dir:
        args.extend(["--out", out_dir])
    for arg in afl_args or []:
        args.extend(["--afl-arg", arg])
    if reps > 1:
        args.extend(["--reps", str(reps)])
    return shell_join(args)


def formtrig_manifest_batch_command(
    manifest_list: str,
    duration_s: int,
    jobs: int,
    *,
    out_root: str | None = None,
) -> str:
    args = [
        "scripts/run_formtrig_manifest_batch.sh",
        "--manifest-list",
        manifest_list,
        "--duration",
        str(duration_s),
        "--jobs",
        str(jobs),
        "--continue-on-fail",
    ]
    if out_root:
        args.extend(["--out-root", out_root])
    return shell_join(args)


def preferred_manifest_list(target_id: str, manifest_root: Path, reps: int = 1) -> str:
    if reps > 1:
        repeated = manifest_root / f"{target_id}.current_{reps}rep.list"
        if repeated.exists():
            return str(repeated)
    current = manifest_root / f"{target_id}.current_1rep.list"
    if current.exists():
        return str(current)
    return str(manifest_root / f"{target_id}.list")


def validated_short_screen_command(
    target_id: str,
    duration_s: int,
    jobs: int,
    reps: int,
    manifest_root: Path,
) -> tuple[str, list[str]]:
    tag = f"{target_id.lower()}_validated_short_{duration_s}s_{reps}rep"
    baseline_out = f"artifacts/formtrig_native_readiness/raw/{tag}_baselines"
    formtrig_out = f"artifacts/formtrig_native_readiness/raw/{tag}_formtrig"
    manifest_list = preferred_manifest_list(target_id, manifest_root, reps)
    baseline_afl_args = afl_args_for_manifest_list(manifest_list)
    commands = [
        magma_baseline_command(
            target_id,
            duration_s,
            jobs,
            reps,
            out_dir=baseline_out,
            afl_args=baseline_afl_args,
        ),
        formtrig_manifest_batch_command(
            manifest_list,
            duration_s,
            jobs,
            out_root=formtrig_out,
        ),
    ]
    followups = [
        "after both arms finish, build a comparison package with tools/compare_formtrig_baselines.py",
        "classify the target as hard-gap evidence only if faithful baselines show flat binary TC guidance and late/missing/high-variance _T",
    ]
    return " && ".join(commands), followups


def tif012_magma_longrun_steps(duration_s: int, reps: int, jobs: int) -> list[str]:
    manifest_list = "artifacts/formtrig_native_readiness/manifests/TIF012.b5_current_3rep.list"
    run_tag = f"tif012_b5_matched_{duration_s}s_{reps}rep_<UTC>"
    formtrig_out = f"artifacts/formtrig_native_readiness/raw/{run_tag}_formtrig"
    baseline_out = f"artifacts/formtrig_native_readiness/raw/{run_tag}_baselines"
    gate_out = f"{formtrig_out}/gate"
    comparison_out = f"artifacts/formtrig_native_readiness/comparisons/{run_tag}"
    return [
        formtrig_manifest_batch_command(
            manifest_list,
            duration_s,
            jobs,
            out_root=formtrig_out,
        ),
        magma_baseline_command(
            "TIF012",
            duration_s,
            jobs,
            reps,
            out_dir=baseline_out,
        ),
        shell_join(
            [
                "scripts/formtrig_experiment_gate.sh",
                "--suite",
                f"TIF012_b5_{duration_s}s_{reps}rep",
                "--out",
                gate_out,
                "--min-runtime",
                str(duration_s),
                "--run",
                f"rep1={formtrig_out}/001_TIF012/out",
                "--run",
                f"rep2={formtrig_out}/002_TIF012/out",
                "--run",
                f"rep3={formtrig_out}/003_TIF012/out",
            ]
        ),
        shell_join(
            [
                "python3",
                "tools/compare_formtrig_baselines.py",
                "--comparison-id",
                run_tag,
                "--target-id",
                "TIF012",
                "--formtrig-gate",
                f"b5_{duration_s}s_{reps}rep={gate_out}/gate_summary.csv",
                "--baseline-summary",
                f"aflpp_family_{duration_s}s_{reps}rep={baseline_out}/summary.json",
                "--out-dir",
                comparison_out,
                "--min-reps",
                str(reps),
                "--required-baselines",
                BASELINE_FAMILY,
            ]
        ),
    ]


def magma_matched_longrun_steps(
    target_id: str,
    duration_s: int,
    reps: int,
    jobs: int,
    manifest_root: Path,
) -> list[str]:
    manifest_list = preferred_manifest_list(target_id, manifest_root, reps)
    utc_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_tag = f"{target_id.lower()}_matched_{duration_s}s_{reps}rep_{utc_stamp}"
    formtrig_out = f"artifacts/formtrig_native_readiness/raw/{run_tag}_formtrig"
    baseline_out = f"artifacts/formtrig_native_readiness/raw/{run_tag}_baselines"
    gate_out = f"{formtrig_out}/gate"
    guidance_out = f"artifacts/formtrig_native_readiness/baseline_guidance_gap/{run_tag}"
    comparison_out = f"artifacts/formtrig_native_readiness/comparisons/{run_tag}"
    gate_args = [
        "scripts/formtrig_experiment_gate.sh",
        "--suite",
        f"{target_id}_{duration_s}s_{reps}rep",
        "--out",
        gate_out,
        "--min-runtime",
        str(duration_s),
    ]
    for index in range(1, reps + 1):
        gate_args.extend(
            [
                "--run",
                f"rep{index}={formtrig_out}/{index:03d}_{target_id}/out",
            ]
        )
    baseline_label = f"aflpp_family_{duration_s}s_{reps}rep"
    return [
        magma_baseline_command(
            target_id,
            duration_s,
            jobs,
            reps,
            out_dir=baseline_out,
            afl_args=afl_args_for_manifest_list(manifest_list),
        ),
        formtrig_manifest_batch_command(
            manifest_list,
            duration_s,
            jobs,
            out_root=formtrig_out,
        ),
        shell_join(gate_args),
        shell_join(
            [
                "python3",
                "tools/analyze_baseline_guidance_gap.py",
                "--analysis-id",
                f"{run_tag}_baseline_guidance_gap",
                "--target-id",
                target_id,
                "--baseline-summary",
                f"{baseline_label}={baseline_out}/summary.json",
                "--out-dir",
                guidance_out,
                "--required-baselines",
                BASELINE_FAMILY,
                "--min-reps",
                str(reps),
                "--acceptable-trigger-s",
                "600",
                "--hard-trigger-s",
                "1800",
            ]
        ),
        shell_join(
            [
                "python3",
                "tools/compare_formtrig_baselines.py",
                "--comparison-id",
                run_tag,
                "--target-id",
                target_id,
                "--formtrig-gate",
                f"typed_hook_{duration_s}s_{reps}rep={gate_out}/gate_summary.csv",
                "--baseline-summary",
                f"{baseline_label}={baseline_out}/summary.json",
                "--baseline-guidance-gap",
                guidance_out,
                "--out-dir",
                comparison_out,
                "--min-reps",
                str(reps),
                "--required-baselines",
                BASELINE_FAMILY,
            ]
        ),
    ]


def longrun_task(
    row: dict[str, Any],
    comparison: dict[str, Any] | None,
    *,
    duration_s: int,
    reps: int,
    jobs: int,
    manifest_root: Path,
    active_runs: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    summary = comparison_summary(comparison)
    target_id = str(row.get("target_id") or "")
    verdict = comparison_verdict(comparison)
    active_run = matching_active_run(
        active_runs or {},
        target_id,
        duration_s=duration_s,
        reps=reps,
    )
    command = ""
    blocking_issue = [
        "no reusable matched 2h runner is recorded for this real-CVE target",
        "existing evidence is 60s x3 plus one 10m confirmation, not 2h repetitions",
    ]
    post_unblock_commands = [
        "create a target-specific matched runner from the saved 10m run records",
        "then rebuild the comparison package with tools/compare_formtrig_baselines.py",
    ]
    runner_path = Path("scripts/run_libarchive_2936_matched_longrun.sh")
    if active_run:
        status = str(active_run.get("status") or "running")
        run_root = str(active_run.get("run_root") or "")
        guidance_out = str(active_run.get("guidance_out") or "")
        comparison_out = str(active_run.get("comparison_out") or "")
        blocking_issue = [
            f"active matched longrun status={status}",
            "wait for all expected baseline run_record.json files before final claims",
        ]
        if run_root:
            blocking_issue.append(f"active run root: {run_root}")
        post_unblock_commands = []
        baseline_roots = [str(value) for value in active_run.get("baseline_roots") or [] if str(value)]
        if len(baseline_roots) > 1:
            post_unblock_commands.append(
                "python3 tools/merge_magma_baseline_roots.py "
                f"--out {run_root}/merged_baselines "
                + " ".join(f"--source {root}" for root in baseline_roots)
                + " --duplicate-policy prefer-later"
            )
        if run_root and guidance_out and comparison_out:
            baseline_dir = (
                f"{run_root}/merged_baselines"
                if len(baseline_roots) > 1
                else (baseline_roots[0] if baseline_roots else f"{run_root}/baselines")
            )
            post_unblock_commands.append(
                shell_join(
                    [
                        "scripts/finalize_magma_matched_run.sh",
                        "--run-root",
                        run_root,
                        "--baseline-dir",
                        baseline_dir,
                        "--guidance-out",
                        guidance_out,
                        "--comparison-out",
                        comparison_out,
                    ]
                )
            )
        command = ""
    elif target_id == "LIBARCHIVE_2936" and runner_path.exists():
        command = shell_join(
            [
                str(runner_path),
                "--duration",
                str(duration_s),
                "--reps",
                str(reps),
                "--jobs",
                str(jobs),
            ]
        )
        blocking_issue = []
        post_unblock_commands = []
    elif target_id == "TIF012" and str(row.get("source") or "") == "magma":
        runner_path = Path("scripts/run_tif012_b5_matched_longrun.sh")
        if runner_path.exists():
            command = shell_join(
                [
                    str(runner_path),
                    "--duration",
                    str(duration_s),
                    "--reps",
                    str(reps),
                    "--jobs",
                    str(jobs),
                ]
            )
            blocking_issue = []
            post_unblock_commands = []
        else:
            blocking_issue = [
                "no single reusable matched long-run runner currently coordinates this Magma target and rebuilds the comparison package",
                "use the recorded TIF012 b5 manifest list and regenerate the comparison package after both arms finish",
            ]
            post_unblock_commands = tif012_magma_longrun_steps(duration_s, reps, jobs)
    elif str(row.get("source") or "") == "magma":
        manifest_list = Path(preferred_manifest_list(target_id, manifest_root, reps))
        if manifest_list.exists():
            utc_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            run_tag = f"{target_id.lower()}_matched_{duration_s}s_{reps}rep_{utc_stamp}"
            runner_args = [
                "scripts/run_magma_matched_longrun.sh",
                "--target-id",
                target_id,
                "--duration",
                str(duration_s),
                "--reps",
                str(reps),
                "--jobs",
                str(jobs),
                "--manifest-list",
                str(manifest_list),
                "--out",
                f"artifacts/formtrig_native_readiness/raw/{run_tag}",
                "--guidance-out",
                f"artifacts/formtrig_native_readiness/baseline_guidance_gap/{run_tag}",
                "--comparison-out",
                f"artifacts/formtrig_native_readiness/comparisons/{run_tag}",
                "--continue-on-fail",
            ]
            for afl_arg in afl_args_for_manifest_list(str(manifest_list)):
                runner_args.extend(["--baseline-afl-arg", afl_arg])
            command = shell_join(runner_args)
            blocking_issue = []
            post_unblock_commands = []
    if verdict == "positive_endpoint_matched_comparison":
        benefit_to_prove = (
            "Confirm that the current matched-budget endpoint benefit "
            f"persists in {reps} matched {duration_s}s repetitions: FORMTRIG "
            "reaches _T while faithful baselines do not."
        )
    else:
        benefit_to_prove = (
            "Confirm that the current first-_T speedup and lower execution cost "
            f"persist in {reps} matched {duration_s}s repetitions."
        )

    return {
        "priority": "P0" if comparison_promotes_longrun(comparison) else priority_for(row),
        "rank": int(row.get("rank") or 0),
        "target_id": target_id,
        "source": str(row.get("source") or ""),
        "project": str(row.get("project") or ""),
        "category": category_text(row),
        "lane": str(row.get("lane") or ""),
        "action": "monitor_active_matched_longrun" if active_run else "extend_matched_longrun",
        "duration_s": duration_s,
        "repetitions": reps,
        "benefit_to_prove": benefit_to_prove,
        "primary_endpoint_metrics": [
            "same-budget terminal success rate",
            "first _T / terminal-crash wall-clock time",
            "first _T / terminal-crash execution count",
            "PRET/TTE under the same seed corpus and oracle",
        ],
        "mechanism_evidence_required": summary["design_evidence"]
        or [
            "strict pre-trigger D_F progress",
            "saved replay-stable non-trigger progress",
            "typed mutation provenance",
            "same timeout/oracle as baselines",
        ],
        "blocking_issue": blocking_issue,
        "claim_boundary": (
            "Report as speedup/attribution unless long-run matched baselines stop "
            "triggering while FORMTRIG remains successful."
        ),
        "command": command,
        "runnable_now": bool(command) and not active_run,
        "post_unblock_commands": post_unblock_commands,
        "comparison_verdict": summary["verdict"],
        "main_claim_strength": summary["main_claim_strength"],
        "current_primary_benefits": summary["primary_benefits"],
        "blocked_claims": summary["blocked_claims"],
        "evidence_paths": evidence_paths_with_active_run(row, comparison, active_run),
        "active_run_status": str(active_run.get("status") or "") if active_run else "",
        "active_run_root": str(active_run.get("run_root") or "") if active_run else "",
    }


def improve_experiment_design_task(
    row: dict[str, Any],
    comparison: dict[str, Any] | None,
) -> dict[str, Any]:
    summary = comparison_summary(comparison)
    design_actions = summary["recommended_design_actions"] or [
        "rerun with a higher-fidelity/raw-format harness or a farther RNT seed",
        "add no-hook and generic-hook FORMTRIG ablations",
        "move hard-gap budget to targets where strong baselines have low success or long R2T tails",
    ]
    return {
        "priority": "P0",
        "rank": int(row.get("rank") or 0),
        "target_id": str(row.get("target_id") or ""),
        "source": str(row.get("source") or ""),
        "project": str(row.get("project") or ""),
        "category": category_text(row),
        "lane": str(row.get("lane") or ""),
        "action": "improve_experiment_design",
        "duration_s": "",
        "repetitions": "",
        "benefit_to_prove": (
            "Make the experiment hard enough to expose SOTA R2T pain: current "
            "speedup is real, but matched baselines trigger too early for this "
            "package to serve as main binary-TC gap evidence."
        ),
        "primary_endpoint_metrics": [
            "baseline success-rate gap under matched budget",
            "baseline R2T tail or median above early-trigger threshold",
            "FORMTRIG TTE and exec-count advantage after no-hook/generic-hook ablations",
        ],
        "mechanism_evidence_required": summary["design_evidence"]
        or [
            "strict pre-trigger D_F progress",
            "typed mutation provenance",
            "same timeout/oracle as baselines",
        ],
        "blocking_issue": [
            f"main_claim_strength={summary['main_claim_strength']}",
            "current comparison is not hard enough for SOTA-gap evidence",
        ],
        "claim_boundary": (
            "Keep the current speedup as secondary engineering evidence only; "
            "do not promote it as main hard-gap evidence until the experiment "
            "is made harder."
        ),
        "command": "",
        "runnable_now": False,
        "post_unblock_commands": design_actions,
        "comparison_verdict": summary["verdict"],
        "current_primary_benefits": summary["primary_benefits"],
        "blocked_claims": summary["blocked_claims"],
        "evidence_paths": evidence_paths(row, comparison),
    }


def expand_hard_evidence_task(
    row: dict[str, Any],
    comparison: dict[str, Any] | None,
) -> dict[str, Any]:
    summary = comparison_summary(comparison)
    return {
        "priority": "P0",
        "rank": int(row.get("rank") or 0),
        "target_id": str(row.get("target_id") or ""),
        "source": str(row.get("source") or ""),
        "project": str(row.get("project") or ""),
        "category": category_text(row),
        "lane": str(row.get("lane") or ""),
        "action": "expand_cross_target_hard_evidence",
        "duration_s": "",
        "repetitions": "",
        "benefit_to_prove": (
            "The matched long-run budget is already complete for this target; "
            "spend new budget on cross-target hard evidence instead of rerunning "
            "the same campaign."
        ),
        "primary_endpoint_metrics": [
            "replicated matched-budget terminal success rate",
            "first _T / terminal-crash wall-clock time",
            "baseline R2T tail and success-rate variance across targets",
        ],
        "mechanism_evidence_required": summary["design_evidence"],
        "blocking_issue": [],
        "claim_boundary": (
            "Use this target as one hard-speedup data point; broad claims still "
            "require additional Magma and real-CVE targets."
        ),
        "command": "",
        "runnable_now": False,
        "post_unblock_commands": [
            "run the next hard Magma/real-CVE target with matched baselines",
            "prioritize targets where strong baselines have low success or long R2T tails",
            "add ablations for any target-specific typed hook before main-claim use",
        ],
        "comparison_verdict": summary["verdict"],
        "current_primary_benefits": summary["primary_benefits"],
        "blocked_claims": summary["blocked_claims"],
        "evidence_paths": evidence_paths(row, comparison),
    }


def binding_spec_first_task(
    row: dict[str, Any],
    comparison: dict[str, Any] | None,
    *,
    short_duration_s: int,
    jobs: int,
    reps: int,
) -> dict[str, Any]:
    target_id = str(row.get("target_id") or "")
    source = str(row.get("source") or "")
    is_magma = source == "magma"
    if is_magma:
        action = "draft_binding_spec_then_short_screen"
        post_unblock = [
            magma_baseline_command(target_id, short_duration_s, jobs, reps),
            formtrig_manifest_batch_command(
                f"artifacts/formtrig_native_readiness/manifests/{target_id}.list",
                short_duration_s,
                jobs,
            ),
        ]
    else:
        action = "validate_replay_then_draft_binding_spec"
        post_unblock = [
            "validate vulnerable build and PoC replay",
            "write harness admissibility note",
            "draft BindingSpec and run binding-signal sweep",
        ]

    return {
        "priority": priority_for(row),
        "rank": int(row.get("rank") or 0),
        "target_id": target_id,
        "source": source,
        "project": str(row.get("project") or ""),
        "category": category_text(row),
        "lane": str(row.get("lane") or ""),
        "action": action,
        "duration_s": short_duration_s,
        "repetitions": reps,
        "runnable_now": False,
        "benefit_to_prove": (
            "Find whether a binary or lifecycle TC can be converted into "
            "accepted non-trigger progress and then a faster terminal outcome "
            "than faithful baselines."
        ),
        "primary_endpoint_metrics": [
            "10m same-budget terminal success rate",
            "first _T / terminal-crash wall-clock time",
            "first _T / terminal-crash execution count",
            "baseline-visible vs FORMTRIG-only endpoint behavior",
        ],
        "mechanism_evidence_required": [
            "BindingSpec compiles against native site ids",
            "D_F_spec_lifted is non-constant before _T",
            "saved non-trigger progress is replay-stable",
            "typed mutation, if used, is BindingSpec-provenance tagged",
        ],
        "blocking_issue": [item.strip() for item in str(row.get("blockers") or "").split(";") if item.strip()]
        or ["no validated BindingSpec gate has been recorded"],
        "claim_boundary": (
            "Do not spend 2h budget or make performance claims until the short "
            "screen has endpoint benefit; use failed screens as negative/control evidence."
        ),
        "command": "",
        "post_unblock_commands": post_unblock,
        "comparison_verdict": comparison_summary(comparison)["verdict"],
        "current_primary_benefits": comparison_summary(comparison)["primary_benefits"],
        "blocked_claims": comparison_summary(comparison)["blocked_claims"],
        "evidence_paths": evidence_paths(row, comparison),
    }


def validation_first_task(
    row: dict[str, Any],
    comparison: dict[str, Any] | None,
    *,
    short_duration_s: int,
    jobs: int,
    reps: int,
) -> dict[str, Any]:
    target_id = str(row.get("target_id") or "")
    source = str(row.get("source") or "")
    post_unblock: list[str] = []
    if source == "magma":
        post_unblock.append(magma_baseline_command(target_id, short_duration_s, jobs, reps))
        post_unblock.append(
            formtrig_manifest_batch_command(
                f"artifacts/formtrig_native_readiness/manifests/{target_id}.list",
                short_duration_s,
                jobs,
            )
        )
    else:
        post_unblock.append("run short FORMTRIG gate and same-budget AFL++ family baselines")

    return {
        "priority": priority_for(row),
        "rank": int(row.get("rank") or 0),
        "target_id": target_id,
        "source": source,
        "project": str(row.get("project") or ""),
        "category": category_text(row),
        "lane": str(row.get("lane") or ""),
        "action": "validate_binding_spec_then_short_screen",
        "duration_s": short_duration_s,
        "repetitions": reps,
        "runnable_now": False,
        "benefit_to_prove": (
            "Before comparing performance, prove that the candidate BindingSpec "
            "creates replay-stable pre-trigger guidance."
        ),
        "primary_endpoint_metrics": [
            "binding audit pass/fail",
            "accepted non-trigger progress count",
            "short-screen first _T/TTE after validation",
        ],
        "mechanism_evidence_required": [
            "native site-map validation",
            "lift audit pass",
            "binding-signal diagnosis pass",
            "seed readiness with reached non-trigger seeds",
        ],
        "blocking_issue": [item.strip() for item in str(row.get("blockers") or "").split(";") if item.strip()]
        or ["BindingSpec is present but not validated"],
        "claim_boundary": "Validation is a gate, not an efficacy result.",
        "command": "",
        "post_unblock_commands": post_unblock,
        "comparison_verdict": comparison_summary(comparison)["verdict"],
        "current_primary_benefits": comparison_summary(comparison)["primary_benefits"],
        "blocked_claims": comparison_summary(comparison)["blocked_claims"],
        "evidence_paths": evidence_paths(row, comparison),
    }


def validated_short_screen_task(
    row: dict[str, Any],
    comparison: dict[str, Any] | None,
    validation: dict[str, Any],
    *,
    short_duration_s: int,
    jobs: int,
    reps: int,
    manifest_root: Path,
) -> dict[str, Any]:
    target_id = str(row.get("target_id") or "")
    source = str(row.get("source") or "")
    command = ""
    followups: list[str] = []
    blocking_issue: list[str] = []
    if source == "magma":
        manifest_list = Path(preferred_manifest_list(target_id, manifest_root))
        if manifest_list.exists():
            command, followups = validated_short_screen_command(
                target_id,
                short_duration_s,
                jobs,
                reps,
                manifest_root,
            )
        else:
            blocking_issue = [
                "validated BindingSpec but short-screen manifest list is missing: "
                + str(manifest_list)
            ]
            followups = [
                "create a FORMTRIG manifest/list from the validated BindingSpec record",
                magma_baseline_command(target_id, short_duration_s, jobs, reps),
            ]
    else:
        blocking_issue = ["no generic validated short-screen runner is known for this real-CVE target"]
        followups = ["create a matched FORMTRIG/baseline runner from the validation record"]

    benefit = (
        validation.get("benefit_readout")
        if isinstance(validation.get("benefit_readout"), dict)
        else {}
    )
    signal = (
        validation.get("binding_signal")
        if isinstance(validation.get("binding_signal"), dict)
        else {}
    )
    mechanism_evidence = [
        "validated native BindingSpec with replay-stable pre-trigger D_F progress",
        "accepted non-trigger progress before terminal _T",
        "same seed corpus and Magma _T oracle as faithful AFL++ baselines",
        "binary-TC guidance-gap classification before any main-claim promotion",
    ]
    if benefit.get("non_trigger_progress_events") is not None:
        mechanism_evidence.append(
            f"validation non-trigger progress events={benefit.get('non_trigger_progress_events')}"
        )
    if signal.get("candidate_events") is not None:
        mechanism_evidence.append(f"validation candidate events={signal.get('candidate_events')}")

    return {
        "priority": priority_for(row),
        "rank": int(row.get("rank") or 0),
        "target_id": target_id,
        "source": source,
        "project": str(row.get("project") or ""),
        "category": category_text(row),
        "lane": str(row.get("lane") or ""),
        "action": "run_validated_matched_short_screen",
        "duration_s": short_duration_s,
        "repetitions": reps,
        "runnable_now": bool(command),
        "benefit_to_prove": (
            "Now that BindingSpec guidance is validated, test endpoint benefit "
            "against faithful AFL++ family baselines under the same budget. "
            "Promote only if baseline binary TC remains flat before _T and "
            "FORMTRIG improves terminal success, TTE, or execution cost."
        ),
        "primary_endpoint_metrics": [
            "same-budget terminal success rate",
            "first _T / terminal-crash wall-clock time",
            "first _T / terminal-crash execution count",
            "baseline-visible binary TC flatness before _T",
            "baseline R2T late/missing/high-variance evidence across repetitions",
        ],
        "mechanism_evidence_required": mechanism_evidence,
        "blocking_issue": blocking_issue,
        "claim_boundary": (
            "A passing short screen is still promotion evidence, not final 2h evidence; "
            "if baselines trigger early with acceptable time cost, demote to control/design work."
        ),
        "command": command,
        "post_unblock_commands": followups,
        "comparison_verdict": comparison_summary(comparison)["verdict"],
        "current_primary_benefits": comparison_summary(comparison)["primary_benefits"],
        "blocked_claims": comparison_summary(comparison)["blocked_claims"],
        "evidence_paths": evidence_paths_with_validation(row, comparison, validation),
    }


def short_triage_task(
    row: dict[str, Any],
    comparison: dict[str, Any] | None,
    *,
    short_duration_s: int,
    jobs: int,
    reps: int,
) -> dict[str, Any]:
    target_id = str(row.get("target_id") or "")
    source = str(row.get("source") or "")
    is_magma = source == "magma"
    command = ""
    if is_magma:
        command = magma_baseline_command(target_id, short_duration_s, jobs, reps)
    return {
        "priority": priority_for(row),
        "rank": int(row.get("rank") or 0),
        "target_id": target_id,
        "source": source,
        "project": str(row.get("project") or ""),
        "category": category_text(row),
        "lane": str(row.get("lane") or ""),
        "action": "run_short_endpoint_screen",
        "duration_s": short_duration_s,
        "repetitions": reps,
        "runnable_now": bool(command),
        "benefit_to_prove": (
            "Determine whether the validated lifted signal creates endpoint "
            "benefit before promoting to long-run repetitions."
        ),
        "primary_endpoint_metrics": [
            "10m same-budget terminal success rate",
            "first _T / terminal-crash wall-clock time",
            "first _T / terminal-crash execution count",
        ],
        "mechanism_evidence_required": [
            "strict pre-trigger guidance",
            "saved non-trigger progress",
            "same seed/oracle alignment",
        ],
        "blocking_issue": [] if command else ["no generic short-screen command is known for this target"],
        "claim_boundary": "Short-screen evidence can promote or demote, not serve as final 2h evidence.",
        "command": command,
        "post_unblock_commands": [],
        "comparison_verdict": comparison_summary(comparison)["verdict"],
        "current_primary_benefits": comparison_summary(comparison)["primary_benefits"],
        "blocked_claims": comparison_summary(comparison)["blocked_claims"],
        "evidence_paths": evidence_paths(row, comparison),
    }


def task_for_row(
    row: dict[str, Any],
    comparisons: dict[str, list[dict[str, Any]]],
    target_triage: dict[str, dict[str, Any]],
    binding_validations: dict[str, dict[str, Any]],
    active_runs: dict[str, dict[str, Any]],
    *,
    short_duration_s: int,
    longrun_duration_s: int,
    jobs: int,
    reps: int,
    longrun_reps: int,
    manifest_root: Path,
) -> dict[str, Any]:
    target_id = str(row.get("target_id") or "")
    triage = target_triage.get(target_id)
    validation = binding_validations.get(target_id)
    target_comparisons = comparisons.get(target_id, [])
    weak_comparison = weak_design_comparison(target_comparisons)
    comparison = weak_comparison or strongest_comparison(target_comparisons)
    disposition = str(row.get("existing_disposition") or "")
    lane = str(row.get("lane") or "")
    if sota_pain_class(triage) in SOTA_PAIN_DESIGN_CLASSES:
        return attach_sota_pain(improve_experiment_design_task(row, comparison), triage)
    if weak_comparison or comparison_main_claim_strength(comparison) in WEAK_MAIN_CLAIM_STRENGTHS:
        return attach_sota_pain(improve_experiment_design_task(row, comparison), triage)
    if comparison_promotes_longrun(comparison) and comparison_longrun_complete(
        comparison,
        duration_s=longrun_duration_s,
        reps=longrun_reps,
    ):
        return attach_sota_pain(expand_hard_evidence_task(row, comparison), triage)
    if comparison_promotes_longrun(comparison):
        return attach_sota_pain(
            longrun_task(
                row,
                comparison,
                duration_s=longrun_duration_s,
                reps=longrun_reps,
                jobs=jobs,
                manifest_root=manifest_root,
                active_runs=active_runs,
            ),
            triage,
        )
    if disposition == "candidate_extend_longruns":
        return attach_sota_pain(
            longrun_task(
                row,
                comparison,
                duration_s=longrun_duration_s,
                reps=longrun_reps,
                jobs=jobs,
                manifest_root=manifest_root,
                active_runs=active_runs,
            ),
            triage,
        )
    if lane == "binding_spec_first":
        return attach_sota_pain(
            binding_spec_first_task(
                row,
                comparison,
                short_duration_s=short_duration_s,
                jobs=jobs,
                reps=reps,
            ),
            triage,
        )
    if lane == "binding_validation_first":
        if binding_validation_ready(validation):
            return attach_sota_pain(
                validated_short_screen_task(
                    row,
                    comparison,
                    validation,
                    short_duration_s=short_duration_s,
                    jobs=jobs,
                    reps=reps,
                    manifest_root=manifest_root,
                ),
                triage,
            )
        return attach_sota_pain(
            validation_first_task(
                row,
                comparison,
                short_duration_s=short_duration_s,
                jobs=jobs,
                reps=reps,
            ),
            triage,
        )
    return attach_sota_pain(
        short_triage_task(
            row,
            comparison,
            short_duration_s=short_duration_s,
            jobs=jobs,
            reps=reps,
        ),
        triage,
    )


def build_worklist(
    queue_path: Path,
    comparison_root: Path,
    *,
    triage_path: Path | None = None,
    native_build_root: Path | None = None,
    binding_validation_root: Path | None = None,
    active_runs_path: Path | None = None,
    manifest_root: Path = DEFAULT_MANIFEST_ROOT,
    limit: int,
    use_all_targets: bool,
    short_duration_s: int,
    longrun_duration_s: int,
    jobs: int,
    reps: int,
    longrun_reps: int,
) -> dict[str, Any]:
    queue = read_json(queue_path)
    rows = queue_rows(queue, use_all_targets=use_all_targets)
    all_rows = queue_rows(queue, use_all_targets=True)
    comparisons = comparison_map(comparison_root)
    target_triage = triage_map(triage_path)
    build_plans = native_build_plan_map(native_build_root)
    binding_validations = binding_validation_map(binding_validation_root)
    active_runs = active_run_map(active_runs_path)
    tasks: list[dict[str, Any]] = []
    skipped_controls: list[dict[str, Any]] = [
        {
            "rank": row.get("rank"),
            "target_id": row.get("target_id"),
            "lane": row.get("lane"),
            "status": row.get("status"),
            "existing_disposition": row.get("existing_disposition"),
            "reason": (
                "sota_pain_triage_not_main_budget"
                if is_sota_pain_skip(row, target_triage)
                else "control_or_negative_not_main_budget"
            ),
            "sota_pain_class": sota_pain_class(
                target_triage.get(target_id_for(row))
            ),
            "sota_pain_evidence": sota_pain_evidence(
                target_triage.get(target_id_for(row))
            ),
            "next_action": row.get("next_action"),
        }
        for row in all_rows
        if is_demoted_control(row) or is_sota_pain_skip(row, target_triage)
    ]
    skipped_low_priority: list[dict[str, Any]] = [
        {
            "rank": row.get("rank"),
            "target_id": row.get("target_id"),
            "lane": row.get("lane"),
            "status": row.get("status"),
            "existing_disposition": row.get("existing_disposition"),
            "reason": "low_priority_or_audit_not_main_budget",
            "next_action": row.get("next_action"),
        }
        for row in all_rows
        if is_non_main_budget(row) and not is_demoted_control(row)
    ]
    for row in rows:
        if is_non_main_budget(row) or is_sota_pain_skip(row, target_triage):
            continue
        task = task_for_row(
            row,
            comparisons,
            target_triage,
            binding_validations,
            active_runs,
            short_duration_s=short_duration_s,
            longrun_duration_s=longrun_duration_s,
            jobs=jobs,
            reps=reps,
            longrun_reps=longrun_reps,
            manifest_root=manifest_root,
        )
        tasks.append(
            apply_native_build_plan_blockers(
                task,
                build_plans.get(target_id_for(row)),
            )
        )
        if len(tasks) >= limit:
            break

    runnable = [task for task in tasks if task.get("runnable_now")]
    return {
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "schema": "formtrig_benefit_first_experiment_worklist_v1",
        "inputs": {
            "queue": str(queue_path),
            "comparison_root": str(comparison_root),
            "triage": str(triage_path) if triage_path else "",
            "native_build_root": str(native_build_root) if native_build_root else "",
            "binding_validation_root": str(binding_validation_root) if binding_validation_root else "",
            "active_runs": str(active_runs_path) if active_runs_path else "",
            "manifest_root": str(manifest_root),
        },
        "defaults": {
            "short_duration_s": short_duration_s,
            "longrun_duration_s": longrun_duration_s,
            "jobs": jobs,
            "repetitions": reps,
            "longrun_repetitions": longrun_reps,
        },
        "benefit_first_rule": (
            "Endpoint benefit and cost come first; D_F, BindingSpec, dominance "
            "frontier, and typed mutation are attribution gates, not cross-tool "
            "performance metrics."
        ),
        "task_count": len(tasks),
        "runnable_now_count": len(runnable),
        "blocked_count": len(tasks) - len(runnable),
        "skipped_control_count": len(skipped_controls),
        "skipped_low_priority_count": len(skipped_low_priority),
        "tasks": tasks,
        "skipped_controls": skipped_controls,
        "skipped_low_priority": skipped_low_priority,
    }


def csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, dict)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def write_csv(path: Path, tasks: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=TASK_FIELDS, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for task in tasks:
            writer.writerow({field: csv_value(task.get(field)) for field in TASK_FIELDS})


def md_escape(value: Any) -> str:
    return str(value or "").replace("\n", " ").replace("|", "\\|")


def bullet_lines(values: list[str]) -> list[str]:
    if not values:
        return ["- none recorded"]
    return [f"- {value}" for value in values]


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    tasks = payload["tasks"]
    runnable = [task for task in tasks if task.get("runnable_now")]
    blocked = [task for task in tasks if not task.get("runnable_now")]
    lines = [
        "# FORMTRIG Benefit-First Experiment Worklist",
        "",
        payload["benefit_first_rule"],
        "",
        f"Generated: `{payload['generated_at_utc']}`",
        f"Tasks: `{payload['task_count']}`; runnable now: `{payload['runnable_now_count']}`; blocked/gated: `{payload['blocked_count']}`; demoted controls skipped: `{payload['skipped_control_count']}`; low-priority skipped: `{payload['skipped_low_priority_count']}`.",
        "",
        "## Budget Order",
        "",
        "1. Spend long-run budget only on targets with endpoint benefit or validated short-screen readiness.",
        "2. Treat `D_F`, BindingSpec, dominance frontier, and typed mutation as mechanism evidence after endpoint metrics.",
        "3. Keep terminal-only or harness-shaped cases as control/negative evidence.",
        "",
        "## Task Summary",
        "",
        "| priority | rank | target | source | SOTA pain | action | runnable | benefit to prove |",
        "| --- | ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for task in tasks:
        lines.append(
            "| {priority} | {rank} | {target_id} | {source} | {sota_pain} | {action} | {runnable} | {benefit} |".format(
                priority=md_escape(task.get("priority")),
                rank=task.get("rank", ""),
                target_id=md_escape(task.get("target_id")),
                source=md_escape(task.get("source")),
                sota_pain=md_escape(task.get("sota_pain_class")),
                action=md_escape(task.get("action")),
                runnable="yes" if task.get("runnable_now") else "blocked",
                benefit=md_escape(task.get("benefit_to_prove")),
            )
        )

    lines.extend(["", "## Runnable Now", ""])
    if runnable:
        for task in runnable:
            lines.extend(
                [
                    f"### {task['priority']} {task['target_id']}",
                    "",
                    f"- Benefit: {task['benefit_to_prove']}",
                    f"- SOTA pain: `{task.get('sota_pain_class') or 'not recorded'}`",
                    f"- SOTA pain evidence: {task.get('sota_pain_evidence') or 'not recorded'}",
                    f"- Command: `{task.get('command')}`",
                    "",
                ]
            )
    else:
        lines.append("No main-budget FORMTRIG task is runnable without a gate/blocker being cleared.")
        lines.append("")

    lines.extend(["## Gated Tasks", ""])
    for task in blocked:
        lines.extend(
            [
                f"### {task['priority']} {task['target_id']} - {task['action']}",
                "",
                f"- Benefit to prove: {task['benefit_to_prove']}",
                f"- SOTA pain: `{task.get('sota_pain_class') or 'not recorded'}`",
                f"- SOTA pain evidence: {task.get('sota_pain_evidence') or 'not recorded'}",
                f"- Endpoint metrics: {', '.join(task.get('primary_endpoint_metrics') or [])}",
                f"- Claim boundary: {task.get('claim_boundary')}",
                "- Blocking issue:",
                *bullet_lines(task.get("blocking_issue") or []),
                "- Mechanism evidence required after benefit:",
                *bullet_lines(task.get("mechanism_evidence_required") or []),
            ]
        )
        if task.get("current_primary_benefits"):
            lines.extend(["- Current primary benefits:", *bullet_lines(task["current_primary_benefits"])])
        if task.get("post_unblock_commands"):
            lines.extend(["- Post-unblock commands or steps:", *bullet_lines(task["post_unblock_commands"])])
        if task.get("evidence_paths"):
            lines.extend(["- Evidence paths:", *bullet_lines(task["evidence_paths"])])
        lines.append("")

    if payload.get("skipped_controls"):
        lines.extend(
            [
                "## Skipped Controls",
                "",
                "| rank | target | lane | disposition/status | SOTA pain | reason |",
                "| ---: | --- | --- | --- | --- | --- |",
            ]
        )
        for row in payload["skipped_controls"]:
            disposition = row.get("existing_disposition") or row.get("status") or ""
            lines.append(
                "| {rank} | {target_id} | {lane} | {disp} | {sota_pain} | {reason} |".format(
                    rank=row.get("rank", ""),
                    target_id=md_escape(row.get("target_id")),
                    lane=md_escape(row.get("lane")),
                    disp=md_escape(disposition),
                    sota_pain=md_escape(row.get("sota_pain_class")),
                    reason=md_escape(row.get("reason")),
                )
            )
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_shell(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# Generated FORMTRIG benefit-first runnable commands.",
        "# Gated tasks are intentionally emitted as comments.",
        "",
    ]
    for task in payload["tasks"]:
        label = f"{task['priority']} {task['target_id']} {task['action']}"
        lines.append(f"# {label}")
        lines.append(f"# benefit: {task['benefit_to_prove']}")
        if task.get("runnable_now") and task.get("command"):
            lines.append(str(task["command"]))
        else:
            blockers = "; ".join(task.get("blocking_issue") or ["blocked"])
            lines.append(f"# blocked: {blockers}")
            for command in task.get("post_unblock_commands") or []:
                lines.append(f"# post-unblock: {command}")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    path.chmod(0o755)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--queue",
        type=Path,
        default=Path("artifacts/formtrig_native_readiness/hard_target_discovery_queue_20260616.json"),
    )
    parser.add_argument(
        "--comparison-root",
        type=Path,
        default=Path("artifacts/formtrig_native_readiness/comparisons"),
    )
    parser.add_argument(
        "--triage",
        type=Path,
        default=Path("artifacts/formtrig_native_readiness/hard_target_triage_20260617.json"),
        help="target-level hard-pain triage JSON; missing files are ignored",
    )
    parser.add_argument(
        "--native-build-root",
        type=Path,
        default=DEFAULT_NATIVE_BUILD_ROOT,
        help="FORMTRIG-native Magma build-plan root; dependency blockers are surfaced when present",
    )
    parser.add_argument(
        "--binding-validation-root",
        type=Path,
        default=DEFAULT_BINDING_VALIDATION_ROOT,
        help="BindingSpec validation JSON root; ready records unblock matched short screens",
    )
    parser.add_argument(
        "--active-runs",
        type=Path,
        default=None,
        help="optional JSON list/map of active matched longruns to monitor instead of relaunching",
    )
    parser.add_argument(
        "--manifest-root",
        type=Path,
        default=DEFAULT_MANIFEST_ROOT,
        help="FORMTRIG manifest-list root used by validated short-screen tasks",
    )
    parser.add_argument("--out-json", required=True, type=Path)
    parser.add_argument("--out-md", required=True, type=Path)
    parser.add_argument("--out-csv", required=True, type=Path)
    parser.add_argument("--out-sh", required=True, type=Path)
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--use-all-targets", action="store_true")
    parser.add_argument("--short-duration", type=int, default=600)
    parser.add_argument("--longrun-duration", type=int, default=7200)
    parser.add_argument("--jobs", type=int, default=4)
    parser.add_argument("--reps", type=int, default=1)
    parser.add_argument("--longrun-reps", type=int, default=3)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_worklist(
        args.queue,
        args.comparison_root,
        triage_path=args.triage,
        native_build_root=args.native_build_root,
        binding_validation_root=args.binding_validation_root,
        active_runs_path=args.active_runs,
        manifest_root=args.manifest_root,
        limit=args.limit,
        use_all_targets=args.use_all_targets,
        short_duration_s=args.short_duration,
        longrun_duration_s=args.longrun_duration,
        jobs=args.jobs,
        reps=args.reps,
        longrun_reps=args.longrun_reps,
    )
    write_json(args.out_json, payload)
    write_csv(args.out_csv, payload["tasks"])
    write_markdown(args.out_md, payload)
    write_shell(args.out_sh, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
