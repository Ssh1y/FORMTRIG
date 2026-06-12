#!/usr/bin/env python3
"""Prepare reusable CC/CXX wrappers for native FORMTRIG target builds."""

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from formtrig_cc import (
    build_pass_command,
    build_runtime_command,
    infer_toolchain,
    parse_env_assignments,
    resolve_pass_load_mode,
)


ROOT = Path(__file__).resolve().parents[2]
FORMTRIG_CC = ROOT / "formtrig" / "tools" / "formtrig_cc.py"


def default_aflpp_tool(name: str) -> Optional[str]:
    candidate = ROOT / "experiments" / "aflplusplus" / "AFLplusplus" / name
    if candidate.exists():
        return str(candidate)
    return shutil.which(name)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Build FORMTRIG pass/runtime once and emit compiler wrappers usable "
            "as CC/CXX for configure, make, cmake, and Magma/CVE builds."
        ),
        allow_abbrev=False,
    )
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--site-map", type=Path, help="Shared FORMTRIG_SITE_MAP path")
    parser.add_argument("--report-json", type=Path, help="Structured environment report")
    parser.add_argument(
        "--cc-compiler",
        default=default_aflpp_tool("afl-clang-fast") or shutil.which("clang") or "clang",
        help="Compiler used by generated formtrig-cc.",
    )
    parser.add_argument(
        "--cxx-compiler",
        default=default_aflpp_tool("afl-clang-fast++")
        or shutil.which("clang++")
        or "clang++",
        help="Compiler used by generated formtrig-cxx.",
    )
    parser.add_argument(
        "--afl-cc",
        help="Set AFL_CC inside generated wrappers; must match --llvm-config.",
    )
    parser.add_argument(
        "--afl-cxx",
        help="Set AFL_CXX inside generated wrappers; must match --llvm-config.",
    )
    parser.add_argument(
        "--pass-cxx",
        default=os.environ.get("FORMTRIG_CXX") or os.environ.get("CXX"),
        help="C++ compiler used to build the FORMTRIG LLVM pass.",
    )
    parser.add_argument(
        "--llvm-config",
        default=os.environ.get("LLVM_CONFIG"),
        help="llvm-config matching --pass-cxx and the target clang backend.",
    )
    parser.add_argument(
        "--pass-load-mode",
        choices=["auto", "legacy", "plugin"],
        default="auto",
        help="How generated wrappers should load the FORMTRIG LLVM pass.",
    )
    parser.add_argument(
        "--runtime-cc",
        default=os.environ.get("FORMTRIG_RUNTIME_CC")
        or shutil.which("cc")
        or shutil.which("clang")
        or "cc",
        help="Compiler used to build FORMTRIG runtime object.",
    )
    parser.add_argument(
        "--instrument-level",
        default=os.environ.get("FORMTRIG_INSTRUMENT_LEVEL", "balanced"),
        choices=["balanced", "tiny", "slice", "cmp", "full"],
    )
    parser.add_argument(
        "--runtime-link-mode",
        choices=["auto", "always", "never"],
        default="auto",
    )
    parser.add_argument(
        "--skip-pass-regex",
        action="append",
        default=[],
        help="Forwarded to formtrig_cc.py for support files compiled without the FORMTRIG LLVM pass.",
    )
    parser.add_argument(
        "--gnu-source",
        choices=["auto", "always", "never"],
        default=os.environ.get("FORMTRIG_GNU_SOURCE", "auto"),
        help=(
            "Forwarded to formtrig_cc.py. auto adds _GNU_SOURCE on Linux "
            "source compilations unless the target build already controls it."
        ),
    )
    parser.add_argument(
        "--runtime-lib",
        action="append",
        default=None,
        help="Library/flag appended by generated wrappers when linking runtime.",
    )
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Environment variable embedded into generated wrappers.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing work-dir.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned setup without writing wrappers or building artifacts.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print build commands before running them.",
    )
    return parser


