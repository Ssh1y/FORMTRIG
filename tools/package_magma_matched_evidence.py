#!/usr/bin/env python3
"""Package small auditable evidence for a matched Magma comparison.

The raw AFL++ queues are intentionally not copied. This tool collects the
summary, gate, monitor, and per-run metadata files needed to audit endpoint
claims and baseline guidance-gap claims from a completed matched run.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


FORMTRIG_DEFAULT_FILES = [
    "formtrig_summary.json",
    "formtrig_diagnosis.json",
    "formtrig_lift_feature_audit.json",
    "formtrig_terminal_monitor.json",
    "fuzzer_stats",
]


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def copy_if_exists(src: Path, dst: Path, copied: list[str], missing: list[str]) -> None:
    if not src.exists():
        missing.append(str(src))
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    copied.append(str(dst))


def copy_baseline_evidence(
    baseline_dir: Path,
    evidence_dir: Path,
    copied: list[str],
    missing: list[str],
) -> None:
    out = evidence_dir / "baselines"
    for name in ("summary.json", "summary.tsv", "run_metadata.txt"):
        copy_if_exists(baseline_dir / name, out / name, copied, missing)
    runs_dir = baseline_dir / "runs"
    if not runs_dir.is_dir():
        missing.append(str(runs_dir))
        return
    for run_dir in sorted(path for path in runs_dir.iterdir() if path.is_dir()):
        for name in ("run_record.json", "events.jsonl", "status.json", "run_config.json"):
            copy_if_exists(run_dir / name, out / "runs" / run_dir.name / name, copied, missing)


def copy_formtrig_evidence(
    formtrig_dir: Path,
    gate_dir: Path,
    evidence_dir: Path,
    copied: list[str],
    missing: list[str],
) -> None:
    out = evidence_dir / "formtrig"
    for name in ("batch_summary.csv", "batch_summary.jsonl"):
        copy_if_exists(formtrig_dir / name, out / name, copied, missing)
    for name in ("gate_summary.csv", "gate_summary.jsonl", "gate_report.md"):
        copy_if_exists(gate_dir / name, out / name, copied, missing)
    for run_dir in sorted(path for path in formtrig_dir.iterdir() if path.is_dir()):
        default_dir = run_dir / "out" / "default"
        run_out = out / "runs" / run_dir.name
        copy_if_exists(run_dir / "out" / "formtrig_mutation_hook.json", run_out / "formtrig_mutation_hook.json", copied, missing)
        for name in FORMTRIG_DEFAULT_FILES:
            copy_if_exists(default_dir / name, run_out / name, copied, missing)


def copy_guidance_gap(
    guidance_dir: Path,
    evidence_dir: Path,
    copied: list[str],
    missing: list[str],
) -> None:
    out = evidence_dir / "guidance_gap"
    for name in (
        "baseline_guidance_gap.json",
        "baseline_guidance_gap.md",
        "baseline_guidance_gap_runs.tsv",
    ):
        copy_if_exists(guidance_dir / name, out / name, copied, missing)


def copy_live_status(
    run_root: Path,
    evidence_dir: Path,
    copied: list[str],
    missing: list[str],
) -> None:
    out = evidence_dir / "live_status"
    for name in ("live_status.json", "live_status.md"):
        copy_if_exists(run_root / name, out / name, copied, missing)


def comparison_summary(comparison_dir: Path) -> dict[str, Any]:
    path = comparison_dir / "comparison.json"
    if not path.exists():
        return {}
    payload = read_json(path)
    analysis = payload.get("analysis") if isinstance(payload.get("analysis"), dict) else {}
    strength = (
        analysis.get("experiment_strength")
        if isinstance(analysis.get("experiment_strength"), dict)
        else {}
    )
    benefit = payload.get("benefit_readout") if isinstance(payload.get("benefit_readout"), dict) else {}
    return {
        "best_formtrig_trigger_time_s": analysis.get("best_formtrig_trigger_time_s"),
        "blocked_claims": benefit.get("blocked_claims") or [],
        "comparison_id": payload.get("comparison_id"),
        "main_claim_strength": strength.get("main_claim_strength"),
        "matched_baseline_count": analysis.get("matched_baseline_count"),
        "primary_benefits": benefit.get("primary_benefits") or [],
        "target_id": payload.get("target_id"),
        "verdict": analysis.get("verdict"),
    }


def write_index(
    path: Path,
    *,
    summary: dict[str, Any],
    target_id: str,
    duration: int,
    reps: int,
    run_root: Path,
    copied: list[str],
    missing: list[str],
) -> None:
    lines = [
        f"# {target_id} {duration}s x{reps} Matched Evidence Bundle",
        "",
        "This directory contains the small, auditable evidence used by the matched",
        "FORMTRIG-vs-baseline comparison. Full AFL++ raw queues are intentionally",
        "left in the run directory and are not copied here.",
        "",
        "## Comparison",
        "",
        f"- target: `{summary.get('target_id') or target_id}`",
        f"- comparison id: `{summary.get('comparison_id') or 'unknown'}`",
        f"- verdict: `{summary.get('verdict') or 'unknown'}`",
        f"- main claim strength: `{summary.get('main_claim_strength') or 'unknown'}`",
        f"- matched baseline runs: `{summary.get('matched_baseline_count')}`",
        f"- best FORMTRIG first `_T`: `{summary.get('best_formtrig_trigger_time_s')}`",
        f"- raw run root: `{run_root}`",
        "",
        "## Primary Benefits",
        "",
    ]
    benefits = summary.get("primary_benefits") or []
    if benefits:
        lines.extend(f"- {benefit}" for benefit in benefits)
    else:
        lines.append("- none recorded")
    lines.extend(["", "## Claim Boundary", ""])
    blocked = summary.get("blocked_claims") or []
    if blocked:
        lines.extend(f"- {claim}" for claim in blocked)
    else:
        lines.append("- no blocked claims recorded by the comparison package")
    lines.extend(
        [
            "",
            "## Files",
            "",
            "- `baselines/`: baseline summaries and per-run monitor/run records.",
            "- `formtrig/`: FORMTRIG batch summary, gate summary, and per-rep stats.",
            "- `guidance_gap/`: baseline no-guidance analysis and per-run table.",
            "- `live_status/`: non-final live snapshot of FORMTRIG and baseline `_R/_T` state.",
            "",
            "## Packaging Status",
            "",
            f"- copied files: `{len(copied)}`",
            f"- missing optional files: `{len(missing)}`",
        ]
    )
    if missing:
        lines.extend(["", "Missing optional files:"])
        lines.extend(f"- `{item}`" for item in missing[:40])
        if len(missing) > 40:
            lines.append(f"- ... {len(missing) - 40} more")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--duration", required=True, type=int)
    parser.add_argument("--reps", required=True, type=int)
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--comparison-dir", required=True, type=Path)
    parser.add_argument("--baseline-dir", required=True, type=Path)
    parser.add_argument("--formtrig-dir", required=True, type=Path)
    parser.add_argument("--gate-dir", required=True, type=Path)
    parser.add_argument("--guidance-dir", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    evidence_dir = args.comparison_dir / "evidence"
    if evidence_dir.exists():
        shutil.rmtree(evidence_dir)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    missing: list[str] = []
    copy_baseline_evidence(args.baseline_dir, evidence_dir, copied, missing)
    copy_formtrig_evidence(args.formtrig_dir, args.gate_dir, evidence_dir, copied, missing)
    copy_guidance_gap(args.guidance_dir, evidence_dir, copied, missing)
    copy_live_status(args.run_root, evidence_dir, copied, missing)
    write_index(
        evidence_dir / "EVIDENCE.md",
        summary=comparison_summary(args.comparison_dir),
        target_id=args.target_id,
        duration=args.duration,
        reps=args.reps,
        run_root=args.run_root,
        copied=copied,
        missing=missing,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
