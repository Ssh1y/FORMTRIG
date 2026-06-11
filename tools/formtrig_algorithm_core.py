#!/usr/bin/env python3
"""FORMTRIG v3 algorithm core.

The module is intentionally standalone and data-oriented.  It can be used by
offline post-reach harnesses and by end-to-end fuzzing glue without importing
Magma-specific runner code.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import shlex
import subprocess
import tempfile
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable


TC_CATEGORIES = {
    "numeric-margin",
    "equality/magic",
    "binary-state-null",
    "compound-sequence-lifecycle",
    "generic",
}

PROGRESS_REASONS = {
    "initial_frontier_seed",
    "triggered",
    "native-distance improvement",
    "lifted-feature improvement",
    "root-aligned state transition",
    "lifecycle-prefix improvement",
    "influence-confidence improvement",
}

REJECTION_REASONS = {
    "not_reached",
    "not_replay_stable",
    "not_root_or_event_aligned",
    "coverage_only",
    "regressed_higher_priority_atom",
    "no_tc_rooted_dominance",
    "insufficient_object_identity",
    "blocked_by_guard",
    "dominated_by_existing_frontier",
}

INF = 1.0e300
NATIVE_DT_STATUSES = {"actionable", "degenerated", "unknown"}
ATOM_OBSERVATION_STATUSES = {
    "NOT_OBSERVED",
    "BLOCKED_BY_GUARD",
    "OBSERVED_FALSE",
    "OBSERVED_TRUE",
    "UNKNOWN_UNSTABLE",
}
TCIR_GROUP_TYPES = {"ALL_OF", "ANY_OF", "NOT", "GUARD", "SEQUENCE", "SAME_OBJECT", "OBSERVED_AT"}
MIN_RNT_SAMPLES = 10
MIN_MUTATION_EDGES = 32
DEFAULT_SIGNAL_HEALTH_THRESHOLDS: dict[str, float | int] = {
    "N_min_RNT": MIN_RNT_SAMPLES,
    "E_min_edges": MIN_MUTATION_EDGES,
    "entropy_min": 0.25,
    "bucket_count_min": 2,
    "most_common_bucket_ratio_max": 0.95,
    "dt_delta_rate_min": 0.05,
    "dt_improvement_rate_min": 0.01,
    "root_observability_min": 0.5,
    "dt_root_alignment_min": 0.5,
    "mutation_reach_stability_min": 0.8,
    "object_identity_confidence_min": 0.5,
    "max_alt_branch_frontier_size": 2,
}


@dataclass
class TCIRNode:
    node_id: str
    node_type: str
    label: str
    attrs: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TCIREdge:
    src: str
    dst: str
    edge_type: str
    attrs: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TCGroup:
    group_id: str
    group_type: str
    children: list[str]
    parent_id: str = ""
    expression: str = ""
    branch_quota: int = 2

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TCIR:
    target_id: str
    expression: str
    root_group_id: str
    atoms: list["TCAtom"]
    groups: list[TCGroup]
    nodes: list[TCIRNode]
    edges: list[TCIREdge]
    source_locations: list[str]
    schema_version: str = "formtrig-tcir-v3"

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "expression": self.expression,
            "root_group_id": self.root_group_id,
            "atoms": [atom.to_dict() for atom in self.atoms],
            "groups": [group.to_dict() for group in self.groups],
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
            "source_locations": self.source_locations,
            "schema_version": self.schema_version,
        }


@dataclass
class AtomObservation:
    atom_id: str
    status: str
    observed: bool
    blocked_by_guard: bool
    evaluated_true: bool
    evaluated_false: bool
    root_key: str
    root_value: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MutationEdge:
    parent_seed_id: str
    child_seed_id: str
    parent_reached: bool
    child_reached: bool
    parent_triggered: bool
    child_triggered: bool
    parent_dt: float | None
    child_dt: float | None
    parent_root_signature: str
    child_root_signature: str
    parent_lifecycle_prefix: int
    child_lifecycle_prefix: int
    source: str = "metadata_parent_child"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GroupProgressVector:
    group_id: str
    group_type: str
    score: float
    satisfied: bool
    selected_branch: str
    branch_scores: dict[str, float]
    regressions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ComparableFrontierKey:
    target_context_hash: str
    selected_branch: str
    object_identity_bucket: str
    guard_context: str = "none"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FullProgressVector:
    target_id: str
    seed_id: str
    reached: bool
    triggered: bool
    replay_stable: bool
    root_or_event_aligned: bool
    target_context_hash: str
    atom_vectors: dict[str, dict[str, Any]]
    atom_observations: dict[str, dict[str, Any]]
    group_progress: dict[str, dict[str, Any]]
    selected_branch: str
    branch_scores: dict[str, float]
    object_identity_confidence: float
    next_event_reachability: float
    phase_novelty: float
    lifecycle_prefix: int
    guard_status: str
    reach_stability: float
    coverage_hash: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SeedProgressRecord:
    record: ReplayRecord
    full_vector: FullProgressVector
    comparable_key: ComparableFrontierKey
    non_dominated_rank: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "record": self.record.to_dict(),
            "full_vector": self.full_vector.to_dict(),
            "comparable_key": self.comparable_key.to_dict(),
            "non_dominated_rank": self.non_dominated_rank,
        }


@dataclass
class TCAtom:
    atom_id: str
    expression: str
    category: str
    source_location: str
    root_variables: list[str]
    operators: list[str]
    confidence: str
    reason: str
    secondary_categories: list[str] = field(default_factory=list)
    composition: str = "all_of"
    group_id: str = "g1"
    source_locations: list[str] = field(default_factory=list)
    root_events: list[str] = field(default_factory=list)
    observation_status: str = "NOT_OBSERVED"
    guarded_by: list[str] = field(default_factory=list)
    sequence_edges: list[str] = field(default_factory=list)
    object_identity_edges: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["secondary_tags"] = list(self.secondary_categories)
        out["composition_group"] = self.group_id
        return out


@dataclass
class ReplayRecord:
    target_id: str
    seed_id: str
    parent_seed_id: str
    content_sha256: str
    input_size: int
    reached_R: bool
    triggered_T: bool
    reached_count: int
    triggered_count: int
    time_s: float
    coverage_hash: str
    native_DT: float | None
    dt_bucket: int | None
    tc_root_state: str
    replay_hash: str
    replay_status: str
    metadata_status: str
    source_seedbank: str
    source_manifest: str
    source_seed: str
    producer: str
    raw: dict[str, str] = field(default_factory=dict)

    @property
    def replay_stable(self) -> bool:
        status = f"{self.replay_status} {self.metadata_status}".lower()
        return (
            self.reached_R
            and not self.triggered_T
            and "timeout" not in status
            and "crash" not in status
            and ("kept_rnt" in status or "verified_rnt" in status or "rnt" in status)
        )

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["replay_stable"] = self.replay_stable
        return out


@dataclass
class SignalHealth:
    target_id: str
    atom_id: str
    category: str
    sample_count: int
    reached_count: int
    triggered_count: int
    dt_entropy: float
    dt_bucket_count: int
    most_common_bucket_ratio: float
    reach_preserving_dt_delta_rate: float
    reach_preserving_dt_improvement_rate: float
    raw_dt_delta_rate: float
    bucket_dt_delta_rate: float
    raw_dt_improve_rate: float
    bucket_dt_improve_rate: float
    mutation_sensitivity: float
    improvement_rate: float
    root_alignment: float
    reach_stability: float
    root_observability: float
    dt_root_alignment: float | None
    dt_delta_rate: float
    dt_improve_rate: float
    mutation_reach_stability: float
    native_status: str
    sample_size_status: str
    rnt_count: int
    mutation_edge_count: int
    discriminative: bool
    sensitive: bool
    improving: bool
    root_aligned: bool
    reach_stable: bool
    actionable_native_dt: bool
    lift_required: bool
    evidence_quality: str
    reasons: list[str]
    failed_checks: list[str] = field(default_factory=list)
    alignment_reason: str = ""
    thresholds: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["sample_size"] = self.rnt_count
        out["dt_delta_rate"] = self.raw_dt_delta_rate
        out["dt_improvement_rate"] = self.dt_improve_rate
        out["failed_checks"] = list(self.failed_checks or self.reasons)
        return out


@dataclass
class AtomPlan:
    target_id: str
    atom_id: str
    category: str
    expression: str
    use_native_dt: bool
    use_lifted_features: bool
    feature_extractors: list[str]
    mutator_operators: list[str]
    priority_components: list[str]
    actionability: dict[str, Any]
    plan_reason: str
    planning_phase: str = "final"
    graph_features: list[dict[str, Any]] = field(default_factory=list)
    graph_node_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TriggerProgressGraph:
    target_id: str
    schema_version: str
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]
    repair_hooks: list[dict[str, Any]]
    confidence_summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProgressVector:
    target_id: str
    seed_id: str
    atom_id: str
    category: str
    reached: bool
    triggered: bool
    native_dt: float | None
    native_bucket: int | None
    root_state: str
    root_signature: str
    lifecycle_prefix: int
    influence_confidence: float
    coverage_hash: str
    replay_stable: bool
    root_or_event_aligned: bool
    observation_status: str = "NOT_OBSERVED"
    atom_score: float = 0.0
    object_identity_confidence: float = 0.0
    next_event_reachability: float = 0.0
    phase_novelty: float = 0.0

    def component(self, name: str) -> float | str | bool | None:
        return {
            "reach": self.reached,
            "trigger": self.triggered,
            "native_bucket": self.native_bucket,
            "native_dt": self.native_dt,
            "root_signature": self.root_signature,
            "root_alignment": self.root_or_event_aligned,
            "lifecycle_prefix": self.lifecycle_prefix,
            "influence_confidence": self.influence_confidence,
            "coverage": self.coverage_hash,
            "observation_status": self.observation_status,
            "atom_score": self.atom_score,
            "object_identity_confidence": self.object_identity_confidence,
            "next_event_reachability": self.next_event_reachability,
            "phase_novelty": self.phase_novelty,
        }.get(name)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProgressDecision:
    seed_id: str
    accepted: bool
    reason: str
    atom_id: str
    improved_components: list[str]
    rejected_components: list[str]
    replay_verifiable: bool
    root_or_event_aligned: bool
    vector: dict[str, Any]
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProgressRecord:
    seed_id: str
    parent_id: str
    input_hash: str
    execution: dict[str, Any]
    atoms: list[dict[str, Any]]
    global_progress: dict[str, Any]
    mutation: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MutationProposal:
    proposal_id: str
    target_id: str
    atom_id: str
    operator_name: str
    seed_id: str
    source_path: str
    mutated_ranges: list[dict[str, Any]]
    executed: bool
    replay_verifiable: bool | None
    changed_target_root_event: bool | None
    kept: bool | None
    keep_reason: str
    output_path: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FeatureExtractorDef:
    name: str
    category: str
    description: str


@dataclass(frozen=True)
class MutationOperatorDef:
    name: str
    category: str
    operator_family: str
    description: str
    required_evidence: tuple[str, ...] = ()
    applicable_atom_types: tuple[str, ...] = ()
    preconditions: tuple[str, ...] = ()
    expected_effect: tuple[str, ...] = ()
    fallback: str = "generic byte perturbation"


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def stable_id(*parts: Any, width: int = 16) -> str:
    text = "\x1f".join(str(part) for part in parts)
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:width]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def load_signal_health_thresholds(path: Path | None = None) -> dict[str, float | int]:
    thresholds = dict(DEFAULT_SIGNAL_HEALTH_THRESHOLDS)
    if path is None or not path.exists():
        return thresholds
    for raw_line in path.read_text().splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = [part.strip() for part in line.split(":", 1)]
        if key not in thresholds:
            continue
        parsed = as_float(value, None)
        if parsed is None:
            continue
        if key.startswith(("N_min", "E_min", "max_alt")):
            thresholds[key] = int(parsed)
        else:
            thresholds[key] = float(parsed)
    return thresholds


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(payload, sort_keys=True) + "\n")


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = []
        for row in rows:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def as_int(value: Any, default: int = 0) -> int:
    try:
        if value is None or value == "":
            return default
        return int(float(str(value)))
    except (TypeError, ValueError):
        return default


def as_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        out = float(str(value))
        if math.isnan(out) or math.isinf(out):
            return default
        return out
    except (TypeError, ValueError):
        return default


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "y", "kept_rnt", "triggered"}


def dt_bucket(value: float | None) -> int | None:
    if value is None:
        return None
    if value <= 0:
        return 0
    if value <= 1:
        return 1
    if value <= 2:
        return 2
    if value <= 4:
        return 3
    if value <= 8:
        return 4
    if value <= 16:
        return 5
    if value <= 32:
        return 6
    if value <= 64:
        return 7
    if value <= 128:
        return 8
    if value <= 256:
        return 9
    return 10


def entropy(values: Iterable[Any]) -> float:
    seq = [value for value in values if value is not None]
    if not seq:
        return 0.0
    counts = Counter(seq)
    total = len(seq)
    return -sum((count / total) * math.log2(count / total) for count in counts.values())


def category_from_expression(expression: str, default: str = "numeric-margin") -> str:
    expr = expression.lower()
    expr_without_literals = re.sub(r"'(?:\\.|[^'])*'|\"(?:\\.|[^\"])*\"", " LIT ", expr)
    if re.search(r"\bnull\b|\bnullptr\b|==\s*0\b|!\s*[a-zA-Z_]", expr):
        return "binary-state-null"
    if any(token in expr for token in ["use_after", "free", "release", "delete", "lifecycle", "same_object", "same object", "state &&"]):
        return "compound-sequence-lifecycle"
    if (
        any(token in expr for token in ["strcmp", "memcmp", "magic", "checksum", "hash"])
        or re.search(r"(?:==|!=)\s*(0x[0-9a-f]+|\d+|'[^']*'|\"[^\"]*\"|[a-zA-Z_][a-zA-Z0-9_]*)", expr)
        or re.search(r"(0x[0-9a-f]+|\d+|'[^']*'|\"[^\"]*\"|[a-zA-Z_][a-zA-Z0-9_]*)\s*(?:==|!=)", expr)
    ):
        return "equality/magic"
    if any(op in expr_without_literals for op in [">", "<", ">=", "<=", "+", "-", "*", "/", "%", "sizeof"]):
        return "numeric-margin"
    return default if default in TC_CATEGORIES else "numeric-margin"


def split_top_level(text: str, delimiters: list[str]) -> list[str]:
    text = text.strip()
    if not text:
        return []
    parts: list[str] = []
    depth = 0
    quote: str | None = None
    start = 0
    i = 0
    while i < len(text):
        ch = text[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
            i += 1
            continue
        if ch in {"'", '"'}:
            quote = ch
            i += 1
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif depth == 0:
            matched = next((delim for delim in delimiters if text.startswith(delim, i)), "")
            if matched:
                part = text[start:i].strip()
                if part:
                    parts.append(strip_wrapping_parens(part))
                start = i + len(matched)
                i += len(matched)
                continue
        i += 1
    tail = text[start:].strip()
    if tail:
        parts.append(strip_wrapping_parens(tail))
    return parts


def split_function_args(text: str) -> list[str]:
    return split_top_level(text, [","])


def split_top_level_atoms(expression: str) -> list[str]:
    expression = expression.strip()
    if not expression:
        return []
    parts = split_top_level(expression, ["&&"])
    return parts or [strip_wrapping_parens(expression)]


def split_source_locations(source_location: str) -> list[str]:
    text = (source_location or "unknown").strip()
    if not text or text == "unknown":
        return ["unknown"]
    raw = re.split(r"\s*(?:;|\|)\s*", text)
    out = [part for part in raw if part]
    return out or [text]


def expand_or_atom(part: str) -> tuple[str, list[str]]:
    stripped = strip_wrapping_parens(part)
    match = re.match(r"^(?:MAGMA_OR|FORMTRIG_OR)\s*\((.*)\)$", stripped)
    if match:
        args = split_function_args(match.group(1))
        if len(args) > 1:
            return "any_of", args
    or_parts = split_top_level(stripped, ["||"])
    if len(or_parts) > 1:
        return "any_of", or_parts
    return "all_of", [stripped]


def strip_wrapping_parens(text: str) -> str:
    out = text.strip()
    while out.startswith("(") and out.endswith(")"):
        depth = 0
        balanced = True
        for i, ch in enumerate(out):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0 and i != len(out) - 1:
                    balanced = False
                    break
        if not balanced:
            break
        out = out[1:-1].strip()
    return out


def extract_operators(expression: str) -> list[str]:
    ops: list[str] = []
    for op in ["==", "!=", ">=", "<=", ">", "<", "&&", "||", "&", "|", "+", "-", "*", "/", "%"]:
        if op in expression and op not in ops:
            ops.append(op)
    for name in ["strcmp", "memcmp", "strlen", "sizeof", "free", "malloc"]:
        if re.search(rf"\b{re.escape(name)}\b", expression) and name not in ops:
            ops.append(name)
    return ops


def extract_root_variables(expression: str) -> list[str]:
    stop = {
        "if",
        "return",
        "sizeof",
        "NULL",
        "nullptr",
        "true",
        "false",
        "size_t",
        "int",
        "uint32_t",
        "uint64_t",
        "png_uint_32",
    }
    expression_no_literals = re.sub(r"'(?:\\.|[^'])*'|\"(?:\\.|[^\"])*\"", " ", expression)
    tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]*(?:->[A-Za-z_][A-Za-z0-9_]*)?(?:\.[A-Za-z_][A-Za-z0-9_]*)?", expression_no_literals)
    roots: list[str] = []
    for token in tokens:
        base = token.split("->", 1)[0].split(".", 1)[0]
        if token in stop or base in stop:
            continue
        if token.isupper() and len(token) > 1:
            continue
        if token not in roots:
            roots.append(token)
    return roots[:8]


def extract_root_events(expression: str) -> list[str]:
    events: list[str] = []
    for name in re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(", expression):
        if name in {"sizeof", "MAGMA_OR", "FORMTRIG_OR", "SAME_OBJECT"}:
            continue
        if name not in events:
            events.append(name)
    for token in ["producer", "guard", "use", "free", "release", "create", "open", "close", "alloc"]:
        if re.search(rf"\b{token}\b", expression.lower()) and token not in events:
            events.append(token)
    return events[:8]


def split_sequence_expression(expression: str) -> list[str]:
    stripped = strip_wrapping_parens(expression)
    parts = re.split(r"\s+(?:before|then|followed\s+by|->|=>)\s+", stripped, flags=re.IGNORECASE)
    out = [strip_wrapping_parens(part) for part in parts if part.strip()]
    return out if len(out) > 1 else [stripped]


def infer_group_type(expression: str) -> str:
    text = f" {expression.lower()} "
    # C/C++ pointer member access (ptr->field) is not a lifecycle/sequence edge.
    # Require explicit ordering prose or a spaced arrow for sequence syntax.
    if any(token in text for token in [" before ", " then ", " followed by ", " sequence ", " lifecycle "]) or re.search(r"\s(?:->|=>)\s", expression):
        return "SEQUENCE"
    if " same_object " in text or "same_object(" in text or "same object" in text:
        return "SAME_OBJECT"
    stripped = strip_wrapping_parens(expression)
    if re.match(r"^(?:MAGMA_OR|FORMTRIG_OR)\s*\((.*)\)$", stripped) or len(split_top_level(stripped, ["||"])) > 1:
        return "ANY_OF"
    return "ALL_OF"


def build_tcir(
    expression: str,
    default_category: str,
    source_location: str,
    secondary_categories: list[str] | None = None,
    target_id: str = "",
) -> TCIR:
    """Build a compact TC-IR without expanding disjunctions into DNF."""

    source_locations = split_source_locations(source_location)
    expression = expression.strip() or "<missing TC expression>"
    atoms: list[TCAtom] = []
    groups: list[TCGroup] = []
    nodes: list[TCIRNode] = []
    edges: list[TCIREdge] = []
    atom_index = 0
    group_index = 0

    def add_group(group_type: str, expr: str, parent_id: str = "") -> TCGroup:
        nonlocal group_index
        group_index += 1
        group = TCGroup(
            group_id=f"g{group_index}",
            group_type=group_type,
            children=[],
            parent_id=parent_id,
            expression=strip_wrapping_parens(expr),
        )
        groups.append(group)
        nodes.append(TCIRNode(group.group_id, "group", group.group_type, {"expression": group.expression}))
        if parent_id:
            edges.append(TCIREdge(parent_id, group.group_id, "composition", {"group_type": group_type}))
        return group

    def add_atom(expr: str, group: TCGroup, reason: str) -> TCAtom:
        nonlocal atom_index
        atom_index += 1
        category = category_from_expression(expr, default_category)
        source = source_locations[min(atom_index - 1, len(source_locations) - 1)]
        atom = TCAtom(
            atom_id=f"a{atom_index}",
            expression=strip_wrapping_parens(expr),
            category=category,
            source_location=source,
            root_variables=extract_root_variables(expr),
            root_events=extract_root_events(expr),
            operators=extract_operators(expr),
            confidence="high" if expr and expr != "<missing TC expression>" else "low",
            reason=reason,
            secondary_categories=secondary_categories or [],
            composition=group.group_type.lower(),
            group_id=group.group_id,
            source_locations=source_locations,
        )
        atoms.append(atom)
        group.children.append(atom.atom_id)
        nodes.append(
            TCIRNode(
                atom.atom_id,
                "atom",
                atom.expression,
                {
                    "category": atom.category,
                    "source_location": atom.source_location,
                    "root_variables": atom.root_variables,
                    "root_events": atom.root_events,
                    "operators": atom.operators,
                    "composition": atom.composition,
                    "group_id": atom.group_id,
                },
            )
        )
        edges.append(TCIREdge(group.group_id, atom.atom_id, "contains", {"composition": group.group_type}))
        for root in atom.root_variables or [f"{atom.atom_id}:root"]:
            root_id = f"root:{atom.atom_id}:{stable_id(root)}"
            nodes.append(
                TCIRNode(
                    root_id,
                    "root",
                    root,
                    {
                        "atom_id": atom.atom_id,
                        "source_location": atom.source_location,
                    },
                )
            )
            edges.append(TCIREdge(root_id, atom.atom_id, "defines_atom"))
        return atom

    def parse_expr(expr: str, parent: TCGroup) -> None:
        stripped = strip_wrapping_parens(expr)
        seq_parts = split_sequence_expression(stripped)
        if len(seq_parts) > 1:
            if parent.group_type == "SEQUENCE" and not parent.children:
                group = parent
            else:
                group = add_group("SEQUENCE", stripped, parent.group_id)
                parent.children.append(group.group_id)
            for part in seq_parts:
                parse_expr(part, group)
            return

        same_object_match = re.match(r"^(?:SAME_OBJECT|same_object)\s*\((.*)\)$", stripped)
        if same_object_match:
            if parent.group_type == "SAME_OBJECT" and not parent.children:
                group = parent
            else:
                group = add_group("SAME_OBJECT", stripped, parent.group_id)
                parent.children.append(group.group_id)
            add_atom(stripped, group, "tcir_same_object_predicate")
            return

        match = re.match(r"^(?:MAGMA_OR|FORMTRIG_OR)\s*\((.*)\)$", stripped)
        if match:
            if parent.group_type == "ANY_OF" and not parent.children:
                group = parent
            else:
                group = add_group("ANY_OF", stripped, parent.group_id)
                parent.children.append(group.group_id)
            for arg in split_function_args(match.group(1)):
                parse_expr(arg, group)
            return

        any_parts = split_top_level(stripped, ["||"])
        if len(any_parts) > 1:
            if parent.group_type == "ANY_OF" and not parent.children:
                group = parent
            else:
                group = add_group("ANY_OF", stripped, parent.group_id)
                parent.children.append(group.group_id)
            for part in any_parts:
                parse_expr(part, group)
            return

        all_parts = split_top_level(stripped, ["&&"])
        if len(all_parts) > 1:
            if parent.group_type == "ALL_OF" and not parent.children:
                group = parent
            else:
                group = add_group("ALL_OF", stripped, parent.group_id)
                parent.children.append(group.group_id)
            for part in all_parts:
                parse_expr(part, group)
            return

        if stripped.startswith("!") and len(stripped) > 1:
            group = add_group("NOT", stripped, parent.group_id)
            parent.children.append(group.group_id)
            parse_expr(stripped[1:].strip(), group)
            return

        add_atom(stripped, parent, "tcir_atomic_predicate")

    root_group = add_group(infer_group_type(expression), expression)
    parse_expr(expression, root_group)

    atom_by_id = {atom.atom_id: atom for atom in atoms}
    same_object_specs: list[dict[str, Any]] = []
    for atom in atoms:
        match = re.match(r"^(?:SAME_OBJECT|same_object)\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)$", atom.expression)
        if match:
            same_object_specs.append({"atom_id": atom.atom_id, "object": match.group(1)})

    for group in groups:
        atom_children = [atom_by_id[item] for item in group.children if item in atom_by_id]
        if group.group_type == "ALL_OF" and len(atom_children) > 1:
            for left, right in zip(atom_children, atom_children[1:]):
                edges.append(TCIREdge(left.atom_id, right.atom_id, "order", {"order": "expression_order"}))
            guard_candidates = [atom for atom in atom_children if atom.category == "equality/magic"]
            guarded_candidates = [atom for atom in atom_children if atom.category in {"binary-state-null", "numeric-margin", "compound-sequence-lifecycle"}]
            for guard in guard_candidates[:2]:
                for guarded in guarded_candidates:
                    if guard.atom_id == guarded.atom_id:
                        continue
                    edges.append(
                        TCIREdge(
                            guard.atom_id,
                            guarded.atom_id,
                            "guard",
                            {
                                "confidence": "medium",
                                "reason": "equality_atom_precedes_state_or_margin_atom_in_all_of",
                            },
                        )
                    )
        if group.group_type == "SEQUENCE":
            for left, right in zip(atom_children, atom_children[1:]):
                edges.append(TCIREdge(left.atom_id, right.atom_id, "order", {"order": "sequence"}))
                left.sequence_edges.append(right.atom_id)
        if group.group_type == "SAME_OBJECT":
            for left, right in zip(atom_children, atom_children[1:]):
                events = list(dict.fromkeys((left.root_events or [left.expression]) + (right.root_events or [right.expression])))
                edges.append(
                    TCIREdge(
                        left.atom_id,
                        right.atom_id,
                        "SAME_OBJECT",
                        {"type": "SAME_OBJECT", "events": events, "object": "", "confidence": "required_by_group"},
                    )
                )
                left.object_identity_edges.append(right.atom_id)
                right.object_identity_edges.append(left.atom_id)
    for spec in same_object_specs:
        event_atoms = [
            atom
            for atom in atoms
            if atom.atom_id != spec["atom_id"]
            and atom.root_events
            and any(root == spec["object"] or root.endswith(f"({spec['object']})") for root in atom.root_variables + [atom.expression])
        ]
        if not event_atoms:
            event_atoms = [atom for atom in atoms if atom.atom_id != spec["atom_id"] and atom.root_events]
        event_names = [event for atom in event_atoms for event in atom.root_events]
        for left, right in zip(event_atoms, event_atoms[1:]):
            edges.append(
                TCIREdge(
                    left.atom_id,
                    right.atom_id,
                    "SAME_OBJECT",
                    {
                        "type": "SAME_OBJECT",
                        "events": event_names,
                        "object": spec["object"],
                        "predicate_atom": spec["atom_id"],
                        "confidence": "required_by_same_object_predicate",
                    },
                )
            )
            left.object_identity_edges.append(right.atom_id)
            right.object_identity_edges.append(left.atom_id)
    for edge_item in edges:
        if edge_item.edge_type == "guard" and edge_item.dst in atom_by_id:
            atom_by_id[edge_item.dst].guarded_by.append(edge_item.src)
    return TCIR(
        target_id=target_id,
        expression=expression,
        root_group_id=root_group.group_id,
        atoms=atoms,
        groups=groups,
        nodes=nodes,
        edges=edges,
        source_locations=source_locations,
    )


def BuildTCIR(
    expression: str,
    default_category: str,
    source_location: str,
    secondary_categories: list[str] | None = None,
    target_id: str = "",
) -> TCIR:
    return build_tcir(expression, default_category, source_location, secondary_categories, target_id)


def decompose_tc(
    expression: str,
    default_category: str,
    source_location: str,
    secondary_categories: list[str] | None = None,
) -> list[TCAtom]:
    """Compatibility wrapper returning TCIR atoms."""

    return build_tcir(expression, default_category, source_location, secondary_categories).atoms


def decompose_tc_v2_string_split(
    expression: str,
    default_category: str,
    source_location: str,
    secondary_categories: list[str] | None = None,
) -> list[TCAtom]:
    """Original v2 string-split decomposer retained for debugging."""

    parts = split_top_level_atoms(expression)
    if not parts:
        parts = [expression or "<missing TC expression>"]
    atoms: list[TCAtom] = []
    source_locations = split_source_locations(source_location)
    atom_index = 0
    for part_index, part in enumerate(parts):
        composition, expanded_parts = expand_or_atom(part)
        group_id = f"g{part_index + 1}"
        for expanded in expanded_parts:
            atom_index += 1
            category = category_from_expression(expanded, default_category)
            confidence = "high" if expanded and expanded != "<missing TC expression>" else "low"
            if len(parts) > 1 and composition == "all_of":
                reason = "top_level_conjunction"
            elif composition == "any_of":
                reason = "top_level_disjunction_or_magma_or"
            else:
                reason = "single_atom_or_unparsed_expression"
            source = source_locations[min(atom_index - 1, len(source_locations) - 1)]
            atoms.append(
                TCAtom(
                    atom_id=f"a{atom_index}",
                    expression=expanded,
                    category=category,
                    source_location=source,
                    root_variables=extract_root_variables(expanded),
                    operators=extract_operators(expanded),
                    confidence=confidence,
                    reason=reason,
                    secondary_categories=secondary_categories or [],
                    composition=composition,
                    group_id=group_id,
                    source_locations=source_locations,
                )
            )
    return atoms


def replay_record_from_row(row: dict[str, str]) -> ReplayRecord:
    native = as_float(row.get("native_DT"), None)
    return ReplayRecord(
        target_id=row.get("target_id", ""),
        seed_id=row.get("seed_id", ""),
        parent_seed_id=row.get("parent_seed_id", ""),
        content_sha256=row.get("content_sha256", ""),
        input_size=as_int(row.get("input_size")),
        reached_R=as_bool(row.get("reached_R")),
        triggered_T=as_bool(row.get("triggered_T")),
        reached_count=as_int(row.get("reached_count")),
        triggered_count=as_int(row.get("triggered_count")),
        time_s=as_float(row.get("time_s"), 0.0) or 0.0,
        coverage_hash=row.get("coverage_hash", ""),
        native_DT=native,
        dt_bucket=dt_bucket(native),
        tc_root_state=row.get("tc_root_state", ""),
        replay_hash=row.get("replay_hash", ""),
        replay_status=row.get("replay_status", ""),
        metadata_status=row.get("metadata_status", ""),
        source_seedbank=row.get("source_seedbank", ""),
        source_manifest=row.get("source_manifest", ""),
        source_seed=row.get("source_seed", ""),
        producer=row.get("producer", ""),
        raw=dict(row),
    )


def parse_root_state(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in re.split(r"[;,]", text or ""):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            key, value = part.split("=", 1)
            out[key.strip()] = value.strip()
        else:
            out[part] = "1"
    return out


def root_signature(text: str) -> str:
    parsed = parse_root_state(text)
    filtered = {k: v for k, v in parsed.items() if k.upper() not in {"R", "T"}}
    if not filtered:
        return ""
    return json.dumps(filtered, sort_keys=True, separators=(",", ":"))


def root_alignment_score(records: list[ReplayRecord]) -> float:
    reached = [record for record in records if record.reached_R]
    if not reached:
        return 0.0
    aligned = 0
    for record in reached:
        sig = root_signature(record.tc_root_state)
        event_probe = record.coverage_hash.startswith("gdb_probe:")
        if sig or event_probe:
            aligned += 1
    return aligned / len(reached)


def lifecycle_prefix_score(text: str) -> int:
    parsed = parse_root_state(text)
    explicit = as_int(parsed.get("lifecycle_prefix"), -1)
    if explicit >= 0:
        return explicit
    full = " ".join([text] + [f"{k}={v}" for k, v in parsed.items()]).lower()
    phases = [
        ("producer", ["producer", "alloc", "create", "open", "parse", "init"]),
        ("configured", ["config", "set", "load", "assign"]),
        ("aliased", ["alias", "ref", "copy"]),
        ("released", ["free", "release", "close", "delete", "cleanup"]),
        ("used", ["use", "sink", "deref", "verify", "probe"]),
    ]
    score = 0
    for _, keys in phases:
        matched = False
        for key in keys:
            if key in parsed:
                matched = str(parsed[key]).lower() not in {"0", "false", "no", "none", "null"}
                break
            if re.search(rf"\b{re.escape(key)}\b", full) and f"{key}=0" not in full and f"{key}=false" not in full:
                matched = True
                break
        if matched:
            score += 1
    return score


def is_strict_rnt(record: ReplayRecord) -> bool:
    return record.reached_R and not record.triggered_T


def build_parent_child_edges(records: list[ReplayRecord]) -> list[MutationEdge]:
    by_seed = {record.seed_id: record for record in records}
    edges: list[MutationEdge] = []
    for child in records:
        parent_id = child.parent_seed_id
        if not parent_id or parent_id == "ROOT" or parent_id not in by_seed:
            continue
        parent = by_seed[parent_id]
        edges.append(
            MutationEdge(
                parent_seed_id=parent.seed_id,
                child_seed_id=child.seed_id,
                parent_reached=parent.reached_R,
                child_reached=child.reached_R,
                parent_triggered=parent.triggered_T,
                child_triggered=child.triggered_T,
                parent_dt=parent.native_DT,
                child_dt=child.native_DT,
                parent_root_signature=root_signature(parent.tc_root_state),
                child_root_signature=root_signature(child.tc_root_state),
                parent_lifecycle_prefix=lifecycle_prefix_score(parent.tc_root_state),
                child_lifecycle_prefix=lifecycle_prefix_score(child.tc_root_state),
            )
        )
    return edges


def sample_size_status(rnt_count: int, edge_count: int, n_min: int = MIN_RNT_SAMPLES, e_min: int = MIN_MUTATION_EDGES) -> str:
    missing = []
    if rnt_count < n_min:
        missing.append("rnt")
    if edge_count < e_min:
        missing.append("mutation_edges")
    if not missing:
        return "sufficient"
    return "insufficient_" + "_and_".join(missing)


def edge_dt_changed(edge: MutationEdge) -> bool:
    return edge.parent_dt is not None and edge.child_dt is not None and edge.parent_dt != edge.child_dt


def edge_dt_improved(edge: MutationEdge) -> bool:
    return edge.parent_dt is not None and edge.child_dt is not None and edge.child_dt < edge.parent_dt


def edge_dt_bucket_changed(edge: MutationEdge) -> bool:
    parent_bucket = dt_bucket(edge.parent_dt)
    child_bucket = dt_bucket(edge.child_dt)
    return parent_bucket is not None and child_bucket is not None and parent_bucket != child_bucket


def edge_dt_bucket_improved(edge: MutationEdge) -> bool:
    parent_bucket = dt_bucket(edge.parent_dt)
    child_bucket = dt_bucket(edge.child_dt)
    return parent_bucket is not None and child_bucket is not None and child_bucket < parent_bucket


def edge_root_progress_aligned(edge: MutationEdge) -> bool:
    if edge.child_root_signature and edge.child_root_signature != edge.parent_root_signature:
        return True
    return edge.child_lifecycle_prefix > edge.parent_lifecycle_prefix


def compute_signal_health(
    target_id: str,
    atom: TCAtom,
    records: list[ReplayRecord],
    mutation_edges: list[MutationEdge] | None = None,
    n_min: int = MIN_RNT_SAMPLES,
    e_min: int = MIN_MUTATION_EDGES,
    thresholds: dict[str, Any] | None = None,
) -> SignalHealth:
    threshold_values = dict(DEFAULT_SIGNAL_HEALTH_THRESHOLDS)
    threshold_values["N_min_RNT"] = n_min
    threshold_values["E_min_edges"] = e_min
    if thresholds:
        threshold_values.update(thresholds)
    n_min = int(threshold_values.get("N_min_RNT", n_min))
    e_min = int(threshold_values.get("E_min_edges", e_min))
    total = len(records)
    rnt = [record for record in records if is_strict_rnt(record)]
    triggered_count = sum(1 for record in records if record.triggered_T)
    atom_dt_values = [as_float(record.raw.get(f"native_DT_{atom.atom_id}"), record.native_DT) for record in rnt]
    buckets = [dt_bucket(value) for value in atom_dt_values if dt_bucket(value) is not None]
    bucket_counts = Counter(buckets)
    most_common_ratio = 1.0
    if buckets:
        most_common_ratio = bucket_counts.most_common(1)[0][1] / len(buckets)
    edges = mutation_edges if mutation_edges is not None else build_parent_child_edges(records)
    reach_preserving = [edge for edge in edges if edge.parent_reached and edge.child_reached]
    comparisons = len(reach_preserving)
    raw_dt_changes = sum(1 for edge in reach_preserving if edge_dt_changed(edge))
    raw_dt_improvements = sum(1 for edge in reach_preserving if edge_dt_improved(edge))
    bucket_dt_changes = sum(1 for edge in reach_preserving if edge_dt_bucket_changed(edge))
    bucket_dt_improvements = sum(1 for edge in reach_preserving if edge_dt_bucket_improved(edge))
    raw_delta_rate = raw_dt_changes / comparisons if comparisons else 0.0
    raw_improve_rate = raw_dt_improvements / comparisons if comparisons else 0.0
    bucket_delta_rate = bucket_dt_changes / comparisons if comparisons else 0.0
    bucket_improve_rate = bucket_dt_improvements / comparisons if comparisons else 0.0
    dt_improving_edges = [edge for edge in reach_preserving if edge_dt_improved(edge)]
    aligned_edges = sum(1 for edge in dt_improving_edges if edge_root_progress_aligned(edge))
    dt_root_alignment: float | None = aligned_edges / len(dt_improving_edges) if dt_improving_edges else None
    alignment_reason = "" if dt_improving_edges else "no_dt_improving_edges"
    signal_improving = [
        edge
        for edge in edges
        if edge_dt_improved(edge) or edge_dt_bucket_improved(edge) or edge_root_progress_aligned(edge)
    ]
    mutation_reach_stability = (
        sum(1 for edge in signal_improving if edge.child_reached) / len(signal_improving)
        if signal_improving
        else 0.0
    )
    dt_entropy_value = entropy(buckets)
    discr = (
        dt_entropy_value >= float(threshold_values["entropy_min"])
        and len(bucket_counts) >= int(threshold_values["bucket_count_min"])
        and most_common_ratio <= float(threshold_values["most_common_bucket_ratio_max"])
    )
    sensitive = raw_delta_rate >= float(threshold_values["dt_delta_rate_min"]) or bucket_delta_rate >= float(threshold_values["dt_delta_rate_min"])
    improving = raw_improve_rate >= float(threshold_values["dt_improvement_rate_min"]) or bucket_improve_rate >= float(threshold_values["dt_improvement_rate_min"])
    observations = [atom_observation(record, atom) for record in rnt]
    root_observability = (sum(1 for obs in observations if obs.observed) / len(observations)) if observations else 0.0
    root_observable = root_observability >= float(threshold_values["root_observability_min"])
    root_aligned = dt_root_alignment is not None and dt_root_alignment >= float(threshold_values["dt_root_alignment_min"])
    reach_stability = mutation_reach_stability
    reach_stable = mutation_reach_stability >= float(threshold_values["mutation_reach_stability_min"]) if signal_improving else False
    size_status = sample_size_status(len(rnt), len(edges), n_min, e_min)
    native_status = "unknown"
    if size_status == "sufficient":
        native_status = "actionable" if discr and sensitive and improving and root_observable and root_aligned and reach_stable else "degenerated"
    actionable = native_status == "actionable"
    evidence_quality = "metadata"
    failed_checks: list[str] = []
    if len(rnt) < n_min:
        failed_checks.append("insufficient_rnt_records")
    if len(edges) < e_min:
        failed_checks.append("insufficient_mutation_edges")
    if not discr:
        failed_checks.append("native_DT_not_discriminative")
    if not sensitive:
        failed_checks.append("native_DT_mutation_insensitive_or_unobserved")
    if not improving:
        failed_checks.append("native_DT_low_improvement_rate")
    if not root_observable:
        failed_checks.append("tc_root_not_observable")
    if dt_root_alignment is None:
        failed_checks.append("native_DT_root_alignment_undefined_no_improving_edges")
    elif not root_aligned:
        failed_checks.append("native_DT_not_root_aligned")
    if not reach_stable:
        failed_checks.append("mutation_improvements_not_reach_stable")
    if not rnt:
        evidence_quality = "insufficient"
        failed_checks.append("no_rnt_records")
    reasons = list(failed_checks)
    return SignalHealth(
        target_id=target_id,
        atom_id=atom.atom_id,
        category=atom.category,
        sample_count=total,
        reached_count=sum(1 for record in records if record.reached_R),
        triggered_count=triggered_count,
        dt_entropy=dt_entropy_value,
        dt_bucket_count=len(bucket_counts),
        most_common_bucket_ratio=most_common_ratio,
        reach_preserving_dt_delta_rate=raw_delta_rate,
        reach_preserving_dt_improvement_rate=raw_improve_rate,
        raw_dt_delta_rate=raw_delta_rate,
        bucket_dt_delta_rate=bucket_delta_rate,
        raw_dt_improve_rate=raw_improve_rate,
        bucket_dt_improve_rate=bucket_improve_rate,
        mutation_sensitivity=max(raw_delta_rate, bucket_delta_rate),
        improvement_rate=max(raw_improve_rate, bucket_improve_rate),
        root_alignment=root_observability if dt_root_alignment is None else dt_root_alignment,
        reach_stability=reach_stability,
        root_observability=root_observability,
        dt_root_alignment=dt_root_alignment,
        dt_delta_rate=raw_delta_rate,
        dt_improve_rate=raw_improve_rate,
        mutation_reach_stability=mutation_reach_stability,
        native_status=native_status,
        sample_size_status=size_status,
        rnt_count=len(rnt),
        mutation_edge_count=len(edges),
        discriminative=discr,
        sensitive=sensitive,
        improving=improving,
        root_aligned=root_aligned,
        reach_stable=reach_stable,
        actionable_native_dt=actionable,
        lift_required=native_status == "degenerated",
        evidence_quality=evidence_quality,
        reasons=reasons,
        failed_checks=failed_checks,
        alignment_reason=alignment_reason,
        thresholds=threshold_values,
    )


def registry() -> dict[str, dict[str, list[dict[str, Any]]]]:
    state_flip_mutators = [
        (
            "optional-region deletion",
            "state_flip",
            "Delete optional region likely controlling the state.",
            ("candidate_input_influence_range",),
        ),
        (
            "guard-field perturbation",
            "state_flip",
            "Perturb guard fields controlling producer execution.",
            ("guard_context",),
        ),
        (
            "error-path induction",
            "state_flip",
            "Induce parse/error path changes.",
            ("guard_context", "producer_context"),
        ),
        (
            "initialization-bypass mutation",
            "state_flip",
            "Bypass initialization-like regions.",
            ("producer_context", "use_context"),
        ),
        (
            "reset/cleanup-path mutation",
            "state_flip",
            "Perturb reset or cleanup path selectors.",
            ("producer_context", "lifecycle_phase"),
        ),
    ]
    data = {
        "numeric-margin": {
            "features": [
                ("normalized_margin", "Normalize signed/unsigned numeric distance."),
                ("boundary_crossing", "Detect crossing of lower/upper bounds."),
                ("bitwidth_signedness_aware_margin", "Track width and signedness-sensitive margin."),
            ],
            "mutators": [
                ("boundary write", "numeric_boundary", "Write near-boundary constants to candidate ranges.", ("candidate_input_influence_range",)),
                ("arithmetic perturbation", "numeric_arithmetic", "Apply small arithmetic deltas.", ("candidate_input_influence_range",)),
                ("numeric byte increment", "numeric_arithmetic", "Increment one byte near a numeric root.", ("candidate_input_influence_range",)),
                ("endian variants", "numeric_encoding", "Try little/big-endian scalar encodings.", ("candidate_input_influence_range",)),
            ],
        },
        "equality/magic": {
            "features": [
                ("matched_bytes", "Count matched bytes against visible operands."),
                ("prefix_match", "Track prefix agreement for strings/tokens."),
                ("operand_visibility", "Record whether comparison operands are available."),
                ("dictionary_hit", "Record dictionary/corpus token matches."),
            ],
            "mutators": [
                ("operand replacement", "compare_operand", "Replace candidate ranges with visible operands.", ("root_variable_or_event", "candidate_input_influence_range")),
                ("dictionary insertion", "token_mutation", "Insert dictionary tokens near candidate ranges.", ("candidate_input_influence_range",)),
                ("token replacement", "token_mutation", "Replace nearby token with target token.", ("candidate_input_influence_range",)),
                ("repair hook", "repair", "Run available format repair after token mutation.", ("repair_hook",)),
            ],
        },
        "binary-state-null": {
            "features": [
                ("root_state", "Track desired binary/null root state."),
                ("producer_reached", "Track producer context execution."),
                ("desired_producer_executed", "Track desired producer path."),
                ("opposite_producer_bypassed", "Track bypass of opposite state producer."),
                ("use_reached", "Track target use context."),
            ],
            "mutators": state_flip_mutators,
        },
        "compound-sequence-lifecycle": {
            "features": [
                ("automaton_prefix", "Track longest satisfied lifecycle prefix."),
                ("object_identity", "Track whether events refer to the same object."),
                ("next_event_reachability", "Track reachability of the next required event."),
                ("phase_novelty", "Track meaningful phase changes."),
            ],
            "mutators": [
                ("event insertion", "sequence_edit", "Insert event-like chunks.", ("lifecycle_phase", "candidate_input_influence_range")),
                ("object-identity alignment", "sequence_edit", "Align object identifiers across observed event records.", ("object_identity", "candidate_input_influence_range")),
                ("event deletion", "sequence_edit", "Delete event-like chunks.", ("lifecycle_phase", "candidate_input_influence_range")),
                ("event duplication", "sequence_edit", "Duplicate event-like chunks.", ("lifecycle_phase", "candidate_input_influence_range")),
                ("event reordering", "sequence_edit", "Reorder adjacent event-like chunks.", ("lifecycle_phase", "candidate_input_influence_range")),
                ("phase-preserving mutation", "sequence_edit", "Mutate while preserving current phase prefix.", ("lifecycle_phase",)),
            ],
        },
        "generic": {
            "features": [
                ("root_event_observation", "Track replay-visible root/event state when available."),
                ("signal_actionability", "Measure whether any numeric or lifted signal is actionable."),
                ("reach_stability", "Track whether mutations preserve target reach."),
            ],
            "mutators": [
                ("generic byte perturbation", "generic_local", "Apply bounded byte-level perturbation to candidate ranges.", ("candidate_input_influence_range",)),
                ("generic byte increment", "generic_local", "Increment one byte in a candidate range.", ("candidate_input_influence_range",)),
                ("generic byte decrement", "generic_local", "Decrement one byte in a candidate range.", ("candidate_input_influence_range",)),
                ("generic token insertion", "generic_local", "Insert small constants or corpus tokens.", ("candidate_input_influence_range",)),
                ("generic region deletion", "generic_local", "Delete bounded candidate ranges.", ("candidate_input_influence_range",)),
            ],
        },
    }
    out: dict[str, dict[str, list[dict[str, str]]]] = {}
    for category, items in data.items():
        out[category] = {
            "features": [
                asdict(FeatureExtractorDef(name=name, category=category, description=description))
                for name, description in items["features"]
            ],
            "mutators": [
                asdict(
                    MutationOperatorDef(
                        name=name,
                        category=category,
                        operator_family=family,
                        description=description,
                        required_evidence=tuple(required),
                        applicable_atom_types=(category,),
                        preconditions=operator_preconditions(name, family, tuple(required)),
                        expected_effect=operator_expected_effect(name, family),
                        fallback=operator_fallback(name, family),
                    )
                )
                for name, family, description, required in items["mutators"]
            ],
        }
    return out


def generic_afl_style_mutators() -> list[str]:
    return ["generic byte perturbation", "generic byte increment", "generic byte decrement", "generic token insertion"]


def typed_mutator_names() -> list[str]:
    generic = set(generic_afl_style_mutators())
    names: list[str] = []
    for category, payload in registry().items():
        if category == "generic":
            continue
        for item in payload["mutators"]:
            if item["name"] not in generic and item["name"] not in names:
                names.append(item["name"])
    return names


def operator_preconditions(name: str, family: str, required: tuple[str, ...]) -> tuple[str, ...]:
    base = ["seed_reaches_target_context", "replay_available"]
    if family == "compare_operand":
        base.extend(["operand_visible_or_dictionary_available", "candidate_input_influence_range_available"])
    elif family == "state_flip":
        base.extend(["root_or_producer_state_observed", "candidate_region_or_guard_evidence_available"])
    elif family == "sequence_edit":
        base.extend(["event_or_phase_boundary_observed", "sequence_mutation_preserves_input_format_with_nonzero_probability"])
    elif family == "repair":
        base.extend(["repair_hook_configured_or_format_repair_available"])
    elif family.startswith("numeric"):
        base.extend(["numeric_root_or_boundary_observed", "candidate_input_influence_range_available"])
    else:
        base.extend(["low_confidence_generic_fallback_only"])
    base.extend(required)
    return tuple(dict.fromkeys(base))


def operator_expected_effect(name: str, family: str) -> tuple[str, ...]:
    if family == "compare_operand":
        return ("change_compare_operand_or_token_match", "improve_equality_atom_or_branch_guard")
    if family == "state_flip":
        return ("change_root_state", "change_producer_state", "preserve_or_recover_use_context")
    if family == "sequence_edit":
        return ("change_lifecycle_prefix", "change_next_event_reachability")
    if family == "repair":
        return ("preserve_reach_after_format_sensitive_mutation",)
    if family.startswith("numeric"):
        return ("change_numeric_margin", "cross_boundary_when_possible")
    return ("produce_replay_stable_root_or_event_change",)


def operator_fallback(name: str, family: str) -> str:
    if family in {"compare_operand", "token_mutation"}:
        return "dictionary insertion"
    if family == "state_flip":
        return "guard-field perturbation"
    if family == "sequence_edit":
        return "phase-preserving mutation"
    if family == "repair":
        return "bounded byte perturbation around candidate range"
    return "generic byte perturbation"


def operator_definition(operator_name: str, category: str) -> dict[str, Any]:
    for item in registry().get(category, registry()["generic"])["mutators"]:
        if item["name"] == operator_name:
            return dict(item)
    for item in registry()["generic"]["mutators"]:
        if item["name"] == operator_name:
            return dict(item)
    return {
        "name": operator_name,
        "category": category,
        "operator_family": "generic_local",
        "preconditions": ("seed_reaches_target_context", "replay_available"),
        "required_evidence": (),
        "expected_effect": ("produce_replay_stable_root_or_event_change",),
        "fallback": "generic byte perturbation",
    }


def evaluate_operator_preconditions(
    operator_name: str,
    atom: TCAtom,
    record: ReplayRecord,
    graph: TriggerProgressGraph,
) -> dict[str, Any]:
    opdef = operator_definition(operator_name, atom.category)
    node_types = {node.get("type") for node in graph.nodes}
    checks: dict[str, bool] = {}
    for precondition in opdef.get("preconditions", []):
        if precondition == "seed_reaches_target_context":
            checks[precondition] = record.reached_R
        elif precondition == "replay_available":
            checks[precondition] = record.replay_stable
        elif "candidate_input_influence_range" in precondition:
            checks[precondition] = "candidate_input_influence_range" in node_types or record.input_size > 0
        elif "guard" in precondition:
            checks[precondition] = "guard_context" in node_types
        elif "producer" in precondition:
            checks[precondition] = "producer_context" in node_types
        elif "use_context" in precondition:
            checks[precondition] = "use_context" in node_types
        elif "event_or_phase_boundary" in precondition or "lifecycle_phase" in precondition:
            checks[precondition] = "lifecycle_phase" in node_types or bool(atom.root_events)
        elif "repair_hook" in precondition:
            checks[precondition] = "repair_hook" in node_types
        elif "operand_visible" in precondition or "numeric_root" in precondition or "root_or_producer" in precondition:
            checks[precondition] = bool(atom.root_variables or atom.root_events or root_signature(record.tc_root_state))
        elif "low_confidence_generic" in precondition:
            checks[precondition] = True
        else:
            checks[precondition] = True
    satisfied = all(checks.values()) if checks else True
    return {
        "operator_name": operator_name,
        "atom_id": atom.atom_id,
        "satisfied": satisfied,
        "checks": checks,
        "definition": opdef,
    }


def priority_components(category: str) -> list[str]:
    if category in {"numeric-margin", "equality/magic"}:
        return ["reach", "trigger", "native_bucket", "native_dt", "root_alignment", "influence_confidence", "coverage"]
    if category == "binary-state-null":
        return ["reach", "trigger", "root_alignment", "root_signature", "native_bucket", "influence_confidence", "coverage"]
    if category == "compound-sequence-lifecycle":
        return ["reach", "trigger", "lifecycle_prefix", "root_alignment", "root_signature", "native_bucket", "coverage"]
    return ["reach", "trigger", "root_alignment", "native_bucket", "native_dt", "influence_confidence", "coverage"]


def graph_features_for_atom(atom: TCAtom, graph: TriggerProgressGraph | None) -> list[dict[str, Any]]:
    if graph is None:
        return []
    allowed = {
        "root_variable_or_event": "root variable/event",
        "producer_context": "producer context",
        "guard_context": "guard context",
        "use_context": "use context",
        "lifecycle_phase": "sequence/lifecycle node",
        "candidate_input_influence_range": "influence range",
    }
    features: list[dict[str, Any]] = []
    for node_item in graph.nodes:
        node_type = str(node_item.get("type", ""))
        if node_type not in allowed:
            continue
        atom_id = str(node_item.get("atom_id", ""))
        if atom_id and atom_id != atom.atom_id:
            continue
        features.append(
            {
                "feature": allowed[node_type],
                "node_id": node_item.get("id", ""),
                "node_type": node_type,
                "label": node_item.get("label", ""),
                "source_location": node_item.get("source_location", ""),
                "runtime_event_id": node_item.get("runtime_event_id", ""),
            }
        )
    return features


def build_atom_plan(
    target_id: str,
    atom: TCAtom,
    health: SignalHealth,
    planning_phase: str = "final",
    graph: TriggerProgressGraph | None = None,
) -> AtomPlan:
    reg = registry().get(atom.category, registry()["generic"])
    if health.native_status == "actionable":
        use_native = True
        use_lifted = False
        reason = "native_DT_actionable"
    elif health.native_status == "unknown":
        use_native = True
        use_lifted = True
        reason = "native_DT_unknown_hybrid:" + ",".join(health.reasons or ["unknown"])
    else:
        use_native = False
        use_lifted = True
        reason = "native_DT_requires_lift:" + ",".join(health.reasons or ["unknown"])
    return AtomPlan(
        target_id=target_id,
        atom_id=atom.atom_id,
        category=atom.category,
        expression=atom.expression,
        use_native_dt=use_native,
        use_lifted_features=use_lifted,
        feature_extractors=[item["name"] for item in reg["features"]],
        mutator_operators=[item["name"] for item in reg["mutators"]],
        priority_components=priority_components(atom.category),
        actionability=health.to_dict(),
        plan_reason=reason,
        planning_phase=planning_phase,
        graph_features=graph_features_for_atom(atom, graph) if planning_phase == "final" else [],
        graph_node_ids=[str(item.get("node_id", "")) for item in graph_features_for_atom(atom, graph)] if planning_phase == "final" else [],
    )


def build_coarse_atom_plan(target_id: str, atom: TCAtom, health: SignalHealth) -> AtomPlan:
    return build_atom_plan(target_id, atom, health, planning_phase="coarse", graph=None)


def finalize_atom_plan(target_id: str, atom: TCAtom, health: SignalHealth, graph: TriggerProgressGraph) -> AtomPlan:
    return build_atom_plan(target_id, atom, health, planning_phase="final", graph=graph)


BuildCoarseAtomPlan = build_coarse_atom_plan
FinalizeAtomPlan = finalize_atom_plan


def node(node_id: str, node_type: str, label: str, **attrs: Any) -> dict[str, Any]:
    payload = {"id": node_id, "type": node_type, "label": label}
    payload.update(attrs)
    return payload


def edge(src: str, dst: str, edge_type: str, **attrs: Any) -> dict[str, Any]:
    payload = {"src": src, "dst": dst, "type": edge_type}
    payload.update(attrs)
    return payload


def build_trigger_progress_graph(
    target_id: str,
    target_meta: dict[str, str],
    atoms: list[TCAtom],
    records: list[ReplayRecord],
) -> TriggerProgressGraph:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    seen_nodes: set[str] = set()

    def add_node(payload: dict[str, Any]) -> None:
        if payload["id"] in seen_nodes:
            return
        seen_nodes.add(payload["id"])
        nodes.append(payload)

    source_location = (
        target_meta.get("target_location")
        or target_meta.get("observation_point")
        or target_meta.get("source_location")
        or f"{target_meta.get('source_file', '')}:{target_meta.get('source_line', '')}".strip(":")
        or "unknown"
    )
    target_node = f"target:{target_id}"
    source_locations = split_source_locations(source_location)
    add_node(
        node(
            target_node,
            "target_context",
            target_id,
            source_location=source_location,
            confidence="high" if source_location != "unknown" else "low",
        )
    )
    for index, loc in enumerate(source_locations):
        site_node = f"site:{index + 1}:{stable_id(loc)}"
        add_node(
            node(
                site_node,
                "target_site_context",
                loc,
                source_location=loc,
                confidence="high" if loc != "unknown" else "low",
            )
        )
        edges.append(edge(site_node, target_node, "site_of_target", site_index=index + 1))
    for atom in atoms:
        atom_node = f"atom:{atom.atom_id}"
        add_node(
            node(
                atom_node,
                "tc_atom",
                atom.expression,
                category=atom.category,
                source_location=atom.source_location or source_location,
                source_locations=atom.source_locations or source_locations,
                composition=atom.composition,
                group_id=atom.group_id,
                confidence=atom.confidence,
            )
        )
        edges.append(edge(atom_node, target_node, "belongs_to_target"))
        if atom.source_location:
            edges.append(edge(atom_node, f"site:{min(source_locations.index(atom.source_location) + 1 if atom.source_location in source_locations else 1, len(source_locations))}:{stable_id(atom.source_location if atom.source_location in source_locations else source_locations[0])}", "located_at"))
        roots = atom.root_variables or [f"{atom.atom_id}:root"]
        for root in roots:
            root_node = f"root:{atom.atom_id}:{stable_id(root)}"
            add_node(
                node(
                    root_node,
                    "root_variable_or_event",
                    root,
                    atom_id=atom.atom_id,
                    source_location=atom.source_location or source_location,
                    source_locations=atom.source_locations or source_locations,
                    confidence="medium" if atom.root_variables else "low",
                )
            )
            edges.append(edge(root_node, atom_node, "defines_atom"))
    for left, right in zip(atoms, atoms[1:]):
        edges.append(
            edge(
                f"atom:{left.atom_id}",
                f"atom:{right.atom_id}",
                "order_constraint",
                order="expression_order",
                confidence="medium" if left.category == "compound-sequence-lifecycle" or right.category == "compound-sequence-lifecycle" else "low",
            )
        )
    if any(atom.category == "compound-sequence-lifecycle" for atom in atoms):
        prev = ""
        for phase in ["producer", "configured", "aliased", "released_or_skipped", "used_or_violated"]:
            phase_node = f"phase:{phase}"
            add_node(
                node(
                    phase_node,
                    "lifecycle_phase",
                    phase,
                    source_location=source_location,
                    runtime_event_id=f"lifecycle:{phase}",
                    confidence="low",
                )
            )
            if prev:
                edges.append(edge(prev, phase_node, "order_constraint", order="lifecycle_prefix"))
            prev = phase_node
    producer_keys = sorted({record.producer or record.source_seedbank for record in records if record.producer or record.source_seedbank})
    if not producer_keys:
        producer_keys = ["unknown_producer"]
    for producer in producer_keys[:32]:
        prod_node = f"producer:{stable_id(producer)}"
        add_node(
            node(
                prod_node,
                "producer_context",
                producer,
                runtime_event_id=f"producer:{stable_id(target_id, producer)}",
                source_location="",
                confidence="medium" if producer != "unknown_producer" else "low",
            )
        )
        edges.append(edge(prod_node, target_node, "may_enable_target"))

    guard_node = f"guard:{stable_id(source_location)}"
    add_node(
        node(
            guard_node,
            "guard_context",
            target_meta.get("canary_expression") or target_meta.get("tc_annotation") or "target_guard",
            source_location=source_location,
            runtime_event_id="",
            confidence="high" if source_location != "unknown" else "low",
        )
    )
    use_node = f"use:{stable_id(target_id, source_location)}"
    add_node(
        node(
            use_node,
            "use_context",
            target_meta.get("observation_point") or source_location,
            source_location=source_location,
            runtime_event_id="",
            confidence="high" if source_location != "unknown" else "low",
        )
    )
    edges.append(edge(guard_node, use_node, "guards_use"))
    edges.append(edge(use_node, target_node, "observes_target"))
    for prod in [item["id"] for item in nodes if item["type"] == "producer_context"]:
        edges.append(edge(prod, guard_node, "order_before", order="producer_before_guard"))
    edges.append(edge(guard_node, use_node, "order_before", order="guard_before_use"))

    for record in records[:64]:
        if record.input_size <= 0:
            continue
        range_records = parse_range_metadata(record)
        if not range_records:
            range_records = [
                {
                    "start": 0,
                    "length": min(record.input_size, 4096),
                    "confidence_label": "low",
                    "runtime_event_id": f"seed:{stable_id(record.seed_id, record.replay_hash)}",
                    "source": "whole_input_fallback",
                }
            ]
        for index, range_record in enumerate(range_records[:8]):
            start = as_int(range_record.get("start"), 0)
            range_len = as_int(range_record.get("length"), 0)
            if range_len <= 0:
                continue
            confidence_label = range_record.get("confidence_label", "medium")
            range_node = f"range:{stable_id(record.seed_id, record.content_sha256, start, range_len, index)}"
            add_node(
                node(
                    range_node,
                    "candidate_input_influence_range",
                    f"{record.seed_id}[{start}:{start + range_len}]",
                    seed_id=record.seed_id,
                    start=start,
                    length=range_len,
                    confidence=confidence_label,
                    confidence_score=confidence_to_float(range_record.get("confidence", confidence_label)),
                    runtime_event_id=range_record.get("runtime_event_id", f"seed:{stable_id(record.seed_id, record.replay_hash)}"),
                    source=range_record.get("source", "replay_metadata"),
                )
            )
            edges.append(edge(range_node, guard_node, "candidate_influences"))

    repair_hooks = repair_hooks_for_target(target_meta)
    for hook in repair_hooks:
        hook_node = f"repair:{stable_id(target_id, hook['name'])}"
        add_node(node(hook_node, "repair_hook", hook["name"], **hook))
        edges.append(edge(hook_node, guard_node, "may_repair_after_mutation"))

    confidence_counts = Counter(item.get("confidence", "unknown") for item in nodes)
    return TriggerProgressGraph(
        target_id=target_id,
        schema_version="formtrig-trigger-progress-graph-v2",
        nodes=nodes,
        edges=edges,
        repair_hooks=repair_hooks,
        confidence_summary=dict(confidence_counts),
    )


def repair_hooks_for_target(target_meta: dict[str, str]) -> list[dict[str, Any]]:
    fmt = " ".join(
        [
            target_meta.get("expected_input_format", ""),
            target_meta.get("program", ""),
            target_meta.get("project", ""),
        ]
    ).lower()
    hooks: list[dict[str, Any]] = []
    if any(token in fmt for token in ["png", "zip", "pdf", "mp4", "jpeg", "xml", "archive"]):
        hooks.append(
            {
                "name": "format_repair_hook_available_if_configured",
                "kind": "external_or_project_format_repair",
                "configured": False,
                "confidence": "low",
            }
        )
    return hooks


def parse_range_metadata(record: ReplayRecord) -> list[dict[str, Any]]:
    raw_value = (
        record.raw.get("hot_ranges")
        or record.raw.get("hot_byte_ranges")
        or record.raw.get("influence_ranges")
        or ""
    )
    if not raw_value:
        return []
    try:
        parsed = json.loads(raw_value)
    except json.JSONDecodeError:
        parsed = []
        for item in re.split(r"\s*[;|]\s*", raw_value):
            if not item:
                continue
            match = re.match(r"^(\d+)\s*[:+,]\s*(\d+)(?:\s*[:+,]\s*([0-9.]+))?$", item)
            if match:
                parsed.append(
                    {
                        "start": int(match.group(1)),
                        "len": int(match.group(2)),
                        "confidence": float(match.group(3) or 0.5),
                    }
                )
    if isinstance(parsed, dict):
        parsed = [parsed]
    ranges: list[dict[str, Any]] = []
    for item in parsed if isinstance(parsed, list) else []:
        if not isinstance(item, dict):
            continue
        start = as_int(item.get("start"), -1)
        length = as_int(item.get("len", item.get("length")), 0)
        if start < 0 or length <= 0 or start >= record.input_size:
            continue
        confidence = confidence_to_float(item.get("confidence", item.get("confidence_label", "medium")))
        ranges.append(
            {
                "start": start,
                "length": min(length, max(0, record.input_size - start)),
                "confidence": confidence,
                "confidence_label": item.get("confidence_label", "verified" if confidence >= 0.8 else "medium"),
                "runtime_event_id": item.get("runtime_event_id", f"seed:{stable_id(record.seed_id, start, length)}"),
                "source": item.get("source", "replay_metadata"),
            }
        )
    return ranges[:8]


def atom_has_incoming_guard(atom: TCAtom, tcir: TCIR | None) -> bool:
    if tcir is None:
        return False
    return any(edge.dst == atom.atom_id and edge.edge_type == "guard" for edge in tcir.edges)


def decode_c_char_literal(token: str) -> int | None:
    if not (token.startswith("'") and token.endswith("'")):
        return None
    body = token[1:-1]
    escapes = {"n": "\n", "r": "\r", "t": "\t", "0": "\0", "\\": "\\", "'": "'", '"': '"'}
    if body.startswith("\\"):
        if len(body) >= 2 and body[1] in escapes:
            return ord(escapes[body[1]])
        if len(body) >= 2 and body[1] == "x":
            try:
                return int(body[2:], 16)
            except ValueError:
                return None
    if len(body) == 1:
        return ord(body)
    return None


def normalize_constant_token(token: str) -> tuple[str, str]:
    raw = token.strip()
    if raw.startswith("'") and raw.endswith("'"):
        value = decode_c_char_literal(raw)
        if value is not None:
            return str(value), "char"
        return raw[1:-1], "char"
    if raw.startswith('"') and raw.endswith('"'):
        return raw[1:-1], "string"
    try:
        return str(int(raw, 0)), "numeric"
    except ValueError:
        pass
    symbolic = {
        "PALETTE": "3",
        "RGB": "2",
        "GRAY": "0",
        "READY": "READY",
        "PARTIAL": "PARTIAL",
        "NULL": "NULL",
    }.get(raw, raw)
    return symbolic, "symbolic"


def symbolic_constant_value(name: str) -> str:
    return normalize_constant_token(name)[0]


def infer_atom_truth_from_root_state(record: ReplayRecord, atom: TCAtom) -> tuple[bool | None, str, str]:
    parsed = parse_root_state(record.tc_root_state)
    expr = atom.expression
    if atom.category == "binary-state-null":
        for root in atom.root_variables:
            base = root.split("->")[-1].split(".")[-1]
            for key in [f"{base}_null", f"{root}_null", "palette_null", "ptr_null", "is_null"]:
                if key in parsed:
                    value = parsed[key].lower()
                    return value in {"1", "true", "yes", "null"}, key, parsed[key]
    match = re.search(r"([A-Za-z_][A-Za-z0-9_.>\-]*)\s*(==|!=)\s*([A-Za-z_][A-Za-z0-9_]*|0x[0-9A-Fa-f]+|\d+|'(?:\\.|[^'])*'|\"[^\"]*\")", expr)
    if match:
        lhs, op, rhs = match.groups()
        key = lhs.split("->")[-1].split(".")[-1]
        rhs_value, rhs_kind = normalize_constant_token(rhs)
        if rhs_kind == "string":
            bool_key = f"{key}_{rhs_value}"
            if bool_key in parsed:
                equal = str(parsed[bool_key]).lower() in {"1", "true", "yes"}
                return (equal if op == "==" else not equal), bool_key, parsed[bool_key]
        if key in parsed:
            equal = parsed[key] == rhs_value
            return (equal if op == "==" else not equal), key, parsed[key]
    if record.triggered_T and len(atom.root_variables) <= 1 and not atom.root_events and not parse_root_state(record.tc_root_state):
        return True, "trigger_oracle", "1"
    return None, "", ""


def atom_observation(record: ReplayRecord, atom: TCAtom, tcir: TCIR | None = None) -> AtomObservation:
    if not record.reached_R:
        return AtomObservation(atom.atom_id, "NOT_OBSERVED", False, False, False, False, "", "", "target_not_reached")
    if not record.replay_stable and not record.triggered_T:
        return AtomObservation(atom.atom_id, "UNKNOWN_UNSTABLE", False, False, False, False, "", "", "replay_not_stable")
    parsed = parse_root_state(record.tc_root_state)
    blocked = str(parsed.get("blocked_by_guard", parsed.get("guard_blocked", ""))).lower() in {"1", "true", "yes"}
    if not blocked and atom_has_incoming_guard(atom, tcir):
        use_value = str(parsed.get("use_reached", "")).lower()
        blocked = use_value in {"0", "false", "no"}
    if blocked:
        return AtomObservation(atom.atom_id, "BLOCKED_BY_GUARD", False, True, False, False, "guard", "blocked", "guard_not_satisfied")
    truth, key, value = infer_atom_truth_from_root_state(record, atom)
    if truth is True:
        return AtomObservation(atom.atom_id, "OBSERVED_TRUE", True, False, True, False, key, value, "root_state_or_trigger_true")
    if truth is False:
        return AtomObservation(atom.atom_id, "OBSERVED_FALSE", True, False, False, True, key, value, "root_state_false")
    for root in atom.root_variables:
        candidates = [root, root.split("->")[-1].split(".")[-1]]
        for candidate in candidates:
            if candidate in parsed:
                return AtomObservation(atom.atom_id, "OBSERVED_FALSE", True, False, False, True, candidate, parsed[candidate], "atom_root_observed_without_truth")
            null_key = f"{candidate}_null"
            if null_key in parsed:
                return AtomObservation(atom.atom_id, "OBSERVED_FALSE", True, False, False, True, null_key, parsed[null_key], "atom_root_observed_without_truth")
    for event in atom.root_events:
        for candidate in [event, f"{event}_reached", f"{event}_seen", f"{event}_event"]:
            if candidate in parsed:
                return AtomObservation(atom.atom_id, "OBSERVED_FALSE", True, False, False, True, candidate, parsed[candidate], "atom_event_observed_without_truth")
    if atom.root_events and record.coverage_hash.startswith("gdb_probe:"):
        return AtomObservation(atom.atom_id, "OBSERVED_FALSE", True, False, False, True, atom.root_events[0], "probe", "runtime_event_probe_observed")
    return AtomObservation(atom.atom_id, "NOT_OBSERVED", False, False, False, False, "", "", "no_atom_observation")


def object_identity_confidence_from_state(text: str) -> float:
    parsed = parse_root_state(text)
    for key in ["object_identity_confidence", "same_object_confidence", "same_object"]:
        if key in parsed:
            return confidence_to_float(parsed[key])
    return 0.0


def next_event_reachability_from_state(text: str) -> float:
    parsed = parse_root_state(text)
    for key in ["next_event_reachability", "next_event"]:
        if key in parsed:
            return confidence_to_float(parsed[key])
    return 1.0 if lifecycle_prefix_score(text) > 0 else 0.0


def phase_novelty_from_state(text: str) -> float:
    parsed = parse_root_state(text)
    if "phase_novelty" in parsed:
        return confidence_to_float(parsed["phase_novelty"])
    return min(lifecycle_prefix_score(text) / 5.0, 1.0)


def atom_score_from_vector(vector: ProgressVector) -> float:
    if vector.triggered:
        return 1000.0
    score = 0.0
    if vector.reached:
        score += 10.0
    if vector.observation_status == "OBSERVED_TRUE":
        score += 100.0
    elif vector.observation_status == "OBSERVED_FALSE":
        score += 20.0
    elif vector.observation_status == "BLOCKED_BY_GUARD":
        score -= 5.0
    if vector.native_bucket is not None:
        score += max(0.0, 20.0 - float(vector.native_bucket))
    score += vector.lifecycle_prefix * 5.0
    score += vector.influence_confidence * 5.0
    score += vector.object_identity_confidence * 10.0
    return score


def progress_vector(record: ReplayRecord, atom: TCAtom, plan: AtomPlan, tcir: TCIR | None = None) -> ProgressVector:
    sig = root_signature(record.tc_root_state)
    aligned = bool(sig or record.coverage_hash.startswith("gdb_probe:"))
    influence = 0.0
    if record.source_seed:
        influence += 0.1
    if record.producer:
        influence += 0.1
    if sig:
        influence += 0.2
    observation = atom_observation(record, atom, tcir)
    atom_native_dt = as_float(record.raw.get(f"native_DT_{atom.atom_id}"), record.native_DT)
    atom_bucket = dt_bucket(atom_native_dt)
    vector = ProgressVector(
        target_id=record.target_id,
        seed_id=record.seed_id,
        atom_id=atom.atom_id,
        category=atom.category,
        reached=record.reached_R,
        triggered=record.triggered_T,
        native_dt=atom_native_dt,
        native_bucket=atom_bucket,
        root_state=record.tc_root_state,
        root_signature=sig,
        lifecycle_prefix=lifecycle_prefix_score(record.tc_root_state),
        influence_confidence=min(influence, 1.0),
        coverage_hash=record.coverage_hash,
        replay_stable=record.replay_stable,
        root_or_event_aligned=aligned,
        observation_status=observation.status,
        object_identity_confidence=object_identity_confidence_from_state(record.tc_root_state),
        next_event_reachability=next_event_reachability_from_state(record.tc_root_state),
        phase_novelty=phase_novelty_from_state(record.tc_root_state),
    )
    vector.atom_score = atom_score_from_vector(vector)
    return vector


def component_improved(component: str, new: ProgressVector, old_vectors: list[ProgressVector]) -> bool:
    if component == "trigger":
        if not old_vectors:
            return new.triggered
        return new.triggered and not any(old.triggered for old in old_vectors)
    if component in {"native_bucket", "native_dt"}:
        value = new.component(component)
        if value is None:
            return False
        if not old_vectors:
            return True
        old_values = [old.component(component) for old in old_vectors if old.component(component) is not None]
        return not old_values or float(value) < min(float(item) for item in old_values)
    if component == "root_signature":
        value = new.root_signature
        if not old_vectors:
            return bool(value)
        return bool(value) and value not in {old.root_signature for old in old_vectors}
    if component == "root_alignment":
        if not old_vectors:
            return new.root_or_event_aligned
        return new.root_or_event_aligned and not all(old.root_or_event_aligned for old in old_vectors)
    if component == "lifecycle_prefix":
        if not old_vectors:
            return new.lifecycle_prefix > 0
        return new.lifecycle_prefix > max((old.lifecycle_prefix for old in old_vectors), default=-1)
    if component == "influence_confidence":
        if not old_vectors:
            return new.influence_confidence > 0.0
        return new.influence_confidence > max((old.influence_confidence for old in old_vectors), default=-1.0)
    if component == "coverage":
        if not old_vectors:
            return bool(new.coverage_hash)
        return bool(new.coverage_hash) and new.coverage_hash not in {old.coverage_hash for old in old_vectors}
    return False


def component_regressed(component: str, new: ProgressVector, old_vectors: list[ProgressVector]) -> bool:
    if not old_vectors:
        return False
    if component == "reach":
        return not new.reached
    if component == "trigger":
        return False
    if component in {"native_bucket", "native_dt"}:
        value = new.component(component)
        old_values = [old.component(component) for old in old_vectors if old.component(component) is not None]
        if value is None or not old_values:
            return False
        return float(value) > min(float(item) for item in old_values)
    if component == "root_alignment":
        return any(old.root_or_event_aligned for old in old_vectors) and not new.root_or_event_aligned
    if component == "lifecycle_prefix":
        return new.lifecycle_prefix < max((old.lifecycle_prefix for old in old_vectors), default=0)
    if component == "influence_confidence":
        return new.influence_confidence + 1e-9 < max((old.influence_confidence for old in old_vectors), default=0.0)
    return False


def reason_for_component(component: str, category: str) -> str:
    if component in {"native_bucket", "native_dt", "trigger"}:
        return "native-distance improvement"
    if component in {"root_signature", "root_alignment"}:
        return "root-aligned state transition"
    if component == "lifecycle_prefix" or category == "compound-sequence-lifecycle":
        return "lifecycle-prefix improvement"
    if component == "influence_confidence":
        return "influence-confidence improvement"
    return "lifted-feature improvement"


def group_score(group: TCGroup, atom_vectors: dict[str, ProgressVector], group_vectors: dict[str, GroupProgressVector]) -> GroupProgressVector:
    child_scores: dict[str, float] = {}
    for child in group.children:
        if child in atom_vectors:
            child_scores[child] = atom_vectors[child].atom_score
        elif child in group_vectors:
            child_scores[child] = group_vectors[child].score
    if not child_scores:
        return GroupProgressVector(group.group_id, group.group_type, 0.0, False, "", {})
    if group.group_type == "ANY_OF":
        selected = max(child_scores, key=lambda item: child_scores[item])
        score = child_scores[selected]
        satisfied = score >= 100.0
    elif group.group_type == "NOT":
        selected = next(iter(child_scores))
        score = -child_scores[selected]
        satisfied = child_scores[selected] <= 0.0
    elif group.group_type == "SEQUENCE":
        selected = ""
        score = sum(child_scores.values())
        satisfied = all(value >= 100.0 for value in child_scores.values())
    else:
        selected = ""
        score = min(child_scores.values()) + 0.1 * sum(child_scores.values())
        satisfied = all(value >= 20.0 for value in child_scores.values())
    return GroupProgressVector(group.group_id, group.group_type, score, satisfied, selected, child_scores)


def build_full_progress_vector(
    record: ReplayRecord,
    tcir: TCIR,
    plans: dict[str, AtomPlan],
) -> FullProgressVector:
    atom_vectors: dict[str, ProgressVector] = {}
    atom_observations: dict[str, dict[str, Any]] = {}
    for atom in tcir.atoms:
        plan = plans[atom.atom_id]
        vector = progress_vector(record, atom, plan, tcir)
        atom_vectors[atom.atom_id] = vector
        atom_observations[atom.atom_id] = atom_observation(record, atom, tcir).to_dict()
    group_vectors: dict[str, GroupProgressVector] = {}
    for group in reversed(tcir.groups):
        group_vectors[group.group_id] = group_score(group, atom_vectors, group_vectors)
    root_group = group_vectors.get(tcir.root_group_id)
    selected_branch = root_group.selected_branch if root_group else ""
    branch_scores = root_group.branch_scores if root_group else {}
    guard_status = "blocked" if any(item.get("status") == "BLOCKED_BY_GUARD" for item in atom_observations.values()) else "available"
    # Comparable frontier slots describe the post-reach target context, not
    # coverage novelty. Coverage remains a tie-breaker in the vector/logs, but
    # must not let coverage-only changes bypass dominance checks.
    target_context_hash = str(record.raw.get("target_context_hash") or stable_id(record.target_id, "target_context"))
    return FullProgressVector(
        target_id=record.target_id,
        seed_id=record.seed_id,
        reached=record.reached_R,
        triggered=record.triggered_T,
        replay_stable=record.replay_stable,
        root_or_event_aligned=bool(root_signature(record.tc_root_state) or record.coverage_hash.startswith("gdb_probe:")),
        target_context_hash=target_context_hash,
        atom_vectors={key: value.to_dict() for key, value in atom_vectors.items()},
        atom_observations=atom_observations,
        group_progress={key: value.to_dict() for key, value in group_vectors.items()},
        selected_branch=selected_branch,
        branch_scores=branch_scores,
        object_identity_confidence=max((value.object_identity_confidence for value in atom_vectors.values()), default=0.0),
        next_event_reachability=max((value.next_event_reachability for value in atom_vectors.values()), default=0.0),
        phase_novelty=max((value.phase_novelty for value in atom_vectors.values()), default=0.0),
        lifecycle_prefix=max((value.lifecycle_prefix for value in atom_vectors.values()), default=0),
        guard_status=guard_status,
        reach_stability=1.0 if record.reached_R else 0.0,
        coverage_hash=record.coverage_hash,
    )


def comparable_key_for_vector(vector: FullProgressVector) -> ComparableFrontierKey:
    object_bucket = "none"
    if vector.object_identity_confidence >= 0.8:
        object_bucket = "same_object_high"
    elif vector.object_identity_confidence > 0:
        object_bucket = "same_object_low"
    return ComparableFrontierKey(vector.target_context_hash, vector.selected_branch, object_bucket, vector.guard_status)


def seed_progress_record(record: ReplayRecord, tcir: TCIR, plans: dict[str, AtomPlan], rank: int = 0) -> SeedProgressRecord:
    full = build_full_progress_vector(record, tcir, plans)
    return SeedProgressRecord(record=record, full_vector=full, comparable_key=comparable_key_for_vector(full), non_dominated_rank=rank)


def full_vector_score(vector: FullProgressVector, tcir: TCIR) -> float:
    root = vector.group_progress.get(tcir.root_group_id, {})
    score = float(root.get("score", 0.0))
    if vector.triggered:
        score += 10000.0
    return score


def vector_dominated_by(new: FullProgressVector, old: FullProgressVector, tcir: TCIR) -> bool:
    if old.triggered and not new.triggered:
        return True
    if full_vector_score(old, tcir) > full_vector_score(new, tcir):
        return True
    if full_vector_score(old, tcir) == full_vector_score(new, tcir):
        old_atoms = old.atom_vectors
        new_atoms = new.atom_vectors
        if all(float(old_atoms.get(atom.atom_id, {}).get("atom_score", 0.0)) >= float(new_atoms.get(atom.atom_id, {}).get("atom_score", 0.0)) for atom in tcir.atoms):
            return True
    return False


def insert_non_dominated(
    frontier: list[SeedProgressRecord],
    seed_progress: SeedProgressRecord,
    tcir: TCIR,
) -> tuple[list[SeedProgressRecord], int]:
    comparable = [item for item in frontier if item.comparable_key == seed_progress.comparable_key]
    if any(vector_dominated_by(seed_progress.full_vector, old.full_vector, tcir) for old in comparable):
        return frontier, 0
    removed_ids = {
        old.record.seed_id
        for old in comparable
        if vector_dominated_by(old.full_vector, seed_progress.full_vector, tcir)
    }
    next_frontier = [item for item in frontier if item.record.seed_id not in removed_ids]
    seed_progress.non_dominated_rank = len(next_frontier)
    next_frontier.append(seed_progress)
    return next_frontier, len(removed_ids)


def select_frontier_seed(frontier: list[SeedProgressRecord], tcir: TCIR, plans: dict[str, AtomPlan]) -> SeedProgressRecord | None:
    if not frontier:
        return None
    return max(frontier, key=lambda item: (full_vector_score(item.full_vector, tcir), -item.non_dominated_rank))


def select_focus_atoms(parent: SeedProgressRecord, tcir: TCIR, plans: dict[str, AtomPlan]) -> list[str]:
    focus: list[str] = []
    for atom in tcir.atoms:
        vec = parent.full_vector.atom_vectors.get(atom.atom_id, {})
        obs = parent.full_vector.atom_observations.get(atom.atom_id, {})
        if obs.get("status") in {"OBSERVED_TRUE"}:
            continue
        if plans[atom.atom_id].use_lifted_features or plans[atom.atom_id].use_native_dt:
            focus.append(atom.atom_id)
    return focus or [atom.atom_id for atom in tcir.atoms]


def build_initial_frontier_records(
    rnt_records: list[ReplayRecord],
    tcir: TCIR,
    plans: dict[str, AtomPlan],
) -> tuple[list[SeedProgressRecord], list[ProgressDecision]]:
    frontier: list[SeedProgressRecord] = []
    decisions: list[ProgressDecision] = []
    for record in rnt_records:
        accepted, decision, seed_progress = progress_dominates_global(record, frontier, tcir, plans)
        if not frontier and is_strict_rnt(record) and record.replay_stable:
            decision.accepted = True
            decision.reason = "initial_frontier_seed"
            frontier.append(seed_progress)
        elif accepted:
            decision.reason = "initial_frontier_seed"
            frontier, _ = insert_non_dominated(frontier, seed_progress, tcir)
        decisions.append(decision)
    return frontier, decisions


BuildInitialFrontier = build_initial_frontier_records
InsertNonDominated = insert_non_dominated
SelectFrontierSeed = select_frontier_seed
SelectFocusAtoms = select_focus_atoms


def global_regressions(new: FullProgressVector, old_records: list[SeedProgressRecord], tcir: TCIR) -> list[str]:
    regressions: list[str] = []
    if not old_records:
        return regressions
    best_by_atom: dict[str, float] = {}
    for old in old_records:
        for atom_id, vec in old.full_vector.atom_vectors.items():
            best_by_atom[atom_id] = max(best_by_atom.get(atom_id, -INF), float(vec.get("atom_score", 0.0)))
    guard_edges = {(edge.src, edge.dst) for edge in tcir.edges if edge.edge_type == "guard"}
    for atom in tcir.atoms:
        new_obs = new.atom_observations.get(atom.atom_id, {})
        if new_obs.get("status") == "BLOCKED_BY_GUARD":
            continue
        new_score = float(new.atom_vectors.get(atom.atom_id, {}).get("atom_score", 0.0))
        best = best_by_atom.get(atom.atom_id)
        if best is not None and new_score + 1e-9 < best:
            regressions.append(f"atom_regressed:{atom.atom_id}")
        for guard, guarded in guard_edges:
            if guarded == atom.atom_id:
                guard_obs = new.atom_observations.get(guard, {})
                if guard_obs.get("status") == "OBSERVED_FALSE":
                    regressions.append(f"guard_regressed:{guard}->{guarded}")
    for atom in tcir.atoms:
        if atom.category == "compound-sequence-lifecycle":
            vec = new.atom_vectors.get(atom.atom_id, {})
            if float(vec.get("lifecycle_prefix", 0.0)) > 0 and float(vec.get("object_identity_confidence", 0.0)) < 0.5:
                regressions.append(f"lifecycle_object_identity_weak:{atom.atom_id}")
    return sorted(set(regressions))


def improved_components_global(new: FullProgressVector, old_records: list[SeedProgressRecord], tcir: TCIR) -> list[str]:
    if new.triggered:
        return ["trigger", "native_bucket", "native_dt"]
    if not old_records:
        return ["frontier_seed"] if new.root_or_event_aligned else []
    improved: list[str] = []
    old_best = max(full_vector_score(old.full_vector, tcir) for old in old_records)
    if full_vector_score(new, tcir) > old_best:
        improved.append("group_progress")
    for atom in tcir.atoms:
        new_vec = new.atom_vectors.get(atom.atom_id, {})
        old_atom_best = max(float(old.full_vector.atom_vectors.get(atom.atom_id, {}).get("atom_score", 0.0)) for old in old_records)
        if float(new_vec.get("atom_score", 0.0)) > old_atom_best:
            improved.append(f"atom_progress:{atom.atom_id}")
        if new_vec.get("root_signature") and new_vec.get("root_signature") not in {
            old.full_vector.atom_vectors.get(atom.atom_id, {}).get("root_signature", "") for old in old_records
        }:
            improved.append(f"root_signature:{atom.atom_id}")
    if new.object_identity_confidence > max((old.full_vector.object_identity_confidence for old in old_records), default=0.0):
        improved.append("object_identity_confidence")
    elif new.triggered and new.object_identity_confidence > 0:
        improved.append("object_identity_confidence")
    if new.phase_novelty > max((old.full_vector.phase_novelty for old in old_records), default=0.0):
        improved.append("phase_novelty")
    return sorted(set(item for item in improved if not item.startswith("coverage")))


def reason_for_global_components(components: list[str], tcir: TCIR) -> str:
    if any(item == "trigger" for item in components):
        return "triggered"
    if any(item in {"native_bucket", "native_dt"} for item in components):
        return "native-distance improvement"
    if any(item.startswith("root_signature") or item == "group_progress" for item in components):
        return "root-aligned state transition"
    if any(item in {"phase_novelty", "object_identity_confidence"} for item in components) or any(
        atom.category == "compound-sequence-lifecycle" for atom in tcir.atoms
    ):
        return "lifecycle-prefix improvement"
    if any(item.startswith("atom_progress") for item in components):
        return "lifted-feature improvement"
    return "influence-confidence improvement"


def progress_dominates_global(
    record: ReplayRecord,
    frontier: list[SeedProgressRecord],
    tcir: TCIR,
    plans: dict[str, AtomPlan],
    mode: str = "postreach_mode",
) -> tuple[bool, ProgressDecision, SeedProgressRecord]:
    seed_progress = seed_progress_record(record, tcir, plans)
    full = seed_progress.full_vector
    atom_id = tcir.atoms[0].atom_id if tcir.atoms else ""
    if not full.reached:
        decision = ProgressDecision(record.seed_id, False, "not_reached", atom_id, [], ["reach"], record.replay_stable, full.root_or_event_aligned, full.to_dict())
        return False, decision, seed_progress
    if not record.replay_stable and not record.triggered_T:
        decision = ProgressDecision(record.seed_id, False, "not_replay_stable", atom_id, [], ["replay_stability"], False, full.root_or_event_aligned, full.to_dict())
        return False, decision, seed_progress
    if not full.root_or_event_aligned and not record.triggered_T:
        decision = ProgressDecision(record.seed_id, False, "not_root_or_event_aligned", atom_id, [], ["root_alignment"], record.replay_stable, False, full.to_dict())
        return False, decision, seed_progress

    comparable = [item for item in frontier if item.comparable_key == seed_progress.comparable_key]
    regression_scope = [
        item
        for item in frontier
        if item.full_vector.target_context_hash == full.target_context_hash
        and item.full_vector.selected_branch == full.selected_branch
        and item.comparable_key.object_identity_bucket == seed_progress.comparable_key.object_identity_bucket
    ]
    if record.triggered_T:
        components = ["trigger", "native_bucket", "native_dt"]
        decision = ProgressDecision(record.seed_id, True, "triggered", atom_id, components, [], True, full.root_or_event_aligned, full.to_dict())
        return True, decision, seed_progress

    regressions = global_regressions(full, regression_scope, tcir)
    if regressions:
        if any("lifecycle_object_identity_weak" in item for item in regressions):
            reason = "insufficient_object_identity"
        elif any("guard" in item for item in regressions):
            reason = "regressed_higher_priority_atom"
        else:
            reason = "regressed_higher_priority_atom"
        decision = ProgressDecision(record.seed_id, False, reason, atom_id, [], regressions, record.replay_stable, full.root_or_event_aligned, full.to_dict())
        return False, decision, seed_progress

    if any(vector_dominated_by(full, old.full_vector, tcir) for old in comparable):
        decision = ProgressDecision(record.seed_id, False, "dominated_by_existing_frontier", atom_id, [], ["dominated"], record.replay_stable, full.root_or_event_aligned, full.to_dict())
        return False, decision, seed_progress

    improved = improved_components_global(full, comparable, tcir)
    coverage_only = improved == ["coverage"]
    if mode == "postreach_mode":
        improved = [item for item in improved if item != "coverage"]
    if not improved:
        reason = "coverage_only" if coverage_only else "no_tc_rooted_dominance"
        decision = ProgressDecision(record.seed_id, False, reason, atom_id, [], ["no_improved_component"], record.replay_stable, full.root_or_event_aligned, full.to_dict())
        return False, decision, seed_progress

    if all(atom.category == "generic" for atom in tcir.atoms):
        generic_ok = any(item.startswith("root_signature") or item in {"group_progress", "influence-confidence improvement"} for item in improved)
        if not generic_ok:
            decision = ProgressDecision(record.seed_id, False, "no_tc_rooted_dominance", atom_id, [], ["generic_strict_save"], record.replay_stable, full.root_or_event_aligned, full.to_dict())
            return False, decision, seed_progress

    reason = reason_for_global_components(improved, tcir)
    decision = ProgressDecision(record.seed_id, True, reason, atom_id, improved, [], record.replay_stable, full.root_or_event_aligned, full.to_dict())
    return True, decision, seed_progress


def progress_dominates(
    record: ReplayRecord,
    frontier: list[ProgressVector],
    atom: TCAtom,
    plan: AtomPlan,
) -> tuple[bool, ProgressDecision, ProgressVector]:
    vector = progress_vector(record, atom, plan)
    if not vector.reached:
        return (
            False,
            ProgressDecision(
                seed_id=record.seed_id,
                accepted=False,
                reason="reject:not_reached",
                atom_id=atom.atom_id,
                improved_components=[],
                rejected_components=["reach"],
                replay_verifiable=record.replay_stable,
                root_or_event_aligned=vector.root_or_event_aligned,
                vector=vector.to_dict(),
            ),
            vector,
        )
    if not record.replay_stable and not record.triggered_T:
        return (
            False,
            ProgressDecision(
                seed_id=record.seed_id,
                accepted=False,
                reason="reject:not_replay_stable",
                atom_id=atom.atom_id,
                improved_components=[],
                rejected_components=["replay_stability"],
                replay_verifiable=False,
                root_or_event_aligned=vector.root_or_event_aligned,
                vector=vector.to_dict(),
            ),
            vector,
        )
    if not vector.root_or_event_aligned and not record.triggered_T:
        return (
            False,
            ProgressDecision(
                seed_id=record.seed_id,
                accepted=False,
                reason="reject:not_root_or_event_aligned",
                atom_id=atom.atom_id,
                improved_components=[],
                rejected_components=["root_alignment"],
                replay_verifiable=record.replay_stable,
                root_or_event_aligned=False,
                vector=vector.to_dict(),
            ),
            vector,
        )

    same_atom = [item for item in frontier if item.atom_id == atom.atom_id]
    improved: list[str] = []
    rejected: list[str] = []
    for idx, component in enumerate(plan.priority_components):
        if component in {"reach"}:
            continue
        if component_improved(component, vector, same_atom):
            higher = plan.priority_components[:idx]
            regressions = [name for name in higher if component_regressed(name, vector, same_atom)]
            if regressions:
                rejected.extend(regressions)
                continue
            if component not in {"coverage"}:
                improved.append(component)
    if not improved:
        return (
            False,
            ProgressDecision(
                seed_id=record.seed_id,
                accepted=False,
                reason="reject:no_tc_rooted_dominance",
                atom_id=atom.atom_id,
                improved_components=[],
                rejected_components=sorted(set(rejected)) or ["no_improved_component"],
                replay_verifiable=record.replay_stable,
                root_or_event_aligned=vector.root_or_event_aligned,
                vector=vector.to_dict(),
            ),
            vector,
        )
    reason = reason_for_component(improved[0], atom.category)
    return (
        True,
        ProgressDecision(
            seed_id=record.seed_id,
            accepted=True,
            reason=reason,
            atom_id=atom.atom_id,
            improved_components=improved,
            rejected_components=sorted(set(rejected)),
            replay_verifiable=record.replay_stable or record.triggered_T,
            root_or_event_aligned=vector.root_or_event_aligned,
            vector=vector.to_dict(),
        ),
        vector,
    )


def constants_from_expression(expression: str) -> list[bytes]:
    constants: list[bytes] = []
    for match in re.findall(r"0x[0-9A-Fa-f]+|\b\d+\b", expression):
        try:
            value = int(match, 0)
        except ValueError:
            continue
        widths = [1, 2, 4, 8]
        for width in widths:
            if value < 1 << (8 * width):
                constants.append(value.to_bytes(width, "little", signed=False))
                constants.append(value.to_bytes(width, "big", signed=False))
                break
    for match in re.findall(r'"([^"]+)"|\'([^\']+)\'', expression):
        token = next((part for part in match if part), "")
        if token:
            constants.append(token.encode("utf-8", errors="ignore"))
    unique: list[bytes] = []
    for item in constants:
        if item and item not in unique:
            unique.append(item)
    return unique[:16]


def operator_family(operator_name: str, category: str) -> str:
    for item in registry().get(category, registry()["generic"])["mutators"]:
        if item["name"] == operator_name:
            return item.get("operator_family", "generic_local")
    for item in registry()["generic"]["mutators"]:
        if item["name"] == operator_name:
            return item.get("operator_family", "generic_local")
    return "generic_local"


def canonical_operator_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def confidence_to_float(value: Any) -> float:
    if isinstance(value, (int, float)):
        return max(0.0, min(1.0, float(value)))
    text = str(value or "").strip().lower()
    try:
        return max(0.0, min(1.0, float(text)))
    except ValueError:
        pass
    return {
        "none": 0.0,
        "unknown": 0.0,
        "low": 0.25,
        "medium": 0.5,
        "high": 0.8,
        "verified": 1.0,
    }.get(text, 0.0)


def candidate_range_records(record: ReplayRecord, data_len: int, graph: TriggerProgressGraph) -> list[dict[str, Any]]:
    ranges: list[dict[str, Any]] = []
    for item in graph.nodes:
        if item.get("type") != "candidate_input_influence_range":
            continue
        if item.get("seed_id") != record.seed_id:
            continue
        start = as_int(item.get("start"), 0)
        length = as_int(item.get("length"), 0)
        if 0 <= start < data_len and length > 0:
            label = item.get("confidence", "low")
            ranges.append(
                {
                    "start": start,
                    "length": min(length, data_len - start),
                    "confidence_label": label,
                    "confidence": confidence_to_float(label),
                    "runtime_event_id": item.get("runtime_event_id", ""),
                    "source": "trigger_progress_graph",
                }
            )
    if not ranges and data_len:
        ranges.append(
            {
                "start": 0,
                "length": min(data_len, 4096),
                "confidence_label": "low",
                "confidence": 0.1,
                "runtime_event_id": "",
                "source": "whole_input_fallback",
            }
        )
    return ranges[:8]


def propose_mutations(
    target_id: str,
    atom: TCAtom,
    plan: AtomPlan,
    record: ReplayRecord,
    seed_path: Path,
    graph: TriggerProgressGraph,
    max_proposals: int,
) -> list[tuple[MutationProposal, bytes | None]]:
    if not seed_path.exists() or max_proposals <= 0:
        return []
    data = seed_path.read_bytes()
    if not data:
        data = b"\x00"
    ranges = candidate_range_records(record, len(data), graph)
    if plan.plan_reason.startswith("native_tc_dgf_native_dt_generic_mutation_only"):
        ranges = [
            {
                "start": 0,
                "length": min(len(data), 4096),
                "confidence_label": "low",
                "confidence": 0.1,
                "runtime_event_id": "",
                "source": "native_tc_dgf_whole_input_generic",
            }
        ]
    constants = constants_from_expression(atom.expression)
    proposals: list[tuple[MutationProposal, bytes | None]] = []

    def add(
        operator: str,
        mutated: bytes,
        range_record: dict[str, Any],
        start: int,
        length: int,
        details: dict[str, Any] | None = None,
    ) -> None:
        if len(proposals) >= max_proposals:
            return
        proposal_id = f"m:{atom.atom_id}:{len(proposals):06d}:{stable_id(record.seed_id, atom.atom_id, operator, len(proposals))}"
        family = operator_family(operator, atom.category)
        detail_payload = details or {}
        detail_payload.setdefault("operator_family", family)
        detail_payload.setdefault("precondition", evaluate_operator_preconditions(operator, atom, record, graph))
        detail_payload.setdefault("influence_confidence", confidence_to_float(range_record.get("confidence")))
        detail_payload.setdefault("influence_confidence_label", range_record.get("confidence_label", "unknown"))
        detail_payload.setdefault("range_source", range_record.get("source", "unknown"))
        detail_payload.setdefault("runtime_event_id", range_record.get("runtime_event_id", ""))
        proposals.append(
            (
                MutationProposal(
                    proposal_id=proposal_id,
                    target_id=target_id,
                    atom_id=atom.atom_id,
                    operator_name=operator,
                    seed_id=record.seed_id,
                    source_path=str(seed_path),
                    mutated_ranges=[
                        {
                            "start": start,
                            "len": length,
                            "confidence": detail_payload["influence_confidence"],
                            "confidence_label": detail_payload["influence_confidence_label"],
                            "runtime_event_id": detail_payload["runtime_event_id"],
                        }
                    ],
                    executed=False,
                    replay_verifiable=None,
                    changed_target_root_event=None,
                    kept=None,
                    keep_reason="not_executed",
                    details=detail_payload,
                ),
                mutated,
            )
        )

    def add_skipped(operator: str, precondition: dict[str, Any]) -> None:
        if len(proposals) >= max_proposals:
            return
        proposal_id = f"m:{atom.atom_id}:{len(proposals):06d}:{stable_id(record.seed_id, atom.atom_id, operator, 'skip')}"
        proposals.append(
            (
                MutationProposal(
                    proposal_id=proposal_id,
                    target_id=target_id,
                    atom_id=atom.atom_id,
                    operator_name=operator,
                    seed_id=record.seed_id,
                    source_path=str(seed_path),
                    mutated_ranges=[],
                    executed=False,
                    replay_verifiable=None,
                    changed_target_root_event=None,
                    kept=False,
                    keep_reason="precondition_not_satisfied",
                    details={
                        "operator_family": operator_family(operator, atom.category),
                        "precondition": precondition,
                        "influence_confidence": 0.0,
                        "influence_confidence_label": "none",
                    },
                ),
                None,
            )
        )

    for operator in plan.mutator_operators:
        op = canonical_operator_name(operator)
        precondition = evaluate_operator_preconditions(operator, atom, record, graph)
        if not precondition["satisfied"]:
            add_skipped(operator, precondition)
            continue
        for range_record in ranges:
            if len(proposals) >= max_proposals:
                break
            start = as_int(range_record.get("start"), 0)
            length = as_int(range_record.get("length"), 0)
            end = start + length
            buf = bytearray(data)
            local_start = start
            if op in {"boundary_write", "operand_replacement", "dictionary_insertion", "token_replacement"}:
                values = constants or [b"\x00", b"\x01", b"\xff", b"\x7f", b"\x80"]
                for value in values[:3]:
                    buf = bytearray(data)
                    pos = min(local_start, len(buf))
                    if op == "dictionary_insertion":
                        buf[pos:pos] = value
                    else:
                        write_len = min(len(value), max(1, len(buf) - pos))
                        buf[pos : pos + write_len] = value[:write_len]
                    add(
                        operator,
                        bytes(buf),
                        range_record,
                        pos,
                        max(1, min(len(value), len(buf) - pos)),
                        {"constant": value.hex()},
                    )
                    if len(proposals) >= max_proposals:
                        break
            elif op in {"arithmetic_perturbation", "numeric_byte_increment", "guard_field_perturbation", "error_path_induction", "phase_preserving_mutation"}:
                pos = min(local_start, len(buf) - 1)
                if op == "error_path_induction":
                    buf[pos:min(end, pos + 8, len(buf))] = b"\x00" * max(1, min(end, pos + 8, len(buf)) - pos)
                else:
                    buf[pos] = (buf[pos] + 1) & 0xFF
                add(operator, bytes(buf), range_record, pos, 1)
            elif op == "endian_variants":
                if local_start + 4 <= len(buf):
                    buf[local_start : local_start + 4] = reversed(buf[local_start : local_start + 4])
                    add(operator, bytes(buf), range_record, local_start, 4)
            elif op in {"generic_byte_perturbation", "generic_byte_increment", "generic_byte_decrement", "generic_token_insertion", "generic_region_deletion"}:
                pos = min(local_start, len(buf) - 1)
                if op == "generic_byte_perturbation":
                    buf[pos] ^= 0x1
                    add(operator, bytes(buf), range_record, pos, 1)
                elif op == "generic_byte_increment":
                    buf[pos] = (buf[pos] + 1) & 0xFF
                    add(operator, bytes(buf), range_record, pos, 1)
                elif op == "generic_byte_decrement":
                    buf[pos] = (buf[pos] - 1) & 0xFF
                    add(operator, bytes(buf), range_record, pos, 1)
                elif op == "generic_token_insertion":
                    buf[pos:pos] = b"\x00"
                    add(operator, bytes(buf), range_record, pos, 1)
                else:
                    delete_len = max(1, min(length, 16, len(buf) - pos))
                    del buf[pos : pos + delete_len]
                    add(operator, bytes(buf), range_record, pos, delete_len)
            elif op in {"optional_region_deletion", "initialization_bypass_mutation", "reset_cleanup_path_mutation", "event_deletion"}:
                delete_len = max(1, min(length, 32, len(buf) - local_start))
                del buf[local_start : local_start + delete_len]
                add(operator, bytes(buf), range_record, local_start, delete_len)
            elif op in {"event_insertion", "event_duplication"}:
                chunk = bytes(buf[local_start : min(end, local_start + 16)]) or b"\x00"
                buf[local_start:local_start] = chunk
                add(operator, bytes(buf), range_record, local_start, len(chunk))
            elif op == "object_identity_alignment":
                id_pos = local_start + 1 if local_start + 1 < len(buf) else local_start
                candidates: list[tuple[int, int, str]] = []
                if id_pos - 2 >= 0:
                    candidates.append((id_pos, buf[id_pos - 2], "copy_previous_event_id"))
                if id_pos + 2 < len(buf):
                    candidates.append((id_pos, buf[id_pos + 2], "copy_next_event_id"))
                for pos, value, strategy in candidates[:2]:
                    if len(proposals) >= max_proposals:
                        break
                    buf = bytearray(data)
                    buf[pos] = value
                    add(operator, bytes(buf), range_record, pos, 1, {"strategy": strategy, "value": int(value)})
            elif op == "event_reordering":
                span = min(length, 32, len(buf) - local_start)
                if span >= 4:
                    half = span // 2
                    buf[local_start : local_start + span] = (
                        buf[local_start + half : local_start + span] + buf[local_start : local_start + half]
                    )
                    add(operator, bytes(buf), range_record, local_start, span)
            elif op == "repair_hook":
                add(operator, bytes(buf), range_record, local_start, 0, {"configured": False})
    return proposals[:max_proposals]


def atom_progress_record(
    record: ReplayRecord,
    atom: TCAtom,
    plan: AtomPlan,
    graph: TriggerProgressGraph | None = None,
    tcir: TCIR | None = None,
) -> dict[str, Any]:
    vec = progress_vector(record, atom, plan, tcir)
    observation = atom_observation(record, atom, tcir)
    root_events: list[dict[str, Any]] = []
    producer_state = {"producer": record.producer, "observed": bool(record.producer)}
    use_state = {"use_reached": record.reached_R, "source": "replay_metadata"}
    influence_ranges: list[dict[str, Any]] = []
    if graph is not None:
        for item in graph.nodes:
            if item.get("type") == "candidate_input_influence_range" and item.get("seed_id") == record.seed_id:
                influence_ranges.append(
                    {
                        "start": item.get("start"),
                        "len": item.get("length"),
                        "confidence_label": item.get("confidence", "low"),
                        "confidence": confidence_to_float(item.get("confidence", "low")),
                        "runtime_event_id": item.get("runtime_event_id", ""),
                    }
                )
            if item.get("type") == "root_variable_or_event" and item.get("atom_id") == atom.atom_id:
                root_events.append(
                    {
                        "label": item.get("label"),
                        "source_location": item.get("source_location"),
                        "confidence": item.get("confidence", "low"),
                    }
                )
    return {
        "atom_id": atom.atom_id,
        "atom_type": atom.category,
        "native_DT_raw": record.native_DT,
        "native_DT_bucket": record.dt_bucket,
        "native_actionable": plan.use_native_dt,
        "lifted_features": {
            "enabled": plan.use_lifted_features,
            "extractors": plan.feature_extractors,
            "plan_reason": plan.plan_reason,
        },
        "root_state": record.tc_root_state,
        "observation": observation.to_dict(),
        "observation_status": observation.status,
        "root_events": root_events,
        "producer_state": producer_state,
        "use_state": use_state,
        "lifecycle_prefix": vec.lifecycle_prefix,
        "object_identity_confidence": vec.object_identity_confidence,
        "next_event_reachability": vec.next_event_reachability,
        "phase_novelty": vec.phase_novelty,
        "equality_match": None,
        "numeric_margin": record.native_DT if atom.category == "numeric-margin" else None,
        "influence_ranges": influence_ranges,
        "progress_vector": vec.to_dict(),
    }


def build_progress_record(
    record: ReplayRecord,
    atoms: list[TCAtom],
    plans: dict[str, AtomPlan],
    graph: TriggerProgressGraph | None,
    decision: ProgressDecision | None = None,
    mutation: MutationProposal | None = None,
    non_dominated_rank: int = 0,
    tcir: TCIR | None = None,
    seed_progress: SeedProgressRecord | None = None,
) -> ProgressRecord:
    if tcir is None:
        tcir = TCIR(
            target_id=record.target_id,
            expression=" && ".join(atom.expression for atom in atoms),
            root_group_id="compat",
            atoms=atoms,
            groups=[TCGroup("compat", "ALL_OF", [atom.atom_id for atom in atoms])],
            nodes=[],
            edges=[],
            source_locations=[],
        )
    if seed_progress is None:
        seed_progress = seed_progress_record(record, tcir, plans, non_dominated_rank)
    atom_rows = [atom_progress_record(record, atom, plans[atom.atom_id], graph, tcir) for atom in atoms]
    execution = {
        "R": record.reached_R,
        "T": record.triggered_T,
        "target_context_hash": str(record.raw.get("target_context_hash") or stable_id(record.target_id, "target_context")),
        "coverage_hash": record.coverage_hash,
        "crash_oracle": record.triggered_T,
        "replay_stable": record.replay_stable,
    }
    novelty_reasons: list[str] = []
    regression_flags: list[str] = []
    progress_vector: dict[str, Any] = {}
    progress_vector_by_atom = {
        str(row.get("atom_id", "")): row.get("progress_vector", {})
        for row in atom_rows
    }
    if decision is not None:
        if decision.accepted:
            novelty_reasons.append(decision.reason)
        regression_flags.extend(decision.rejected_components)
        progress_vector = decision.vector
    mutation_payload = {
        "parent_seed_id": record.parent_seed_id,
        "mutation_operator": "",
        "mutated_ranges": [],
        "influence_confidence": 0.0,
    }
    if mutation is not None:
        influence_confidence = confidence_to_float(mutation.details.get("influence_confidence", 0.0))
        if not influence_confidence and mutation.mutated_ranges:
            influence_confidence = max(confidence_to_float(item.get("confidence", 0.0)) for item in mutation.mutated_ranges)
        mutation_payload = {
            "parent_seed_id": mutation.seed_id,
            "mutation_operator": mutation.operator_name,
            "mutated_ranges": mutation.mutated_ranges,
            "influence_confidence": influence_confidence,
            "operator_family": mutation.details.get("operator_family", ""),
            "changed_target_root_event": mutation.changed_target_root_event,
            "kept": mutation.kept,
            "keep_reason": mutation.keep_reason,
            "operator_effect": mutation.details.get("operator_effect", {}),
        }
    return ProgressRecord(
        seed_id=record.seed_id,
        parent_id=record.parent_seed_id,
        input_hash=record.content_sha256,
        execution=execution,
        atoms=atom_rows,
        global_progress={
            "schema": "formtrig-progress-record-v3",
            "progress_vector": progress_vector,
            "full_progress_vector": seed_progress.full_vector.to_dict(),
            "group_progress": seed_progress.full_vector.group_progress,
            "progress_vector_by_atom": progress_vector_by_atom,
            "selected_branch": seed_progress.full_vector.selected_branch,
            "branch_scores": seed_progress.full_vector.branch_scores,
            "non_dominated_rank": non_dominated_rank,
            "novelty_reasons": novelty_reasons,
            "regression_flags": sorted(set(regression_flags)),
        },
        mutation=mutation_payload,
    )


def mutation_operator_effect(parent: ReplayRecord, child: ReplayRecord, decision: ProgressDecision) -> dict[str, Any]:
    parent_parsed = parse_root_state(parent.tc_root_state)
    child_parsed = parse_root_state(child.tc_root_state)
    changed_keys = sorted(
        key
        for key in set(parent_parsed) | set(child_parsed)
        if parent_parsed.get(key) != child_parsed.get(key)
    )
    producer_keys = [key for key in changed_keys if "producer" in key.lower() or "init" in key.lower() or "alloc" in key.lower()]
    use_keys = [key for key in changed_keys if "use" in key.lower() or "sink" in key.lower()]
    parent_prefix = lifecycle_prefix_score(parent.tc_root_state)
    child_prefix = lifecycle_prefix_score(child.tc_root_state)
    parent_object_identity = object_identity_confidence_from_state(parent.tc_root_state)
    child_object_identity = object_identity_confidence_from_state(child.tc_root_state)
    return {
        "changed_root_state": bool(changed_keys),
        "changed_root_keys": changed_keys,
        "changed_producer_state": bool(producer_keys),
        "changed_producer_keys": producer_keys,
        "changed_use_context": bool(use_keys),
        "changed_use_keys": use_keys,
        "changed_lifecycle_prefix": child_prefix != parent_prefix,
        "changed_object_identity_confidence": child_object_identity != parent_object_identity,
        "parent_object_identity_confidence": parent_object_identity,
        "child_object_identity_confidence": child_object_identity,
        "parent_lifecycle_prefix": parent_prefix,
        "child_lifecycle_prefix": child_prefix,
        "preserved_reach": child.reached_R,
        "improved_atom": decision.atom_id if decision.accepted else "",
        "improved_components": decision.improved_components,
        "triggered": child.triggered_T,
    }


def seed_path_for_record(seed_dir: Path, record: ReplayRecord) -> Path:
    exact = seed_dir / record.seed_id
    if exact.exists():
        return exact
    if record.content_sha256:
        matches = sorted(seed_dir.glob(f"*{record.content_sha256[:16]}*"))
        if matches:
            return matches[0]
    matches = sorted(seed_dir.glob(f"{record.seed_id.split(',', 1)[0]}*"))
    if matches:
        return matches[0]
    return exact


def parse_target_cmd(template: str, input_path: Path) -> list[str]:
    return shlex.split(template.replace("@@", str(input_path)))


def target_cmd_uses_shell(template: str) -> bool:
    return any(token in template for token in ["&&", "||", ";", "=", "$(", "`"]) or template.strip().startswith(("cd ", "env "))


def json_records(text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            out.append(value)
    return out


def normalize_runtime_signal(stdout: str, stderr: str, returncode: int, elapsed_s: float) -> dict[str, Any]:
    records = json_records(stdout) + json_records(stderr)
    last = records[-1] if records else {}
    combined = f"{stdout}\n{stderr}"
    sanitizer_error = any(
        marker in combined
        for marker in [
            "ERROR: AddressSanitizer",
            "AddressSanitizer:",
            "UndefinedBehaviorSanitizer",
            "runtime error:",
            "SUMMARY: AddressSanitizer",
        ]
    )
    return {
        "returncode": returncode,
        "elapsed_s": elapsed_s,
        "json_records": len(records),
        "sanitizer_error": sanitizer_error,
        "reached": last.get("reached"),
        "triggered": last.get("triggered", last.get("crash_predicate")),
        "native_DT": last.get("D_T", last.get("d_t")),
        "lifted_DF": last.get("D_F", last.get("d_f", last.get("d_f_lifted"))),
        "root_state": last.get("root_state", last.get("state_hash", "")),
        "trace_signature": last.get("trace_signature", ""),
        "df_source": last.get("df_source"),
        "hot_ranges": last.get("hot_ranges", last.get("hot_byte_ranges", [])),
        "debug_events": last.get("debug_events", []),
    }


def run_target_cmd(target_cmd: str, data: bytes, timeout_s: float) -> dict[str, Any]:
    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(data)
        input_path = Path(f.name)
    start = time.time()
    try:
        proc = subprocess.run(
            target_cmd.replace("@@", str(input_path)) if target_cmd_uses_shell(target_cmd) else parse_target_cmd(target_cmd, input_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            timeout=timeout_s,
            check=False,
            shell=target_cmd_uses_shell(target_cmd),
        )
        return normalize_runtime_signal(proc.stdout, proc.stderr, proc.returncode, time.time() - start)
    except subprocess.TimeoutExpired as exc:
        return normalize_runtime_signal(str(exc.stdout or ""), str(exc.stderr or ""), 124, time.time() - start)
    finally:
        try:
            input_path.unlink()
        except OSError:
            pass


def target_meta_from_inventories(target_id: str, inventory_paths: list[Path]) -> dict[str, str]:
    for path in inventory_paths:
        for row in read_csv(path):
            if row.get("target_id") == target_id:
                meta = dict(row)
                if "canary_expression" not in meta and "tc_annotation" in meta:
                    meta["canary_expression"] = meta.get("tc_annotation", "")
                if "primary_tc_category" not in meta and "tc_category" in meta:
                    meta["primary_tc_category"] = meta.get("tc_category", "")
                return meta
    return {"target_id": target_id}


def expression_from_meta(meta: dict[str, str]) -> str:
    return (
        meta.get("canary_expression")
        or meta.get("tc_annotation")
        or meta.get("trigger_oracle")
        or meta.get("target_id")
        or "<missing TC expression>"
    )


def category_from_meta(meta: dict[str, str], fallback: str = "numeric-margin") -> str:
    value = meta.get("primary_tc_category") or meta.get("tc_category") or fallback
    return value if value in TC_CATEGORIES else fallback


def source_location_from_meta(meta: dict[str, str]) -> str:
    return (
        meta.get("target_location")
        or meta.get("observation_point")
        or f"{meta.get('source_file', '')}:{meta.get('source_line', '')}".strip(":")
        or "unknown"
    )


def load_replay_records(metadata_csv: Path) -> list[ReplayRecord]:
    return [replay_record_from_row(row) for row in read_csv(metadata_csv)]
