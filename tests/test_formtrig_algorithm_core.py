import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.formtrig_algorithm_core import (
    MutationEdge,
    MutationProposal,
    ReplayRecord,
    build_tcir,
    build_parent_child_edges,
    build_trigger_progress_graph,
    build_progress_record,
    build_atom_plan,
    compute_signal_health,
    decompose_tc,
    progress_dominates_global,
    progress_dominates,
    registry,
)


def record(
    seed_id: str,
    native_dt: float = 1.0,
    root_state: str = "R=1;T=0;probe=target",
    coverage_hash: str = "gdb_probe:abc",
    reached: bool = True,
    triggered: bool = False,
) -> ReplayRecord:
    return ReplayRecord(
        target_id="T",
        seed_id=seed_id,
        parent_seed_id="ROOT",
        content_sha256=seed_id,
        input_size=4,
        reached_R=reached,
        triggered_T=triggered,
        reached_count=1 if reached else 0,
        triggered_count=1 if triggered else 0,
        time_s=0.0,
        coverage_hash=coverage_hash,
        native_DT=native_dt,
        dt_bucket=1 if native_dt <= 1 else 2,
        tc_root_state=root_state,
        replay_hash=seed_id,
        replay_status="kept_rnt",
        metadata_status="formal_replay_verified_rnt",
        source_seedbank="",
        source_manifest="",
        source_seed="",
        producer="test",
    )


def test_decompose_mixed_tc_atoms():
    atoms = decompose_tc(
        "color_type == PALETTE && palette == NULL",
        "equality/magic",
        "png.c:10;png.c:11",
    )
    assert [atom.category for atom in atoms] == ["equality/magic", "binary-state-null"]
    assert [atom.root_variables for atom in atoms] == [["color_type"], ["palette"]]
    assert [atom.source_location for atom in atoms] == ["png.c:10", "png.c:11"]


def test_decompose_magma_or_as_any_of_group():
    atoms = decompose_tc("MAGMA_OR(num <= 0, gen < 0)", "numeric-margin", "p.cc:1")
    assert len(atoms) == 2
    assert {atom.composition for atom in atoms} == {"any_of"}
    assert {atom.group_id for atom in atoms} == {"g1"}
    assert [atom.root_variables for atom in atoms] == [["num"], ["gen"]]


def test_char_literal_compare_is_equality_not_numeric():
    atoms = decompose_tc("RAW != '>'", "equality/magic", "xml.c:1")
    assert atoms[0].category == "equality/magic"


def test_signal_health_rejects_flat_unaligned_dt():
    atom = decompose_tc("num <= 0", "numeric-margin", "p.cc:1")[0]
    records = [
        record("s1", root_state="R=1;T=0", coverage_hash="monitor_row:flat"),
        record("s2", root_state="R=2;T=0", coverage_hash="monitor_row:flat"),
    ]
    health = compute_signal_health("T", atom, records)
    assert not health.actionable_native_dt
    assert health.native_status == "unknown"
    assert not health.lift_required
    assert "native_DT_root_alignment_undefined_no_improving_edges" in health.reasons
    assert any("mutation_edges" in reason for reason in health.reasons)


def test_dominance_accepts_root_aligned_native_improvement():
    atom = decompose_tc("x > 10", "numeric-margin", "x.c:1")[0]
    records = [record("old", native_dt=4.0), record("new", native_dt=1.0)]
    health = compute_signal_health("T", atom, records)
    plan = build_atom_plan("T", atom, health)
    _, _, old_vector = progress_dominates(records[0], [], atom, plan)
    accepted, decision, _ = progress_dominates(records[1], [old_vector], atom, plan)
    assert accepted
    assert decision.reason == "native-distance improvement"


def test_dominance_rejects_non_root_aligned_novelty():
    atom = decompose_tc("x > 10", "numeric-margin", "x.c:1")[0]
    old = record("old", native_dt=1.0, root_state="R=1;T=0", coverage_hash="monitor_row:a")
    new = record("new", native_dt=1.0, root_state="R=2;T=0", coverage_hash="monitor_row:b")
    health = compute_signal_health("T", atom, [old, new])
    plan = build_atom_plan("T", atom, health)
    _, _, old_vector = progress_dominates(old, [], atom, plan)
    accepted, decision, _ = progress_dominates(new, [old_vector], atom, plan)
    assert not accepted
    assert decision.reason == "reject:not_root_or_event_aligned"


