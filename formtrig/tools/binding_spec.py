#!/usr/bin/env python3
"""FORMTRIG BindingSpec loader and materializer.

BindingSpec is the external contract that connects known TC semantics to
runtime-observable events. This module deliberately contains no PNG, SQL,
Magma, or CVE-specific logic. It only validates generic roles and translates
them into trigger-graph/runtime-map inputs consumed by the native FORMTRIG
compiler and binding audit.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from audit_lift_bindings import graph_binding_audit
from compile_lift_spec import load_runtime_map, parse_site_map


ROLE_TO_NODE_TYPE = {
    "root_observe": "root_context",
    "guard": "guard_context",
    "producer": "producer_context",
    "desired_producer": "producer_context",
    "opposite_producer": "producer_context",
    "use": "use_context",
    "lifecycle_event": "lifecycle_phase",
    "same_object": "same_object_context",
}

BINDING_SECTION_ROLE = {
    "roots": "root_observe",
    "guards": "guard",
    "producers": "producer",
    "uses": "use",
    "lifecycle_events": "lifecycle_event",
    "same_object": "same_object",
}

ROLE_COMPONENT_DEFAULT = {
    "root_observe": "producer_use",
    "guard": "guard_progress",
    "producer": "producer_use",
    "desired_producer": "producer_use",
    "opposite_producer": "producer_use",
    "use": "producer_use",
    "lifecycle_event": "event_phase",
    "same_object": "object_identity",
}

VALID_CATEGORIES = {
    "numeric-margin",
    "equality/magic",
    "binary-state-null",
    "compound-sequence-lifecycle",
}

VALID_ROLES = set(ROLE_TO_NODE_TYPE) | {"input_influence", "repair_hook"}


def load_json_or_yaml(path: Path) -> Dict[str, Any]:
    text = path.read_text()
    if path.suffix.lower() in {".yaml", ".yml"}:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise SystemExit(
                "YAML BindingSpec requires PyYAML; use JSON or install python3-yaml"
            ) from exc
        data = yaml.safe_load(text)
    else:
        data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: BindingSpec must be a JSON/YAML object")
    return data


def as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def normalize_role(raw: Any, default: str) -> str:
    role = str(raw or default).strip()
    if role == "root":
        role = "root_observe"
    if role == "lifecycle":
        role = "lifecycle_event"
    if role == "object_identity":
        role = "same_object"
    return role


def source_location(observe: Dict[str, Any]) -> str:
    raw = observe.get("source_location") or observe.get("location")
    if raw:
        return str(raw)
    file_name = str(observe.get("file") or "")
    line = observe.get("line")
    if not file_name or line is None:
        return ""
    loc = f"{file_name}:{line}"
    column = observe.get("column")
    if column not in (None, ""):
        loc += f":{column}"
    function = observe.get("function")
    if function:
        loc += f"#{function}"
    return loc


def runtime_event_key(section: str, binding: Dict[str, Any], observe: Dict[str, Any], index: int) -> str:
    runtime_event_id = observe.get("runtime_event_id") or binding.get("runtime_event_id")
    if runtime_event_id:
        return str(runtime_event_id)
    return f"{section}:{binding['id']}:{index}"


def runtime_map_entry(
    *,
    target_id: str,
    atom_id: str,
    binding_id: str,
    role: str,
    observe: Dict[str, Any],
    node_type: str,
    binding_index: int,
) -> Dict[str, Any]:
    entry: Dict[str, Any] = {
        "target_id": target_id,
        "atom_id": atom_id,
        "binding_id": binding_id,
        "role": role,
        "node_type": node_type,
        "source_location": source_location(observe),
        "mapping_status": "declared",
    }
    for key in (
        "event_kind",
        "site_id",
        "value_mode",
        "component_kind",
        "direction",
        "priority",
        "confidence",
        "source",
    ):
        if observe.get(key) is not None:
            entry[key] = observe[key]
    if "component_kind" not in entry and role in ROLE_COMPONENT_DEFAULT:
        entry["component_kind"] = ROLE_COMPONENT_DEFAULT[role]
    if "value_mode" not in entry:
        entry["value_mode"] = "hit"
    if "source" not in entry:
        entry["source"] = "binding-spec"
    if "event_id" not in entry:
        entry["event_id"] = f"{target_id}:{atom_id}:{binding_id}:{role}:{binding_index}"
    return entry


def validate_binding_spec(spec: Dict[str, Any]) -> List[Dict[str, str]]:
    failures: List[Dict[str, str]] = []

    def fail(path: str, reason: str) -> None:
        failures.append({"path": path, "reason": reason})

    target_id = spec.get("tc_id")
    if not isinstance(target_id, str) or not target_id.strip():
        fail("tc_id", "missing_or_empty")
    tc = spec.get("tc")
    if not isinstance(tc, dict):
        fail("tc", "missing_or_invalid")
    else:
        if not isinstance(tc.get("expression"), str) or not tc.get("expression", "").strip():
            fail("tc.expression", "missing_or_empty")
        if tc.get("category") not in VALID_CATEGORIES:
            fail("tc.category", "unknown_category")

    atoms = spec.get("atoms")
    atom_ids = set()
    if not isinstance(atoms, list) or not atoms:
        fail("atoms", "missing_or_empty")
    else:
        for idx, atom in enumerate(atoms):
            if not isinstance(atom, dict):
                fail(f"atoms[{idx}]", "invalid_atom")
                continue
            atom_id = atom.get("id")
            if not isinstance(atom_id, str) or not atom_id.strip():
                fail(f"atoms[{idx}].id", "missing_or_empty")
            else:
                atom_ids.add(atom_id)
            if not isinstance(atom.get("expr"), str) or not atom.get("expr", "").strip():
                fail(f"atoms[{idx}].expr", "missing_or_empty")
            if not isinstance(atom.get("kind"), str) or not atom.get("kind", "").strip():
                fail(f"atoms[{idx}].kind", "missing_or_empty")

    bindings = spec.get("bindings")
    if not isinstance(bindings, dict):
        fail("bindings", "missing_or_invalid")
        return failures

    for section, default_role in BINDING_SECTION_ROLE.items():
        for idx, binding in enumerate(as_list(bindings.get(section))):
            if not isinstance(binding, dict):
                fail(f"bindings.{section}[{idx}]", "invalid_binding")
                continue
            if not isinstance(binding.get("id"), str) or not binding.get("id", "").strip():
                fail(f"bindings.{section}[{idx}].id", "missing_or_empty")
            atom = binding.get("atom")
            if atom is not None and str(atom) not in atom_ids:
                fail(f"bindings.{section}[{idx}].atom", "unknown_atom")
            role = normalize_role(binding.get("role"), default_role)
            if role not in VALID_ROLES:
                fail(f"bindings.{section}[{idx}].role", "unknown_role")
            observes = as_list(binding.get("observe_at"))
            if not observes:
                fail(f"bindings.{section}[{idx}].observe_at", "missing")
                continue
            for obs_idx, observe in enumerate(observes):
                if not isinstance(observe, dict):
                    fail(f"bindings.{section}[{idx}].observe_at[{obs_idx}]", "invalid_observe_at")
                    continue
                obs_role = normalize_role(observe.get("role"), role)
                if obs_role not in VALID_ROLES:
                    fail(f"bindings.{section}[{idx}].observe_at[{obs_idx}].role", "unknown_role")
                has_site = observe.get("site_id") not in (None, "")
                has_location = bool(source_location(observe))
                has_runtime = observe.get("runtime_event_id") not in (None, "")
                if not has_site and not has_location and not has_runtime:
                    fail(
                        f"bindings.{section}[{idx}].observe_at[{obs_idx}]",
                        "missing_runtime_event_or_source_location",
                    )

    for idx, binding in enumerate(as_list(bindings.get("input_influence"))):
        if not isinstance(binding, dict):
            fail(f"bindings.input_influence[{idx}]", "invalid_binding")
            continue
        if not isinstance(binding.get("id"), str) or not binding.get("id", "").strip():
            fail(f"bindings.input_influence[{idx}].id", "missing_or_empty")
        ranges = as_list(binding.get("ranges"))
        if not ranges:
            fail(f"bindings.input_influence[{idx}].ranges", "missing")
        for range_idx, item in enumerate(ranges):
            if not isinstance(item, dict):
                fail(f"bindings.input_influence[{idx}].ranges[{range_idx}]", "invalid_range")
                continue
            try:
                start = int(item.get("start"))
                length = int(item.get("length", item.get("len")))
            except (TypeError, ValueError):
                fail(f"bindings.input_influence[{idx}].ranges[{range_idx}]", "invalid_bounds")
                continue
            if start < 0 or length <= 0:
                fail(f"bindings.input_influence[{idx}].ranges[{range_idx}]", "invalid_bounds")

    return failures


def binding_spec_to_graph_and_runtime_map(spec: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    failures = validate_binding_spec(spec)
    if failures:
        raise ValueError(json.dumps({"validation_failures": failures}, indent=2))

    target_id = str(spec["tc_id"])
    graph_nodes: List[Dict[str, Any]] = []
    graph_edges: List[Dict[str, Any]] = []
    runtime_events: Dict[str, Dict[str, Any]] = {}

    for atom in spec["atoms"]:
        graph_nodes.append(
            {
                "id": str(atom["id"]),
                "type": "tc_atom",
                "category": str(atom.get("kind") or spec["tc"]["category"]),
                "label": str(atom["expr"]),
                "root": atom.get("root"),
                "source_locations": atom.get("source_locations", []),
            }
        )

    bindings = spec["bindings"]
    lifecycle_nodes: List[str] = []
    for section, default_role in BINDING_SECTION_ROLE.items():
        for binding in as_list(bindings.get(section)):
            atom_id = str(binding.get("atom") or spec["atoms"][0]["id"])
            for obs_idx, observe in enumerate(as_list(binding.get("observe_at"))):
                role = normalize_role(observe.get("role", binding.get("role")), default_role)
                node_type = ROLE_TO_NODE_TYPE[role]
                runtime_key = runtime_event_key(section, binding, observe, obs_idx)
                node_id = f"{role}:{binding['id']}:{obs_idx}"
                node: Dict[str, Any] = {
                    "id": node_id,
                    "type": node_type,
                    "runtime_event_id": runtime_key,
                    "binding_role": role,
                    "atom": atom_id,
                    "label": str(binding.get("expr") or binding.get("event") or binding["id"]),
                    "confidence": observe.get("confidence", binding.get("confidence", "medium")),
                    "binding_required": True,
                }
                loc = source_location(observe)
                if loc:
                    node["source_location"] = loc
                for key in ("value_mode", "component_kind", "direction", "priority"):
                    if observe.get(key) is not None:
                        node[key] = observe[key]
                graph_nodes.append(node)
                graph_edges.append(
                    {
                        "type": "observes_atom",
                        "src": node_id,
                        "dst": atom_id,
                        "role": role,
                    }
                )
                if role == "lifecycle_event":
                    lifecycle_nodes.append(node_id)
                runtime_events[runtime_key] = runtime_map_entry(
                    target_id=target_id,
                    atom_id=atom_id,
                    binding_id=str(binding["id"]),
                    role=role,
                    observe=observe,
                    node_type=node_type,
                    binding_index=obs_idx,
                )

    for left, right in zip(lifecycle_nodes, lifecycle_nodes[1:]):
        graph_edges.append(
            {
                "type": "order_constraint",
                "order": "lifecycle_prefix",
                "src": left,
                "dst": right,
            }
        )

    for binding in as_list(bindings.get("input_influence")):
        atom_id = str(binding.get("atom") or spec["atoms"][0]["id"])
        for idx, item in enumerate(as_list(binding.get("ranges"))):
            graph_nodes.append(
                {
                    "id": f"range:{binding['id']}:{idx}",
                    "type": "candidate_input_influence_range",
                    "atom": atom_id,
                    "runtime_event_id": str(binding.get("runtime_event_id", "")),
                    "start": int(item.get("start")),
                    "length": int(item.get("length", item.get("len"))),
                    "confidence": item.get("confidence", binding.get("confidence", "medium")),
                }
            )

    graph = {
        "target_id": target_id,
        "tc": spec["tc"],
        "nodes": graph_nodes,
        "edges": graph_edges,
        "binding_spec_version": 1,
    }
    runtime_map = {
        "runtime_events": runtime_events,
        "summary": {
            "target_id": target_id,
            "bindings": len(runtime_events),
        },
    }
    return graph, runtime_map


def write_quality_csv(path: Path, audit: Dict[str, Any]) -> None:
    rows = ["target_id,atom_id,category,binding_tier,minimum_tier,lift_allowed,roles,progress_binding_count"]
    for graph in audit.get("graphs", []):
        target_id = str(graph.get("target_id", ""))
        for item in graph.get("binding_tiers", []):
            rows.append(
                ",".join(
                    [
                        target_id,
                        str(item.get("atom_id", "")),
                        str(item.get("category", "")),
                        str(item.get("binding_tier", "")),
                        str(item.get("minimum_tier", "")),
                        str(item.get("lift_allowed", "")),
                        "|".join(item.get("roles", [])),
                        str(item.get("progress_binding_count", "")),
                    ]
                )
            )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(rows) + "\n")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate/materialize a FORMTRIG BindingSpec",
        allow_abbrev=False,
    )
    parser.add_argument("--binding-spec", required=True, type=Path)
    parser.add_argument("--graph-out", type=Path)
    parser.add_argument("--runtime-map-out", type=Path)
    parser.add_argument("--audit-json", type=Path)
    parser.add_argument("--quality-csv", type=Path)
    parser.add_argument("--site-map", type=Path)
    parser.add_argument("--existing-runtime-map", type=Path)
    parser.add_argument("--require-valid", action="store_true")
    parser.add_argument("--require-ready", action="store_true")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    spec = load_json_or_yaml(args.binding_spec)
    failures = validate_binding_spec(spec)
    if failures:
        report = {"status": "fail", "validation_failures": failures}
        text = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.audit_json:
            args.audit_json.parent.mkdir(parents=True, exist_ok=True)
            args.audit_json.write_text(text)
        else:
            sys.stdout.write(text)
        return 2 if args.require_valid else 0

    graph, runtime_map = binding_spec_to_graph_and_runtime_map(spec)
    if args.graph_out:
        args.graph_out.parent.mkdir(parents=True, exist_ok=True)
        args.graph_out.write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n")
    if args.runtime_map_out:
        args.runtime_map_out.parent.mkdir(parents=True, exist_ok=True)
        args.runtime_map_out.write_text(json.dumps(runtime_map, indent=2, sort_keys=True) + "\n")

    if args.audit_json or args.quality_csv or args.require_ready:
        if not args.graph_out:
            raise SystemExit("--audit-json/--quality-csv/--require-ready requires --graph-out")
        runtime_map_path = args.runtime_map_out or args.existing_runtime_map
        runtime_bindings = load_runtime_map(runtime_map_path)
        site_map = parse_site_map(args.site_map)
        graph_audit = graph_binding_audit(args.graph_out, runtime_bindings, site_map)
        audit = {
            "status": "pass" if graph_audit.get("mutation_ready") else "fail",
            "validation_failures": [],
            "graphs": [graph_audit],
            "summary": {
                "graphs": 1,
                "mutation_ready": 1 if graph_audit.get("mutation_ready") else 0,
            },
        }
        if args.audit_json:
            args.audit_json.parent.mkdir(parents=True, exist_ok=True)
            args.audit_json.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n")
        if args.quality_csv:
            write_quality_csv(args.quality_csv, audit)
        print(json.dumps(audit["summary"], sort_keys=True))
        if args.require_ready and not graph_audit.get("mutation_ready"):
            return 3
        return 0

    print(json.dumps({"status": "pass", "validation_failures": []}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
