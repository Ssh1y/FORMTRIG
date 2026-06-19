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


class BitWriter:
    def __init__(self):
        self.bits = []

    def add_bits(self, value, count):
        for shift in range(count - 1, -1, -1):
            self.bits.append((value >> shift) & 1)

    def add_bool(self, value):
        self.add_bits(1 if value else 0, 1)

    def add_ue(self, value):
        code_num = value + 1
        body = f"{code_num:b}"
        self.bits.extend([0] * (len(body) - 1))
        self.bits.extend(1 if bit == "1" else 0 for bit in body)

    def to_bytes(self):
        bits = list(self.bits)
        bits.append(1)
        while len(bits) % 8:
            bits.append(0)
        out = bytearray()
        for index in range(0, len(bits), 8):
            value = 0
            for bit in bits[index : index + 8]:
                value = (value << 1) | bit
            out.append(value)
        return bytes(out)


def add_profile_tier_level(writer):
    writer.add_bits(0, 96)


def vps_payload(vps_id=0, max_layer_id=50):
    writer = BitWriter()
    writer.add_bits(vps_id, 4)
    writer.add_bool(True)
    writer.add_bool(True)
    writer.add_bits(3, 6)
    writer.add_bits(0, 3)
    writer.add_bool(True)
    writer.add_bits(0xFFFF, 16)
    add_profile_tier_level(writer)
    writer.add_bool(True)
    writer.add_ue(0)
    writer.add_ue(0)
    writer.add_ue(0)
    writer.add_bits(max_layer_id, 6)
    writer.add_ue(0)
    return writer.to_bytes()


def sps_payload(vps_id=0, sps_id=0):
    writer = BitWriter()
    writer.add_bits(vps_id, 4)
    writer.add_bits(0, 3)
    writer.add_bool(True)
    add_profile_tier_level(writer)
    writer.add_ue(sps_id)
    writer.add_ue(1)
    writer.add_ue(4)
    writer.add_ue(2)
    writer.add_bool(False)
    writer.add_ue(0)
    writer.add_ue(0)
    writer.add_ue(4)
    return writer.to_bytes()


def pps_payload(pps_id=0, sps_id=0):
    writer = BitWriter()
    writer.add_ue(pps_id)
    writer.add_ue(sps_id)
    writer.add_bool(False)
    return writer.to_bytes()


def slice_payload(pps_id=0, irap=True):
    writer = BitWriter()
    writer.add_bool(True)
    if irap:
        writer.add_bool(False)
    writer.add_ue(pps_id)
    return writer.to_bytes()


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

    def test_semantic_cross_references_report_consistent_parameter_sets(self):
        audit = load_module(AUDIT_PATH, "gpac3403_hevc_structure_audit_semantics_ok")
        hook = load_module(HOOK_PATH, "hevc_annexb_structure_hook_for_audit_semantics_ok")
        data = (
            nalu(hook, 32, 0, vps_payload(vps_id=0))
            + nalu(hook, 33, 0, sps_payload(vps_id=0, sps_id=0))
            + nalu(hook, 34, 0, pps_payload(pps_id=0, sps_id=0))
            + nalu(hook, 16, 0, slice_payload(pps_id=0, irap=True))
        )

        profile = audit.nal_profile(data, hook)
        refs = profile["semantics"]["cross_references"]

        self.assertEqual(refs["vps_ids"], [0])
        self.assertEqual(refs["sps_ids"], [0])
        self.assertEqual(refs["pps_ids"], [0])
        self.assertEqual(refs["sps_without_vps_count"], 0)
        self.assertEqual(refs["pps_without_sps_count"], 0)
        self.assertEqual(refs["slice_without_pps_count"], 0)

    def test_semantic_cross_references_report_unresolved_ids(self):
        audit = load_module(AUDIT_PATH, "gpac3403_hevc_structure_audit_semantics_bad")
        hook = load_module(HOOK_PATH, "hevc_annexb_structure_hook_for_audit_semantics_bad")
        data = nalu(hook, 34, 0, pps_payload(pps_id=7, sps_id=99)) + nalu(
            hook, 1, 0, slice_payload(pps_id=8, irap=False)
        )

        profile = audit.nal_profile(data, hook)
        refs = profile["semantics"]["cross_references"]

        self.assertEqual(refs["pps_ids"], [7])
        self.assertEqual(refs["pps_without_sps_count"], 1)
        self.assertEqual(refs["slice_without_pps_count"], 1)

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
