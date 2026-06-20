import json
import tempfile
from pathlib import Path
import unittest

from tools.summarize_post_reach_baselines import flatten_record, group_rows


class SummarizePostReachBaselinesTest(unittest.TestCase):
    def write_run(
        self,
        root: Path,
        name: str,
        *,
        returncode: int,
        success: bool,
        execs_done: int,
    ) -> Path:
        run_dir = root / name
        run_dir.mkdir(parents=True)
        record = {
            "target_id": "GPAC_3403",
            "baseline": "aflplusplus_cmplog",
            "budget": 60,
            "run_id": f"GPAC_3403:aflplusplus_cmplog:{name}",
            "success": success,
            "trigger_time_s": 1.0 if success else None,
            "trigger_time_kind": "afl_crash_filename_exact" if success else None,
            "stats": {
                "run_time": 60 if returncode in (0, 124) else 2,
                "execs_done": execs_done,
                "execs_per_sec": "20.0" if execs_done else None,
                "corpus_count": 1 if execs_done else 0,
                "saved_crashes": 1 if success else 0,
                "saved_hangs": 0,
                "magma_reached": 0,
                "magma_triggered": 0,
            },
        }
        (run_dir / "run_record.json").write_text(
            json.dumps(record) + "\n",
            encoding="utf-8",
        )
        (run_dir / "status.json").write_text(
            json.dumps({"status": "complete", "returncode": returncode}) + "\n",
            encoding="utf-8",
        )
        return run_dir / "run_record.json"

    def test_invalid_returncode_marks_run_invalid_and_removes_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = self.write_run(
                root,
                "rep1",
                returncode=1,
                success=True,
                execs_done=0,
            )

            row = flatten_record(path)

        self.assertFalse(row["valid_run"])
        self.assertEqual(row["returncode"], 1)
        self.assertFalse(row["success"])

    def test_group_counts_only_valid_repetitions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            valid = flatten_record(
                self.write_run(
                    root,
                    "rep1",
                    returncode=0,
                    success=False,
                    execs_done=1200,
                )
            )
            invalid = flatten_record(
                self.write_run(
                    root,
                    "rep2",
                    returncode=1,
                    success=False,
                    execs_done=0,
                )
            )

            groups = group_rows([valid, invalid])

        self.assertEqual(groups[0]["attempted_reps"], 2)
        self.assertEqual(groups[0]["reps"], 1)
        self.assertEqual(groups[0]["invalid_reps"], 1)
        self.assertEqual(groups[0]["success_rate"], 0.0)


if __name__ == "__main__":
    unittest.main()
