#!/usr/bin/env python3
"""Build RNT seedbanks for FORMTRIG v3 fresh smoke targets."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BIN = ROOT / "benchmarks" / "fresh_v3_cases" / "fresh_v3_cases"
INVENTORY = ROOT / "artifacts" / "fresh_v3_inventory.csv"
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
    "tc_root_state",
    "replay_hash",
    "replay_status",
    "metadata_status",
    "source_seedbank",
    "source_manifest",
    "source_seed",
    "producer",
    "hot_ranges",
]

TARGETS = {
    "FRESH_NUMERIC_MARGIN": {
        "case": "numeric",
        "category": "numeric-margin",
        "expression": "byte0 >= 80",
        "location": "benchmarks/fresh_v3_cases/fresh_v3_cases.c:75#run_numeric_margin",
        "seeds": [b"Oaaa", b"Nbbb", b"Axxx", b"\x10num", b"\x00low"],
    },
    "FRESH_ANY_OF": {
        "case": "anyof",
        "category": "equality/magic",
        "expression": "tag == 'A' || tag == 'B'",
        "location": "benchmarks/fresh_v3_cases/fresh_v3_cases.c:55#run_anyof",
        "seeds": [b"Cxxx", b"Dxxx", b"Zpayload", b"0tag", b"Qmore"],
    },
    "FRESH_GUARDED_NUMERIC_BINARY": {
        "case": "guarded",
        "category": "binary-state-null",
        "secondary": "numeric-margin",
        "expression": "hdr == 'G' && input_len > 8 && ctx.obj == NULL",
        "location": "benchmarks/fresh_v3_cases/fresh_v3_cases.c:72#run_guarded_numeric_binary",
        "seeds": [b"GOBJpayload", b"GxxOBJpayload", b"G123OBJabcdef", b"GOBJzzzzzzzz", b"GpreOBJtail"],
    },
    "FRESH_SAME_OBJECT_LIFECYCLE": {
        "case": "lifecycle",
        "category": "compound-sequence-lifecycle",
        "expression": "create(obj) before release(obj) before use(obj) && SAME_OBJECT(obj)",
        "location": "benchmarks/fresh_v3_cases/fresh_v3_cases.c:96#run_same_object_lifecycle",
        "seeds": [b"C1U1", b"C1R2U1", b"C1R1U2", b"C2R1U2", b"C3U3"],
    },
}

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


def replay(case: str, data: bytes) -> dict:
    proc = subprocess.run(
        [str(BIN), case],
        input=data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    lines = [line for line in proc.stdout.decode(errors="replace").splitlines() if line.startswith("{")]
    if not lines:
        raise RuntimeError(f"no JSON replay output: case={case} rc={proc.returncode} stderr={proc.stderr!r}")
    rec = json.loads(lines[-1])
    rec["returncode"] = proc.returncode
    return rec


def build_one(target_id: str, meta: dict[str, object]) -> list[dict[str, str]]:
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
        rows.append(
            {
                "target_id": target_id,
                "project": "fresh_v3_cases",
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
                "tc_root_state": str(rec.get("root_state", "")),
                "replay_hash": replay_hash,
                "replay_status": "kept_rnt",
                "metadata_status": "fresh_v3_replay_verified_rnt",
                "source_seedbank": str(out),
                "source_manifest": str(out / "metadata.csv"),
                "source_seed": str(seed_path),
                "producer": "fresh_v3_replay",
                "hot_ranges": json.dumps(rec.get("hot_ranges", []), separators=(",", ":")),
            }
        )
    with (out / "metadata.csv").open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    (out / "build_status.json").write_text(
        json.dumps(
            {
                "target_id": target_id,
                "built_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "seed_count": len(rows),
                "binary": str(BIN),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return rows


def main() -> int:
    if not BIN.exists():
        raise SystemExit(f"missing target binary: {BIN}")
    inventory_rows = []
    built = {}
    for target_id, meta in TARGETS.items():
        rows = build_one(target_id, meta)
        built[target_id] = len(rows)
        inventory_rows.append(
            {
                "target_id": target_id,
                "project": "fresh_v3_cases",
                "program": str(BIN),
                "canary_expression": str(meta["expression"]),
                "primary_tc_category": str(meta["category"]),
                "secondary_tc_category": str(meta.get("secondary", "")),
                "target_location": str(meta["location"]),
                "trigger_oracle": "JSON triggered == true",
                "initial_corpus": str(OUT_ROOT / target_id / "seeds"),
                "build_command": f"gcc -O2 -Wall -Wextra -o {BIN} {BIN}.c",
                "run_command": f"{BIN} {meta['case']} @@",
                "sanitizer_mode": "none",
                "notes": "fresh_v3_algorithm_smoke",
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
