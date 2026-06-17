import importlib.util
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_hook():
    path = REPO_ROOT / "scripts" / "formtrig_hooks" / "pdf_device_n_colorspace_hook.py"
    spec = importlib.util.spec_from_file_location("pdf_device_n_colorspace_hook", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class PdfDeviceNHookTest(unittest.TestCase):
    def test_minimal_image_variant_is_structurally_valid_pdf(self):
        hook = load_hook()

        out = hook.minimal_image_pdf(0)

        self.assertTrue(out.startswith(b"%PDF-1.4\n"))
        self.assertIn(b"/Subtype /Image", out)
        self.assertIn(b"/ColorSpace /DeviceRGB", out)
        self.assertIn(b"/BitsPerComponent 8", out)
        self.assertIn(b"stream\n\xff\x00\x00\nendstream", out)
        self.assertIn(b"xref\n0 6\n", out)
        self.assertTrue(out.rstrip().endswith(b"%%EOF"))

    def test_mutate_prefers_complete_image_pdf_for_pdf_inputs(self):
        hook = load_hook()
        seed = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n"
        fallback = seed + b"% fallback\n"

        out = hook.mutate(seed, fallback, off=0, op=0, sample=0)

        self.assertNotEqual(out, seed)
        self.assertNotEqual(out, fallback)
        self.assertIn(b"/Subtype /Image", out)
        self.assertIn(b"/ColorSpace /DeviceRGB", out)


if __name__ == "__main__":
    unittest.main()
