import csv
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class ManifestBatchJobsTest(unittest.TestCase):
    def test_parallel_batch_preserves_per_manifest_results_on_failure(self):
        script = REPO_ROOT / "scripts" / "run_formtrig_manifest_batch.sh"
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            manifest_a = tmp / "a.manifest"
            manifest_b = tmp / "b.manifest"
            manifest_a.write_text(
                "target_id: STUB_A\n"
                "category: binary-null\n"
                "seed_dir: /no/such/seeds\n"
                "out_dir: /tmp/out\n",
                encoding="utf-8",
            )
            manifest_b.write_text(
                "target_id: STUB_B\n"
                "category: binary-null\n"
                "seed_dir: /no/such/seeds\n"
                "out_dir: /tmp/out\n",
                encoding="utf-8",
            )
            out_root = tmp / "out"

            result = subprocess.run(
                [
                    str(script),
                    "--jobs",
                    "2",
                    "--continue-on-fail",
                    "--out-root",
                    str(out_root),
                    str(manifest_a),
                    str(manifest_b),
                ],
                cwd=REPO_ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(result.returncode, 1)
            with (out_root / "batch_summary.csv").open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual([row["target_id"] for row in rows], ["STUB_A", "STUB_B"])
            self.assertEqual([row["status"] for row in rows], ["runner_failed", "runner_failed"])
            self.assertTrue(rows[0]["out_dir"].endswith("/001_STUB_A/out"))
            self.assertTrue(rows[1]["out_dir"].endswith("/002_STUB_B/out"))

            json_rows = [
                json.loads(line)
                for line in (out_root / "batch_summary.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([row["target_id"] for row in json_rows], ["STUB_A", "STUB_B"])


if __name__ == "__main__":
    unittest.main()
