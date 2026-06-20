#!/usr/bin/env python3
"""Draft conservative BindingSpecs from real-CVE trigger graphs.

This is a drafting tool, not an efficacy validator.  It only emits bindings
that have either a source location or an exact input range in the trigger graph.
Dynamic signal quality still has to be proven by native site-map validation,
lift audit, frontier diagnosis, and matched endpoint experiments.
"""

from __future__ import annotations

import argparse
import json
import re
import shlex
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_TRIGGER_GRAPH_DIR = Path("artifacts/trigger_graphs")
DEFAULT_TCIR_DIR = Path("artifacts/tcir")
DEFAULT_CVE_INVENTORY = Path("artifacts/cve_bench_inventory.json")
DEFAULT_SPEC_DIR = Path("artifacts/binding_specs")
DEFAULT_REPORT_JSON = Path("artifacts/formtrig_native_readiness/real_cve_binding_drafts_20260620.json")
DEFAULT_REPORT_MD = Path("artifacts/formtrig_native_readiness/real_cve_binding_drafts_20260620.md")


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def yaml_quote(value: Any) -> str:
    text = "" if value is None else str(value)
    return "'" + text.replace("'", "''") + "'"


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return slug.strip("_") or "draft"


def load_inventory(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = read_json(path)
    records = payload.get("records") if isinstance(payload.get("records"), list) else []
    by_target: dict[str, dict[str, Any]] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        target_id = str(record.get("target_id") or record.get("candidate_id") or "")
        if target_id:
            by_target[target_id] = record
    return by_target


def parse_location(value: Any) -> dict[str, Any] | None:
    text = str(value or "").strip()
    if not text:
        return None
    first = next((part.strip() for part in text.split(";") if part.strip()), "")
    if not first:
        return None
    left, _, function = first.partition("#")
    pieces = left.rsplit(":", 2)
    if len(pieces) == 3:
        file_path, line, column = pieces
    elif len(pieces) == 2:
        file_path, line = pieces
        column = ""
    else:
        return None
    try:
        line_no = int(line)
    except ValueError:
        return None
    location: dict[str, Any] = {
        "file": Path(file_path).name,
        "source_file": file_path,
        "line": line_no,
        "function": function,
    }
    if column:
        try:
            location["column"] = int(column)
        except ValueError:
            pass
    return location


def nodes_by_type(graph: dict[str, Any], node_type: str) -> list[dict[str, Any]]:
    return [
        node
        for node in graph.get("nodes", [])
        if isinstance(node, dict) and str(node.get("type") or "") == node_type
    ]


def first_node_location(graph: dict[str, Any], node_types: list[str]) -> dict[str, Any] | None:
    for node_type in node_types:
        for node in nodes_by_type(graph, node_type):
            location = parse_location(node.get("source_location"))
            if location:
                return location
    return None


def first_atom(tcir: dict[str, Any], graph: dict[str, Any]) -> dict[str, Any] | None:
    atoms = tcir.get("atoms") if isinstance(tcir.get("atoms"), list) else []
    for atom in atoms:
        if isinstance(atom, dict):
            return atom
    for node in nodes_by_type(graph, "tc_atom"):
        return {
            "atom_id": str(node.get("id") or "a1").split(":")[-1],
            "category": node.get("category") or "generic",
            "composition": node.get("composition") or "all_of",
            "expression": node.get("label") or "",
            "root_variables": [],
            "source_location": node.get("source_location") or "",
        }
    return None


def atom_id_int(value: Any) -> int:
    match = re.search(r"(\d+)$", str(value or "1"))
    return int(match.group(1)) if match else 1


def root_summary(atom: dict[str, Any], fallback_location: dict[str, Any] | None) -> str:
    roots = atom.get("root_variables") if isinstance(atom.get("root_variables"), list) else []
    useful = [
        str(root)
        for root in roots
        if str(root).strip().lower() not in {"the", "a", "an", "and", "or", "when"}
    ]
    if useful:
        return " ".join(useful[:6])
    if fallback_location and fallback_location.get("function"):
        return f"{fallback_location['function']} TC root state"
    expression = str(atom.get("expression") or "").strip()
    return expression[:100] or "real_cve_tc_root"


def target_info(target_id: str, inventory: dict[str, Any]) -> dict[str, str]:
    project = str(inventory.get("project") or target_id.split("_", 1)[0]).lower()
    command = str(inventory.get("run_command") or "./target @@")
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = command.split()
    binary = Path(parts[0]).name if parts else ""
    return {"project": project, "binary": binary, "command": command}


def binding_shape(category: str) -> dict[str, str]:
    normalized = category.strip().lower().replace("_", "-")
    if normalized in {"numeric", "numeric-margin"}:
        return {"component": "boundary_margin", "direction": "lower", "value_mode": "distance"}
    if normalized in {"equality", "equality-magic", "equality/magic"}:
        return {"component": "native_distance", "direction": "lower", "value_mode": "distance"}
    return {"component": "root_state", "direction": "higher", "value_mode": "outcome"}


def append_observe_at(lines: list[str], location: dict[str, Any], kind: str) -> None:
    lines.extend(
        [
            "    observe_at:",
            f"      kind: {yaml_quote(kind)}",
            f"      function: {yaml_quote(location.get('function', ''))}",
            f"      file: {yaml_quote(location.get('file', ''))}",
            f"      line: {int(location['line'])}",
        ]
    )
    if location.get("column") is not None:
        lines.append(f"      column: {int(location['column'])}")


def append_binding(
    lines: list[str],
    *,
    binding_id: str,
    atom_id: int,
    role: str,
    expr: str,
    location: dict[str, Any],
    kind: str,
    component: str,
    priority: int,
    direction: str,
    value_mode: str,
    value: Any,
    confidence: Any,
) -> None:
    lines.extend(
        [
            f"  - id: {yaml_quote(binding_id)}",
            f"    atom: {atom_id}",
            f"    role: {yaml_quote(role)}",
            f"    expr: {yaml_quote(expr)}",
        ]
    )
    append_observe_at(lines, location, kind)
    lines.extend(
        [
            f"    component: {yaml_quote(component)}",
            f"    priority: {priority}",
            f"    direction: {yaml_quote(direction)}",
            f"    value_mode: {yaml_quote(value_mode)}",
            f"    value: {value}",
            f"    confidence: {confidence}",
            "    observe_window: 'any'",
        ]
    )


def range_mutation(node: dict[str, Any]) -> tuple[str, int]:
    values = node.get("integer_values")
    if isinstance(values, list):
        for raw in values:
            try:
                value = int(raw)
            except (TypeError, ValueError):
                continue
            if 0 <= value <= 255:
                return "set_byte", value
    return "set_byte", 65


def append_input_influence(
    lines: list[str],
    *,
    target_id: str,
    atom_id: int,
    node: dict[str, Any],
    location: dict[str, Any],
    index: int,
) -> None:
    start = int(node.get("start"))
    length = int(node.get("length"))
    hint, value = range_mutation(node)
    range_kind = str(node.get("range_kind") or "input_range")
    label = str(node.get("label") or f"{target_id}[{start}:{start + length}]")
    lines.extend(
        [
            f"  - id: {yaml_quote('input_range_%02d_%s' % (index, safe_slug(range_kind)))}",
            f"    atom: {atom_id}",
            "    role: 'input_influence'",
            f"    expr: {yaml_quote(label + ' influences the trigger guard')}",
        ]
    )
    append_observe_at(lines, location, "branch")
    lines.extend(
        [
            "    component: 'input_influence'",
            f"    priority: {40 + index}",
            "    direction: 'higher'",
            "    value_mode: 'hit'",
            "    value: 1.0",
            f"    confidence: {float(node.get('confidence_score') or 0.5):.2f}",
            "    observe_window: 'any'",
            f"    range_start: {start}",
            f"    range_len: {length}",
            f"    mutation_hint: {yaml_quote(hint)}",
            f"    mutation_value: {value}",
        ]
    )


def draft_spec_text(
    *,
    target_id: str,
    graph: dict[str, Any],
    tcir: dict[str, Any],
    inventory: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    atom = first_atom(tcir, graph)
    if atom is None:
        raise ValueError(f"{target_id}: no TC atom found in TCIR or trigger graph")
    target_location = first_node_location(graph, ["target_site_context", "target_context"])
    if target_location is None:
        target_location = parse_location(atom.get("source_location"))
    if target_location is None:
        raise ValueError(f"{target_id}: no source location found for target/root binding")

    guard_location = first_node_location(graph, ["guard_context"]) or target_location
    use_location = first_node_location(graph, ["use_context"]) or target_location
    category = str(atom.get("category") or tcir.get("category") or "generic")
    expression = str(atom.get("expression") or tcir.get("expression") or "")
    composition = str(atom.get("composition") or "all_of")
    atom_id = atom_id_int(atom.get("atom_id") or "a1")
    target = target_info(target_id, inventory)
    shape = binding_shape(category)

    lines = [
        "# Conservative draft generated from a real-CVE trigger graph.",
        "# Validate native site-map compilation and dynamic binding signal before benefit claims.",
        f"tc_id: {yaml_quote(target_id)}",
        "target:",
        f"  project: {yaml_quote(target['project'])}",
        f"  binary: {yaml_quote(target['binary'])}",
        f"  command: {yaml_quote(target['command'])}",
        "tc:",
        f"  category: {yaml_quote(category)}",
        f"  expression: {yaml_quote(expression)}",
        f"  composition: {yaml_quote(composition)}",
        "atoms:",
        f"  - id: {atom_id}",
        f"    expr: {yaml_quote(expression)}",
        f"    kind: {yaml_quote(category)}",
        f"    root: {yaml_quote(root_summary(atom, target_location))}",
        "bindings:",
    ]

    append_binding(
        lines,
        binding_id="trigger_graph_root_observe",
        atom_id=atom_id,
        role="root_observe",
        expr="TC-rooted target site observation from trigger graph",
        location=target_location,
        kind="binary",
        component=shape["component"],
        priority=10,
        direction=shape["direction"],
        value_mode=shape["value_mode"],
        value="1.0",
        confidence="0.75",
    )
    append_binding(
        lines,
        binding_id="trigger_graph_guard",
        atom_id=atom_id,
        role="guard",
        expr="Trigger-graph guard context for the target condition",
        location=guard_location,
        kind="branch",
        component="guard_progress",
        priority=20,
        direction="higher",
        value_mode="hit",
        value="1.0",
        confidence="0.70",
    )
    append_binding(
        lines,
        binding_id="trigger_graph_use",
        atom_id=atom_id,
        role="use",
        expr="Trigger-graph use context that observes the target state",
        location=use_location,
        kind="binary",
        component="producer_use",
        priority=30,
        direction="higher",
        value_mode="hit",
        value="1.0",
        confidence="0.70",
    )

    limitations: list[str] = []
    for node in nodes_by_type(graph, "producer_context"):
        if parse_location(node.get("source_location")) is None:
            limitations.append(
                "producer_context has no source_location; desired_producer binding was not emitted"
            )
    for node in nodes_by_type(graph, "repair_hook"):
        if not node.get("configured"):
            limitations.append("repair_hook exists but is not configured; repair_hook binding was not emitted")

    range_nodes = sorted(
        nodes_by_type(graph, "candidate_input_influence_range"),
        key=lambda node: (
            int(node.get("root_priority") or 999),
            int(node.get("start") or 0),
            int(node.get("length") or 0),
        ),
    )
    emitted_ranges = 0
    for node in range_nodes:
        if node.get("start") is None or node.get("length") is None:
            limitations.append(f"input range {node.get('id') or ''} missing start/length")
            continue
        append_input_influence(
            lines,
            target_id=target_id,
            atom_id=atom_id,
            node=node,
            location=guard_location,
            index=emitted_ranges + 1,
        )
        emitted_ranges += 1

    if not emitted_ranges:
        limitations.append("no candidate_input_influence_range nodes were emitted")

    lines.append("")
    metadata = {
        "target_id": target_id,
        "category": category,
        "atom_expression": expression,
        "target_location": target_location,
        "guard_location": guard_location,
        "use_location": use_location,
        "input_range_count": emitted_ranges,
        "limitations": sorted(dict.fromkeys(limitations)),
    }
    return "\n".join(lines), metadata


def spec_name(target_id: str, metadata: dict[str, Any]) -> str:
    location = metadata.get("target_location") if isinstance(metadata.get("target_location"), dict) else {}
    function = safe_slug(str(location.get("function") or "trigger_graph"))
    return f"{target_id}.native_b1_{function}_candidate.yml"


def build_drafts(
    *,
    target_ids: list[str],
    trigger_graph_dir: Path,
    tcir_dir: Path,
    cve_inventory: Path,
    spec_dir: Path,
    overwrite: bool,
) -> dict[str, Any]:
    inventory = load_inventory(cve_inventory)
    drafts: list[dict[str, Any]] = []
    skipped: list[dict[str, str]] = []
    for target_id in target_ids:
        graph_path = trigger_graph_dir / f"{target_id}.json"
        tcir_path = tcir_dir / f"{target_id}.json"
        if not graph_path.exists():
            skipped.append({"target_id": target_id, "reason": f"missing trigger graph: {graph_path}"})
            continue
        if not tcir_path.exists():
            skipped.append({"target_id": target_id, "reason": f"missing TCIR: {tcir_path}"})
            continue
        try:
            text, metadata = draft_spec_text(
                target_id=target_id,
                graph=read_json(graph_path),
                tcir=read_json(tcir_path),
                inventory=inventory.get(target_id, {}),
            )
        except Exception as exc:
            skipped.append({"target_id": target_id, "reason": str(exc)})
            continue
        spec_path = spec_dir / spec_name(target_id, metadata)
        if spec_path.exists() and not overwrite:
            skipped.append({"target_id": target_id, "reason": f"exists: {spec_path}"})
            continue
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        spec_path.write_text(text, encoding="utf-8")
        drafts.append(
            {
                "target_id": target_id,
                "binding_spec": str(spec_path),
                "trigger_graph": str(graph_path),
                "tcir": str(tcir_path),
                "category": metadata["category"],
                "input_range_count": metadata["input_range_count"],
                "limitations": metadata["limitations"],
            }
        )
    return {
        "schema": "formtrig_real_cve_binding_drafts_v1",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "inputs": {
            "target_ids": target_ids,
            "trigger_graph_dir": str(trigger_graph_dir),
            "tcir_dir": str(tcir_dir),
            "cve_inventory": str(cve_inventory),
            "spec_dir": str(spec_dir),
            "overwrite": overwrite,
        },
        "draft_count": len(drafts),
        "skipped_count": len(skipped),
        "drafts": drafts,
        "skipped": skipped,
    }


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        "# Real-CVE BindingSpec Drafts",
        "",
        "These drafts are conservative source/range candidates. They do not prove",
        "FORMTRIG guidance or endpoint benefit until native validation and matched",
        "experiments pass.",
        "",
        f"Generated: `{payload['generated_at_utc']}`",
        f"Drafts written: `{payload['draft_count']}`",
        "",
        "| target | category | spec | ranges | limitations |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for row in payload["drafts"]:
        limitations = "; ".join(row.get("limitations") or []) or "none"
        lines.append(
            "| {target_id} | {category} | `{binding_spec}` | {ranges} | {limitations} |".format(
                target_id=row["target_id"],
                category=row["category"],
                binding_spec=row["binding_spec"],
                ranges=row["input_range_count"],
                limitations=limitations,
            )
        )
    if payload.get("skipped"):
        lines.extend(["", "## Skipped", ""])
        for row in payload["skipped"]:
            lines.append(f"- `{row['target_id']}`: {row['reason']}")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target-id", action="append", required=True)
    parser.add_argument("--trigger-graph-dir", type=Path, default=DEFAULT_TRIGGER_GRAPH_DIR)
    parser.add_argument("--tcir-dir", type=Path, default=DEFAULT_TCIR_DIR)
    parser.add_argument("--cve-inventory", type=Path, default=DEFAULT_CVE_INVENTORY)
    parser.add_argument("--spec-dir", type=Path, default=DEFAULT_SPEC_DIR)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--out-json", type=Path, default=DEFAULT_REPORT_JSON)
    parser.add_argument("--out-md", type=Path, default=DEFAULT_REPORT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_drafts(
        target_ids=args.target_id,
        trigger_graph_dir=args.trigger_graph_dir,
        tcir_dir=args.tcir_dir,
        cve_inventory=args.cve_inventory,
        spec_dir=args.spec_dir,
        overwrite=args.overwrite,
    )
    write_json(args.out_json, payload)
    write_markdown(args.out_md, payload)
    return 0 if payload["draft_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
