from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class MagmaBaselineRunnerTest(unittest.TestCase):
    def test_runner_patches_formtrig_canary_baseline_builds(self):
        script = (REPO_ROOT / "scripts" / "run_magma_baselines.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("sync_formtrig_canary_runtime", script)
        self.assertIn("formtrig/formtrig_runtime.h", script)
        self.assertIn("FORMTRIG_CANARY_INCLUDE", script)
        self.assertIn("FORMTRIG_RUNTIME_OBJECTS", script)
        self.assertIn("formtrig_runtime.o", script)

    def test_runner_protects_dirty_target_repositories(self):
        script = (REPO_ROOT / "scripts" / "run_magma_baselines.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("prepare_clean_target_context", script)
        self.assertIn("restore_target_context", script)
        self.assertIn("git -C \"$target_repo_path\" status", script)
        self.assertIn("mktemp -d", script)
        self.assertIn("rm -rf \"$target_repo_path\"", script)
        self.assertIn("trap restore_target_context EXIT", script)

    def test_runner_patches_libtiff_autogen_without_network_dependency(self):
        script = (REPO_ROOT / "scripts" / "run_magma_baselines.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("FORMTRIG_LOCAL_CONFIG_AUX", script)
        self.assertIn("config.guess", script)
        self.assertIn("config.sub", script)
        self.assertIn("FORMTRIG_WGET", script)
        self.assertIn("FORMTRIG_CONFIG_LOG_ON_FAILURE", script)

    def test_runner_exports_formtrig_include_path_to_target_configure(self):
        script = (REPO_ROOT / "scripts" / "run_magma_baselines.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("FORMTRIG_CANARY_TARGET_CFLAGS", script)
        self.assertIn("patch_target_canary_include_flags", script)
        self.assertIn('export CFLAGS="${CFLAGS:-} -I$MAGMA/formtrig/include"', script)
        self.assertIn('export CXXFLAGS="${CXXFLAGS:-} -I$MAGMA/formtrig/include"', script)
        self.assertIn("changed = False", script)
        self.assertIn("if changed:", script)
        self.assertIn("patch_target_build_helpers\npatch_target_canary_include_flags", script)

    def test_runner_handles_cmake_targets_without_repo_cd(self):
        script = (REPO_ROOT / "scripts" / "run_magma_baselines.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("cmake_needle = 'cmake \"$TARGET/repo\"'", script)
        self.assertIn("text.replace(cmake_needle, extra + cmake_needle, 1)", script)
        self.assertIn("raise SystemExit(0)", script)
        self.assertIn("FORMTRIG_POPPLER_DEFAULT_CONFIGURE_NATIVE", script)
        self.assertIn('pushd "$TARGET/freetype2"', script)

    def test_runner_uses_native_configure_compiler_for_autoconf_targets(self):
        script = (REPO_ROOT / "scripts" / "run_magma_baselines.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("FORMTRIG_BASELINE_CONFIGURE_CC", script)
        self.assertIn("AFLGO_CONFIGURE_NATIVE=1", script)
        self.assertIn("AFLGO_CONFIGURE_CC=", script)
        self.assertIn('env "${build_env[@]}" ./tools/captain/build.sh', script)

    def test_runner_passes_extra_afl_args_to_magma_fuzzargs(self):
        script = (REPO_ROOT / "scripts" / "run_magma_baselines.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("declare -a extra_fuzz_args=()", script)
        self.assertIn("--afl-arg", script)
        self.assertIn('FUZZARGS="${extra_fuzz_args[*]}"', script)
        self.assertIn("fuzz_args=%s", script)

    def test_runner_patches_php_icu_bool_host_compatibility(self):
        script = (REPO_ROOT / "scripts" / "run_magma_baselines.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("patch_php_host_compatibility", script)
        self.assertIn("FORMTRIG_PHP_ICU_BOOL_HOST_COMPAT", script)
        self.assertIn("FORMTRIG_PHP_ICU_EXPECTED_RETURN", script)
        self.assertIn("expected_icu_operator_return", script)
        self.assertIn("virtual UBool operator==", script)
        self.assertIn("virtual bool operator==", script)
        self.assertIn("synchronized PHP ICU", script)
        self.assertIn("FORMTRIG_PHP_DEDUP_FUZZING_ENGINE", script)
        self.assertIn('PHP_TARGET_FUZZING_ENGINE="${PHP_LIB_FUZZING_ENGINE:--Wall}"', script)
        self.assertIn("legacy_future", script)
        self.assertNotIn("from __future__ import annotations\n\nimport sys\nfrom pathlib import Path\n\n\nrepo =", script)


if __name__ == "__main__":
    unittest.main()
