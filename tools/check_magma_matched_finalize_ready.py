#!/usr/bin/env python3
"""Check whether a sharded Magma matched run is safe to merge and finalize."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def active_run_rows(path: Path) -> list[dict[str, Any]]:
    payload = read_json(path)
    if isinstance(payload, list):
        return [row for row in payload if isinstance(row, dict)]
    rows = payload.get("runs") if isinstance(payload, dict) else None
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def find_active_run(path: Path, target_id: str) -> dict[str, Any]:
    matches = [row for row in active_run_rows(path) if str(row.get("target_id") or "") == target_id]
    if not matches:
        raise SystemExit(f"no active run for target: {target_id}")
    matches.sort(
        key=lambda row: (
            str(row.get("launched_at_utc") or row.get("generated_at_utc") or ""),
            str(row.get("run_root") or ""),
        )
    )
    return matches[-1]


def split_csv(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [part.strip() for part in str(value or "").replace(",", " ").split() if part.strip()]


def run_metadata(run_root: Path) -> dict[str, Any]:
    path = run_root / "run_metadata.json"
    if not path.exists():
        return {}
    payload = read_json(path)
    return payload if isinstance(payload, dict) else {}


def expected_run_names(metadata: dict[str, Any], active_run: dict[str, Any]) -> list[str]:
    baselines = split_csv(metadata.get("baselines") or active_run.get("baselines"))
    duration = int_value(metadata.get("duration_s") or active_run.get("duration_s"))
    reps = int_value(metadata.get("reps") or active_run.get("repetitions") or active_run.get("reps"))
    if not baselines:
        raise SystemExit("could not determine baseline families from metadata or active run")
    if duration <= 0:
        raise SystemExit("could not determine baseline duration")
    if reps <= 0:
        raise SystemExit("could not determine repetition count")
    return [
        f"{baseline}_{duration}s_rep{rep}"
        for baseline in baselines
        for rep in range(1, reps + 1)
    ]


def run_dir_record(run_dir: Path, source_root: Path) -> dict[str, Any]:
    return {
        "run": run_dir.name,
        "source_root": str(source_root),
        "run_dir": str(run_dir),
        "has_run_record": (run_dir / "run_record.json").is_file(),
        "has_status": (run_dir / "status.json").is_file(),
    }


def collect_run_dirs(baseline_roots: list[Path]) -> dict[str, list[dict[str, Any]]]:
    collected: dict[str, list[dict[str, Any]]] = {}
    for root in baseline_roots:
        runs_dir = root / "runs"
        if not runs_dir.is_dir():
            continue
        for run_dir in sorted(path for path in runs_dir.iterdir() if path.is_dir()):
            collected.setdefault(run_dir.name, []).append(run_dir_record(run_dir, root))
    return collected


def select_runs(
    collected: dict[str, list[dict[str, Any]]],
    *,
    duplicate_policy: str,
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    selected: dict[str, dict[str, Any]] = {}
    duplicates: list[dict[str, Any]] = []
    for run_name, records in sorted(collected.items()):
        if duplicate_policy == "refuse" and len(records) > 1:
            duplicates.append({"run": run_name, "policy": duplicate_policy, "records": records})
            continue
        selected_record = records[0] if duplicate_policy == "prefer-earlier" else records[-1]
        selected[run_name] = selected_record
        if len(records) > 1:
            duplicates.append(
                {
                    "run": run_name,
                    "policy": duplicate_policy,
                    "kept": selected_record,
                    "discarded": [record for record in records if record is not selected_record],
                }
            )
    return selected, duplicates


def summarize(
    *,
    active_runs_path: Path,
    target_id: str,
    duplicate_policy: str,
) -> dict[str, Any]:
    active_run = find_active_run(active_runs_path, target_id)
    run_root = Path(str(active_run.get("run_root") or ""))
    if not run_root:
        raise SystemExit("active run has no run_root")
    metadata = run_metadata(run_root)
    baseline_roots = [Path(str(root)) for root in active_run.get("baseline_roots") or [] if str(root)]
    if not baseline_roots:
        baseline_roots = [run_root / "baselines"]
    expected = expected_run_names(metadata, active_run)
    collected = collect_run_dirs(baseline_roots)
    selected, duplicates = select_runs(collected, duplicate_policy=duplicate_policy)
    missing = [name for name in expected if name not in selected]
    incomplete = [
        selected[name]
        for name in expected
        if name in selected and not selected[name].get("has_run_record")
    ]
    unexpected = sorted(name for name in selected if name not in set(expected))
    ready = not missing and not incomplete and not (
        duplicate_policy == "refuse" and duplicates
    )

    merge_out = run_root / "merged_baselines"
    guidance_out = str(active_run.get("guidance_out") or "")
    comparison_out = str(active_run.get("comparison_out") or "")
    merge_command = [
        "python3",
        "tools/merge_magma_baseline_roots.py",
        "--out",
        str(merge_out),
    ]
    for root in baseline_roots:
        merge_command.extend(["--source", str(root)])
    merge_command.extend(["--duplicate-policy", duplicate_policy])
    finalize_command: list[str] = []
    if guidance_out and comparison_out:
        finalize_command = [
            "scripts/finalize_magma_matched_run.sh",
            "--run-root",
            str(run_root),
            "--baseline-dir",
            str(merge_out),
            "--guidance-out",
            guidance_out,
            "--comparison-out",
            comparison_out,
        ]

    return {
        "analysis_time_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "target_id": target_id,
        "ready_to_finalize": ready,
        "duplicate_policy": duplicate_policy,
        "run_root": str(run_root),
        "baseline_roots": [str(root) for root in baseline_roots],
        "expected_run_count": len(expected),
        "selected_run_count": sum(1 for name in expected if name in selected),
        "complete_selected_run_count": sum(
            1
            for name in expected
            if name in selected and selected[name].get("has_run_record")
        ),
        "missing_runs": missing,
        "incomplete_runs": incomplete,
        "duplicate_runs": duplicates,
        "unexpected_runs": unexpected,
        "merge_command": merge_command,
        "finalize_command": finalize_command,
        "claim_boundary": (
            "ready_to_finalize only checks baseline run-record completeness and "
            "duplicate resolution; final claims still require finalize output review"
        ),
    }


def to_markdown(payload: dict[str, Any]) -> str:
    lines = [
        f"# Magma Matched Finalize Readiness: {payload['target_id']}",
        "",
        f"- ready to finalize: `{str(payload['ready_to_finalize']).lower()}`",
        f"- expected runs: `{payload['expected_run_count']}`",
        f"- selected runs: `{payload['selected_run_count']}`",
        f"- complete selected runs: `{payload['complete_selected_run_count']}`",
        f"- duplicate policy: `{payload['duplicate_policy']}`",
        f"- boundary: {payload['claim_boundary']}",
        "",
    ]
    if payload["missing_runs"]:
        lines.extend(["## Missing Runs", ""])
        lines.extend(f"- `{name}`" for name in payload["missing_runs"])
        lines.append("")
    if payload["incomplete_runs"]:
        lines.extend(["## Incomplete Runs", ""])
        lines.extend(
            f"- `{row['run']}` from `{row['source_root']}` lacks `run_record.json`"
            for row in payload["incomplete_runs"]
        )
        lines.append("")
    if payload["duplicate_runs"]:
        lines.extend(["## Duplicate Runs", ""])
        for duplicate in payload["duplicate_runs"]:
            kept = duplicate.get("kept") or {}
            lines.append(
                f"- `{duplicate['run']}` policy=`{duplicate['policy']}` kept=`{kept.get('source_root', '')}`"
            )
        lines.append("")
    lines.extend(["## Commands", ""])
    lines.append("```bash")
    lines.append(" ".join(payload["merge_command"]))
    if payload["finalize_command"]:
        lines.append(" ".join(payload["finalize_command"]))
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--active-runs", required=True, type=Path)
    parser.add_argument("--target-id", required=True)
    parser.add_argument(
        "--duplicate-policy",
        choices=["refuse", "prefer-earlier", "prefer-later"],
        default="prefer-later",
    )
    parser.add_argument("--out-json", type=Path)
    parser.add_argument("--out-md", type=Path)
    parser.add_argument(
        "--fail-if-not-ready",
        action="store_true",
        help="exit non-zero when ready_to_finalize is false",
    )
    parser.add_argument("--format", choices=["json", "md"], default="md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = summarize(
        active_runs_path=args.active_runs,
        target_id=args.target_id,
        duplicate_policy=args.duplicate_policy,
    )
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(to_markdown(payload), encoding="utf-8")
    if args.format == "json":
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(to_markdown(payload), end="")
    if args.fail_if_not_ready and not payload["ready_to_finalize"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
