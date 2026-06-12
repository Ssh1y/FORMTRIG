#!/usr/bin/env python3
"""Audit whether trigger-progress graphs are runnable with native FORMTRIG.

This is a readiness gate, not an observer. It does not infer PNG, SQL, Magma,
or CVE semantics. It asks one narrow question: do the graph nodes that carry
trigger-progress meaning have an external runtime binding that the native
runtime can consume?
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from compile_lift_spec import (
    Binding,
    SITE_KIND_PREFERENCE,
    attach_predecessor_reference_sites,
    apply_source_relocations,
    atom_numeric_id,
    binding_node_for_graph,
    binding_supports_distance,
    compile_graph,
    function_matches,
    graph_has_atom_category,
    load_runtime_map,
    node_binding_required,
    node_binding_role,
    node_source_locations,
    nodes_by_id,
    parse_source_location,
    parse_binding,
    parse_site_map,
    path_matches,
    resolve_binding,
)


PROGRESS_NODE_TYPES = {
    "root_context",
    "root_observe_context",
    "lifecycle_phase",
    "guard_context",
    "producer_context",
    "use_context",
    "same_object_context",
    "object_identity",
    "event_phase_context",
}
RANGE_NODE_TYPES = {"candidate_input_influence_range"}
AUDITED_NODE_TYPES = PROGRESS_NODE_TYPES | RANGE_NODE_TYPES

TIER_RANK = {"B0": 0, "B1": 1, "B2": 2, "B3": 3, "B4": 4}

CATEGORY_MIN_TIER = {
    "numeric-margin": "B1",
    "equality/magic": "B1",
    "binary-state-null": "B2",
    "compound-sequence-lifecycle": "B3",
}

PRODUCER_ROLES = {"producer", "desired_producer", "opposite_producer"}


def graph_node_key(node: Dict[str, Any]) -> str:
    runtime_event_id = node.get("runtime_event_id")
    if runtime_event_id:
        return str(runtime_event_id)
    source_locations = node_source_locations(node)
    if source_locations:
        return f"source:{source_locations[0]}"
    return str(node.get("id"))


def merge_template_entry(
    template: Dict[str, Dict[str, Any]],
    *,
    key: str,
    node: Dict[str, Any],
    required_for: str,
    reason: str,
    candidate_bindings: Optional[List[Dict[str, Any]]] = None,
) -> None:
    entry = template.setdefault(
        key,
        {
            "event_kind": "",
            "site_id": 0,
            "required_for": [],
            "node_types": [],
            "graph_nodes": [],
            "source_locations": [],
            "candidate_bindings": [],
            "reason": [],
        },
    )
    if required_for not in entry["required_for"]:
        entry["required_for"].append(required_for)
    node_type = str(node.get("type"))
    if node_type not in entry["node_types"]:
        entry["node_types"].append(node_type)
    node_id = str(node.get("id"))
    if node_id not in entry["graph_nodes"]:
        entry["graph_nodes"].append(node_id)
    source_location = str(node.get("source_location") or "")
    if source_location and source_location not in entry["source_locations"]:
        entry["source_locations"].append(source_location)
    if reason not in entry["reason"]:
        entry["reason"].append(reason)
    if candidate_bindings:
        candidates = entry.setdefault("candidate_bindings", [])
        seen = {
            (str(item.get("event_kind")), str(item.get("site_id")))
            for item in candidates
            if isinstance(item, dict)
        }
        for candidate in candidate_bindings:
            key_tuple = (str(candidate.get("event_kind")), str(candidate.get("site_id")))
            if key_tuple in seen:
                continue
            candidates.append(candidate)
            seen.add(key_tuple)


def direct_runtime_binding(node: Dict[str, Any]) -> Optional[Binding]:
    runtime_event_id = node.get("runtime_event_id")
    if not runtime_event_id:
        return None
    return parse_binding(runtime_event_id, source="runtime_event_id")


def candidate_bindings_for_node(
    node: Dict[str, Any], site_map: List[Any], *, limit: int = 24
) -> List[Dict[str, Any]]:
    preferred = SITE_KIND_PREFERENCE.get(str(node.get("type")), ())
    out = []  # type: List[Dict[str, Any]]
    seen = set()  # type: set
    for source_location in node_source_locations(node):
        graph_file, line, column, function = parse_source_location(source_location)
        if not graph_file or not line:
            continue
        for entry in site_map:
            if preferred and getattr(entry, "kind", "") not in preferred:
                continue
            if not path_matches(getattr(entry, "file", ""), graph_file):
                continue
            if not function_matches(getattr(entry, "function", ""), function):
                continue
            entry_line = int(getattr(entry, "line", 0))
            exact_line = entry_line == line
            window_line = (
                column is not None and column > 0 and abs(entry_line - line) <= column
            )
            if not exact_line and not window_line:
                continue
            key = (str(getattr(entry, "kind", "")), str(getattr(entry, "site_id", "")))
            if key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "event_kind": getattr(entry, "kind", ""),
                    "site_id": int(getattr(entry, "site_id", 0)),
                    "source": "site-map" if exact_line else "site-map-window",
                    "function": getattr(entry, "function", ""),
                    "file": getattr(entry, "file", ""),
                    "line": entry_line,
                    "column": int(getattr(entry, "column", 0)),
                    "inst_no": int(getattr(entry, "inst_no", 0)),
                    "opcode": getattr(entry, "opcode", ""),
                }
            )
            if len(out) >= limit:
                return out
    return out


def needs_exact_progress_binding(
    graph: Dict[str, Any], node: Dict[str, Any], binding: Binding
) -> bool:
    return (
        str(node.get("type")) == "guard_context"
        and graph_has_atom_category(graph, "numeric-margin")
        and binding.event_kind == "7"
        and not binding_supports_distance(binding)
    )


def collapsed_progress_bindings(binding_details: Any) -> List[Dict[str, Any]]:
    if not isinstance(binding_details, list):
        return []
    by_site: Dict[tuple[str, str], List[Dict[str, Any]]] = {}
    for detail in binding_details:
        if not isinstance(detail, dict):
            continue
        event_kind = str(detail.get("event_kind") or "")
        site_id = str(detail.get("site_id") or "")
        node_type = str(detail.get("type") or "")
        node_id = str(detail.get("node") or "")
        if not event_kind or not site_id or not node_type or not node_id:
            continue
        by_site.setdefault((event_kind, site_id), []).append(detail)
    collapsed: List[Dict[str, Any]] = []
    for (event_kind, site_id), details in by_site.items():
        node_types = sorted({str(item.get("type") or "") for item in details})
        nodes = sorted({str(item.get("node") or "") for item in details})
        if len(node_types) <= 1 or len(nodes) <= 1:
            continue
        collapsed.append(
            {
                "event_kind": event_kind,
                "site_id": site_id,
                "node_types": node_types,
                "nodes": nodes,
                "reason": "multiple_semantic_progress_nodes_share_one_runtime_site",
            }
        )
    return collapsed


def atom_categories(graph: Dict[str, Any]) -> Dict[int, str]:
    out: Dict[int, str] = {}
    for node in graph.get("nodes", []):
        if not isinstance(node, dict) or node.get("type") != "tc_atom":
            continue
        out[atom_numeric_id(node.get("id"))] = str(node.get("category") or "")
    return out


def binding_tier_from_roles(
    roles: set[str], *, has_distance: bool = False, lifecycle_event_count: int = 0
) -> str:
    if not roles and not has_distance:
        return "B0"
    tier = "B0"
    if has_distance or roles.intersection({"root_observe", "guard"}):
        tier = "B1"
    if (
        roles.intersection({"root_observe", "guard"})
        and roles.intersection(PRODUCER_ROLES)
        and "use" in roles
    ):
        tier = "B2"
    if lifecycle_event_count >= 2 and "same_object" in roles:
        tier = "B3"
    if "input_influence" in roles or "repair_hook" in roles:
        tier = "B4"
    return tier


def binding_tier_report(
    graph: Dict[str, Any],
    binding_details: Any,
    *,
    range_rules: int = 0,
) -> List[Dict[str, Any]]:
    if not isinstance(binding_details, list):
        binding_details = []
    categories = atom_categories(graph)
    details_by_atom: Dict[int, List[Dict[str, Any]]] = {}
    for detail in binding_details:
        if not isinstance(detail, dict):
            continue
        try:
            atom_id = int(detail.get("atom_id", 1))
        except (TypeError, ValueError):
            atom_id = 1
        details_by_atom.setdefault(atom_id, []).append(detail)

    atoms = sorted(set(categories) | set(details_by_atom))
    report: List[Dict[str, Any]] = []
    for atom_id in atoms:
        details = details_by_atom.get(atom_id, [])
        roles = {
            str(detail.get("role") or "")
            for detail in details
            if str(detail.get("role") or "")
        }
        lifecycle_event_count = sum(
            1 for detail in details if str(detail.get("role") or "") == "lifecycle_event"
        )
        has_distance = any(
            isinstance(detail.get("emitted_metrics"), list)
            and any(str(metric).endswith("_distance") for metric in detail["emitted_metrics"])
            for detail in details
        )
        tier = binding_tier_from_roles(
            roles,
            has_distance=has_distance,
            lifecycle_event_count=lifecycle_event_count,
        )
        category = categories.get(atom_id, "")
        min_tier = CATEGORY_MIN_TIER.get(category, "B0")
        lift_allowed = TIER_RANK.get(tier, 0) >= TIER_RANK.get(min_tier, 0)
        if range_rules > 0 and TIER_RANK.get(tier, 0) >= 1:
            tier_with_influence = "B4"
        else:
            tier_with_influence = tier
        report.append(
            {
                "atom_id": atom_id,
                "category": category,
                "roles": sorted(roles),
                "lifecycle_event_count": lifecycle_event_count,
                "binding_tier": tier,
                "binding_tier_with_influence": tier_with_influence,
                "minimum_tier": min_tier,
                "lift_allowed": lift_allowed,
                "has_distance_component": has_distance,
                "progress_binding_count": len(details),
            }
        )
    return report


def graph_binding_audit(
    graph_path: Path,
    runtime_map: Dict[str, Binding],
    site_map: List[Any],
    *,
    include_comments: bool = False,
    source_roots: Optional[List[Path]] = None,
) -> Dict[str, Any]:
    source_roots = source_roots or []
    graph = apply_source_relocations(
        json.loads(graph_path.read_text()), site_map, source_roots
    )
    _, compile_report = compile_graph(
        graph_path,
        runtime_map,
        site_map,
        include_comments=include_comments,
        source_roots=source_roots,
    )

    missing_progress = []  # type: List[Dict[str, str]]
    missing_ranges = []  # type: List[Dict[str, str]]
    static_ranges = []  # type: List[Dict[str, str]]
    needs_exact_progress = []  # type: List[Dict[str, Any]]
    template = {}  # type: Dict[str, Dict[str, Any]]
    graph_node_by_id = nodes_by_id(graph)

    for node in graph.get("nodes", []):
        node_type = str(node.get("type"))
        if node_type not in AUDITED_NODE_TYPES:
            continue
        if not node_binding_required(node):
            continue
        binding_node = binding_node_for_graph(node, graph, graph_node_by_id)
        binding_node = attach_predecessor_reference_sites(
            binding_node, graph_node_by_id, runtime_map, site_map
        )
        binding, reason = resolve_binding(binding_node, runtime_map, site_map)
        if binding is not None:
            if needs_exact_progress_binding(graph, node, binding):
                candidates = candidate_bindings_for_node(binding_node, site_map)
                item = {
                    "node": str(node.get("id")),
                    "type": node_type,
                    "role": node_binding_role(node, binding),
                    "key": graph_node_key(binding_node),
                    "reason": "fuzzy_binding_no_distance",
                    "binding_source": binding.source,
                    "event_kind": binding.event_kind,
                    "site_id": binding.site_id,
                    "candidate_bindings": candidates,
                }
                needs_exact_progress.append(item)
                source_locations = node_source_locations(binding_node)
                keys = [item["key"]]
                for loc in source_locations:
                    key = f"source:{loc}"
                    if key not in keys:
                        keys.append(key)
                for key in keys:
                    merge_template_entry(
                        template,
                        key=key,
                        node=binding_node,
                        required_for="exact_progress",
                        reason=item["reason"],
                        candidate_bindings=candidates,
                    )
            continue

        required_for = "progress" if node_type in PROGRESS_NODE_TYPES else "range"
        item = {
            "node": str(node.get("id")),
            "type": node_type,
            "role": node_binding_role(node),
            "key": graph_node_key(binding_node),
            "reason": reason or "unmapped",
        }
        if node_type in PROGRESS_NODE_TYPES:
            missing_progress.append(item)
        else:
            static_ranges.append(item)
            continue

        # A direct numeric binding in runtime_event_id would have worked without
        # a map; symbolic values and source locations need an external binding.
        if direct_runtime_binding(node) is None:
            source_locations = node_source_locations(binding_node)
            keys = [item["key"]]
            for loc in source_locations:
                key = f"source:{loc}"
                if key not in keys:
                    keys.append(key)
            for key in keys:
                merge_template_entry(
                    template,
                    key=key,
                    node=node,
                    required_for=required_for,
                    reason=item["reason"],
                )

    progress_rules = int(compile_report.get("progress_rules", 0))
    range_rules = int(compile_report.get("range_rules", 0))
    binding_details = compile_report.get("binding_details", [])
    exact_progress_bindings = 0
    fuzzy_progress_bindings = 0
    distance_progress_bindings = 0
    collapsed_progress = collapsed_progress_bindings(binding_details)
    tier_report = binding_tier_report(
        graph,
        binding_details,
        range_rules=range_rules,
    )
    insufficient_tiers = [
        item
        for item in tier_report
        if item.get("category") in CATEGORY_MIN_TIER and not item.get("lift_allowed")
    ]
    if isinstance(binding_details, list):
        for detail in binding_details:
            if not isinstance(detail, dict):
                continue
            source = str(detail.get("binding_source") or "")
            if source.startswith("site-map-") and source != "site-map":
                fuzzy_progress_bindings += 1
            else:
                exact_progress_bindings += 1
            metrics = detail.get("emitted_metrics")
            if isinstance(metrics, list) and any(
                str(metric).endswith("_distance") for metric in metrics
            ):
                distance_progress_bindings += 1
    status = "ready" if progress_rules > 0 else "blocked_no_progress"
    if progress_rules > 0 and range_rules == 0 and not missing_progress:
        status = "progress_only_no_hot_ranges"
    if progress_rules > 0 and insufficient_tiers:
        status = "insufficient_binding_tier"
    if progress_rules > 0 and missing_progress:
        status = "partial_progress_bindings"
    if progress_rules > 0 and collapsed_progress:
        status = "collapsed_progress_bindings"
    if progress_rules > 0 and needs_exact_progress:
        status = "needs_exact_progress_binding"

    return {
        "graph": str(graph_path),
        "target_id": str(graph.get("target_id") or graph_path.stem),
        "status": status,
        "runnable": progress_rules > 0,
        "mutation_ready": status == "ready",
        "rules": int(compile_report.get("rules", 0)),
        "progress_rules": progress_rules,
        "range_rules": range_rules,
        "exact_progress_bindings": exact_progress_bindings,
        "fuzzy_progress_bindings": fuzzy_progress_bindings,
        "distance_progress_bindings": distance_progress_bindings,
        "binding_tiers": tier_report,
        "insufficient_binding_tiers": insufficient_tiers,
        "insufficient_binding_tier_count": len(insufficient_tiers),
        "collapsed_progress_bindings": collapsed_progress,
        "collapsed_progress_count": len(collapsed_progress),
        "binding_details": binding_details,
        "needs_exact_progress_bindings": needs_exact_progress,
        "needs_exact_progress_count": len(needs_exact_progress),
        "missing_progress_bindings": missing_progress,
        "missing_range_bindings": missing_ranges,
        "static_range_bindings": static_ranges,
        "missing_progress_count": len(missing_progress),
        "missing_range_count": len(missing_ranges),
        "static_range_count": len(static_ranges),
        "runtime_map_template": template,
        "compile_skipped": compile_report.get("skipped", []),
    }


def write_runtime_template(path: Path, audits: List[Dict[str, Any]]) -> None:
    merged = {}  # type: Dict[str, Dict[str, Any]]
    for audit in audits:
        target_id = audit["target_id"]
        for key, entry in audit["runtime_map_template"].items():
            out = merged.setdefault(key, dict(entry))
            targets = out.setdefault("target_ids", [])
            if target_id not in targets:
                targets.append(target_id)
            for field in (
                "required_for",
                "node_types",
                "graph_nodes",
                "source_locations",
                "reason",
            ):
                values = out.setdefault(field, [])
                for value in entry.get(field, []):
                    if value not in values:
                        values.append(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"runtime_events": merged}, indent=2, sort_keys=True) + "\n")


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Audit native FORMTRIG runtime bindings for trigger graphs",
        allow_abbrev=False,
    )
    parser.add_argument(
        "--trigger-graph",
        action="append",
        required=True,
        type=Path,
        help="Trigger-progress graph JSON. May be passed multiple times.",
    )
    parser.add_argument("--runtime-map", type=Path, help="External runtime binding JSON")
    parser.add_argument("--site-map", type=Path, help="FORMTRIG_SITE_MAP output")
    parser.add_argument(
        "--source-root",
        action="append",
        default=[],
        type=Path,
        help="External source root used to relocate stale/generated source locations.",
    )
    parser.add_argument("--report-json", type=Path, help="Write structured audit report")
    parser.add_argument(
        "--template-out",
        type=Path,
        help="Write a runtime-map template containing missing symbolic bindings",
    )
    parser.add_argument(
        "--fail-on-unrunnable",
        action="store_true",
        help="Exit non-zero if any graph has no progress rules.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    runtime_map = load_runtime_map(args.runtime_map)
    site_map = parse_site_map(args.site_map)
    audits = [
        graph_binding_audit(graph, runtime_map, site_map, source_roots=args.source_root)
        for graph in args.trigger_graph
    ]
    report = {
        "graphs": audits,
        "summary": {
            "graphs": len(audits),
            "runnable": sum(1 for item in audits if item["runnable"]),
            "mutation_ready": sum(1 for item in audits if item["mutation_ready"]),
            "blocked_no_progress": sum(
                1 for item in audits if item["status"] == "blocked_no_progress"
            ),
        },
    }

    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(text)
    else:
        sys.stdout.write(text)

    if args.template_out:
        write_runtime_template(args.template_out, audits)

    if args.fail_on_unrunnable and any(not item["runnable"] for item in audits):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
