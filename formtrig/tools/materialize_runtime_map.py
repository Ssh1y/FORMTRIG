#!/usr/bin/env python3
"""Materialize a FORMTRIG runtime-map from graph bindings and site-map data."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Union, Optional, Tuple

from audit_lift_bindings import (
    AUDITED_NODE_TYPES,
    PROGRESS_NODE_TYPES,
    graph_binding_audit,
    write_runtime_template,
)
from compile_lift_spec import (
    Binding,
    apply_source_relocations,
    attach_predecessor_reference_sites,
    binding_node_for_graph,
    load_runtime_map,
    nodes_by_id,
    node_source_locations,
    parse_site_map,
    resolve_binding,
)


def binding_payload(binding: Binding, *, node: Dict[str, Any], target_id: str) -> Dict[str, Any]:
    site_id = None  # type: Union[int, str, None]
    site_id = int(binding.site_id) if binding.site_id.isdigit() else binding.site_id
    event_kind = None  # type: Union[int, str, None]
    event_kind = int(binding.event_kind) if binding.event_kind.isdigit() else binding.event_kind
    return {
        "event_kind": event_kind,
        "site_id": site_id,
        "source": binding.source,
        "target_id": target_id,
        "node_id": str(node.get("id")),
        "node_type": str(node.get("type")),
        "source_location": str(node.get("source_location") or ""),
    }


def preferred_output_key(node: Dict[str, Any]) -> str:
    keys = preferred_output_keys(node)
    return keys[0]


def preferred_output_keys(node: Dict[str, Any]) -> List[str]:
    runtime_event_id = node.get("runtime_event_id")
    if runtime_event_id:
        return [str(runtime_event_id)]
    source_locations = node_source_locations(node)
    if source_locations:
        return [f"source:{loc}" for loc in source_locations]
    return [str(node.get("id"))]


def materialize_graph_bindings(
    graph_path: Path,
    runtime_map: Dict[str, Binding],
    site_map: List[Any],
    *,
    source_roots: Optional[List[Path]] = None,
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    source_roots = source_roots or []
    graph = apply_source_relocations(
        json.loads(graph_path.read_text()), site_map, source_roots
    )
    target_id = str(graph.get("target_id") or graph_path.stem)
    output = {}  # type: Dict[str, Dict[str, Any]]
    graph_node_by_id = nodes_by_id(graph)

    for node in graph.get("nodes", []):
        node_type = str(node.get("type"))
        if node_type not in AUDITED_NODE_TYPES:
            continue
        binding_node = node
        if node_type in PROGRESS_NODE_TYPES:
            binding_node = binding_node_for_graph(node, graph, graph_node_by_id)
            binding_node = attach_predecessor_reference_sites(
                binding_node, graph_node_by_id, runtime_map, site_map
            )
        binding, _ = resolve_binding(binding_node, runtime_map, site_map)
        if binding is None:
            continue
        keys = preferred_output_keys(binding_node)
        if node_type in PROGRESS_NODE_TYPES:
            for key in keys:
                output[key] = binding_payload(
                    binding, node=binding_node, target_id=target_id
                )
        else:
            for key in keys:
                if key not in output:
                    output[key] = binding_payload(
                        binding, node=binding_node, target_id=target_id
                    )

    audit = graph_binding_audit(
        graph_path, runtime_map, site_map, source_roots=source_roots
    )
    return output, audit


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create a runtime-map JSON from FORMTRIG graph/site-map bindings",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--trigger-graph",
        action="append",
        required=True,
        type=Path,
        help="Trigger-progress graph JSON. May be passed multiple times.",
    )
    parser.add_argument("--runtime-map", type=Path, help="Manual/existing runtime-map JSON")
    parser.add_argument("--site-map", type=Path, help="FORMTRIG_SITE_MAP output")
    parser.add_argument(
        "--source-root",
        action="append",
        default=[],
        type=Path,
        help="External source root used to relocate stale/generated source locations.",
    )
    parser.add_argument("-o", "--output", required=True, type=Path, help="Runtime-map JSON output")
    parser.add_argument("--audit-json", type=Path, help="Write binding audit JSON")
    parser.add_argument("--template-out", type=Path, help="Write missing-binding template")
    parser.add_argument(
        "--require-progress",
        action="store_true",
        help="Exit non-zero unless every graph has at least one progress rule.",
    )
    parser.add_argument(
        "--require-ready",
        action="store_true",
        help=(
            "Exit non-zero unless every graph has runnable progress and no "
            "exact-progress binding debt."
        ),
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    runtime_map = load_runtime_map(args.runtime_map)
    site_map = parse_site_map(args.site_map)

    merged = {}  # type: Dict[str, Dict[str, Any]]
    audits = []  # type: List[Dict[str, Any]]
    for graph in args.trigger_graph:
        bindings, audit = materialize_graph_bindings(
            graph, runtime_map, site_map, source_roots=args.source_root
        )
        merged.update(bindings)
        audits.append(audit)

    ready_count = sum(
        1
        for item in audits
        if item["runnable"] and int(item.get("needs_exact_progress_count", 0)) == 0
    )
    payload = {
        "runtime_events": merged,
        "summary": {
            "graphs": len(audits),
            "bindings": len(merged),
            "runnable": sum(1 for item in audits if item["runnable"]),
            "ready": ready_count,
            "mutation_ready": sum(1 for item in audits if item["mutation_ready"]),
            "needs_exact_progress_binding": sum(
                1 for item in audits if item["status"] == "needs_exact_progress_binding"
            ),
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    audit_report = {
        "graphs": audits,
        "summary": {
            "graphs": len(audits),
            "runnable": sum(1 for item in audits if item["runnable"]),
            "ready": ready_count,
            "mutation_ready": sum(1 for item in audits if item["mutation_ready"]),
            "blocked_no_progress": sum(
                1 for item in audits if item["status"] == "blocked_no_progress"
            ),
            "needs_exact_progress_binding": sum(
                1 for item in audits if item["status"] == "needs_exact_progress_binding"
            ),
        },
    }
    if args.audit_json:
        args.audit_json.parent.mkdir(parents=True, exist_ok=True)
        args.audit_json.write_text(json.dumps(audit_report, indent=2, sort_keys=True) + "\n")
    if args.template_out:
        write_runtime_template(args.template_out, audits)

    print(json.dumps(payload["summary"], sort_keys=True))
    if args.require_progress and any(not item["runnable"] for item in audits):
        return 2
    if args.require_ready and ready_count != len(audits):
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