def test_progress_record_has_layered_schema():
    atoms = decompose_tc("color_type == PALETTE && palette == NULL", "equality/magic", "png.c:1;png.c:2")
    records = [record("s1")]
    plans = {atom.atom_id: build_atom_plan("T", atom, compute_signal_health("T", atom, records)) for atom in atoms}
    accepted, decision, _ = progress_dominates(records[0], [], atoms[0], plans[atoms[0].atom_id])
    rec = build_progress_record(records[0], atoms, plans, graph=None, decision=decision).to_dict()
    assert {"seed_id", "parent_id", "input_hash", "execution", "atoms", "global_progress", "mutation"} <= set(rec)
    assert {"R", "T", "target_context_hash", "coverage_hash", "crash_oracle", "replay_stable"} <= set(rec["execution"])
    assert {"atom_id", "atom_type", "native_DT_raw", "native_DT_bucket", "native_actionable", "lifted_features"} <= set(rec["atoms"][0])
    assert {"progress_vector", "non_dominated_rank", "novelty_reasons", "regression_flags"} <= set(rec["global_progress"])
    assert "progress_vector_by_atom" in rec["global_progress"]
    assert {"a1", "a2"} <= set(rec["global_progress"]["progress_vector_by_atom"])
    assert {"parent_seed_id", "mutation_operator", "mutated_ranges", "influence_confidence"} <= set(rec["mutation"])


def test_progress_record_carries_mutation_influence_confidence():
    atom = decompose_tc("palette == NULL", "binary-state-null", "png.c:2")[0]
    records = [record("s1")]
    plans = {atom.atom_id: build_atom_plan("T", atom, compute_signal_health("T", atom, records))}
    accepted, decision, _ = progress_dominates(records[0], [], atom, plans[atom.atom_id])
    mutation = MutationProposal(
        proposal_id="m:a1:0",
        target_id="T",
        atom_id=atom.atom_id,
        operator_name="optional-region deletion",
        seed_id="s1",
        source_path="/tmp/s1",
        mutated_ranges=[{"start": 0, "len": 4, "confidence": 0.5, "confidence_label": "medium"}],
        executed=True,
        replay_verifiable=True,
        changed_target_root_event=True,
        kept=accepted,
        keep_reason=decision.reason,
        details={"operator_family": "state_flip", "influence_confidence": 0.5},
    )
    rec = build_progress_record(records[0], [atom], plans, graph=None, decision=decision, mutation=mutation).to_dict()
    assert rec["mutation"]["operator_family"] == "state_flip"
    assert rec["mutation"]["influence_confidence"] == 0.5
    assert rec["mutation"]["mutated_ranges"][0]["confidence_label"] == "medium"


def test_binary_null_registry_uses_state_flip_operator_family():
    mutators = registry()["binary-state-null"]["mutators"]
    families = {item["operator_family"] for item in mutators}
    names = {item["name"] for item in mutators}
    assert families == {"state_flip"}
    assert "optional-region deletion" in names
    assert "guard-field perturbation" in names
    assert "reset/cleanup-path mutation" in names
    for item in mutators:
        assert item["preconditions"]
        assert item["required_evidence"]
        assert item["expected_effect"]
        assert item["fallback"]


def test_graph_uses_replay_hot_ranges_as_candidate_influence_ranges():
    atom = decompose_tc("ctx.palette == NULL", "binary-state-null", "fresh.c:10")[0]
    rec = record("s1")
    rec.input_size = 16
    rec.raw["hot_ranges"] = '[{"start":3,"len":4,"confidence":0.9,"runtime_event_id":"PLTE_region"}]'
    graph = build_trigger_progress_graph(
        "T",
        {"target_location": "fresh.c:10", "canary_expression": "ctx.palette == NULL"},
        [atom],
        [rec],
    )
    ranges = [node for node in graph.nodes if node["type"] == "candidate_input_influence_range"]
    assert len(ranges) == 1
    assert ranges[0]["start"] == 3
    assert ranges[0]["length"] == 4
    assert ranges[0]["runtime_event_id"] == "PLTE_region"
    assert ranges[0]["source"] == "replay_metadata"


def test_tcir_preserves_any_of_without_dnf_expansion():
    tcir = build_tcir("len > cap && (state == READY || state == PARTIAL)", "numeric-margin", "x.c:1")
    assert len(tcir.atoms) == 3
    group_types = {group.group_type for group in tcir.groups}
    assert "ALL_OF" in group_types
    assert "ANY_OF" in group_types
    any_groups = [group for group in tcir.groups if group.group_type == "ANY_OF"]
    assert len(any_groups) == 1
    assert len(any_groups[0].children) == 2


def test_tcir_has_all_of_group():
    tcir = build_tcir("len > cap && ptr == NULL", "numeric-margin", "x.c:1;x.c:2")
    assert tcir.groups[0].group_type == "ALL_OF"
    assert len(tcir.atoms) == 2


def test_tcir_adds_guard_edge_for_guarded_null_atom():
    tcir = build_tcir("ctx.color_type == PALETTE && ctx.palette == NULL", "binary-state-null", "fresh.c:1;fresh.c:2")
    guard_edges = [edge for edge in tcir.edges if edge.edge_type == "guard"]
    assert guard_edges
    src_atom = next(atom for atom in tcir.atoms if atom.atom_id == guard_edges[0].src)
    dst_atom = next(atom for atom in tcir.atoms if atom.atom_id == guard_edges[0].dst)
    assert src_atom.category == "equality/magic"
    assert dst_atom.category == "binary-state-null"


