#!/usr/bin/env python3
"""GPAC SCAL-reference MP4 typed-mutation hook.

This hook is a GPAC_3403 repair hook for the B12 scaffold line.  It keeps the
two-track MP4 + track-2 -> track-1 SCAL relation intact, while using the
Annex-B HEVC typed hook to mutate the enhanced track payload.  It does not
replay the endpoint or inspect the crash oracle.
"""

from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MP4BOX = Path("/tmp/formtrig_gpac3403_src/bin/gcc/MP4Box")
DEFAULT_BASE_HEVC = Path("/tmp/formtrig_gpac3403_blackwhite_seed/blackwhite_yuv444p-frame.hevc")
DEFAULT_HEVC_HOOK = REPO_ROOT / "scripts" / "formtrig_hooks" / "hevc_annexb_structure_hook.py"
DEFAULT_BASE_TRACK_ID = 1
DEFAULT_REF_TRACK_ID = 2


def env_path(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value) if value else default


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return int(value, 0)


def load_hook(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("gpac_scal_ref_hevc_hook", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load HEVC hook: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def run_command(cmd: list[str], stdout_path: Path, stderr_path: Path) -> int:
    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
        result = subprocess.run(cmd, stdout=stdout, stderr=stderr, check=False)
    return result.returncode


def build_scal_ref_mp4(
    *,
    source_hevc: bytes,
    start: int,
    span: int,
    off: int,
    op: int,
    sample: int,
    work_dir: Path,
) -> bytes | None:
    mp4box = env_path("FORMTRIG_GPAC3403_MP4BOX", DEFAULT_MP4BOX)
    hevc_hook_path = env_path("FORMTRIG_GPAC3403_HEVC_HOOK", DEFAULT_HEVC_HOOK)
    base_track_id = env_int("FORMTRIG_GPAC3403_BASE_TRACK_ID", DEFAULT_BASE_TRACK_ID)
    ref_track_id = env_int("FORMTRIG_GPAC3403_REF_TRACK_ID", DEFAULT_REF_TRACK_ID)
    hevc_start = env_int("FORMTRIG_GPAC3403_HEVC_START", 0)
    hevc_span = env_int("FORMTRIG_GPAC3403_HEVC_SPAN", len(source_hevc))
    hevc_off = env_int("FORMTRIG_GPAC3403_HEVC_OFF", 6)
    hevc_op = max(0, op + env_int("FORMTRIG_GPAC3403_HEVC_OP_BIAS", 0))
    hevc_sample = max(0, sample + env_int("FORMTRIG_GPAC3403_HEVC_SAMPLE_BIAS", 0))
    work_dir.mkdir(parents=True, exist_ok=True)

    if start > 0 or span > 0 or off > 0:
        # Keep these parameters observable for provenance while defaulting to
        # HEVC-aligned offsets.  They can be enabled via env overrides.
        hevc_start = env_int("FORMTRIG_GPAC3403_HEVC_START", hevc_start)
        hevc_span = env_int("FORMTRIG_GPAC3403_HEVC_SPAN", hevc_span)
        hevc_off = env_int("FORMTRIG_GPAC3403_HEVC_OFF", hevc_off)

    hook = load_hook(hevc_hook_path)
    enhanced = hook.mutate(
        source_hevc,
        start=hevc_start,
        span=hevc_span,
        off=hevc_off,
        op=hevc_op,
        sample=hevc_sample,
    )

    base_hevc = work_dir / "base.hevc"
    enhanced_hevc = work_dir / "enhanced.hevc"
    mp4_path = work_dir / "two_track_scal_ref.mp4"
    base_hevc.write_bytes(source_hevc)
    enhanced_hevc.write_bytes(enhanced)

    commands = [
        (["-add", str(base_hevc), str(mp4_path)], "build_base"),
        (["-add", str(enhanced_hevc), str(mp4_path)], "build_enhanced"),
        (["-ref", f"{ref_track_id}:scal:{base_track_id}", str(mp4_path)], "add_scal_ref"),
    ]
    for args, label in commands:
        rc = run_command(
            [str(mp4box), *args],
            work_dir / f"{label}.stdout",
            work_dir / f"{label}.stderr",
        )
        if rc != 0:
            return None
    if not mp4_path.is_file():
        return None
    return mp4_path.read_bytes()


def mutate(data: bytes, start: int, span: int, off: int, op: int, sample: int) -> bytes:
    base_hevc_path = env_path("FORMTRIG_GPAC3403_BASE_HEVC", DEFAULT_BASE_HEVC)
    if base_hevc_path.is_file():
        source_hevc = base_hevc_path.read_bytes()
    else:
        source_hevc = data
    if not source_hevc:
        return data
    with tempfile.TemporaryDirectory(prefix="formtrig_gpac_scal_ref_hook_") as tmp:
        built = build_scal_ref_mp4(
            source_hevc=source_hevc,
            start=start,
            span=span,
            off=off,
            op=op,
            sample=sample,
            work_dir=Path(tmp),
        )
    return built if built else data


def main(argv: list[str]) -> int:
    if len(argv) < 15:
        return 2
    orig_path, mut_path, out_path = Path(argv[1]), Path(argv[2]), Path(argv[3])
    start = int(argv[5])
    span = int(argv[6])
    off = int(argv[7])
    op = int(argv[8])
    sample = int(argv[9])

    original = orig_path.read_bytes()
    mutated = mut_path.read_bytes()
    source = mutated if mutated else original
    repaired = mutate(source, start=start, span=span, off=off, op=op, sample=sample)
    if repaired == source and mutated:
        repaired = mutated
    Path(out_path).write_bytes(repaired)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
