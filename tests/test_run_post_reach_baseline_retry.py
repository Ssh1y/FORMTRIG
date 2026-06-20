import json
import subprocess
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class RunPostReachBaselineRetryTest(unittest.TestCase):
    def test_startup_retry_uses_second_attempt_for_valid_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            seed = root / "seed"
            seed.mkdir()
            (seed / "id_0").write_bytes(b"seed")
            target = root / "target"
            target.write_text("#!/usr/bin/env bash\ncat \"$1\" >/dev/null\n", encoding="utf-8")
            target.chmod(0o755)
            counter = root / "counter"
            fake_afl = root / "fake_afl"
            fake_afl.write_text(
                "#!/usr/bin/env bash\n"
                "out=''\n"
                "while [ $# -gt 0 ]; do\n"
                "  if [ \"$1\" = '-o' ]; then out=\"$2\"; shift 2; else shift; fi\n"
                "done\n"
                "n=0\n"
                f"if [ -f {counter!s} ]; then n=$(cat {counter!s}); fi\n"
                "if [ \"$n\" = '0' ]; then\n"
                f"  echo 1 > {counter!s}\n"
                "  exit 1\n"
                "fi\n"
                "mkdir -p \"$out/default\"\n"
                "cat > \"$out/default/fuzzer_stats\" <<'EOF'\n"
                "run_time : 1\n"
                "execs_done : 10\n"
                "execs_per_sec : 10.0\n"
                "saved_crashes : 0\n"
                "saved_hangs : 0\n"
                "corpus_count : 1\n"
                "EOF\n"
                "exit 0\n",
                encoding="utf-8",
            )
            fake_afl.chmod(0o755)
            out_dir = root / "run"

            subprocess.run(
                [
                    "python3",
                    str(REPO_ROOT / "tools" / "run_post_reach_baseline.py"),
                    "--baseline",
                    "aflplusplus_vanilla",
                    "--target-id",
                    "TGT",
                    "--seed-corpus",
                    str(seed),
                    "--out-dir",
                    str(out_dir),
                    "--budget-sec",
                    "1",
                    "--target-cmd",
                    f"{target} @@",
                    "--afl-fuzz",
                    str(fake_afl),
                    "--startup-retries",
                    "1",
                    "--timeout-grace-sec",
                    "1",
                ],
                cwd=REPO_ROOT,
                check=True,
            )

            status = json.loads((out_dir / "status.json").read_text(encoding="utf-8"))
            record = json.loads((out_dir / "run_record.json").read_text(encoding="utf-8"))

        self.assertEqual(status["returncode"], 0)
        self.assertEqual(len(status["attempts"]), 2)
        self.assertTrue(status["attempts"][0]["retryable_startup_failure"])
        self.assertFalse(status["attempts"][1]["retryable_startup_failure"])
        self.assertIn("fuzzer_out_attempt2", " ".join(status["resolved_cmd"]))
        self.assertEqual(record["stats"]["execs_done"], 10)


if __name__ == "__main__":
    unittest.main()
