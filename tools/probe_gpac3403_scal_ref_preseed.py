#!/usr/bin/env python3
"""Build and replay a GPAC_3403 SCAL-reference preseed candidate.

B10 narrows the GPAC_3403 repair target to process_extractor returning at the
no-reference-track site.  This probe turns that diagnosis into an executable
gate: generate an enhanced HEVC stream with the typed hook, import base/enhanced
tracks into MP4, add an explicit track-2 -> track-1 SCAL reference, and replay
the result through the GPAC concatenation endpoint.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


ANSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
DOUBLE_FREE_RE = re.compile(r"double[- ]free|free\\(\\): double free", re.IGNORECASE)
NO_REF_RE = re.compile(r"Extractor target track is not present")
CORRUPT_NAL_RE = re.compile(r"rewrite: corrupted NAL Unit")


def load_hook(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("gpac3403_scal_ref_hook", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load hook: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def clean_text(text: str) -> str:
    return ANSI_RE.sub("", text)


def is_native_crash(exit_code: int | None) -> bool:
    return exit_code is not None and (exit_code < 0 or 128 <= exit_code <= 159)


def run_command(cmd: list[str], stdout_path: Path, stderr_path: Path, env: dict[str, str] | None = None) -> int:
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        result = subprocess.run(cmd, stdout=stdout, stderr=stderr, env=env, check=False)
    return result.returncode


def build_preseed(args: argparse.Namespace, out_dir: Path) -> dict[str, Any]:
    hook = load_hook(args.hook)
    seed = args.seed.read_bytes()
    enhanced = hook.mutate(
        seed,
        start=args.start,
        span=args.span,
        off=args.off,
        op=args.op,
        sample=args.sample,
    )

    base_hevc = out_dir / "base.hevc"
    enhanced_hevc = out_dir / "enhanced.hevc"
    mp4_path = out_dir / "two_track_scal_ref.mp4"
    base_hevc.write_bytes(seed)
    enhanced_hevc.write_bytes(enhanced)

    build1 = [
        str(args.mp4box),
        "-add",
        str(base_hevc),
        str(mp4_path),
    ]
    build2 = [
        str(args.mp4box),
        "-add",
        str(enhanced_hevc),
        str(mp4_path),
    ]
    ref = [
        str(args.mp4box),
        "-ref",
        f"{args.ref_track_id}:scal:{args.base_track_id}",
        str(mp4_path),
    ]

    rc_build1 = run_command(build1, out_dir / "build_base.stdout", out_dir / "build_base.stderr")
    rc_build2 = run_command(build2, out_dir / "build_enhanced.stdout", out_dir / "build_enhanced.stderr")
    rc_ref = run_command(ref, out_dir / "add_scal_ref.stdout", out_dir / "add_scal_ref.stderr")

    return {
        "base_hevc": str(base_hevc),
        "enhanced_hevc": str(enhanced_hevc),
        "mp4": str(mp4_path),
        "base_size": len(seed),
        "enhanced_size": len(enhanced),
        "commands": {
            "build_base": build1,
            "build_enhanced": build2,
            "add_scal_ref": ref,
        },
        "exit_codes": {
            "build_base": rc_build1,
            "build_enhanced": rc_build2,
            "add_scal_ref": rc_ref,
        },
        "built": rc_build1 == 0 and rc_build2 == 0 and rc_ref == 0 and mp4_path.exists(),
    }


def replay_preseed(args: argparse.Namespace, out_dir: Path, mp4_path: Path) -> dict[str, Any]:
    runtime_log = out_dir / "runtime.jsonl"
    stdout_log = out_dir / "replay.stdout"
    stderr_log = out_dir / "replay.stderr"
    env = os.environ.copy()
    if args.lift_spec:
        env.update(
            {
                "FORMTRIG_TARGET_BUG": "GPAC_3403",
                "FORMTRIG_PUBLISH_EAGER": "1",
                "FORMTRIG_ALLOW_HEURISTIC_LIFT": "0",
                "FORMTRIG_OBSERVE_HEURISTIC_LIFT": "0",
                "FORMTRIG_ALLOW_MANUAL_LIFT": "0",
                "FORMTRIG_PRE_REACH_EVENTS": "1",
                "FORMTRIG_LIFT_SPEC": str(args.lift_spec),
                "FORMTRIG_LOG": str(runtime_log),
            }
        )
        if args.target_site_ids:
            env["FORMTRIG_TARGET_SITE_IDS"] = args.target_site_ids

    cmd = [
        str(args.mp4box),
        "-cat",
        str(mp4_path),
        str(args.companion_mp4),
        "-out",
        "/dev/null",
    ]
    exit_code = run_command(cmd, stdout_log, stderr_log, env=env)
    stderr_text = clean_text(stderr_log.read_text(encoding="utf-8", errors="replace"))
    return {
        "command": cmd,
        "exit_code": exit_code,
        "native_crash": is_native_crash(exit_code),
        "double_free_signature": bool(DOUBLE_FREE_RE.search(stderr_text)),
        "no_reference_track_messages": len(NO_REF_RE.findall(stderr_text)),
        "corrupt_nal_messages": len(CORRUPT_NAL_RE.findall(stderr_text)),
        "runtime_log": str(runtime_log),
        "runtime_log_exists": runtime_log.exists(),
        "stdout": str(stdout_log),
        "stderr": str(stderr_log),
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    args.out.mkdir(parents=True, exist_ok=True)
    preseed = build_preseed(args, args.out)
    replay: dict[str, Any] | None = None
    if preseed["built"]:
        replay = replay_preseed(args, args.out, Path(preseed["mp4"]))

    status = "preseed_build_failed"
    next_action = "Fix MP4Box preseed construction before endpoint replay."
    if replay:
        if replay["double_free_signature"]:
            status = "scal_ref_preseed_triggers_double_free"
            next_action = (
                "Promote SCAL-reference construction into the GPAC typed-mutation/preseed path, "
                "then compare against faithful baselines with the same endpoint oracle."
            )
        elif replay["no_reference_track_messages"]:
            status = "scal_ref_preseed_still_has_no_reference_gaps"
            next_action = "Inspect track IDs and per-sample extractor ref_index alignment."
        else:
            status = "scal_ref_preseed_no_terminal_crash"
            next_action = "Use B10 downstream probes to refine extractor payload offsets and lengths."

    return {
        "schema": "formtrig_gpac3403_scal_ref_preseed_probe_v1",
        "target": "GPAC_3403",
        "status": status,
        "next_action": next_action,
        "parameters": {
            "op": args.op,
            "sample": args.sample,
            "start": args.start,
            "span": args.span,
            "off": args.off,
            "base_track_id": args.base_track_id,
            "ref_track_id": args.ref_track_id,
        },
        "preseed": preseed,
        "replay": replay,
    }


def write_markdown(report: dict[str, Any], path: Path) -> None:
    replay = report.get("replay") or {}
    lines = [
        "# GPAC_3403 SCAL Reference Preseed Probe",
        "",
        f"- status: `{report['status']}`",
        f"- next_action: {report['next_action']}",
        "",
        "## Replay",
        "",
        "| metric | value |",
        "|---|---:|",
        f"| exit_code | {replay.get('exit_code')} |",
        f"| native_crash | {replay.get('native_crash')} |",
        f"| double_free_signature | {replay.get('double_free_signature')} |",
        f"| no_reference_track_messages | {replay.get('no_reference_track_messages')} |",
        f"| corrupt_nal_messages | {replay.get('corrupt_nal_messages')} |",
        f"| runtime_log_exists | {replay.get('runtime_log_exists')} |",
    ]
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument("--hook", type=Path, required=True)
    parser.add_argument("--mp4box", type=Path, required=True)
    parser.add_argument("--companion-mp4", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--lift-spec", type=Path)
    parser.add_argument("--target-site-ids", default="115396228")
    parser.add_argument("--start", type=int, default=0)
    parser.add_argument("--span", type=int, default=2975)
    parser.add_argument("--off", type=int, default=6)
    parser.add_argument("--op", type=int, default=52)
    parser.add_argument("--sample", type=int, default=2)
    parser.add_argument("--base-track-id", type=int, default=1)
    parser.add_argument("--ref-track-id", type=int, default=2)
    parser.add_argument("--out-json", type=Path)
    parser.add_argument("--out-md", type=Path)
    args = parser.parse_args(argv)

    report = build_report(args)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    out_json = args.out_json or (args.out / "summary.json")
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(rendered, encoding="utf-8")
    if args.out_md:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        write_markdown(report, args.out_md)
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
