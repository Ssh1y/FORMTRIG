#!/usr/bin/env python3
"""Compile trigger-progress graphs into FORMTRIG_LIFT_SPEC.

This tool is intentionally a compiler, not an observer. It does not parse PNG,
SQL, Magma, CVE inputs, or target-specific formats. It only translates graph
nodes that already have an external runtime binding into the small spec language
consumed by the native FORMTRIG runtime.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, NamedTuple, Optional, Tuple


EVENT_KIND = {
    "target": 1,
    "reached": 1,
    "crash": 2,
    "trigger": 2,
    "direct": 4,
    "load": 5,
    "store": 6,
    "cmp": 7,
    "compare": 7,
    "branch": 8,
    "div": 10,
    "binary": 11,
    "arith": 11,
    "manual": 12,
    "memtransfer": 15,
    "memtransfer_call": 15,
}

COMPONENT = {
    "native_distance": 1,
    "lifted_distance": 2,
    "boundary_margin": 3,
    "operand_influence": 4,
    "guard_progress": 5,
    "producer_use": 6,
    "lifecycle_prefix": 7,
    "object_identity": 8,
    "event_phase": 9,
}

COMPONENT_BY_ID = {str(v): k for k, v in COMPONENT.items()}

CONFIDENCE = {
    "none": 0.0,
    "low": 0.35,
    "medium": 0.65,
    "med": 0.65,
    "high": 0.85,
    "verified": 0.95,
}

NODE_KIND_COMPONENT = {
    "root_context": COMPONENT["producer_use"],
    "root_observe_context": COMPONENT["producer_use"],
    "guard_context": COMPONENT["guard_progress"],
    "producer_context": COMPONENT["producer_use"],
    "use_context": COMPONENT["producer_use"],
    "same_object_context": COMPONENT["object_identity"],
    "object_identity": COMPONENT["object_identity"],
    "event_phase_context": COMPONENT["event_phase"],
}

NODE_KIND_PRIORITY = {
    "root_context": 25,
    "root_observe_context": 25,
    "guard_context": 20,
    "producer_context": 30,
    "use_context": 30,
    "same_object_context": 40,
    "object_identity": 40,
    "event_phase_context": 15,
}

NODE_KIND_ROLE = {
    "root_context": "root_observe",
    "root_observe_context": "root_observe",
    "guard_context": "guard",
    "producer_context": "producer",
    "use_context": "use",
    "same_object_context": "same_object",
    "object_identity": "same_object",
    "event_phase_context": "lifecycle_event",
    "lifecycle_phase": "lifecycle_event",
}

ROLE_ALIASES = {
    "root": "root_observe",
    "root_observe": "root_observe",
    "root-observe": "root_observe",
    "root_observation": "root_observe",
    "guard": "guard",
    "producer": "producer",
    "desired_producer": "desired_producer",
    "desired-producer": "desired_producer",
    "opposite_producer": "opposite_producer",
    "opposite-producer": "opposite_producer",
    "use": "use",
    "lifecycle": "lifecycle_event",
    "lifecycle_event": "lifecycle_event",
    "lifecycle-event": "lifecycle_event",
    "same_object": "same_object",
    "same-object": "same_object",
    "object_identity": "same_object",
    "object-identity": "same_object",
    "input_influence": "input_influence",
    "input-influence": "input_influence",
    "repair_hook": "repair_hook",
    "repair-hook": "repair_hook",
}

ROLE_COMPONENT = {
    "root_observe": COMPONENT["producer_use"],
    "guard": COMPONENT["guard_progress"],
    "producer": COMPONENT["producer_use"],
    "desired_producer": COMPONENT["producer_use"],
    "opposite_producer": COMPONENT["producer_use"],
    "use": COMPONENT["producer_use"],
    "lifecycle_event": COMPONENT["event_phase"],
    "same_object": COMPONENT["object_identity"],
    "input_influence": COMPONENT["operand_influence"],
}

ROLE_PRIORITY = {
    "root_observe": 25,
    "guard": 20,
    "producer": 30,
    "desired_producer": 30,
    "opposite_producer": 30,
    "use": 30,
    "lifecycle_event": 15,
    "same_object": 40,
    "input_influence": 10,
}

VALUE_MODES = {
    "const": "const",
    "value": "const",
    "0": "const",
    "distance": "distance",
    "dist": "distance",
    "1": "distance",
    "hit": "hit",
    "2": "hit",
    "outcome": "outcome",
    "3": "outcome",
    "not_outcome": "not_outcome",
    "not-outcome": "not_outcome",
    "4": "not_outcome",
    "a": "a",
    "5": "a",
    "b": "b",
    "6": "b",
    "c": "c",
    "7": "c",
}

SITE_KIND_PREFERENCE = {
    "guard_context": ("cmp", "branch"),
    "producer_context": ("store", "load", "cmp", "branch", "memtransfer"),
    "use_context": ("load", "cmp", "branch"),
    "lifecycle_phase": ("branch", "cmp"),
}

DIV_OPCODES = {"udiv", "sdiv", "urem", "srem"}
DISALLOWED_LIFT_EVENT_KINDS = {"1", "2"}
PRODUCER_SOURCE_EDGE_TYPES = {"order_before", "order_constraint"}
DEFAULT_INFERRED_SOURCE_WINDOW = 8
SOURCE_LABEL_SEARCH_WINDOW = 16
SOURCE_LABEL_ANCHOR_RE = re.compile(r"\bMAGMA_LOG(?:_V)?\s*\(")

FNV_OFFSET = 1469598103934665603
FNV_PRIME = 1099511628211


class Binding(NamedTuple):
    event_kind: str
    site_id: str
    source: str
    attributes: Optional[Dict[str, Any]] = None


class SiteMapEntry(NamedTuple):
    site_id: int
    kind: str
    function: str
    inst_no: int
    opcode: str
    file: str
    line: int
    column: int


def fnv1a64(text: str) -> int:
    h = FNV_OFFSET
    for b in text.encode("utf-8"):
        h ^= b
        h = (h * FNV_PRIME) & 0xFFFFFFFFFFFFFFFF
    return h


def atom_numeric_id(atom_id: Optional[str], default: int = 1) -> int:
    if not atom_id:
        return default
    m = re.search(r"a(\d+)$", atom_id)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)$", atom_id)
    if m:
        return int(m.group(1))
    return (fnv1a64(atom_id) & 0x7FFFFFFF) or default


def confidence_value(node: Dict[str, Any]) -> float:
    score = node.get("confidence_score")
    if isinstance(score, (int, float)):
        return max(0.0, min(1.0, float(score)))
    raw = str(node.get("confidence", "medium")).lower()
    return CONFIDENCE.get(raw, 0.65)


def binding_attrs(binding: Optional[Binding]) -> Dict[str, Any]:
    if binding is None or not isinstance(binding.attributes, dict):
        return {}
    return binding.attributes


def first_attr(
    node: Dict[str, Any], binding: Optional[Binding], names: Iterable[str]
) -> Any:
    attrs = binding_attrs(binding)
    for name in names:
        if node.get(name) is not None:
            return node.get(name)
    for name in names:
        if attrs.get(name) is not None:
            return attrs.get(name)
    return None


def normalize_role(raw: Any) -> Optional[str]:
    if raw is None:
        return None
    role = str(raw).strip().lower()
    if not role:
        return None
    return ROLE_ALIASES.get(role, role if role in ROLE_ALIASES.values() else None)


def node_binding_role(node: Dict[str, Any], binding: Optional[Binding] = None) -> str:
    raw = first_attr(node, binding, ("binding_role", "role", "semantic_role"))
    role = normalize_role(raw)
    if role:
        return role
    return NODE_KIND_ROLE.get(str(node.get("type")), str(node.get("type")))


def parse_component_kind_value(raw: Any, default: int) -> int:
    if raw is None:
        return default
    if isinstance(raw, int):
        return raw
    token = str(raw).strip()
    if not token:
        return default
    if token.isdigit():
        return int(token)
    return COMPONENT.get(token.lower(), default)


def parse_priority_value(raw: Any, default: int) -> int:
    if raw is None:
        return default
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return default
    return max(1, value)


def parse_direction_value(raw: Any, default: str = "higher") -> str:
    if raw is None:
        return default
    token = str(raw).strip().lower()
    if token in {"lower", "lt", "-", "1", "min", "decrease"}:
        return "lower"
    if token in {"higher", "gt", "+", "2", "max", "increase"}:
        return "higher"
    return default


def parse_value_mode_value(raw: Any, default: str = "hit") -> str:
    if raw is None:
        return default
    token = str(raw).strip().lower()
    if not token:
        return default
    return VALUE_MODES.get(token, default)


def parse_float_value(raw: Any, default: float) -> float:
    if raw is None:
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def parse_u64_value(raw: Any, default: int) -> int:
    if raw is None:
        return default
    try:
        value = int(str(raw), 0)
    except (TypeError, ValueError):
        return default
    return value if value >= 0 else default


def has_explicit_component_fields(
    node: Dict[str, Any], binding: Optional[Binding]
) -> bool:
    attrs = binding_attrs(binding)
    keys = {
        "progress_component",
        "progress_components",
        "component",
        "components",
        "component_kind",
        "kind",
        "value_mode",
        "metric",
        "direction",
        "value",
    }
    return any(key in node for key in keys) or any(key in attrs for key in keys)


def raw_component_specs(node: Dict[str, Any], binding: Optional[Binding]) -> List[Any]:
    attrs = binding_attrs(binding)
    for key in ("progress_components", "components"):
        raw = node.get(key, attrs.get(key))
        if raw is not None:
            return raw if isinstance(raw, list) else [raw]
    for key in ("progress_component", "component"):
        raw = node.get(key, attrs.get(key))
        if raw is not None:
            return raw if isinstance(raw, list) else [raw]
    return [{}] if has_explicit_component_fields(node, binding) else []


def component_metric_name(component_kind: int, value_mode: str) -> str:
    name = COMPONENT_BY_ID.get(str(component_kind), f"component_{component_kind}")
    return f"{name}_{value_mode}"


def spec_number(value: float) -> str:
    if float(value).is_integer():
        return f"{value:.1f}"
    return f"{value:.6g}"


def explicit_component_specs(
    node: Dict[str, Any],
    binding: Binding,
    *,
    default_component_kind: int,
    default_priority: int,
    default_confidence: float,
    default_source_id: int,
    default_context_hash: int,
) -> List[Dict[str, Any]]:
    specs = []  # type: List[Dict[str, Any]]
    attrs = binding_attrs(binding)
    role = node_binding_role(node, binding)
    role_component = ROLE_COMPONENT.get(role, default_component_kind)
    role_priority = ROLE_PRIORITY.get(role, default_priority)

    for raw in raw_component_specs(node, binding):
        if isinstance(raw, str):
            raw = {"component_kind": raw}
        if not isinstance(raw, dict):
            continue
        component_kind = parse_component_kind_value(
            raw.get(
                "component_kind",
                raw.get("kind", first_attr(node, binding, ("component_kind", "kind"))),
            ),
            role_component,
        )
        priority = parse_priority_value(
            raw.get("priority", first_attr(node, binding, ("priority",))),
            role_priority,
        )
        direction = parse_direction_value(
            raw.get("direction", first_attr(node, binding, ("direction",))),
            "higher",
        )
        value_mode = parse_value_mode_value(
            raw.get("value_mode", raw.get("metric", first_attr(node, binding, ("value_mode", "metric")))),
            "hit",
        )
        value = parse_float_value(
            raw.get("value", first_attr(node, binding, ("value",))),
            1.0 if value_mode == "hit" else 0.0,
        )
        confidence = parse_float_value(
            raw.get("confidence", attrs.get("confidence")),
            default_confidence,
        )
        source_id = parse_u64_value(
            raw.get("source_id", first_attr(node, binding, ("source_id",))),
            default_source_id,
        )
        context_hash = parse_u64_value(
            raw.get("context_hash", first_attr(node, binding, ("context_hash",))),
            default_context_hash,
        )
        specs.append(
            {
                "component_kind": component_kind,
                "priority": priority,
                "direction": direction,
                "value_mode": value_mode,
                "value": value,
                "confidence": max(0.0, min(1.0, confidence)),
                "source_id": source_id,
                "context_hash": context_hash,
                "metric": str(raw.get("name") or component_metric_name(component_kind, value_mode)),
            }
        )
    return specs


def parse_event_kind(value: Any) -> Optional[str]:
    if value is None:
        return "*"
    if isinstance(value, int):
        return str(value)
    token = str(value).strip()
    if not token:
        return "*"
    if token == "*":
        return token
    if token.isdigit():
        return token
    kind = EVENT_KIND.get(token.lower())
    if kind is None:
        return None
    return str(kind)


def parse_binding(value: Any, *, source: str) -> Optional[Binding]:
    if isinstance(value, int):
        return Binding("*", str(value), source)
    if isinstance(value, str):
        token = value.strip()
        if not token:
            return None
        if token.isdigit():
            return Binding("*", token, source)
        m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*|\d+)[@:](\d+)$", token)
        if not m:
            return None
        event_kind = parse_event_kind(m.group(1))
        if event_kind is None:
            return None
        return Binding(event_kind, m.group(2), source)
    if isinstance(value, dict):
        binding_source = source
        raw_source = value.get("source")
        if isinstance(raw_source, str) and raw_source.strip():
            binding_source = raw_source.strip()
        attrs = {
            str(k): v
            for k, v in value.items()
            if k
            not in {
                "event_kind",
                "kind",
                "event",
                "site_id",
                "site",
                "id",
                "source",
            }
        }
        site = value.get("site_id", value.get("site", value.get("id")))
        if site is None:
            return None
        if isinstance(site, str) and not site.strip().isdigit():
            nested = parse_binding(site, source=binding_source)
            if nested is None:
                return None
            return Binding(
                nested.event_kind,
                nested.site_id,
                nested.source,
                attrs or nested.attributes,
            )
        event_kind = parse_event_kind(
            value.get("event_kind", value.get("kind", value.get("event")))
        )
        if event_kind is None:
            return None
        return Binding(event_kind, str(int(site)), binding_source, attrs or None)
    return None


def node_requires_concrete_site(node: Dict[str, Any]) -> bool:
    node_type = str(node.get("type"))
    return node_type == "lifecycle_phase" or node_type in NODE_KIND_COMPONENT


def node_binding_required(node: Dict[str, Any]) -> bool:
    value = node.get("binding_required")
    if isinstance(value, bool):
        return value
    if value is None:
        return True
    return str(value).strip().lower() not in {"0", "false", "no", "off"}


def unsafe_binding_reason(
    binding: Binding, *, require_concrete_site: bool = False
) -> Optional[str]:
    if binding.event_kind in DISALLOWED_LIFT_EVENT_KINDS:
        return f"disallowed_lift_event_kind:{binding.event_kind}"
    if require_concrete_site:
        if not binding.site_id.isdigit():
            return f"non_concrete_lift_site:{binding.site_id}"
        if int(binding.site_id) <= 0:
            return f"non_concrete_lift_site:{binding.site_id}"
    return None


def binding_is_lift_safe(
    binding: Binding, *, require_concrete_site: bool = False
) -> bool:
    return unsafe_binding_reason(
        binding, require_concrete_site=require_concrete_site
    ) is None


def load_runtime_map(path: Optional[Path]) -> Dict[str, Binding]:
    if path is None:
        return {}
    data = json.loads(path.read_text())
    out = {}  # type: Dict[str, Binding]

    def add(key: Any, value: Any, source: str) -> None:
        if key is None:
            return
        binding = parse_binding(value, source=source)
        if binding is not None:
            out[str(key)] = binding

    if isinstance(data, list):
        for entry in data:
            if not isinstance(entry, dict):
                continue
            key = (
                entry.get("runtime_event_id")
                or entry.get("node_id")
                or entry.get("id")
                or entry.get("name")
            )
            add(key, entry, f"{path}:{key}")
        return out

    if not isinstance(data, dict):
        raise ValueError(f"{path}: runtime map must be a JSON object or array")

    for section in ("events", "nodes", "runtime_events", "bindings"):
        value = data.get(section)
        if isinstance(value, dict):
            for key, binding in value.items():
                add(key, binding, f"{path}:{section}:{key}")
        elif isinstance(value, list):
            for entry in value:
                if not isinstance(entry, dict):
                    continue
                key = (
                    entry.get("runtime_event_id")
                    or entry.get("node_id")
                    or entry.get("id")
                    or entry.get("name")
                )
                add(key, entry, f"{path}:{section}:{key}")

    for key, value in data.items():
        if key in {"events", "nodes", "runtime_events", "bindings"}:
            continue
        add(key, value, f"{path}:{key}")

    return out


def parse_site_map(path: Optional[Path]) -> List[SiteMapEntry]:
    if path is None:
        return []
    entries = []  # type: List[SiteMapEntry]
    for lineno, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        fields = line.split("\t")
        if len(fields) < 8:
            raise ValueError(f"{path}:{lineno}: expected 8 tab-separated fields")
        try:
            entries.append(
                SiteMapEntry(
                    site_id=int(fields[0], 0),
                    kind=fields[1],
                    function=fields[2],
                    inst_no=int(fields[3], 0),
                    opcode=fields[4],
                    file=fields[5],
                    line=int(fields[6], 0),
                    column=int(fields[7], 0),
                )
            )
        except ValueError as exc:
            raise ValueError(f"{path}:{lineno}: invalid site-map row: {exc}") from exc
    return entries


def parse_source_location(raw: Optional[str]) -> Tuple[str, int, Optional[int], Optional[str]]:
    if not raw:
        return ("", 0, None, None)
    loc, _, function = raw.partition("#")
    parts = loc.rsplit(":", 2)
    if len(parts) >= 3 and parts[-1].isdigit() and parts[-2].isdigit():
        return (parts[0], int(parts[-2]), int(parts[-1]), function or None)
    parts = loc.rsplit(":", 1)
    if len(parts) == 2 and parts[-1].isdigit():
        return (parts[0], int(parts[-1]), None, function or None)
    else:
        return (loc, 0, None, function or None)


def node_source_locations(node: Dict[str, Any]) -> List[str]:
    values = []  # type: List[str]
    raw_values = []  # type: List[Any]
    if node.get("source_location") is not None:
        raw_values.append(node.get("source_location"))
    if node.get("source_locations") is not None:
        raw_values.append(node.get("source_locations"))

    def add(raw: Any) -> None:
        if raw is None:
            return
        if isinstance(raw, dict):
            raw = raw.get("location") or raw.get("source_location")
        if not isinstance(raw, str):
            return
        for part in raw.split(";"):
            item = part.strip()
            if item and item not in values:
                values.append(item)

    for raw in raw_values:
        if isinstance(raw, list):
            for item in raw:
                add(item)
        else:
            add(raw)
    return values


def compact_text(value: str) -> str:
    return re.sub(r"\s+", "", value)


def searchable_source_label(node: Dict[str, Any]) -> Optional[str]:
    label = str(node.get("label") or "").strip()
    if len(label) < 4:
        return None
    if not re.search(r"[<>=!&|+\-*/()[\].]", label):
        return None
    if re.search(r"\.(?:c|cc|cpp|cxx|h|hpp):\d+", label):
        return None
    return label


def unique_paths(paths: Iterable[Path]) -> List[Path]:
    out = []  # type: List[Path]
    seen = set()  # type: set
    for path in paths:
        try:
            key = str(path.resolve())
        except OSError:
            key = str(path)
        if key in seen:
            continue
        seen.add(key)
        out.append(path)
    return out


def source_file_candidates(
    graph_file: str,
    site_map: List[SiteMapEntry],
    source_roots: List[Path],
) -> List[Path]:
    if not source_roots:
        return []
    raw_names = []  # type: List[str]
    seen_names = set()  # type: set
    def add_name(name: str) -> None:
        if not name or name in seen_names:
            return
        seen_names.add(name)
        raw_names.append(name)
    if graph_file:
        add_name(graph_file)
    for entry in site_map:
        add_name(entry.file)
    basenames = {Path(name.replace("\\", "/")).name for name in raw_names if name}
    candidates = []  # type: List[Path]
    for root in source_roots:
        if not root.exists():
            continue
        for name in raw_names:
            if not name:
                continue
            normalized = name.replace("\\", "/").lstrip("/")
            direct = root / normalized
            if direct.is_file():
                candidates.append(direct)
        for basename in basenames:
            if not basename:
                continue
            direct = root / basename
            if direct.is_file():
                candidates.append(direct)
            try:
                candidates.extend(path for path in root.rglob(basename) if path.is_file())
            except OSError:
                continue
    return unique_paths(candidates)


def source_label_match_lines(lines: List[str], needle: str) -> List[int]:
    found = []  # type: List[int]
    seen = set()  # type: set

    def add_line(lineno: int) -> None:
        if lineno <= 0 or lineno in seen:
            return
        seen.add(lineno)
        found.append(lineno)

    for start in range(len(lines)):
        compact_window = ""
        offset_to_line = []  # type: List[int]
        max_end = min(len(lines), start + SOURCE_LABEL_SEARCH_WINDOW)
        for end in range(start, max_end):
            compact_line = compact_text(lines[end])
            if compact_line:
                offset_to_line.extend([end + 1] * len(compact_line))
                compact_window += compact_line
            pos = compact_window.find(needle)
            if pos < 0:
                continue

            if offset_to_line:
                begin_line = offset_to_line[pos]
                end_pos = min(pos + len(needle) - 1, len(offset_to_line) - 1)
                end_line = offset_to_line[end_pos]
            else:
                begin_line = end + 1
                end_line = end + 1

            add_line(begin_line)
            for lineno in range(begin_line + 1, end_line + 1):
                add_line(lineno)
            for anchor_idx in range(start, end + 1):
                if SOURCE_LABEL_ANCHOR_RE.search(lines[anchor_idx]):
                    add_line(anchor_idx + 1)
            break
    return found


def relocated_source_locations(
    node: Dict[str, Any],
    site_map: List[SiteMapEntry],
    source_roots: List[Path],
) -> List[str]:
    label = searchable_source_label(node)
    if label is None:
        return []
    source_locations = node_source_locations(node)
    if not source_locations:
        return []
    graph_file, _, column, function = parse_source_location(source_locations[0])
    needle = compact_text(label)
    if not needle:
        return []
    found = []  # type: List[str]
    for candidate in source_file_candidates(graph_file, site_map, source_roots):
        try:
            lines = candidate.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for lineno in source_label_match_lines(lines, needle):
            loc = f"{candidate.name}:{lineno}"
            if function:
                loc += f"#{function}"
            if loc not in found:
                found.append(loc)
    return found


def apply_source_relocations(
    graph: Dict[str, Any],
    site_map: List[SiteMapEntry],
    source_roots: List[Path],
) -> Dict[str, Any]:
    if not source_roots:
        return graph
    out = dict(graph)
    relocated_nodes = []  # type: List[Dict[str, Any]]
    for node in graph.get("nodes", []):
        if not isinstance(node, dict):
            relocated_nodes.append(node)
            continue
        relocations = relocated_source_locations(node, site_map, source_roots)
        if not relocations:
            relocated_nodes.append(node)
            continue
        updated = dict(node)
        if node.get("source_location"):
            updated["_source_original_location"] = str(node.get("source_location"))
        updated["source_location"] = relocations[0]
        updated["source_locations"] = relocations
        updated["_source_relocation"] = "label_search"
        relocated_nodes.append(updated)
    out["nodes"] = relocated_nodes
    return out


def nodes_by_id(graph: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        str(node.get("id")): node
        for node in graph.get("nodes", [])
        if isinstance(node, dict) and node.get("id") is not None
    }


def infer_producer_source_locations(
    node: Dict[str, Any],
    graph: Dict[str, Any],
    by_id: Dict[str, Dict[str, Any]],
) -> List[str]:
    if str(node.get("type")) != "producer_context":
        return []
    node_id = str(node.get("id"))
    locations = []  # type: List[str]
    for edge in graph.get("edges", []):
        if not isinstance(edge, dict):
            continue
        if edge.get("type") not in PRODUCER_SOURCE_EDGE_TYPES:
            continue
        if str(edge.get("src")) != node_id:
            continue
        dst = by_id.get(str(edge.get("dst")))
        if not dst:
            continue
        for loc in node_source_locations(dst):
            if loc not in locations:
                locations.append(loc)
    return locations


def infer_producer_successor_ids(
    node: Dict[str, Any],
    graph: Dict[str, Any],
    by_id: Dict[str, Dict[str, Any]],
) -> List[str]:
    if str(node.get("type")) != "producer_context":
        return []
    node_id = str(node.get("id"))
    successors = []  # type: List[str]
    for edge in graph.get("edges", []):
        if not isinstance(edge, dict):
            continue
        if edge.get("type") not in PRODUCER_SOURCE_EDGE_TYPES:
            continue
        if str(edge.get("src")) != node_id:
            continue
        dst_id = str(edge.get("dst"))
        if dst_id in by_id and dst_id not in successors:
            successors.append(dst_id)
    return successors


def inferred_source_window(node: Dict[str, Any]) -> int:
    windows = []  # type: List[int]
    for loc in node_source_locations(node):
        _, _, column, _ = parse_source_location(loc)
        if column is not None and column > 0:
            windows.append(column)
    if not windows:
        return DEFAULT_INFERRED_SOURCE_WINDOW
    return max(windows)


def binding_node_for_graph(
    node: Dict[str, Any],
    graph: Dict[str, Any],
    by_id: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    if node_source_locations(node):
        return node
    by_id = by_id if by_id is not None else nodes_by_id(graph)
    inferred = infer_producer_source_locations(node, graph, by_id)
    if not inferred:
        return node
    out = dict(node)
    out["source_locations"] = inferred
    out["_source_inference"] = "ordered_successor"
    out["_source_inference_direction"] = "predecessor"
    out["_source_inference_successors"] = infer_producer_successor_ids(node, graph, by_id)
    out["_source_inference_window"] = inferred_source_window(out)
    return out


def site_entries_by_id(site_map: List[SiteMapEntry]) -> Dict[str, SiteMapEntry]:
    return {str(entry.site_id): entry for entry in site_map}


def line_cluster_candidate(candidates: List[SiteMapEntry]) -> Optional[SiteMapEntry]:
    if not candidates:
        return None
    first = candidates[0]
    for entry in candidates[1:]:
        if (
            entry.kind != first.kind
            or entry.function != first.function
            or entry.file != first.file
            or entry.line != first.line
        ):
            return None
    return sorted(candidates, key=lambda item: (item.inst_no, item.site_id))[0]


def binding_from_site_entry(entry: SiteMapEntry, source: str) -> Tuple[Optional[Binding], Optional[str]]:
    event_kind = site_map_event_kind(entry)
    if event_kind is None:
        return (None, f"unsupported_site_kind:{entry.kind}")
    return (Binding(event_kind, str(entry.site_id), source), None)


def attach_predecessor_reference_sites(
    node: Dict[str, Any],
    by_id: Dict[str, Dict[str, Any]],
    runtime_map: Dict[str, Binding],
    site_map: List[SiteMapEntry],
) -> Dict[str, Any]:
    if node.get("_source_inference_direction") != "predecessor":
        return node
    successor_ids = node.get("_source_inference_successors")
    if not isinstance(successor_ids, list) or not successor_ids:
        return node
    site_by_id = site_entries_by_id(site_map)
    reference_ids = []  # type: List[str]
    for successor_id in successor_ids:
        successor = by_id.get(str(successor_id))
        if not successor:
            continue
        binding, _ = resolve_binding(successor, runtime_map, site_map)
        if binding is None or not binding.site_id.isdigit():
            continue
        if int(binding.site_id) <= 0:
            continue
        if binding.site_id in site_by_id and binding.site_id not in reference_ids:
            reference_ids.append(binding.site_id)
    if not reference_ids:
        return node
    out = dict(node)
    out["_source_inference_reference_site_ids"] = reference_ids
    return out


def path_matches(site_file: str, graph_file: str) -> bool:
    if not site_file or not graph_file:
        return False
    site = site_file.replace("\\", "/")
    graph = graph_file.replace("\\", "/")
    return site == graph or site.endswith("/" + graph) or graph.endswith("/" + site)


def function_matches(site_function: str, graph_function: Optional[str]) -> bool:
    if not graph_function:
        return True
    if not site_function:
        return True
    site = site_function.strip()
    graph = graph_function.strip()
    if not graph:
        return True
    if site == graph:
        return True
    return site.endswith("_" + graph) or graph.endswith("_" + site)


def resolve_from_site_map(
    node: Dict[str, Any], site_map: List[SiteMapEntry], preferred_kinds: Iterable[str]
) -> Tuple[Optional[Binding], Optional[str]]:
    if not site_map:
        return (None, "no_site_map")
    source_locations = node_source_locations(node)
    if not source_locations:
        return (None, "no_source_location")

    def context_matches(
        entry: SiteMapEntry,
        *,
        graph_file: str,
        function: Optional[str],
    ) -> bool:
        if not function_matches(entry.function, function):
            return False
        return path_matches(entry.file, graph_file)

    def line_matches(
        entry: SiteMapEntry,
        *,
        graph_file: str,
        line: int,
        function: Optional[str],
    ) -> bool:
        if entry.line != line:
            return False
        return context_matches(entry, graph_file=graph_file, function=function)

    preferred = tuple(preferred_kinds)
    candidate_kinds = preferred or tuple(sorted({entry.kind for entry in site_map}))
    source_direction = str(node.get("_source_inference_direction") or "")
    source_contexts = []  # type: List[Tuple[str, int, Optional[int], Optional[str]]]
    if source_direction == "predecessor":
        site_by_id = site_entries_by_id(site_map)
        reference_ids = node.get("_source_inference_reference_site_ids")
        if isinstance(reference_ids, list):
            for site_id in reference_ids:
                entry = site_by_id.get(str(site_id))
                if entry is None:
                    continue
                source_contexts.append(
                    (entry.file, entry.line, entry.column, entry.function)
                )
    if not source_contexts:
        for source_location in source_locations:
            graph_file, line, column, function = parse_source_location(source_location)
            if graph_file and line:
                source_contexts.append((graph_file, line, column, function))

    saw_location_match = False
    ambiguous = None  # type: Optional[str]
    for graph_file, line, column, function in source_contexts:
        for kind_filter in candidate_kinds:
            if source_direction == "predecessor":
                window_value = node.get("_source_inference_window")
                try:
                    window = int(window_value)
                except (TypeError, ValueError):
                    window = 0
                if window <= 0:
                    window = column if column is not None and column > 0 else DEFAULT_INFERRED_SOURCE_WINDOW
                predecessor_candidates = [
                    entry
                    for entry in site_map
                    if entry.kind == kind_filter
                    and context_matches(
                        entry, graph_file=graph_file, function=function
                    )
                    and entry.line < line
                    and line - entry.line <= window
                ]
                if not predecessor_candidates:
                    continue
                saw_location_match = True
                nearest = min(line - entry.line for entry in predecessor_candidates)
                nearest_candidates = [
                    entry
                    for entry in predecessor_candidates
                    if line - entry.line == nearest
                ]
                unique_nearest = {(m.kind, m.site_id) for m in nearest_candidates}
                if len(unique_nearest) == 1:
                    kind, site_id = next(iter(unique_nearest))
                    matched = next(
                        m
                        for m in nearest_candidates
                        if m.kind == kind and m.site_id == site_id
                    )
                    return binding_from_site_entry(matched, "site-map-predecessor")
                if len(unique_nearest) > 1:
                    matched = line_cluster_candidate(nearest_candidates)
                    if matched is not None:
                        return binding_from_site_entry(
                            matched, "site-map-predecessor-cluster"
                        )
                    ambiguous = f"site_map_ambiguous:{kind_filter}:predecessor:{len(unique_nearest)}"
                continue

            line_candidates = [
                entry
                for entry in site_map
                if entry.kind == kind_filter
                and line_matches(
                    entry, graph_file=graph_file, line=line, function=function
                )
            ]
            if not line_candidates:
                if column is None or column <= 0:
                    continue
                window_candidates = [
                    entry
                    for entry in site_map
                    if entry.kind == kind_filter
                    and abs(entry.line - line) <= column
                    and line_matches(
                        entry,
                        graph_file=graph_file,
                        line=entry.line,
                        function=function,
                    )
                ]
                if not window_candidates:
                    continue
                saw_location_match = True
                nearest = min(abs(entry.line - line) for entry in window_candidates)
                nearest_candidates = [
                    entry
                    for entry in window_candidates
                    if abs(entry.line - line) == nearest
                ]
                unique_nearest = {(m.kind, m.site_id) for m in nearest_candidates}
                if len(unique_nearest) == 1:
                    kind, site_id = next(iter(unique_nearest))
                    matched = next(
                        m
                        for m in nearest_candidates
                        if m.kind == kind and m.site_id == site_id
                    )
                    return binding_from_site_entry(matched, "site-map-window")
                if len(unique_nearest) > 1:
                    matched = line_cluster_candidate(nearest_candidates)
                    if matched is not None:
                        return binding_from_site_entry(
                            matched, "site-map-window-cluster"
                        )
                    ambiguous = f"site_map_ambiguous:{kind_filter}:window:{len(unique_nearest)}"
                continue
            saw_location_match = True

            if column is not None:
                exact_column = [
                    entry
                    for entry in line_candidates
                    if entry.column and entry.column == column
                ]
                unique_exact = {(m.kind, m.site_id) for m in exact_column}
                if len(unique_exact) == 1:
                    kind, site_id = next(iter(unique_exact))
                    matched = next(
                        m for m in exact_column if m.kind == kind and m.site_id == site_id
                    )
                    return binding_from_site_entry(matched, "site-map")
                if len(unique_exact) > 1:
                    matched = line_cluster_candidate(exact_column)
                    if matched is not None:
                        return binding_from_site_entry(
                            matched, "site-map-column-cluster"
                        )
                    ambiguous = f"site_map_ambiguous:{kind_filter}:column:{len(unique_exact)}"
                    continue

            unique_line = {(m.kind, m.site_id) for m in line_candidates}
            if len(unique_line) == 1:
                kind, site_id = next(iter(unique_line))
                matched = next(
                    m for m in line_candidates if m.kind == kind and m.site_id == site_id
                )
                return binding_from_site_entry(matched, "site-map")
            if len(unique_line) > 1:
                matched = line_cluster_candidate(line_candidates)
                if matched is not None:
                    return binding_from_site_entry(matched, "site-map-line-cluster")
                ambiguous = f"site_map_ambiguous:{kind_filter}:line:{len(unique_line)}"
                continue
    if ambiguous:
        return (None, ambiguous)
    if source_direction == "predecessor":
        return (None, "site_map_no_predecessor")
    if not saw_location_match:
        return (None, "site_map_no_match")
    return (None, "site_map_preferred_kind_no_match")


def site_map_event_kind(entry: SiteMapEntry) -> Optional[str]:
    if entry.kind == "binary" and entry.opcode.lower() in DIV_OPCODES:
        return str(EVENT_KIND["div"])
    return parse_event_kind(entry.kind)


def resolve_binding(
    node: Dict[str, Any],
    runtime_map: Dict[str, Binding],
    site_map: List[SiteMapEntry],
) -> Tuple[Optional[Binding], Optional[str]]:
    source_locations = node_source_locations(node)
    source_location = node.get("source_location")
    require_concrete_site = node_requires_concrete_site(node)
    invalid_runtime_binding = None  # type: Optional[str]
    keys = [
        node.get("id"),
        node.get("runtime_event_id"),
        node.get("label"),
        source_location,
        f"source:{source_location}" if source_location else None,
    ]
    for loc in source_locations:
        keys.extend([loc, f"source:{loc}"])
    for key in keys:
        if key is not None and str(key) in runtime_map:
            binding = runtime_map[str(key)]
            reason = unsafe_binding_reason(
                binding, require_concrete_site=require_concrete_site
            )
            if reason is not None:
                invalid_runtime_binding = reason
                continue
            return (binding, None)
    runtime_event_id = node.get("runtime_event_id")
    unmapped_runtime_event = None
    if runtime_event_id:
        binding = parse_binding(runtime_event_id, source="runtime_event_id")
        if binding is not None:
            reason = unsafe_binding_reason(
                binding, require_concrete_site=require_concrete_site
            )
            if reason is None:
                return (binding, None)
            invalid_runtime_binding = reason
        unmapped_runtime_event = f"unmapped_runtime_event_id:{runtime_event_id}"
    preferred = SITE_KIND_PREFERENCE.get(str(node.get("type")), ())
    binding, reason = resolve_from_site_map(node, site_map, preferred)
    if binding is not None:
        unsafe_reason = unsafe_binding_reason(
            binding, require_concrete_site=require_concrete_site
        )
        if unsafe_reason is not None:
            return (None, unsafe_reason)
        return (binding, None)
    if invalid_runtime_binding is not None:
        return (None, invalid_runtime_binding)
    if unmapped_runtime_event and reason in {"no_site_map", "site_map_no_match"}:
        return (None, unmapped_runtime_event)
    return (None, reason)


def graph_atoms(graph: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [n for n in graph.get("nodes", []) if n.get("type") == "tc_atom"]


def first_atom_id(graph: Dict[str, Any], *categories: str) -> int:
    atoms = graph_atoms(graph)
    if categories:
        wanted = set(categories)
        for atom in atoms:
            if atom.get("category") in wanted:
                return atom_numeric_id(atom.get("id"))
    if atoms:
        return atom_numeric_id(atoms[0].get("id"))
    return 1


def graph_has_atom_category(graph: Dict[str, Any], *categories: str) -> bool:
    wanted = set(categories)
    return any(atom.get("category") in wanted for atom in graph_atoms(graph))


def binding_supports_distance(binding: Binding) -> bool:
    if binding.source == "site-map":
        return True
    if binding.source.startswith("site-map-"):
        return False
    return True


def phase_order(graph: Dict[str, Any], phases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    by_id = {str(n.get("id")): n for n in phases}
    incoming = {node_id: 0 for node_id in by_id}  # type: Dict[str, int]
    outgoing = {node_id: [] for node_id in by_id}  # type: Dict[str, List[str]]
    for edge in graph.get("edges", []):
        if edge.get("type") != "order_constraint":
            continue
        if edge.get("order") not in (None, "lifecycle_prefix", "sequence"):
            continue
        src = str(edge.get("src"))
        dst = str(edge.get("dst"))
        if src in by_id and dst in by_id:
            outgoing[src].append(dst)
            incoming[dst] += 1
    if not any(outgoing.values()):
        return phases
    ready = [node_id for node_id, degree in incoming.items() if degree == 0]
    ordered = []  # type: List[Dict[str, Any]]
    while ready:
        node_id = ready.pop(0)
        ordered.append(by_id[node_id])
        for dst in outgoing[node_id]:
            incoming[dst] -= 1
            if incoming[dst] == 0:
                ready.append(dst)
    return ordered if len(ordered) == len(phases) else phases


def spec_comment(text: str) -> str:
    return "# " + text.replace("\n", " ")


def compile_graph(
    path: Path,
    runtime_map: Dict[str, Binding],
    site_map: List[SiteMapEntry],
    *,
    include_comments: bool,
    source_roots: Optional[List[Path]] = None,
) -> Tuple[List[str], Dict[str, Any]]:
    source_roots = source_roots or []
    graph = apply_source_relocations(json.loads(path.read_text()), site_map, source_roots)
    target_id = str(graph.get("target_id") or path.stem)
    nodes = graph.get("nodes", [])
    graph_node_by_id = nodes_by_id(graph)
    lines = []  # type: List[str]
    skipped = []  # type: List[Dict[str, str]]
    binding_details = []  # type: List[Dict[str, Any]]
    progress_site_ids = []  # type: List[int]
    rules = 0
    progress_rules = 0
    range_rules_count = 0

    def remember_progress_site(binding: Binding) -> None:
        if not binding.site_id.isdigit():
            return
        site_id = int(binding.site_id)
        if site_id <= 0 or site_id in progress_site_ids:
            return
        progress_site_ids.append(site_id)

    def emit(line: str, comment: str, *, progress: bool) -> None:
        nonlocal rules, progress_rules, range_rules_count
        if include_comments:
            lines.append(spec_comment(comment))
        lines.append(line)
        rules += 1
        if progress:
            progress_rules += 1
        else:
            range_rules_count += 1

    if include_comments:
        lines.append(spec_comment(f"FORMTRIG_LIFT_SPEC generated from {path} target={target_id}"))

    phases = [n for n in nodes if n.get("type") == "lifecycle_phase"]
    if phases:
        atom_id = first_atom_id(graph, "compound-sequence-lifecycle")
        context_hash = fnv1a64(f"{target_id}:lifecycle_prefix")
        blocked = False
        for idx, phase in enumerate(phase_order(graph, phases), 1):
            if not node_binding_required(phase):
                skipped.append(
                    {
                        "node": str(phase.get("id")),
                        "type": str(phase.get("type")),
                        "reason": "binding_not_required",
                    }
                )
                continue
            binding, reason = resolve_binding(phase, runtime_map, site_map)
            if binding is None:
                skipped.append(
                    {
                        "node": str(phase.get("id")),
                        "type": str(phase.get("type")),
                        "reason": reason or "unmapped_phase",
                    }
                )
                blocked = True
                continue
            if blocked:
                skipped.append(
                    {
                        "node": str(phase.get("id")),
                        "type": str(phase.get("type")),
                        "reason": "missing_prior_phase_binding",
                    }
                )
                continue
            confidence = confidence_value(phase)
            line = (
                f"phase {binding.event_kind} {binding.site_id} "
                f"{COMPONENT['lifecycle_prefix']} {atom_id} 10 {idx} "
                f"{confidence:.6g} {context_hash}"
            )
            emit(
                line,
                f"phase node={phase.get('id')} binding={binding.source}",
                progress=True,
            )
            remember_progress_site(binding)
            binding_details.append(
                {
                    "node": str(phase.get("id")),
                    "type": str(phase.get("type")),
                    "role": node_binding_role(phase, binding),
                    "binding_source": binding.source,
                    "event_kind": binding.event_kind,
                    "site_id": binding.site_id,
                    "distance_binding_supported": False,
                    "emitted_metrics": ["lifecycle_prefix"],
                }
            )

    for node in nodes:
        node_type = str(node.get("type"))
        component_kind = NODE_KIND_COMPONENT.get(node_type)
        if component_kind is None:
            continue
        if not node_binding_required(node):
            skipped.append(
                {
                    "node": str(node.get("id")),
                    "type": node_type,
                    "reason": "binding_not_required",
                }
            )
            continue
        binding_node = binding_node_for_graph(node, graph, graph_node_by_id)
        binding_node = attach_predecessor_reference_sites(
            binding_node, graph_node_by_id, runtime_map, site_map
        )
        binding, reason = resolve_binding(binding_node, runtime_map, site_map)
        if binding is None:
            skipped.append(
                {
                    "node": str(node.get("id")),
                    "type": node_type,
                    "reason": reason or "unmapped_component",
                }
            )
            continue
        if node_type in ("producer_context", "use_context"):
            atom_id = first_atom_id(
                graph, "binary-state-null", "compound-sequence-lifecycle"
            )
        else:
            atom_id = first_atom_id(graph)
        role = node_binding_role(node, binding)
        default_component_kind = ROLE_COMPONENT.get(role, component_kind)
        priority = parse_priority_value(
            first_attr(node, binding, ("priority",)),
            ROLE_PRIORITY.get(role, NODE_KIND_PRIORITY[node_type]),
        )
        confidence = confidence_value(node)
        source_id = fnv1a64(f"{target_id}:{node.get('id')}:source")
        context_hash = fnv1a64(f"{target_id}:{atom_id}:{default_component_kind}")
        emitted_metrics = []  # type: List[str]
        distance_supported = binding_supports_distance(binding)

        inference = binding_node.get("_source_inference", "")
        detail = f"{node_type} node={node.get('id')} binding={binding.source}"
        if inference:
            detail += f" source_inference={inference}"
        relocation = binding_node.get("_source_relocation", "")
        if relocation:
            detail += f" source_relocation={relocation}"

        def emit_component_spec(spec: Dict[str, Any], detail_suffix: str = "") -> None:
            line = (
                f"component {binding.event_kind} {binding.site_id} "
                f"{spec['component_kind']} {atom_id} {spec['priority']} "
                f"{spec['direction']} {spec['value_mode']} {spec_number(spec['value'])} "
                f"{spec['confidence']:.6g} {spec['source_id']} {spec['context_hash']}"
            )
            emit(
                line,
                f"{detail} role={role} metric={spec['metric']}{detail_suffix}",
                progress=True,
            )
            remember_progress_site(binding)
            emitted_metrics.append(str(spec["metric"]))

        explicit_specs = explicit_component_specs(
            node,
            binding,
            default_component_kind=default_component_kind,
            default_priority=priority,
            default_confidence=confidence,
            default_source_id=source_id,
            default_context_hash=context_hash,
        )
        if explicit_specs:
            for spec in explicit_specs:
                emit_component_spec(spec, "")
        else:
            if (
                node_type == "guard_context"
                and binding.event_kind == str(EVENT_KIND["cmp"])
                and distance_supported
                and graph_has_atom_category(graph, "numeric-margin")
            ):
                distance_source_id = fnv1a64(f"{target_id}:{node.get('id')}:distance")
                distance_context_hash = fnv1a64(
                    f"{target_id}:{atom_id}:{COMPONENT['boundary_margin']}"
                )
                emit_component_spec(
                    {
                        "component_kind": COMPONENT["boundary_margin"],
                        "priority": priority,
                        "direction": "lower",
                        "value_mode": "distance",
                        "value": 0.0,
                        "confidence": confidence,
                        "source_id": distance_source_id,
                        "context_hash": distance_context_hash,
                        "metric": "boundary_margin_distance",
                    },
                    "",
                )
            emit_component_spec(
                {
                    "component_kind": default_component_kind,
                    "priority": priority,
                    "direction": "higher",
                    "value_mode": "hit",
                    "value": 1.0,
                    "confidence": confidence,
                    "source_id": source_id,
                    "context_hash": context_hash,
                    "metric": "hit",
                },
                "",
            )
        binding_details.append(
            {
                "node": str(node.get("id")),
                "type": node_type,
                "role": role,
                "binding_source": binding.source,
                "event_kind": binding.event_kind,
                "site_id": binding.site_id,
                "atom_id": atom_id,
                "distance_binding_supported": distance_supported,
                "emitted_metrics": emitted_metrics,
            }
        )

    range_rules = {}  # type: Dict[Tuple[str, str, int, int], Tuple[float, str]]
    for node in nodes:
        if node.get("type") != "candidate_input_influence_range":
            continue
        try:
            start = int(node.get("start"))
            length = int(node.get("length", node.get("len")))
        except (TypeError, ValueError):
            skipped.append(
                {
                    "node": str(node.get("id")),
                    "type": "candidate_input_influence_range",
                    "reason": "invalid_range_bounds",
                }
            )
            continue
        if start < 0 or length <= 0:
            skipped.append(
                {
                    "node": str(node.get("id")),
                    "type": "candidate_input_influence_range",
                    "reason": "invalid_range_bounds",
                }
            )
            continue

        binding, reason = resolve_binding(node, runtime_map, site_map)
        if binding is None:
            binding = Binding("*", "*", f"static_range:{reason or 'unmapped_range'}")

        key = (binding.event_kind, binding.site_id, start, length)
        influence = confidence_value(node)
        previous = range_rules.get(key)
        if previous is None or influence > previous[0]:
            range_rules[key] = (influence, str(node.get("id")))

    def range_sort_key(item: Tuple[Tuple[str, str, int, int], Tuple[float, str]]) -> Tuple[int, int, int]:
        _, site_id, start, length = item[0]
        site_sort = -1 if site_id == "*" else int(site_id)
        return (site_sort, start, length)

    for (event_kind, site_id, start, length), (influence, node_id) in sorted(
        range_rules.items(), key=range_sort_key
    ):
        emit(
            f"range {event_kind} {site_id} {start} {length} {influence:.6g}",
            f"candidate_input_influence_range node={node_id}",
            progress=False,
        )

    if include_comments:
        for item in skipped:
            lines.append(
                spec_comment(
                    f"skipped node={item['node']} type={item['type']} reason={item['reason']}"
                )
            )

    report = {
        "target_id": target_id,
        "graph": str(path),
        "rules": rules,
        "progress_rules": progress_rules,
        "range_rules": range_rules_count,
        "progress_site_ids": progress_site_ids,
        "binding_details": binding_details,
        "skipped": skipped,
    }
    return lines, report


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compile trigger-progress graph JSON into FORMTRIG_LIFT_SPEC"
    )
    parser.add_argument(
        "--trigger-graph",
        action="append",
        required=True,
        type=Path,
        help="Trigger-progress graph JSON. May be passed multiple times.",
    )
    parser.add_argument(
        "--runtime-map",
        type=Path,
        help="External JSON binding from graph runtime_event_id/node id to runtime event/site.",
    )
    parser.add_argument(
        "--site-map",
        type=Path,
        help="FORMTRIG_SITE_MAP output from the LLVM pass.",
    )
    parser.add_argument(
        "--source-root",
        action="append",
        default=[],
        type=Path,
        help=(
            "External source tree root used to relocate stale/amalgamated "
            "TCIR source locations by expression label."
        ),
    )
    parser.add_argument("-o", "--output", type=Path, help="Write spec to this path.")
    parser.add_argument(
        "--report-json", type=Path, help="Write structured compile report."
    )
    parser.add_argument(
        "--no-comments",
        action="store_true",
        help="Emit only runtime spec lines, without skipped-node comments.",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)
    runtime_map = load_runtime_map(args.runtime_map)
    site_map = parse_site_map(args.site_map)

    all_lines = []  # type: List[str]
    reports = []  # type: List[Dict[str, Any]]
    for graph_path in args.trigger_graph:
        lines, report = compile_graph(
            graph_path,
            runtime_map,
            site_map,
            include_comments=not args.no_comments,
            source_roots=args.source_root,
        )
        if all_lines and not args.no_comments:
            all_lines.append("")
        all_lines.extend(lines)
        reports.append(report)

    text = "\n".join(all_lines) + ("\n" if all_lines else "")
    if args.output:
        args.output.write_text(text)
    else:
        sys.stdout.write(text)

    if args.report_json:
        args.report_json.write_text(
            json.dumps({"graphs": reports}, indent=2, sort_keys=True) + "\n"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
