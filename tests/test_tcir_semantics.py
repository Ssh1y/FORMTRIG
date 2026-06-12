import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.formtrig_algorithm_core import ReplayRecord, atom_observation, build_tcir


def record(root_state: str) -> ReplayRecord:
    return ReplayRecord(
        target_id="T",
        seed_id="s",
        parent_seed_id="ROOT",
        content_sha256="s",
        input_size=4,
        reached_R=True,
        triggered_T=False,
        reached_count=1,
        triggered_count=0,
        time_s=0.0,
        coverage_hash="semantic:test",
        native_DT=1.0,
        dt_bucket=1,
        tc_root_state=root_state,
        replay_hash="s",
        replay_status="kept_rnt",
        metadata_status="verified_rnt",
        source_seedbank="",
        source_manifest="",
        source_seed="",
        producer="test",
    )


def test_pointer_access_is_not_sequence():
    tcir = build_tcir("ptr->field == NULL", "binary-state-null", "x.c:1")
    assert tcir.groups[0].group_type == "ALL_OF"
    assert len(tcir.atoms) == 1


def test_char_equality_has_no_numeric_secondary_tag():
    tcir = build_tcir("hdr == 'G'", "equality/magic", "x.c:1")
    atom = tcir.atoms[0]
    assert atom.category == "equality/magic"
    assert atom.secondary_categories == []


def test_null_check_is_binary_without_numeric_secondary_tag():
    tcir = build_tcir("ctx.obj == NULL", "binary-state-null", "x.c:1")
    atom = tcir.atoms[0]
    assert atom.category == "binary-state-null"
    assert atom.secondary_categories == []


def test_numeric_manifest_category_dominates_numeric_equality_shape():
    tcir = build_tcir("row_factor_l == ((size_t)1 << (sizeof(png_uint_32) * 8))", "numeric-margin", "x.c:1")
    atom = tcir.atoms[0]
    assert atom.category == "numeric-margin"


def test_lifecycle_manifest_category_dominates_scalar_relation_shape():
    tcir = build_tcir("pNew->nLSlot < (pNew->nLTerm+1)", "compound-sequence-lifecycle", "x.c:1")
    atom = tcir.atoms[0]
    assert atom.category == "compound-sequence-lifecycle"


def test_mixed_tc_uses_per_atom_categories_not_target_primary():
    tcir = build_tcir(
        "flag == 1 && len > cap && ctx.obj == NULL",
        "compound-sequence-lifecycle",
        "x.c:1;x.c:2;x.c:3",
    )
    categories = {atom.expression: atom.category for atom in tcir.atoms}
    assert categories["flag == 1"] == "equality/magic"
    assert categories["len > cap"] == "numeric-margin"
    assert categories["ctx.obj == NULL"] == "binary-state-null"


def test_pointer_field_equality_is_not_numeric_from_arrow():
    tcir = build_tcir("obj->state == READY && len > cap", "compound-sequence-lifecycle", "x.c:1;x.c:2")
    categories = {atom.expression: atom.category for atom in tcir.atoms}
    assert categories["obj->state == READY"] == "equality/magic"


def test_same_object_links_multiple_event_atoms():
    tcir = build_tcir(
        "create(obj) before release(obj) before use(obj) && SAME_OBJECT(obj)",
        "compound-sequence-lifecycle",
        "x.c:1;x.c:2;x.c:3;x.c:4",
    )
    same_edges = [edge for edge in tcir.edges if edge.edge_type == "SAME_OBJECT"]
    assert same_edges
    assert all(edge.src != edge.dst for edge in same_edges)
    linked = {edge.src for edge in same_edges} | {edge.dst for edge in same_edges}
    event_atoms = {atom.atom_id for atom in tcir.atoms if atom.root_events and atom.expression != "SAME_OBJECT(obj)"}
    assert len(linked & event_atoms) >= 2


def test_guard_false_blocks_guarded_atom():
    tcir = build_tcir("hdr == 'G' && ctx.obj == NULL", "binary-state-null", "x.c:1;x.c:2")
    guarded = next(atom for atom in tcir.atoms if atom.category == "binary-state-null")
    obs = atom_observation(record("hdr=72;hdr_is_G=0;obj_null=1;use_reached=0;blocked_by_guard=1"), guarded, tcir)
    assert obs.status == "BLOCKED_BY_GUARD"


if __name__ == "__main__":
    tests = sorted((name, fn) for name, fn in globals().items() if name.startswith("test_") and callable(fn))
    for _, fn in tests:
        fn()
    print(f"{len(tests)} tests_passed")