def quote_cmd(parts: List[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def run(cmd: List[str], *, dry_run: bool, verbose: bool) -> None:
    if dry_run or verbose:
        print(quote_cmd(cmd), file=sys.stderr)
    if not dry_run:
        subprocess.run(cmd, check=True)


def wrapper_text(
    *,
    compiler: str,
    pass_so: Path,
    runtime_object: Path,
    site_map: Path,
    instrument_level: str,
    pass_load_mode: str,
    runtime_link_mode: str,
    runtime_libs: List[str],
    skip_pass_regexes: List[str],
    gnu_source: str,
    env_assignments: Dict[str, str],
    afl_cc: Optional[str],
    afl_cxx: Optional[str],
) -> str:
    cmd = [
        sys.executable,
        str(FORMTRIG_CC),
        "--compiler",
        compiler,
        "--pass-so",
        str(pass_so),
        "--runtime-object",
        str(runtime_object),
        "--site-map",
        str(site_map),
        "--instrument-level",
        instrument_level,
        "--pass-load-mode",
        pass_load_mode,
        "--runtime-link-mode",
        runtime_link_mode,
        "--gnu-source",
        gnu_source,
        "--no-build-pass",
        "--no-build-runtime",
        "--append-site-map",
        "--quiet",
    ]
    if afl_cc:
        cmd.extend(["--afl-cc", afl_cc])
    if afl_cxx:
        cmd.extend(["--afl-cxx", afl_cxx])
    for pattern in skip_pass_regexes:
        cmd.extend(["--skip-pass-regex", pattern])
    for lib in runtime_libs:
        cmd.append(f"--runtime-lib={lib}")
    for key, value in sorted(env_assignments.items()):
        cmd.extend(["--env", f"{key}={value}"])
    cmd.append("--")
    return "#!/bin/sh\nexec " + quote_cmd(cmd) + ' "$@"\n'


def write_executable(path: Path, text: str, *, dry_run: bool) -> None:
    if dry_run:
        return
    path.write_text(text)
    path.chmod(0o755)


def shell_exports(report: Dict[str, Any]) -> str:
    return "\n".join(
        [
            f"export CC={shlex.quote(report['cc_wrapper'])}",
            f"export CXX={shlex.quote(report['cxx_wrapper'])}",
            f"export FORMTRIG_SITE_MAP={shlex.quote(report['site_map'])}",
            f"export FORMTRIG_NATIVE_BUILD_REPORT={shlex.quote(report['report_json'])}",
        ]
    ) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    work_dir = args.work_dir
    if work_dir.exists() and any(work_dir.iterdir()) and not args.force:
        raise SystemExit(f"work-dir is not empty; use --force: {work_dir}")
    if not args.dry_run:
        work_dir.mkdir(parents=True, exist_ok=True)

    site_map = args.site_map or (work_dir / "formtrig_sites.tsv")
    pass_so = work_dir / "libFormtrigPass.so"
    runtime_object = work_dir / "formtrig_runtime.o"
    cc_wrapper = work_dir / "formtrig-cc"
    cxx_wrapper = work_dir / "formtrig-cxx"
    env_file = work_dir / "formtrig_build_env.sh"
    report_json = args.report_json or (work_dir / "formtrig_native_build.json")
    env_assignments = parse_env_assignments(args.env)
    runtime_libs = args.runtime_lib if args.runtime_lib is not None else ["-lm", "-lrt"]
    pass_cxx, llvm_config = infer_toolchain(
        args.cc_compiler, args.pass_cxx, args.llvm_config
    )
    pass_load_mode = resolve_pass_load_mode(args.pass_load_mode, llvm_config)

    pass_cmd = build_pass_command(pass_cxx, llvm_config, pass_so)
    runtime_cmd = build_runtime_command(args.runtime_cc, runtime_object)
    run(pass_cmd, dry_run=args.dry_run, verbose=args.verbose)
    run(runtime_cmd, dry_run=args.dry_run, verbose=args.verbose)
    if site_map.exists() and not args.dry_run:
        site_map.unlink()

    cc_text = wrapper_text(
        compiler=args.cc_compiler,
        pass_so=pass_so,
        runtime_object=runtime_object,
        site_map=site_map,
        instrument_level=args.instrument_level,
        pass_load_mode=pass_load_mode,
        runtime_link_mode=args.runtime_link_mode,
        runtime_libs=runtime_libs,
        skip_pass_regexes=args.skip_pass_regex,
        gnu_source=args.gnu_source,
        env_assignments=env_assignments,
        afl_cc=args.afl_cc,
        afl_cxx=args.afl_cxx,
    )
    cxx_text = wrapper_text(
        compiler=args.cxx_compiler,
        pass_so=pass_so,
        runtime_object=runtime_object,
        site_map=site_map,
        instrument_level=args.instrument_level,
        pass_load_mode=pass_load_mode,
        runtime_link_mode=args.runtime_link_mode,
        runtime_libs=runtime_libs,
        skip_pass_regexes=args.skip_pass_regex,
        gnu_source=args.gnu_source,
        env_assignments=env_assignments,
        afl_cc=args.afl_cc,
        afl_cxx=args.afl_cxx,
    )
    write_executable(cc_wrapper, cc_text, dry_run=args.dry_run)
    write_executable(cxx_wrapper, cxx_text, dry_run=args.dry_run)

    report = {
        "work_dir": str(work_dir),
        "cc_wrapper": str(cc_wrapper),
        "cxx_wrapper": str(cxx_wrapper),
        "site_map": str(site_map),
        "pass_so": str(pass_so),
        "pass_cxx": pass_cxx,
        "llvm_config": llvm_config,
        "runtime_object": str(runtime_object),
        "report_json": str(report_json),
        "instrument_level": args.instrument_level,
        "pass_load_mode": pass_load_mode,
        "runtime_link_mode": args.runtime_link_mode,
        "skip_pass_regex": args.skip_pass_regex,
        "gnu_source": args.gnu_source,
        "commands": {
            "build_pass": pass_cmd,
            "build_runtime": runtime_cmd,
        },
        "env": {
            "CC": str(cc_wrapper),
            "CXX": str(cxx_wrapper),
            "FORMTRIG_SITE_MAP": str(site_map),
            "FORMTRIG_NATIVE_BUILD_REPORT": str(report_json),
        },
    }
    if not args.dry_run:
        report_json.parent.mkdir(parents=True, exist_ok=True)
        report_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
        env_file.write_text(shell_exports(report))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
