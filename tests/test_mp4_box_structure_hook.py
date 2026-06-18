import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = REPO_ROOT / "scripts" / "formtrig_hooks" / "mp4_box_structure_hook.py"


def load_hook():
    spec = importlib.util.spec_from_file_location("mp4_box_structure_hook", HOOK_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Mp4BoxStructureHookTest(unittest.TestCase):
    def test_mutates_parseable_mp4_without_poc_bytes(self):
        hook = load_hook()
        sample = (
            b"\x00\x00\x00\x18ftypisom\x00\x00\x00\x01isommp41"
            b"\x00\x00\x00\x08moov"
            b"\x00\x00\x00\x10mdatABCDEFGH"
        )

        mutated_outputs = {
            hook.mutate(sample, start=24, span=8, off=32, op=op, sample=op + 1)
            for op in range(8)
        }

        self.assertGreaterEqual(len(mutated_outputs), 4)
        for output in mutated_outputs:
            self.assertTrue(output)
            self.assertLessEqual(len(output), hook.MAX_OUTPUT_LEN)
            self.assertNotEqual(output, sample)

    def test_cli_falls_back_to_mutated_input_for_unparseable_data(self):
        hook = load_hook()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            orig = root / "orig"
            mutated = root / "mutated"
            out = root / "out"
            orig.write_bytes(b"not an mp4")
            mutated.write_bytes(b"still not mp4 but fuzzed")

            rc = hook.main(
                [
                    str(HOOK_PATH),
                    str(orig),
                    str(mutated),
                    str(out),
                    "0",
                    "0",
                    "8",
                    "0",
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
        self.assertEqual(out_bytes, b"still not mp4 but fuzzed")


if __name__ == "__main__":
    unittest.main()
