import importlib.util
import json
import sys
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "analyze_gpac3403_extractor_path.py"


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
                "outer_error,1,compound-sequence-lifecycle,guard,8,3035684152,0000000000001001,exact,0x00000000,B4,true,ok,5,32,higher,outcome,gf_isom_nalu_sample_rewrite,isomedia/avc_ext.c,809,9,br,any",
                "invalid_nal_size,1,compound-sequence-lifecycle,guard,8,4008811561,0000000000001002,exact,0x00000000,B4,true,ok,5,34,higher,outcome,gf_isom_nalu_sample_rewrite,isomedia/avc_ext.c,844,9,br,any",
                "loop_entry,1,compound-sequence-lifecycle,lifecycle_event,8,2366748155,0000000000001003,exact,0x00000000,B4,true,ok,7,35,higher,hit,process_extractor,isomedia/avc_ext.c,119,3,br,any",
                "constructor,1,compound-sequence-lifecycle,guard,8,2400597583,0000000000001004,exact,0x00000000,B4,true,ok,5,36,higher,outcome,process_extractor,isomedia/avc_ext.c,123,8,br,any",
                "reference_track,1,compound-sequence-lifecycle,guard,8,3793165467,0000000000001005,exact,0x00000000,B4,true,ok,5,37,higher,outcome,process_extractor,isomedia/avc_ext.c,151,8,br,any",
                "no_ref_ok,1,compound-sequence-lifecycle,opposite_producer,8,1427918546,0000000000001006,exact,0x00000000,B4,true,ok,6,38,higher,outcome,process_extractor,isomedia/avc_ext.c,154,8,br,any",
                "missing_ref_sample,1,compound-sequence-lifecycle,guard,8,4118449176,0000000000001007,exact,0x00000000,B4,true,ok,5,39,higher,outcome,process_extractor,isomedia/avc_ext.c,181,8,br,any",
                "negative_offset,1,compound-sequence-lifecycle,guard,8,4084452653,0000000000001008,exact,0x00000000,B4,true,ok,5,40,higher,outcome,process_extractor,isomedia/avc_ext.c,182,8,br,any",
                "referred_size_ok,1,compound-sequence-lifecycle,guard,8,2977846854,0000000000001009,exact,0x00000000,B4,true,ok,5,41,higher,outcome,process_extractor,isomedia/avc_ext.c,207,8,br,any",
                "size_too_large_ok,1,compound-sequence-lifecycle,opposite_producer,8,3416563163,000000000000100a,exact,0x00000000,B4,true,ok,6,42,higher,hit,process_extractor,isomedia/avc_ext.c,248,5,br,any",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def component(source_id: int, value: int) -> dict:
    return {"source_id": source_id, "value": value}


def write_runtime(path: Path, components: list[dict]) -> None:
    path.write_text(
        json.dumps(
            {
                "reached": True,
                "D_F_spec_lifted": 3,
                "trace_signature": "0xbeef",
                "components": components,
            }
        )
        + "\n",
        encoding="utf-8",
    )


class AnalyzeGpac3403ExtractorPathTest(unittest.TestCase):
    def build_report(self, components):
        tool = load_module(TOOL, "gpac3403_extractor_path")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            event_map = root / "map.csv"
            runtime = root / "runtime.jsonl"
            write_event_map(event_map)
            write_runtime(runtime, components)
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
            return tool.build_report(args)

    def test_reports_extractor_not_reached_without_loop_entry(self):
        report = self.build_report([component(0x1001, 0), component(0x1002, 0)])

        self.assertEqual(report["verdict"]["status"], "extractor_not_reached")
        self.assertEqual(report["totals"].get("records_with_extractor_components"), 1)
        self.assertEqual(report["totals"].get("extractor_loop_entry_observed_records", 0), 0)

    def test_reports_ok_return_without_reference_track(self):
        report = self.build_report([component(0x1003, 1), component(0x1006, 1)])

        self.assertEqual(report["verdict"]["status"], "extractor_returns_ok_without_reference_track")
        self.assertEqual(report["totals"]["extractor_loop_entry_satisfied_records"], 1)
        self.assertEqual(report["totals"]["no_reference_track_ok_return_satisfied_records"], 1)

    def test_reports_constructor_only_when_no_error_or_ok_barrier(self):
        report = self.build_report([component(0x1003, 1), component(0x1004, 1)])

        self.assertEqual(report["verdict"]["status"], "extractor_constructor_mode_only")
        self.assertEqual(report["totals"]["constructor_mode_satisfied_records"], 1)

    def test_error_path_takes_precedence_over_ok_barrier(self):
        report = self.build_report(
            [
                component(0x1001, 1),
                component(0x1003, 1),
                component(0x1006, 1),
                component(0x1008, 1),
            ]
        )

        self.assertEqual(report["verdict"]["status"], "extractor_error_path_satisfied")
        self.assertEqual(report["totals"]["outer_hevc_extractor_error_satisfied_records"], 1)
        self.assertEqual(report["totals"]["negative_sample_offset_error_satisfied_records"], 1)


if __name__ == "__main__":
    unittest.main()
