#!/usr/bin/env python3
"""Merge split Magma baseline roots into one auditable baseline summary root.

This is intended for recovery runs launched with --rep-start/--rep-end.  It
copies the small per-run evidence under runs/ from each shard, rebuilds
summary.json/summary.tsv, and records merge metadata.  Raw Magma monitor and
findings directories are intentionally not copied.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.summarize_post_reach_baselines import flatten_record, write_json, write_tsv


RUN_FILES = {
    "captain_stderr.log",
    "captain_stdout.log",
    "events.jsonl",
    "run_config.json",
    "run_record.json",
    "status.json",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def read_key_value(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def copy_run_dir(src: Path, dst: Path) -> list[str]:
    dst.mkdir(parents=True, exist_ok=False)
    copied: list[str] = []
    for item in sorted(src.iterdir()):
        if item.is_file() and item.name in RUN_FILES:
            shutil.copy2(item, dst / item.name)
            copied.append(item.name)
    record = dst / "run_record.json"
    config = dst / "run_config.json"
    if record.exists() and config.exists():
        payload = json.loads(record.read_text(encoding="utf-8"))
        payload["config_path"] = str(config)
        record.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return copied


def collect_runs(sources: list[Path]) -> dict[str, Path]:
    runs: dict[str, Path] = {}
    for source in sources:
        runs_dir = source / "runs"
        if not runs_dir.is_dir():
            raise SystemExit(f"baseline source has no runs/ directory: {source}")
        for run_dir in sorted(path for path in runs_dir.iterdir() if path.is_dir()):
            if not (run_dir / "run_record.json").is_file():
                raise SystemExit(f"baseline run is incomplete, missing run_record.json: {run_dir}")
            if run_dir.name in runs:
                raise SystemExit(
                    f"duplicate baseline run directory {run_dir.name}: "
                    f"{runs[run_dir.name]} and {run_dir}"
                )
            runs[run_dir.name] = run_dir
    return runs


def rebuild_summary(out_dir: Path) -> list[dict[str, Any]]:
    rows = [
        flatten_record(path)
        for path in sorted((out_dir / "runs").rglob("run_record.json"))
    ]
    rows.sort(
        key=lambda row: (
            str(row.get("target_id")),
            str(row.get("baseline")),
            int(row.get("budget") or 0),
            int(row.get("rep") or 0),
        )
    )
    write_json(out_dir / "summary.json", rows)
    write_tsv(out_dir / "summary.tsv", rows)
    return rows


def write_merge_metadata(
    out_dir: Path,
    sources: list[Path],
    runs: dict[str, Path],
    copied_files: dict[str, list[str]],
    rows: list[dict[str, Any]],
) -> None:
    source_metadata = {
        str(source): read_key_value(source / "run_metadata.txt") for source in sources
    }
    payload = {
        "copied_run_count": len(runs),
        "copied_run_files": copied_files,
        "created_utc": utc_now(),
        "raw_magma_dirs_copied": False,
        "record_count": len(rows),
        "source_metadata": source_metadata,
        "sources": [str(source) for source in sources],
    }
    (out_dir / "baseline_merge_metadata.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    lines = [
        "# Magma Baseline Merge",
        "",
        f"- created: `{payload['created_utc']}`",
        f"- copied runs: `{len(runs)}`",
        f"- summarized records: `{len(rows)}`",
        "- raw Magma monitor/findings directories copied: `false`",
        "",
        "## Sources",
        "",
    ]
    lines.extend(f"- `{source}`" for source in sources)
    lines.extend(["", "## Runs", ""])
    lines.extend(f"- `{name}` from `{src}`" for name, src in sorted(runs.items()))
    lines.append("")
    (out_dir / "baseline_merge_metadata.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--source", required=True, action="append", type=Path)
    parser.add_argument("--force", action="store_true", help="replace an existing output directory")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = args.out
    sources = [source.resolve() for source in args.source]
    if out_dir.exists():
        if not args.force:
            raise SystemExit(f"output directory already exists; pass --force: {out_dir}")
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    runs = collect_runs(sources)
    copied_files: dict[str, list[str]] = {}
    for run_name, source_run in sorted(runs.items()):
        copied_files[run_name] = copy_run_dir(source_run, out_dir / "runs" / run_name)

    first_metadata = sources[0] / "run_metadata.txt"
    if first_metadata.exists():
        shutil.copy2(first_metadata, out_dir / "run_metadata.txt")
    rows = rebuild_summary(out_dir)
    write_merge_metadata(out_dir, sources, runs, copied_files, rows)
    print(f"merged {len(runs)} baseline runs into {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
