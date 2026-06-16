#!/usr/bin/env python3
"""Run a baseline from an identical post-reach seed corpus.

The baseline matrix points here as the common execution entrypoint. This runner
keeps the contract deliberately small: real AFL-family baselines execute the
local artifact, while representative-only baselines are refused by default so
they cannot be mistaken for SOTA evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
AFLPP_BASELINES = {
    "aflplusplus_vanilla",
    "aflplusplus_cmplog",
    "redqueen_operand",
    "formtrig_full",
}
AFLGO_BASELINES = {"aflgo"}
REPRESENTATIVE_BASELINES = {
    "fishfuzz_reach_rank",
    "angora_branch_distance",
    "csfuzz_state_bucket",
    "cafl_constraint_sequence",
    "idfuzz_field_mutation",
    "native_tc_dgf",
    "uniform_tc_distance",
}
ACCEPTED_BASELINE_FAITHFULNESS = {
    "accepted_executable_control",
    "accepted_executable_artifact",
    "paper_equivalent_reimplementation",
    "thin_public_artifact_adapter",
}
REQUIRED_BASELINE_CONTRACT_FIELDS = (
    "paper_anchors",
    "artifact_anchors",
    "information_budget",
)
BASELINE_CONTRACTS: dict[str, dict[str, Any]] = {
    "aflplusplus_vanilla": {
        "faithfulness": "accepted_executable_control",
        "implementation": "local AFL++ afl-fuzz artifact",
        "mechanism": "coverage-guided AFL++ execution without FORMTRIG lifted D_F or BindingSpec semantics",
        "scope": "coverage/reach-only control, not a post-reach TC-distance method",
        "paper_anchors": [
            "related_papers/AFL++ CMPLOG.pdf",
            "paper/notes/RELATED_PAPER_ARTIFACTS.md:AFL++ CmpLog",
            "paper/notes/TC_GAP_CAPABILITY_MATRIX.md:AFL++ CmpLog",
        ],
        "artifact_anchors": [
            "experiments/aflplusplus/AFLplusplus@f596a297c4de",
            "experiments/aflplusplus/AFLplusplus/afl-fuzz",
        ],
        "information_budget": (
            "coverage feedback only; no FORMTRIG lifted D_F, BindingSpec "
            "roles, or typed mutation registry"
        ),
    },
    "aflplusplus_cmplog": {
        "faithfulness": "accepted_executable_artifact",
        "implementation": "local AFL++ CmpLog instrumentation plus matching cmplog binary",
        "mechanism": "comparison operand logging and comparison-guided mutation from AFL++",
        "scope": "faithful AFL++ CmpLog baseline for visible scalar/string comparison feedback",
        "paper_anchors": [
            "related_papers/AFL++ CMPLOG.pdf",
            "paper/notes/RELATED_PAPER_ARTIFACTS.md:AFL++ CmpLog",
            "paper/notes/TC_GAP_CAPABILITY_MATRIX.md:AFL++ CmpLog",
        ],
        "artifact_anchors": [
            "experiments/aflplusplus/AFLplusplus@f596a297c4de",
            "experiments/aflplusplus/AFLplusplus/instrumentation/README.cmplog.md",
            "experiments/aflplusplus/AFLplusplus/src/afl-fuzz-redqueen.c",
        ],
        "information_budget": (
            "AFL++ CmpLog operand map and normal AFL++ feedback; no FORMTRIG "
            "lifted D_F, BindingSpec roles, or typed mutation registry"
        ),
    },
    "redqueen_operand": {
        "faithfulness": "accepted_executable_artifact",
        "implementation": "local AFL++ Redqueen/CmpLog mode with a matching cmplog binary",
        "mechanism": "AFL++ value-profile/operand-substitution machinery",
        "scope": "AFL++ Redqueen-style operand baseline; not a substitute for the original Redqueen artifact unless separately mapped",
        "paper_anchors": [
            "related_papers/Redqueen.pdf",
            "related_papers/AFL++ CMPLOG.pdf",
            "paper/notes/TC_GAP_CAPABILITY_MATRIX.md:Redqueen",
            "paper/notes/CITATION_TODO.md:Redqueen",
        ],
        "artifact_anchors": [
            "experiments/aflplusplus/AFLplusplus@f596a297c4de",
            "experiments/aflplusplus/AFLplusplus/src/afl-fuzz-redqueen.c",
        ],
        "information_budget": (
            "AFL++ Redqueen/CmpLog operand observations and substitutions; "
            "no FORMTRIG lifted D_F, BindingSpec roles, or typed mutation "
            "registry"
        ),
        "equivalence_note": (
            "This local adapter is the AFL++ Redqueen/CmpLog implementation "
            "path. It is not evidence for the original Redqueen artifact "
            "unless a separate paper-equivalence mapping is added."
        ),
    },
    "aflgo": {
        "faithfulness": "accepted_executable_artifact",
        "implementation": "local AFLGo artifact path or AFLGO_FUZZ override",
        "mechanism": "static target-distance directed greybox fuzzing",
        "scope": "reach-side directed baseline; no FORMTRIG post-reach target-state signal is injected",
        "paper_anchors": [
            "related_papers/aflgo.pdf",
            "paper/notes/RELATED_PAPER_ARTIFACTS.md:AFLGo",
            "paper/notes/TC_GAP_CAPABILITY_MATRIX.md:AFLGo",
        ],
        "artifact_anchors": [
            "experiments/aflgo_formtrig/aflgo@fa125da5d706",
            "experiments/aflgo_formtrig/aflgo/afl-2.57b/afl-fuzz",
        ],
        "information_budget": (
            "AFLGo static reach distance and AFL feedback; no FORMTRIG "
            "lifted D_F, BindingSpec roles, or typed mutation registry"
        ),
    },
    "formtrig_full": {
        "faithfulness": "system_under_test",
        "implementation": "FORMTRIG native AFL++ integration",
        "mechanism": "spec-driven lifted D_F, dominance/frontier retention, and typed mutation",
        "scope": "FORMTRIG treatment arm, not an external baseline",
    },
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_event(
    path: Path,
    baseline: str,
    target_id: str,
    rep: int,
    event: str,
    details: dict[str, Any],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    row = {
        "baseline": baseline,
        "details": details,
        "event": event,
        "rep": rep,
        "target_id": target_id,
        "time_utc": utc_now(),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def parse_key_value(items: list[str]) -> dict[str, str]:
    env: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise SystemExit(f"--env expects KEY=VALUE, got: {item}")
        key, value = item.split("=", 1)
        if not key:
            raise SystemExit(f"--env key is empty in: {item}")
        env[key] = value
    return env


def parse_fuzzer_stats(path: Path) -> dict[str, str]:
    stats: dict[str, str] = {}
    if not path.exists():
        return stats
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        stats[key.strip()] = value.strip()
    return stats


def baseline_contract(baseline: str) -> dict[str, Any]:
    if baseline in BASELINE_CONTRACTS:
        return BASELINE_CONTRACTS[baseline]
    if baseline in REPRESENTATIVE_BASELINES:
        return {
            "faithfulness": "not_accepted",
            "implementation": "none",
            "mechanism": "representative-only placeholder",
            "scope": "must not enter main quantitative comparison",
        }
    return {
        "faithfulness": "unknown",
        "implementation": "unknown",
        "mechanism": "unknown",
        "scope": "unsupported baseline id",
    }


def resolve_anchor_path(anchor: str) -> Path:
    path_text = anchor.split(":", 1)[0]
    path = Path(path_text)
    if not path.is_absolute():
        path = REPO_ROOT / path
    if path.exists():
        return path

    if "@" in path_text:
        versionless = Path(path_text.split("@", 1)[0])
        if not versionless.is_absolute():
            versionless = REPO_ROOT / versionless
        return versionless
    return path


def unresolved_contract_anchors(contract: dict[str, Any], field: str) -> list[str]:
    anchors = contract.get(field)
    if not isinstance(anchors, list) or not anchors:
        return [f"<missing {field}>"]
    unresolved = []
    for anchor in anchors:
        if not isinstance(anchor, str) or not anchor.strip():
            unresolved.append(repr(anchor))
            continue
        if not resolve_anchor_path(anchor).exists():
            unresolved.append(anchor)
    return unresolved


def has_pdf_paper_anchor(contract: dict[str, Any]) -> bool:
    anchors = contract.get("paper_anchors", [])
    if not isinstance(anchors, list):
        return False
    return any(
        isinstance(anchor, str)
        and resolve_anchor_path(anchor).suffix.lower() == ".pdf"
        and resolve_anchor_path(anchor).is_file()
        for anchor in anchors
    )


def baseline_contract_rejection(baseline: str) -> str | None:
    contract = baseline_contract(baseline)
    faithfulness = contract.get("faithfulness")
    if faithfulness == "system_under_test":
        return None
    if faithfulness not in ACCEPTED_BASELINE_FAITHFULNESS:
        if baseline in REPRESENTATIVE_BASELINES:
            return "representative-only baseline has no faithful executable adapter"
        return "unsupported baseline has no accepted faithful contract"
    missing = [field for field in REQUIRED_BASELINE_CONTRACT_FIELDS if not contract.get(field)]
    if missing:
        return "accepted baseline contract is missing required anchors: " + ",".join(missing)
    for field in ("paper_anchors", "artifact_anchors"):
        unresolved = unresolved_contract_anchors(contract, field)
        if unresolved:
            return "accepted baseline contract has unresolved " + field + ": " + ",".join(unresolved)
    if not has_pdf_paper_anchor(contract):
        return "accepted baseline contract has no local PDF paper anchor"
    return None


def refuse_unaccepted_baseline(args: argparse.Namespace, events_path: Path) -> int | None:
    reason = baseline_contract_rejection(args.baseline)
    if reason is None:
        return None
    status_name = (
        "not_faithful_baseline_adapter"
        if args.baseline in REPRESENTATIVE_BASELINES
        else "unaccepted_baseline_contract"
    )
    detail = {
        "baseline": args.baseline,
        "baseline_contract": baseline_contract(args.baseline),
        "faithfulness": baseline_contract(args.baseline).get("faithfulness", "unknown"),
        "reason": reason,
        "status": status_name,
    }
    write_json(Path(args.out_dir) / "status.json", detail)
    append_event(events_path, args.baseline, args.target_id, args.rep, "run_error", detail)
    return 2


def find_fuzzer_stats(fuzzer_out: Path) -> Path | None:
    candidates = [
        fuzzer_out / "default" / "fuzzer_stats",
        fuzzer_out / "fuzzer_stats",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    matches = sorted(fuzzer_out.glob("*/fuzzer_stats"))
    return matches[0] if matches else None


def parse_afl_crash_metadata(path: Path) -> dict[str, int | str]:
    metadata: dict[str, int | str] = {"file": str(path)}
    for part in path.name.split(","):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        if key in {"time", "execs"}:
            try:
                metadata[key] = int(value)
            except ValueError:
                metadata[key] = value
        else:
            metadata[key] = value
    return metadata


def first_crash_record(stats_path: Path | None) -> dict[str, Any] | None:
    if stats_path is None:
        return None
    crash_dir = stats_path.parent / "crashes"
    if not crash_dir.is_dir():
        return None
    records = []
    for path in crash_dir.glob("id:*"):
        metadata = parse_afl_crash_metadata(path)
        time_ms = metadata.get("time")
        execs = metadata.get("execs")
        if not isinstance(time_ms, int):
            continue
        sort_execs = execs if isinstance(execs, int) else sys.maxsize
        records.append((time_ms, sort_execs, path.name, metadata))
    if not records:
        return None
    records.sort()
    metadata = records[0][3].copy()
    metadata["time_s"] = records[0][0] / 1000.0
    return metadata


def int_stat(stats: dict[str, str], key: str, default: int = 0) -> int:
    try:
        return int(float(stats.get(key, str(default))))
    except ValueError:
        return default


def resolve_tool(args: argparse.Namespace) -> Path:
    if args.afl_fuzz:
        return Path(args.afl_fuzz)
    if args.baseline in AFLGO_BASELINES:
        return Path(os.environ.get("AFLGO_FUZZ", "experiments/aflgo_formtrig/aflgo/afl-2.57b/afl-fuzz"))
    return Path(os.environ.get("AFLPP_FUZZ", "experiments/aflplusplus/AFLplusplus/afl-fuzz"))


def build_command(args: argparse.Namespace, tool: Path, fuzzer_out: Path) -> list[str]:
    target_cmd = shlex.split(args.target_cmd)
    if not target_cmd:
        raise SystemExit("--target-cmd resolved to an empty command")
    if "@@" not in target_cmd:
        raise SystemExit("--target-cmd must contain @@ so AFL can substitute inputs")

    cmd = [
        str(tool),
        "-i",
        str(args.seed_corpus),
        "-o",
        str(fuzzer_out),
        "-m",
        args.memory_limit,
    ]
    if args.baseline in AFLPP_BASELINES:
        cmd.extend(["-V", str(args.budget_sec)])
    if args.baseline in {"aflplusplus_cmplog", "redqueen_operand"}:
        if not args.cmplog_binary:
            raise SystemExit(f"{args.baseline} requires --cmplog-binary")
        cmd.extend(["-c", str(args.cmplog_binary)])
    for afl_arg in args.afl_arg:
        cmd.append(afl_arg)
    cmd.append("--")
    cmd.extend(target_cmd)
    return cmd


def infer_run_record(
    args: argparse.Namespace,
    cmd: list[str],
    returncode: int | None,
    elapsed_s: float,
    fuzzer_out: Path,
    mode_status: str,
) -> dict[str, Any]:
    stats_path = find_fuzzer_stats(fuzzer_out)
    stats = parse_fuzzer_stats(stats_path) if stats_path else {}

    saved_crashes = int_stat(stats, "saved_crashes")
    saved_hangs = int_stat(stats, "saved_hangs")
    start_time = int_stat(stats, "start_time")
    last_crash = int_stat(stats, "last_crash")
    last_crash_time_s = None
    if saved_crashes > 0 and start_time > 0 and last_crash > 0:
        last_crash_time_s = max(0, last_crash - start_time)
    first_crash = first_crash_record(stats_path)
    trigger_time_s = first_crash.get("time_s") if first_crash else last_crash_time_s
    trigger_execs = first_crash.get("execs") if first_crash else None
    if saved_crashes > 0 and trigger_execs is None:
        trigger_execs = int_stat(stats, "execs_done")

    run_time = int_stat(stats, "run_time", int(elapsed_s))
    timeout = returncode == 124 or (mode_status == "complete" and run_time >= args.budget_sec and saved_crashes == 0)
    success = saved_crashes > 0

    return {
        "baseline": args.baseline,
        "baseline_contract": baseline_contract(args.baseline),
        "budget": args.budget_sec,
        "command_line": cmd,
        "config_path": str(Path(args.out_dir) / "run_config.json"),
        "fuzzer_stats": str(stats_path) if stats_path else None,
        "run_id": f"{args.target_id}:{args.baseline}:rep{args.rep}",
        "seed_set_id": str(args.seed_corpus),
        "success": success,
        "target_id": args.target_id,
        "tc_category": args.tc_category,
        "timeout": timeout,
        "first_crash": first_crash,
        "last_crash_time_s": last_crash_time_s,
        "trigger_execs": trigger_execs if success else None,
        "trigger_time_s": trigger_time_s,
        "stats": {
            "execs_done": int_stat(stats, "execs_done"),
            "execs_per_sec": stats.get("execs_per_sec"),
            "run_time": run_time,
            "saved_crashes": saved_crashes,
            "saved_hangs": saved_hangs,
            "corpus_count": int_stat(stats, "corpus_count"),
        },
    }


def run_execute(args: argparse.Namespace, events_path: Path) -> int:
    refusal = refuse_unaccepted_baseline(args, events_path)
    if refusal is not None:
        return refusal

    tool = resolve_tool(args)
    if not tool.exists():
        raise SystemExit(f"baseline fuzzer not found: {tool}")
    if not os.access(tool, os.X_OK):
        raise SystemExit(f"baseline fuzzer is not executable: {tool}")
    if not Path(args.seed_corpus).is_dir():
        raise SystemExit(f"seed corpus is not a directory: {args.seed_corpus}")
    if args.cmplog_binary and not Path(args.cmplog_binary).exists():
        raise SystemExit(f"cmplog binary not found: {args.cmplog_binary}")

    fuzzer_out = Path(args.out_dir) / "fuzzer_out"
    fuzzer_out.mkdir(parents=True, exist_ok=True)
    cmd = build_command(args, tool, fuzzer_out)
    env = os.environ.copy()
    env.setdefault("AFL_NO_UI", "1")
    env.setdefault("AFL_SKIP_CPUFREQ", "1")
    env.setdefault("AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES", "1")
    env.update(parse_key_value(args.env))

    append_event(
        events_path,
        args.baseline,
        args.target_id,
        args.rep,
        "tool_resolution",
        {
            "baseline_contract": baseline_contract(args.baseline),
            "cwd": str(Path.cwd()),
            "resolved_cmd": cmd,
            "runner_mode": args.mode,
            "seed_corpus_exists": Path(args.seed_corpus).is_dir(),
            "tool": str(tool),
        },
    )
    append_event(events_path, args.baseline, args.target_id, args.rep, "fuzzer_start", {"cmd": cmd})

    stdout_path = Path(args.out_dir) / "fuzzer_stdout.log"
    stderr_path = Path(args.out_dir) / "fuzzer_stderr.log"
    start = time.monotonic()
    proc: subprocess.Popen[str] | None = None
    returncode: int | None
    try:
        with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open("w", encoding="utf-8") as stderr:
            proc = subprocess.Popen(
                cmd,
                env=env,
                stdout=stdout,
                stderr=stderr,
                text=True,
                preexec_fn=os.setsid,
            )
            try:
                returncode = proc.wait(timeout=args.budget_sec + args.timeout_grace_sec)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGTERM)
                try:
                    returncode = proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(proc.pid, signal.SIGKILL)
                    returncode = proc.wait()
                returncode = 124
    finally:
        elapsed_s = time.monotonic() - start

    append_event(
        events_path,
        args.baseline,
        args.target_id,
        args.rep,
        "fuzzer_exit",
        {"elapsed_s": elapsed_s, "returncode": returncode},
    )

    run_record = infer_run_record(args, cmd, returncode, elapsed_s, fuzzer_out, "complete")
    write_json(Path(args.out_dir) / "run_record.json", run_record)
    status = {
        "baseline_contract": baseline_contract(args.baseline),
        "elapsed_s": elapsed_s,
        "resolved_cmd": cmd,
        "returncode": returncode,
        "run_record": str(Path(args.out_dir) / "run_record.json"),
        "status": "complete",
    }
    write_json(Path(args.out_dir) / "status.json", status)
    append_event(events_path, args.baseline, args.target_id, args.rep, "run_complete", status)
    return 0 if returncode in (0, 124) else int(returncode or 1)


def run_dry(args: argparse.Namespace, events_path: Path) -> int:
    refusal = refuse_unaccepted_baseline(args, events_path)
    if refusal is not None:
        return refusal

    tool = resolve_tool(args)
    fuzzer_out = Path(args.out_dir) / "fuzzer_out"
    cmd = build_command(args, tool, fuzzer_out)
    status = {
        "baseline_contract": baseline_contract(args.baseline),
        "resolved_cmd": cmd,
        "status": "dry_run",
        "tool_exists": tool.exists(),
        "tool": str(tool),
    }
    write_json(Path(args.out_dir) / "status.json", status)
    append_event(events_path, args.baseline, args.target_id, args.rep, "run_complete", status)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--tc-category", default="unknown")
    parser.add_argument("--seed-corpus", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--budget-sec", type=int, required=True)
    parser.add_argument("--rep", type=int, default=1)
    parser.add_argument("--target-cmd", required=True)
    parser.add_argument("--cmplog-binary", default="")
    parser.add_argument("--afl-fuzz", default="")
    parser.add_argument("--memory-limit", default="none")
    parser.add_argument("--timeout-grace-sec", type=int, default=5)
    parser.add_argument("--mode", choices=["dry-run", "execute"], default="execute")
    parser.add_argument("--afl-arg", action="append", default=[])
    parser.add_argument("--env", action="append", default=[], help="extra environment KEY=VALUE for the fuzzer")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    events_path = out_dir / "events.jsonl"
    run_config = vars(args).copy()
    run_config["baseline_contract"] = baseline_contract(args.baseline)
    run_config["standard_event_schema"] = {
        "baseline": "baseline identifier",
        "details": "event-specific object",
        "event": "run_start|tool_resolution|fuzzer_start|fuzzer_exit|run_complete|run_error",
        "rep": "integer repetition id",
        "target_id": "target identifier",
        "time_utc": "ISO-8601 UTC timestamp",
    }
    write_json(out_dir / "run_config.json", run_config)
    append_event(events_path, args.baseline, args.target_id, args.rep, "run_start", run_config)

    try:
        if args.mode == "dry-run":
            return run_dry(args, events_path)
        return run_execute(args, events_path)
    except SystemExit as exc:
        message = str(exc)
        detail = {"status": "error", "message": message}
        write_json(out_dir / "status.json", detail)
        append_event(events_path, args.baseline, args.target_id, args.rep, "run_error", detail)
        raise
    except Exception as exc:  # pragma: no cover - defensive top-level reporting
        detail = {"status": "error", "message": str(exc), "type": type(exc).__name__}
        write_json(out_dir / "status.json", detail)
        append_event(events_path, args.baseline, args.target_id, args.rep, "run_error", detail)
        raise


if __name__ == "__main__":
    sys.exit(main())
