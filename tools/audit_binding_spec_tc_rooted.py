#!/usr/bin/env python3
"""Audit whether a BindingSpec is statically rooted in a trigger condition.

This tool does not claim that a lifted signal is useful during fuzzing. It only
checks the first half of the evidence chain: the spec must start from a TC atom
and bind semantic roles that can plausibly influence or preserve that atom. The
dynamic half is still handled by binding-signal/frontier validation.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover - exercised only when PyYAML is absent.
    yaml = None  # type: ignore[assignment]


ROOT_ROLES = {"root_observe"}
PRODUCER_ROLES = {"producer", "desired_producer", "opposite_producer"}
BINARY_BRIDGE_ROLES = PRODUCER_ROLES | {"use", "input_influence"}
LIFECYCLE_ROOT_ROLES = {"root_observe", "lifecycle_event"}
EXACT_OBSERVE_KEYS = {"site_id", "label", "bug", "canary_label"}


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_binding_spec(path: Path) -> dict[str, Any]:
    if yaml is None:
        raise RuntimeError("PyYAML is required to parse BindingSpec YAML files")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("BindingSpec YAML root must be a mapping")
    return payload


def normalize_category(value: Any) -> str:
    category = str(value or "").strip().lower().replace("_", "-")
    if category in {"binary-state-null", "binary-null", "binary-state"}:
        return "binary-null"
    if category in {"numeric", "numeric-margin"}:
        return "numeric"
    if category in {"equality", "equality-magic", "equality/magic"}:
        return "equality"
    if category in {"lifecycle", "compound-sequence-lifecycle", "sequence-lifecycle"}:
        return "lifecycle"
    return category or "unknown"


def nonempty(value: Any) -> bool:
    return bool(str(value or "").strip())


def atom_id(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def observe_at_is_exact(observe_at: Any) -> bool:
    if not isinstance(observe_at, dict):
        return False
    if any(nonempty(observe_at.get(key)) for key in EXACT_OBSERVE_KEYS):
        return True
    return nonempty(observe_at.get("file")) and atom_id(observe_at.get("line")) is not None


def input_influence_mapping_is_exact(binding: dict[str, Any]) -> bool:
    start = atom_id(binding.get("range_start"))
    length = atom_id(binding.get("range_len"))
    if start is not None and length is not None and length > 0:
        return True
    return nonempty(binding.get("mutation_hook")) or nonempty(binding.get("typed_mutation_hook"))


def binding_mapping_is_exact(binding: dict[str, Any]) -> bool:
    if observe_at_is_exact(binding.get("observe_at")):
        return True
    if str(binding.get("role") or "") == "input_influence":
        return input_influence_mapping_is_exact(binding)
    return False


def sorted_counter(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def audit_payload(payload: dict[str, Any], *, source_path: str = "") -> dict[str, Any]:
    blockers: list[str] = []
    limitations: list[str] = []

    tc = payload.get("tc") if isinstance(payload.get("tc"), dict) else {}
    category = normalize_category(tc.get("category"))
    expression = str(tc.get("expression") or "")

    if not nonempty(payload.get("tc_id")):
        blockers.append("missing tc_id")
    if not nonempty(expression):
        blockers.append("missing tc.expression")
    if category == "unknown":
        blockers.append("missing or unknown tc.category")

    atoms_raw = payload.get("atoms") if isinstance(payload.get("atoms"), list) else []
    bindings_raw = payload.get("bindings") if isinstance(payload.get("bindings"), list) else []
    if not atoms_raw:
        blockers.append("missing atoms")
    if not bindings_raw:
        blockers.append("missing bindings")

    atoms: dict[int, dict[str, Any]] = {}
    for raw_atom in atoms_raw:
        if not isinstance(raw_atom, dict):
            blockers.append("atom entry is not a mapping")
            continue
        current_id = atom_id(raw_atom.get("id"))
        if current_id is None:
            blockers.append("atom is missing an integer id")
            continue
        atoms[current_id] = raw_atom
        if not nonempty(raw_atom.get("expr")):
            blockers.append(f"atom {current_id} is missing expr")
        if not nonempty(raw_atom.get("root")):
            blockers.append(f"atom {current_id} is missing root")
        if not nonempty(raw_atom.get("kind")):
            blockers.append(f"atom {current_id} is missing kind")

    roles_by_atom: dict[int, set[str]] = defaultdict(set)
    role_counts: Counter[str] = Counter()
    bindings_with_exact_observe = 0
    repair_hook_bindings = 0
    same_object_bindings = 0

    for index, raw_binding in enumerate(bindings_raw, 1):
        if not isinstance(raw_binding, dict):
            blockers.append(f"binding {index} is not a mapping")
            continue
        current_atom = atom_id(raw_binding.get("atom"))
        role = str(raw_binding.get("role") or "")
        if current_atom is None or current_atom not in atoms:
            blockers.append(f"binding {raw_binding.get('id') or index} references an unknown atom")
            continue
        if not nonempty(role):
            blockers.append(f"binding {raw_binding.get('id') or index} is missing role")
            continue
        roles_by_atom[current_atom].add(role)
        role_counts[role] += 1
        if role == "repair_hook":
            repair_hook_bindings += 1
        if binding_mapping_is_exact(raw_binding):
            bindings_with_exact_observe += 1
        else:
            blockers.append(
                f"binding {raw_binding.get('id') or index} lacks exact runtime/input mapping"
            )
        if role == "same_object":
            same_object_bindings += 1
            for key in ("relation_from", "relation_to", "object_expr"):
                if not nonempty(raw_binding.get(key)):
                    blockers.append(
                        f"same_object binding {raw_binding.get('id') or index} is missing {key}"
                    )

    for current_id in sorted(atoms):
        roles = roles_by_atom.get(current_id, set())
        if not roles:
            blockers.append(f"atom {current_id} has no bindings")
            continue
        if category in {"numeric", "equality"} and not roles.intersection(ROOT_ROLES):
            blockers.append(f"atom {current_id} lacks root_observe binding")
        elif category == "binary-null":
            if not roles.intersection(ROOT_ROLES):
                blockers.append(f"atom {current_id} lacks root_observe binding")
            if not roles.intersection(BINARY_BRIDGE_ROLES):
                blockers.append(
                    f"atom {current_id} lacks producer/use/input_influence binding for binary/null TC"
                )
        elif category == "lifecycle":
            if not roles.intersection(LIFECYCLE_ROOT_ROLES):
                blockers.append(f"atom {current_id} lacks lifecycle/root observation binding")
            if "same_object" not in roles:
                blockers.append(f"atom {current_id} lacks same_object binding for lifecycle TC")
        else:
            if not roles.intersection(ROOT_ROLES | {"lifecycle_event"}):
                limitations.append(f"atom {current_id} has no explicit root/lifecycle role")

    if repair_hook_bindings:
        limitations.append("repair_hook roles require separate ablation before efficacy claims")
    if category == "binary-null" and not set(role_counts).intersection(PRODUCER_ROLES):
        limitations.append("binary/null spec has no producer role; endpoint R2T may stall")
    if category == "lifecycle" and same_object_bindings == 0:
        limitations.append("lifecycle spec has no same_object relation")

    status = "pass" if not blockers else "fail"
    return {
        "schema": "formtrig_binding_spec_tc_rooted_audit_v1",
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "source_path": source_path,
        "status": status,
        "tc_id": str(payload.get("tc_id") or ""),
        "tc_category": str(tc.get("category") or ""),
        "normalized_category": category,
        "tc_expression": expression,
        "atom_count": len(atoms),
        "binding_count": len([item for item in bindings_raw if isinstance(item, dict)]),
        "role_counts": sorted_counter(role_counts),
        "roles_by_atom": {
            str(current_id): sorted(roles)
            for current_id, roles in sorted(roles_by_atom.items())
        },
        "checks": {
            "static_root_binding_pass": not any(
                "lacks root_observe" in blocker
                or "lacks lifecycle/root" in blocker
                or "missing atoms" in blocker
                for blocker in blockers
            ),
            "semantic_role_coverage_pass": not any(
                "lacks producer/use/input_influence" in blocker
                or "lacks same_object" in blocker
                for blocker in blockers
            ),
            "exact_runtime_mapping_pass": bindings_with_exact_observe
            == len([item for item in bindings_raw if isinstance(item, dict)])
            and bool(bindings_raw),
            "negative_role_rejection_pass": not (
                category == "binary-null" and set(role_counts) <= ROOT_ROLES
            ),
        },
        "blockers": sorted(dict.fromkeys(blockers)),
        "limitations": sorted(dict.fromkeys(limitations)),
    }


def audit_file(path: Path) -> dict[str, Any]:
    try:
        payload = read_binding_spec(path)
    except Exception as exc:
        return {
            "schema": "formtrig_binding_spec_tc_rooted_audit_v1",
            "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "source_path": str(path),
            "status": "unknown",
            "blockers": [f"could not read BindingSpec: {exc}"],
            "limitations": [],
            "checks": {
                "static_root_binding_pass": False,
                "semantic_role_coverage_pass": False,
                "exact_runtime_mapping_pass": False,
                "negative_role_rejection_pass": False,
            },
        }
    return audit_payload(payload, source_path=str(path))


def write_markdown(path: Path, payload: dict[str, Any]) -> None:
    lines = [
        f"# TC-Rooted BindingSpec Audit: {payload.get('tc_id', '')}",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Category: `{payload.get('tc_category', '')}`",
        f"- Source: `{payload.get('source_path', '')}`",
        f"- Atoms: `{payload.get('atom_count', 0)}`",
        f"- Bindings: `{payload.get('binding_count', 0)}`",
        "",
        "## Checks",
        "",
    ]
    checks = payload.get("checks") if isinstance(payload.get("checks"), dict) else {}
    for key in sorted(checks):
        lines.append(f"- {key}: `{checks[key]}`")
    lines.extend(["", "## Role Counts", ""])
    role_counts = payload.get("role_counts") if isinstance(payload.get("role_counts"), dict) else {}
    if role_counts:
        lines.extend(f"- {role}: `{count}`" for role, count in sorted(role_counts.items()))
    else:
        lines.append("- none")
    lines.extend(["", "## Blockers", ""])
    blockers = payload.get("blockers") or []
    if blockers:
        lines.extend(f"- {blocker}" for blocker in blockers)
    else:
        lines.append("- none")
    lines.extend(["", "## Limitations", ""])
    limitations = payload.get("limitations") or []
    if limitations:
        lines.extend(f"- {limitation}" for limitation in limitations)
    else:
        lines.append("- none")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binding-spec", type=Path, required=True)
    parser.add_argument("--out-json", type=Path, required=True)
    parser.add_argument("--out-md", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = audit_file(args.binding_spec)
    write_json(args.out_json, payload)
    if args.out_md:
        write_markdown(args.out_md, payload)
    return 0 if payload.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
