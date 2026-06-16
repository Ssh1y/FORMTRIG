#!/usr/bin/env python3
"""Build or plan FORMTRIG-native Magma target assets.

The tool intentionally defaults to dry-run planning. Use --execute to run the
Magma fetch/patch/instrument chain. A successful execution should leave the
expected executable under OUT/afl and the FORMTRIG site map under
OUT/formtrig_native/formtrig_sites.tsv; tools/discover_magma_native_assets.py
can then turn those files into validation assets.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_MAGMA_ROOT = Path("experiments/magma_workspace/magma")
DEFAULT_OUT_ROOT = Path("artifacts/formtrig_native_readiness/magma_native_builds")


def shell_join(parts: list[str]) -> str:
    return " ".join(shlex.quote(str(part)) for part in parts)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def quote_env(env: dict[str, str]) -> str:
    return " ".join(f"{key}={shlex.quote(value)}" for key, value in sorted(env.items()))


def parse_program_args(configrc: Path, program: str) -> str:
    if not configrc.exists():
        return "@@"
    pattern = re.compile(rf"^{re.escape(program)}_ARGS=(.*)$")
    for raw in configrc.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        match = pattern.match(line)
        if not match:
            continue
        value = match.group(1).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            return value[1:-1]
        return value or "@@"
    return "@@"


def repo_has_magma_log(repo: Path) -> bool:
    if not repo.exists():
        return False
    try:
        proc = subprocess.run(
            ["rg", "-q", "MAGMA_LOG", str(repo)],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return proc.returncode == 0
    except FileNotFoundError:
        for root, dirnames, filenames in os.walk(repo):
            dirnames[:] = [name for name in dirnames if name != ".git"]
            for filename in filenames:
                path = Path(root) / filename
                try:
                    if "MAGMA_LOG" in path.read_text(encoding="utf-8", errors="ignore"):
                        return True
                except OSError:
                    continue
    return False


def default_out_dir(target_id: str, target: str, program: str) -> Path:
    name = target_id or f"{target}_{program}"
    return DEFAULT_OUT_ROOT / name


def step(
    name: str,
    command: list[str],
    *,
    env: dict[str, str],
    selected: bool,
    reason: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "selected": selected,
        "reason": reason,
        "command": command,
        "shell": quote_env(env) + (" " if env else "") + shell_join(command),
        "env": env,
    }


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    magma_root = args.magma_root.resolve()
    magma = magma_root / "magma"
    fuzzer = magma_root / "fuzzers" / args.fuzzer
    target = magma_root / "targets" / args.target
    out_dir = (args.out_dir or default_out_dir(args.target_id, args.target, args.program)).resolve()
    out = out_dir / "out"
    shared = out_dir / "shared"
    logs = out_dir / "logs"
    site_map = out / "formtrig_native" / "formtrig_sites.tsv"
    target_cwd = out / "afl"
    executable = target_cwd / args.program
    args_template = args.args_template or parse_program_args(target / "configrc", args.program)
    target_cmd = f"{shlex.quote(str(executable))} {args_template}".strip()

    common_env = {
        "FUZZER": str(fuzzer),
        "TARGET": str(target),
        "MAGMA": str(magma),
        "OUT": str(out),
        "SHARED": str(shared),
        "PROGRAM": args.program,
    }
    build_env = {
        **common_env,
        "LD": args.ld,
        "CFLAGS": " ".join(
            item
            for item in [
                f"-include {magma / 'src' / 'canary.h'}",
                "-DMAGMA_ENABLE_CANARIES",
                "-g",
                "-O0",
                args.extra_cflags,
            ]
            if item
        ),
        "CXXFLAGS": " ".join(
            item
            for item in [
                f"-include {magma / 'src' / 'canary.h'}",
                "-DMAGMA_ENABLE_CANARIES",
                "-g",
                "-O0",
                args.extra_cxxflags,
            ]
            if item
        ),
        "LIBS": " ".join(item for item in ["-l:magma.o", "-lrt", args.extra_libs] if item),
        "LDFLAGS": " ".join(item for item in ["-g", f"-L{out}", args.extra_ldflags] if item),
        "FORMTRIG_INSTRUMENT_LEVEL": args.instrument_level,
    }
    if args.formtrig_target_bug:
        build_env["FORMTRIG_TARGET_BUG"] = args.formtrig_target_bug

    fuzzer_repo = fuzzer / "repo"
    fuzzer_needs_fetch = args.force_fuzzer_fetch or not fuzzer_repo.exists()
    fuzzer_needs_build = args.force_fuzzer_build or not all(
        path.exists()
        for path in [
            fuzzer_repo / "afl-clang-fast",
            fuzzer_repo / "afl-clang-fast++",
            fuzzer_repo / "utils" / "aflpp_driver" / "libAFLDriver.a",
        ]
    )
    target_repo = target / "repo"
    target_needs_fetch = args.force_target_fetch or not target_repo.exists()
    patches_needed = args.force_patches or target_needs_fetch or not repo_has_magma_log(target_repo)

    steps = [
        step(
            "fuzzer_fetch",
            ["bash", str(fuzzer / "fetch.sh")],
            env={"FUZZER": str(fuzzer)},
            selected=fuzzer_needs_fetch and not args.skip_fuzzer_fetch,
            reason="fuzzer repo missing or forced" if fuzzer_needs_fetch else "fuzzer repo already present",
        ),
        step(
            "fuzzer_build",
            ["bash", str(fuzzer / "build.sh")],
            env=common_env,
            selected=fuzzer_needs_build and not args.skip_fuzzer_build,
            reason="AFL++/driver artifacts missing or forced" if fuzzer_needs_build else "AFL++/driver artifacts already present",
        ),
        step(
            "target_preinstall",
            ["bash", str(target / "preinstall.sh")],
            env={"TARGET": str(target)},
            selected=args.run_preinstall,
            reason="explicit --run-preinstall requested",
        ),
        step(
            "target_fetch",
            ["bash", str(target / "fetch.sh")],
            env={"TARGET": str(target)},
            selected=target_needs_fetch and not args.skip_target_fetch,
            reason="target repo missing or forced" if target_needs_fetch else "target repo already present",
        ),
        step(
            "apply_patches",
            ["bash", str(magma / "apply_patches.sh")],
            env={"TARGET": str(target)},
            selected=patches_needed and not args.skip_patches,
            reason="target repo lacks MAGMA_LOG markers or patches forced" if patches_needed else "target repo already has MAGMA_LOG markers",
        ),
        step(
            "instrument_target",
            ["bash", str(fuzzer / "instrument.sh")],
            env=build_env,
            selected=True,
            reason="build FORMTRIG-native target executable and site map",
        ),
    ]

    refresh_commands: list[dict[str, Any]] = []
    if args.refresh_discovery:
        discovery_env: dict[str, str] = {}
        refresh_commands.append(
            step(
                "refresh_asset_discovery",
                [
                    sys.executable,
                    "tools/discover_magma_native_assets.py",
                    "--search-root",
                    str(out_dir),
                    "--search-root",
                    "artifacts/formtrig_native_readiness",
                    "--search-root",
                    "experiments/magma_workspace",
                ],
                env=discovery_env,
                selected=True,
                reason="explicit --refresh-discovery requested",
            )
        )
        refresh_commands.append(
            step(
                "refresh_validation_worklist",
                [
                    sys.executable,
                    "tools/plan_magma_binding_validation.py",
                    "--assets",
                    "artifacts/formtrig_native_readiness/magma_binding_validation_assets.discovered_20260616.json",
                ],
                env=discovery_env,
                selected=True,
                reason="explicit --refresh-discovery requested",
            )
        )

    return {
        "schema": "formtrig_magma_native_build_plan_v1",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "mode": "execute" if args.execute else "dry-run",
        "target_id": args.target_id,
        "target": args.target,
        "program": args.program,
        "inputs": {
            "magma_root": str(magma_root),
            "fuzzer": args.fuzzer,
            "instrument_level": args.instrument_level,
            "run_preinstall": args.run_preinstall,
            "skip_fuzzer_fetch": args.skip_fuzzer_fetch,
            "skip_fuzzer_build": args.skip_fuzzer_build,
            "skip_target_fetch": args.skip_target_fetch,
            "skip_patches": args.skip_patches,
            "refresh_discovery": args.refresh_discovery,
        },
        "paths": {
            "out_dir": str(out_dir),
            "out": str(out),
            "shared": str(shared),
            "logs": str(logs),
            "magma": str(magma),
            "fuzzer": str(fuzzer),
            "target": str(target),
            "site_map": str(site_map),
            "target_cwd": str(target_cwd),
            "executable": str(executable),
        },
        "expected_validation_asset": {
            "target_id": args.target_id,
            "site_map": str(site_map),
            "target_cwd": str(target_cwd),
            "target_cmd": target_cmd,
            "program_args": args_template,
        },
        "steps": steps,
        "post_build_steps": refresh_commands,
    }


def run_step(row: dict[str, Any], *, cwd: Path, logs: Path) -> dict[str, Any]:
    if not row["selected"]:
        return {**row, "status": "skipped", "exit_code": None, "log": ""}
    logs.mkdir(parents=True, exist_ok=True)
    log_path = logs / f"{row['name']}.log"
    env = os.environ.copy()
    env.update(row.get("env") or {})
    with log_path.open("w", encoding="utf-8") as handle:
        handle.write("$ " + row["shell"] + "\n")
        proc = subprocess.run(
            row["command"],
            cwd=cwd,
            env=env,
            stdout=handle,
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
        )
    return {
        **row,
        "status": "ok" if proc.returncode == 0 else "failed",
        "exit_code": proc.returncode,
        "log": str(log_path),
    }


def execute_plan(plan: dict[str, Any], *, cwd: Path) -> dict[str, Any]:
    out = Path(plan["paths"]["out"])
    shared = Path(plan["paths"]["shared"])
    logs = Path(plan["paths"]["logs"])
    out.mkdir(parents=True, exist_ok=True)
    shared.mkdir(parents=True, exist_ok=True)
    executed_steps: list[dict[str, Any]] = []
    failed = False
    for row in plan["steps"]:
        result = run_step(row, cwd=cwd, logs=logs)
        executed_steps.append(result)
        if result["status"] == "failed":
            failed = True
            break
    if not failed:
        for row in plan["post_build_steps"]:
            result = run_step(row, cwd=cwd, logs=logs)
            executed_steps.append(result)
            if result["status"] == "failed":
                failed = True
                break
    plan["executed_steps"] = executed_steps
    plan["status"] = "failed" if failed else "executed"
    return plan


def write_markdown(path: Path, plan: dict[str, Any]) -> None:
    selected = [row for row in plan["steps"] + plan["post_build_steps"] if row["selected"]]
    lines = [
        "# Magma FORMTRIG Native Build Plan",
        "",
        "This is a build/readiness artifact, not endpoint performance evidence.",
        "A successful build should be followed by native asset discovery and a",
        "BindingSpec validation sweep before any long-run benefit claim.",
        "",
        f"Generated: `{plan['generated_at_utc']}`",
        f"Mode: `{plan['mode']}`",
        f"Target: `{plan['target_id'] or plan['target']}` / `{plan['program']}`",
        f"Expected site map: `{plan['paths']['site_map']}`",
        f"Expected executable: `{plan['paths']['executable']}`",
        "",
        "## Selected Steps",
        "",
    ]
    for row in selected:
        lines.append(f"- `{row['name']}`: `{row['shell']}`")
    if not selected:
        lines.append("- none")
    lines.extend(
        [
            "",
            "## Validation Asset",
            "",
            f"- `site_map`: `{plan['expected_validation_asset']['site_map']}`",
            f"- `target_cwd`: `{plan['expected_validation_asset']['target_cwd']}`",
            f"- `target_cmd`: `{plan['expected_validation_asset']['target_cmd']}`",
            "",
        ]
    )
    if plan.get("executed_steps"):
        lines.extend(["## Execution", ""])
        for row in plan["executed_steps"]:
            lines.append(
                f"- `{row['name']}`: `{row['status']}`"
                + (f" log=`{row['log']}`" if row.get("log") else "")
            )
        lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--target", required=True, help="Magma target directory name, e.g. poppler")
    parser.add_argument("--program", required=True, help="Magma program/fuzzer binary name")
    parser.add_argument("--target-id", default="", help="Optional TC id, e.g. PDF003")
    parser.add_argument("--magma-root", type=Path, default=DEFAULT_MAGMA_ROOT)
    parser.add_argument("--fuzzer", default="formtrig_native")
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--out-json", type=Path)
    parser.add_argument("--out-md", type=Path)
    parser.add_argument("--args-template", default="", help="Override target args template; defaults to target configrc or @@")
    parser.add_argument("--instrument-level", default="balanced")
    parser.add_argument("--formtrig-target-bug", default="")
    parser.add_argument("--ld", default=shutil.which("ld") or "/usr/bin/ld")
    parser.add_argument("--extra-cflags", default="")
    parser.add_argument("--extra-cxxflags", default="")
    parser.add_argument("--extra-ldflags", default="")
    parser.add_argument("--extra-libs", default="")
    parser.add_argument("--run-preinstall", action="store_true")
    parser.add_argument("--skip-fuzzer-fetch", action="store_true")
    parser.add_argument("--skip-fuzzer-build", action="store_true")
    parser.add_argument("--skip-target-fetch", action="store_true")
    parser.add_argument("--skip-patches", action="store_true")
    parser.add_argument("--force-fuzzer-fetch", action="store_true")
    parser.add_argument("--force-fuzzer-build", action="store_true")
    parser.add_argument("--force-target-fetch", action="store_true")
    parser.add_argument("--force-patches", action="store_true")
    parser.add_argument("--refresh-discovery", action="store_true")
    parser.add_argument("--execute", action="store_true", help="Run selected steps; default is dry-run planning")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    plan = build_plan(args)
    out_dir = Path(plan["paths"]["out_dir"])
    out_json = args.out_json or (out_dir / "build_plan.json")
    out_md = args.out_md or (out_dir / "build_plan.md")
    if args.execute:
        plan = execute_plan(plan, cwd=Path.cwd())
    else:
        plan["status"] = "planned"
    write_json(out_json, plan)
    write_markdown(out_md, plan)
    print(json.dumps({"status": plan["status"], "out_json": str(out_json), "out_md": str(out_md)}, sort_keys=True))
    return 1 if plan["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
