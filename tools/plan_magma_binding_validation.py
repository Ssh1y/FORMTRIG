#!/usr/bin/env python3
"""Plan validation runs for Magma BindingSpec drafts.

The generated BindingSpecs are not endpoint evidence. This planner turns them
into concrete validation jobs when native Magma assets are available, and keeps
them explicitly blocked when a site map or executable target command is still
missing.
"""

from __future__ import annotations

import argparse
import csv
import json
import shlex
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DRAFTS = Path("artifacts/formtrig_native_readiness/magma_binding_drafts_20260616.json")
DEFAULT_OUT_JSON = Path("artifacts/formtrig_native_readiness/magma_binding_validation_worklist_20260616.json")
DEFAULT_OUT_MD = Path("artifacts/formtrig_native_readiness/magma_binding_validation_worklist_20260616.md")
DEFAULT_OUT_CSV = Path("artifacts/formtrig_native_readiness/magma_binding_validation_worklist_20260616.csv")
DEFAULT_OUT_SH = Path("artifacts/formtrig_native_readiness/magma_binding_validation_worklist_20260616.sh")
DEFAULT_RAW_ROOT = Path("artifacts/formtrig_native_readiness/raw")
DEFAULT_VALIDATION_ROOT = Path("artifacts/formtrig_native_readiness/binding_validation")


CSV_FIELDS = [
    "target_id",
    "project",
    "category",
    "runnable_now",
    "action",
    "binding_spec",
    "seed_dir",
    "site_map",
    "target_cwd",
    "target_cmd",
    "blockers",
    "command",
    "summary_command",
    "validation_record",
]


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def trim(value: str) -> str:
    return value.strip()


def manifest_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    return values


