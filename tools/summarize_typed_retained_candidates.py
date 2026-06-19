#!/usr/bin/env python3
"""Summarize FORMTRIG typed-retained candidate corpora.

The AFL++ integration can optionally preserve typed-mutation candidates that
produce TC-rooted FORMTRIG signal but are not saved by normal queueing.  This
tool converts the retention TSV into a JSON summary and a records.jsonl file
that downstream structure or endpoint auditors can consume.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path
from typing import Any


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


INT_FIELDS = {
    "source_queue_id",
    "stage_cur",
    "op",
    "component_index",
    "range_index",
    "sample_index",
    "start",
    "span",
    "offset",
    "len",
    "hook_used",
    "component_kind",
    "atom_id",
    "role",
    "component_flags",
    "hint_kind",
    "hint_value",
}
FLOAT_FIELDS = {"d_t", "d_f_spec_lifted", "component_value"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    return int(value, 0)


def parse_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    parsed = float(value)
    if parsed > 1.0e299 or parsed < -1.0e299:
        return None
    return parsed


def parse_tsv(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row_index, row in enumerate(reader):
            record: dict[str, Any] = {"source_records_tsv": str(path), "row_index": row_index}
            for key, value in row.items():
                if key in INT_FIELDS:
                    record[key] = parse_int(value)
                elif key in FLOAT_FIELDS:
                    record[key] = parse_float(value)
                else:
                    record[key] = value
            records.append(record)
    return records


def resolve_records_paths(args: argparse.Namespace) -> list[Path]:
    paths = list(args.records_tsv or [])
    for retain_dir in args.retain_dir or []:
        paths.append(retain_dir / "records.tsv")
    seen: set[Path] = set()
    resolved: list[Path] = []
    for path in paths:
        path = path.resolve()
        if path in seen:
            continue
        seen.add(path)
        resolved.append(path)
    return resolved


def normalize_record(record: dict[str, Any], index: int, copy_corpus: Path | None) -> dict[str, Any]:
    input_path = Path(str(record.get("path") or ""))
    exists = input_path.is_file()
    output_path = input_path
    sha256 = None
    size = None
    if exists:
        sha256 = sha256_file(input_path)
        size = input_path.stat().st_size
        if copy_corpus:
            copy_corpus.mkdir(parents=True, exist_ok=True)
            suffix = input_path.suffix or ".bin"
            output_path = copy_corpus / f"id:{index:06d},src:{record.get('source_queue_id', 0):06d}{suffix}"
            shutil.copy2(input_path, output_path)

    role = record.get("role")
    normalized = {
        "index": index,
        "path": str(output_path),
        "original_path": str(input_path),
        "input_exists": exists,
        "sha256": sha256,
        "size": size,
        "source_queue_id": record.get("source_queue_id"),
        "stage_cur": record.get("stage_cur"),
        "op": record.get("op"),
        "component_index": record.get("component_index"),
        "range_index": record.get("range_index"),
        "sample": record.get("sample_index"),
        "sample_index": record.get("sample_index"),
        "start": record.get("start"),
        "span": record.get("span"),
        "off": record.get("offset"),
        "offset": record.get("offset"),
        "len": record.get("len"),
        "hook_used": bool(record.get("hook_used")),
        "d_t": record.get("d_t"),
        "d_f_spec_lifted": record.get("d_f_spec_lifted"),
        "trace_signature": record.get("trace_signature"),
        "component_kind": record.get("component_kind"),
        "atom_id": record.get("atom_id"),
        "role": role,
        "role_name": ROLE_NAMES.get(role, f"role_{role}") if isinstance(role, int) else None,
        "component_flags": record.get("component_flags"),
        "component_value": record.get("component_value"),
        "hint_kind": record.get("hint_kind"),
        "hint_value": record.get("hint_value"),
        "source_records_tsv": record.get("source_records_tsv"),
        "row_index": record.get("row_index"),
        "retained_candidate_source": "FORMTRIG_TYPED_RETAIN",
    }
    return normalized


def counter(items: list[Any]) -> dict[str, int]:
    counts = Counter(str(item) for item in items if item is not None)
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def compact_record(record: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "index",
        "path",
        "sha256",
        "size",
        "source_queue_id",
        "stage_cur",
        "op",
        "sample",
        "start",
        "span",
        "off",
        "d_f_spec_lifted",
        "role_name",
        "component_kind",
        "atom_id",
        "hook_used",
    ]
    return {key: record.get(key) for key in keys}


def build_summary(
    records_paths: list[Path],
    missing_records_paths: list[Path],
    records: list[dict[str, Any]],
    top: int,
) -> dict[str, Any]:
    existing = [record for record in records if record["input_exists"]]
    missing = [record for record in records if not record["input_exists"]]
    d_f_values = [record["d_f_spec_lifted"] for record in existing if record.get("d_f_spec_lifted") is not None]
    best_by_d_f = sorted(
        existing,
        key=lambda record: (
            record.get("d_f_spec_lifted") if record.get("d_f_spec_lifted") is not None else 1.0e300,
            record["index"],
        ),
    )[:top]
    largest_by_size = sorted(
        existing,
        key=lambda record: (record.get("size") or 0, record["index"]),
        reverse=True,
    )[:top]
    return {
        "schema": "formtrig_typed_retained_candidates_v1",
        "records_tsv": [str(path) for path in records_paths],
        "missing_records_tsv": [str(path) for path in missing_records_paths],
        "retained_records": len(records),
        "existing_inputs": len(existing),
        "missing_inputs": len(missing),
        "total_existing_bytes": sum(record.get("size") or 0 for record in existing),
        "hook_used_records": sum(1 for record in existing if record.get("hook_used")),
        "roles": counter(record.get("role_name") for record in existing),
        "component_kinds": counter(record.get("component_kind") for record in existing),
        "ops": counter(record.get("op") for record in existing),
        "source_queue_ids": counter(record.get("source_queue_id") for record in existing),
        "d_f_spec_lifted": {
            "count": len(d_f_values),
            "min": min(d_f_values) if d_f_values else None,
            "max": max(d_f_values) if d_f_values else None,
            "unique": sorted(set(d_f_values))[:64],
        },
        "best_by_d_f": [compact_record(record) for record in best_by_d_f],
        "largest_by_size": [compact_record(record) for record in largest_by_size],
        "missing_examples": [compact_record(record) for record in missing[:top]],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--records-tsv", action="append", type=Path)
    parser.add_argument("--retain-dir", action="append", type=Path)
    parser.add_argument("--out-json", type=Path)
    parser.add_argument("--out-records-jsonl", type=Path)
    parser.add_argument("--copy-corpus", type=Path)
    parser.add_argument("--top", type=int, default=12)
    parser.add_argument(
        "--allow-empty",
        action="store_true",
        help="Emit an empty summary when a requested records.tsv is missing.",
    )
    args = parser.parse_args(argv)

    if not args.records_tsv and not args.retain_dir:
        parser.error("provide --records-tsv or --retain-dir")
    if args.top <= 0:
        parser.error("--top must be positive")

    records_paths = resolve_records_paths(args)
    existing_paths: list[Path] = []
    missing_paths: list[Path] = []
    for path in records_paths:
        if path.is_file():
            existing_paths.append(path)
        elif args.allow_empty:
            missing_paths.append(path)
        else:
            parser.error(f"records TSV not found: {path}")

    raw_records: list[dict[str, Any]] = []
    for path in existing_paths:
        raw_records.extend(parse_tsv(path))
    records = [
        normalize_record(record, index, args.copy_corpus)
        for index, record in enumerate(raw_records)
    ]
    summary = build_summary(existing_paths, missing_paths, records, args.top)
    if args.out_records_jsonl:
        args.out_records_jsonl.parent.mkdir(parents=True, exist_ok=True)
        with args.out_records_jsonl.open("w", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
        summary["records_jsonl"] = str(args.out_records_jsonl)
    if args.copy_corpus:
        summary["copied_corpus"] = str(args.copy_corpus)

    rendered = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(rendered, encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
