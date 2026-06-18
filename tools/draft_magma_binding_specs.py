#!/usr/bin/env python3
"""Draft FORMTRIG BindingSpecs from the Magma canary inventory.

This is intentionally a drafting tool, not a validator. The generated specs are
source-selector candidates that must still pass native site-map compilation,
seed readiness, binding-signal diagnosis, and endpoint comparison before any
benefit claim is made.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_QUEUE = Path("artifacts/formtrig_native_readiness/hard_target_discovery_queue_20260616.json")
DEFAULT_INVENTORY = Path("artifacts/magma_canary_inventory.json")
DEFAULT_SPEC_DIR = Path("artifacts/binding_specs")
DEFAULT_TEMPLATE_DIR = Path("artifacts/formtrig_native_readiness/manifest_templates")
DEFAULT_REPORT_JSON = Path("artifacts/formtrig_native_readiness/magma_binding_drafts_20260616.json")
DEFAULT_REPORT_MD = Path("artifacts/formtrig_native_readiness/magma_binding_drafts_20260616.md")


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def yaml_quote(value: Any) -> str:
    text = "" if value is None else str(value)
    return "'" + text.replace("'", "''") + "'"


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return slug.strip("_") or "draft"


def inventory_records(path: Path) -> dict[str, dict[str, Any]]:
    payload = read_json(path)
    return {
        str(record.get("target_id")): record
        for record in payload.get("records", [])
        if record.get("target_id")
    }


def queue_target_ids(path: Path, limit: int) -> list[str]:
    payload = read_json(path)
    rows = payload.get("top_targets") or payload.get("all_targets") or []
    target_ids: list[str] = []
    for row in rows:
        if row.get("source") != "magma":
            continue
        if row.get("lane") != "binding_spec_first":
            continue
        target_id = str(row.get("target_id") or "")
        if target_id:
            target_ids.append(target_id)
        if len(target_ids) >= limit:
            break
    return target_ids


def parse_location_text(value: Any) -> list[dict[str, Any]]:
    text = str(value or "")
    locations: list[dict[str, Any]] = []
    for raw in [part.strip() for part in text.split(";") if part.strip()]:
        left, _, function = raw.partition("#")
        parts = left.rsplit(":", 2)
        if len(parts) == 3:
            file_path, line, column = parts
        elif len(parts) == 2:
            file_path, line = parts
            column = ""
        else:
            continue
        try:
            line_no = int(line)
        except ValueError:
            continue
        location: dict[str, Any] = {
            "file": file_path,
            "line": line_no,
            "function": function,
        }
        if column:
            try:
                location["column"] = int(column)
            except ValueError:
                pass
        locations.append(location)
    return locations


def record_locations(record: dict[str, Any]) -> list[dict[str, Any]]:
    locations = parse_location_text(record.get("target_location"))
    if locations:
        return locations
    locations = parse_location_text(record.get("observation_point"))
    if locations:
        return locations
    source_file = record.get("source_file")
    source_line = record.get("source_line")
    if source_file and source_line:
        try:
            line_no = int(str(source_line))
        except ValueError:
            return []
        return [{"file": str(source_file), "line": line_no, "function": ""}]
    return []


def root_expr(canary_expression: str) -> str:
    expr = canary_expression.strip()
    match = re.search(r"([A-Za-z_][A-Za-z0-9_]*(?:->[A-Za-z_][A-Za-z0-9_]*)?(?:\.[A-Za-z_][A-Za-z0-9_]*)?)\s*(?:==|!=|<=|>=|<|>)", expr)
    if match:
        return match.group(1)
    return expr[:120] if expr else "magma_canary_state"


def category_for_manifest(category: str) -> str:
    if category == "binary-state-null":
        return "binary-null"
    if category == "compound-sequence-lifecycle":
        return "lifecycle"
    if category == "equality/magic":
        return "equality"
    if category == "numeric-margin":
        return "numeric"
    return "generic"


def binding_shape(category: str) -> dict[str, str]:
    if category == "numeric-margin":
        return {"component": "boundary_margin", "direction": "lower", "value_mode": "distance"}
    if category == "equality/magic":
        return {"component": "native_distance", "direction": "lower", "value_mode": "distance"}
    return {"component": "root_state", "direction": "higher", "value_mode": "outcome"}


def draft_spec_text(record: dict[str, Any], locations: list[dict[str, Any]], source_kind: str, max_locations: int) -> str:
    target_id = str(record["target_id"])
    category = str(record.get("primary_tc_category") or "generic")
    canary = str(record.get("canary_expression") or "")
    shape = binding_shape(category)
    lines = [
        f"tc_id: {yaml_quote(target_id)}",
        "target:",
        f"  project: {yaml_quote(record.get('project', ''))}",
        f"  binary: {yaml_quote(record.get('program', ''))}",
        f"  command: {yaml_quote(record.get('args_template', '@@'))}",
        "tc:",
        f"  category: {yaml_quote(category)}",
        f"  expression: {yaml_quote(canary)}",
        "  composition: 'all_of'",
        "atoms:",
        "  - id: 1",
        f"    expr: {yaml_quote(canary)}",
        f"    kind: {yaml_quote(category)}",
        f"    root: {yaml_quote(root_expr(canary))}",
        "bindings:",
    ]
    selected = locations[:max_locations]
    for index, loc in enumerate(selected, 1):
        priority = 10 + index - 1
        lines.extend(
            [
                f"  - id: {yaml_quote('magma_canary_root_%02d' % index)}",
                "    atom: 1",
                "    role: 'root_observe'",
                f"    expr: {yaml_quote('Magma canary source selector for ' + canary)}",
                "    observe_at:",
                f"      kind: {yaml_quote(source_kind)}",
                f"      function: {yaml_quote(loc.get('function', ''))}",
                f"      file: {yaml_quote(loc.get('file', ''))}",
                f"      line: {int(loc['line'])}",
            ]
        )
        if loc.get("column") is not None:
            lines.append(f"      column: {int(loc['column'])}")
        lines.extend(
            [
                f"    component: {yaml_quote(shape['component'])}",
                f"    priority: {priority}",
                f"    direction: {yaml_quote(shape['direction'])}",
                f"    value_mode: {yaml_quote(shape['value_mode'])}",
                "    value: 1.0",
                "    confidence: 0.55",
                "    observe_window: 'any'",
            ]
        )
    lines.append("")
    return "\n".join(lines)


def draft_manifest_template(record: dict[str, Any], spec_path: Path, template_dir: Path) -> str:
    target_id = str(record["target_id"])
    category = category_for_manifest(str(record.get("primary_tc_category") or "generic"))
    rel_spec = Path("../../binding_specs") / spec_path.name
    args_template = str(record.get("args_template") or "@@")
    target_cmd = f"TODO_FORMTRIG_MAGMA_{safe_slug(str(record.get('project', 'project'))).upper()}_{safe_slug(str(record.get('program', 'program'))).upper()}_BINARY {args_template}"
    lines = [
        "# Draft manifest template generated from Magma inventory.",
        "# Replace TODO_* fields after building a FORMTRIG-native Magma target and site map.",
        f"target_id: {target_id}",
        f"category: {category}",
        f"seed_dir: {record.get('initial_seed_corpus', '')}",
        f"out_dir: ../../formtrig_native_readiness/raw/{target_id.lower()}_formtrig_600s",
        f"binding_spec: {rel_spec}",
        "site_map: TODO_FORMTRIG_NATIVE_SITE_MAP.tsv",
        f"duration: 600",
        "seed_preflight: require",
        "seed_preflight_max: 32",
        "seed_preflight_timeout: 5",
        "target_cwd: TODO_FORMTRIG_NATIVE_TARGET_CWD",
        f"target_cmd: {target_cmd}",
        "",
    ]
    return "\n".join(lines)


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Magma BindingSpec Drafts",
        "",
        "These are validation-first drafts. They are not evidence that FORMTRIG has",
        "pre-trigger guidance or endpoint benefit until native site-map compilation,",
        "seed readiness, binding-signal diagnosis, and matched endpoint comparison pass.",
        "",
        f"Generated: `{payload['generated_at_utc']}`",
        f"Selection source: `{payload['inputs'].get('selection_source', '')}`",
        "Selected targets: "
        + ", ".join(f"`{target_id}`" for target_id in payload["inputs"].get("target_ids", [])),
        f"Drafts written: `{len(payload['drafts'])}`",
        "",
        "| target | project | category | spec | manifest template | locations |",
        "| --- | --- | --- | --- | --- | ---: |",
    ]
    for row in payload["drafts"]:
        lines.append(
            "| {target_id} | {project} | {category} | `{spec}` | `{manifest}` | {locations} |".format(
                target_id=row["target_id"],
                project=row["project"],
                category=row["category"],
                spec=row["binding_spec"],
                manifest=row["manifest_template"],
                locations=row["location_count"],
            )
        )
    if payload.get("skipped"):
        lines.extend(["", "## Skipped", ""])
        for row in payload["skipped"]:
            lines.append(f"- `{row['target_id']}`: {row['reason']}")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def build_drafts(
    *,
    inventory_path: Path,
    queue_path: Path,
    target_ids: list[str],
    limit: int,
    spec_dir: Path,
    template_dir: Path,
    source_kind: str,
    max_locations: int,
    overwrite: bool,
) -> dict[str, Any]:
    records = inventory_records(inventory_path)
    requested_target_ids = list(target_ids)
    selection_source = "explicit_target_ids" if requested_target_ids else "queue_binding_spec_first"
    if not target_ids:
        target_ids = queue_target_ids(queue_path, limit)
    selected_target_ids = target_ids[:limit]
    drafts: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for target_id in selected_target_ids:
        record = records.get(target_id)
        if not record:
            skipped.append({"target_id": target_id, "reason": "target not found in Magma inventory"})
            continue
        locations = record_locations(record)
        if not locations:
            skipped.append({"target_id": target_id, "reason": "no source location in Magma inventory"})
            continue
        spec_path = spec_dir / f"{target_id}.native_draft_magma_canary.yml"
        template_path = template_dir / f"{target_id}.manifest.template"
        if spec_path.exists() and not overwrite:
            skipped.append({"target_id": target_id, "reason": f"BindingSpec exists: {spec_path}"})
            continue
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        template_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(
            draft_spec_text(record, locations, source_kind, max_locations),
            encoding="utf-8",
        )
        template_path.write_text(
            draft_manifest_template(record, spec_path, template_dir),
            encoding="utf-8",
        )
        drafts.append(
            {
                "target_id": target_id,
                "project": str(record.get("project") or ""),
                "program": str(record.get("program") or ""),
                "category": str(record.get("primary_tc_category") or ""),
                "secondary_category": str(record.get("secondary_tc_category") or ""),
                "binding_spec": str(spec_path),
                "manifest_template": str(template_path),
                "location_count": min(len(locations), max_locations),
                "source_kind": source_kind,
                "status": "draft_needs_native_site_map_validation",
                "next_step": "compile against a FORMTRIG-native site_map.tsv, then run seed readiness and binding-signal diagnosis before endpoint screening",
            }
        )
    return {
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "schema": "formtrig_magma_binding_drafts_v1",
        "inputs": {
            "inventory": str(inventory_path),
            "queue": str(queue_path),
            "selection_source": selection_source,
            "target_ids": selected_target_ids,
            "source_kind": source_kind,
            "max_locations": max_locations,
        },
        "drafts": drafts,
        "skipped": skipped,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--target-id", action="append", default=[])
    parser.add_argument("--limit", type=int, default=6)
    parser.add_argument("--spec-dir", type=Path, default=DEFAULT_SPEC_DIR)
    parser.add_argument("--manifest-template-dir", type=Path, default=DEFAULT_TEMPLATE_DIR)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_REPORT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_REPORT_MD)
    parser.add_argument("--source-kind", default="cmp")
    parser.add_argument("--max-locations", type=int, default=2)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_drafts(
        inventory_path=args.inventory,
        queue_path=args.queue,
        target_ids=args.target_id,
        limit=args.limit,
        spec_dir=args.spec_dir,
        template_dir=args.manifest_template_dir,
        source_kind=args.source_kind,
        max_locations=args.max_locations,
        overwrite=args.overwrite,
    )
    write_json(args.out_json, payload)
    write_markdown(args.out_md, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
