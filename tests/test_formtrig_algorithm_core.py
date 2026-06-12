import json
import sys
import tempfile
import zlib
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
    candidate_range_records,
    compute_signal_health,
    content_aware_candidate_ranges,
    decompose_tc,
    evaluate_operator_preconditions,
    missing_event_tokens,
    progress_dominates_global,
    progress_dominates,
    propose_mutations,
    registry,
    root_signature,
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


def test_root_signature_ignores_monitor_reach_trigger_counts():
    assert root_signature("PNG003_R=7;PNG003_T=0;R=1;T=0") == ""
    assert root_signature("PNG003_R=7;PNG003_T=0;R=1;T=0;plte_entries=7") == '{"plte_entries":"7"}'


def test_trigger_record_is_replay_verifiable_not_strict_rnt():
    rec = record("triggered", native_dt=0.0, reached=True, triggered=True)
    rec.replay_status = "executed_mutation"
    rec.metadata_status = "trigger_evidence_replayed"
    assert rec.replay_stable
    assert rec.reached_R and rec.triggered_T


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


def test_graph_does_not_treat_replay_provenance_as_runtime_producer():
    atom = decompose_tc("ctx.palette == NULL", "binary-state-null", "fresh.c:10")[0]
    rec = record("s1")
    rec.producer = "aflplusplus"
    graph = build_trigger_progress_graph(
        "T",
        {"target_location": "fresh.c:10", "canary_expression": "ctx.palette == NULL"},
        [atom],
        [rec],
    )
    assert not [node for node in graph.nodes if node["type"] == "producer_context"]
    provenance = [node for node in graph.nodes if node["type"] == "input_provenance_context"]
    assert len(provenance) == 1
    assert provenance[0]["binding_required"] is False
    assert not [
        edge
        for edge in graph.edges
        if edge.get("order") == "producer_before_guard"
    ]


def test_state_flip_root_or_producer_precondition_uses_root_state_without_runtime_producer():
    atom = decompose_tc("ctx.palette == NULL", "binary-state-null", "fresh.c:10")[0]
    rec = record("s1", root_state="R=1;T=0;palette_null=0;use_reached=1")
    rec.producer = "aflplusplus"
    graph = build_trigger_progress_graph(
        "T",
        {"target_location": "fresh.c:10", "canary_expression": "ctx.palette == NULL"},
        [atom],
        [rec],
    )
    precondition = evaluate_operator_preconditions(
        "optional-region deletion",
        atom,
        rec,
        graph,
    )
    assert precondition["checks"]["root_or_producer_state_observed"] is True
    assert precondition["satisfied"] is True


def test_graph_uses_only_explicit_external_producer_bindings_for_runtime_producer():
    atom = decompose_tc("ctx.palette == NULL", "binary-state-null", "fresh.c:10")[0]
    rec = record("s1")
    rec.producer = "aflplusplus"
    graph = build_trigger_progress_graph(
        "T",
        {
            "target_location": "fresh.c:10",
            "canary_expression": "ctx.palette == NULL",
            "producer_contexts": json.dumps(
                [
                    {
                        "label": "parse_palette",
                        "source_location": "fresh.c:7#parse_palette",
                        "confidence": "verified",
                    }
                ]
            ),
        },
        [atom],
        [rec],
    )
    producers = [node for node in graph.nodes if node["type"] == "producer_context"]
    assert len(producers) == 1
    assert producers[0]["label"] == "parse_palette"
    assert producers[0]["source_location"] == "fresh.c:7#parse_palette"
    assert producers[0]["binding_required"] is True
    assert [
        edge
        for edge in graph.edges
        if edge["src"] == producers[0]["id"] and edge.get("order") == "producer_before_guard"
    ]


def test_repair_hooks_require_external_metadata_not_format_name():
    atom = decompose_tc("tag == MAGIC", "equality/magic", "png.c:10")[0]
    rec = record("s1")
    no_hook_graph = build_trigger_progress_graph(
        "T",
        {"target_location": "png.c:10", "expected_input_format": "png"},
        [atom],
        [rec],
    )
    assert not [node for node in no_hook_graph.nodes if node["type"] == "repair_hook"]

    hook_graph = build_trigger_progress_graph(
        "T",
        {
            "target_location": "png.c:10",
            "expected_input_format": "png",
            "external_repair_hooks": json.dumps(
                [{"name": "png_crc_repair", "kind": "external_format_repair"}]
            ),
        },
        [atom],
        [rec],
    )
    hooks = [node for node in hook_graph.nodes if node["type"] == "repair_hook"]
    assert len(hooks) == 1
    assert hooks[0]["name"] == "png_crc_repair"
    assert hooks[0]["source"] == "external_metadata"


