import importlib.util
import struct
import sys
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_hook():
    path = REPO_ROOT / "scripts" / "formtrig_hooks" / "tiff_tif012_ifd_tag_hook.py"
    spec = importlib.util.spec_from_file_location("tiff_tif012_ifd_tag_hook", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def make_tiff(entries: list[tuple[int, int, int, int]]) -> bytes:
    endian = "<"
    first_ifd = 8
    payload = bytearray(b"II" + struct.pack("<H", 42) + struct.pack("<I", first_ifd))
    payload += struct.pack("<H", len(entries))
    for entry in entries:
        payload += struct.pack("<HHII", *entry)
    payload += struct.pack("<I", 0)
    return bytes(payload)


def tags(data: bytes) -> list[int]:
    first_ifd = struct.unpack("<I", data[4:8])[0]
    count = struct.unpack("<H", data[first_ifd : first_ifd + 2])[0]
    out = []
    for idx in range(count):
        pos = first_ifd + 2 + idx * 12
        out.append(struct.unpack("<H", data[pos : pos + 2])[0])
    return out


class TiffTif012HookTest(unittest.TestCase):
    def test_rewrites_existing_extra_samples_then_spp_shape_in_place(self):
        hook = load_hook()
        original = make_tiff(
            [
                (256, 3, 1, 80),
                (338, 3, 1, 1),
                (277, 3, 1, 3),
                (279, 4, 1, 64),
            ]
        )

        rewritten = hook.build_tif012_candidate(original, op=0, sample=1)

        self.assertIsNotNone(rewritten)
        self.assertEqual(len(rewritten), len(original))
        self.assertEqual(tags(rewritten), [256, 338, 341, 279])

    def test_fallback_keeps_state_tags_before_inserted_samples_per_pixel(self):
        hook = load_hook()
        original = make_tiff(
            [
                (256, 3, 1, 80),
                (257, 3, 1, 60),
                (279, 4, 1, 64),
            ]
        )

        rewritten = hook.build_tif012_candidate(original, op=0, sample=1)

        self.assertIsNotNone(rewritten)
        rewritten_tags = tags(rewritten)
        self.assertLess(rewritten_tags.index(341), rewritten_tags.index(277))
        self.assertLess(rewritten_tags.index(301), rewritten_tags.index(277))


if __name__ == "__main__":
    unittest.main()
