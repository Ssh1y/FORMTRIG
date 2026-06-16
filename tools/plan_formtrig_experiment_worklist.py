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


def strongest_comparison(comparisons: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not comparisons:
        return None

    def score(payload: dict[str, Any]) -> tuple[int, int, str]:
        analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
        benefit = payload.get("benefit_readout") if isinstance(payload.get("benefit_readout"), dict) else {}
        verdict = str(analysis.get("verdict") or "")
        has_longrun = int(bool(analysis.get("longrun_10m_confirmation") or payload.get("longrun_10m_confirmation")))
        benefit_count = len(benefit.get("primary_benefits") or [])
        positive = int("positive" in verdict or benefit_count > 0)
        return (positive, has_longrun, str(payload.get("_comparison_path") or ""))

    return max(comparisons, key=score)


def is_demoted_control(row: dict[str, Any]) -> bool:
    lane = str(row.get("lane") or "")
    status = str(row.get("status") or "")
    disposition = str(row.get("existing_disposition") or "")
    return lane in DEMOTED_CONTROL_LANES or status in CONTROL_STATUSES or disposition in DEMOTE_DISPOSITIONS


def is_non_main_budget(row: dict[str, Any]) -> bool:
    lane = str(row.get("lane") or "")
    return is_demoted_control(row) or lane in NON_MAIN_BUDGET_LANES


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


def comparison_summary(comparison: dict[str, Any] | None) -> dict[str, Any]:
    if not comparison:
        return {
            "verdict": "",
            "primary_benefits": [],
            "design_evidence": [],
            "blocked_claims": [],
            "longrun_10m_confirmation": None,
        }
    analysis = comparison.get("analysis") if isinstance(comparison.get("analysis"), dict) else {}
    benefit = comparison.get("benefit_readout") if isinstance(comparison.get("benefit_readout"), dict) else {}
    return {
        "verdict": str(analysis.get("verdict") or ""),
        "primary_benefits": as_list(benefit.get("primary_benefits"))[:4],
        "design_evidence": as_list(benefit.get("design_evidence"))[:6],
        "blocked_claims": as_list(benefit.get("blocked_claims"))[:4],
        "longrun_10m_confirmation": analysis.get("longrun_10m_confirmation")
        or comparison.get("longrun_10m_confirmation"),
    }


def shell_join(args: list[str]) -> str:
    return " ".join(shlex.quote(arg) for arg in args)


def magma_baseline_command(target_id: str, duration_s: int, jobs: int, reps: int) -> str:
    args = [
        "scripts/run_magma_baselines.sh",
        "--target-id",
        target_id,
        "--durations",
        str(duration_s),
        "--jobs",
        str(jobs),
    ]
    if reps > 1:
        args.extend(["--reps", str(reps)])
    return shell_join(args)


def formtrig_manifest_batch_command(manifest_list: str, duration_s: int, jobs: int) -> str:
    return shell_join(
        [
            "scripts/run_formtrig_manifest_batch.sh",
            "--manifest-list",
            manifest_list,
            "--duration",
            str(duration_s),
            "--jobs",
            str(jobs),
            "--continue-on-fail",
        ]
    )


def longrun_task(
    row: dict[str, Any],
    comparison: dict[str, Any] | None,
    *,
    duration_s: int,
    reps: int,
    jobs: int,
) -> dict[str, Any]:
    summary = comparison_summary(comparison)
    target_id = str(row.get("target_id") or "")
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
    if target_id == "LIBARCHIVE_2936" and runner_path.exists():
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
    return {
        "priority": priority_for(row),
        "rank": int(row.get("rank") or 0),
        "target_id": target_id,
        "source": str(row.get("source") or ""),
        "project": str(row.get("project") or ""),
        "category": category_text(row),
        "lane": str(row.get("lane") or ""),
        "action": "extend_matched_longrun",
        "duration_s": duration_s,
        "repetitions": reps,
        "benefit_to_prove": (
            "Confirm that the current first-_T speedup and lower execution cost "
            f"persist in {reps} matched {duration_s}s repetitions."
        ),
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
        "runnable_now": bool(command),
        "post_unblock_commands": post_unblock_commands,
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
    *,
    short_duration_s: int,
    longrun_duration_s: int,
    jobs: int,
    reps: int,
    longrun_reps: int,
) -> dict[str, Any]:
    target_id = str(row.get("target_id") or "")
    comparison = strongest_comparison(comparisons.get(target_id, []))
    disposition = str(row.get("existing_disposition") or "")
    lane = str(row.get("lane") or "")
    if disposition == "candidate_extend_longruns":
        return longrun_task(row, comparison, duration_s=longrun_duration_s, reps=longrun_reps, jobs=jobs)
    if lane == "binding_spec_first":
        return binding_spec_first_task(row, comparison, short_duration_s=short_duration_s, jobs=jobs, reps=reps)
    if lane == "binding_validation_first":
        return validation_first_task(row, comparison, short_duration_s=short_duration_s, jobs=jobs, reps=reps)
    return short_triage_task(row, comparison, short_duration_s=short_duration_s, jobs=jobs, reps=reps)


def build_worklist(
    queue_path: Path,
    comparison_root: Path,
    *,
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
    tasks: list[dict[str, Any]] = []
    skipped_controls: list[dict[str, Any]] = [
        {
            "rank": row.get("rank"),
            "target_id": row.get("target_id"),
            "lane": row.get("lane"),
            "status": row.get("status"),
            "existing_disposition": row.get("existing_disposition"),
            "reason": "control_or_negative_not_main_budget",
            "next_action": row.get("next_action"),
        }
        for row in all_rows
        if is_demoted_control(row)
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
        if is_non_main_budget(row):
            continue
        tasks.append(
            task_for_row(
                row,
                comparisons,
                short_duration_s=short_duration_s,
                longrun_duration_s=longrun_duration_s,
                jobs=jobs,
                reps=reps,
                longrun_reps=longrun_reps,
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
        "| priority | rank | target | source | action | runnable | benefit to prove |",
        "| --- | ---: | --- | --- | --- | --- | --- |",
    ]
    for task in tasks:
        lines.append(
            "| {priority} | {rank} | {target_id} | {source} | {action} | {runnable} | {benefit} |".format(
                priority=md_escape(task.get("priority")),
                rank=task.get("rank", ""),
                target_id=md_escape(task.get("target_id")),
                source=md_escape(task.get("source")),
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
                "| rank | target | lane | disposition/status | reason |",
                "| ---: | --- | --- | --- | --- |",
            ]
        )
        for row in payload["skipped_controls"]:
            disposition = row.get("existing_disposition") or row.get("status") or ""
            lines.append(
                "| {rank} | {target_id} | {lane} | {disp} | {reason} |".format(
                    rank=row.get("rank", ""),
                    target_id=md_escape(row.get("target_id")),
                    lane=md_escape(row.get("lane")),
                    disp=md_escape(disposition),
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