def test_graph_candidate_ranges_preserve_numeric_confidence_score():
    atom = decompose_tc("x < 1", "numeric-margin", "x.c:1")[0]
    rec = record("s1")
    rec.input_size = 16
    rec.raw["hot_ranges"] = json.dumps(
        [
            {"start": 4, "len": 2, "confidence": 0.84, "runtime_event_id": "lower_priority"},
            {"start": 8, "len": 2, "confidence": 0.92, "runtime_event_id": "higher_priority"},
        ]
    )
    graph = build_trigger_progress_graph("T", {"target_location": "x.c:1"}, [atom], [rec])
    ranges = candidate_range_records(rec, 16, graph)
    by_event = {item["runtime_event_id"]: item["confidence"] for item in ranges}
    assert by_event["lower_priority"] == 0.84
    assert by_event["higher_priority"] == 0.92


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    crc = zlib.crc32(kind + payload).to_bytes(4, "big")
    return len(payload).to_bytes(4, "big") + kind + payload + crc


def test_content_aware_png_mutation_avoids_signature_and_repairs_crc():
    atom = decompose_tc("row_factor_l == ((size_t)1 << 32)", "numeric-margin", "png.c:1")[0]
    data = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", b"\x00\x00\x00\x20\x00\x00\x00\x20\x08\x03\x00\x00\x00")
        + png_chunk(b"PLTE", b"\x00\x00\x00\xff\xff\xff")
        + png_chunk(b"IEND", b"")
    )
    ranges = content_aware_candidate_ranges(data, atom)
    assert ranges
    assert all(item["start"] >= 8 for item in ranges)
    assert ranges[0]["range_kind"] == "png_width"
    rec = record("s1")
    rec.input_size = len(data)
    graph = build_trigger_progress_graph("T", {"target_location": "png.c:1"}, [atom], [rec])
    with tempfile.TemporaryDirectory() as tmp:
        seed = Path(tmp) / "seed.png"
        seed.write_bytes(data)
        proposals = propose_mutations("T", atom, build_atom_plan("T", atom, compute_signal_health("T", atom, [rec])), rec, seed, graph, 1)
    proposal, mutated = proposals[0]
    assert proposal.mutated_ranges[0]["start"] != 0
    assert proposal.mutated_ranges[0]["format_family"] == "png"
    assert mutated is not None
    chunk_start = proposal.mutated_ranges[0]["start"] - 8
    length = int.from_bytes(mutated[chunk_start : chunk_start + 4], "big")
    crc_start = chunk_start + 8 + length
    assert mutated[crc_start : crc_start + 4] == zlib.crc32(mutated[chunk_start + 4 : crc_start]).to_bytes(4, "big")


def test_lifted_png_field_hot_range_repairs_containing_chunk_crc():
    atom = decompose_tc("row_width * pixel_depth != wide_product", "numeric-margin", "png.c:1")[0]
    data = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", b"\x00\x00\x00\x20\x00\x00\x00\x20\x08\x03\x00\x00\x00")
        + png_chunk(b"IEND", b"")
    )
    rec = record("s1")
    rec.input_size = len(data)
    rec.raw["hot_ranges"] = '[{"start":16,"len":4,"confidence":0.95,"runtime_event_id":"IHDR_width","range_kind":"png_width","source":"png_lifted_observer"}]'
    graph = build_trigger_progress_graph("T", {"target_location": "png.c:1"}, [atom], [rec])
    with tempfile.TemporaryDirectory() as tmp:
        seed = Path(tmp) / "seed.png"
        seed.write_bytes(data)
        proposals = propose_mutations("T", atom, build_atom_plan("T", atom, compute_signal_health("T", atom, [rec])), rec, seed, graph, 1)
    proposal, mutated = proposals[0]
    assert proposal.mutated_ranges[0]["source"] == "png_lifted_observer"
    assert proposal.mutated_ranges[0]["format_family"] == "png"
    assert mutated is not None
    ihdr_start = 8
    ihdr_len = int.from_bytes(mutated[ihdr_start : ihdr_start + 4], "big")
    crc_start = ihdr_start + 8 + ihdr_len
    assert mutated[crc_start : crc_start + 4] == zlib.crc32(mutated[ihdr_start + 4 : crc_start]).to_bytes(4, "big")


