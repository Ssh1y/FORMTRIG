import importlib.util
import json
import subprocess
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
            self.assertIn("--runtime-link-mode never", script_text)
            self.assertIn("magma/magma/formtrig/runtime", script_text)
            self.assertIn("CMakeFiles/(CMakeScratch|CMakeTmp)", script_text)
            self.assertIn(r"conftest\.(c|cc|cpp|cxx)", script_text)
            self.assertIn("freetype2/src/tools", script_text)
            self.assertIn("AFLGO_CONFIGURE_NATIVE", script_text)
            self.assertIn("AFLGO_CONFIGURE_CC", script_text)
            self.assertIn("FORMTRIG host-compat: synchronized PHP ICU", script_text)
            self.assertIn("expected_icu_operator_return", script_text)
            self.assertIn("pkcs7_decode.c", script_text)
            self.assertIn("PKCS7_dataDecode", script_text)
            self.assertIn("OPENSSL_NO_FUZZ_LIBFUZZER", script_text)
            self.assertIn('rstrip() + "\\n"', script_text)
            self.assertIn('text.rstrip() + "\\n\\n" + fragment', script_text)
            instrument_step = next(row for row in plan["steps"] if row["name"] == "instrument_target")
            self.assertTrue(instrument_step["env"]["FORMTRIG_SOURCE_DIR"].endswith("/formtrig"))
            self.assertFalse((out_dir / "out" / "afl" / "pdfimages").exists())
            self.assertIn("Magma FORMTRIG Native Build Plan", (out_dir / "build_plan.md").read_text(encoding="utf-8"))

    def test_php_host_compatibility_patch_is_recorded(self):
        runner = load_tool("build_magma_formtrig_native_assets")

        patches = runner.host_compatibility_patches_for_target("php")

        self.assertEqual([row["id"] for row in patches], ["php_icu_breakiterator_operator_return"])
        self.assertIn("codepointiterator_internal.h", patches[0]["files"][0])
        self.assertEqual(runner.host_compatibility_patches_for_target("libpng"), [])

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
                    "--skip-dependency-preflight",
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

    def test_cli_entry_does_not_require_or_link_afl_driver(self):
        runner = load_tool("build_magma_formtrig_native_assets")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            magma_root = self.make_fake_magma(root)
            driver = (
                magma_root
                / "fuzzers"
                / "formtrig_native"
                / "repo"
                / "utils"
                / "aflpp_driver"
                / "libAFLDriver.a"
            )
            driver.unlink()
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
                    "--instrument-entry",
                    "cli",
                ]
            )

            self.assertEqual(code, 0)
            plan = json.loads((out_dir / "build_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["inputs"]["instrument_entry"], "cli")
            self.assertFalse(
                next(row for row in plan["steps"] if row["name"] == "fuzzer_build")[
                    "selected"
                ]
            )
            instrument_step = next(row for row in plan["steps"] if row["name"] == "instrument_target")
            self.assertEqual(instrument_step["env"]["FORMTRIG_MAGMA_LINK_AFL_DRIVER"], "0")
            script_text = (out_dir / "runner_instrument_target.sh").read_text(encoding="utf-8")
            self.assertIn("FORMTRIG_MAGMA_LINK_AFL_DRIVER", script_text)
            self.assertIn('driver_lib=" $driver"', script_text)

    def test_failure_log_summary_extracts_missing_dependencies(self):
        runner = load_tool("build_magma_formtrig_native_assets")
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "instrument_target.log"
            log.write_text(
                "\n".join(
                    [
                        "/usr/bin/ld: cannot find -ljpeg: No such file or directory",
                        "/usr/bin/ld: cannot find -llzma: No such file or directory",
                        "/usr/bin/ld: cannot find -ltiff: No such file or directory",
                        "/usr/bin/ld: cannot find -llcms2: No such file or directory",
                        "/usr/bin/ld: cannot find /usr/local/lib/clang/11.0.0/lib/linux/libclang_rt.ubsan_standalone-x86_64.a",
                        "clang: error: linker command failed with exit code 1",
                    ]
                ),
                encoding="utf-8",
            )

            summary = runner.summarize_failure_log(log)

            self.assertEqual(summary["missing_link_libraries"], ["jpeg", "lcms2", "lzma", "tiff"])
            self.assertIn("libjpeg-dev", summary["apt_package_hints"])
            self.assertIn("liblcms2-dev", summary["apt_package_hints"])
            self.assertIn("liblzma-dev", summary["apt_package_hints"])
            self.assertIn("libtiff-dev", summary["apt_package_hints"])
            self.assertIn("libclang-rt-11-dev", summary["apt_package_hints"])
            self.assertIn("clang: error: linker command failed with exit code 1", summary["error_lines"])
            self.assertIn("clang: error: linker command failed with exit code 1", summary["tail_lines"])

    def test_dependency_preflight_reports_poppler_dev_packages(self):
        runner = load_tool("build_magma_formtrig_native_assets")

        summary = runner.dependency_preflight_for_target(
            "poppler",
            pkg_exists=lambda _name: False,
            glob_match=lambda _patterns: "",
        )

        self.assertEqual(summary["status"], "missing")
        self.assertIn("libcairo2-dev", summary["apt_package_hints"])
        self.assertIn("libopenjp2-7-dev", summary["apt_package_hints"])
        self.assertIn("libtiff-dev", summary["apt_package_hints"])
        self.assertIn("liblcms2-dev", summary["apt_package_hints"])
        self.assertEqual(
            [row["status"] for row in summary["checks"]],
            ["missing", "missing", "missing", "missing"],
        )

    def test_poppler_openjpeg_patch_preserves_or_repairs_shell_quote(self):
        runner = load_tool("build_magma_formtrig_native_assets")

        fixed = runner.patch_poppler_openjpeg_dir_text(
            '    EXTRA="$EXTRA -DOpenJPEG_DIR=/old/path"\n',
            "/usr/lib/x86_64-linux-gnu/openjpeg-2.1",
        )
        repaired = runner.patch_poppler_openjpeg_dir_text(
            '    EXTRA="$EXTRA -DOpenJPEG_DIR=/old/path\n',
            "/usr/lib/x86_64-linux-gnu/openjpeg-2.1",
        )

        expected = (
            '    EXTRA="$EXTRA '
            '-DOpenJPEG_DIR=/usr/lib/x86_64-linux-gnu/openjpeg-2.1"\n'
        )
        self.assertEqual(fixed, expected)
        self.assertEqual(repaired, expected)

    def test_poppler_build_patch_disables_unused_freetype_codecs(self):
        runner = load_tool("build_magma_formtrig_native_assets")

        patched = runner.patch_poppler_build_text(
            "\n".join(
                [
                    './configure --prefix="$WORK" --disable-shared PKG_CONFIG_PATH="$WORK/lib/pkgconfig"',
                    '    EXTRA="$EXTRA -DOpenJPEG_DIR=/old/path',
                    '$CXX $CXXFLAGS -std=c++11 -I"$WORK/poppler/cpp" -I"$TARGET/repo/cpp" \\',
                    '    "$TARGET/src/pdf_fuzzer.cc" -o "$OUT/pdf_fuzzer" \\',
                    '    "$WORK/poppler/cpp/libpoppler-cpp.a" "$WORK/poppler/libpoppler.a" \\',
                    '    "$WORK/lib/libfreetype.a" $LDFLAGS $LIBS -ljpeg -lz \\',
                    '    -lopenjp2 -lpng -ltiff -llcms2 -lm -lpthread -pthread',
                ]
            )
            + "\n",
            "/usr/lib/x86_64-linux-gnu/openjpeg-2.1",
        )
        repatched = runner.patch_poppler_build_text(
            patched,
            "/usr/lib/x86_64-linux-gnu/openjpeg-2.1",
        )

        self.assertIn("--with-bzip2=no --with-brotli=no", patched)
        self.assertIn('-DOpenJPEG_DIR=/usr/lib/x86_64-linux-gnu/openjpeg-2.1"', patched)
        self.assertIn('if [ "${PROGRAM:-}" = "pdf_fuzzer" ]; then', patched)
        self.assertEqual(repatched, patched)

    def test_dependency_preflight_reports_php_build_tools(self):
        runner = load_tool("build_magma_formtrig_native_assets")

        summary = runner.dependency_preflight_for_target(
            "php",
            pkg_exists=lambda name: name == "icu-uc",
            cmd_exists=lambda _name: False,
        )

        self.assertEqual(summary["status"], "missing")
        self.assertIn("bison", summary["apt_package_hints"])
        self.assertIn("re2c", summary["apt_package_hints"])
        self.assertNotIn("libicu-dev", summary["apt_package_hints"])
        self.assertEqual(
            [row["status"] for row in summary["checks"]],
            ["missing", "missing", "ok"],
        )

    def test_php_exif_thumbnail_runner_patch_adds_thumbnail_enabled_program(self):
        runner = load_tool("build_magma_formtrig_native_assets")

        source = (
            "int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size) {\n"
            "\tzval stream_zv;\n"
            "\tfuzzer_call_php_func_zval(\"exif_read_data\", 1, &stream_zv);\n"
            "\tzval_ptr_dtor(&stream_zv);\n"
            "}\n"
        )
        config = (
            "  if test -n \"$enable_exif\" && test \"$enable_exif\" != \"no\"; then\n"
            "    PHP_FUZZER_TARGET([exif], PHP_FUZZER_EXIF_OBJS)\n"
            "  fi\n"
        )
        build_sh = (
            'FUZZERS="php-fuzz-json php-fuzz-exif php-fuzz-mbstring '
            'php-fuzz-unserialize php-fuzz-parser"\n'
        )
        makefile = (
            "$(SAPI_FUZZER_PATH)/php-fuzz-exif: $(PHP_GLOBAL_OBJS) $(PHP_SAPI_OBJS) "
            "$(PHP_FUZZER_EXIF_OBJS)\n"
            "\t$(FUZZER_BUILD) $(PHP_FUZZER_EXIF_OBJS) -o $@\n"
        )

        patched_runner = runner.php_exif_thumbnail_runner_text(source)
        patched_config = runner.patch_php_fuzzer_config_for_exif_thumbnail_text(config)
        patched_build = runner.patch_php_build_for_exif_thumbnail_text(build_sh)
        patched_makefile = runner.patch_php_fuzzer_makefile_for_exif_thumbnail_text(makefile)

        self.assertIn('fuzzer_call_php_func_zval("exif_thumbnail", 3, args);', patched_runner)
        self.assertIn("ZVAL_NULL(&args[1]);", patched_runner)
        self.assertIn("ZVAL_NULL(&args[2]);", patched_runner)
        self.assertNotIn('"exif_read_data", 1', patched_runner)
        self.assertIn(
            "PHP_FUZZER_TARGET([exif_thumbnail], PHP_FUZZER_EXIF_THUMBNAIL_OBJS)",
            patched_config,
        )
        self.assertEqual(
            runner.patch_php_fuzzer_config_for_exif_thumbnail_text(patched_config),
            patched_config,
        )
        self.assertIn("php-fuzz-exif_thumbnail", patched_build)
        self.assertEqual(
            runner.patch_php_build_for_exif_thumbnail_text(patched_build),
            patched_build,
        )
        self.assertIn("php-fuzz-exif_thumbnail:", patched_makefile)
        self.assertIn("$(PHP_FUZZER_EXIF_THUMBNAIL_OBJS)", patched_makefile)
        self.assertEqual(
            runner.patch_php_fuzzer_makefile_for_exif_thumbnail_text(patched_makefile),
            patched_makefile,
        )

    def test_php_exif_thumbnail_build_plan_defaults_to_file_argument(self):
        runner = load_tool("build_magma_formtrig_native_assets")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            magma_root = self.make_fake_magma(root)
            php_target = magma_root / "targets" / "php"
            poppler_target = magma_root / "targets" / "poppler"
            php_target.parent.mkdir(parents=True, exist_ok=True)
            poppler_target.rename(php_target)
            (php_target / "configrc").write_text("PROGRAMS=(json exif unserialize parser)\n", encoding="utf-8")
            out_dir = root / "build"

            code = runner.main(
                [
                    "--target",
                    "php",
                    "--program",
                    "exif_thumbnail",
                    "--target-id",
                    "PHP003",
                    "--magma-root",
                    str(magma_root),
                    "--out-dir",
                    str(out_dir),
                    "--skip-dependency-preflight",
                ]
            )

            self.assertEqual(code, 0)
            plan = json.loads((out_dir / "build_plan.json").read_text(encoding="utf-8"))
            self.assertEqual(plan["expected_validation_asset"]["program_args"], "@@")
            self.assertTrue(
                plan["expected_validation_asset"]["target_cmd"].endswith("/exif_thumbnail @@")
            )
            script = (out_dir / "runner_instrument_target.sh").read_text(encoding="utf-8")
            self.assertIn("fuzzer-exif_thumbnail.c", script)
            self.assertIn("php-fuzz-exif_thumbnail", script)
            self.assertIn("Makefile.frag", script)
            self.assertIn('fuzzer_call_php_func_zval("exif_thumbnail", 3, args);', script)

    def test_git_repo_has_head_rejects_parent_worktree(self):
        runner = load_tool("build_magma_formtrig_native_assets")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init"], cwd=root, check=True, stdout=subprocess.DEVNULL)
            (root / "README").write_text("root\n", encoding="utf-8")
            subprocess.run(["git", "add", "README"], cwd=root, check=True, stdout=subprocess.DEVNULL)
            subprocess.run(
                ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", "commit", "-m", "init"],
                cwd=root,
                check=True,
                stdout=subprocess.DEVNULL,
            )
            nested = root / "targets" / "php" / "repo"
            nested.mkdir(parents=True)

            self.assertFalse(runner.git_repo_has_head(nested))

    def test_openssl_programs_default_to_stdin_args(self):
        runner = load_tool("build_magma_formtrig_native_assets")
        with tempfile.TemporaryDirectory() as tmp:
            configrc = Path(tmp) / "openssl" / "configrc"
            configrc.parent.mkdir()
            configrc.write_text("PROGRAMS=(asn1)\n", encoding="utf-8")

            self.assertEqual(runner.parse_program_args(configrc, "pkcs7_decode"), "-")


if __name__ == "__main__":
    unittest.main()
