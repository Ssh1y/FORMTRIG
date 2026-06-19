import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = REPO_ROOT / "tools" / "gpac3403_endpoint_signature_audit.py"


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Gpac3403EndpointSignatureAuditTest(unittest.TestCase):
    def test_analyze_text_strips_ansi_and_extracts_values(self):
        audit = load_module(AUDIT_PATH, "gpac3403_endpoint_signature_audit_text")
        text = (
            "\x1b[31m[HEVC] Wrong number of output layer sets in VPS 132, max 4 supported\x1b[0m\n"
            "\x1b[31m[HEVC] Failed to parse VPS extensions\x1b[0m\n"
            "\x1b[31m[HEVC] 47 layers in VPS but only 4 supported in GPAC\x1b[0m\n"
            "\x1b[32mTrack Importing HEVC - Width 4 Height 2 FPS 25/1\x1b[0m\n"
        )

        signatures = audit.analyze_text(text)

        self.assertTrue(signatures["wrong_output_layer_sets"]["present"])
        self.assertEqual(signatures["wrong_output_layer_sets"]["values"], [("132", "4")])
        self.assertTrue(signatures["failed_vps_extensions"]["present"])
        self.assertEqual(signatures["layers_only_4"]["values"], [("47", "4")])
        self.assertTrue(signatures["track_importing_hevc"]["present"])

    def test_classify_log_recognizes_variant_and_positive_control(self):
        audit = load_module(AUDIT_PATH, "gpac3403_endpoint_signature_audit_classify")

        variant = audit.classify_log(Path("variant_000092.endpoint_1.stderr"))
        positive = audit.classify_log(Path("positive_control.endpoint_2.stderr"))

        self.assertEqual(variant["kind"], "variant")
        self.assertEqual(variant["variant_index"], 92)
        self.assertEqual(variant["rep"], 1)
        self.assertEqual(positive["kind"], "positive_control")
        self.assertEqual(positive["rep"], 2)

    def test_build_report_contrasts_positive_only_signatures(self):
        audit = load_module(AUDIT_PATH, "gpac3403_endpoint_signature_audit_report")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            logs = root / "logs"
            logs.mkdir()
            summary = root / "summary.json"
            summary.write_text(
                json.dumps(
                    {
                        "generated_variants": 1,
                        "endpoint_replayed_variants": 1,
                        "reached": 1,
                        "triggered": 0,
                    }
                ),
                encoding="utf-8",
            )
            (logs / "variant_000000.endpoint_1.stderr").write_text(
                "[HEVC] VPS max layer ID 9 but GPAC only supports 4\n"
                "[HEVC] Error parsing Video Param Set\n",
                encoding="utf-8",
            )
            (logs / "positive_control.endpoint_1.stderr").write_text(
                "[HEVC] Wrong number of output layer sets in VPS 132, max 4 supported\n"
                "[HEVC] Failed to parse VPS extensions\n"
                "SUMMARY: AddressSanitizer: heap-buffer-overflow\n",
                encoding="utf-8",
            )

            args = type(
                "Args",
                (),
                {
                    "logs_dir": logs,
                    "summary": summary,
                    "exclude_other": True,
                    "include_records": False,
                },
            )
            report = audit.build_report(args)

        self.assertEqual(report["summary"]["generated_variants"], 1)
        self.assertEqual(report["variant"]["signatures"]["vps_max_layer_id"]["files"], 1)
        self.assertEqual(report["positive_control"]["signatures"]["asan"]["files"], 1)
        self.assertIn(
            "wrong_output_layer_sets",
            report["contrast"]["positive_control_signatures_absent_from_variants"],
        )
        self.assertIn(
            "failed_vps_extensions",
            report["contrast"]["positive_control_signatures_absent_from_variants"],
        )


if __name__ == "__main__":
    unittest.main()