def test_proposals_diversify_operators_under_small_budget():
    atom = decompose_tc("row_width * pixel_depth != wide_product", "numeric-margin", "png.c:1")[0]
    data = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", b"\x00\x00\x00\x20\x00\x00\x00\x20\x08\x03\x00\x00\x00")
        + png_chunk(b"IEND", b"")
    )
    rec = record("s1")
    rec.input_size = len(data)
    rec.raw["hot_ranges"] = '[{"start":16,"len":4,"confidence":0.95,"runtime_event_id":"IHDR_width","range_kind":"png_width","source":"png_lifted_observer"}]'
    graph = build_trigger_progress_graph("T", {"target_location": "png.c:1"}, [atom], [rec])
    with tempfile.TemporaryDirectory() as tmp:
        seed = Path(tmp) / "seed.png"
        seed.write_bytes(data)
        proposals = propose_mutations("T", atom, build_atom_plan("T", atom, compute_signal_health("T", atom, [rec])), rec, seed, graph, 4)
    names = [proposal.operator_name for proposal, _ in proposals]
    assert "boundary write" in names
    assert any(name in names for name in ["arithmetic perturbation", "numeric byte increment", "endian variants"])


def test_png_numeric_field_small_step_mutates_least_significant_byte():
    atom = decompose_tc("row_width * pixel_depth != wide_product", "numeric-margin", "png.c:1")[0]
    data = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", b"\x00\x00\x00\x20\x00\x00\x00\x20\x08\x03\x00\x00\x00")
        + png_chunk(b"IEND", b"")
    )
    rec = record("s1")
    rec.input_size = len(data)
    rec.raw["hot_ranges"] = '[{"start":16,"len":4,"confidence":0.95,"runtime_event_id":"IHDR_width","range_kind":"png_width","source":"png_lifted_observer"}]'
    graph = build_trigger_progress_graph("T", {"target_location": "png.c:1"}, [atom], [rec])
    with tempfile.TemporaryDirectory() as tmp:
        seed = Path(tmp) / "seed.png"
        seed.write_bytes(data)
        proposals = propose_mutations("T", atom, build_atom_plan("T", atom, compute_signal_health("T", atom, [rec])), rec, seed, graph, 4)
    small_step = next(mutated for proposal, mutated in proposals if proposal.operator_name in {"arithmetic perturbation", "numeric byte increment"})
    assert small_step is not None
    assert int.from_bytes(small_step[16:20], "big") == 33


def test_lifted_png_missing_exif_promotes_valid_chunk_insertion():
    atom = decompose_tc("info_ptr->eXIf_buf != NULL", "binary-state-null", "png.c:1")[0]
    data = (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", b"\x00\x00\x00\x20\x00\x00\x00\x20\x08\x03\x00\x00\x00")
        + png_chunk(b"IDAT", b"x\x9cc``\x00\x00\x00\x04\x00\x01")
        + png_chunk(b"IEND", b"")
    )
    rec = record("s1", root_state="R=1;T=0;format_family=png;exif_seen=0;use_reached=1")
    rec.input_size = len(data)
    rec.raw["hot_ranges"] = '[{"start":33,"len":1,"confidence":0.8,"runtime_event_id":"IDAT_insert_before","range_kind":"png_chunk_insert_before_idat","source":"png_lifted_observer"}]'
    graph = build_trigger_progress_graph("T", {"target_location": "png.c:1"}, [atom], [rec])
    with tempfile.TemporaryDirectory() as tmp:
        seed = Path(tmp) / "seed.png"
        seed.write_bytes(data)
        proposals = propose_mutations("T", atom, build_atom_plan("T", atom, compute_signal_health("T", atom, [rec])), rec, seed, graph, 2)
    proposal, mutated = proposals[0]
    assert proposal.operator_name == "event insertion"
    assert proposal.details["lift_guided_operator"] is True
    assert mutated is not None
    assert b"eXIf" in mutated
    exif_pos = mutated.index(b"eXIf") - 4
    exif_len = int.from_bytes(mutated[exif_pos : exif_pos + 4], "big")
    crc_start = exif_pos + 8 + exif_len
    assert mutated[crc_start : crc_start + 4] == zlib.crc32(mutated[exif_pos + 4 : crc_start]).to_bytes(4, "big")