def test_tcir_does_not_treat_c_pointer_access_as_sequence():
    tcir = build_tcir("png_ptr->palette == NULL", "binary-state-null", "pngrtran.c:1967")
    assert tcir.groups[0].group_type == "ALL_OF"
    assert len(tcir.atoms) == 1
    assert tcir.atoms[0].category == "binary-state-null"


def test_tcir_sequence_edges_are_explicit_only():
    tcir = build_tcir("free(x) before use(x)", "compound-sequence-lifecycle", "uaf.c:1;uaf.c:2")
    assert tcir.groups[0].group_type == "SEQUENCE"
    assert len(tcir.atoms) == 2
    assert tcir.atoms[0].sequence_edges == ["a2"]


def test_tcir_same_object_group():
    tcir = build_tcir("SAME_OBJECT(obj)", "compound-sequence-lifecycle", "uaf.c:1")
    assert tcir.groups[0].group_type == "SAME_OBJECT"
    assert len(tcir.atoms) == 1
    assert tcir.atoms[0].object_identity_edges


def test_signal_health_uses_rnt_only_and_parent_child_edges():
    atom = decompose_tc("x > 10", "numeric-margin", "x.c:1")[0]
    parent = record("p", native_dt=5.0, root_state="x=5", triggered=False)
    child = record("c", native_dt=1.0, root_state="x=9", triggered=False)
    child.parent_seed_id = "p"
    triggered = record("t", native_dt=0.0, root_state="x=11", triggered=True)
    triggered.parent_seed_id = "c"
    records = [parent, child, triggered]
    edges = build_parent_child_edges(records)
    health = compute_signal_health("T", atom, records, edges, n_min=2, e_min=1)
    assert health.rnt_count == 2
    assert health.triggered_count == 1
    assert health.mutation_edge_count == 2
    assert health.dt_delta_rate > 0
    assert health.dt_improve_rate > 0
    assert health.sample_size_status == "sufficient"


def test_global_dominance_rejects_all_of_regression():
    tcir = build_tcir("ctx.color_type == PALETTE && ctx.palette == NULL", "binary-state-null", "fresh.c:1;fresh.c:2")
    records = [
        record("old", native_dt=1.0, root_state="color_type=3;palette_null=0;use_reached=1"),
        record("new", native_dt=1.0, root_state="color_type=2;palette_null=1;use_reached=0"),
    ]
    plans = {atom.atom_id: build_atom_plan("T", atom, compute_signal_health("T", atom, records, [], n_min=1, e_min=0)) for atom in tcir.atoms}
    _, _, old_seed = progress_dominates_global(records[0], [], tcir, plans)
    accepted, decision, _ = progress_dominates_global(records[1], [old_seed], tcir, plans)
    assert not accepted
    assert decision.reason == "regressed_higher_priority_atom"


def test_guard_blocked_atom_is_not_observed_false_regression():
    tcir = build_tcir("ctx.color_type == PALETTE && ctx.palette == NULL", "binary-state-null", "fresh.c:1;fresh.c:2")
    atom = next(atom for atom in tcir.atoms if atom.category == "binary-state-null")
    blocked = record("blocked", root_state="color_type=2;palette_null=1;use_reached=0")
    from tools.formtrig_algorithm_core import atom_observation

    obs = atom_observation(blocked, atom, tcir)
    assert obs.status == "BLOCKED_BY_GUARD"


def test_lifecycle_requires_object_identity_for_global_progress():
    tcir = build_tcir("free(x) before use(x)", "compound-sequence-lifecycle", "uaf.c:1")
    records = [
        record("old", root_state="producer=1;free=0;use=0;object_identity_confidence=0"),
        record("new", root_state="producer=1;free=1;use=1;object_identity_confidence=0"),
    ]
    plans = {atom.atom_id: build_atom_plan("T", atom, compute_signal_health("T", atom, records, [], n_min=1, e_min=0)) for atom in tcir.atoms}
    _, _, old_seed = progress_dominates_global(records[0], [], tcir, plans)
    accepted, decision, _ = progress_dominates_global(records[1], [old_seed], tcir, plans)
    assert not accepted
    assert any("lifecycle_object_identity_weak" in item for item in decision.rejected_components)


def test_lifecycle_registry_has_object_identity_alignment_operator():
    mutators = registry()["compound-sequence-lifecycle"]["mutators"]
    names = {item["name"] for item in mutators}
    assert "object-identity alignment" in names


if __name__ == "__main__":
    tests = sorted((name, fn) for name, fn in globals().items() if name.startswith("test_") and callable(fn))
    for name, fn in tests:
        fn()
    print(f"{len(tests)} tests_passed")
