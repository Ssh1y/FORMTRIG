import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SWEEP_PATH = REPO_ROOT / "tools" / "gpac3403_hevc_frontier_sweep.py"
HOOK_PATH = REPO_ROOT / "scripts" / "formtrig_hooks" / "hevc_annexb_structure_hook.py"


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sample_hevc():
    def nalu(nal_type, payload):
        return b"\x00\x00\x00\x01" + bytes([(nal_type << 1) & 0x7E, 1]) + payload

    return (
        nalu(32, b"\x01\x02\x03\x80")
        + nalu(33, b"\x04\x05\x06\x80")
        + nalu(34, b"\x07\x08\x80")
        + nalu(19, b"\x09\x0a\x0b\x0c\x80")
    )


class Gpac3403HevcFrontierSweepTest(unittest.TestCase):
    def test_generates_unique_annexb_variants(self):
        sweep = load_module(SWEEP_PATH, "gpac3403_hevc_frontier_sweep")
        hook = load_module(HOOK_PATH, "hevc_annexb_structure_hook_for_sweep")
        seed = sample_hevc()

        with tempfile.TemporaryDirectory() as tmp:
            variants = sweep.generate_variants(
                hook=hook,
                seed=seed,
                ranges=[(0, len(seed))],
                max_variants=24,
                op_start=0,
                op_count=8,
                sample_count=8,
                variants_dir=Path(tmp),
            )

        self.assertEqual(len({v.sha256 for v in variants}), len(variants))
        self.assertGreaterEqual(len(variants), 8)
        self.assertTrue(all(v.size > 0 for v in variants))

    def test_generate_variants_can_target_later_operator_window(self):
        sweep = load_module(SWEEP_PATH, "gpac3403_hevc_frontier_sweep_op_start")
        hook = load_module(HOOK_PATH, "hevc_annexb_structure_hook_for_sweep_op_start")
        seed = sample_hevc()

        with tempfile.TemporaryDirectory() as tmp:
            variants = sweep.generate_variants(
                hook=hook,
                seed=seed,
                ranges=[(0, len(seed))],
                max_variants=12,
                op_start=8,
                op_count=2,
                sample_count=8,
                variants_dir=Path(tmp),
            )

        self.assertTrue(variants)
        self.assertTrue(all(8 <= v.op < 10 for v in variants))

    def test_summary_counts_trigger_and_same_object(self):
        sweep = load_module(SWEEP_PATH, "gpac3403_hevc_frontier_sweep_summary")
        records = [
            sweep.ReplayRecord(
                index=0,
                op=0,
                sample=0,
                start=0,
                span=10,
                off=0,
                sha256="a",
                size=10,
                path="a",
                runtime_log="a.log",
                stdout_log="a.out",
                stderr_log="a.err",
                exit_code=0,
                timed_out=False,
                reached=True,
                triggered=False,
                spec_lifted=True,
                target_hit_count=1,
                d_f_spec_lifted=2.0,
                roles=["root_observe"],
                role_bits=["root_observe"],
                trace_signature="1",
            ),
            sweep.ReplayRecord(
                index=1,
                op=1,
                sample=0,
                start=0,
                span=10,
                off=1,
                sha256="b",
                size=11,
                path="b",
                runtime_log="b.log",
                stdout_log="b.out",
                stderr_log="b.err",
                exit_code=0,
                timed_out=False,
                reached=True,
                triggered=True,
                spec_lifted=True,
                target_hit_count=1,
                d_f_spec_lifted=0.0,
                roles=["same_object"],
                role_bits=["same_object", "use"],
                trace_signature="2",
            ),
        ]

        summary = sweep.summarize(records, generated=2, seed_sha256="seed")

        self.assertEqual(summary["triggered"], 1)
        self.assertEqual(summary["rnt"], 1)
        self.assertEqual(summary["d_f_spec_lifted_min"], 0.0)
        self.assertEqual(summary["same_object_samples"], 1)
        self.assertEqual(summary["reached_same_object_samples"], 1)
        self.assertEqual(summary["role_sample_counts"]["use"], 1)

    def test_event_map_prefers_root_observe_target_site_ids(self):
        sweep = load_module(SWEEP_PATH, "gpac3403_hevc_frontier_sweep_event_map")

        with tempfile.TemporaryDirectory() as tmp:
            event_map = Path(tmp) / "formtrig_runtime_event_map.csv"
            event_map.write_text(
                "site_id,role,name\n"
                "111,use,use-site\n"
                "222,root_observe,root-site\n"
                "333,same_object,same-object-site\n",
                encoding="utf-8",
            )

            target_site_ids = sweep.target_site_ids_from_event_map(event_map)

        self.assertEqual(target_site_ids, "222")

    def test_endpoint_probe_detects_sanitizer_exit_and_summary(self):
        sweep = load_module(SWEEP_PATH, "gpac3403_hevc_frontier_sweep_endpoint")

        with tempfile.TemporaryDirectory() as tmp:
            input_path = Path(tmp) / "input.hevc"
            input_path.write_bytes(sample_hevc())
            probes = sweep.run_endpoint_probes(
                input_path=str(input_path),
                kind="variant",
                log_prefix="variant_000000",
                endpoint_cmd=[
                    sys.executable,
                    "-c",
                    "import sys; sys.stderr.write('SUMMARY: AddressSanitizer: boom\\n'); sys.exit(86)",
                    "@@",
                ],
                out_dir=Path(tmp),
                endpoint_env={},
                timeout_s=5.0,
                reps=1,
                sanitizer_exit_code=86,
            )

        self.assertEqual(len(probes), 1)
        self.assertEqual(probes[0].exit_code, 86)
        self.assertTrue(probes[0].sanitizer_crash)
        self.assertFalse(probes[0].native_crash)
        self.assertTrue(probes[0].stderr_sha256)

    def test_summary_counts_endpoint_crashes(self):
        sweep = load_module(SWEEP_PATH, "gpac3403_hevc_frontier_sweep_endpoint_summary")
        record = sweep.ReplayRecord(
            index=0,
            op=0,
            sample=0,
            start=0,
            span=10,
            off=0,
            sha256="a",
            size=10,
            path="a",
            runtime_log="a.log",
            stdout_log="a.out",
            stderr_log="a.err",
            exit_code=0,
            timed_out=False,
            reached=True,
            triggered=False,
            spec_lifted=True,
            target_hit_count=1,
            d_f_spec_lifted=1.0,
            roles=["root_observe"],
            role_bits=["root_observe"],
            trace_signature="1",
            endpoint_probes=[
                sweep.EndpointProbe(
                    kind="variant",
                    rep=1,
                    input="a",
                    stdout_log="a.endpoint.out",
                    stderr_log="a.endpoint.err",
                    exit_code=86,
                    timed_out=False,
                    sanitizer_crash=True,
                    native_crash=False,
                    stdout_sha256="stdout",
                    stderr_sha256="stderr",
                )
            ],
        )

        summary = sweep.summarize([record], generated=1, seed_sha256="seed")

        self.assertEqual(summary["endpoint_replayed_variants"], 1)
        self.assertEqual(summary["endpoint_probe_runs"], 1)
        self.assertEqual(summary["endpoint_sanitizer_crashes"], 1)
        self.assertEqual(summary["endpoint_native_crashes"], 0)
        self.assertEqual(summary["endpoint_exit_code_counts"]["86"], 1)


if __name__ == "__main__":
    unittest.main()