def test_lifted_xml_missing_entity_promotes_event_insertion():
    atom = decompose_tc("entity->etype == XML_EXTERNAL_PARAMETER_ENTITY", "compound-sequence-lifecycle", "xml.c:1")[0]
    data = b"<r/>"
    rec = record("xml_seed", root_state="R=1;T=0;format_family=xml;xml_doctype_seen=0;xml_parameter_entity_seen=0;xml_external_entity_seen=0;xml_entity_ref_seen=0")
    rec.input_size = len(data)
    rec.raw["hot_ranges"] = '[{"start":0,"len":1,"confidence":0.7,"runtime_event_id":"xml_document_prefix","range_kind":"xml_document_prefix","source":"xml_lifted_observer","format_family":"xml"}]'
    graph = build_trigger_progress_graph("T", {"target_location": "xml.c:1"}, [atom], [rec])
    with tempfile.TemporaryDirectory() as tmp:
        seed = Path(tmp) / "seed.xml"
        seed.write_bytes(data)
        proposals = propose_mutations("T", atom, build_atom_plan("T", atom, compute_signal_health("T", atom, [rec])), rec, seed, graph, 2)
    proposal, mutated = proposals[0]
    assert proposal.operator_name == "event insertion"
    assert proposal.details["lift_guided_operator"] is True
    assert mutated is not None
    assert b"<!DOCTYPE" in mutated
    assert b"<!ENTITY %" in mutated


def test_lifted_sql_missing_blob_promotes_event_insertion():
    atom = decompose_tc("ExpandBlob(pVal)", "compound-sequence-lifecycle", "sqlite.c:1")[0]
    data = b"CREATE TABLE t(x);"
    rec = record("sql_seed", root_state="R=1;T=0;format_family=sql;sql_expression_intent=blob;sql_blob_seen=0;use_reached=1")
    rec.input_size = len(data)
    rec.raw["hot_ranges"] = '[{"start":16,"len":1,"confidence":0.7,"runtime_event_id":"sql_insert","range_kind":"sql_phase_token","source":"sql_expression_lifted_observer","format_family":"sql"}]'
    graph = build_trigger_progress_graph("T", {"target_location": "sqlite.c:1"}, [atom], [rec])
    with tempfile.TemporaryDirectory() as tmp:
        seed = Path(tmp) / "seed.sql"
        seed.write_bytes(data)
        proposals = propose_mutations("T", atom, build_atom_plan("T", atom, compute_signal_health("T", atom, [rec])), rec, seed, graph, 2)
    proposal, mutated = proposals[0]
    assert proposal.operator_name == "event insertion"
    assert proposal.details["lift_guided_operator"] is True
    assert mutated is not None
    assert mutated.startswith(data)
    assert b"zeroblob" in mutated


def test_lifted_sql_missing_quoted_token_uses_self_contained_statement():
    atom = decompose_tc("dequote == 0", "equality/magic", "sqlite.c:1")[0]
    data = b"SELECT 1;"
    rec = record("sql_quote", root_state="R=1;T=0;format_family=sql;sql_expression_intent=quoted_token;sql_quoted_token_seen=0;use_reached=1")
    rec.input_size = len(data)
    rec.raw["hot_ranges"] = '[{"start":0,"len":6,"confidence":0.7,"runtime_event_id":"sql_select","range_kind":"sql_select","source":"sql_expression_lifted_observer","format_family":"sql"}]'
    graph = build_trigger_progress_graph("T", {"target_location": "sqlite.c:1"}, [atom], [rec])
    with tempfile.TemporaryDirectory() as tmp:
        seed = Path(tmp) / "seed.sql"
        seed.write_bytes(data)
        proposals = propose_mutations("T", atom, build_atom_plan("T", atom, compute_signal_health("T", atom, [rec])), rec, seed, graph, 2)
    proposal, mutated = proposals[0]
    assert proposal.operator_name == "event insertion"
    assert mutated is not None
    assert mutated.startswith(data)
    assert b"SELECT 'formtrig';" in mutated


