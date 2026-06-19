#!/usr/bin/env python3
"""Replay GPAC_3403 HEVC frontier variants through native FORMTRIG.

This is a diagnostic/repair helper for the GPAC_3403 B6 path.  It starts from a
saved FORMTRIG frontier input, enumerates Annex-B HEVC typed-hook variants, and
replays each variant with the native runtime enabled.  The output answers
whether the current last-mile problem is endpoint reachability, hook search
space, or AFL scheduling throughput.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import json
import os
import shlex
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable


ROLE_NAMES = {
    0: "unknown",
    1: "root_observe",
    2: "guard",
    3: "producer",
    4: "desired_producer",
    5: "opposite_producer",
    6: "use",
    7: "lifecycle_event",
    8: "same_object",
    9: "input_influence",
    10: "repair_hook",
}

SANITIZER_MARKERS = (
    b"ERROR: AddressSanitizer",
    b"AddressSanitizer:",
    b"SUMMARY: AddressSanitizer",
    b"ERROR: UndefinedBehaviorSanitizer",
    b"SUMMARY: UndefinedBehaviorSanitizer",
)


@dataclass(frozen=True)
class MutationCase:
    index: int
    op: int
    sample: int
    start: int
    span: int
    off: int
    sha256: str
    size: int
    path: str


@dataclass
class EndpointProbe:
    kind: str
    rep: int
    input: str
    stdout_log: str
    stderr_log: str
    exit_code: int | None
    timed_out: bool
    sanitizer_crash: bool
    native_crash: bool
    stdout_sha256: str
    stderr_sha256: str


@dataclass
class ReplayRecord:
    index: int
    op: int
    sample: int
    start: int
    span: int
    off: int
    sha256: str
    size: int
    path: str
    runtime_log: str
    stdout_log: str
    stderr_log: str
    exit_code: int | None
    timed_out: bool
    reached: bool
    triggered: bool
    spec_lifted: bool
    target_hit_count: int
    d_f_spec_lifted: float | None
    roles: list[str]
    role_bits: list[str]
    trace_signature: str | None
    endpoint_probes: list[EndpointProbe] = field(default_factory=list)


def load_hook(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("formtrig_hevc_hook", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load hook: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_range_token(token: str) -> tuple[int, int]:
    if ":" not in token:
        raise argparse.ArgumentTypeError("range must be START:LEN")
    start_s, len_s = token.split(":", 1)
    try:
        start = int(start_s, 0)
        length = int(len_s, 0)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("range must use integer START:LEN") from exc
    if start < 0 or length <= 0:
        raise argparse.ArgumentTypeError("range START must be >=0 and LEN >0")
    return start, length


def binding_ranges(binding_spec: Path | None, data_len: int) -> list[tuple[int, int]]:
    if not binding_spec:
        return []
    ranges: list[tuple[int, int]] = []
    pending_start: int | None = None
    for raw in binding_spec.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("range_start:"):
            try:
                pending_start = int(line.split(":", 1)[1].strip().strip("'\""), 0)
            except ValueError:
                pending_start = None
        elif line.startswith("range_len:") and pending_start is not None:
            try:
                length = int(line.split(":", 1)[1].strip().strip("'\""), 0)
            except ValueError:
                pending_start = None
                continue
            start = min(pending_start, data_len)
            clipped = min(length, max(0, data_len - start))
            if clipped > 0:
                ranges.append((start, clipped))
            pending_start = None
    return ranges


def target_site_ids_from_event_map(path: Path | None) -> str:
    if not path:
        return ""
    root_ids: list[str] = []
    all_ids: list[str] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            site_id = (row.get("site_id") or "").strip()
            if not site_id or site_id == "*":
                continue
            if site_id not in all_ids:
                all_ids.append(site_id)
            if (row.get("role") or "").strip() == "root_observe" and site_id not in root_ids:
                root_ids.append(site_id)
    return ",".join(root_ids or all_ids)


def candidate_offsets(hook: ModuleType, data: bytes, start: int, span: int) -> list[int]:
    if not data:
        return []
    end = min(len(data), start + max(span, 1))
    offsets = {start, max(start, end - 1)}
    if end > start + 1:
        offsets.update(
            start + int((end - start - 1) * frac)
            for frac in (0.125, 0.25, 0.5, 0.75, 0.875)
        )

    for nalu in hook.parse_nalus(data):
        for base in (nalu.start, nalu.header_start, nalu.payload_start):
            if start <= base < end:
                offsets.add(base)
        body = min(nalu.payload_start + 2, max(nalu.payload_start, nalu.end - 1))
        for delta in (0, 1, 2, 4, 8, 16, 23, 32, 64, 96, 128):
            off = min(nalu.end - 1, body + delta)
            if start <= off < end:
                offsets.add(off)

    return sorted(off for off in offsets if 0 <= off < len(data))


def generate_variants(
    hook: ModuleType,
    seed: bytes,
    ranges: Iterable[tuple[int, int]],
    max_variants: int,
    op_start: int,
    op_count: int,
    sample_count: int,
    variants_dir: Path,
    schedule: str = "nested",
) -> list[MutationCase]:
    variants_dir.mkdir(parents=True, exist_ok=True)
    seen = {sha256_bytes(seed)}
    variants: list[MutationCase] = []
    op_values = list(range(op_start, op_start + op_count))

    def add_variant(start: int, span: int, off: int, op: int, sample: int) -> bool:
        mutated = hook.mutate(seed, start=start, span=span, off=off, op=op, sample=sample)
        digest = sha256_bytes(mutated)
        if digest in seen:
            return False
        seen.add(digest)
        index = len(variants)
        path = variants_dir / f"variant_{index:06d}.hevc"
        path.write_bytes(mutated)
        variants.append(
            MutationCase(
                index=index,
                op=op,
                sample=sample,
                start=start,
                span=span,
                off=off,
                sha256=digest,
                size=len(mutated),
                path=str(path),
            )
        )
        return len(variants) >= max_variants

    range_infos: list[tuple[int, int, list[int]]] = []
    for start, span in ranges:
        if start >= len(seed):
            continue
        span = min(span, len(seed) - start)
        if span <= 0:
            continue
        offsets = candidate_offsets(hook, seed, start, span)
        if offsets:
            range_infos.append((start, span, offsets))

    if schedule == "round_robin":
        max_depth = max((max(sample_count, len(offsets)) for _, _, offsets in range_infos), default=0)
        for depth in range(max_depth):
            for start, span, offsets in range_infos:
                off = offsets[depth % len(offsets)]
                sample = depth % sample_count
                for op in op_values:
                    if add_variant(start, span, off, op, sample):
                        return variants
        return variants

    for start, span, offsets in range_infos:
        if len(variants) >= max_variants:
            break
        for off in offsets:
            for op in op_values:
                for sample in range(sample_count):
                    if add_variant(start, span, off, op, sample):
                        return variants
    return variants


def last_json_line(path: Path) -> dict[str, Any] | None:
    if not path.exists() or path.stat().st_size == 0:
        return None
    last: dict[str, Any] | None = None
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                last = parsed
    return last


def as_number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def roles_from_record(record: dict[str, Any] | None) -> tuple[list[str], list[str]]:
    if not record:
        return [], []
    roles: set[str] = set()
    for component in record.get("components") or []:
        if not isinstance(component, dict):
            continue
        role = component.get("role")
        if isinstance(role, int):
            roles.add(ROLE_NAMES.get(role, str(role)))
    role_bits: set[str] = set()
    for signal in record.get("atom_signals") or []:
        if not isinstance(signal, dict):
            continue
        bits = signal.get("role_bits")
        if not isinstance(bits, int):
            continue
        for role_id, role_name in ROLE_NAMES.items():
            if role_id and bits & (1 << role_id):
                role_bits.add(role_name)
    return sorted(roles), sorted(role_bits)


def command_for_variant(target_cmd: list[str], variant_path: str) -> list[str]:
    used_at = any("@@" in arg for arg in target_cmd)
    if used_at:
        return [arg.replace("@@", variant_path) for arg in target_cmd]
    return target_cmd


def parse_env_pairs(pairs: list[str] | None) -> dict[str, str]:
    env: dict[str, str] = {}
    for pair in pairs or []:
        if "=" not in pair:
            raise argparse.ArgumentTypeError("--endpoint-env entries must use KEY=VALUE")
        key, value = pair.split("=", 1)
        key = key.strip()
        if not key:
            raise argparse.ArgumentTypeError("--endpoint-env entries need a non-empty key")
        env[key] = value
    return env


def lift_spec_pre_reach_enabled(lift_spec: Path | None) -> str:
    if not lift_spec:
        return "0"
    text = lift_spec.read_text(encoding="utf-8", errors="replace")
    markers = ("pre_reach", "pre-reach", "before_reach", "before-reach", "any", "both")
    return "1" if any(marker in text for marker in markers) else "0"


def is_native_crash(exit_code: int | None, sanitizer_crash: bool) -> bool:
    if exit_code is None or sanitizer_crash:
        return False
    return exit_code < 0 or 128 <= exit_code <= 159


def should_run_endpoint_probe(endpoint_filter: str, reached: bool, d_f: float | None, d_f_max: float) -> bool:
    if endpoint_filter == "all":
        return True
    if endpoint_filter == "reached":
        return reached
    if endpoint_filter == "reached-d-f":
        return reached and d_f is not None and d_f <= d_f_max
    raise ValueError(f"unknown endpoint filter: {endpoint_filter}")


def run_endpoint_probes(
    input_path: str,
    kind: str,
    log_prefix: str,
    endpoint_cmd: list[str],
    out_dir: Path,
    endpoint_env: dict[str, str],
    timeout_s: float,
    reps: int,
    sanitizer_exit_code: int | None,
) -> list[EndpointProbe]:
    probes: list[EndpointProbe] = []
    logs_dir = out_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    for rep in range(1, reps + 1):
        stdout_log = logs_dir / f"{log_prefix}.endpoint_{rep}.stdout"
        stderr_log = logs_dir / f"{log_prefix}.endpoint_{rep}.stderr"
        env = os.environ.copy()
        env.update(endpoint_env)
        cmd = command_for_variant(endpoint_cmd, input_path)
        exit_code: int | None = None
        timed_out = False
        try:
            stdin_handle = None
            if not any("@@" in arg for arg in endpoint_cmd):
                stdin_handle = open(input_path, "rb")
            with stdout_log.open("wb") as stdout, stderr_log.open("wb") as stderr:
                result = subprocess.run(
                    cmd,
                    stdin=stdin_handle,
                    stdout=stdout,
                    stderr=stderr,
                    env=env,
                    timeout=timeout_s,
                    check=False,
                )
            exit_code = result.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            if "stdin_handle" in locals() and stdin_handle is not None:
                stdin_handle.close()

        stderr_bytes = stderr_log.read_bytes() if stderr_log.exists() else b""
        sanitizer_crash = any(marker in stderr_bytes for marker in SANITIZER_MARKERS)
        if sanitizer_exit_code is not None and exit_code == sanitizer_exit_code:
            sanitizer_crash = True
        probes.append(
            EndpointProbe(
                kind=kind,
                rep=rep,
                input=input_path,
                stdout_log=str(stdout_log),
                stderr_log=str(stderr_log),
                exit_code=exit_code,
                timed_out=timed_out,
                sanitizer_crash=sanitizer_crash,
                native_crash=is_native_crash(exit_code, sanitizer_crash),
                stdout_sha256=sha256_file(stdout_log) if stdout_log.exists() else "",
                stderr_sha256=sha256_file(stderr_log) if stderr_log.exists() else "",
            )
        )
    return probes


def replay_variant(
    case: MutationCase,
    target_cmd: list[str],
    out_dir: Path,
    env_base: dict[str, str],
    timeout_s: float,
    endpoint_cmd: list[str] | None = None,
    endpoint_env: dict[str, str] | None = None,
    endpoint_timeout_s: float = 5.0,
    endpoint_replays: int = 1,
    endpoint_sanitizer_exit_code: int | None = 86,
    endpoint_filter: str = "all",
    endpoint_d_f_max: float = 1.0,
) -> ReplayRecord:
    runtime_log = out_dir / "logs" / f"variant_{case.index:06d}.runtime.jsonl"
    stdout_log = out_dir / "logs" / f"variant_{case.index:06d}.stdout"
    stderr_log = out_dir / "logs" / f"variant_{case.index:06d}.stderr"
    runtime_log.parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env.update(env_base)
    env["FORMTRIG_LOG"] = str(runtime_log)

    cmd = command_for_variant(target_cmd, case.path)
    exit_code: int | None = None
    timed_out = False
    try:
        stdin_handle = None
        if not any("@@" in arg for arg in target_cmd):
            stdin_handle = open(case.path, "rb")
        with stdout_log.open("wb") as stdout, stderr_log.open("wb") as stderr:
            result = subprocess.run(
                cmd,
                stdin=stdin_handle,
                stdout=stdout,
                stderr=stderr,
                env=env,
                timeout=timeout_s,
                check=False,
            )
        exit_code = result.returncode
    except subprocess.TimeoutExpired:
        timed_out = True
    finally:
        if "stdin_handle" in locals() and stdin_handle is not None:
            stdin_handle.close()

    runtime = last_json_line(runtime_log)
    roles, role_bits = roles_from_record(runtime)
    d_f = as_number(runtime.get("D_F_spec_lifted")) if runtime else None
    reached = bool(runtime and runtime.get("reached") is True)
    triggered = bool(
        runtime
        and (runtime.get("triggered") is True or runtime.get("crash_predicate") is True)
    )
    spec_lifted = bool(runtime and runtime.get("uses_spec_lifted") is True)
    target_hit_count = 0
    if runtime and isinstance(runtime.get("target_hit_count"), int):
        target_hit_count = int(runtime["target_hit_count"])
    endpoint_probes: list[EndpointProbe] = []
    if endpoint_cmd and should_run_endpoint_probe(endpoint_filter, reached, d_f, endpoint_d_f_max):
        endpoint_probes = run_endpoint_probes(
            input_path=case.path,
            kind="variant",
            log_prefix=f"variant_{case.index:06d}",
            endpoint_cmd=endpoint_cmd,
            out_dir=out_dir,
            endpoint_env=endpoint_env or {},
            timeout_s=endpoint_timeout_s,
            reps=endpoint_replays,
            sanitizer_exit_code=endpoint_sanitizer_exit_code,
        )
    return ReplayRecord(
        index=case.index,
        op=case.op,
        sample=case.sample,
        start=case.start,
        span=case.span,
        off=case.off,
        sha256=case.sha256,
        size=case.size,
        path=case.path,
        runtime_log=str(runtime_log),
        stdout_log=str(stdout_log),
        stderr_log=str(stderr_log),
        exit_code=exit_code,
        timed_out=timed_out,
        reached=reached,
        triggered=triggered,
        spec_lifted=spec_lifted,
        target_hit_count=target_hit_count,
        d_f_spec_lifted=d_f,
        roles=roles,
        role_bits=role_bits,
        trace_signature=str(runtime.get("trace_signature")) if runtime and runtime.get("trace_signature") else None,
        endpoint_probes=endpoint_probes,
    )


def summarize(records: list[ReplayRecord], generated: int, seed_sha256: str) -> dict[str, Any]:
    d_f_values = [r.d_f_spec_lifted for r in records if r.d_f_spec_lifted is not None]
    role_counts: dict[str, int] = {}
    reached_role_counts: dict[str, int] = {}
    for record in records:
        record_roles = set(record.roles) | set(record.role_bits)
        for role in record_roles:
            role_counts[role] = role_counts.get(role, 0) + 1
            if record.reached:
                reached_role_counts[role] = reached_role_counts.get(role, 0) + 1

    best = sorted(
        (r for r in records if r.d_f_spec_lifted is not None),
        key=lambda r: (r.d_f_spec_lifted if r.d_f_spec_lifted is not None else 1.0e300, r.index),
    )[:10]
    best_reached = sorted(
        (r for r in records if r.reached and r.d_f_spec_lifted is not None),
        key=lambda r: (r.d_f_spec_lifted if r.d_f_spec_lifted is not None else 1.0e300, r.index),
    )[:10]
    triggered = [r for r in records if r.triggered]
    endpoint_records = [probe for record in records for probe in record.endpoint_probes]
    endpoint_exit_counts: dict[str, int] = {}
    for probe in endpoint_records:
        key = "timeout" if probe.timed_out else str(probe.exit_code)
        endpoint_exit_counts[key] = endpoint_exit_counts.get(key, 0) + 1
    return {
        "schema": "formtrig_gpac3403_hevc_frontier_sweep_v1",
        "seed_sha256": seed_sha256,
        "generated_variants": generated,
        "replayed_variants": len(records),
        "reached": sum(1 for r in records if r.reached),
        "triggered": len(triggered),
        "rnt": sum(1 for r in records if r.reached and not r.triggered),
        "spec_lifted": sum(1 for r in records if r.spec_lifted),
        "timeouts": sum(1 for r in records if r.timed_out),
        "d_f_spec_lifted_min": min(d_f_values) if d_f_values else None,
        "d_f_spec_lifted_max": max(d_f_values) if d_f_values else None,
        "d_f_spec_lifted_values": sorted(set(d_f_values)),
        "role_sample_counts": dict(sorted(role_counts.items())),
        "reached_role_sample_counts": dict(sorted(reached_role_counts.items())),
        "same_object_samples": role_counts.get("same_object", 0),
        "reached_same_object_samples": reached_role_counts.get("same_object", 0),
        "first_trigger": asdict(triggered[0]) if triggered else None,
        "best_frontier_variants": [asdict(r) for r in best],
        "best_reached_frontier_variants": [asdict(r) for r in best_reached],
        "endpoint_replayed_variants": sum(1 for r in records if r.endpoint_probes),
        "endpoint_probe_runs": len(endpoint_records),
        "endpoint_sanitizer_crashes": sum(
            1 for r in records if any(probe.sanitizer_crash for probe in r.endpoint_probes)
        ),
        "endpoint_native_crashes": sum(
            1 for r in records if any(probe.native_crash for probe in r.endpoint_probes)
        ),
        "endpoint_timeouts": sum(1 for probe in endpoint_records if probe.timed_out),
        "endpoint_exit_code_counts": dict(sorted(endpoint_exit_counts.items())),
        "first_endpoint_sanitizer_crash": asdict(
            next(
                (
                    probe
                    for record in records
                    for probe in record.endpoint_probes
                    if probe.sanitizer_crash
                ),
                None,
            )
        )
        if any(probe.sanitizer_crash for probe in endpoint_records)
        else None,
        "first_endpoint_native_crash": asdict(
            next(
                (
                    probe
                    for record in records
                    for probe in record.endpoint_probes
                    if probe.native_crash
                ),
                None,
            )
        )
        if any(probe.native_crash for probe in endpoint_records)
        else None,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", required=True, type=Path)
    parser.add_argument("--hook", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--target-bug", default="GPAC_3403")
    parser.add_argument("--lift-spec", type=Path)
    parser.add_argument("--binding-spec", type=Path)
    parser.add_argument("--runtime-event-map", type=Path)
    parser.add_argument("--target-site-ids")
    parser.add_argument("--range", dest="ranges", action="append", type=parse_range_token)
    parser.add_argument("--max-variants", type=int, default=256)
    parser.add_argument("--max-replays", type=int, default=256)
    parser.add_argument("--op-start", type=int, default=0)
    parser.add_argument("--ops", type=int, default=16)
    parser.add_argument("--samples", type=int, default=16)
    parser.add_argument("--schedule", choices=("nested", "round_robin"), default="nested")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--endpoint-cmd", help="Optional shell-like endpoint replay command; use @@ for the variant path.")
    parser.add_argument("--endpoint-env", action="append", default=[])
    parser.add_argument("--endpoint-timeout", type=float, default=5.0)
    parser.add_argument("--endpoint-replays", type=int, default=1)
    parser.add_argument("--endpoint-sanitizer-exit-code", type=int, default=86)
    parser.add_argument("--endpoint-filter", choices=("all", "reached", "reached-d-f"), default="all")
    parser.add_argument("--endpoint-d-f-max", type=float, default=1.0)
    parser.add_argument("--endpoint-positive-control", type=Path)
    parser.add_argument("target_cmd", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    if args.target_cmd and args.target_cmd[0] == "--":
        args.target_cmd = args.target_cmd[1:]
    if not args.target_cmd:
        parser.error("target command is required after --")
    if args.max_variants <= 0 or args.max_replays <= 0:
        parser.error("--max-variants and --max-replays must be positive")
    if args.op_start < 0:
        parser.error("--op-start must be non-negative")
    if args.ops <= 0 or args.samples <= 0:
        parser.error("--ops and --samples must be positive")
    if args.endpoint_replays <= 0:
        parser.error("--endpoint-replays must be positive")
    endpoint_cmd = shlex.split(args.endpoint_cmd) if args.endpoint_cmd else None
    if args.endpoint_cmd and not endpoint_cmd:
        parser.error("--endpoint-cmd must not be empty")
    if args.endpoint_positive_control and not endpoint_cmd:
        parser.error("--endpoint-positive-control requires --endpoint-cmd")
    try:
        endpoint_env = parse_env_pairs(args.endpoint_env)
    except argparse.ArgumentTypeError as exc:
        parser.error(str(exc))

    seed = args.seed.read_bytes()
    hook = load_hook(args.hook)
    args.out.mkdir(parents=True, exist_ok=True)
    variants_dir = args.out / "variants"

    ranges = list(args.ranges or [])
    ranges.extend(binding_ranges(args.binding_spec, len(seed)))
    if not ranges:
        ranges = [(0, len(seed))]
    ranges = [(start, min(length, max(0, len(seed) - start))) for start, length in ranges]
    ranges = [(start, length) for start, length in ranges if length > 0]

    generated = generate_variants(
        hook=hook,
        seed=seed,
        ranges=ranges,
        max_variants=args.max_variants,
        op_start=args.op_start,
        op_count=args.ops,
        sample_count=args.samples,
        variants_dir=variants_dir,
        schedule=args.schedule,
    )

    env_base = {
        "FORMTRIG_TARGET_BUG": args.target_bug,
        "FORMTRIG_PUBLISH_EAGER": "1",
        "FORMTRIG_ALLOW_HEURISTIC_LIFT": "0",
        "FORMTRIG_OBSERVE_HEURISTIC_LIFT": "0",
        "FORMTRIG_ALLOW_MANUAL_LIFT": "0",
        "FORMTRIG_PRE_REACH_EVENTS": lift_spec_pre_reach_enabled(args.lift_spec),
    }
    target_site_ids = args.target_site_ids or target_site_ids_from_event_map(args.runtime_event_map)
    if target_site_ids:
        env_base["FORMTRIG_TARGET_SITE_IDS"] = target_site_ids
    if args.lift_spec:
        env_base["FORMTRIG_LIFT_SPEC"] = str(args.lift_spec)

    records: list[ReplayRecord] = []
    started = time.time()
    for case in generated[: args.max_replays]:
        records.append(
            replay_variant(
                case=case,
                target_cmd=args.target_cmd,
                out_dir=args.out,
                env_base=env_base,
                timeout_s=args.timeout,
                endpoint_cmd=endpoint_cmd,
                endpoint_env=endpoint_env,
                endpoint_timeout_s=args.endpoint_timeout,
                endpoint_replays=args.endpoint_replays,
                endpoint_sanitizer_exit_code=args.endpoint_sanitizer_exit_code,
                endpoint_filter=args.endpoint_filter,
                endpoint_d_f_max=args.endpoint_d_f_max,
            )
        )

    summary = summarize(records, len(generated), sha256_bytes(seed))
    positive_control: list[EndpointProbe] = []
    if args.endpoint_positive_control and endpoint_cmd:
        positive_control = run_endpoint_probes(
            input_path=str(args.endpoint_positive_control),
            kind="positive_control",
            log_prefix="positive_control",
            endpoint_cmd=endpoint_cmd,
            out_dir=args.out,
            endpoint_env=endpoint_env,
            timeout_s=args.endpoint_timeout,
            reps=args.endpoint_replays,
            sanitizer_exit_code=args.endpoint_sanitizer_exit_code,
        )
    summary["duration_s"] = round(time.time() - started, 3)
    summary["seed"] = str(args.seed)
    summary["hook"] = str(args.hook)
    summary["lift_spec"] = str(args.lift_spec) if args.lift_spec else None
    summary["binding_spec"] = str(args.binding_spec) if args.binding_spec else None
    summary["runtime_event_map"] = str(args.runtime_event_map) if args.runtime_event_map else None
    summary["target_site_ids"] = target_site_ids
    summary["target_cmd"] = args.target_cmd
    summary["ranges"] = ranges
    summary["op_start"] = args.op_start
    summary["ops"] = args.ops
    summary["samples"] = args.samples
    summary["schedule"] = args.schedule
    summary["endpoint_cmd"] = endpoint_cmd
    summary["endpoint_env_keys"] = sorted(endpoint_env)
    summary["endpoint_replays"] = args.endpoint_replays if endpoint_cmd else 0
    summary["endpoint_timeout"] = args.endpoint_timeout if endpoint_cmd else None
    summary["endpoint_sanitizer_exit_code"] = args.endpoint_sanitizer_exit_code if endpoint_cmd else None
    summary["endpoint_filter"] = args.endpoint_filter if endpoint_cmd else None
    summary["endpoint_d_f_max"] = args.endpoint_d_f_max if endpoint_cmd else None
    summary["endpoint_positive_control"] = [asdict(probe) for probe in positive_control]

    with (args.out / "records.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(asdict(record), sort_keys=True) + "\n")
    (args.out / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
