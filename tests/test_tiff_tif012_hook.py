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


def entry_value(data: bytes, tag: int) -> int:
    first_ifd = struct.unpack("<I", data[4:8])[0]
    count = struct.unpack("<H", data[first_ifd : first_ifd + 2])[0]
    for idx in range(count):
        pos = first_ifd + 2 + idx * 12
        entry_tag, _typ, _count, value = struct.unpack("<HHII", data[pos : pos + 12])
        if entry_tag == tag:
            return value
    raise AssertionError(f"missing tag {tag}")


class TiffTif012HookTest(unittest.TestCase):
    def test_rewrites_existing_extra_samples_then_spp_shape_in_place(self):
        hook = load_hook()
        original = make_tiff(
            [
                (256, 3, 1, 80),
                (259, 3, 1, 32773),
                (338, 3, 1, 1),
                (277, 3, 1, 3),
                (279, 4, 1, 64),
            ]
        )

        rewritten = hook.build_tif012_candidate(original, op=0, sample=1)

        self.assertIsNotNone(rewritten)
        self.assertEqual(len(rewritten), len(original))
        self.assertEqual(tags(rewritten), [256, 259, 338, 341, 279])
        self.assertEqual(entry_value(rewritten, 259) & 0xFFFF, 6)

    def test_fallback_omits_samples_per_pixel_and_inserts_state_tags(self):
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
        self.assertNotIn(277, rewritten_tags)
        self.assertIn(259, rewritten_tags)
        self.assertIn(338, rewritten_tags)
        self.assertIn(341, rewritten_tags)
        self.assertEqual(entry_value(rewritten, 259) & 0xFFFF, 6)
        self.assertLess(rewritten_tags.index(338), rewritten_tags.index(341))

    def test_fallback_replaces_existing_samples_per_pixel_when_extra_is_missing(self):
        hook = load_hook()
        original = make_tiff(
            [
                (256, 3, 1, 80),
                (257, 3, 1, 60),
                (259, 3, 1, 32773),
                (277, 3, 1, 3),
                (279, 4, 1, 64),
            ]
        )

        rewritten = hook.build_tif012_candidate(original, op=0, sample=1)

        self.assertIsNotNone(rewritten)
        rewritten_tags = tags(rewritten)
        self.assertNotIn(277, rewritten_tags)
        self.assertEqual(entry_value(rewritten, 259) & 0xFFFF, 6)
        self.assertLess(rewritten_tags.index(338), rewritten_tags.index(341))


if __name__ == "__main__":
    unittest.main()
