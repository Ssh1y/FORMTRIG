#!/usr/bin/env python3
"""FORMTRIG v2 post-reach and end-to-end mode entrypoints."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import shutil
import time
from collections import Counter
from pathlib import Path
from typing import Any

try:
    from tools.formtrig_algorithm_core import (
        AtomPlan,
        MutationEdge,
        ProgressVector,
        ReplayRecord,
        SeedProgressRecord,
        TCAtom,
        TCIR,
        TriggerProgressGraph,
        append_jsonl,
        atom_observation,
        build_coarse_atom_plan,
        finalize_atom_plan,
        build_parent_child_edges,
        build_progress_record,
        build_atom_plan,
        build_tcir,
        build_trigger_progress_graph,
        category_from_meta,
        compute_signal_health,
        decompose_tc,
        dt_bucket,
        expression_from_meta,
        generic_afl_style_mutators,
        is_strict_rnt,
        insert_non_dominated,
        load_replay_records,
        load_signal_health_thresholds,
        lifecycle_prefix_score,
        mutation_operator_effect,
        progress_dominates,
        progress_dominates_global,
        propose_mutations,
        read_csv,
        registry,
        replay_record_from_row,
        root_signature,
        run_target_cmd,
        seed_path_for_record,
        source_location_from_meta,
        target_meta_from_inventories,
        typed_mutator_names,
        utc_now,
        write_csv,
        write_json,
    )
except ModuleNotFoundError:
    from formtrig_algorithm_core import (  # type: ignore
        AtomPlan,
        MutationEdge,
        ProgressVector,
        ReplayRecord,
        SeedProgressRecord,
        TCAtom,
        TCIR,
        TriggerProgressGraph,
        append_jsonl,
        atom_observation,
        build_coarse_atom_plan,
        finalize_atom_plan,
        build_parent_child_edges,
        build_progress_record,
        build_atom_plan,
        build_tcir,
        build_trigger_progress_graph,
        category_from_meta,
        compute_signal_health,
        decompose_tc,
        dt_bucket,
        expression_from_meta,
        generic_afl_style_mutators,
        is_strict_rnt,
        insert_non_dominated,
        load_replay_records,
        load_signal_health_thresholds,
        lifecycle_prefix_score,
        mutation_operator_effect,
        progress_dominates,
        progress_dominates_global,
        propose_mutations,
        read_csv,
        registry,
        replay_record_from_row,
        root_signature,
        run_target_cmd,
        seed_path_for_record,
        source_location_from_meta,
        target_meta_from_inventories,
        typed_mutator_names,
        utc_now,
        write_csv,
        write_json,
    )


DEFAULT_INVENTORIES = [
    Path("artifacts/magma_canary_inventory.csv"),
    Path("artifacts/cve_bench_inventory.csv"),
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def append_event(path: Path, mode: str, target_id: str, event: str, details: dict[str, Any]) -> None:
    append_jsonl(
        path,
        {
            "event": event,
            "time_utc": utc_now(),
            "mode": mode,
            "target_id": target_id,
            "details": details,
        },
    )


def jsonable(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(item) for item in value]
    return value


def load_target_bundle(
    root: Path,
    target_id: str,
    metadata_csv: Path | None,
    inventory_paths: list[Path],
) -> tuple[dict[str, str], Path, Path, list[ReplayRecord]]:
    metadata_path = metadata_csv or root / "artifacts" / "rnt_corpus" / target_id / "metadata.csv"
    seed_dir = metadata_path.parent / "seeds"
    records = load_replay_records(metadata_path)
    meta = target_meta_from_inventories(target_id, inventory_paths)
    if records and not meta.get("primary_tc_category") and records[0].raw.get("tc_category"):
        meta["primary_tc_category"] = records[0].raw.get("tc_category", "")
    return meta, metadata_path, seed_dir, records


def build_plans(
    target_id: str,
    meta: dict[str, str],
    records: list[ReplayRecord],
) -> tuple[TCIR, list[dict[str, Any]], list[dict[str, Any]], list[AtomPlan]]:
    expression = expression_from_meta(meta)
    category = category_from_meta(meta, records[0].raw.get("tc_category", "numeric-margin") if records else "numeric-margin")
    secondary = []
    if meta.get("secondary_tc_category"):
        secondary = [meta["secondary_tc_category"]]
    tcir = build_tcir(expression, category, source_location_from_meta(meta), secondary, target_id=target_id)
    rnt_records = [record for record in records if is_strict_rnt(record)]
    mutation_edges = build_parent_child_edges(records)
    health_rows: list[dict[str, Any]] = []
    plans: list[AtomPlan] = []
    for atom in tcir.atoms:
        health = compute_signal_health(target_id, atom, rnt_records, mutation_edges)
        health_rows.append(health.to_dict())
        plans.append(build_atom_plan(target_id, atom, health))
    return tcir, [atom.to_dict() for atom in tcir.atoms], health_rows, plans


def replay_signal_to_record(
    target_id: str,
    seed_id: str,
    parent: ReplayRecord,
    data: bytes,
    seed_path: Path,
    producer: str,
    signal: dict[str, Any],
) -> ReplayRecord:
    reached = bool(signal.get("reached")) if signal.get("reached") is not None else parent.reached_R
    triggered = bool(signal.get("triggered")) if signal.get("triggered") is not None else bool(signal.get("sanitizer_error"))
    native_dt = signal.get("native_DT")
    try:
        native_text = "" if native_dt is None else str(float(native_dt))
    except (TypeError, ValueError):
        native_text = ""
    record = ReplayRecord(
        target_id=target_id,
        seed_id=seed_id,
        parent_seed_id=parent.seed_id,
        content_sha256=sha256_bytes(data),
        input_size=len(data),
        reached_R=reached,
        triggered_T=triggered,
        reached_count=1 if reached else 0,
        triggered_count=1 if triggered else 0,
        time_s=0.0,
        coverage_hash=str(signal.get("trace_signature") or parent.coverage_hash),
        native_DT=float(native_text) if native_text else parent.native_DT,
        dt_bucket=None,
        tc_root_state=str(signal.get("root_state") or parent.tc_root_state),
        replay_hash=sha256_bytes(json.dumps(signal, sort_keys=True).encode()),
        replay_status="executed_mutation",
        metadata_status="formal_replay_verified_rnt" if reached and not triggered else "executed_mutation",
        source_seedbank=str(seed_path.parent),
        source_manifest="formtrig_mode",
        source_seed=str(seed_path),
        producer=producer,
        raw={key: str(value) for key, value in signal.items()},
    )
    record.dt_bucket = dt_bucket(record.native_DT)
    return record


def mutation_edge_from_records(parent: ReplayRecord, child: ReplayRecord, source: str) -> MutationEdge:
    return MutationEdge(
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
        source=source,
    )


def apply_baseline_to_plan(plan: AtomPlan, baseline: str) -> AtomPlan:
    if baseline == "native_tc_dgf":
        plan.use_native_dt = True
        plan.use_lifted_features = False
        plan.feature_extractors = ["native_DT"]
        plan.priority_components = ["reach", "trigger", "native_bucket", "native_dt"]
        plan.mutator_operators = generic_afl_style_mutators()
        plan.plan_reason = "native_tc_dgf_native_dt_generic_mutation_only"
        plan.graph_features = []
        plan.graph_node_ids = []
    elif baseline == "native_tc_dgf_typedmut":
        plan.use_native_dt = True
        plan.use_lifted_features = False
        plan.feature_extractors = ["native_DT"]
        plan.priority_components = ["reach", "trigger", "native_bucket", "native_dt"]
        plan.plan_reason = "native_tc_dgf_typedmut_native_dt_with_typed_mutators"
        plan.graph_features = []
        plan.graph_node_ids = []
    return plan


def annotate_atoms(tcir: TCIR, records: list[ReplayRecord]) -> list[dict[str, Any]]:
    priority = ["OBSERVED_TRUE", "OBSERVED_FALSE", "BLOCKED_BY_GUARD", "UNKNOWN_UNSTABLE", "NOT_OBSERVED"]
    for atom in tcir.atoms:
        statuses = [atom_observation(record, atom, tcir).status for record in records]
        atom.observation_status = next((status for status in priority if status in statuses), "NOT_OBSERVED")
    return [atom.to_dict() for atom in tcir.atoms]


def controlled_calibration_mutations(
    args: argparse.Namespace,
    target_id: str,
    atoms: list[Any],
    rnt_records: list[ReplayRecord],
    seed_dir: Path,
    graph: TriggerProgressGraph,
    thresholds: dict[str, Any],
    out_dir: Path,
) -> tuple[list[MutationEdge], list[dict[str, Any]], list[dict[str, Any]]]:
    edges: list[MutationEdge] = []
    rows: list[dict[str, Any]] = []
    insufficient: list[dict[str, Any]] = []
    e_min = int(thresholds.get("E_min_edges", 16))
    if not args.target_cmd:
        insufficient.append({"target_id": target_id, "reason": "missing_target_cmd_for_calibration", "needed_edges": e_min})
        return edges, rows, insufficient
    calib_dir = out_dir / "calibration_seeds"
    calib_dir.mkdir(parents=True, exist_ok=True)
    max_seed_records = int(getattr(args, "max_seed_records", 16))
    fake_records = rnt_records[: max(1, min(len(rnt_records), max_seed_records))]
    fake_edges: list[MutationEdge] = []
    for parent in fake_records:
        if len(edges) >= e_min:
            break
        seed_path = seed_path_for_record(seed_dir, parent)
        for atom in atoms:
            if len(edges) >= e_min:
                break
            health = compute_signal_health(target_id, atom, rnt_records, fake_edges, thresholds=thresholds)
            plan = apply_baseline_to_plan(build_coarse_atom_plan(target_id, atom, health), args.baseline)
            proposals = propose_mutations(target_id, atom, plan, parent, seed_path, graph, max(1, args.calibration_mutations_per_seed))
            for proposal, data in proposals:
                if len(edges) >= e_min:
                    break
                if data is None:
                    rows.append({"event": "calibration_skip", "proposal": proposal.to_dict(), "reason": proposal.keep_reason})
                    continue
                child_path = calib_dir / proposal.proposal_id.replace(":", "_")
                child_path.write_bytes(data)
                signal = run_target_cmd(args.target_cmd, data, args.per_exec_timeout)
                child = replay_signal_to_record(target_id, proposal.proposal_id, parent, data, child_path, proposal.operator_name, signal)
                edge = mutation_edge_from_records(parent, child, "controlled_calibration")
                edges.append(edge)
                fake_edges.append(edge)
                rows.append(
                    {
                        "event": "calibration_edge",
                        "target_id": target_id,
                        "parent_seed": parent.to_dict(),
                        "child_seed": {"seed_id": child.seed_id, "path": str(child_path), "content_sha256": child.content_sha256},
                        "child_replay_record": child.to_dict(),
                        "proposal": proposal.to_dict(),
                        "edge": edge.to_dict(),
                        "runtime_signal": signal,
                    }
                )
    if len(edges) < e_min:
        insufficient.append({"target_id": target_id, "reason": "calibration_edge_budget_infeasible", "edges": len(edges), "needed_edges": e_min})
    return edges, rows, insufficient


def prepare_algorithm_state(
    args: argparse.Namespace,
    meta: dict[str, str],
    records: list[ReplayRecord],
    seed_dir: Path,
    out_dir: Path,
) -> dict[str, Any]:
    thresholds = load_signal_health_thresholds(args.thresholds)
    expression = expression_from_meta(meta)
    category = category_from_meta(meta, records[0].raw.get("tc_category", "numeric-margin") if records else "numeric-margin")
    secondary = [meta["secondary_tc_category"]] if meta.get("secondary_tc_category") else []
    tcir = build_tcir(expression, category, source_location_from_meta(meta), secondary, target_id=args.target_id)
    initial_graph = build_trigger_progress_graph(args.target_id, meta, tcir.atoms, [])
    rnt_records = [record for record in records if is_strict_rnt(record)]
    parent_edges = build_parent_child_edges(records)
    calibration_rows: list[dict[str, Any]] = []
    insufficient_rows: list[dict[str, Any]] = []
    calibration_edges: list[MutationEdge] = []
    if len(parent_edges) < int(thresholds.get("E_min_edges", 16)):
        calibration_edges, calibration_rows, insufficient_rows = controlled_calibration_mutations(
            args,
            args.target_id,
            tcir.atoms,
            rnt_records,
            seed_dir,
            initial_graph,
            thresholds,
            out_dir,
        )
    all_edges = parent_edges + calibration_edges
    health_rows: list[dict[str, Any]] = []
    health_by_atom = {}
    coarse_plans: list[AtomPlan] = []
    for atom in tcir.atoms:
        health = compute_signal_health(args.target_id, atom, rnt_records, all_edges, thresholds=thresholds)
        health_by_atom[atom.atom_id] = health
        health_rows.append(health.to_dict())
        coarse_plans.append(build_coarse_atom_plan(args.target_id, atom, health))
    graph = build_trigger_progress_graph(args.target_id, meta, tcir.atoms, rnt_records)
    coarse_plans = [apply_baseline_to_plan(plan, args.baseline) for plan in coarse_plans]
    final_plans = [
        apply_baseline_to_plan(finalize_atom_plan(args.target_id, atom, health_by_atom[atom.atom_id], graph), args.baseline)
        for atom in tcir.atoms
    ]
    atoms = annotate_atoms(tcir, rnt_records)
    return {
        "thresholds": thresholds,
        "tcir": tcir,
        "atoms": atoms,
        "initial_graph": initial_graph,
        "graph": graph,
        "rnt_records": rnt_records,
        "parent_edges": parent_edges,
        "calibration_edges": calibration_edges,
        "calibration_rows": calibration_rows,
        "insufficient_rows": insufficient_rows,
        "health_rows": health_rows,
        "coarse_plans": coarse_plans,
        "final_plans": final_plans,
    }


def summarize_target_health(health_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not health_rows:
        return []
    sample_count = sum(int(row.get("sample_count") or 0) for row in health_rows)
    reached_count = sum(int(row.get("reached_count") or 0) for row in health_rows)
    triggered_count = sum(int(row.get("triggered_count") or 0) for row in health_rows)
    actionable_atoms = sum(1 for row in health_rows if row.get("actionable_native_dt") is True)
    lift_required_atoms = sum(1 for row in health_rows if row.get("lift_required") is True)
    atom_count = len(health_rows)
    return [
        {
            "target_id": health_rows[0].get("target_id", ""),
            "atom_count": atom_count,
            "sample_count": sample_count,
            "reached_count": reached_count,
            "triggered_count": triggered_count,
            "actionable_native_dt_atoms": actionable_atoms,
            "lift_required_atoms": lift_required_atoms,
            "min_dt_entropy": min(float(row.get("dt_entropy") or 0.0) for row in health_rows),
            "max_most_common_bucket_ratio": max(float(row.get("most_common_bucket_ratio") or 0.0) for row in health_rows),
            "min_root_alignment": min(float(row.get("root_alignment") or 0.0) for row in health_rows),
            "min_reach_stability": min(float(row.get("reach_stability") or 0.0) for row in health_rows),
            "native_status_counts": json.dumps(dict(Counter(str(row.get("native_status", "unknown")) for row in health_rows)), sort_keys=True),
            "min_root_observability": min(float(row.get("root_observability") or 0.0) for row in health_rows),
            "min_mutation_reach_stability": min(float(row.get("mutation_reach_stability") or 0.0) for row in health_rows),
        }
    ]


def write_common_outputs(
    root: Path,
    out_dir: Path,
    target_id: str,
    meta: dict[str, str],
    tcir: TCIR,
    atoms: list[dict[str, Any]],
    health_rows: list[dict[str, Any]],
    coarse_plans: list[AtomPlan],
    final_plans: list[AtomPlan],
    initial_graph: TriggerProgressGraph,
    graph: TriggerProgressGraph,
    calibration_rows: list[dict[str, Any]],
    insufficient_rows: list[dict[str, Any]],
) -> None:
    logs_dir = out_dir / "logs"
    artifacts_dir = out_dir / "artifacts"
    diagnostics_dir = out_dir / "results" / "diagnostics"
    plan_payload_common = {
        "target_id": target_id,
        "target_meta": meta,
        "tcir_schema": tcir.schema_version,
        "atoms": atoms,
        "registry": registry(),
    }
    write_json(artifacts_dir / "tcir" / f"{target_id}.json", tcir.to_dict())
    write_json(artifacts_dir / "atoms" / f"{target_id}.json", {"target_id": target_id, "atoms": atoms})
    write_json(artifacts_dir / "trigger_graphs" / f"{target_id}.json", graph.to_dict())
    write_json(out_dir / "tcir.json", tcir.to_dict())
    write_json(out_dir / "initial_trigger_progress_graph.json", initial_graph.to_dict())
    write_json(out_dir / "trigger_progress_graph.json", graph.to_dict())
    write_json(logs_dir / "atom_plans_coarse.json", {**plan_payload_common, "plans": [plan.to_dict() for plan in coarse_plans]})
    write_json(logs_dir / "atom_plans_final.json", {**plan_payload_common, "plans": [plan.to_dict() for plan in final_plans]})
    write_json(out_dir / "atom_plans_coarse.json", {**plan_payload_common, "plans": [plan.to_dict() for plan in coarse_plans]})
    write_json(out_dir / "atom_plans_final.json", {**plan_payload_common, "plans": [plan.to_dict() for plan in final_plans]})
    write_json(out_dir / "atom_plans.json", {**plan_payload_common, "plans": [plan.to_dict() for plan in final_plans]})
    write_json(root / "artifacts" / "tcir" / f"{target_id}.json", tcir.to_dict())
    write_json(root / "artifacts" / "atoms" / f"{target_id}.json", {"target_id": target_id, "atoms": atoms})
    write_json(root / "artifacts" / "trigger_graphs" / f"{target_id}.json", graph.to_dict())
    write_json(root / "artifacts" / "registry_dump.json", registry())
    write_csv(diagnostics_dir / "signal_health_by_atom.csv", health_rows)
    write_csv(diagnostics_dir / "signal_health_by_target.csv", summarize_target_health(health_rows))
    write_csv(out_dir / "signal_health_by_atom.csv", health_rows)
    write_csv(out_dir / "signal_health_by_target.csv", summarize_target_health(health_rows))
    (diagnostics_dir / "calibration_edges.jsonl").parent.mkdir(parents=True, exist_ok=True)
    (diagnostics_dir / "calibration_edges.jsonl").touch()
    (root / "results" / "diagnostics" / "calibration_edges.jsonl").parent.mkdir(parents=True, exist_ok=True)
    (root / "results" / "diagnostics" / "calibration_edges.jsonl").touch()
    if calibration_rows:
        for row in calibration_rows:
            append_jsonl(diagnostics_dir / "calibration_edges.jsonl", row)
            append_jsonl(root / "results" / "diagnostics" / "calibration_edges.jsonl", row)
    write_csv(diagnostics_dir / "insufficient_edges.csv", insufficient_rows)
    write_csv(root / "results" / "diagnostics" / "insufficient_edges.csv", insufficient_rows)


def initial_frontier(
    records: list[ReplayRecord],
    atom_dicts: list[dict[str, Any]],
    plans: list[AtomPlan],
    tcir: TCIR,
    graph: TriggerProgressGraph | None = None,
) -> tuple[list[SeedProgressRecord], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    atoms = tcir.atoms
    plan_by_atom = {plan.atom_id: plan for plan in plans}
    frontier: list[SeedProgressRecord] = []
    decisions: list[dict[str, Any]] = []
    progress_records: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []
    for record in records:
        accepted, decision, seed_progress = progress_dominates_global(record, frontier, tcir, plan_by_atom)
        row = decision.to_dict()
        if not is_strict_rnt(record) or not record.replay_stable:
            row["event_role"] = "initial_candidate_rejected"
            decisions.append(row)
            progress_records.append(
                build_progress_record(record, atoms, plan_by_atom, graph, decision=decision, tcir=tcir, seed_progress=seed_progress).to_dict()
            )
            continue
        if accepted:
            row["reason"] = "initial_frontier_seed"
            row["improved_components"] = []
            row["event_role"] = "initial_frontier"
            decision.reason = "initial_frontier_seed"
            decision.improved_components = []
            seed_progress.non_dominated_rank = 0
            frontier, removed = insert_non_dominated(frontier, seed_progress, tcir)
            decisions.append(row)
            progress_records.append(
                build_progress_record(record, atoms, plan_by_atom, graph, decision=decision, tcir=tcir, seed_progress=seed_progress).to_dict()
            )
            snapshots.append(frontier_snapshot(frontier, tcir, row["reason"], removed, record.seed_id, [atom.atom_id for atom in atoms]))
            continue
        row["event_role"] = "initial_corpus_dominance_check"
        decisions.append(row)
        progress_records.append(
            build_progress_record(record, atoms, plan_by_atom, graph, decision=decision, tcir=tcir, seed_progress=seed_progress).to_dict()
        )
    return frontier, decisions, progress_records, snapshots


def frontier_snapshot(
    frontier: list[SeedProgressRecord],
    tcir: TCIR,
    accept_reason: str,
    dominated_removed: int,
    selected_seed_id: str,
    focus_atoms: list[str],
) -> dict[str, Any]:
    class_counts = Counter()
    reason_counts = Counter()
    for item in frontier:
        for atom in tcir.atoms:
            if atom.atom_id in item.full_vector.atom_vectors:
                class_counts[atom.category] += 1
        if item.record.triggered_T:
            reason_counts["triggered"] += 1
        else:
            reason_counts[accept_reason] += 1
    return {
        "event": "frontier_snapshot",
        "time_utc": utc_now(),
        "target_id": tcir.target_id,
        "frontier_size": len(frontier),
        "records_by_tc_class": dict(class_counts),
        "records_by_accept_reason": dict(reason_counts),
        "dominated_records_removed": dominated_removed,
        "selected_seed_id": selected_seed_id,
        "focus_atoms": focus_atoms,
    }


def reproducible_trigger(target_cmd: str, data: bytes, timeout_s: float, first_signal: dict[str, Any]) -> tuple[bool, list[dict[str, Any]]]:
    signals = [first_signal]
    second = run_target_cmd(target_cmd, data, timeout_s)
    signals.append(second)
    ok = all(bool(item.get("triggered") or item.get("sanitizer_error")) for item in signals)
    return ok, signals


def save_trigger_evidence(
    out_dir: Path,
    proposal: Any,
    data: bytes,
    child_record: ReplayRecord,
    replays: list[dict[str, Any]],
    effect: dict[str, Any],
    decision: dict[str, Any],
    tcir: TCIR,
) -> Path:
    evidence_dir = out_dir / "trigger_evidence" / proposal.proposal_id.replace(":", "_")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "seed").write_bytes(data)
    write_json(evidence_dir / "proposal.json", proposal.to_dict())
    write_json(evidence_dir / "child_replay_record.json", child_record.to_dict())
    write_json(evidence_dir / "effect.json", effect)
    write_json(evidence_dir / "decision.json", decision)
    write_json(
        evidence_dir / "target_status.json",
        {
            "target_id": child_record.target_id,
            "atom_status": decision.get("vector", {}).get("atom_observations", {}),
            "group_status": decision.get("vector", {}).get("group_progress", {}),
        },
    )
    for index, signal in enumerate(replays):
        append_jsonl(evidence_dir / "replays.jsonl", {"replay_index": index, **signal})
    return evidence_dir


def structured_mutation_row(
    parent: ReplayRecord,
    child: ReplayRecord | None,
    proposal: Any,
    effect: dict[str, Any],
    decision: dict[str, Any],
    baseline: str = "",
    mode: str = "",
) -> dict[str, Any]:
    precondition = proposal.details.get("precondition", {})
    operator_family = proposal.details.get("operator_family", "")
    effect_payload = {
        "preserved_reach": bool(effect.get("preserved_reach", False)),
        "triggered": bool(effect.get("triggered", False)),
        "changed_root_state": bool(effect.get("changed_root_state", False)),
        "changed_producer_state": bool(effect.get("changed_producer_state", False)),
        "changed_use_context": bool(effect.get("changed_use_context", False)),
        "changed_lifecycle_prefix": bool(effect.get("changed_lifecycle_prefix", False)),
        "changed_object_identity_confidence": bool(effect.get("changed_object_identity_confidence", False)),
        "parent_object_identity_confidence": effect.get("parent_object_identity_confidence", 0.0),
        "child_object_identity_confidence": effect.get("child_object_identity_confidence", 0.0),
        "parent_lifecycle_prefix": effect.get("parent_lifecycle_prefix", 0),
        "child_lifecycle_prefix": effect.get("child_lifecycle_prefix", 0),
        "improved_components": list(effect.get("improved_components", decision.get("improved_components", [])) or []),
    }
    return {
        "event": "mutation_record",
        "target_id": proposal.target_id,
        "baseline": baseline,
        "mode": mode,
        "parent_seed_id": parent.seed_id,
        "child_seed_id": child.seed_id if child else "",
        "atom_id": proposal.atom_id,
        "operator_name": proposal.operator_name,
        "operator_family": operator_family,
        "precondition_satisfied": bool(precondition.get("satisfied", False)),
        "mutated_ranges": proposal.mutated_ranges,
        "influence_confidence": proposal.details.get("influence_confidence", 0.0),
        "executed": proposal.executed,
        "replay_verifiable": proposal.replay_verifiable,
        "effect": effect_payload,
        "decision_reason": decision.get("reason", ""),
        "precondition": precondition,
        "parent_seed": parent.to_dict(),
        "child_seed": {
            "seed_id": child.seed_id if child else "",
            "path": proposal.output_path,
            "content_sha256": child.content_sha256 if child else "",
        },
        "child_replay_record": child.to_dict() if child else {},
        "proposal": proposal.to_dict(),
        "raw_effect": effect,
        "decision": decision,
        # Compatibility fields for quick ad-hoc summaries.
        "kept": proposal.kept,
        "keep_reason": proposal.keep_reason,
    }


def execute_mutation_proposals(
    args: argparse.Namespace,
    records: list[ReplayRecord],
    atom_dicts: list[dict[str, Any]],
    plans: list[AtomPlan],
    frontier: list[SeedProgressRecord],
    seed_dir: Path,
    out_dir: Path,
    graph_payload: dict[str, Any],
    tcir: TCIR,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], int, dict[str, Any] | None]:
    atoms = tcir.atoms
    graph = TriggerProgressGraph(**graph_payload)
    plan_by_atom = {plan.atom_id: plan for plan in plans}
    mutation_rows: list[dict[str, Any]] = []
    decision_rows: list[dict[str, Any]] = []
    progress_records: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []
    executed = 0
    trigger_success: dict[str, Any] | None = None
    queue_dir = out_dir / "queue"
    queue_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.rng_seed)
    candidate_records = [record for record in records if record.reached_R and not record.triggered_T and record.replay_stable]
    rng.shuffle(candidate_records)
    for record in candidate_records[: args.max_seed_records]:
        seed_path = seed_path_for_record(seed_dir, record)
        for atom in atoms:
            plan = plan_by_atom[atom.atom_id]
            proposals = propose_mutations(
                args.target_id,
                atom,
                plan,
                record,
                seed_path,
                graph,
                max(1, args.max_mutation_proposals_per_seed),
            )
            for proposal, data in proposals:
                if executed >= args.max_total_mutations:
                    mutation_rows.append(structured_mutation_row(record, None, proposal, {}, {"accepted": False, "reason": "budget_exhausted"}, args.baseline, args.mode))
                    continue
                if data is None:
                    mutation_rows.append(structured_mutation_row(record, None, proposal, {}, {"accepted": False, "reason": proposal.keep_reason}, args.baseline, args.mode))
                    continue
                out_seed = queue_dir / proposal.proposal_id.replace(":", "_")
                out_seed.write_bytes(data)
                proposal.output_path = str(out_seed)
                if args.execute_mutations and args.target_cmd:
                    signal = run_target_cmd(args.target_cmd, data, args.per_exec_timeout)
                    executed += 1
                    new_record = replay_signal_to_record(record.target_id, proposal.proposal_id, record, data, out_seed, proposal.operator_name, signal)
                    proposal.executed = True
                    proposal.changed_target_root_event = (
                        new_record.tc_root_state != record.tc_root_state
                        or new_record.coverage_hash != record.coverage_hash
                    )
                    proposal.details["runtime_signal"] = signal
                    if new_record.triggered_T:
                        reproducible, replays = reproducible_trigger(args.target_cmd, data, args.per_exec_timeout, signal)
                        _, trigger_decision, seed_progress = progress_dominates_global(new_record, frontier, tcir, plan_by_atom)
                        decision = trigger_decision.to_dict()
                        decision["accepted"] = reproducible
                        decision["reason"] = "triggered" if reproducible else "not_replay_stable"
                        decision["rejected_components"] = [] if reproducible else ["trigger_not_reproducible"]
                        decision["replay_verifiable"] = reproducible
                        decision["details"]["replay_count"] = len(replays)
                        effect = mutation_operator_effect(record, new_record, type("Decision", (), decision)())
                        proposal.replay_verifiable = reproducible
                        proposal.kept = reproducible
                        proposal.keep_reason = decision["reason"]
                        proposal.details["operator_effect"] = effect
                        if reproducible:
                            evidence_dir = save_trigger_evidence(out_dir, proposal, data, new_record, replays, effect, decision, tcir)
                            trigger_success = {
                                "target_id": args.target_id,
                                "proposal_id": proposal.proposal_id,
                                "seed_id": new_record.seed_id,
                                "evidence_dir": str(evidence_dir),
                                "replay_count": len(replays),
                                "decision": decision,
                            }
                        decision_rows.append(decision)
                        mutation_rows.append(structured_mutation_row(record, new_record, proposal, effect, decision, args.baseline, args.mode))
                        progress_records.append(
                            build_progress_record(
                                new_record,
                                atoms,
                                plan_by_atom,
                                graph,
                                decision=type("Decision", (), decision)(),
                                mutation=proposal,
                                tcir=tcir,
                            ).to_dict()
                        )
                        if reproducible:
                            return mutation_rows, decision_rows, progress_records, snapshots, executed, trigger_success
                        continue

                    accepted, decision, seed_progress = progress_dominates_global(new_record, frontier, tcir, plan_by_atom)
                    proposal.replay_verifiable = decision.replay_verifiable
                    proposal.kept = accepted
                    proposal.keep_reason = decision.reason
                    effect = mutation_operator_effect(record, new_record, decision)
                    proposal.details["operator_effect"] = effect
                    decision_rows.append(decision.to_dict())
                    progress_records.append(
                        build_progress_record(
                            new_record,
                            atoms,
                            plan_by_atom,
                            graph,
                            decision=decision,
                            mutation=proposal,
                            tcir=tcir,
                            seed_progress=seed_progress,
                        ).to_dict()
                    )
                    if accepted:
                        frontier, removed = insert_non_dominated(frontier, seed_progress, tcir)
                        snapshots.append(frontier_snapshot(frontier, tcir, decision.reason, removed, new_record.seed_id, [atom.atom_id]))
                    mutation_rows.append(structured_mutation_row(record, new_record, proposal, effect, decision.to_dict(), args.baseline, args.mode))
                else:
                    proposal.keep_reason = "not_executed"
                    mutation_rows.append(structured_mutation_row(record, None, proposal, {}, {"accepted": False, "reason": "not_executed"}, args.baseline, args.mode))
    return mutation_rows, decision_rows, progress_records, snapshots, executed, trigger_success


def run_postreach_mode(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    events = out_dir / "standard_events.jsonl"
    append_event(events, "postreach_mode", args.target_id, "mode_start", jsonable(vars(args)))
    inventory_paths = [root / item for item in args.inventory]
    meta, metadata_path, seed_dir, records = load_target_bundle(root, args.target_id, args.metadata_csv, inventory_paths)
    if not records:
        append_event(events, "postreach_mode", args.target_id, "mode_error", {"error": f"no metadata records: {metadata_path}"})
        raise SystemExit(f"no metadata records: {metadata_path}")
    state = prepare_algorithm_state(args, meta, records, seed_dir, out_dir)
    tcir = state["tcir"]
    atoms = state["atoms"]
    health_rows = state["health_rows"]
    plans = state["final_plans"]
    rnt_records = state["rnt_records"]
    write_common_outputs(
        root,
        out_dir,
        args.target_id,
        meta,
        tcir,
        atoms,
        health_rows,
        state["coarse_plans"],
        state["final_plans"],
        state["initial_graph"],
        state["graph"],
        state["calibration_rows"],
        state["insufficient_rows"],
    )
    graph_payload = json.loads((out_dir / "trigger_progress_graph.json").read_text())
    graph = TriggerProgressGraph(**graph_payload)
    frontier, import_decisions, import_progress_records, import_snapshots = initial_frontier(rnt_records, atoms, plans, tcir, graph)
    logs_dir = out_dir / "logs"
    progress_path = logs_dir / "progress_decisions.jsonl"
    progress_record_path = logs_dir / "progress_records.jsonl"
    snapshot_path = logs_dir / "frontier_snapshots.jsonl"
    for row in import_decisions:
        append_jsonl(progress_path, {"event": "seed_import_progress_decision", **row})
    for row in import_progress_records:
        append_jsonl(progress_record_path, {"event": "seed_import_progress_record", **row})
    for row in import_snapshots:
        append_jsonl(snapshot_path, row)
    mutations, mutation_decisions, mutation_progress_records, mutation_snapshots, executed, trigger_success = execute_mutation_proposals(
        args,
        records,
        atoms,
        plans,
        frontier,
        seed_dir,
        out_dir,
        graph_payload,
        tcir,
    )
    for row in mutation_decisions:
        append_jsonl(progress_path, {"event": "mutation_progress_decision", **row})
    for row in mutation_progress_records:
        append_jsonl(progress_record_path, {"event": "mutation_progress_record", **row})
    for row in mutation_snapshots:
        append_jsonl(snapshot_path, row)
    mutation_path = logs_dir / "mutation_records.jsonl"
    for row in mutations:
        append_jsonl(mutation_path, row)
    for path in [progress_path, progress_record_path, mutation_path, snapshot_path]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
    # Compatibility copies for existing ad-hoc tooling.
    shutil.copyfile(progress_path, out_dir / "progress_decisions.jsonl")
    shutil.copyfile(progress_record_path, out_dir / "progress_records.jsonl")
    shutil.copyfile(mutation_path, out_dir / "mutation_records.jsonl")
    shutil.copyfile(snapshot_path, out_dir / "frontier_snapshots.jsonl")
    status = {
        "status": "complete",
        "mode": "postreach_mode",
        "baseline": args.baseline,
        "target_id": args.target_id,
        "metadata_csv": str(metadata_path),
        "seed_dir": str(seed_dir),
        "records": len(records),
        "rnt_records": len(rnt_records),
        "atoms": len(atoms),
        "frontier_size": len(frontier),
        "mutation_records": len(mutations),
        "progress_records": len(import_progress_records) + len(mutation_progress_records),
        "executed_mutations": executed,
        "trigger_success": trigger_success,
        "out_dir": str(out_dir),
        "completed_utc": utc_now(),
    }
    write_json(out_dir / "status.json", status)
    append_event(events, "postreach_mode", args.target_id, "mode_complete", status)
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0


def run_e2e_mode(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    out_dir = args.out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    events = out_dir / "standard_events.jsonl"
    append_event(events, "e2e_mode", args.target_id, "mode_start", jsonable(vars(args)))
    inventory_paths = [root / item for item in args.inventory]
    meta = target_meta_from_inventories(args.target_id, inventory_paths)
    stream_records: list[ReplayRecord] = []
    if args.metadata_csv and args.metadata_csv.exists():
        stream_records = load_replay_records(args.metadata_csv)
    elif args.rnt_stream and args.rnt_stream.exists():
        rows = []
        with args.rnt_stream.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                value = json.loads(line)
                rows.append({key: str(value.get(key, "")) for key in value})
        stream_records = [replay_record_from_row(row) for row in rows]
    metadata_path = args.metadata_csv or root / "artifacts" / "rnt_corpus" / args.target_id / "metadata.csv"
    seed_dir = metadata_path.parent / "seeds"
    state = prepare_algorithm_state(args, meta, stream_records, seed_dir, out_dir)
    tcir = state["tcir"]
    atoms = state["atoms"]
    health_rows = state["health_rows"]
    plans = state["final_plans"]
    rnt_records = state["rnt_records"]
    write_common_outputs(
        root,
        out_dir,
        args.target_id,
        meta,
        tcir,
        atoms,
        health_rows,
        state["coarse_plans"],
        state["final_plans"],
        state["initial_graph"],
        state["graph"],
        state["calibration_rows"],
        state["insufficient_rows"],
    )
    graph_payload = json.loads((out_dir / "trigger_progress_graph.json").read_text())
    graph = TriggerProgressGraph(**graph_payload)
    frontier, import_decisions, import_progress_records, import_snapshots = initial_frontier(rnt_records, atoms, plans, tcir, graph)
    logs_dir = out_dir / "logs"
    progress_path = logs_dir / "progress_decisions.jsonl"
    progress_record_path = logs_dir / "progress_records.jsonl"
    snapshot_path = logs_dir / "frontier_snapshots.jsonl"
    for row in import_decisions:
        append_jsonl(progress_path, {"event": "dynamic_rnt_progress_decision", **row})
    for row in import_progress_records:
        append_jsonl(progress_record_path, {"event": "dynamic_rnt_progress_record", **row})
    for row in import_snapshots:
        append_jsonl(snapshot_path, row)
    mutation_path = logs_dir / "mutation_records.jsonl"
    mutations: list[dict[str, Any]] = []
    mutation_decisions: list[dict[str, Any]] = []
    mutation_progress_records: list[dict[str, Any]] = []
    mutation_snapshots: list[dict[str, Any]] = []
    executed = 0
    trigger_success = None
    if not args.dry_run:
        args.execute_mutations = True
        mutations, mutation_decisions, mutation_progress_records, mutation_snapshots, executed, trigger_success = execute_mutation_proposals(
            args,
            stream_records,
            atoms,
            plans,
            frontier,
            seed_dir,
            out_dir,
            graph_payload,
            tcir,
        )
        for row in mutation_decisions:
            append_jsonl(progress_path, {"event": "mutation_progress_decision", **row})
        for row in mutation_progress_records:
            append_jsonl(progress_record_path, {"event": "mutation_progress_record", **row})
        for row in mutation_snapshots:
            append_jsonl(snapshot_path, row)
        for row in mutations:
            append_jsonl(mutation_path, row)
    mutation_path.parent.mkdir(parents=True, exist_ok=True)
    mutation_path.touch()
    for path in [progress_path, progress_record_path, snapshot_path, mutation_path]:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)
    write_json(
        out_dir / "base_queue_stats.json",
        {
            "target_id": args.target_id,
            "baseline": args.baseline,
            "mode": "e2e_mode",
            "input_records": len(stream_records),
            "strict_rnt_records": len(rnt_records),
            "dry_run": args.dry_run,
        },
    )
    write_json(
        out_dir / "trigger_progress_frontier_stats.json",
        {
            "target_id": args.target_id,
            "baseline": args.baseline,
            "mode": "e2e_mode",
            "frontier_size": len(frontier),
            "mutation_records": len(mutations),
            "executed_mutations": executed,
            "trigger_success": trigger_success,
        },
    )
    shutil.copyfile(out_dir / "base_queue_stats.json", logs_dir / "base_queue_stats.json")
    shutil.copyfile(out_dir / "trigger_progress_frontier_stats.json", logs_dir / "trigger_progress_frontier_stats.json")
    shutil.copyfile(progress_path, out_dir / "progress_decisions.jsonl")
    shutil.copyfile(progress_record_path, out_dir / "progress_records.jsonl")
    shutil.copyfile(snapshot_path, out_dir / "frontier_snapshots.jsonl")
    shutil.copyfile(mutation_path, out_dir / "mutation_records.jsonl")
    status = {
        "status": "complete",
        "mode": "e2e_mode",
        "baseline": args.baseline,
        "target_id": args.target_id,
        "dynamic_rnt_records": len(stream_records),
        "strict_rnt_records": len(rnt_records),
        "atoms": len(atoms),
        "frontier_size": len(frontier),
        "progress_records": len(import_progress_records) + len(mutation_progress_records),
        "mutation_records": len(mutations),
        "executed_mutations": executed,
        "trigger_success": trigger_success,
        "dry_run": args.dry_run,
        "out_dir": str(out_dir),
        "completed_utc": utc_now(),
    }
    write_json(out_dir / "status.json", status)
    append_event(events, "e2e_mode", args.target_id, "mode_complete", status)
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    common: dict[str, Any] = {}
    for name in ["postreach_mode", "e2e_mode"]:
        sp = sub.add_parser(name)
        sp.add_argument("--root", type=Path, default=Path("."))
        sp.add_argument("--target-id", required=True)
        sp.add_argument("--out-dir", required=True, type=Path)
        sp.add_argument("--metadata-csv", type=Path)
        sp.add_argument("--inventory", action="append", type=Path, default=list(DEFAULT_INVENTORIES))
        sp.add_argument("--target-cmd", default="")
        sp.add_argument("--per-exec-timeout", type=float, default=2.0)
        sp.add_argument("--thresholds", type=Path, default=Path("configs/signal_health_thresholds.yaml"))
        sp.add_argument("--calibration-mutations-per-seed", type=int, default=4)
        sp.add_argument("--baseline", choices=["formtrig", "native_tc_dgf", "native_tc_dgf_typedmut"], default="formtrig")
        common[name] = sp
    post = common["postreach_mode"]
    post.add_argument("--execute-mutations", action="store_true")
    post.add_argument("--max-seed-records", type=int, default=16)
    post.add_argument("--max-mutation-proposals-per-seed", type=int, default=8)
    post.add_argument("--max-total-mutations", type=int, default=64)
    post.add_argument("--rng-seed", type=int, default=1337)
    e2e = common["e2e_mode"]
    e2e.add_argument("--rnt-stream", type=Path)
    e2e.add_argument("--dry-run", action="store_true")
    e2e.add_argument("--max-seed-records", type=int, default=16)
    e2e.add_argument("--max-mutation-proposals-per-seed", type=int, default=8)
    e2e.add_argument("--max-total-mutations", type=int, default=64)
    e2e.add_argument("--rng-seed", type=int, default=1337)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.mode == "postreach_mode":
        return run_postreach_mode(args)
    if args.mode == "e2e_mode":
        return run_e2e_mode(args)
    raise SystemExit(f"unknown mode: {args.mode}")


if __name__ == "__main__":
    raise SystemExit(main())
