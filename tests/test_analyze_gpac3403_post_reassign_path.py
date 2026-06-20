import importlib.util
import json
import sys
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "analyze_gpac3403_post_reassign_path.py"


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_event_map(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "binding_id,atom_id,category,role,event_kind,site_id,event_id,mapping_status,collapsed_with,binding_tier,lift_allowed,reason,component_kind,priority,direction,value_mode,function,file,line,column,opcode,observe_window",
                "gpac_sample_release_data_object_value,1,compound-sequence-lifecycle,lifecycle_event,7,3013921722,0000000000001001,exact,0x00000000,B4,true,ok,8,26,higher,a,gf_isom_sample_del,isomedia/isom_read.c,112,6,icmp,any",
                "gpac_dynamic_bitstream_external_buffer_same_object,1,compound-sequence-lifecycle,same_object,7,1549213408,0000000000001002,exact,0x00000000,B4,true,ok,8,60,higher,a,gf_bs_reassign_buffer,utils/bitstream.c,122,6,icmp,any",
                "gpac_bitstream_original_cleanup_object_value,1,compound-sequence-lifecycle,use,7,65063371,0000000000001003,exact,0x00000000,B4,true,ok,8,42,higher,a,gf_bs_del,utils/bitstream.c,372,48,icmp,any",
                "gpac_nalu_out_reassign_fallback_lifecycle_event,1,compound-sequence-lifecycle,lifecycle_event,8,1766076671,0000000000001004,exact,0x00000000,B4,true,ok,7,30,higher,hit,gf_isom_nalu_sample_rewrite,isomedia/avc_ext.c,672,59,br,any",
                "gpac_hevc_extractor_error_pre_detach_producer,1,compound-sequence-lifecycle,desired_producer,8,3035684152,0000000000001005,exact,0x00000000,B4,true,ok,6,32,higher,outcome,gf_isom_nalu_sample_rewrite,isomedia/avc_ext.c,809,9,br,any",
                "gpac_invalid_nal_size_pre_detach_producer,1,compound-sequence-lifecycle,desired_producer,8,4008811561,0000000000001006,exact,0x00000000,B4,true,ok,6,34,higher,outcome,gf_isom_nalu_sample_rewrite,isomedia/avc_ext.c,844,9,br,any",
                "gpac_final_normal_get_content_absent,1,compound-sequence-lifecycle,opposite_producer,8,224520426,0000000000001007,exact,0x00000000,B4,true,ok,6,36,higher,absent,gf_isom_nalu_sample_rewrite,isomedia/avc_ext.c,912,6,br,any",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def component(source_id: int, value: int, priority: int = 1) -> dict:
    return {"source_id": source_id, "value": value, "priority": priority}


def write_runtime(path: Path, components: list[dict]) -> None:
    path.write_text(
        json.dumps(
            {
                "reached": True,
                "D_F_spec_lifted": 2,
                "trace_signature": "0xabc",
                "components": components,
            }
        )
        + "\n",
        encoding="utf-8",
    )


class AnalyzeGpac3403PostReassignPathTest(unittest.TestCase):
    def test_reports_missing_pre_detach_error_when_only_absence_and_alias_gap_seen(self):
        tool = load_module(TOOL, "gpac3403_post_reassign_missing")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            event_map = root / "map.csv"
            runtime = root / "runtime.jsonl"
            write_event_map(event_map)
            write_runtime(
                runtime,
                [
                    component(0x1001, 0x20000),
                    component(0x1002, 0x20000),
                    component(0x1003, 0x18000),
                    component(0x1007, 1),
                ],
            )
            args = type(
                "Args",
                (),
                {
                    "runtime_event_map": event_map,
                    "runtime_jsonl": [runtime],
                    "records": None,
                    "record_limit": 3,
                },
            )
            report = tool.build_report(args)

        self.assertEqual(report["verdict"]["status"], "pre_detach_error_missing")
        self.assertEqual(report["totals"]["normal_detach_absent_records"], 1)
        self.assertEqual(report["totals"]["release_reassign_same_records"], 1)
        self.assertEqual(report["totals"]["reassign_cleanup_same_records"], 0)

    def test_alias_cleanup_closure_takes_precedence(self):
        tool = load_module(TOOL, "gpac3403_post_reassign_closed")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            event_map = root / "map.csv"
            runtime = root / "runtime.jsonl"
            write_event_map(event_map)
            write_runtime(
                runtime,
                [
                    component(0x1001, 0x20000),
                    component(0x1002, 0x20000),
                    component(0x1003, 0x20000),
                    component(0x1005, 1),
                    component(0x1007, 1),
                ],
            )
            args = type(
                "Args",
                (),
                {
                    "runtime_event_map": event_map,
                    "runtime_jsonl": [runtime],
                    "records": None,
                    "record_limit": 3,
                },
            )
            report = tool.build_report(args)

        self.assertEqual(report["verdict"]["status"], "alias_cleanup_closure_observed")
        self.assertEqual(report["totals"]["pre_detach_error_records"], 1)
        self.assertEqual(report["totals"]["reassign_cleanup_same_records"], 1)

    def test_normal_detach_observed_when_absence_component_is_missing(self):
        tool = load_module(TOOL, "gpac3403_post_reassign_normal_detach")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            event_map = root / "map.csv"
            runtime = root / "runtime.jsonl"
            write_event_map(event_map)
            write_runtime(
                runtime,
                [
                    component(0x1001, 0x20000),
                    component(0x1002, 0x20000),
                    component(0x1003, 0x18000),
                    component(0x1005, 1),
                ],
            )
            args = type(
                "Args",
                (),
                {
                    "runtime_event_map": event_map,
                    "runtime_jsonl": [runtime],
                    "records": None,
                    "record_limit": 3,
                },
            )
            report = tool.build_report(args)

        self.assertEqual(report["verdict"]["status"], "normal_detach_path_observed")
        self.assertEqual(report["totals"]["normal_detach_absent_records"], 0)
        self.assertEqual(report["totals"]["pre_detach_error_records"], 1)

    def test_pre_detach_guard_observed_with_zero_value_is_not_satisfied(self):
        tool = load_module(TOOL, "gpac3403_post_reassign_zero_guard")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            event_map = root / "map.csv"
            runtime = root / "runtime.jsonl"
            write_event_map(event_map)
            write_runtime(
                runtime,
                [
                    component(0x1001, 0x20000),
                    component(0x1002, 0x20000),
                    component(0x1003, 0x18000),
                    component(0x1005, 0),
                    component(0x1007, 1),
                ],
            )
            args = type(
                "Args",
                (),
                {
                    "runtime_event_map": event_map,
                    "runtime_jsonl": [runtime],
                    "records": None,
                    "record_limit": 3,
                },
            )
            report = tool.build_report(args)

        self.assertEqual(report["verdict"]["status"], "pre_detach_error_missing")
        self.assertEqual(report["totals"]["pre_detach_error_observed_records"], 1)
        self.assertEqual(report["totals"]["pre_detach_error_records"], 0)


if __name__ == "__main__":
    unittest.main()