def test_content_aware_sql_ranges_pick_literals_not_script_prefix():
    atom = decompose_tc("pNew->nLSlot < (pNew->nLTerm+1)", "compound-sequence-lifecycle", "where.c:1")[0]
    data = b"CREATE TABLE t1(a INT); INSERT INTO t1 VALUES(123); ANALYZE; SELECT * FROM t1 WHERE a=123;\n"
    ranges = content_aware_candidate_ranges(data, atom)
    assert ranges
    assert all(item["start"] > 0 for item in ranges)
    assert any(item["range_kind"] == "numeric_literal" for item in ranges)


def test_content_aware_sql_ranges_preserve_byte_offsets_with_binary_prefix():
    atom = decompose_tc("dequote == 0", "equality/magic", "sqlite.c:1")[0]
    data = b"\xff\nSELECT 'a' COLLATE \"nocase\";"
    ranges = content_aware_candidate_ranges(data, atom)
    quoted = [item for item in ranges if item["range_kind"] == "quoted_value"]
    assert quoted
    spans = {(item["start"], item["length"]) for item in quoted}
    assert (10, 1) in spans
    assert (22, 6) in spans
    assert data[10:11] == b"a"
    assert data[22:28] == b"nocase"


def test_lifted_text_length_expansion_hot_range_inserts_token():
    atom = decompose_tc("size - strlen(buf) <= 2", "numeric-margin", "xml.c:1")[0]
    data = b"<!DOCTYPE doc [<!ELEMENT doc (a)>]><doc/>"
    rec = record(
        "xml_len",
        native_dt=5.0,
        root_state="R=1;T=0;format_family=xml;xml_length_pressure=12;operand_binding_confidence=0.65",
    )
    rec.input_size = len(data)
    rec.raw["hot_ranges"] = json.dumps(
        [
            {
                "start": 10,
                "len": 3,
                "confidence": 0.85,
                "runtime_event_id": "xml_element_name",
                "range_kind": "xml_element_name",
                "source": "xml_structural_lifted_observer",
                "format_family": "xml",
                "mutation_strategy": "text_length_expansion",
                "insert_token": "formtrig",
            }
        ]
    )
    graph = build_trigger_progress_graph("T", {"target_location": "xml.c:1"}, [atom], [rec])
    with tempfile.TemporaryDirectory() as tmp:
        seed = Path(tmp) / "seed.xml"
        seed.write_bytes(data)
        proposals = propose_mutations("T", atom, build_atom_plan("T", atom, compute_signal_health("T", atom, [rec])), rec, seed, graph, 2)
    assert any(mutated is not None and len(mutated) > len(data) and b"formtrig" in mutated for _, mutated in proposals)
    assert any(proposal.details.get("mutation_strategy") == "text_length_expansion" for proposal, _ in proposals)


def test_lifted_integer_boundary_hot_range_writes_full_endian_field():
    atom = decompose_tc("paf_fmt.channels < 1", "numeric-margin", "audio.c:1")[0]
    data = b" paf" + (0).to_bytes(4, "big") + (0).to_bytes(4, "big") + (16000).to_bytes(4, "big") + (1).to_bytes(4, "big") + (1).to_bytes(4, "big")
    rec = record(
        "audio_seed",
        root_state="R=1;T=0;format_family=audio;audio_channels=1;audio_channel_guard_margin=1;operand_binding_confidence=0.85",
    )
    rec.input_size = len(data)
    rec.raw["hot_ranges"] = json.dumps(
        [
            {
                "start": 16,
                "len": 4,
                "confidence": 0.92,
                "runtime_event_id": "audio_channels",
                "range_kind": "audio_channels",
                "source": "audio_header_lifted_observer",
                "format_family": "audio",
                "mutation_strategy": "integer_boundary",
                "integer_width": 4,
                "integer_endian": "big",
                "integer_values": [0, 1, 1025],
            }
        ]
    )
    graph = build_trigger_progress_graph("T", {"target_location": "audio.c:1"}, [atom], [rec])
    with tempfile.TemporaryDirectory() as tmp:
        seed = Path(tmp) / "seed.paf"
        seed.write_bytes(data)
        proposals = propose_mutations("T", atom, build_atom_plan("T", atom, compute_signal_health("T", atom, [rec])), rec, seed, graph, 8)
    integer_proposal = next((item for item in proposals if item[0].details.get("mutation_strategy") == "integer_boundary"), None)
    assert integer_proposal is not None
    proposal, mutated = integer_proposal
    assert proposal.details["integer_value"] == 0
    assert mutated is not None
    assert mutated[16:20] == b"\x00\x00\x00\x00"


