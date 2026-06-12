#!/usr/bin/env python3
import csv
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MAGMA = ROOT / "experiments" / "magma_workspace" / "magma"
FUZZER = MAGMA / "fuzzers" / "formtrig_native"
RUN_MAGMA_CAMPAIGN = ROOT / "tools" / "run_magma_campaign.py"
EXECUTE_MANIFEST = ROOT / "tools" / "execute_magma_manifest.py"


def load_execute_manifest_module():
    spec = importlib.util.spec_from_file_location("execute_magma_manifest", EXECUTE_MANIFEST)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FormtrigMagmaNativeAdapterTests(unittest.TestCase):
    def test_adapter_shell_scripts_parse(self) -> None:
        scripts = sorted(FUZZER.glob("*.sh")) + [
            MAGMA / "tools" / "captain" / "build.sh",
            MAGMA / "tools" / "captain" / "start.sh",
        ]
        for script in scripts:
            with self.subTest(script=script.name):
                result = subprocess.run(
                    ["bash", "-n", str(script)],
                    text=True,
                    capture_output=True,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_adapter_uses_generic_native_lift_chain(self) -> None:
        instrument = (FUZZER / "instrument.sh").read_text()
        run = (FUZZER / "run.sh").read_text()
        build = (MAGMA / "tools" / "captain" / "build.sh").read_text()
        start = (MAGMA / "tools" / "captain" / "start.sh").read_text()

        self.assertIn("prepare_native_build.py", instrument)
        self.assertIn("formtrig_build_env.sh", instrument)
        self.assertIn("afl-clang-fast", instrument)
        self.assertIn("--skip-pass-regex", instrument)
        self.assertIn("magma/magma/src", instrument)
        self.assertIn("run_aflpp_lift.py", run)
        self.assertIn("check_runtime_progress_health.py", run)
        self.assertIn("--trigger-graph", run)
        self.assertIn("--site-map", run)
        self.assertIn("--binding-audit-json", run)
        self.assertIn("formtrig_runtime_health.json", run)
        self.assertIn("FORMTRIG_REQUIRE_BINDING_READY", run)
        self.assertIn("--require-binding-ready", run)
        self.assertIn("FORMTRIG_FAIL_ON_RUNTIME_HEALTH", run)
        self.assertIn("formtrig_sites.tsv", run)
        self.assertIn("cp \"$site_map\" \"$SHARED/formtrig_sites.tsv\"", run)
        self.assertIn("FORMTRIG_RUNTIME_MAP", run)
        self.assertIn("--runtime-map", run)
        self.assertIn("formtrig_runtime_map.used.json", run)
        self.assertIn("AFL_DRIVER_DONT_DEFER=1", run)
        self.assertIn("[ \"${ARGS:-}\" = \"@@\" ]", run)
        self.assertIn("[ \"${ARGS:-}\" = \"-\" ]", run)
        self.assertIn("target_args=\"\"", run)
        self.assertIn("formtrig_native", build)
        self.assertIn("FORMTRIG_TRIGGER_GRAPH", start)
        self.assertIn("FORMTRIG_RUNTIME_MAP", start)
        self.assertIn("FORMTRIG_REQUIRE_BINDING_READY", start)
        self.assertIn("FORMTRIG_FAIL_ON_RUNTIME_HEALTH", start)
        for target_specific in ("PNG001", "PNG007", "SQL013", "XML017", "libpng", "sqlite3"):
            self.assertNotIn(target_specific, instrument)
            self.assertNotIn(target_specific, run)

    def test_magma_build_bundles_formtrig_patched_aflpp(self) -> None:
        build = (MAGMA / "tools" / "captain" / "build.sh").read_text()
        fetch = (FUZZER / "fetch.sh").read_text()
        dockerfile = (MAGMA / "docker" / "Dockerfile").read_text()
        afl_header = (
            ROOT / "experiments" / "aflplusplus" / "AFLplusplus" / "include" / "afl-fuzz.h"
        ).read_text()
        afl_queue = (
            ROOT / "experiments" / "aflplusplus" / "AFLplusplus" / "src" / "afl-fuzz-queue.c"
        ).read_text()
        afl_stats = (
            ROOT / "experiments" / "aflplusplus" / "AFLplusplus" / "src" / "afl-fuzz-stats.c"
        ).read_text()
        afl_driver = (
            ROOT
            / "experiments"
            / "aflplusplus"
            / "AFLplusplus"
            / "utils"
            / "aflpp_driver"
            / "aflpp_driver.c"
        ).read_text()
        afl_makefile = (
            ROOT / "experiments" / "aflplusplus" / "AFLplusplus" / "GNUmakefile"
        ).read_text()

        self.assertIn("FORMTRIG_AFLPP_REPO", build)
        self.assertIn("MAGMA_APT_MIRROR", build)
        self.assertIn("MAGMA_BASE_IMAGE", build)
        self.assertIn("MAGMA_GIT_INSTEAD_OF", build)
        self.assertIn("MAGMA_BUILD_NO_PROXY", build)
        self.assertIn("--build-arg\" \"$proxy_var=", build)
        self.assertIn("--build-arg\" \"MAGMA_APT_MIRROR", build)
        self.assertIn("--build-arg\" \"MAGMA_BASE_IMAGE", build)
        self.assertIn("--build-arg\" \"MAGMA_GIT_INSTEAD_OF", build)
        self.assertIn("ARG MAGMA_BASE_IMAGE=ubuntu:18.04", dockerfile)
        self.assertIn("FROM ${MAGMA_BASE_IMAGE}", dockerfile)
        self.assertIn("ARG MAGMA_APT_MIRROR", dockerfile)
        self.assertIn("ARG MAGMA_GIT_INSTEAD_OF", dockerfile)
        self.assertIn("git config --global url.", dockerfile)
        self.assertIn("insteadOf https://github.com/", dockerfile)
        self.assertIn("archive.ubuntu.com", dockerfile)
        self.assertIn("security.ubuntu.com", dockerfile)
        self.assertIn("Acquire::http::Timeout", dockerfile)
        self.assertIn("Acquire::http::Pipeline-Depth", dockerfile)
        self.assertIn("git ls-files -z | tar --null", build)
        self.assertIn("[ -d \"$FUZZER/repo\" ]", fetch)
        self.assertIn("prepackaged AFL++ repo", fetch)
        self.assertNotIn("__afl_sharedmem_fuzzing = 0", fetch)
        self.assertNotIn("SIG_AFL_NOT_PERSISTENT", fetch)
        self.assertIn("FORMTRIG_RUNTIME_ROOT", afl_makefile)
        self.assertIn("formtrig/formtrig_abi.h", afl_header)
        self.assertNotIn("../../../../formtrig", afl_header)
        self.assertIn("FORMTRIG_AFLPP", afl_queue)
        self.assertIn("formtrig_frontier_count", afl_stats)
        self.assertIn("formtrig_typed_execs", afl_stats)
        self.assertIn("formtrig_register_input", afl_driver)
        self.assertIn("formtrig_finalize", afl_driver)
        self.assertIn("ExecuteOneInput(callback, __afl_fuzz_ptr", afl_driver)

    def test_magma_campaign_manifest_stages_formtrig_native_graph(self) -> None:
        with tempfile.TemporaryDirectory(prefix="formtrig_magma_native_manifest_") as tmp:
            tmp_path = Path(tmp)
            matrix = tmp_path / "matrix.csv"
            graph_dir = tmp_path / "graphs"
            corpus_dir = tmp_path / "corpus"
            graph_dir.mkdir()
            corpus_dir.mkdir()
            graph = graph_dir / "PNG007.json"
            runtime_dir = tmp_path / "runtime_maps"
            runtime_dir.mkdir()
            runtime_map = runtime_dir / "PNG007.json"
            graph.write_text(json.dumps({"target_id": "PNG007", "nodes": [], "edges": []}))
            runtime_map.write_text(
                json.dumps(
                    {
                        "runtime_events": {
                            "source:example.c:10#f": {
                                "event_kind": "branch",
                                "site_id": 7,
                            }
                        }
                    }
                )
            )
            (corpus_dir / "seed").write_bytes(b"seed")
            (corpus_dir / "manifest.json").write_text("{}")
            with matrix.open("w", newline="") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "group",
                        "bug_id",
                        "target",
                        "patch",
                        "target_source",
                        "available",
                        "default_program",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "group": "weak",
                        "bug_id": "PNG007",
                        "target": "libpng",
                        "patch": "",
                        "target_source": "pngrtran.c:1967:8#png_read_transform_info",
                        "available": "True",
                        "default_program": "libpng_read_fuzzer",
                    }
                )
            manifest = tmp_path / "manifest.json"
            result = subprocess.run(
                [
                    sys.executable,
                    str(RUN_MAGMA_CAMPAIGN),
                    "--matrix",
                    str(matrix),
                    "--out-root",
                    str(tmp_path / "runs"),
                    "--variants",
                    "formtrig_native",
                    "--bugs",
                    "PNG007",
                    "--trigger-graph-dir",
                    str(graph_dir),
                    "--runtime-map-dir",
                    str(runtime_dir),
                    "--input-corpus",
                    str(corpus_dir),
                    "--manifest",
                    str(manifest),
                    "--timeout",
                    "1m",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            payload = json.loads(manifest.read_text())

        campaign = payload["campaigns"][0]
        self.assertEqual(campaign["variant"], "formtrig_native")
        self.assertEqual(campaign["env"]["FUZZER"], "formtrig_native")
        self.assertEqual(campaign["env"]["FORMTRIG_TRIGGER_GRAPH"], "/magma_shared/trigger_graph.json")
        self.assertEqual(campaign["env"]["FORMTRIG_RUNTIME_MAP"], "/magma_shared/formtrig_runtime_map.json")
        self.assertEqual(campaign["env"]["FORMTRIG_AFL_TIMEOUT"], "5000")
        self.assertNotIn("+", campaign["env"]["FORMTRIG_AFL_TIMEOUT"])
        self.assertEqual(Path(campaign["trigger_graph"]), graph.resolve())
        self.assertEqual(Path(campaign["runtime_map"]), runtime_map.resolve())
        self.assertEqual(Path(campaign["input_corpus"]), corpus_dir.resolve())

    def test_execute_manifest_copies_trigger_graph_to_shared_volume(self) -> None:
        module = load_execute_manifest_module()
        with tempfile.TemporaryDirectory(prefix="formtrig_magma_native_stage_") as tmp:
            tmp_path = Path(tmp)
            graph = tmp_path / "SQL013.json"
            runtime_map = tmp_path / "SQL013.runtime.json"
            corpus = tmp_path / "corpus"
            corpus.mkdir()
            graph.write_text(json.dumps({"target_id": "SQL013", "nodes": [], "edges": []}))
            runtime_map.write_text(json.dumps({"runtime_events": {"phase": {"event_kind": "branch", "site_id": 9}}}))
            (corpus / "seed").write_bytes(b"select 1;")
            (corpus / ".hidden").write_bytes(b"ignore")
            (corpus / "manifest.json").write_text("{}")
            campaign = {
                "shared": str(tmp_path / "shared"),
                "trigger_graph": str(graph),
                "input_corpus": str(corpus),
                "variant": "formtrig_native",
                "bug_id": "SQL013",
                "env": {"FORMTRIG_TRIGGER_GRAPH": "/magma_shared/trigger_graph.json"},
                "runtime_map": str(runtime_map),
            }
            shared = module.prepare_shared(campaign, clean=True)

            staged = shared / "trigger_graph.json"
            self.assertTrue(staged.is_file())
            self.assertEqual(json.loads(staged.read_text())["target_id"], "SQL013")
            self.assertEqual(
                json.loads((shared / "formtrig_runtime_map.json").read_text())["runtime_events"]["phase"]["site_id"],
                9,
            )
            self.assertEqual((shared / "input_corpus" / "seed").read_bytes(), b"select 1;")
            self.assertFalse((shared / "input_corpus" / ".hidden").exists())
            self.assertFalse((shared / "input_corpus" / "manifest.json").exists())
            self.assertEqual(json.loads((shared / "campaign.json").read_text())["trigger_graph"], str(graph))


if __name__ == "__main__":
    unittest.main()