def load_assets(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    payload = read_json(path)
    if isinstance(payload, dict) and isinstance(payload.get("targets"), dict):
        return {
            str(target_id): asset
            for target_id, asset in payload["targets"].items()
            if isinstance(asset, dict)
        }
    if isinstance(payload, dict) and isinstance(payload.get("targets"), list):
        return {
            str(asset.get("target_id")): asset
            for asset in payload["targets"]
            if isinstance(asset, dict) and asset.get("target_id")
        }
    if isinstance(payload, list):
        return {
            str(asset.get("target_id")): asset
            for asset in payload
            if isinstance(asset, dict) and asset.get("target_id")
        }
    raise ValueError(f"unsupported assets JSON shape: {path}")


def repo_path(value: str, *, base: Path | None = None) -> Path:
    path = Path(value)
    if path.is_absolute() or base is None:
        return path
    return base / path


def has_todo(value: str) -> bool:
    return "TODO" in value or value.strip() == ""


def display_path(path: Path | str) -> str:
    return str(path)


def command_path(path: Path | str) -> str:
    value = Path(path)
    if value.is_absolute():
        return str(value)
    return str((Path.cwd() / value).resolve())


def category_for_runner(category: str) -> str:
    if category == "binary-state-null":
        return "binary-null"
    if category == "compound-sequence-lifecycle":
        return "lifecycle"
    if category == "equality/magic":
        return "equality"
    if category == "numeric-margin":
        return "numeric"
    return "generic"


def shell_join(args: list[str]) -> str:
    return " ".join(shlex.quote(str(arg)) for arg in args)


def parse_target_cmd(target_cmd: str) -> tuple[list[str], str | None]:
    if has_todo(target_cmd):
        return [], "target_cmd is missing or still contains TODO"
    try:
        argv = shlex.split(target_cmd)
    except ValueError as exc:
        return [], f"target_cmd cannot be parsed by shlex: {exc}"
    if not argv:
        return [], "target_cmd parses to an empty argv"
    return argv, None


def task_from_draft(
    draft: dict[str, Any],
    *,
    assets: dict[str, dict[str, Any]],
    duration_s: int,
    raw_root: Path,
    validation_root: Path,
    aflpp_dir: str,
    seed_preflight_max: int,
    seed_preflight_timeout: int,
) -> dict[str, Any]:
    target_id = str(draft.get("target_id") or "")
    asset = assets.get(target_id, {})
    manifest_template = Path(str(draft.get("manifest_template") or ""))
    manifest_dir = manifest_template.parent if manifest_template else Path(".")
    template = manifest_values(manifest_template)

    binding_spec = str(asset.get("binding_spec") or draft.get("binding_spec") or template.get("binding_spec") or "")
    seed_dir = str(asset.get("seed_dir") or template.get("seed_dir") or "")
    site_map = str(asset.get("site_map") or template.get("site_map") or "")
    target_cwd = str(asset.get("target_cwd") or template.get("target_cwd") or "")
    target_cmd = str(asset.get("target_cmd") or template.get("target_cmd") or "")
    target_site_ids = str(asset.get("target_site_ids") or template.get("target_site_ids") or "")
    category = str(asset.get("category") or draft.get("category") or template.get("category") or "generic")
    runner_category = str(asset.get("runner_category") or category_for_runner(category))
    duration = int(asset.get("duration_s") or asset.get("duration") or duration_s)
    target_aflpp_dir = str(asset.get("aflpp_dir") or aflpp_dir)

    resolved_binding_spec = repo_path(binding_spec, base=manifest_dir if binding_spec.startswith("..") else None)
    resolved_seed_dir = repo_path(seed_dir, base=manifest_dir if seed_dir.startswith("..") else None)
    resolved_site_map = repo_path(site_map, base=manifest_dir if site_map.startswith("..") else None)
    resolved_target_cwd = repo_path(target_cwd, base=manifest_dir if target_cwd.startswith("..") else None)

    blockers: list[str] = []
    if has_todo(binding_spec) or not resolved_binding_spec.exists():
        blockers.append(f"binding_spec is missing or unresolved: {binding_spec or '<empty>'}")
    if has_todo(seed_dir) or not resolved_seed_dir.exists():
        blockers.append(f"seed_dir is missing or unresolved: {seed_dir or '<empty>'}")
    if has_todo(site_map) or not resolved_site_map.exists():
        blockers.append(f"site_map is missing or unresolved: {site_map or '<empty>'}")
    if has_todo(target_cwd) or not resolved_target_cwd.exists():
        blockers.append(f"target_cwd is missing or unresolved: {target_cwd or '<empty>'}")

    target_argv, cmd_error = parse_target_cmd(target_cmd)
    if cmd_error:
        blockers.append(cmd_error)

    out_dir = Path(str(asset.get("out_dir") or raw_root / f"{target_id.lower()}_binding_validation_{duration}s"))
    validation_record = Path(
        str(
            asset.get("validation_record")
            or validation_root / f"{resolved_binding_spec.stem if binding_spec else target_id}.validation.json"
        )
    )

    sweep_args = [
        command_path("scripts/run_formtrig_binding_candidate_sweep.sh"),
        "--in",
        command_path(resolved_seed_dir),
        "--out",
        command_path(out_dir),
        "--target-bug",
        target_id,
        "--category",
        runner_category,
        "--site-map",
        command_path(resolved_site_map),
        "--candidate",
        command_path(resolved_binding_spec),
        "--candidate-kind",
        "binding-spec",
        "--duration",
        str(duration),
        "--seed-preflight",
        "require",
        "--seed-preflight-max",
        str(asset.get("seed_preflight_max") or seed_preflight_max),
        "--seed-preflight-timeout",
        str(asset.get("seed_preflight_timeout") or seed_preflight_timeout),
        "--aflpp-dir",
        command_path(target_aflpp_dir),
    ]
    if target_site_ids:
        sweep_args.extend(["--target-site-ids", target_site_ids])
    sweep_args.append("--")
    sweep_args.extend(target_argv)

    summary_args = [
        "python3",
        command_path("tools/summarize_binding_candidate_sweep.py"),
        "--summary-jsonl",
        command_path(out_dir / "summary.jsonl"),
        "--target-id",
        target_id,
        "--out",
        command_path(validation_record),
        "--out-md",
        command_path(validation_record.with_suffix(".md")),
        "--site-map",
        command_path(resolved_site_map),
    ]
    if binding_spec:
        summary_args.extend(["--binding-spec", command_path(resolved_binding_spec)])

    command = ""
    if not blockers:
        command = f"(cd {shlex.quote(command_path(resolved_target_cwd))} && {shell_join(sweep_args)})"
    summary_command = shell_join(summary_args) if not blockers else ""
    if command and summary_command:
        command = f"{command} && {summary_command}"

    return {
        "target_id": target_id,
        "project": str(draft.get("project") or ""),
        "program": str(draft.get("program") or ""),
        "category": category,
        "runner_category": runner_category,
        "action": "run_binding_candidate_sweep_then_summarize_validation",
        "duration_s": duration,
        "runnable_now": not blockers,
        "blockers": blockers,
        "binding_spec": display_path(resolved_binding_spec),
        "manifest_template": str(manifest_template),
        "seed_dir": display_path(resolved_seed_dir),
        "site_map": display_path(resolved_site_map),
        "target_cwd": display_path(resolved_target_cwd),
        "target_cmd": target_cmd,
        "target_site_ids": target_site_ids,
        "out_dir": str(out_dir),
        "validation_record": str(validation_record),
        "command": command,
        "summary_command": summary_command,
        "benefit_to_prove": (
            "Validate that this BindingSpec creates replay-stable, non-terminal "
            "pre-trigger guidance before spending endpoint comparison budget."
        ),
        "claim_boundary": "Validation is a gate; it is not FORMTRIG-vs-baseline efficacy evidence.",
        "next_step": (
            "Run the command, inspect the generated validation record, then rerun "
            "the hard-target and benefit-first planners."
            if not blockers
            else "Provide native Magma assets in --assets before running validation."
        ),
    }


def build_worklist(
    *,
    drafts_path: Path,
    assets_path: Path | None,
    duration_s: int,
    raw_root: Path,
    validation_root: Path,
    aflpp_dir: str,
    seed_preflight_max: int,
    seed_preflight_timeout: int,
) -> dict[str, Any]:
    drafts_payload = read_json(drafts_path)
    assets = load_assets(assets_path)
    tasks = [
        task_from_draft(
            draft,
            assets=assets,
            duration_s=duration_s,
            raw_root=raw_root,
            validation_root=validation_root,
            aflpp_dir=aflpp_dir,
            seed_preflight_max=seed_preflight_max,
            seed_preflight_timeout=seed_preflight_timeout,
        )
        for draft in drafts_payload.get("drafts", [])
    ]
    return {
        "schema": "formtrig_magma_binding_validation_worklist_v1",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "inputs": {
            "drafts": str(drafts_path),
            "assets": str(assets_path) if assets_path else "",
            "duration_s": duration_s,
            "raw_root": str(raw_root),
            "validation_root": str(validation_root),
        },
        "task_count": len(tasks),
        "runnable_now_count": sum(1 for task in tasks if task["runnable_now"]),
        "blocked_count": sum(1 for task in tasks if not task["runnable_now"]),
        "tasks": tasks,
    }


def write_csv(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS, lineterminator="\n")
        writer.writeheader()
        for task in payload["tasks"]:
            row = {field: task.get(field, "") for field in CSV_FIELDS}
            row["runnable_now"] = "yes" if task.get("runnable_now") else "no"
            row["blockers"] = "; ".join(task.get("blockers") or [])
            writer.writerow(row)


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Magma Binding Validation Worklist",
        "",
        "This is a validation worklist, not a performance-result table. A runnable",
        "task executes a short BindingSpec candidate sweep and then summarizes it",
        "into the existing `binding_validation` schema consumed by target planners.",
        "",
        f"Generated: `{payload['generated_at_utc']}`",
        f"Tasks: `{payload['task_count']}`; runnable now: `{payload['runnable_now_count']}`; blocked: `{payload['blocked_count']}`",
        "",
        "| target | category | runnable | blocker summary | validation record |",
        "| --- | --- | --- | --- | --- |",
    ]
    for task in payload["tasks"]:
        blockers = "; ".join(task.get("blockers") or [])
        lines.append(
            "| {target} | {category} | {runnable} | {blockers} | `{record}` |".format(
                target=task["target_id"],
                category=task["category"],
                runnable="yes" if task["runnable_now"] else "blocked",
                blockers=blockers or "none",
                record=task["validation_record"],
            )
        )
    lines.extend(["", "## Runnable Commands", ""])
    runnable = [task for task in payload["tasks"] if task["runnable_now"]]
    if not runnable:
        lines.append("No tasks are runnable until native Magma assets are supplied via `--assets`.")
    for task in runnable:
        lines.extend([f"### {task['target_id']}", "", f"```bash\n{task['command']}\n```", ""])
    lines.extend(["", "## Blocked Tasks", ""])
    for task in payload["tasks"]:
        if task["runnable_now"]:
            continue
        lines.append(f"### {task['target_id']}")
        for blocker in task.get("blockers") or []:
            lines.append(f"- {blocker}")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def write_shell(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# Generated Magma BindingSpec validation commands.",
        "# Blocked tasks are emitted as comments until native assets are provided.",
        "",
    ]
    for task in payload["tasks"]:
        lines.append(f"# {task['target_id']} {task['action']}")
        lines.append(f"# benefit: {task['benefit_to_prove']}")
        if task["runnable_now"]:
            lines.append(task["command"])
        else:
            lines.append("# blocked: " + "; ".join(task.get("blockers") or []))
            lines.append("# next: provide site_map, target_cwd, and target_cmd in a validation assets JSON")
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    path.chmod(0o755)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--drafts", type=Path, default=DEFAULT_DRAFTS)
    parser.add_argument("--assets", type=Path)
    parser.add_argument("--duration", type=int, default=600)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--validation-root", type=Path, default=DEFAULT_VALIDATION_ROOT)
    parser.add_argument("--aflpp-dir", default="experiments/aflplusplus/AFLplusplus")
    parser.add_argument("--seed-preflight-max", type=int, default=32)
    parser.add_argument("--seed-preflight-timeout", type=int, default=5)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    parser.add_argument("--out-csv", type=Path, default=DEFAULT_OUT_CSV)
    parser.add_argument("--out-sh", type=Path, default=DEFAULT_OUT_SH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_worklist(
        drafts_path=args.drafts,
        assets_path=args.assets,
        duration_s=args.duration,
        raw_root=args.raw_root,
        validation_root=args.validation_root,
        aflpp_dir=args.aflpp_dir,
        seed_preflight_max=args.seed_preflight_max,
        seed_preflight_timeout=args.seed_preflight_timeout,
    )
    write_json(args.out_json, payload)
    write_markdown(args.out_md, payload)
    write_csv(args.out_csv, payload)
    write_shell(args.out_sh, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
