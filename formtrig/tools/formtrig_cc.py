#!/usr/bin/env python3
"""Compile native targets with FORMTRIG LLVM instrumentation.

This is a small compiler-driver wrapper for experiments. It builds the
FORMTRIG LLVM pass, loads it into a clang-compatible compiler such as clang or
afl-clang-fast, emits FORMTRIG_SITE_MAP, and links the native FORMTRIG runtime.
All TC semantics still come from TCIR/trigger graphs and external lift specs.
"""

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ROOT = Path(__file__).resolve().parents[2]
FORMTRIG_DIR = ROOT / "formtrig"
INCLUDE_DIR = FORMTRIG_DIR / "include"
PASS_SRC = FORMTRIG_DIR / "llvm" / "formtrig_pass.cpp"
RUNTIME_C = FORMTRIG_DIR / "runtime" / "formtrig_runtime.c"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compile a target with native FORMTRIG instrumentation",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--compiler",
        default=os.environ.get("FORMTRIG_CC")
        or shutil.which("clang")
        or os.environ.get("CC")
        or "clang",
        help="Target compiler. Use afl-clang-fast for AFL++ experiments.",
    )
    parser.add_argument(
        "--afl-cc",
        help=(
            "Set AFL_CC for afl-clang-fast/afl-cc. This clang must match "
            "--llvm-config for the FORMTRIG pass ABI."
        ),
    )
    parser.add_argument(
        "--afl-cxx",
        help=(
            "Set AFL_CXX for afl-clang-fast++/afl-c++. This clang++ must match "
            "--llvm-config for the FORMTRIG pass ABI."
        ),
    )
    parser.add_argument(
        "--runtime-cc",
        default=os.environ.get("FORMTRIG_RUNTIME_CC")
        or shutil.which("cc")
        or shutil.which("clang")
        or "cc",
        help="Compiler used for the FORMTRIG runtime object.",
    )
    parser.add_argument(
        "--cxx",
        default=os.environ.get("FORMTRIG_CXX") or os.environ.get("CXX"),
        help="C++ compiler used to build the LLVM pass.",
    )
    parser.add_argument(
        "--llvm-config",
        default=os.environ.get("LLVM_CONFIG"),
        help="llvm-config matching the clang-compatible compiler.",
    )
    parser.add_argument(
        "--pass-load-mode",
        choices=["auto", "legacy", "plugin"],
        default="auto",
        help="How to load the FORMTRIG LLVM pass into the target compiler.",
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        help="Directory for generated pass/runtime/report files.",
    )
    parser.add_argument("--pass-so", type=Path, help="Reuse or write this pass .so")
    parser.add_argument(
        "--runtime-object",
        type=Path,
        help="Reuse or write this FORMTRIG runtime object.",
    )
    parser.add_argument(
        "--site-map",
        type=Path,
        help="FORMTRIG_SITE_MAP output. Defaults to work-dir/formtrig_sites.tsv.",
    )
    parser.add_argument(
        "--report-json",
        type=Path,
        help="Write a structured compile report.",
    )
    parser.add_argument(
        "--instrument-level",
        default=os.environ.get("FORMTRIG_INSTRUMENT_LEVEL", "balanced"),
        choices=["balanced", "tiny", "slice", "cmp", "full"],
        help="FORMTRIG LLVM instrumentation level.",
    )
    parser.add_argument(
        "--append-site-map",
        action="store_true",
        help="Append to an existing site-map instead of starting a fresh one.",
    )
    parser.add_argument(
        "--skip-pass-regex",
        action="append",
        default=[],
        help=(
            "Regex matched against compiler arguments for support files that "
            "must be compiled without the FORMTRIG LLVM pass. Runtime linking "
            "is unchanged."
        ),
    )
    parser.add_argument(
        "--gnu-source",
        choices=["auto", "always", "never"],
        default=os.environ.get("FORMTRIG_GNU_SOURCE", "auto"),
        help=(
            "Add -D_GNU_SOURCE=1 for source compilations. auto enables this "
            "on Linux unless the target build already sets or unsets it."
        ),
    )
    parser.add_argument(
        "--no-build-pass",
        action="store_true",
        help="Require --pass-so to already exist.",
    )
    parser.add_argument(
        "--no-build-runtime",
        action="store_true",
        help="Require --runtime-object to already exist when runtime linking is needed.",
    )
    parser.add_argument(
        "--no-link-runtime",
        action="store_true",
        help="Do not append the FORMTRIG runtime object during link steps.",
    )
    parser.add_argument(
        "--runtime-link-mode",
        choices=["auto", "always", "never"],
        default="auto",
        help=(
            "When to append the FORMTRIG runtime object. auto links only final "
            "executable-like compiler invocations."
        ),
    )
    parser.add_argument(
        "--runtime-lib",
        action="append",
        default=None,
        help="Library/flag appended after the runtime object during link steps.",
    )
    parser.add_argument(
        "--env",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Extra environment variable for the target compiler invocation.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build planned commands/report without running compiler steps.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print commands before running them.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Do not print the per-invocation JSON report to stdout.",
    )
    parser.add_argument(
        "compiler_args",
        nargs=argparse.REMAINDER,
        help="Compiler arguments after --.",
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


def command_output(cmd: List[str]) -> str:
    return subprocess.check_output(cmd, universal_newlines=True).strip()


def version_major_from_text(text: str) -> Optional[int]:
    m = re.search(r"\b(?:clang|LLVM)\s+version\s+(\d+)\.", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r"^(\d+)\.", text.strip())
    if m:
        return int(m.group(1))
    return None


def tool_version_major(tool: str) -> Optional[int]:
    try:
        return version_major_from_text(command_output([tool, "--version"]))
    except (OSError, subprocess.CalledProcessError):
        return None


def tool_for_major(name: str, major: int) -> Optional[str]:
    candidates = [
        Path(f"/usr/lib/llvm-{major}/bin/{name}"),
        Path(f"/usr/bin/{name}-{major}"),
    ]
    path_candidate = shutil.which(f"{name}-{major}")
    if path_candidate:
        candidates.append(Path(path_candidate))
    plain = shutil.which(name)
    if plain:
        candidates.append(Path(plain))
    for candidate in candidates:
        if not candidate.exists():
            continue
        candidate_str = str(candidate)
        if tool_version_major(candidate_str) == major:
            return candidate_str
    return None


def infer_toolchain(
    compiler: str, cxx: Optional[str], llvm_config: Optional[str]
) -> Tuple[str, str]:
    if cxx and llvm_config:
        return (cxx, llvm_config)
    major = tool_version_major(compiler)
    inferred_cxx = cxx
    inferred_llvm_config = llvm_config
    if major is not None:
        if inferred_cxx is None:
            inferred_cxx = tool_for_major("clang++", major)
        if inferred_llvm_config is None:
            inferred_llvm_config = tool_for_major("llvm-config", major)
    if inferred_cxx is None:
        inferred_cxx = shutil.which("clang++") or "clang++"
    if inferred_llvm_config is None:
        inferred_llvm_config = shutil.which("llvm-config") or "llvm-config"
    return (inferred_cxx, inferred_llvm_config)


def llvm_cxxflags(llvm_config: str) -> List[str]:
    return shlex.split(command_output([llvm_config, "--cxxflags"]))


def llvm_major(llvm_config: str) -> int:
    version = command_output([llvm_config, "--version"])
    try:
        return int(version.split(".", 1)[0])
    except (ValueError, IndexError):
        return 0


def resolve_pass_load_mode(mode: str, llvm_config: str) -> str:
    if mode != "auto":
        return mode
    return "plugin" if llvm_major(llvm_config) >= 12 else "legacy"


def compiler_output_path(compiler_args: List[str]) -> Optional[str]:
    for index, arg in enumerate(compiler_args):
        if arg == "-o" and index + 1 < len(compiler_args):
            return compiler_args[index + 1]
        if arg.startswith("-o") and len(arg) > 2:
            return arg[2:]
    return None


SOURCE_EXTENSIONS = {
    ".c",
    ".cc",
    ".cpp",
    ".cxx",
    ".c++",
    ".C",
    ".m",
    ".mm",
    ".s",
    ".S",
    ".i",
    ".ii",
    ".bc",
    ".ll",
}


def compiler_source_args(compiler_args: List[str]) -> List[str]:
    out = []  # type: List[str]
    skip_next = False
    options_with_value = {
        "-o",
        "-x",
        "-include",
        "-include-pch",
        "-isystem",
        "-idirafter",
        "-iquote",
        "-imacros",
        "-MF",
        "-MT",
        "-MQ",
        "-D",
        "-U",
        "-I",
        "-L",
        "-Xclang",
        "-Xlinker",
        "-Xpreprocessor",
    }
    for arg in compiler_args:
        if skip_next:
            skip_next = False
            continue
        if arg in options_with_value:
            skip_next = True
            continue
        if arg.startswith("-"):
            continue
        if Path(arg).suffix in SOURCE_EXTENSIONS:
            out.append(arg)
    return out


def macro_state(compiler_args: List[str], macro: str) -> Optional[bool]:
    expect_define_value = False
    expect_undef_value = False
    for arg in compiler_args:
        if expect_define_value:
            if arg == macro or arg.startswith(macro + "="):
                return True
            expect_define_value = False
            continue
        if expect_undef_value:
            if arg == macro:
                return False
            expect_undef_value = False
            continue
        if arg == "-D":
            expect_define_value = True
            continue
        if arg == "-U":
            expect_undef_value = True
            continue
        if arg.startswith("-D"):
            value = arg[2:]
            if value == macro or value.startswith(macro + "="):
                return True
        elif arg.startswith("-U"):
            if arg[2:] == macro:
                return False
    return None


def feature_test_macro_args(compiler_args: List[str], gnu_source: str) -> List[str]:
    if gnu_source == "never":
        return []
    if gnu_source == "auto":
        if not sys.platform.startswith("linux"):
            return []
        if not compiler_source_args(compiler_args):
            return []
    if macro_state(compiler_args, "_GNU_SOURCE") is not None:
        return []
    return ["-D_GNU_SOURCE=1"]


def needs_link_runtime(
    compiler_args: List[str],
    no_link_runtime: bool,
    runtime_link_mode: str,
) -> bool:
    if no_link_runtime or runtime_link_mode == "never":
        return False
    if runtime_link_mode == "always":
        return True
    compile_only_flags = {"-c", "-S", "-E", "-M", "-MM"}
    if any(arg in compile_only_flags for arg in compiler_args):
        return False
    if any(arg == "-shared" or arg == "-r" or arg == "-Wl,-r" for arg in compiler_args):
        return False
    output = compiler_output_path(compiler_args)
    if output:
        suffix = Path(output).suffix
        if suffix in {".o", ".lo", ".a", ".so", ".dylib"}:
            return False
    return True


def should_skip_pass(compiler_args: List[str], patterns: List[str]) -> bool:
    if not patterns:
        return False
    sources = compiler_source_args(compiler_args)
    if not sources:
        return False
    text = "\n".join(sources)
    return any(re.search(pattern, text) for pattern in patterns)


def run(cmd: List[str], *, env: Optional[Dict[str, str]], dry_run: bool, verbose: bool) -> None:
    if verbose or dry_run:
        print(" ".join(shlex.quote(part) for part in cmd), file=sys.stderr)
    if not dry_run:
        subprocess.run(cmd, check=True, env=env)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def build_pass_command(cxx: str, llvm_config: str, pass_so: Path) -> List[str]:
    return [
        cxx,
        "-shared",
        "-fPIC",
        "-Wl,-znodelete",
        *llvm_cxxflags(llvm_config),
        f"-I{INCLUDE_DIR}",
        str(PASS_SRC),
        "-o",
        str(pass_so),
    ]


def build_runtime_command(runtime_cc: str, runtime_object: Path) -> List[str]:
    return [
        runtime_cc,
        "-O2",
        "-g",
        f"-I{INCLUDE_DIR}",
        "-c",
        str(RUNTIME_C),
        "-o",
        str(runtime_object),
    ]


def target_compile_command(
    compiler: str,
    pass_so: Optional[Path],
    compiler_args: List[str],
    *,
    pass_load_mode: str,
    runtime_object: Optional[Path],
    runtime_libs: List[str],
    feature_macro_args: Optional[List[str]] = None,
) -> List[str]:
    if pass_so is None:
        load_args = []
    elif pass_load_mode == "plugin":
        load_args = [f"-fpass-plugin={pass_so}"]
    else:
        load_args = ["-Xclang", "-load", "-Xclang", str(pass_so)]
    macros = feature_macro_args or []
    cmd = [compiler, *load_args, f"-I{INCLUDE_DIR}", *macros, *compiler_args]
    if runtime_object is not None:
        cmd.extend([str(runtime_object), *runtime_libs])
    return cmd


def write_report(path: Optional[Path], report: Dict[str, Any]) -> None:
    if path is None:
        return
    ensure_parent(path)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    compiler_args = normalize_remainder(args.compiler_args)
    if not compiler_args:
        raise SystemExit("missing compiler arguments after --")
    pass_cxx, llvm_config = infer_toolchain(args.compiler, args.cxx, args.llvm_config)

    needs_default_work_dir = (
        args.pass_so is None
        or args.runtime_object is None
        or args.site_map is None
        or (args.report_json is None and not args.quiet)
    )
    work_dir = args.work_dir
    if work_dir is None and needs_default_work_dir:
        work_dir = Path(tempfile.mkdtemp(prefix="formtrig_cc_"))
    if work_dir is not None:
        work_dir.mkdir(parents=True, exist_ok=True)
    pass_so = args.pass_so or (work_dir / "libFormtrigPass.so")
    runtime_object = args.runtime_object or (work_dir / "formtrig_runtime.o")
    site_map = args.site_map or (work_dir / "formtrig_sites.tsv")
    report_json = args.report_json
    if report_json is None and not args.quiet:
        report_json = work_dir / "formtrig_cc_report.json"
    pass_load_mode = resolve_pass_load_mode(args.pass_load_mode, llvm_config)
    env_override = parse_env_assignments(args.env)
    if args.afl_cc:
        existing = env_override.get("AFL_CC") or os.environ.get("AFL_CC")
        if existing and existing != args.afl_cc:
            raise SystemExit(
                f"conflicting AFL_CC values: existing {existing!r}, --afl-cc {args.afl_cc!r}"
            )
        env_override["AFL_CC"] = args.afl_cc
    if args.afl_cxx:
        existing = env_override.get("AFL_CXX") or os.environ.get("AFL_CXX")
        if existing and existing != args.afl_cxx:
            raise SystemExit(
                f"conflicting AFL_CXX values: existing {existing!r}, --afl-cxx {args.afl_cxx!r}"
            )
        env_override["AFL_CXX"] = args.afl_cxx

    ensure_parent(pass_so)
    ensure_parent(runtime_object)
    ensure_parent(site_map)
    if not args.append_site_map and site_map.exists() and not args.dry_run:
        site_map.unlink()

    pass_cmd = build_pass_command(pass_cxx, llvm_config, pass_so)
    if args.no_build_pass:
        if not pass_so.exists():
            raise SystemExit(f"--no-build-pass requires existing pass: {pass_so}")
    else:
        run(pass_cmd, env=None, dry_run=args.dry_run, verbose=args.verbose)

    runtime_link_mode = "never" if args.no_link_runtime else args.runtime_link_mode
    link_runtime = needs_link_runtime(
        compiler_args, args.no_link_runtime, args.runtime_link_mode
    )
    runtime_cmd = None  # type: Optional[List[str]]
    runtime_for_target = None  # type: Optional[Path]
    if link_runtime:
        runtime_for_target = runtime_object
        runtime_cmd = build_runtime_command(args.runtime_cc, runtime_object)
        if args.no_build_runtime:
            if not runtime_object.exists():
                raise SystemExit(
                    f"--no-build-runtime requires existing runtime object: {runtime_object}"
                )
        else:
            run(runtime_cmd, env=None, dry_run=args.dry_run, verbose=args.verbose)

    env = os.environ.copy()
    env.update(env_override)
    env["FORMTRIG_SITE_MAP"] = str(site_map)
    env["FORMTRIG_INSTRUMENT_LEVEL"] = args.instrument_level
    source_args = compiler_source_args(compiler_args)
    skip_pass = should_skip_pass(compiler_args, args.skip_pass_regex)
    feature_macros = feature_test_macro_args(compiler_args, args.gnu_source)

    compile_cmd = target_compile_command(
        args.compiler,
        None if skip_pass else pass_so,
        compiler_args,
        pass_load_mode=pass_load_mode,
        runtime_object=runtime_for_target,
        runtime_libs=args.runtime_lib if args.runtime_lib is not None else ["-lm", "-lrt"],
        feature_macro_args=feature_macros,
    )
    run(compile_cmd, env=env, dry_run=args.dry_run, verbose=args.verbose)

    report = {
        "compiler": args.compiler,
        "afl_cc": env.get("AFL_CC"),
        "afl_cxx": env.get("AFL_CXX"),
        "pass_cxx": pass_cxx,
        "llvm_config": llvm_config,
        "compiler_args": compiler_args,
        "source_args": source_args,
        "instrument_level": args.instrument_level,
        "feature_macros": feature_macros,
        "gnu_source": args.gnu_source,
        "pass_load_mode": pass_load_mode,
        "runtime_link_mode": runtime_link_mode,
        "pass_so": str(pass_so),
        "runtime_object": str(runtime_object) if link_runtime else None,
        "runtime_linked": link_runtime,
        "pass_skipped": skip_pass,
        "skip_pass_regex": args.skip_pass_regex,
        "site_map": str(site_map),
        "commands": {
            "build_pass": pass_cmd,
            "build_runtime": runtime_cmd,
            "compile_target": compile_cmd,
        },
    }
    if site_map.exists():
        rows = [
            line
            for line in site_map.read_text(errors="replace").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        report["site_map_rows"] = len(rows)
    write_report(report_json, report)
    if not args.quiet:
        print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
