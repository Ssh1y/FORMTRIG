import importlib.util
import json
import os
import stat
import sys
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "probe_gpac3403_scal_ref_preseed.py"


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_fake_hook(path: Path) -> None:
    path.write_text(
        "def mutate(data, start, span, off, op, sample):\n"
        "    return data + bytes([op & 0xff, sample & 0xff])\n",
        encoding="utf-8",
    )


def write_fake_mp4box(path: Path) -> None:
    path.write_text(
        "#!/usr/bin/env python3\n"
        "import pathlib, sys\n"
        "args=sys.argv[1:]\n"
        "if '-add' in args:\n"
        "    dst=pathlib.Path(args[-1]); dst.write_bytes(dst.read_bytes() if dst.exists() else b'MP4')\n"
        "    sys.stderr.write('Track Importing HEVC\\n')\n"
        "    raise SystemExit(0)\n"
        "if '-ref' in args:\n"
        "    sys.stderr.write('Saving file: In-place rewrite\\n')\n"
        "    raise SystemExit(0)\n"
        "if '-cat' in args:\n"
        "    sys.stderr.write('ISOBMF: Extractor target track is not present in file - skipping.\\n')\n"
        "    sys.stderr.write('free(): double free detected in tcache 2\\n')\n"
        "    raise SystemExit(134)\n"
        "raise SystemExit(1)\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def write_fake_mp4box_clean_replay(path: Path) -> None:
    path.write_text(
        "#!/usr/bin/env python3\n"
        "import pathlib, sys\n"
        "args=sys.argv[1:]\n"
        "if '-add' in args:\n"
        "    dst=pathlib.Path(args[-1]); dst.write_bytes(dst.read_bytes() if dst.exists() else b'MP4')\n"
        "    sys.stderr.write('Track Importing HEVC\\n')\n"
        "    raise SystemExit(0)\n"
        "if '-ref' in args:\n"
        "    sys.stderr.write('Saving file: In-place rewrite\\n')\n"
        "    raise SystemExit(0)\n"
        "if '-cat' in args:\n"
        "    sys.stderr.write('Done\\n')\n"
        "    raise SystemExit(0)\n"
        "raise SystemExit(1)\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


class ProbeGpac3403ScalRefPreseedTest(unittest.TestCase):
    def test_signature_helpers_classify_native_double_free(self):
        tool = load_module(TOOL, "probe_gpac3403_scal_ref_helpers")

        self.assertTrue(tool.is_native_crash(134))
        self.assertTrue(tool.is_native_crash(-6))
        self.assertFalse(tool.is_native_crash(1))
        self.assertTrue(tool.DOUBLE_FREE_RE.search("free(): double free detected in tcache 2"))

    def test_fake_mp4box_report_marks_double_free_preseed(self):
        tool = load_module(TOOL, "probe_gpac3403_scal_ref_report")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed = root / "seed.hevc"
            hook = root / "hook.py"
            mp4box = root / "MP4Box"
            companion = root / "white.mp4"
            out = root / "out"
            seed.write_bytes(b"\x00\x00\x00\x01\x40\x01\x80")
            companion.write_bytes(b"mp4")
            write_fake_hook(hook)
            write_fake_mp4box(mp4box)
            args = type(
                "Args",
                (),
                {
                    "seed": seed,
                    "hook": hook,
                    "mp4box": mp4box,
                    "companion_mp4": companion,
                    "out": out,
                    "lift_spec": None,
                    "target_site_ids": "115396228",
                    "enhanced_mode": "mutated",
                    "start": 0,
                    "span": 7,
                    "off": 0,
                    "op": 52,
                    "sample": 2,
                    "base_track_id": 1,
                    "ref_track_id": 2,
                },
            )

            report = tool.build_report(args)

        self.assertEqual(report["status"], "scal_ref_preseed_triggers_double_free")
        self.assertEqual(report["preseed_class"], "terminal_positive_control")
        self.assertTrue(report["preseed"]["built"])
        self.assertEqual(report["preseed"]["enhanced_mode"], "mutated")
        self.assertEqual(report["preseed"]["exit_codes"]["add_scal_ref"], 0)
        self.assertEqual(report["replay"]["exit_code"], 134)
        self.assertTrue(report["replay"]["native_crash"])
        self.assertTrue(report["replay"]["double_free_signature"])
        self.assertEqual(report["replay"]["no_reference_track_messages"], 1)

    def test_copy_base_mode_marks_clean_nonterminal_scaffold_candidate(self):
        tool = load_module(TOOL, "probe_gpac3403_scal_ref_copy_base")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed = root / "seed.hevc"
            mp4box = root / "MP4Box"
            companion = root / "white.mp4"
            out = root / "out"
            seed.write_bytes(b"\x00\x00\x00\x01\x40\x01\x80")
            companion.write_bytes(b"mp4")
            write_fake_mp4box_clean_replay(mp4box)
            args = type(
                "Args",
                (),
                {
                    "seed": seed,
                    "hook": None,
                    "mp4box": mp4box,
                    "companion_mp4": companion,
                    "out": out,
                    "lift_spec": None,
                    "target_site_ids": "115396228",
                    "enhanced_mode": "copy-base",
                    "start": 0,
                    "span": 7,
                    "off": 0,
                    "op": 52,
                    "sample": 2,
                    "base_track_id": 1,
                    "ref_track_id": 2,
                },
            )

            report = tool.build_report(args)

        self.assertEqual(report["status"], "scal_ref_preseed_no_terminal_crash")
        self.assertEqual(report["preseed_class"], "reference_scaffold_candidate")
        self.assertTrue(report["preseed"]["built"])
        self.assertEqual(report["preseed"]["enhanced_mode"], "copy-base")
        self.assertEqual(report["preseed"]["base_size"], report["preseed"]["enhanced_size"])
        self.assertEqual(report["replay"]["exit_code"], 0)
        self.assertFalse(report["replay"]["native_crash"])
        self.assertFalse(report["replay"]["double_free_signature"])


if __name__ == "__main__":
    unittest.main()