def test_lifted_integer_boundary_values_rotate_across_operators():
    atom = decompose_tc("paf_fmt.channels < 1", "numeric-margin", "audio.c:1")[0]
    data = b" paf" + (0).to_bytes(4, "big") + (0).to_bytes(4, "big") + (16000).to_bytes(4, "big") + (1).to_bytes(4, "big") + (1).to_bytes(4, "big")
    rec = record(
        "audio_seed",
        root_state="R=1;T=0;format_family=audio;audio_channels=1;audio_channel_guard_margin=1;operand_binding_confidence=0.85",
    )
    rec.input_size = len(data)
    rec.raw["hot_ranges"] = json.dumps(
        [
            {
                "start": 16,
                "len": 4,
                "confidence": 0.92,
                "runtime_event_id": "audio_channels",
                "range_kind": "audio_channels",
                "source": "audio_header_lifted_observer",
                "format_family": "audio",
                "mutation_strategy": "integer_boundary",
                "integer_width": 4,
                "integer_endian": "big",
                "integer_values": [10, 11, 12, 13],
            }
        ]
    )
    graph = build_trigger_progress_graph("T", {"target_location": "audio.c:1"}, [atom], [rec])
    with tempfile.TemporaryDirectory() as tmp:
        seed = Path(tmp) / "seed.paf"
        seed.write_bytes(data)
        proposals = propose_mutations("T", atom, build_atom_plan("T", atom, compute_signal_health("T", atom, [rec])), rec, seed, graph, 4)
    values = [proposal.details.get("integer_value") for proposal, _ in proposals if proposal.details.get("mutation_strategy") == "integer_boundary"]
    assert values[:4] == [10, 11, 12, 13]


def test_lifted_integer_boundary_applies_to_state_operator_ranges():
    atom = decompose_tc("stripsperplane == 0", "binary-state-null", "tif_read.c:501")[0]
    data = b"II*\x00" + (34).to_bytes(4, "little") + b"\x00" * 16
    rec = record(
        "tiff_state_seed",
        root_state=(
            "R=1;T=0;format_family=tiff;tiff_numeric_intent=strip_geometry;"
            "tiff_strips_per_plane=2;producer_state=tiff_ifd;use_reached=1;guard_satisfied=1"
        ),
    )
    rec.input_size = len(data)
    rec.raw["hot_ranges"] = json.dumps(
        [
            {
                "start": 4,
                "len": 4,
                "confidence": 0.86,
                "runtime_event_id": "tiff_rows_per_strip",
                "range_kind": "tiff_rows_per_strip",
                "source": "tiff_ifd_lifted_observer",
                "format_family": "tiff",
                "mutation_strategy": "integer_boundary",
                "integer_width": 4,
                "integer_endian": "little",
                "integer_values": [60, 61, 0],
            }
        ]
    )
    graph = build_trigger_progress_graph("T", {"target_location": "tif_read.c:501"}, [atom], [rec])
    with tempfile.TemporaryDirectory() as tmp:
        seed = Path(tmp) / "seed.tif"
        seed.write_bytes(data)
        proposals = propose_mutations("T", atom, build_atom_plan("T", atom, compute_signal_health("T", atom, [rec])), rec, seed, graph, 8)
    projected = next((item for item in proposals if item[0].details.get("mutation_strategy") == "integer_boundary"), None)
    assert projected is not None
    proposal, mutated = projected
    assert proposal.details["integer_boundary_applied_to_operator"] != "boundary_write"
    assert proposal.details["integer_value"] == 60
    assert mutated is not None
    assert mutated[4:8] == (60).to_bytes(4, "little")


