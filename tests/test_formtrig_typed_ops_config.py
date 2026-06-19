from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class FormtrigTypedOpsConfigTest(unittest.TestCase):
    def test_aflpp_runtime_patch_makes_typed_ops_configurable(self):
        patch = (
            REPO_ROOT / "patches" / "aflplusplus" / "formtrig_native_runtime.patch"
        ).read_text(encoding="utf-8")

        self.assertIn("#define FORMTRIG_TYPED_BUILTIN_OPS 16u", patch)
        self.assertIn("#define FORMTRIG_TYPED_OPS_DEFAULT 16u", patch)
        self.assertIn("static u32 formtrig_typed_ops(void)", patch)
        self.assertIn('"FORMTRIG_TYPED_OPS"', patch)
        self.assertIn("u32 typed_ops = formtrig_typed_ops();", patch)
        self.assertIn("op = cursor % typed_ops", patch)
        self.assertNotIn("#define FORMTRIG_TYPED_OPS 16u", patch)
        self.assertNotIn("op = cursor % FORMTRIG_TYPED_OPS", patch)

    def test_aflpp_runtime_patch_records_formtrig_env_provenance(self):
        patch = (
            REPO_ROOT / "patches" / "aflplusplus" / "formtrig_native_runtime.patch"
        ).read_text(encoding="utf-8")

        for env_name in [
            "AFL_FORMTRIG",
            "FORMTRIG_AFLPP",
            "FORMTRIG_ALLOW_HEURISTIC_LIFT",
            "FORMTRIG_ALLOW_MANUAL_LIFT",
            "FORMTRIG_PROGRESS_LOG",
            "FORMTRIG_PROGRESS_LOG_LIMIT",
            "FORMTRIG_SAVED_PROGRESS_LOG_LIMIT",
            "FORMTRIG_SAVED_PROGRESS_LOG_SAMPLE_RATE",
            "FORMTRIG_SEMANTIC_DF_SLACK",
            "FORMTRIG_TYPED_FALLBACK_RANGES",
            "FORMTRIG_TYPED_MUTATION_HOOK",
            "FORMTRIG_TYPED_MUTATION_MAX",
            "FORMTRIG_TYPED_OPS",
            "FORMTRIG_TYPED_RANGE_SAMPLES",
            "FORMTRIG_TYPED_RANGE_WINDOW",
            "FORMTRIG_TYPED_RETAIN_DIR",
            "FORMTRIG_TYPED_RETAIN_MAX",
            "FORMTRIG_TYPED_RETAIN_MODE",
        ]:
            self.assertIn(f'"{env_name}"', patch)

        self.assertIn("FORMTRIG_TYPED_RETAIN_MODE_HOOK", patch)
        self.assertIn("formtrig_typed_retain_mode", patch)
        self.assertIn("formtrig_typed_retain_eligible", patch)
        self.assertIn("retain_queued_candidate", patch)

    def test_campaign_runner_exports_typed_ops_when_requested(self):
        runner = (
            REPO_ROOT / "scripts" / "run_formtrig_aflpp_campaign.sh"
        ).read_text(encoding="utf-8")

        self.assertIn("--typed-ops N", runner)
        self.assertIn('typed_ops="${2:-}"', runner)
        self.assertIn('env_args+=(FORMTRIG_TYPED_OPS="$typed_ops")', runner)
        self.assertIn("formtrig_typed_ops.json", runner)

    def test_manifest_forwards_typed_ops_to_campaign_runner(self):
        manifest_runner = (
            REPO_ROOT / "scripts" / "run_formtrig_native_manifest.sh"
        ).read_text(encoding="utf-8")

        self.assertIn("typed_ops: N", manifest_runner)
        self.assertIn('typed_ops="${cfg[typed_ops]:-}"', manifest_runner)
        self.assertIn('campaign_args+=(--typed-ops "$typed_ops")', manifest_runner)


if __name__ == "__main__":
    unittest.main()
