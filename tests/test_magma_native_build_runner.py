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


def write_script(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)


class MagmaNativeBuildRunnerTest(unittest.TestCase):
    def make_fake_magma(self, root: Path) -> Path:
        magma_root = root / "magma"
        fuzzer = magma_root / "fuzzers" / "formtrig_native"
        target = magma_root / "targets" / "poppler"
        magma = magma_root / "magma"
        (fuzzer / "repo" / "utils" / "aflpp_driver").mkdir(parents=True)
        (target / "repo").mkdir(parents=True)
        (magma / "src").mkdir(parents=True)
        (fuzzer / "repo" / "afl-clang-fast").write_text("", encoding="utf-8")
        (fuzzer / "repo" / "afl-clang-fast++").write_text("", encoding="utf-8")
        (fuzzer / "repo" / "utils" / "aflpp_driver" / "libAFLDriver.a").write_text("", encoding="utf-8")
        (target / "repo" / "patched.c").write_text("MAGMA_LOG(\"PDF003\", 0);\n", encoding="utf-8")
        (target / "configrc").write_text(
            "PROGRAMS=(pdfimages)\npdfimages_ARGS=\"@@ /tmp/out\"\n",
            encoding="utf-8",
        )
        for script in [
            fuzzer / "fetch.sh",
            fuzzer / "build.sh",
            target / "preinstall.sh",
            target / "fetch.sh",
            magma / "apply_patches.sh",
        ]:
            write_script(script, "#!/bin/sh\nexit 0\n")
        write_script(
            fuzzer / "instrument.sh",
            """#!/bin/sh
set -eu
mkdir -p "$OUT/formtrig_native" "$OUT/afl" "$SHARED"
printf '%s\n' "$FUZZER" > "$SHARED/fuzzer.txt"
printf '%s\n' "$TARGET" > "$SHARED/target.txt"
printf '%s\n' "$MAGMA" > "$SHARED/magma.txt"
printf '%s\n' "$PROGRAM" > "$SHARED/program.txt"
printf '%s\n' "$CFLAGS" > "$SHARED/cflags.txt"
printf '1\tcmp\tf\t1\ticmp\tfile.c\t10\t2\n' > "$OUT/formtrig_native/formtrig_sites.tsv"
printf '#!/bin/sh\nexit 0\n' > "$OUT/afl/$PROGRAM"
chmod +x "$OUT/afl/$PROGRAM"
""",
        )
        return magma_root

    def test_dry_run_writes_expected_build_plan_and_validation_asset(self):
        runner = load_tool("build_magma_formtrig_native_assets")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            magma_root = self.make_fake_magma(root)
            out_dir = root / "build"
            code = runner.main(
                [
                    "--target",
                    "poppler",
                    "--program",
                    "pdfimages",
                    "--target-id",
                    "PDF003",
                    "--magma-root",
                    str(magma_root),
                    "--out-dir",
                    str(out_dir),
                ]
            )

            self.assertEqual(code, 0)
            plan = json.loads((out_dir / "build_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["status"], "planned")
            self.assertEqual(plan["mode"], "dry-run")
            self.assertEqual(plan["inputs"]["instrument_entry"], "runner")
            self.assertEqual(plan["expected_validation_asset"]["program_args"], "@@ /tmp/out")
            self.assertEqual(
                plan["expected_validation_asset"]["site_map"],
                str(out_dir / "out" / "formtrig_native" / "formtrig_sites.tsv"),
            )
            self.assertEqual(
                plan["expected_validation_asset"]["target_cwd"],
                str(out_dir / "out" / "afl"),
            )
            self.assertIn("instrument_target", [row["name"] for row in plan["steps"] if row["selected"]])
            script = out_dir / "runner_instrument_target.sh"
            self.assertTrue(script.exists())
            script_text = script.read_text(encoding="utf-8")
            self.assertIn("FORMTRIG_MAGMA_CXX_STDLIB", script_text)
            self.assertIn("FORMTRIG_SOURCE_DIR", script_text)
            self.assertIn("--afl-cc", script_text)
            self.assertIn("FORMTRIG_LOCAL_CONFIG_AUX", script_text)
            instrument_step = next(row for row in plan["steps"] if row["name"] == "instrument_target")
            self.assertTrue(instrument_step["env"]["FORMTRIG_SOURCE_DIR"].endswith("/formtrig"))
            self.assertFalse((out_dir / "out" / "afl" / "pdfimages").exists())
            self.assertIn("Magma FORMTRIG Native Build Plan", (out_dir / "build_plan.md").read_text(encoding="utf-8"))

    def test_execute_runs_instrument_with_magma_formtrig_environment(self):
        runner = load_tool("build_magma_formtrig_native_assets")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            magma_root = self.make_fake_magma(root)
            out_dir = root / "build"
            code = runner.main(
                [
                    "--target",
                    "poppler",
                    "--program",
                    "pdfimages",
                    "--target-id",
                    "PDF003",
                    "--magma-root",
                    str(magma_root),
                    "--out-dir",
                    str(out_dir),
                    "--skip-fuzzer-fetch",
                    "--skip-fuzzer-build",
                    "--skip-target-fetch",
                    "--skip-patches",
                    "--instrument-entry",
                    "fuzzer",
                    "--execute",
                ]
            )

            self.assertEqual(code, 0)
            plan = json.loads((out_dir / "build_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["status"], "executed")
            self.assertTrue((out_dir / "out" / "formtrig_native" / "formtrig_sites.tsv").exists())
            self.assertTrue((out_dir / "out" / "afl" / "pdfimages").exists())
            self.assertEqual(
                (out_dir / "shared" / "program.txt").read_text(encoding="utf-8").strip(),
                "pdfimages",
            )
            self.assertIn(
                "-DMAGMA_ENABLE_CANARIES",
                (out_dir / "shared" / "cflags.txt").read_text(encoding="utf-8"),
            )
            self.assertEqual(
                [row["status"] for row in plan["executed_steps"] if row["selected"]],
                ["ok"],
            )

    def test_failure_log_summary_extracts_missing_dependencies(self):
        runner = load_tool("build_magma_formtrig_native_assets")
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "instrument_target.log"
            log.write_text(
                "\n".join(
                    [
                        "/usr/bin/ld: cannot find -ljpeg: No such file or directory",
                        "/usr/bin/ld: cannot find -llzma: No such file or directory",
                        "/usr/bin/ld: cannot find /usr/local/lib/clang/11.0.0/lib/linux/libclang_rt.ubsan_standalone-x86_64.a",
                        "clang: error: linker command failed with exit code 1",
                    ]
                ),
                encoding="utf-8",
            )

            summary = runner.summarize_failure_log(log)

            self.assertEqual(summary["missing_link_libraries"], ["jpeg", "lzma"])
            self.assertIn("libjpeg-dev", summary["apt_package_hints"])
            self.assertIn("liblzma-dev", summary["apt_package_hints"])
            self.assertIn("libclang-rt-11-dev", summary["apt_package_hints"])
            self.assertIn("clang: error: linker command failed with exit code 1", summary["error_lines"])
            self.assertIn("clang: error: linker command failed with exit code 1", summary["tail_lines"])


if __name__ == "__main__":
    unittest.main()
