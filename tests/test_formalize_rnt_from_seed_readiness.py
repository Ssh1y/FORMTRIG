import argparse
import csv
import importlib.util
import json
import tempfile
from pathlib import Path
import unittest


def load_tool(name: str):
    path = Path(__file__).resolve().parents[1] / "tools" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class FormalizeRntFromSeedReadinessTest(unittest.TestCase):
    def test_formalizes_only_rnt_spec_lifted_seed_records(self):
        tool = load_tool("formalize_rnt_from_seed_readiness")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seedbank = root / "corpus"
            logs = root / "logs"
            out_dir = root / "rnt" / "SSL015"
            seedbank.mkdir()
            logs.mkdir()
            keep = seedbank / "keep.cms"
            skip_non_rnt = seedbank / "skip_non_rnt.cms"
            skip_unlifted = seedbank / "skip_unlifted.cms"
            keep.write_bytes(b"pkcs7-rnt")
            skip_non_rnt.write_bytes(b"plain")
            skip_unlifted.write_bytes(b"unlifted")
            runtime_log = logs / "keep.runtime.jsonl"
            runtime_log.write_text(
                json.dumps(
                    {
                        "reached": True,
                        "crash_predicate": False,
                        "D_T": 1,
                        "trace_signature": "0xabc",
                        "target_hit_count": 2,
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            readiness = root / "seed_readiness.json"
            readiness.write_text(
                json.dumps(
                    {
                        "seeds": [
                            {
                                "seed": str(keep),
                                "runtime_log": str(runtime_log),
                                "rnt": True,
                                "spec_lifted": True,
                                "triggered": False,
                            },
                            {
                                "seed": str(skip_non_rnt),
                                "runtime_log": str(logs / "non_rnt.jsonl"),
                                "rnt": False,
                                "spec_lifted": True,
                                "triggered": False,
                            },
                            {
                                "seed": str(skip_unlifted),
                                "runtime_log": str(logs / "unlifted.jsonl"),
                                "rnt": True,
                                "spec_lifted": False,
                                "triggered": False,
                            },
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            status_json = root / "rnt_corpus_status.json"
            status_json.write_text(
                json.dumps(
                    {
                        "generated_at_utc": "2026-06-18T00:00:00Z",
                        "records": [
                            {
                                "target_id": "SSL015",
                                "suite": "magma",
                                "project": "openssl",
                                "program": "asn1",
                                "status": "excluded",
                            }
                        ],
                        "rnt_root": "artifacts/rnt_corpus",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            status_csv = root / "rnt_corpus_status.csv"
            status_md = root / "rnt_corpus_status.md"

            result = tool.formalize(
                argparse.Namespace(
                    seed_readiness=str(readiness),
                    target_id="SSL015",
                    project="openssl",
                    program="pkcs7_decode",
                    tc_category="binary-state-null",
                    source_seedbank=str(seedbank),
                    source_manifest=str(readiness),
                    producer="unit_test_replay",
                    out_dir=str(out_dir),
                    suite="magma",
                    max_seeds=32,
                    max_input_size=1000,
                    allow_unlifted=False,
                    update_status_json=str(status_json),
                    update_status_csv=str(status_csv),
                    update_status_md=str(status_md),
                )
            )

            self.assertEqual(result["selected"], 1)
            seed_files = list((out_dir / "seeds").iterdir())
            self.assertEqual(len(seed_files), 1)
            self.assertEqual(seed_files[0].read_bytes(), b"pkcs7-rnt")

            with (out_dir / "metadata.csv").open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["program"], "pkcs7_decode")
            self.assertEqual(rows[0]["reached_R"], "1")
            self.assertEqual(rows[0]["triggered_T"], "0")
            self.assertEqual(rows[0]["coverage_hash"], "trace:0xabc")
            self.assertEqual(rows[0]["tc_root_state"], "R=2;T=0")

            status = json.loads(status_json.read_text(encoding="utf-8"))
            self.assertEqual(status["records"][0]["target_id"], "SSL015")
            self.assertEqual(status["records"][0]["program"], "pkcs7_decode")
            self.assertEqual(status["records"][0]["status"], "formal_ready")
            with status_csv.open(encoding="utf-8", newline="") as handle:
                status_rows = list(csv.DictReader(handle))
            self.assertEqual(status_rows[0]["target_id"], "SSL015")
            self.assertEqual(status_rows[0]["status"], "formal_ready")
            self.assertIn("formal_ready", status_md.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
