import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = REPO_ROOT / "scripts" / "formtrig_hooks" / "hevc_annexb_structure_hook.py"
AUDIT_PATH = REPO_ROOT / "tools" / "gpac3403_hevc_structure_audit.py"


def load_hook():
    spec = importlib.util.spec_from_file_location("hevc_annexb_structure_hook", HOOK_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sample_hevc():
    def nalu(nal_type, payload):
        return b"\x00\x00\x00\x01" + bytes([(nal_type << 1) & 0x7E, 1]) + payload

    return (
        nalu(32, b"\x01\x02\x03\x80")
        + nalu(33, b"\x04\x05\x06\x80")
        + nalu(34, b"\x07\x08\x80")
        + nalu(19, b"\x09\x0a\x0b\x0c\x80")
    )


class HevcAnnexBStructureHookTest(unittest.TestCase):
    def test_mutates_annexb_hevc_without_poc_bytes(self):
        hook = load_hook()
        original = sample_hevc()

        mutated_outputs = {
            hook.mutate(original, start=0, span=len(original), off=8, op=op, sample=op + 1)
            for op in range(8)
        }

        self.assertGreaterEqual(len(mutated_outputs), 5)
        for output in mutated_outputs:
            self.assertIn(b"\x00\x00\x00\x01", output)
            self.assertLessEqual(len(output), hook.MAX_OUTPUT_LEN)
            self.assertNotEqual(output, original)

        self.assertTrue(any(has_nonzero_layer_id(hook, output) for output in mutated_outputs))

    def test_layer_stress_ops_emit_high_layers_and_extractors(self):
        hook = load_hook()
        original = sample_hevc()

        mutated_outputs = [
            hook.mutate(original, start=0, span=len(original), off=8, op=op, sample=op + 11)
            for op in range(8, 14)
        ]

        self.assertTrue(any(has_layer_at_least(hook, output, 4) for output in mutated_outputs))
        self.assertTrue(any(has_nalu_type(hook, output, 49) for output in mutated_outputs))
        self.assertTrue(any(len(output) > len(original) * 2 for output in mutated_outputs))
        for output in mutated_outputs:
            self.assertIn(b"\x00\x00\x00\x01", output)
            self.assertLessEqual(len(output), hook.MAX_OUTPUT_LEN)
            self.assertNotEqual(output, original)

    def test_bit_helpers_use_msb_first_fields(self):
        hook = load_hook()

        payload = hook.set_bits(b"\x00\x00", 4, 6, 0b101011)

        self.assertEqual(hook.get_bits(payload, 4, 6), 0b101011)

    def test_field_ops_emit_vps_sps_pps_field_trains(self):
        hook = load_hook()
        original = sample_hevc()

        mutated_outputs = [
            hook.mutate(original, start=0, span=len(original), off=8, op=op, sample=op + 17)
            for op in range(14, 20)
        ]

        self.assertTrue(any(has_nalu_type(hook, output, 32) for output in mutated_outputs))
        self.assertTrue(any(has_nalu_type(hook, output, 33) for output in mutated_outputs))
        self.assertTrue(any(has_nalu_type(hook, output, 34) for output in mutated_outputs))
        self.assertTrue(any(has_layer_at_least(hook, output, 7) for output in mutated_outputs))
        self.assertTrue(any(first_vps_max_layers_minus1(hook, output) is not None for output in mutated_outputs))
        for output in mutated_outputs:
            self.assertIn(b"\x00\x00\x00\x01", output)
            self.assertLessEqual(len(output), hook.MAX_OUTPUT_LEN)
            self.assertNotEqual(output, original)

    def test_dense_sequence_ops_emit_stateful_layered_hevc(self):
        hook = load_hook()
        original = sample_hevc()

        mutated_outputs = [
            hook.mutate(original, start=0, span=len(original), off=8, op=op, sample=op + 23)
            for op in range(20, 24)
        ]

        for output in mutated_outputs:
            types = {hook.nalu_type(output, nalu) for nalu in hook.parse_nalus(output)}
            layers = {hook.layer_id(output, nalu) for nalu in hook.parse_nalus(output)}

            self.assertGreaterEqual(len(hook.parse_nalus(output)), 50)
            self.assertTrue({1, 5, 21, 49}.issubset(types))
            self.assertTrue({16, 18, 32, 37, 50}.issubset(layers))
            self.assertIn(b"\x00\x00\x00\x01", output)
            self.assertLessEqual(len(output), hook.MAX_OUTPUT_LEN)
            self.assertNotEqual(output, original)

    def test_output_layer_set_ops_emit_bounded_vps_extension_candidates(self):
        hook = load_hook()
        audit = load_module(AUDIT_PATH, "gpac3403_hevc_structure_audit_for_hook_test")
        original = sample_hevc()

        mutated_outputs = [
            hook.mutate(original, start=0, span=len(original), off=8, op=op, sample=op + 29)
            for op in range(24, 28)
        ]

        for output in mutated_outputs:
            parsed_vps = parse_vps_items(hook, audit, output)

            self.assertTrue(parsed_vps)
            self.assertTrue(any(item["max_layers_minus1"] <= 3 for item in parsed_vps))
            self.assertTrue(any(item["max_layer_id"] <= 3 for item in parsed_vps))
            self.assertTrue(any(item["num_layer_sets_minus1"] >= 1 for item in parsed_vps))
            self.assertIn(b"\x00\x00\x00\x01", output)
            self.assertLessEqual(len(output), hook.MAX_OUTPUT_LEN)
            self.assertNotEqual(output, original)

    def test_output_layer_set_dense_ops_keep_extractor_and_many_nalus(self):
        hook = load_hook()
        audit = load_module(AUDIT_PATH, "gpac3403_hevc_structure_audit_for_dense_hook_test")
        original = sample_hevc()

        mutated_outputs = [
            hook.mutate(original, start=0, span=len(original), off=8, op=op, sample=op + 37)
            for op in range(28, 32)
        ]

        for output in mutated_outputs:
            parsed_vps = parse_vps_items(hook, audit, output)
            types = {hook.nalu_type(output, nalu) for nalu in hook.parse_nalus(output)}

            self.assertGreaterEqual(len(hook.parse_nalus(output)), 200)
            self.assertIn(49, types)
            self.assertTrue(any(item["max_layers_minus1"] <= 3 for item in parsed_vps))
            self.assertTrue(any(item["max_layer_id"] <= 3 for item in parsed_vps))
            self.assertTrue(any(item["num_layer_sets_minus1"] >= 1 for item in parsed_vps))
            self.assertLessEqual(len(output), hook.MAX_OUTPUT_LEN)

    def test_compact_output_layer_set_ops_keep_extractor_without_large_growth(self):
        hook = load_hook()
        audit = load_module(AUDIT_PATH, "gpac3403_hevc_structure_audit_for_compact_hook_test")
        original = sample_hevc()

        mutated_outputs = [
            hook.mutate(original, start=0, span=len(original), off=8, op=op, sample=op + 41)
            for op in range(32, 36)
        ]

        for output in mutated_outputs:
            parsed_vps = parse_vps_items(hook, audit, output)
            types = {hook.nalu_type(output, nalu) for nalu in hook.parse_nalus(output)}

            self.assertGreaterEqual(len(hook.parse_nalus(output)), 100)
            self.assertLess(len(output), 16000)
            self.assertIn(49, types)
            self.assertTrue(any(item["max_layers_minus1"] <= 3 for item in parsed_vps))
            self.assertTrue(any(item["max_layer_id"] <= 3 for item in parsed_vps))
            self.assertTrue(any(item["num_layer_sets_minus1"] >= 1 for item in parsed_vps))

    def test_access_unit_ops_emit_multiple_first_slice_vcl_units(self):
        hook = load_hook()
        audit = load_module(AUDIT_PATH, "gpac3403_hevc_structure_audit_for_access_unit_hook_test")
        original = sample_hevc()

        mutated_outputs = [
            hook.mutate(original, start=0, span=len(original), off=8, op=op, sample=op + 43)
            for op in range(36, 40)
        ]

        for output in mutated_outputs:
            nalus = hook.parse_nalus(output)
            types = [hook.nalu_type(output, nalu) for nalu in nalus]
            layers = {hook.layer_id(output, nalu) for nalu in nalus}
            vcl_nalus = [nalu for nalu in nalus if 0 <= hook.nalu_type(output, nalu) <= 31]

            self.assertGreaterEqual(len(nalus), 24)
            self.assertGreaterEqual(len(vcl_nalus), 8)
            self.assertIn(32, types)
            self.assertIn(33, types)
            self.assertGreaterEqual(types.count(34), 4)
            self.assertTrue(all(output[nalu.payload_start + 2] & 0x80 for nalu in vcl_nalus[:8]))
            self.assertLessEqual(len(output), hook.MAX_OUTPUT_LEN)
            self.assertNotEqual(output, original)

        layered_outputs = mutated_outputs[1:]
        self.assertTrue(any(has_nalu_type(hook, output, 49) for output in layered_outputs))
        self.assertTrue(any(has_layer_at_least(hook, output, 22) for output in layered_outputs))
        self.assertTrue(any(parse_vps_items(hook, audit, output) for output in layered_outputs))

    def test_high_max_layer_access_unit_ops_cover_vps_max_layer_path(self):
        hook = load_hook()
        audit = load_module(AUDIT_PATH, "gpac3403_hevc_structure_audit_for_high_vps_hook_test")
        original = sample_hevc()

        mutated_outputs = [
            hook.mutate(original, start=0, span=len(original), off=8, op=op, sample=op + 47)
            for op in range(40, 44)
        ]

        for output in mutated_outputs:
            nalus = hook.parse_nalus(output)
            types = {hook.nalu_type(output, nalu) for nalu in nalus}
            parsed_vps = parse_vps_items(hook, audit, output)
            vcl_nalus = [nalu for nalu in nalus if 0 <= hook.nalu_type(output, nalu) <= 31]

            self.assertGreaterEqual(len(nalus), 24)
            self.assertTrue(vcl_nalus)
            self.assertIn(49, types)
            self.assertTrue(parsed_vps)
            self.assertTrue(any(item.get("max_layer_id", 0) >= 4 for item in parsed_vps))
            self.assertLessEqual(len(output), hook.MAX_OUTPUT_LEN)
            self.assertNotEqual(output, original)

    def test_import_safe_extractor_ops_keep_type49_with_bounded_import_shape(self):
        hook = load_hook()
        audit = load_module(AUDIT_PATH, "gpac3403_hevc_structure_audit_for_import_safe_extractor_test")
        original = sample_hevc()

        mutated_outputs = [
            hook.mutate(original, start=0, span=len(original), off=8, op=op, sample=op + 53)
            for op in range(48, 52)
        ]

        for output in mutated_outputs:
            nalus = hook.parse_nalus(output)
            types = [hook.nalu_type(output, nalu) for nalu in nalus]
            vcl_nalus = [nalu for nalu in nalus if 0 <= hook.nalu_type(output, nalu) <= 31]
            parsed_vps = parse_vps_items(hook, audit, output)

            self.assertGreaterEqual(len(nalus), 18)
            self.assertIn(32, types)
            self.assertIn(33, types)
            self.assertIn(34, types)
            self.assertIn(49, types)
            self.assertTrue(vcl_nalus)
            self.assertTrue(parsed_vps)
            self.assertLess(len(output), 20000)
            self.assertLessEqual(len(output), hook.MAX_OUTPUT_LEN)
            self.assertNotEqual(output, original)

    def test_poc_shape_lifecycle_ops_emit_gp3403_sized_type_mix_without_poc_bytes(self):
        hook = load_hook()
        original = sample_hevc()

        mutated_outputs = [
            hook.mutate(original, start=0, span=len(original), off=8, op=op, sample=op + 59)
            for op in range(52, 56)
        ]

        for output in mutated_outputs:
            nalus = hook.parse_nalus(output)
            types = [hook.nalu_type(output, nalu) for nalu in nalus]
            layers = {hook.layer_id(output, nalu) for nalu in nalus}

            self.assertGreaterEqual(len(nalus), 330)
            self.assertGreaterEqual(types.count(0), 100)
            self.assertGreaterEqual(types.count(34), 100)
            self.assertGreaterEqual(types.count(49), 2)
            self.assertIn(50, layers)
            self.assertLessEqual(len(output), hook.MAX_OUTPUT_LEN)
            self.assertNotEqual(output, original)
            self.assertNotIn(b"\x7f\xff\xd9", output)

    def test_cli_prefers_mutated_annexb_when_available(self):
        hook = load_hook()
        original = b"not annex b"
        mutated = sample_hevc()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            orig = root / "orig"
            mut = root / "mut"
            out = root / "out"
            orig.write_bytes(original)
            mut.write_bytes(mutated)

            rc = hook.main(
                [
                    str(HOOK_PATH),
                    str(orig),
                    str(mut),
                    str(out),
                    str(len(mutated)),
                    "0",
                    str(len(mutated)),
                    "8",
                    "1",
                    "2",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                ]
            )
            out_bytes = out.read_bytes()

        self.assertEqual(rc, 0)
        self.assertIn(b"\x00\x00\x00\x01", out_bytes)
        self.assertNotEqual(out_bytes, original)


def has_nonzero_layer_id(hook, data):
    for nalu in hook.parse_nalus(data):
        if hook.layer_id(data, nalu):
            return True
    return False


def has_layer_at_least(hook, data, minimum):
    for nalu in hook.parse_nalus(data):
        if hook.layer_id(data, nalu) >= minimum:
            return True
    return False


def has_nalu_type(hook, data, nal_type):
    for nalu in hook.parse_nalus(data):
        if hook.nalu_type(data, nalu) == nal_type:
            return True
    return False


def first_vps_max_layers_minus1(hook, data):
    for nalu in hook.parse_nalus(data):
        if hook.nalu_type(data, nalu) != 32:
            continue
        body = data[nalu.payload_start + 2 : nalu.end]
        if len(body) >= 2:
            return hook.get_bits(body, 6, 6)
    return None


def parse_vps_items(hook, audit, data):
    parsed = []
    for nalu in hook.parse_nalus(data):
        if hook.nalu_type(data, nalu) != 32:
            continue
        try:
            parsed.append(audit.parse_vps(audit.rbsp_from_ebsp(hook.nalu_body(data, nalu))))
        except Exception:
            continue
    return parsed


if __name__ == "__main__":
    unittest.main()
