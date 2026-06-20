import importlib.util
import os
import stat
import sys
import tempfile
from pathlib import Path
from unittest import mock
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
HOOK_PATH = REPO_ROOT / "scripts" / "formtrig_hooks" / "gpac_scal_ref_mp4_hook.py"


def load_hook(name="gpac_scal_ref_mp4_hook"):
    spec = importlib.util.spec_from_file_location(name, HOOK_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_fake_hevc_hook(path: Path) -> None:
    path.write_text(
        "def mutate(data, start, span, off, op, sample):\n"
        "    return data + b'|HEVC_OP_%d_SAMPLE_%d_OFF_%d|' % (op, sample, off)\n",
        encoding="utf-8",
    )


def write_fake_mp4box(path: Path, fail: bool = False) -> None:
    if fail:
        path.write_text("#!/usr/bin/env python3\nraise SystemExit(1)\n", encoding="utf-8")
    else:
        path.write_text(
            "#!/usr/bin/env python3\n"
            "import pathlib, sys\n"
            "args=sys.argv[1:]\n"
            "if '-add' in args:\n"
            "    src=pathlib.Path(args[args.index('-add')+1])\n"
            "    dst=pathlib.Path(args[-1])\n"
            "    old=dst.read_bytes() if dst.exists() else b''\n"
            "    dst.write_bytes(old + b'|ADD|' + src.read_bytes())\n"
            "    raise SystemExit(0)\n"
            "if '-ref' in args:\n"
            "    dst=pathlib.Path(args[-1])\n"
            "    old=dst.read_bytes() if dst.exists() else b''\n"
            "    dst.write_bytes(old + b'|REF|' + args[args.index('-ref')+1].encode())\n"
            "    raise SystemExit(0)\n"
            "raise SystemExit(2)\n",
            encoding="utf-8",
        )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


class GpacScalRefMp4HookTest(unittest.TestCase):
    def test_builds_scal_ref_mp4_from_hevc_typed_payload(self):
        hook = load_hook("gpac_scal_ref_mp4_hook_build")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mp4box = root / "MP4Box"
            hevc_hook = root / "hevc_hook.py"
            write_fake_mp4box(mp4box)
            write_fake_hevc_hook(hevc_hook)
            env = {
                "FORMTRIG_GPAC3403_MP4BOX": str(mp4box),
                "FORMTRIG_GPAC3403_HEVC_HOOK": str(hevc_hook),
                "FORMTRIG_GPAC3403_HEVC_SAMPLE_BIAS": "2",
            }
            with mock.patch.dict(os.environ, env, clear=False):
                built = hook.build_scal_ref_mp4(
                    source_hevc=b"BASE_HEVC",
                    start=0,
                    span=9,
                    off=1,
                    op=52,
                    sample=0,
                    work_dir=root / "work",
                )

        self.assertIsNotNone(built)
        assert built is not None
        self.assertIn(b"BASE_HEVC", built)
        self.assertIn(b"HEVC_OP_52_SAMPLE_2_OFF_6", built)
        self.assertIn(b"|REF|2:scal:1", built)

    def test_cli_falls_back_to_mutated_input_when_mp4box_fails(self):
        hook = load_hook("gpac_scal_ref_mp4_hook_cli")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            mp4box = root / "MP4Box"
            hevc_hook = root / "hevc_hook.py"
            base = root / "base.hevc"
            orig = root / "orig.mp4"
            mutated = root / "mutated.mp4"
            out = root / "out.mp4"
            write_fake_mp4box(mp4box, fail=True)
            write_fake_hevc_hook(hevc_hook)
            base.write_bytes(b"BASE")
            orig.write_bytes(b"ORIG")
            mutated.write_bytes(b"MUTATED")
            env = {
                "FORMTRIG_GPAC3403_MP4BOX": str(mp4box),
                "FORMTRIG_GPAC3403_HEVC_HOOK": str(hevc_hook),
                "FORMTRIG_GPAC3403_BASE_HEVC": str(base),
            }
            with mock.patch.dict(os.environ, env, clear=False):
                rc = hook.main(
                    [
                        str(HOOK_PATH),
                        str(orig),
                        str(mutated),
                        str(out),
                        "0",
                        "0",
                        "9",
                        "1",
                        "52",
                        "0",
                        "0",
                        "0",
                        "0",
                        "0",
                        "0",
                    ]
                )

            self.assertEqual(rc, 0)
            self.assertTrue(out.exists())
            self.assertEqual(out.read_bytes(), b"MUTATED")


if __name__ == "__main__":
    unittest.main()
