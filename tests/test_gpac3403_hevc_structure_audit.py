import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = REPO_ROOT / "tools" / "gpac3403_hevc_structure_audit.py"
HOOK_PATH = REPO_ROOT / "scripts" / "formtrig_hooks" / "hevc_annexb_structure_hook.py"


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def nalu(hook, nal_type, layer, payload):
    return b"\x00\x00\x00\x01" + hook.make_header(nal_type, layer) + payload


def sample_hevc(hook):
    vps_payload = hook.set_bits(b"\x00\x00\x80", 6, 6, 4)
    return (
        nalu(hook, 32, 22, vps_payload)
        + nalu(hook, 33, 36, b"\x04\x05\x80")
        + nalu(hook, 34, 4, b"\x06\x80")
        + nalu(hook, 16, 50, b"\x07\x08\x80")
    )


def mp4_box(box_type, payload):
    return (len(payload) + 8).to_bytes(4, "big") + box_type.encode("ascii") + payload


class Gpac3403HevcStructureAuditTest(unittest.TestCase):
    def test_nal_profile_counts_types_layers_and_vps_fields(self):
        audit = load_module(AUDIT_PATH, "gpac3403_hevc_structure_audit_profile")
        hook = load_module(HOOK_PATH, "hevc_annexb_structure_hook_for_audit_profile")
        profile = audit.nal_profile(sample_hevc(hook), hook)

        self.assertEqual(profile["total_nalus"], 4)
        self.assertEqual(profile["type_counts"]["32"], 1)
        self.assertEqual(profile["type_counts"]["16"], 1)
        self.assertEqual(profile["layer_counts"]["22"], 1)
        self.assertEqual(profile["max_layer"], 50)
        self.assertEqual(profile["vps_field_count"], 1)
        self.assertEqual(profile["vps_fields"][0]["vps_max_layers_minus1"], 4)

    def test_walk_boxes_recurses_into_mp4_containers(self):
        audit = load_module(AUDIT_PATH, "gpac3403_hevc_structure_audit_boxes")
        data = mp4_box("ftyp", b"isom") + mp4_box("moov", mp4_box("trak", b"abcd"))

        boxes = audit.walk_boxes(data)

        self.assertEqual([box["path"] for box in boxes], ["ftyp", "moov", "moov/trak"])

    def test_compare_annexb_reports_missing_reference_structure(self):
        audit = load_module(AUDIT_PATH, "gpac3403_hevc_structure_audit_compare")
        hook = load_module(HOOK_PATH, "hevc_annexb_structure_hook_for_audit_compare")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            reference = root / "reference.hevc"
            candidate = root / "candidate.hevc"
            reference.write_bytes(sample_hevc(hook))
            candidate.write_bytes(nalu(hook, 32, 22, b"\x00\x80") + nalu(hook, 34, 4, b"\x80"))

            ref_profile = audit.file_profile(reference, hook)
            cand_profile = audit.file_profile(candidate, hook)
            comparison = audit.compare_annexb(ref_profile, cand_profile)

        self.assertEqual(comparison["nalu_count_delta"], -2)
        self.assertIn(33, comparison["missing_reference_types"])
        self.assertIn(16, comparison["missing_reference_types"])
        self.assertIn(36, comparison["missing_reference_layers"])
        self.assertIn(50, comparison["missing_reference_layers"])

    def test_variant_records_report_best_and_largest_profiles(self):
        audit = load_module(AUDIT_PATH, "gpac3403_hevc_structure_audit_records")
        hook = load_module(HOOK_PATH, "hevc_annexb_structure_hook_for_audit_records")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            small = root / "small.hevc"
            large = root / "large.hevc"
            records = root / "records.jsonl"
            small.write_bytes(nalu(hook, 32, 0, b"\x00\x80"))
            large.write_bytes(sample_hevc(hook) + sample_hevc(hook))
            rows = [
                {"index": 0, "op": 1, "sample": 0, "d_f_spec_lifted": 2.0, "path": str(small), "endpoint_probes": [{"exit_code": 0}]},
                {"index": 1, "op": 2, "sample": 0, "d_f_spec_lifted": 1.0, "path": str(large), "endpoint_probes": [{"exit_code": 0}]},
            ]
            records.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")

            summary = audit.load_variant_records(records, hook, top=1)

        self.assertEqual(summary["record_count"], 2)
        self.assertEqual(summary["best_by_d_f"][0]["index"], 1)
        self.assertEqual(summary["largest_by_nalus"][0]["index"], 1)
        self.assertEqual(summary["largest_by_nalus"][0]["total_nalus"], 8)


if __name__ == "__main__":
    unittest.main()
