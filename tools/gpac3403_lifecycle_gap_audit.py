#!/usr/bin/env python3
"""Audit the remaining GPAC_3403 lifecycle gap after retained typed mutations."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROLE_NAMES = {
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

ATOM_SIGNAL_HAS_OBJECT_ID = 1 << 2
PARSER_PROXIMITY_SIGNATURES = {
    "vps_max_layer_id",
    "video_param_set_error",
    "nal_type_32_error",
    "nal_type_49_not_handled",
    "track_importing_hevc",
    "hevc_import_results",
    "lhevc_import_results",
    "wrong_output_layer_sets",
    "failed_vps_extensions",
    "layers_only_4",
}
TERMINAL_SIGNATURES = {"asan", "asan_double_free"}


def read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def clean_scalar(value: str) -> str:
    value = value.strip()
    if "#" in value:
        value = value.split("#", 1)[0].strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def parse_scalar_line(line: str) -> tuple[str, str] | None:
    if ":" not in line:
        return None
    key, value = line.split(":", 1)
    return key.strip(), clean_scalar(value)


def parse_binding_spec(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}

    spec: dict[str, Any] = {
        "path": str(path),
        "tc_id": None,
        "category": None,
        "expression": None,
        "role_bindings": [],
        "same_object_relations": [],
    }
    in_bindings = False
    current: dict[str, Any] | None = None

    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped == "bindings:":
            in_bindings = True
            continue
        parsed = parse_scalar_line(stripped)
        if not parsed:
            continue
        key, value = parsed

        if not in_bindings:
            if key == "tc_id":
                spec["tc_id"] = value
            elif key == "category" and spec["category"] is None:
                spec["category"] = value
            elif key == "expression" and spec["expression"] is None:
                spec["expression"] = value
            continue

        if stripped.startswith("- id:"):
            if current:
                spec["role_bindings"].append(current)
                if current.get("role") == "same_object":
                    spec["same_object_relations"].append(
                        {
                            "binding_id": current.get("id"),
                            "relation_from": current.get("relation_from"),
                            "relation_to": current.get("relation_to"),
                            "object_expr": current.get("object_expr"),
                            "site_id": current.get("site_id"),
                        }
                    )
            current = {"id": value}
            continue
        if current is None:
            continue
        if key in {
            "role",
            "expr",
            "site_id",
            "component",
            "priority",
            "direction",
            "value_mode",
            "relation_from",
            "relation_to",
            "object_expr",
        }:
            current[key] = value

    if current:
        spec["role_bindings"].append(current)
        if current.get("role") == "same_object":
            spec["same_object_relations"].append(
                {
                    "binding_id": current.get("id"),
                    "relation_from": current.get("relation_from"),
                    "relation_to": current.get("relation_to"),
                    "object_expr": current.get("object_expr"),
                    "site_id": current.get("site_id"),
                }
            )

    role_counts = Counter(
        binding.get("role")
        for binding in spec["role_bindings"]
        if binding.get("role")
    )
    spec["roles"] = sorted(role_counts)
    spec["role_counts"] = dict(sorted(role_counts.items()))
    return spec


def role_bit(role: int) -> int:
    return 1 << (role - 1) if role > 0 else 0


def role_names_from_bits(bits: Any) -> list[str]:
    try:
        parsed = int(bits)
    except (TypeError, ValueError):
        return []
    return [
        name
        for role, name in ROLE_NAMES.items()
        if parsed & role_bit(role)
    ]


def role_name(role: Any) -> str:
    try:
        return ROLE_NAMES.get(int(role), "unknown")
    except (TypeError, ValueError):
        return "unknown"


def numeric(value: Any) -> float | int | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        parsed = float(str(value).strip())
    except ValueError:
        return None
    return int(parsed) if parsed.is_integer() else parsed


def read_progress(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    events = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                events.append(payload)
    return events


def summarize_progress(events: list[dict[str, Any]]) -> dict[str, Any]:
    event_counts = Counter(str(event.get("event")) for event in events)
    d_f_spec_values: list[float | int] = []
    same_object_component_values: list[Any] = []
    same_object_atom_signal_events = 0
    same_object_object_id_events = 0
    role_component_counts: Counter[str] = Counter()
    atom_signal_role_counts: Counter[str] = Counter()

    for event in events:
        value = numeric(event.get("d_f_spec_lifted"))
        if value is not None:
            d_f_spec_values.append(value)

        for component in event.get("component_values", []) or []:
            if not isinstance(component, dict):
                continue
            role = role_name(component.get("role"))
            role_component_counts[role] += 1
            if role == "same_object":
                same_object_component_values.append(component.get("value"))

        for signal in event.get("atom_signal_values", []) or []:
            if not isinstance(signal, dict):
                continue
            roles = signal.get("roles")
            if not isinstance(roles, list):
                roles = role_names_from_bits(signal.get("role_bits"))
            for role in roles:
                atom_signal_role_counts[str(role)] += 1
            if "same_object" in roles:
                same_object_atom_signal_events += 1
                flags = int(numeric(signal.get("flags")) or 0)
                object_id_bucket = numeric(signal.get("object_id_bucket"))
                if (flags & ATOM_SIGNAL_HAS_OBJECT_ID) or object_id_bucket not in (None, 0):
                    same_object_object_id_events += 1

    return {
        "events": len(events),
        "event_counts": dict(sorted(event_counts.items())),
        "d_f_spec_lifted_values": sorted(set(d_f_spec_values)),
        "d_f_spec_lifted_min": min(d_f_spec_values) if d_f_spec_values else None,
        "d_f_spec_lifted_max": max(d_f_spec_values) if d_f_spec_values else None,
        "role_component_counts": dict(sorted(role_component_counts.items())),
        "atom_signal_role_counts": dict(sorted(atom_signal_role_counts.items())),
        "same_object_component_samples": len(same_object_component_values),
        "same_object_component_unique_values": len(
            {str(value) for value in same_object_component_values}
        ),
        "same_object_component_value_examples": [
            value for value in same_object_component_values[:8]
        ],
        "same_object_atom_signal_events": same_object_atom_signal_events,
        "same_object_object_id_events": same_object_object_id_events,
    }


def summarize_binding_signal(signal: dict[str, Any]) -> dict[str, Any]:
    atoms = []
    role_totals: Counter[str] = Counter()
    constant_roles = []
    sparse_roles = []
    same_object_roles = []

    for atom in signal.get("atoms", []) or []:
        if not isinstance(atom, dict):
            continue
        roles = []
        for role in atom.get("roles", []) or []:
            if not isinstance(role, dict):
                continue
            name = str(role.get("role") or "unknown")
            role_totals[name] += int(numeric(role.get("samples")) or 0)
            compact = {
                "role": name,
                "samples": role.get("samples"),
                "candidate_samples": role.get("candidate_samples"),
                "unique_values": role.get("unique_values"),
                "candidate_unique_values": role.get("candidate_unique_values"),
                "values": role.get("values", [])[:8],
                "candidate_values": role.get("candidate_values", [])[:8],
            }
            roles.append(compact)
            unique_values = int(numeric(role.get("unique_values")) or 0)
            candidate_unique = int(numeric(role.get("candidate_unique_values")) or 0)
            samples = int(numeric(role.get("samples")) or 0)
            candidates = int(numeric(role.get("candidate_samples")) or 0)
            if samples and unique_values <= 1 and candidate_unique <= 1:
                constant_roles.append(name)
            if samples <= 2 or candidates <= 1:
                sparse_roles.append(name)
            if name == "same_object":
                same_object_roles.append(compact)
        atoms.append(
            {
                "atom_id": atom.get("atom_id"),
                "category": atom.get("category"),
                "diagnosis": atom.get("diagnosis"),
                "bound_roles": atom.get("bound_roles", []),
                "sampled_roles": atom.get("sampled_roles", []),
                "candidate_sampled_roles": atom.get("candidate_sampled_roles", []),
                "variable_roles": atom.get("variable_roles", []),
                "candidate_variable_roles": atom.get("candidate_variable_roles", []),
                "roles": roles,
            }
        )

    return {
        "status": signal.get("status"),
        "diagnosis": signal.get("diagnosis"),
        "spec_role_samples": signal.get("spec_role_samples"),
        "spec_role_candidate_samples": signal.get("spec_role_candidate_samples"),
        "spec_d_f_samples": signal.get("spec_d_f_samples"),
        "spec_d_f_candidate_samples": signal.get("spec_d_f_candidate_samples"),
        "non_trigger_candidate_lift_delta": signal.get("non_trigger_candidate_lift_delta"),
        "atoms": atoms,
        "role_sample_totals": dict(sorted(role_totals.items())),
        "constant_roles": sorted(set(constant_roles)),
        "sparse_roles": sorted(set(sparse_roles)),
        "same_object_roles": same_object_roles,
    }


def endpoint_report(payload: dict[str, Any]) -> dict[str, Any]:
    if "endpoint_audit" in payload:
        audit = payload.get("endpoint_audit")
        if isinstance(audit, dict) and isinstance(audit.get("report"), dict):
            return audit["report"]
    if "contrast" in payload and "variant" in payload:
        return payload
    return {}


def summarize_endpoint(payload: dict[str, Any]) -> dict[str, Any]:
    report = endpoint_report(payload)
    contrast = report.get("contrast", {}) if isinstance(report, dict) else {}
    top_variants = contrast.get("top_variants_by_positive_overlap", []) or []
    top_variant = top_variants[0] if top_variants else {}
    variant_metrics = (
        report.get("variant", {}).get("metrics", {}) if isinstance(report, dict) else {}
    )
    positive_metrics = (
        report.get("positive_control", {}).get("metrics", {})
        if isinstance(report, dict)
        else {}
    )

    matched = set(top_variant.get("matched_positive_signatures", []) or [])
    positive_only = set(
        contrast.get("positive_control_signatures_absent_from_variants", []) or []
    )
    parser_proximity = bool(matched & PARSER_PROXIMITY_SIGNATURES) or bool(
        numeric(variant_metrics.get("hevc_import_files"))
    )
    variant_terminal = bool(numeric(variant_metrics.get("asan_double_free_files"))) or (
        bool(TERMINAL_SIGNATURES & matched) and not TERMINAL_SIGNATURES <= positive_only
    )

    return {
        "available": bool(report),
        "variant_files": contrast.get("variant_files"),
        "positive_control_files": contrast.get("positive_control_files"),
        "positive_control_signatures_absent_from_variants": sorted(positive_only),
        "top_variant": {
            key: top_variant.get(key)
            for key in [
                "variant_index",
                "matched_positive_signatures",
                "missing_positive_signatures",
                "matched_positive_signature_count",
                "weighted_match_score",
                "weighted_missing_score",
                "matched_values",
                "path",
            ]
            if key in top_variant
        },
        "variant_metrics": {
            key: variant_metrics.get(key)
            for key in [
                "hevc_import_files",
                "hevc_samples_max",
                "hevc_nalus_max",
                "lhevc_import_files",
                "asan_double_free_files",
            ]
            if key in variant_metrics
        },
        "positive_control_metrics": {
            key: positive_metrics.get(key)
            for key in [
                "hevc_import_files",
                "hevc_samples_max",
                "hevc_nalus_max",
                "lhevc_import_files",
                "asan_double_free_files",
            ]
            if key in positive_metrics
        },
        "parser_proximity_observed": parser_proximity,
        "terminal_observed_in_variants": variant_terminal,
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    binding = parse_binding_spec(args.binding_spec)
    signal = summarize_binding_signal(read_json(args.binding_diagnosis))
    progress = summarize_progress(read_progress(args.progress_jsonl))
    summary = read_json(args.summary_json)
    endpoint = summarize_endpoint(read_json(args.endpoint_package))

    same_object_needed = bool(binding.get("same_object_relations"))
    same_object_signal = bool(signal.get("same_object_roles")) or (
        progress.get("same_object_component_samples", 0) > 0
    )
    same_object_sparse = "same_object" in signal.get("sparse_roles", [])
    same_object_constant = "same_object" in signal.get("constant_roles", [])
    relation_runtime_proof = False
    terminal_observed = bool(endpoint.get("terminal_observed_in_variants")) or bool(
        numeric(summary.get("formtrig_triggered_execs"))
    )
    parser_proximity = bool(endpoint.get("parser_proximity_observed"))

    if terminal_observed:
        status = "terminal_trigger_reached"
        primary_gap = None
    elif parser_proximity and same_object_needed and not relation_runtime_proof:
        status = "parser_proximity_without_alias_terminal"
        primary_gap = "same_object_relation_semantics_missing"
    elif parser_proximity:
        status = "parser_proximity_without_terminal"
        primary_gap = "terminal_gap_unclassified"
    else:
        status = "insufficient_parser_proximity"
        primary_gap = "parser_reachability_gap"

    return {
        "schema": "formtrig_gpac3403_lifecycle_gap_audit_v1",
        "inputs": {
            "binding_spec": str(args.binding_spec) if args.binding_spec else None,
            "binding_diagnosis": str(args.binding_diagnosis)
            if args.binding_diagnosis
            else None,
            "progress_jsonl": str(args.progress_jsonl) if args.progress_jsonl else None,
            "summary_json": str(args.summary_json) if args.summary_json else None,
            "endpoint_package": str(args.endpoint_package)
            if args.endpoint_package
            else None,
        },
        "binding_spec": binding,
        "runtime_signal": {
            "binding_signal": signal,
            "progress": progress,
            "summary": {
                key: summary.get(key)
                for key in [
                    "execs_done",
                    "formtrig_reached_execs",
                    "terminal_triggered_execs",
                    "formtrig_triggered_execs",
                    "formtrig_queued_progress",
                    "formtrig_saved_non_trigger_log_seen",
                    "d_f_spec_lifted_min",
                    "d_f_spec_lifted_max",
                    "d_f_spec_lifted_count",
                    "has_role_signal",
                    "has_tc_rooted_progress",
                ]
                if key in summary
            },
        },
        "endpoint_evidence": endpoint,
        "verdict": {
            "status": status,
            "primary_gap": primary_gap,
            "parser_proximity_observed": parser_proximity,
            "terminal_observed_in_variants": terminal_observed,
            "same_object_relation_declared": same_object_needed,
            "same_object_signal_observed": same_object_signal,
            "same_object_signal_sparse": same_object_sparse,
            "same_object_signal_constant": same_object_constant,
            "same_object_relation_runtime_proof": relation_runtime_proof,
            "guidance_effect": {
                "r_to_parser_neighborhood": parser_proximity,
                "r_to_lifecycle_alias_terminal": terminal_observed,
                "d_f_has_non_trigger_delta": bool(
                    signal.get("non_trigger_candidate_lift_delta")
                )
                or progress.get("d_f_spec_lifted_min")
                != progress.get("d_f_spec_lifted_max"),
            },
            "interpretation": (
                "Typed mutations and lifted D_F reached GPAC HEVC/LHEVC parser "
                "neighborhoods, but the current runtime evidence does not prove "
                "the same GF_ISOSample data pointer is later freed through "
                "GF_BitStream->original."
            ),
        },
        "next_actions": [
            "Bind relation-aware events for sample->data allocation/release and GF_BitStream->original cleanup.",
            "Score same_object by matching object identity across lifecycle_event and use endpoints, not by a single pointer observation.",
            "Keep high-VPS/type49 typed ops as parser-frontier support, but require alias-lifecycle evidence before claiming GPAC_3403 R2T closure.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binding-spec", type=Path)
    parser.add_argument("--binding-diagnosis", type=Path)
    parser.add_argument("--progress-jsonl", type=Path)
    parser.add_argument("--summary-json", type=Path)
    parser.add_argument("--endpoint-package", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    report = build_report(args)
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(rendered, encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
