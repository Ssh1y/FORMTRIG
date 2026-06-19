import importlib.util
import json
import tempfile
from pathlib import Path
import unittest


def load_tool():
    path = Path(__file__).resolve().parents[1] / "tools" / "summarize_magma_binary_tc_cohort.py"
    spec = importlib.util.spec_from_file_location("summarize_magma_binary_tc_cohort", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class MagmaBinaryTCCohortTest(unittest.TestCase):
    def test_builds_binary_cohort_with_rnt_status_and_strict_subset(self):
        tool = load_tool()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inventory = root / "inventory.json"
            rnt_status = root / "rnt.json"
            inventory.write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "target_id": "PNG007",
                                "project": "libpng",
                                "program": "libpng_read_fuzzer",
                                "primary_tc_category": "binary-state-null",
                                "secondary_tc_category": "",
                                "ambiguous": "false",
                                "classification_confidence": "known_manifest",
                                "canary_expression": "png_ptr->palette == NULL",
                            },
                            {
                                "target_id": "PDF003",
                                "project": "poppler",
                                "program": "pdfimages",
                                "primary_tc_category": "binary-state-null",
                                "secondary_tc_category": "compound-sequence-lifecycle",
                                "ambiguous": "true",
                                "classification_confidence": "heuristic",
                                "canary_expression": "colorMap->getColorSpace2() == nullptr",
                            },
                            {
                                "target_id": "SSL008",
                                "project": "openssl",
                                "program": "server",
                                "primary_tc_category": "binary-state-null",
                                "secondary_tc_category": "equality/magic",
                                "ambiguous": "true",
                                "classification_confidence": "heuristic",
                                "canary_expression": "ckey == NULL",
                            },
                            {
                                "target_id": "PNG001",
                                "project": "libpng",
                                "program": "libpng_read_fuzzer",
                                "primary_tc_category": "numeric-margin",
                                "canary_expression": "size == limit",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            rnt_status.write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "suite": "magma",
                                "target_id": "PNG007",
                                "status": "formal_ready",
                                "seed_files": "2",
                                "reached_rows": "2",
                                "triggered_rows": "0",
                            },
                            {
                                "suite": "magma",
                                "target_id": "PDF003",
                                "status": "formal_ready",
                                "seed_files": "1",
                                "reached_rows": "1",
                                "triggered_rows": "0",
                            },
                            {
                                "suite": "magma",
                                "target_id": "SSL008",
                                "status": "excluded",
                                "blocking_reason": "runner does not construct client key exchange",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            payload = tool.build_cohort(inventory, rnt_status)

        self.assertEqual(payload["summary"]["inventory_binary_total"], 3)
        self.assertEqual(payload["summary"]["main_experiment_eligible"], 2)
        self.assertEqual(payload["summary"]["excluded_or_blocked"], 1)
        self.assertEqual(payload["summary"]["strict_clean_binary"], 1)
        by_id = {record["target_id"]: record for record in payload["records"]}
        self.assertTrue(by_id["PNG007"]["strict_clean_binary"])
        self.assertEqual(by_id["PNG007"]["cohort_role"], "strict_clean_binary_candidate")
        self.assertEqual(by_id["PDF003"]["cohort_role"], "formal_ready_binary_candidate")
        self.assertEqual(by_id["SSL008"]["cohort_role"], "harness_repair_or_runner_gap")
        self.assertFalse(by_id["SSL008"]["main_experiment_eligible"])

    def test_writes_markdown_tables(self):
        tool = load_tool()
        payload = {
            "generated_at_utc": "2026-06-19T00:00:00Z",
            "summary": {
                "inventory_binary_total": 1,
                "main_experiment_eligible": 1,
                "excluded_or_blocked": 0,
                "strict_clean_binary": 1,
                "ambiguous_or_secondary": 0,
            },
            "methodology": {
                "main_claim_rule": "Use eligible targets.",
                "excluded_rule": "Do not count excluded targets.",
                "strict_clean_binary_rule": "Keep strict subset separate.",
            },
            "records": [
                {
                    "target_id": "PDF010",
                    "project": "poppler",
                    "program": "pdf_fuzzer",
                    "classification_confidence": "known_manifest",
                    "secondary_tc_category": "",
                    "canary_expression": "t3GlyphStack == nullptr",
                    "main_experiment_eligible": True,
                    "rnt_status": "formal_ready",
                    "strict_clean_binary": True,
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "cohort.md"
            tool.write_markdown(out, payload)
            text = out.read_text(encoding="utf-8")

        self.assertIn("# Magma Binary-State TC Cohort", text)
        self.assertIn("| PDF010 | poppler | pdf_fuzzer | known_manifest |  | `t3GlyphStack == nullptr` |", text)
        self.assertIn("## Strict Clean Binary Subset", text)


if __name__ == "__main__":
    unittest.main()
