#!/usr/bin/env python3
"""Discover FORMTRIG-native Magma assets for BindingSpec validation.

This tool is conservative: it only fills a site map when the map contains a
row matching at least one source selector from the BindingSpec draft, and it
only fills a target command when an executable with the expected program name
is found. Missing pieces stay as TODOs so validation planners remain blocked
instead of silently running against the wrong binary or seed corpus.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_DRAFTS = Path("artifacts/formtrig_native_readiness/magma_binding_drafts_20260616.json")
DEFAULT_RNT_STATUS = Path("artifacts/rnt_corpus_status.json")
DEFAULT_ASSETS = Path("artifacts/formtrig_native_readiness/magma_binding_validation_assets.discovered_20260616.json")
DEFAULT_REPORT_JSON = Path("artifacts/formtrig_native_readiness/magma_native_asset_discovery_20260616.json")
DEFAULT_REPORT_MD = Path("artifacts/formtrig_native_readiness/magma_native_asset_discovery_20260616.md")


DEFAULT_SEARCH_ROOTS = [
    Path("/tmp"),
    Path("artifacts/formtrig_native_readiness"),
    Path("experiments/magma_workspace"),
]


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def has_todo(value: str) -> bool:
    return "TODO" in value or value.strip() == ""


def unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1].replace("''", "'")
    return value


def manifest_values(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    return values


def binding_selectors(path: Path) -> list[dict[str, str]]:
    selectors: list[dict[str, str]] = []
    if not path.exists():
        return selectors
    current: dict[str, str] | None = None
    in_observe = False
    for raw in path.read_text(encoding="utf-8").splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        stripped = raw.strip()
        if stripped.startswith("- id:"):
            if current:
                selectors.append(current)
            current = {}
            in_observe = False
            continue
        if current is None:
            continue
        if in_observe and indent <= 4 and stripped != "observe_at:":
            in_observe = False
        if stripped == "observe_at:":
            in_observe = True
            continue
        if in_observe and ":" in stripped:
            key, value = stripped.split(":", 1)
            if key in {"kind", "function", "file", "line", "column"}:
                current[key] = unquote(value)
    if current:
        selectors.append(current)
    return selectors


def load_rnt_status(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = read_json(path)
    rows = payload.get("records", []) if isinstance(payload, dict) else []
    return {
        str(row.get("target_id")): row
        for row in rows
        if isinstance(row, dict) and row.get("target_id")
    }


def walk_files(roots: list[Path], *, max_files: int) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        if root.is_file():
            candidates = [root]
        else:
            candidates = []
            for dirpath, dirnames, filenames in os.walk(root):
                dirnames[:] = [
                    dirname
                    for dirname in dirnames
                    if dirname not in {".git", "__pycache__", "crashes", "hangs", ".synced"}
                ]
                for filename in filenames:
                    candidates.append(Path(dirpath) / filename)
                    if len(files) + len(candidates) >= max_files:
                        break
                if len(files) + len(candidates) >= max_files:
                    break
        for path in candidates:
            try:
                resolved = path.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            files.append(path)
            if len(files) >= max_files:
                return files
    return files


def site_map_paths(files: list[Path]) -> list[Path]:
    out: list[Path] = []
    for path in files:
        name = path.name
        if name == "site_map.tsv" or name.endswith("_site_map.tsv") or "site_map" in name and name.endswith(".tsv"):
            out.append(path)
    return sorted(out)


def executable_paths(files: list[Path], program_names: set[str]) -> dict[str, list[Path]]:
    out: dict[str, list[Path]] = {name: [] for name in program_names}
    for path in files:
        if path.name not in program_names:
            continue
        try:
            if path.is_file() and os.access(path, os.X_OK):
                out[path.name].append(path)
        except OSError:
            continue
    return {name: sorted(paths) for name, paths in out.items()}


def read_site_rows(path: Path, *, max_rows: int = 200000) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    try:
        with path.open(encoding="utf-8", errors="replace") as handle:
            for idx, raw in enumerate(handle):
                if idx >= max_rows:
                    break
                fields = raw.rstrip("\n").split("\t")
                if len(fields) < 8:
                    continue
                rows.append(
                    {
                        "site_id": fields[0],
                        "kind": fields[1],
                        "function": fields[2],
                        "inst_no": fields[3],
                        "opcode": fields[4],
                        "file": fields[5],
                        "line": fields[6],
                        "column": fields[7],
                    }
                )
    except OSError:
        return []
    return rows


def selector_matches_row(selector: dict[str, str], row: dict[str, str]) -> bool:
    if selector.get("kind") and selector["kind"] != row.get("kind"):
        return False
    if selector.get("line") and str(selector["line"]) != str(row.get("line", "")):
        return False
    selector_file = selector.get("file", "")
    if selector_file and selector_file not in row.get("file", ""):
        return False
    selector_function = selector.get("function", "")
    if selector_function and selector_function != row.get("function", ""):
        return False
    if selector.get("column") and str(selector["column"]) != str(row.get("column", "")):
        return False
    return True


def score_site_map(path: Path, selectors: list[dict[str, str]]) -> dict[str, Any]:
    rows = read_site_rows(path)
    if not rows:
        return {"path": str(path), "score": 0, "matched_selectors": 0, "row_count": 0}
    matched = 0
    for selector in selectors:
        if any(selector_matches_row(selector, row) for row in rows):
            matched += 1
    return {
        "path": str(path),
        "score": matched * 1000 + min(len(rows), 999),
        "matched_selectors": matched,
        "selector_count": len(selectors),
        "row_count": len(rows),
    }


def target_command(executable: Path, args_template: str) -> str:
    binary = shlex.quote(str(executable))
    if not args_template:
        return f"{binary} @@"
    return f"{binary} {args_template}"


def shell_join(args: list[str]) -> str:
    return " ".join(shlex.quote(str(arg)) for arg in args)


def args_template_from_target_cmd(target_cmd: str) -> str:
    """Strip the manifest binary placeholder and keep only target arguments."""

    if not target_cmd.strip():
        return "@@"
    try:
        argv = shlex.split(target_cmd)
    except ValueError:
        parts = target_cmd.split(None, 1)
        return parts[1] if len(parts) > 1 else "@@"
    if len(argv) <= 1:
        return "@@"
    return shell_join(argv[1:])


def intish(value: Any) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return 0


def formal_rnt_ready(row: dict[str, Any]) -> bool:
    return (
        str(row.get("status") or "") == "formal_ready"
        and str(row.get("seed_dir_exists") or "").lower() == "true"
        and intish(row.get("seed_files")) > 0
    )


def category_for_runner(category: str) -> str:
    if category == "binary-state-null":
        return "binary-null"
    if category == "compound-sequence-lifecycle":
        return "lifecycle"
    if category == "equality/magic":
        return "equality"
    if category == "numeric-margin":
        return "numeric"
    return "generic"


def build_discovery(
    *,
    drafts_path: Path,
    rnt_status_path: Path,
    search_roots: list[Path],
    max_files: int,
    source_discovery_path: Path = DEFAULT_REPORT_JSON,
) -> tuple[dict[str, Any], dict[str, Any]]:
    drafts = read_json(drafts_path)
    rnt_rows = load_rnt_status(rnt_status_path)
    program_names = {str(draft.get("program") or "") for draft in drafts.get("drafts", [])}
    program_names.discard("")
    files = walk_files(search_roots, max_files=max_files)
    maps = site_map_paths(files)
    executables = executable_paths(files, program_names)

    report_rows: list[dict[str, Any]] = []
    asset_targets: dict[str, Any] = {}
    for draft in drafts.get("drafts", []):
        target_id = str(draft.get("target_id") or "")
        program = str(draft.get("program") or "")
        spec = Path(str(draft.get("binding_spec") or ""))
        manifest_template = Path(str(draft.get("manifest_template") or ""))
        manifest = manifest_values(manifest_template)
        args_template = args_template_from_target_cmd(manifest.get("target_cmd", ""))
        selectors = binding_selectors(spec)
        site_scores = [score_site_map(path, selectors) for path in maps]
        site_scores = sorted(site_scores, key=lambda row: (row["score"], row["matched_selectors"]), reverse=True)
        best_site = site_scores[0] if site_scores and site_scores[0]["matched_selectors"] > 0 else None
        exe_candidates = executables.get(program, [])
        best_exe = exe_candidates[0] if exe_candidates else None
        rnt = rnt_rows.get(target_id, {})
        rnt_ready = formal_rnt_ready(rnt)
        seed_dir = str(rnt.get("seed_dir") or f"TODO_FORMAL_RNT_SEED_DIR_FOR_{target_id}")

        blockers: list[str] = []
        if not rnt_ready:
            blockers.append(
                "formal RNT seed corpus is not ready"
                + (f": {rnt.get('status')}" if rnt.get("status") else "")
            )
        if not best_site:
            blockers.append("no site_map.tsv matched the BindingSpec source selectors")
        if not best_exe:
            blockers.append(f"no executable found for program {program}")

        asset_targets[target_id] = {
            "binding_spec": str(spec),
            "seed_dir": seed_dir if rnt_ready else f"TODO_FORMAL_RNT_SEED_DIR_FOR_{target_id}",
            "site_map": best_site["path"] if best_site else f"TODO_FORMTRIG_NATIVE_SITE_MAP_FOR_{target_id}.tsv",
            "target_cwd": str(best_exe.parent) if best_exe else f"TODO_FORMTRIG_NATIVE_TARGET_CWD_FOR_{target_id}",
                "target_cmd": target_command(best_exe, args_template) if best_exe else manifest.get("target_cmd", ""),
                "category": str(draft.get("category") or "generic"),
                "runner_category": manifest.get("category", "") or category_for_runner(str(draft.get("category") or "")),
            "duration_s": 600,
            "seed_preflight_max": 32,
            "seed_preflight_timeout": 5,
            "validation_record": f"artifacts/formtrig_native_readiness/binding_validation/{spec.stem}.validation.json",
            "discovery_status": "runnable_candidate" if not blockers else "blocked",
            "discovery_blockers": blockers,
        }
        report_rows.append(
            {
                "target_id": target_id,
                "program": program,
                "rnt_status": str(rnt.get("status") or ""),
                "rnt_seed_files": intish(rnt.get("seed_files")),
                "selector_count": len(selectors),
                "best_site_map": best_site,
                "executable_candidates": [str(path) for path in exe_candidates[:5]],
                "runnable_candidate": not blockers,
                "blockers": blockers,
            }
        )

    report = {
        "schema": "formtrig_magma_native_asset_discovery_v1",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "inputs": {
            "drafts": str(drafts_path),
            "rnt_status": str(rnt_status_path),
            "search_roots": [str(path) for path in search_roots],
            "max_files": max_files,
        },
        "scanned_file_count": len(files),
        "site_map_count": len(maps),
        "program_names": sorted(program_names),
        "runnable_candidate_count": sum(1 for row in report_rows if row["runnable_candidate"]),
        "targets": report_rows,
    }
    assets = {
        "schema": "formtrig_magma_binding_validation_assets_discovered_v1",
        "generated_at_utc": report["generated_at_utc"],
        "source_discovery": str(source_discovery_path),
        "targets": asset_targets,
    }
    return report, assets


def write_markdown(path: Path, report: dict[str, Any], assets_path: Path) -> None:
    lines = [
        "# Magma Native Asset Discovery",
        "",
        "This report only records discovered validation inputs. It is not endpoint",
        "performance evidence. A target is runnable only when formal RNT seeds, a",
        "source-matching `site_map.tsv`, and an executable target command are all present.",
        "",
        f"Generated: `{report['generated_at_utc']}`",
        f"Scanned files: `{report['scanned_file_count']}`; site maps: `{report['site_map_count']}`; runnable candidates: `{report['runnable_candidate_count']}`",
        f"Assets JSON: `{assets_path}`",
        "",
        "| target | program | runnable | best site map | executables | blockers |",
        "| --- | --- | --- | --- | ---: | --- |",
    ]
    for row in report["targets"]:
        best_site = row.get("best_site_map") or {}
        blockers = "; ".join(row.get("blockers") or [])
        lines.append(
            "| {target} | {program} | {runnable} | `{site}` | {exe_count} | {blockers} |".format(
                target=row["target_id"],
                program=row["program"],
                runnable="yes" if row["runnable_candidate"] else "blocked",
                site=best_site.get("path", ""),
                exe_count=len(row.get("executable_candidates") or []),
                blockers=blockers or "none",
            )
        )
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--drafts", type=Path, default=DEFAULT_DRAFTS)
    parser.add_argument("--rnt-status", type=Path, default=DEFAULT_RNT_STATUS)
    parser.add_argument("--search-root", type=Path, action="append", default=[])
    parser.add_argument("--max-files", type=int, default=200000)
    parser.add_argument("--out-assets", type=Path, default=DEFAULT_ASSETS)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_REPORT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_REPORT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    roots = args.search_root or DEFAULT_SEARCH_ROOTS
    report, assets = build_discovery(
        drafts_path=args.drafts,
        rnt_status_path=args.rnt_status,
        search_roots=roots,
        max_files=args.max_files,
        source_discovery_path=args.out_json,
    )
    write_json(args.out_json, report)
    write_json(args.out_assets, assets)
    write_markdown(args.out_md, report, args.out_assets)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
