#!/usr/bin/env python3
"""Audit whether a target is admissible as core FORMTRIG R2T evidence."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise SystemExit(f"failed to read {path}: {exc}") from exc


def line_hits(text: str, patterns: list[str], limit: int = 8) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    compiled = [re.compile(pattern) for pattern in patterns]
    for lineno, line in enumerate(text.splitlines(), 1):
        if any(pattern.search(line) for pattern in compiled):
            hits.append({"line": lineno, "text": line.rstrip()})
            if len(hits) >= limit:
                break
    return hits


def extract_target_id(binding_text: str, binding_path: Path) -> str:
    match = re.search(r"(?m)^\s*tc_id:\s*['\"]?([^'\"\s]+)", binding_text)
    if match:
        return match.group(1)
    return binding_path.stem


def seed_summary(seed_dir: Path | None) -> dict[str, Any]:
    if seed_dir is None:
        return {"provided": False}
    files = [path for path in sorted(seed_dir.rglob("*")) if path.is_file()]
    sizes = []
    for path in files:
        try:
            sizes.append(path.stat().st_size)
        except OSError:
            continue
    return {
        "provided": True,
        "path": str(seed_dir),
        "file_count": len(files),
        "min_size": min(sizes) if sizes else None,
        "max_size": max(sizes) if sizes else None,
        "sizes": sizes[:32],
    }


def add_flag(
    flags: list[dict[str, Any]],
    flag_id: str,
    severity: str,
    title: str,
    detail: str,
    evidence: list[dict[str, Any]] | None = None,
) -> None:
    flags.append(
        {
            "id": flag_id,
            "severity": severity,
            "title": title,
            "detail": detail,
            "evidence": evidence or [],
        }
    )


def audit(binding_path: Path, harness_path: Path | None, seed_dir: Path | None) -> dict[str, Any]:
    binding_text = read_text(binding_path)
    harness_text = read_text(harness_path) if harness_path is not None else ""
    target_id = extract_target_id(binding_text, binding_path)
    flags: list[dict[str, Any]] = []

    harness_lower = harness_text.lower()
    binding_lower = binding_text.lower()

    direct_alloc_switch = (
        ("fail_malloc_at" in harness_lower or "malloc_fail" in harness_lower)
        and "return null" in harness_lower
        and ("malloc_count ==" in harness_lower or "g_malloc_count ==" in harness_lower)
        and re.search(r"\b(buf|data|input)\s*\[\s*0\s*\]", harness_text) is not None
    )
    if direct_alloc_switch:
        add_flag(
            flags,
            "direct_input_allocation_failure_switch",
            "critical",
            "Harness exposes allocation failure as an input byte switch",
            "The harness appears to map input byte 0 to a malloc-failure index, "
            "then returns NULL when the allocation counter matches that value. "
            "This collapses the real R2T search into a small artificial knob.",
            line_hits(
                harness_text,
                [
                    r"fail_malloc_at",
                    r"malloc_count",
                    r"return NULL",
                    r"\bbuf\s*\[\s*0\s*\]",
                ],
                limit=16,
            ),
        )

    harness_binding = (
        "benchmarks/cve_harnesses" in binding_lower
        or "hook_malloc" in binding_lower
        or "harness" in binding_lower
    )
    if harness_binding:
        add_flag(
            flags,
            "binding_depends_on_harness_semantics",
            "high",
            "BindingSpec uses harness-level semantics",
            "At least one binding role is grounded in the replay harness rather "
            "than the vulnerable library's natural parser state. This may still "
            "be useful for smoke tests, but it is not admissible as core evidence "
            "that FORMTRIG solves natural binary-trigger guidance.",
            line_hits(
                binding_text,
                [
                    r"hook_malloc",
                    r"benchmarks/cve_harnesses",
                    r"harness",
                    r"input-selected",
                ],
            ),
        )

    one_byte_hint = (
        re.search(r"(?m)^\s*range_start:\s*0\s*$", binding_text) is not None
        and re.search(r"(?m)^\s*range_len:\s*1\s*$", binding_text) is not None
        and re.search(r"(?m)^\s*mutation_hint:\s*['\"]?set_byte", binding_text) is not None
        and re.search(r"(?m)^\s*mutation_value:\s*", binding_text) is not None
    )
    if one_byte_hint:
        add_flag(
            flags,
            "one_byte_terminal_mutation_hint",
            "high",
            "BindingSpec contains a one-byte set-byte mutation hint",
            "A one-byte mutation hint can be valid as a typed mutator hint, but "
            "combined with a harness allocation-failure switch it effectively "
            "names the terminal knob.",
            line_hits(
                binding_text,
                [
                    r"range_start:",
                    r"range_len:",
                    r"mutation_hint:",
                    r"mutation_value:",
                ],
            ),
        )

    seeds = seed_summary(seed_dir)
    if seeds.get("provided") and seeds.get("file_count") and seeds.get("max_size") is not None:
        max_size = int(seeds["max_size"])
        if max_size <= 2:
            add_flag(
                flags,
                "tiny_seed_space",
                "medium",
                "Seed corpus contains only tiny inputs",
                "Tiny RNT seeds are not invalid by themselves, but they are a "
                "warning sign when the trigger is also exposed through a direct "
                "one-byte harness control.",
                [{"path": seeds.get("path"), "max_size": max_size, "sizes": seeds.get("sizes")}],
            )

    severity_rank = {"info": 0, "medium": 1, "high": 2, "critical": 3}
    max_severity = max((severity_rank.get(flag["severity"], 0) for flag in flags), default=0)
    if any(flag["severity"] == "critical" for flag in flags):
        status = "inadmissible_core_evidence"
        summary = (
            "Not admissible as core FORMTRIG R2T evidence because the harness "
            "exposes an artificial trigger-control knob."
        )
    elif max_severity >= severity_rank["high"]:
        status = "review_required"
        summary = (
            "Requires manual review before it can be used as core FORMTRIG R2T "
            "evidence."
        )
    else:
        status = "admissible"
        summary = "No harness-bias pattern was detected by this static audit."

    recommendations = []
    if status != "admissible":
        recommendations.extend(
            [
                "Do not count this target as core evidence for solving natural R2T guidance.",
                "Keep it only as a native pipeline, BindingSpec, or crash-accounting sanity case.",
                "Replace it with targets where the input naturally drives parser state, length, magic, structure, or lifecycle constraints.",
            ]
        )

    return {
        "schema": "formtrig_harness_admissibility_v1",
        "target_id": target_id,
        "status": status,
        "core_evidence_allowed": status == "admissible",
        "summary": summary,
        "inputs": {
            "binding_spec": str(binding_path),
            "harness": str(harness_path) if harness_path is not None else None,
            "seed_dir": str(seed_dir) if seed_dir is not None else None,
        },
        "seed_summary": seeds,
        "flags": flags,
        "recommendations": recommendations,
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    lines = [
        f"# Harness Admissibility Audit: {report['target_id']}",
        "",
        f"- Status: `{report['status']}`",
        f"- Core evidence allowed: `{str(report['core_evidence_allowed']).lower()}`",
        f"- Summary: {report['summary']}",
        "",
        "## Flags",
        "",
    ]
    if not report["flags"]:
        lines.append("- None")
    for flag in report["flags"]:
        lines.append(f"- `{flag['severity']}` `{flag['id']}`: {flag['title']}")
        lines.append(f"  {flag['detail']}")
        for item in flag.get("evidence", []):
            if "line" in item:
                lines.append(f"  - line {item['line']}: `{item['text']}`")
            elif "path" in item:
                lines.append(f"  - seed path `{item['path']}`, max_size={item.get('max_size')}")
    if report["recommendations"]:
        lines.extend(["", "## Recommendations", ""])
        for recommendation in report["recommendations"]:
            lines.append(f"- {recommendation}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binding-spec", required=True, type=Path)
    parser.add_argument("--harness", type=Path)
    parser.add_argument("--seed-dir", type=Path)
    parser.add_argument("--out-json", type=Path)
    parser.add_argument("--out-md", type=Path)
    parser.add_argument(
        "--fail-on-inadmissible",
        action="store_true",
        help="return non-zero when the audit marks the target inadmissible",
    )
    args = parser.parse_args(argv)

    report = audit(args.binding_spec, args.harness, args.seed_dir)
    encoded = json.dumps(report, indent=2, sort_keys=True)
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(encoded + "\n", encoding="utf-8")
    else:
        print(encoded)
    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        write_markdown(report, args.out_md)
    if args.fail_on_inadmissible and report["status"] == "inadmissible_core_evidence":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
