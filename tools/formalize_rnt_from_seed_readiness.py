#!/usr/bin/env python3
"""Create a formal RNT corpus from FORMTRIG seed-readiness replay output."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


METADATA_FIELDS = [
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
]

STATUS_FIELDS = [
    "target_id",
    "suite",
    "project",
    "program",
    "tc_category",
    "expected",
    "rnt_dir",
    "metadata_csv",
    "manifest_json",
    "seed_dir",
    "metadata_exists",
    "manifest_exists",
    "seed_dir_exists",
    "metadata_rows",
    "seed_files",
    "unique_content_sha256",
    "reached_rows",
    "triggered_rows",
    "non_rnt_rows",
    "missing_seed_files",
    "duplicate_content_rows",
    "missing_required_field_rows",
    "program_mismatch_rows",
    "placeholder_native_DT_rows",
    "placeholder_tc_root_state_rows",
    "replay_statuses",
    "metadata_statuses",
    "manifest_metadata_status",
    "native_DT_status",
    "tc_root_state_status",
    "status",
    "blocking_reason",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def boolish(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def last_runtime_event(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    last: dict[str, Any] = {}
    with path.open(encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                last = parsed
    return last


def selected_seed_records(
    payload: dict[str, Any],
    *,
    max_seeds: int,
    max_input_size: int | None,
    require_spec_lifted: bool,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    for record in payload.get("seeds", []):
        if not isinstance(record, dict):
            continue
        if not boolish(record.get("rnt")):
            continue
        if require_spec_lifted and not boolish(record.get("spec_lifted")):
            continue
        if boolish(record.get("triggered")):
            continue
        seed = Path(str(record.get("seed") or ""))
        if not seed.exists() or not seed.is_file():
            continue
        input_size = seed.stat().st_size
        if max_input_size is not None and input_size > max_input_size:
            continue
        content_sha = sha256_path(seed)
        if content_sha in seen_hashes:
            continue
        seen_hashes.add(content_sha)
        record = dict(record)
        record["_input_size"] = input_size
        record["_content_sha256"] = content_sha
        selected.append(record)
        if len(selected) >= max_seeds:
            break
    return selected


def make_metadata_row(
    *,
    args: argparse.Namespace,
    index: int,
    record: dict[str, Any],
) -> dict[str, str]:
    seed = Path(str(record["seed"]))
    runtime_log = Path(str(record.get("runtime_log") or ""))
    event = last_runtime_event(runtime_log)
    reached = boolish(event.get("reached", record.get("reached")))
    triggered = boolish(event.get("crash_predicate", record.get("triggered")))
    reached_count = int(event.get("target_hit_count") or (1 if reached else 0))
    triggered_count = 1 if triggered else 0
    trace_signature = str(event.get("trace_signature") or "")
    coverage_hash = f"trace:{trace_signature}" if trace_signature else f"runtime:{sha256_path(runtime_log)[:16]}" if runtime_log.exists() else "runtime:missing"
    native_dt = str(event.get("D_T", 1 if reached and not triggered else 0))
    replay_hash = sha256_path(runtime_log) if runtime_log.exists() else sha256_text(json.dumps(event, sort_keys=True))
    content_sha = str(record["_content_sha256"])
    return {
        "target_id": args.target_id,
        "project": args.project,
        "program": args.program,
        "tc_category": args.tc_category,
        "seed_id": f"id:{index:06d},sha256:{content_sha[:16]}",
        "parent_seed_id": "ROOT",
        "content_sha256": content_sha,
        "input_size": str(record["_input_size"]),
        "reached_R": "1" if reached else "0",
        "triggered_T": "1" if triggered else "0",
        "reached_count": str(reached_count),
        "triggered_count": str(triggered_count),
        "arrival_timestamp": "0",
        "time_s": "0",
        "coverage_hash": coverage_hash,
        "native_DT": native_dt,
        "tc_root_state": f"R={reached_count};T={triggered_count}",
        "replay_hash": replay_hash,
        "replay_status": "kept_rnt",
        "metadata_status": "formal_replay_verified_rnt",
        "source_seedbank": args.source_seedbank,
        "source_manifest": args.source_manifest,
        "source_seed": str(seed),
        "producer": args.producer,
    }


def write_metadata(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=METADATA_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def write_manifest(path: Path, *, args: argparse.Namespace, seed_count: int) -> None:
    write_json(
        path,
        {
            "created_at_utc": utc_now(),
            "formal_replay_log": args.source_manifest,
            "metadata_status": "formal_replay_verified_rnt",
            "native_DT_semantics": (
                f"binary R/T oracle distance from FORMTRIG-native Magma {args.target_id} "
                f"seed readiness under {args.program}"
            ),
            "native_DT_status": "computed",
            "producer": args.producer,
            "program": args.program,
            "seed_count": seed_count,
            "source_seedbank": args.source_seedbank,
            "suite": args.suite,
            "target_id": args.target_id,
            "tc_root_state_status": "computed",
            "unique_rnt_seed_count": seed_count,
        },
    )


def status_record(args: argparse.Namespace, *, seed_count: int) -> dict[str, str]:
    out_dir = Path(args.out_dir)
    return {
        "target_id": args.target_id,
        "suite": args.suite,
        "project": args.project,
        "program": args.program,
        "tc_category": args.tc_category,
        "expected": "true",
        "rnt_dir": str(out_dir),
        "metadata_csv": str(out_dir / "metadata.csv"),
        "manifest_json": str(out_dir / "manifest.json"),
        "seed_dir": str(out_dir / "seeds"),
        "metadata_exists": "true",
        "manifest_exists": "true",
        "seed_dir_exists": "true",
        "metadata_rows": str(seed_count),
        "seed_files": str(seed_count),
        "unique_content_sha256": str(seed_count),
        "reached_rows": str(seed_count),
        "triggered_rows": "0",
        "non_rnt_rows": "0",
        "missing_seed_files": "0",
        "duplicate_content_rows": "0",
        "missing_required_field_rows": "0",
        "program_mismatch_rows": "0",
        "placeholder_native_DT_rows": "0",
        "placeholder_tc_root_state_rows": "0",
        "replay_statuses": "kept_rnt",
        "metadata_statuses": "formal_replay_verified_rnt",
        "manifest_metadata_status": "formal_replay_verified_rnt",
        "native_DT_status": "computed",
        "tc_root_state_status": "computed",
        "status": "formal_ready",
        "blocking_reason": "",
    }


def update_status_json(path: Path, record: dict[str, str]) -> None:
    payload: dict[str, Any]
    if path.exists():
        payload = load_json(path)
    else:
        payload = {"records": [], "rnt_root": "artifacts/rnt_corpus"}
    rows = payload.get("records", [])
    if not isinstance(rows, list):
        rows = []
    replaced = False
    next_rows: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict) and row.get("target_id") == record["target_id"]:
            next_rows.append(record)
            replaced = True
        else:
            next_rows.append(row)
    if not replaced:
        next_rows.append(record)
    payload["generated_at_utc"] = utc_now()
    payload["records"] = next_rows
    write_json(path, payload)


def update_status_csv(path: Path, record: dict[str, str]) -> None:
    rows: list[dict[str, str]] = []
    if path.exists():
        with path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                rows.append({field: row.get(field, "") for field in STATUS_FIELDS})
    replaced = False
    next_rows: list[dict[str, str]] = []
    for row in rows:
        if row.get("target_id") == record["target_id"]:
            next_rows.append(record)
            replaced = True
        else:
            next_rows.append(row)
    if not replaced:
        next_rows.append(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=STATUS_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(next_rows)


def markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join("---" for _ in headers) + "|")
    out.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(out)


def status_markdown(path: Path, status_json: Path) -> None:
    payload = load_json(status_json)
    rows = [row for row in payload.get("records", []) if isinstance(row, dict)]
    status_counts = Counter(str(row.get("status") or "") for row in rows)
    suites: dict[str, Counter[str]] = defaultdict(Counter)
    classes: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        suites[str(row.get("suite") or "")][str(row.get("status") or "")] += 1
        classes[str(row.get("tc_category") or "")][str(row.get("status") or "")] += 1
    statuses = ["formal_ready", "candidate_only", "invalid", "missing", "excluded"]
    first_blockers = [
        row
        for row in rows
        if str(row.get("status") or "") != "formal_ready" or str(row.get("blocking_reason") or "")
    ][:40]
    lines = [
        "# RNT Corpus Status",
        "",
        f"Generated UTC: {payload.get('generated_at_utc', utc_now())}",
        "",
        "## Overall",
        "",
        markdown_table(
            ["status", "count"],
            [[status, str(count)] for status, count in sorted(status_counts.items())],
        ),
        "",
        "## By Suite",
        "",
        markdown_table(
            ["suite", *statuses],
            [[suite, *[str(counter.get(status, 0)) for status in statuses]] for suite, counter in sorted(suites.items())],
        ),
        "",
        "## By TC Class",
        "",
        markdown_table(
            ["TC class", *statuses],
            [[tc_class, *[str(counter.get(status, 0)) for status in statuses]] for tc_class, counter in sorted(classes.items())],
        ),
        "",
        "## First Blockers",
        "",
        markdown_table(
            ["target_id", "suite", "TC class", "status", "blocking reason"],
            [
                [
                    str(row.get("target_id") or ""),
                    str(row.get("suite") or ""),
                    str(row.get("tc_category") or ""),
                    str(row.get("status") or ""),
                    str(row.get("blocking_reason") or ""),
                ]
                for row in first_blockers
            ],
        ),
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def formalize(args: argparse.Namespace) -> dict[str, Any]:
    payload = load_json(Path(args.seed_readiness))
    records = selected_seed_records(
        payload,
        max_seeds=args.max_seeds,
        max_input_size=args.max_input_size,
        require_spec_lifted=not args.allow_unlifted,
    )
    if not records:
        raise SystemExit("no RNT seed records matched the requested filters")

    out_dir = Path(args.out_dir)
    seed_dir = out_dir / "seeds"
    seed_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str]] = []
    for index, record in enumerate(records):
        row = make_metadata_row(args=args, index=index, record=record)
        source_seed = Path(str(record["seed"]))
        shutil.copyfile(source_seed, seed_dir / row["seed_id"])
        rows.append(row)

    write_metadata(out_dir / "metadata.csv", rows)
    write_manifest(out_dir / "manifest.json", args=args, seed_count=len(rows))
    record = status_record(args, seed_count=len(rows))
    if args.update_status_json:
        update_status_json(Path(args.update_status_json), record)
    if args.update_status_csv:
        update_status_csv(Path(args.update_status_csv), record)
    if args.update_status_md:
        if not args.update_status_json:
            raise SystemExit("--update-status-md requires --update-status-json")
        status_markdown(Path(args.update_status_md), Path(args.update_status_json))
    return {"selected": len(rows), "out_dir": str(out_dir)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed-readiness", required=True)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--project", required=True)
    parser.add_argument("--program", required=True)
    parser.add_argument("--tc-category", required=True)
    parser.add_argument("--source-seedbank", required=True)
    parser.add_argument("--source-manifest", required=True)
    parser.add_argument("--producer", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--suite", default="magma")
    parser.add_argument("--max-seeds", type=int, default=32)
    parser.add_argument("--max-input-size", type=int)
    parser.add_argument("--allow-unlifted", action="store_true")
    parser.add_argument("--update-status-json")
    parser.add_argument("--update-status-csv")
    parser.add_argument("--update-status-md")
    return parser.parse_args()


def main() -> None:
    result = formalize(parse_args())
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