def test_lifted_integer_boundary_covers_multiple_root_ranges_under_small_budget():
    atom = decompose_tc("nstrips > 1000000", "compound-sequence-lifecycle", "tif_dirread.c:5850")[0]
    data = b"II*\x00" + (8).to_bytes(4, "little") + b"\x00" * 128
    rec = record(
        "tiff_multi_root_seed",
        root_state=(
            "R=1;T=0;format_family=tiff;tiff_numeric_intent=strip_chop;"
            "tiff_chop_nstrips=1000;tiff_chop_nstrips_gap=999001;"
            "producer_state=tiff_ifd;use_reached=1;guard_satisfied=1;object_identity_confidence=0.85"
        ),
    )
    rec.input_size = len(data)
    rec.raw["hot_ranges"] = json.dumps(
        [
            {
                "start": 32,
                "len": 4,
                "confidence": 0.86,
                "runtime_event_id": "tiff_rows_per_strip",
                "range_kind": "tiff_rows_per_strip",
                "source": "tiff_ifd_lifted_observer",
                "format_family": "tiff",
                "mutation_strategy": "integer_boundary",
                "integer_width": 4,
                "integer_endian": "little",
                "integer_values": [1, 2, 0],
                "root_priority": 0,
            },
            {
                "start": 44,
                "len": 4,
                "confidence": 0.86,
                "runtime_event_id": "tiff_image_length",
                "range_kind": "tiff_image_length",
                "source": "tiff_ifd_lifted_observer",
                "format_family": "tiff",
                "mutation_strategy": "integer_boundary",
                "integer_width": 4,
                "integer_endian": "little",
                "integer_values": [1_000_001, 1_000_000, 999_999],
                "root_priority": 1,
            },
        ]
    )
    graph = build_trigger_progress_graph("T", {"target_location": "tif_dirread.c:5850"}, [atom], [rec])
    with tempfile.TemporaryDirectory() as tmp:
        seed = Path(tmp) / "seed.tif"
        seed.write_bytes(data)
        proposals = propose_mutations("T", atom, build_atom_plan("T", atom, compute_signal_health("T", atom, [rec])), rec, seed, graph, 8)
    integer_ranges = [
        proposal.details.get("range_kind")
        for proposal, _ in proposals
        if proposal.details.get("mutation_strategy") == "integer_boundary"
    ]
    assert "tiff_rows_per_strip" in integer_ranges
    assert "tiff_image_length" in integer_ranges


def test_lifted_missing_event_tokens_promote_insertion_operator():
    atom = decompose_tc("t3GlyphStack == nullptr", "binary-state-null", "pdf.cc:1")[0]
    data = b"%PDF-1.4\n1 0 obj << /Type /Font /Subtype /Type3 /CharProcs << >> >> endobj\nstream\nendstream\n"
    rec = record(
        "pdf_seed",
        root_state=(
            "R=1;T=0;format_family=pdf;pdf_type3_seen=1;pdf_charprocs_seen=1;"
            "pdf_glyph_seen=0;use_reached=1;guard_satisfied=1;lifecycle_prefix=4"
        ),
    )
    rec.input_size = len(data)
    rec.raw["hot_ranges"] = '[{"start":9,"len":24,"confidence":0.8,"runtime_event_id":"pdf_font","range_kind":"pdf_token","format_family":"pdf"}]'
    graph = build_trigger_progress_graph(
        "T",
        {"target_location": "pdf.cc:1", "canary_expression": "t3GlyphStack == nullptr", "expected_input_format": "PDF file"},
        [atom],
        [rec],
    )
    plan = build_atom_plan("T", atom, compute_signal_health("T", atom, [rec]))
    assert "event insertion" not in plan.mutator_operators
    with tempfile.TemporaryDirectory() as tmp:
        seed = Path(tmp) / "seed.pdf"
        seed.write_bytes(data)
        proposals = propose_mutations("T", atom, plan, rec, seed, graph, 2)
    assert proposals
    proposal, mutated = proposals[0]
    assert proposal.operator_name == "event insertion"
    assert proposal.details["lift_guided_operator"] is True
    assert proposal.details["missing_event_token_count"] >= 1
    assert mutated is not None
    assert b"BuildGlyph" in mutated or b"BuildChar" in mutated or b"glyph" in mutated


def test_tcir_preserves_any_of_without_dnf_expansion():
    tcir = build_tcir("len > cap && (state == READY || state == PARTIAL)", "numeric-margin", "x.c:1")
    assert len(tcir.atoms) == 3
    group_types = {group.group_type for group in tcir.groups}
    assert "ALL_OF" in group_types
    assert "ANY_OF" in group_types
    any_groups = [group for group in tcir.groups if group.group_type == "ANY_OF"]
    assert len(any_groups) == 1
    assert len(any_groups[0].children) == 2


