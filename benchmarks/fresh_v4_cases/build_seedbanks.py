#!/usr/bin/env python3
"""Build strict RNT seedbanks for FORMTRIG preflight-v2 fresh targets."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BIN = ROOT / "benchmarks" / "fresh_v4_cases" / "fresh_v4_cases"
INVENTORY = ROOT / "artifacts" / "fresh_v4_inventory.csv"
OUT_ROOT = ROOT / "artifacts" / "rnt_corpus"

FIELDS = [
    "target_id",
    "project",
    "program",
    "tc_category",
    "seed_id",
    "parent_seed_id",
    "content_sha256",
    "input_size",
    "reached_R",
    "triggered_T",
    "reached_count",
    "triggered_count",
    "arrival_timestamp",
    "time_s",
    "coverage_hash",
    "native_DT",
    "native_DT_a1",
    "native_DT_a2",
    "native_DT_a3",
    "native_DT_a4",
    "tc_root_state",
    "replay_hash",
    "replay_status",
    "metadata_status",
    "source_seedbank",
    "source_manifest",
    "source_seed",
    "producer",
    "hot_ranges",
    "target_context_hash",
]

INV_FIELDS = [
    "target_id",
    "project",
    "program",
    "canary_expression",
    "primary_tc_category",
    "secondary_tc_category",
    "target_location",
    "trigger_oracle",
    "initial_corpus",
    "build_command",
    "run_command",
    "sanitizer_mode",
    "notes",
]

TARGETS = {
    "T1_NUMERIC_ACTIONABLE": {
        "case": "numeric",
        "category": "numeric-margin",
        "expression": "byte0 >= 200",
        "location": "benchmarks/fresh_v4_cases/fresh_v4_cases.c:57#run_numeric_actionable",
        "seeds": [bytes([v]) + b"NUM" for v in [120, 128, 136, 144, 152, 160, 168, 176, 184, 188, 190, 192, 194, 196, 197, 198]],
    },
    "T2_EQUALITY_DIRECT_ANYOF": {
        "case": "anyof",
        "category": "equality/magic",
        "expression": "tag == 'A' || tag == 'B'",
        "location": "benchmarks/fresh_v4_cases/fresh_v4_cases.c:73#run_equality_direct_anyof",
        "seeds": [bytes([v]) + b"TAG" for v in [63, 64, 67, 68, 69, 70, 80, 81, 82, 83, 90, 48, 49, 50, 51, 52]],
    },
    "T3_EQUALITY_TRANSFORMED": {
        "case": "transformed",
        "category": "equality/magic",
        "expression": "hdr == \"TX\" && checksum4(payload) == 0xc7",
        "location": "benchmarks/fresh_v4_cases/fresh_v4_cases.c:94#run_equality_transformed",
        "seeds": [b"TX" + bytes([i, i + 1, i + 2, i + 3]) for i in range(1, 17)],
    },
    "T4_BINARY_NULL_LIFT": {
        "case": "null",
        "category": "binary-state-null",
        "expression": "ctx.obj == NULL",
        "location": "benchmarks/fresh_v4_cases/fresh_v4_cases.c:116#run_binary_null_lift",
        "seeds": [b"N" + f"{i:02d}".encode() + b"OBJpayload" + bytes([65 + i]) for i in range(16)],
    },
    "T5_GUARDED_BINARY": {
        "case": "guarded",
        "category": "binary-state-null",
        "expression": "hdr == 'G' && ctx.obj == NULL",
        "location": "benchmarks/fresh_v4_cases/fresh_v4_cases.c:139#run_guarded_binary",
        "seeds": [b"H" + f"{i:02d}".encode() + b"OBJguard" for i in range(8)]
        + [b"G" + f"{i:02d}".encode() + b"OBJguard" for i in range(8)],
    },
    "T6_SAME_OBJECT_LIFECYCLE": {
        "case": "lifecycle",
        "category": "compound-sequence-lifecycle",
        "expression": "create(obj) before release(obj) before use(obj) && SAME_OBJECT(obj)",
        "location": "benchmarks/fresh_v4_cases/fresh_v4_cases.c:162#run_same_object_lifecycle",
        "seeds": [bytes([ord("C"), 1 + i, ord("R"), 20 + i, ord("U"), 1 + i]) for i in range(16)],
    },
}


def replay(case: str, data: bytes) -> dict:
    proc = subprocess.run([str(BIN), case], input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    lines = [line for line in proc.stdout.decode(errors="replace").splitlines() if line.startswith("{")]
    if not lines:
        raise RuntimeError(f"no JSON output for case={case} rc={proc.returncode} stderr={proc.stderr!r}")
    rec = json.loads(lines[-1])
    rec["returncode"] = proc.returncode
    return rec


def build_one(target_id: str, meta: dict[str, object]) -> int:
    out = OUT_ROOT / target_id
    seed_dir = out / "seeds"
    seed_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    for index, data in enumerate(meta["seeds"]):  # type: ignore[index]
        rec = replay(str(meta["case"]), data)
        if not rec.get("reached") or rec.get("triggered") or rec.get("crash_predicate"):
            raise RuntimeError(f"{target_id} seed is not strict RNT: {data!r} -> {rec}")
        digest = hashlib.sha256(data).hexdigest()
        seed_id = f"id:{index:06d},sha256:{digest[:16]}"
        seed_path = seed_dir / seed_id
        seed_path.write_bytes(data)
        replay_hash = hashlib.sha256(json.dumps(rec, sort_keys=True).encode()).hexdigest()
        row = {
            "target_id": target_id,
            "project": "fresh_v4_cases",
            "program": str(BIN),
            "tc_category": str(meta["category"]),
            "seed_id": seed_id,
            "parent_seed_id": "ROOT",
            "content_sha256": digest,
            "input_size": str(len(data)),
            "reached_R": "1",
            "triggered_T": "0",
            "reached_count": "1",
            "triggered_count": "0",
            "arrival_timestamp": "0",
            "time_s": str(index),
            "coverage_hash": str(rec.get("trace_signature", "")),
            "native_DT": str(rec.get("D_T", 1)),
            "native_DT_a1": str(rec.get("native_DT_a1", "")),
            "native_DT_a2": str(rec.get("native_DT_a2", "")),
            "native_DT_a3": str(rec.get("native_DT_a3", "")),
            "native_DT_a4": str(rec.get("native_DT_a4", "")),
            "tc_root_state": str(rec.get("root_state", "")),
            "replay_hash": replay_hash,
            "replay_status": "kept_rnt",
            "metadata_status": "fresh_v4_replay_verified_rnt",
            "source_seedbank": str(out),
            "source_manifest": str(out / "metadata.csv"),
            "source_seed": str(seed_path),
            "producer": "fresh_v4_replay",
            "hot_ranges": json.dumps(rec.get("hot_ranges", []), separators=(",", ":")),
            "target_context_hash": str(rec.get("target_context_hash", target_id)),
        }
        rows.append(row)
    with (out / "metadata.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    (out / "build_status.json").write_text(json.dumps({"target_id": target_id, "seed_count": len(rows)}, indent=2) + "\n")
    return len(rows)


def main() -> int:
    if not BIN.exists():
        raise SystemExit(f"missing target binary: {BIN}")
    inventory_rows = []
    built = {}
    for target_id, meta in TARGETS.items():
        built[target_id] = build_one(target_id, meta)
        inventory_rows.append(
            {
                "target_id": target_id,
                "project": "fresh_v4_cases",
                "program": str(BIN),
                "canary_expression": str(meta["expression"]),
                "primary_tc_category": str(meta["category"]),
                "secondary_tc_category": "",
                "target_location": str(meta["location"]),
                "trigger_oracle": "JSON triggered == true",
                "initial_corpus": str(OUT_ROOT / target_id / "seeds"),
                "build_command": f"gcc -O2 -Wall -Wextra -Werror -o {BIN} {BIN}.c",
                "run_command": f"{BIN} {meta['case']} @@",
                "sanitizer_mode": "none",
                "notes": "fresh_v4_preflight_v2_semantic_gate",
            }
        )
    with INVENTORY.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=INV_FIELDS)
        writer.writeheader()
        writer.writerows(inventory_rows)
    print(json.dumps({"built": built, "inventory": str(INVENTORY)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
