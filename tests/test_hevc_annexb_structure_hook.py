import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = REPO_ROOT / "scripts" / "formtrig_hooks" / "hevc_annexb_structure_hook.py"


def load_hook():
    spec = importlib.util.spec_from_file_location("hevc_annexb_structure_hook", HOOK_PATH)
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


if __name__ == "__main__":
    unittest.main()
