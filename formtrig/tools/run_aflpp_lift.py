#!/usr/bin/env python3
"""Run AFL++ with native FORMTRIG lift guidance.

The native runtime consumes `FORMTRIG_LIFT_SPEC`, while AFL++ consumes the
FORMTRIG shared-memory signal. This wrapper connects those pieces: it compiles
trigger-progress graphs into an external lift spec, then launches AFL++ with
only the environment needed for native FORMTRIG guidance.
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from audit_lift_bindings import graph_binding_audit, write_runtime_template
from compile_lift_spec import compile_graph, load_runtime_map, parse_site_map


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compile FORMTRIG lift spec and run AFL++ with native guidance",
        allow_abbrev=False,
    )
    parser.add_argument("--afl-fuzz", required=True, type=Path, help="Path to afl-fuzz")
    parser.add_argument(
        "--trigger-graph",
        action="append",
        required=True,
        type=Path,
        help="Trigger-progress graph JSON. May be passed multiple times.",
    )
    parser.add_argument("--runtime-map", type=Path, help="External runtime binding JSON")
    parser.add_argument("--site-map", type=Path, help="FORMTRIG_SITE_MAP output")
    parser.add_argument(
        "--source-root",
        action="append",
        default=[],
        type=Path,
        help=(
            "External source root used by the lift compiler to relocate stale "
            "or generated-source TCIR locations."
        ),
    )
    parser.add_argument(
        "--spec-out",
        type=Path,
        help="Write FORMTRIG_LIFT_SPEC here. Defaults to a file in --work-dir.",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        help="Write structured lift-spec compile report here.",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        help="Directory for generated spec/report when explicit paths are omitted.",
    )
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Additional environment variable for afl-fuzz/target.",
    )
    parser.add_argument(
        "--no-comments",
        action="store_true",
        help="Emit only runtime spec lines, without compiler comments.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compile spec and print command/env JSON without executing afl-fuzz.",
    )
    parser.add_argument(
        "--compile-only",
        action="store_true",
        help="Compile spec/report and exit without constructing an AFL++ command.",
    )
    parser.add_argument(
        "--allow-no-progress-rules",
        action="store_true",
        help="Allow AFL++ launch when the compiled spec has no progress rules.",
    )
    parser.add_argument(
        "--binding-audit-json",
        type=Path,
        help="Write native binding readiness audit for the trigger graph(s).",
    )
    parser.add_argument(
        "--binding-template-out",
        type=Path,
        help="Write a runtime-map template for missing graph bindings.",
    )
    parser.add_argument(
        "--require-binding-ready",
        action="store_true",
        help="Refuse launch if any binding audit is not fully ready.",
    )
    parser.add_argument(
        "afl_args",
        nargs=argparse.REMAINDER,
        help="AFL++ arguments after --, including the target command.",
    )
    return parser


def normalize_remainder(args: List[str]) -> List[str]:
    if args and args[0] == "--":
        return args[1:]
    return args


def parse_env_assignments(assignments: List[str]) -> Dict[str, str]:
    out = {}  # type: Dict[str, str]
    for assignment in assignments:
        key, sep, value = assignment.partition("=")
        if not sep or not key:
            raise ValueError(f"--env expects KEY=VALUE, got {assignment!r}")
        out[key] = value
    return out


def default_work_dir() -> Path:
    return Path(tempfile.mkdtemp(prefix="formtrig_aflpp_lift_"))


def compile_lift_spec(
    graph_paths: List[Path],
    runtime_map_path: Optional[Path],
    site_map_path: Optional[Path],
    spec_out: Path,
    report_json: Optional[Path],
    *,
    include_comments: bool,
    source_roots: List[Path],
) -> Dict[str, Any]:
    runtime_map = load_runtime_map(runtime_map_path)
    site_map = parse_site_map(site_map_path)

    all_lines = []  # type: List[str]
    reports = []  # type: List[Dict[str, Any]]
    total_rules = 0
    progress_rules = 0
    range_rules = 0
    for graph_path in graph_paths:
        lines, report = compile_graph(
            graph_path,
            runtime_map,
            site_map,
            include_comments=include_comments,
            source_roots=source_roots,
        )
        if all_lines and include_comments:
            all_lines.append("")
        all_lines.extend(lines)
        reports.append(report)
        total_rules += int(report.get("rules", 0))
        progress_rules += int(report.get("progress_rules", 0))
        range_rules += int(report.get("range_rules", 0))

    spec_out.parent.mkdir(parents=True, exist_ok=True)
    spec_out.write_text("\n".join(all_lines) + ("\n" if all_lines else ""))

    report = {
        "spec": str(spec_out),
        "rules": total_rules,
        "progress_rules": progress_rules,
        "range_rules": range_rules,
        "graphs": reports,
    }
    if report_json is not None:
        report_json.parent.mkdir(parents=True, exist_ok=True)
        report_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def write_binding_audit(
    graph_paths: List[Path],
    runtime_map_path: Optional[Path],
    site_map_path: Optional[Path],
    audit_json: Optional[Path],
    template_out: Optional[Path],
    source_roots: List[Path],
    *,
    force: bool = False,
) -> Optional[Dict[str, Any]]:
    if audit_json is None and template_out is None and not force:
        return None
    runtime_map = load_runtime_map(runtime_map_path)
    site_map = parse_site_map(site_map_path)
    audits = [
        graph_binding_audit(graph, runtime_map, site_map, source_roots=source_roots)
        for graph in graph_paths
    ]
    report = {
        "graphs": audits,
        "summary": {
            "graphs": len(audits),
            "runnable": sum(1 for item in audits if item["runnable"]),
            "mutation_ready": sum(1 for item in audits if item["mutation_ready"]),
            "blocked_no_progress": sum(
                1 for item in audits if item["status"] == "blocked_no_progress"
            ),
        },
    }
    if audit_json is not None:
        audit_json.parent.mkdir(parents=True, exist_ok=True)
        audit_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    if template_out is not None:
        write_runtime_template(template_out, audits)
    return report


def collect_progress_site_ids(report: Dict[str, Any]) -> List[int]:
    site_ids = []  # type: List[int]
    for graph_report in report.get("graphs", []):
        if not isinstance(graph_report, dict):
            continue
        for raw in graph_report.get("progress_site_ids", []):
            try:
                site_id = int(raw)
            except (TypeError, ValueError):
                continue
            if site_id <= 0 or site_id in site_ids:
                continue
            site_ids.append(site_id)
    return site_ids


def configure_graph_driven_reach(env: Dict[str, str], report: Dict[str, Any]) -> None:
    site_ids = collect_progress_site_ids(report)
    if not site_ids:
        return
    if not env.get("FORMTRIG_TARGET_SITE_IDS"):
        env["FORMTRIG_TARGET_SITE_IDS"] = ",".join(str(site_id) for site_id in site_ids)
    env.setdefault("FORMTRIG_SOURCE_OBJECTIVE", "1")
    env.setdefault("FORMTRIG_SOURCE_SITE_REACH", "1")


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    afl_args = normalize_remainder(args.afl_args)
    if not args.compile_only and not afl_args:
        raise SystemExit("missing AFL++ arguments after --")

    work_dir = args.work_dir or default_work_dir()
    spec_out = args.spec_out or (work_dir / "formtrig.lift.spec")
    report_json = args.report_json or (work_dir / "formtrig_lift_report.json")

    report = compile_lift_spec(
        args.trigger_graph,
        args.runtime_map,
        args.site_map,
        spec_out,
        report_json,
        include_comments=not args.no_comments,
        source_roots=args.source_root,
    )
    binding_audit = write_binding_audit(
        args.trigger_graph,
        args.runtime_map,
        args.site_map,
        args.binding_audit_json,
        args.binding_template_out,
        args.source_root,
        force=args.require_binding_ready,
    )

    if args.require_binding_ready and binding_audit is not None:
        not_ready = [
            item
            for item in binding_audit.get("graphs", [])
            if isinstance(item, dict) and item.get("status") != "ready"
        ]
        if not_ready:
            details = ", ".join(
                f"{item.get('target_id')}={item.get('status')}" for item in not_ready
            )
            raise SystemExit(
                "binding audit is not ready; refusing AFL++ launch: " + details
            )

    if args.compile_only:
        payload = dict(report)
        if binding_audit is not None:
            payload["binding_audit"] = binding_audit
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0
    if report["progress_rules"] <= 0 and not args.allow_no_progress_rules:
        details = ""
        if args.binding_audit_json or args.binding_template_out:
            detail_items = []
            if args.binding_audit_json:
                detail_items.append(f"audit={args.binding_audit_json}")
            if args.binding_template_out:
                detail_items.append(f"template={args.binding_template_out}")
            details = " (" + ", ".join(detail_items) + ")"
        raise SystemExit(
            "compiled lift spec has no progress rules; refusing AFL++ launch "
            "(use --allow-no-progress-rules to override)" + details
        )

    env_override = parse_env_assignments(args.env)
    env = os.environ.copy()
    env.update(env_override)
    env.setdefault("FORMTRIG_AFLPP", "1")
    env["FORMTRIG_LIFT_SPEC"] = str(spec_out.resolve())
    configure_graph_driven_reach(env, report)

    cmd = [str(args.afl_fuzz), *afl_args]
    dry_run = {
        "cmd": cmd,
        "env": {
            "FORMTRIG_AFLPP": env["FORMTRIG_AFLPP"],
            "FORMTRIG_LIFT_SPEC": env["FORMTRIG_LIFT_SPEC"],
            "FORMTRIG_SOURCE_OBJECTIVE": env.get("FORMTRIG_SOURCE_OBJECTIVE", ""),
            "FORMTRIG_SOURCE_SITE_REACH": env.get("FORMTRIG_SOURCE_SITE_REACH", ""),
            "FORMTRIG_TARGET_SITE_IDS": env.get("FORMTRIG_TARGET_SITE_IDS", ""),
            **env_override,
        },
        "report": report,
    }
    if binding_audit is not None:
        dry_run["binding_audit"] = binding_audit

    if args.dry_run:
        print(json.dumps(dry_run, indent=2, sort_keys=True))
        return 0

    return subprocess.call(cmd, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
