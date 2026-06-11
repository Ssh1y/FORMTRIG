import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.formtrig_algorithm_core import (
    AtomPlan,
    ReplayRecord,
    atom_observation,
    build_full_progress_vector,
    build_tcir,
    confidence_to_float,
    object_identity_confidence_from_state,
    progress_dominates_global,
    seed_progress_record,
)


def rec(root_state: str, triggered: bool = False, target_id: str = "T") -> ReplayRecord:
    return ReplayRecord(
        target_id=target_id,
        seed_id="s",
        parent_seed_id="ROOT",
        content_sha256="s",
        input_size=4,
        reached_R=True,
        triggered_T=triggered,
        reached_count=1,
        triggered_count=1 if triggered else 0,
        time_s=0.0,
        coverage_hash="truth:test",
        native_DT=0.0 if triggered else 1.0,
        dt_bucket=0 if triggered else 1,
        tc_root_state=root_state,
        replay_hash="s",
        replay_status="kept_rnt" if not triggered else "triggered",
        metadata_status="verified_rnt" if not triggered else "triggered",
        source_seedbank="",
        source_manifest="",
        source_seed="",
        producer="test",
        raw={"target_context_hash": target_id},
    )


def plans(tcir):
    return {
        atom.atom_id: AtomPlan(
            target_id=tcir.target_id,
            atom_id=atom.atom_id,
            category=atom.category,
            expression=atom.expression,
            use_native_dt=True,
            use_lifted_features=False,
            feature_extractors=["native_DT"],
            mutator_operators=[],
            priority_components=["reach", "trigger", "native_bucket", "native_dt"],
            actionability={},
            plan_reason="test",
        )
        for atom in tcir.atoms
    }


def test_char_literal_truth_normalizes_ascii_numeric_root():
    tcir = build_tcir("tag == 'A'", "equality/magic", "x.c:1")
    atom = tcir.atoms[0]
    assert atom_observation(rec("tag=65"), atom, tcir).status == "OBSERVED_TRUE"
    tcir_b = build_tcir("tag == 'B'", "equality/magic", "x.c:1")
    assert atom_observation(rec("tag=65"), tcir_b.atoms[0], tcir_b).status == "OBSERVED_FALSE"
    tcir_g = build_tcir("hdr == 'G'", "equality/magic", "x.c:1")
    assert atom_observation(rec("hdr=71"), tcir_g.atoms[0], tcir_g).status == "OBSERVED_TRUE"


def test_string_literal_truth_supports_flag_and_token_forms():
    tcir = build_tcir('hdr == "TX"', "equality/magic", "x.c:1")
    atom = tcir.atoms[0]
    assert atom_observation(rec("hdr_TX=1"), atom, tcir).status == "OBSERVED_TRUE"
    assert atom_observation(rec("hdr=TX"), atom, tcir).status == "OBSERVED_TRUE"


def test_confidence_to_float_numeric_strings_and_labels():
    assert confidence_to_float("1.0") == 1.0
    assert confidence_to_float("0.8") == 0.8
    assert confidence_to_float("0.5") == 0.5
    assert confidence_to_float("verified") == 1.0
    assert confidence_to_float("high") == 0.8


def test_anyof_trigger_keeps_atom_truth_separate():
    tcir = build_tcir("tag == 'A' || tag == 'B'", "equality/magic", "x.c:1;x.c:2", target_id="T2_EQUALITY_DIRECT_ANYOF")
    vector = build_full_progress_vector(rec("tag=65", triggered=True, target_id="T2_EQUALITY_DIRECT_ANYOF"), tcir, plans(tcir))
    assert vector.atom_observations["a1"]["status"] == "OBSERVED_TRUE"
    assert vector.atom_observations["a2"]["status"] == "OBSERVED_FALSE"
    assert vector.atom_vectors["a1"]["atom_score"] > vector.atom_vectors["a2"]["atom_score"]
    assert vector.atom_vectors["a2"]["atom_score"] < 1000.0
    assert vector.selected_branch == "a1"
    assert vector.group_progress[tcir.root_group_id]["satisfied"] is True
    assert vector.triggered is True


def test_guarded_trigger_keeps_guard_and_null_atoms_true():
    tcir = build_tcir("hdr == 'G' && ctx.obj == NULL", "binary-state-null", "x.c:1;x.c:2", target_id="T5_GUARDED_BINARY")
    vector = build_full_progress_vector(
        rec("hdr=71;hdr_is_G=1;obj_null=1;use_reached=1", triggered=True, target_id="T5_GUARDED_BINARY"),
        tcir,
        plans(tcir),
    )
    assert vector.atom_observations["a1"]["status"] == "OBSERVED_TRUE"
    assert vector.atom_observations["a2"]["status"] == "OBSERVED_TRUE"
    assert vector.group_progress[tcir.root_group_id]["satisfied"] is True


def test_object_identity_confidence_numeric_string():
    assert object_identity_confidence_from_state("object_identity_confidence=1.0") == 1.0
    assert object_identity_confidence_from_state("object_identity_confidence=0.8") == 0.8


def test_triggered_lifecycle_records_object_identity_component():
    tcir = build_tcir(
        "create(obj) -> release(obj) -> use(obj) && SAME_OBJECT(obj)",
        "compound-sequence-lifecycle",
        "x.c:1;x.c:2;x.c:3;x.c:4",
        target_id="T6_SAME_OBJECT_LIFECYCLE",
    )
    plan_by_atom = plans(tcir)
    old = rec(
        "lifecycle_prefix=2;object_identity_confidence=0.0;create=1;release=1;use=0",
        triggered=False,
        target_id="T6_SAME_OBJECT_LIFECYCLE",
    )
    new = rec(
        "lifecycle_prefix=3;object_identity_confidence=1.0;create=1;release=1;use=1",
        triggered=True,
        target_id="T6_SAME_OBJECT_LIFECYCLE",
    )
    frontier = [seed_progress_record(old, tcir, plan_by_atom)]
    accepted, decision, seed_progress = progress_dominates_global(new, frontier, tcir, plan_by_atom)
    assert accepted is True
    assert decision.reason == "triggered"
    assert "object_identity_confidence" in decision.improved_components
    assert seed_progress.full_vector.object_identity_confidence >= 0.5


if __name__ == "__main__":
    tests = sorted((name, fn) for name, fn in globals().items() if name.startswith("test_") and callable(fn))
    for _, fn in tests:
        fn()
    print(f"{len(tests)} tests_passed")
