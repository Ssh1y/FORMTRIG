import json
import subprocess
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "summarize_typed_retained_candidates.py"


HEADER = (
    "path\tsource_queue_id\tstage_cur\top\tcomponent_index\trange_index\t"
    "sample_index\tstart\tspan\toffset\tlen\thook_used\td_t\t"
    "d_f_spec_lifted\ttrace_signature\tcomponent_kind\tatom_id\trole\t"
    "component_flags\tcomponent_value\thint_kind\thint_value\n"
)


class SummarizeTypedRetainedCandidatesTest(unittest.TestCase):
    def test_summarizes_and_exports_records_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            retain = root / "typed_retained"
            retain.mkdir()
            low = retain / "low.bin"
            high = retain / "high.bin"
            low.write_bytes(b"\x00\x00\x01\x40low")
            high.write_bytes(b"\x00\x00\x01\x40high")
            records_tsv = retain / "records.tsv"
            records_tsv.write_text(
                HEADER
                + f"{low}\t7\t11\t39\t0\t1\t2\t3\t4\t5\t8\t1\t1\t0.5\tabc\t7\t1\t4\t86\t0.5\t0\t0\n"
                + f"{high}\t7\t12\t40\t1\t2\t3\t4\t5\t6\t9\t0\t1\t2\tdef\t6\t1\t6\t86\t2\t0\t0\n",
                encoding="utf-8",
            )
            summary_json = root / "summary.json"
            records_jsonl = root / "records.jsonl"

            subprocess.run(
                [
                    "python3",
                    str(TOOL),
                    "--retain-dir",
                    str(retain),
                    "--out-json",
                    str(summary_json),
                    "--out-records-jsonl",
                    str(records_jsonl),
                    "--top",
                    "1",
                ],
                cwd=REPO_ROOT,
                check=True,
            )

            summary = json.loads(summary_json.read_text(encoding="utf-8"))
            exported = [
                json.loads(line)
                for line in records_jsonl.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(summary["retained_records"], 2)
        self.assertEqual(summary["existing_inputs"], 2)
        self.assertEqual(summary["hook_used_records"], 1)
        self.assertEqual(summary["roles"], {"desired_producer": 1, "use": 1})
        self.assertEqual(summary["d_f_spec_lifted"]["min"], 0.5)
        self.assertEqual(summary["best_by_d_f"][0]["path"], str(low))
        self.assertEqual(exported[0]["index"], 0)
        self.assertEqual(exported[0]["op"], 39)
        self.assertEqual(exported[0]["sample"], 2)
        self.assertEqual(exported[0]["d_f_spec_lifted"], 0.5)
        self.assertEqual(exported[0]["role_name"], "desired_producer")
        self.assertTrue(exported[0]["input_exists"])

    def test_copy_corpus_rewrites_exported_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            retain = root / "typed_retained"
            corpus = root / "corpus"
            retain.mkdir()
            seed = retain / "seed.bin"
            seed.write_bytes(b"candidate")
            (retain / "records.tsv").write_text(
                HEADER
                + f"{seed}\t3\t4\t5\t0\t0\t0\t0\t9\t1\t9\t0\t1\t1\tfeed\t6\t1\t6\t86\t1\t0\t0\n",
                encoding="utf-8",
            )
            records_jsonl = root / "records.jsonl"
            subprocess.run(
                [
                    "python3",
                    str(TOOL),
                    "--retain-dir",
                    str(retain),
                    "--out-records-jsonl",
                    str(records_jsonl),
                    "--copy-corpus",
                    str(corpus),
                ],
                cwd=REPO_ROOT,
                check=True,
                stdout=subprocess.DEVNULL,
            )
            exported = json.loads(records_jsonl.read_text(encoding="utf-8").splitlines()[0])

            self.assertTrue(Path(exported["path"]).is_file())
            self.assertEqual(Path(exported["path"]).parent, corpus)
            self.assertEqual(exported["original_path"], str(seed))
            self.assertEqual(Path(exported["path"]).read_bytes(), b"candidate")

    def test_allow_empty_reports_missing_records_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            summary_json = root / "summary.json"
            missing_dir = root / "missing_retained"
            subprocess.run(
                [
                    "python3",
                    str(TOOL),
                    "--retain-dir",
                    str(missing_dir),
                    "--allow-empty",
                    "--out-json",
                    str(summary_json),
                ],
                cwd=REPO_ROOT,
                check=True,
                stdout=subprocess.DEVNULL,
            )
            summary = json.loads(summary_json.read_text(encoding="utf-8"))

        self.assertEqual(summary["retained_records"], 0)
        self.assertEqual(summary["existing_inputs"], 0)
        self.assertEqual(summary["records_tsv"], [])
        self.assertEqual(summary["missing_records_tsv"], [str((missing_dir / "records.tsv").resolve())])


if __name__ == "__main__":
    unittest.main()
