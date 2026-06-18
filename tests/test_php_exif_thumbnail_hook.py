import importlib.util
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_hook():
    path = REPO_ROOT / "scripts" / "formtrig_hooks" / "php_exif_thumbnail_length_hook.py"
    spec = importlib.util.spec_from_file_location("php_exif_thumbnail_length_hook", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def exif_jpeg_with_thumbnail_length(length: int = 523) -> bytes:
    tiff = bytearray()
    tiff.extend(b"MM\x00\x2a")
    tiff.extend((8).to_bytes(4, "big"))
    tiff.extend((1).to_bytes(2, "big"))
    tiff.extend((0x010f).to_bytes(2, "big"))
    tiff.extend((2).to_bytes(2, "big"))
    tiff.extend((2).to_bytes(4, "big"))
    tiff.extend(b"FT\x00\x00")
    tiff.extend((26).to_bytes(4, "big"))
    tiff.extend((2).to_bytes(2, "big"))
    tiff.extend((0x0201).to_bytes(2, "big"))
    tiff.extend((4).to_bytes(2, "big"))
    tiff.extend((1).to_bytes(4, "big"))
    tiff.extend((64).to_bytes(4, "big"))
    tiff.extend((0x0202).to_bytes(2, "big"))
    tiff.extend((4).to_bytes(2, "big"))
    tiff.extend((1).to_bytes(4, "big"))
    length_entry_value_offset = len(tiff)
    tiff.extend(length.to_bytes(4, "big"))
    tiff.extend((0).to_bytes(4, "big"))
    if len(tiff) < 64:
        tiff.extend(b"\x00" * (64 - len(tiff)))
    tiff.extend(b"\xff\xd8\xff\xdbTHUMB")
    app1_payload = b"Exif\x00\x00" + bytes(tiff)
    return b"\xff\xd8\xff\xe1" + (len(app1_payload) + 2).to_bytes(2, "big") + app1_payload + b"\xff\xd9"


class PhpExifThumbnailHookTest(unittest.TestCase):
    def test_mutate_sets_ifd1_thumbnail_length_below_four(self):
        hook = load_hook()
        data = exif_jpeg_with_thumbnail_length(523)

        out = hook.mutate(data, 0)

        self.assertIsNotNone(out)
        assert out is not None
        base = out.find(b"Exif\x00\x00") + 6
        ifd1 = int.from_bytes(out[base + 22 : base + 26], "big")
        length_entry = base + ifd1 + 2 + 12
        self.assertEqual(int.from_bytes(out[length_entry + 8 : length_entry + 12], "big"), 1)

    def test_mutate_returns_none_when_exif_thumbnail_tags_missing(self):
        hook = load_hook()

        self.assertIsNone(hook.mutate(b"\xff\xd8\xff\xd9", 0))


if __name__ == "__main__":
    unittest.main()