def test_any_of_branch_selection_uses_atom_local_root_distance():
    tcir = build_tcir("tag == 'A' || tag == 'B'", "equality/magic", "x.c:1")
    records = [
        record("near_a", native_dt=99.0, root_state="tag=63;use_reached=1"),
        record("near_b", native_dt=99.0, root_state="tag=68;use_reached=1"),
    ]
    plans = {atom.atom_id: build_atom_plan("T", atom, compute_signal_health("T", atom, records, [], n_min=1, e_min=0)) for atom in tcir.atoms}
    _, _, near_a = progress_dominates_global(records[0], [], tcir, plans)
    _, _, near_b = progress_dominates_global(records[1], [], tcir, plans)
    assert near_a.full_vector.selected_branch == "a1"
    assert near_b.full_vector.selected_branch == "a2"
    assert near_a.full_vector.atom_vectors["a1"]["lifted_df"] < near_a.full_vector.atom_vectors["a2"]["lifted_df"]
    assert near_b.full_vector.atom_vectors["a2"]["lifted_df"] < near_b.full_vector.atom_vectors["a1"]["lifted_df"]


def test_global_dominance_accepts_same_bucket_native_distance_improvement():
    tcir = build_tcir("row_factor_l == 4294967296", "numeric-margin", "png.c:1")
    old = record("old", native_dt=32.0, root_state="row_factor_l=33;target_margin=4294967263")
    new = record("new", native_dt=31.95, root_state="row_factor_l=134744073;target_margin=4160223223")
    plans = {atom.atom_id: build_atom_plan("T", atom, compute_signal_health("T", atom, [old], [], n_min=1, e_min=0)) for atom in tcir.atoms}
    _, _, old_seed = progress_dominates_global(old, [], tcir, plans)
    accepted, decision, _ = progress_dominates_global(new, [old_seed], tcir, plans)
    assert accepted
    assert decision.reason == "lifted-feature improvement"
    assert "lifted_df" in decision.improved_components


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
    tcir = build_tcir(
        "create(obj) before release(obj) before use(obj) && SAME_OBJECT(obj)",
        "compound-sequence-lifecycle",
        "uaf.c:1;uaf.c:2;uaf.c:3;uaf.c:4",
    )
    same_edges = [edge for edge in tcir.edges if edge.edge_type == "SAME_OBJECT"]
    assert same_edges
    assert all(edge.src != edge.dst for edge in same_edges)


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


def test_lifecycle_progress_in_new_identity_bucket_names_real_components():
    tcir = build_tcir("pNew->nLSlot < (pNew->nLTerm+1)", "compound-sequence-lifecycle", "where.c:1")
    old = record("old", root_state="R=1;T=0", coverage_hash="monitor_row:old")
    new = record(
        "new",
        native_dt=0.0,
        root_state=(
            "create_table=1;create_index=1;insert=1;analyze=1;stat1=1;"
            "select_where=1;order_by=1;lifecycle_prefix=6;"
            "object_identity_confidence=1;phase_novelty=1"
        ),
        coverage_hash="monitor_row:new",
    )
    plans = {atom.atom_id: build_atom_plan("T", atom, compute_signal_health("T", atom, [old], [], n_min=1, e_min=0)) for atom in tcir.atoms}
    _, _, old_seed = progress_dominates_global(old, [], tcir, plans)
    accepted, decision, _ = progress_dominates_global(new, [old_seed], tcir, plans)
    assert accepted
    assert decision.reason == "lifecycle-prefix improvement"
    assert "frontier_seed" not in decision.improved_components
    assert "lifecycle_prefix" in decision.improved_components
    assert "object_identity_confidence" in decision.improved_components


def test_lifecycle_registry_has_object_identity_alignment_operator():
    mutators = registry()["compound-sequence-lifecycle"]["mutators"]
    names = {item["name"] for item in mutators}
    assert "object-identity alignment" in names


def test_text_like_lift_can_insert_tcir_root_variable_tokens():
    tcir = build_tcir(
        "malformed record creates comment ownership state before destroy",
        "compound-sequence-lifecycle",
        "rec.c:1",
    )
    atom = tcir.atoms[0]
    rec = record("r", root_state="R=1;T=0;format_family=record_text")
    tokens = missing_event_tokens(rec, atom)
    assert b" comment " in tokens
    assert b" record " in tokens


if __name__ == "__main__":
    tests = sorted((name, fn) for name, fn in globals().items() if name.startswith("test_") and callable(fn))
    for name, fn in tests:
        fn()
    print(f"{len(tests)} tests_passed")
