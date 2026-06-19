import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = REPO_ROOT / "tools" / "gpac3403_alias_relation_audit.py"


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_lift(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "role_component 8 3030846436 lifecycle_event 7 1 25 higher hit 1.0 0.85 1004 1004 any",
                "role_component 7 3013921722 lifecycle_event 8 1 26 higher a 1.0 0.9 1001 1001 any",
                "role_component 8 14730514 use 6 1 40 higher not_outcome 1.0 0.8 1005 1005 any",
                "role_component 7 65063371 use 8 1 42 higher a 1.0 0.9 1003 1003 any",
                "role_component 7 115396228 root_observe 3 1 50 higher not_outcome 1.0 0.9 1006 1006 any",
                "role_component 7 1549213408 same_object 8 1 60 higher a 1.0 0.85 1002 1002 any",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def component(source_id: int, value: int) -> dict:
    return {"source_id": source_id, "value": value}


class Gpac3403AliasRelationAuditTest(unittest.TestCase):
    def test_release_reassign_alias_without_cleanup_free_alias(self):
        audit = load_module(AUDIT_PATH, "gpac3403_alias_relation_audit_gap")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lift = root / "b7.normalized.lift"
            runtime = root / "runtime.jsonl"
            write_lift(lift)
            runtime.write_text(
                json.dumps(
                    {
                        "components": [
                            component(1001, 0x10000),
                            component(1002, 0x10000),
                            component(1003, 0x20000),
                            component(1004, 1),
                            component(1005, 1),
                            component(1006, 1),
                        ],
                        "D_F_spec_lifted": 2,
                        "reached": True,
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            report = audit.build_report(lift, [runtime])

        self.assertEqual(
            report["verdict"]["status"],
            "release_reassign_alias_observed_terminal_cleanup_missing",
        )
        self.assertFalse(report["verdict"]["complete_alias_free_relation"])
        self.assertTrue(report["verdict"]["release_reassign_alias_observed"])
        best = report["runtimes"][0]["best_record"]
        self.assertEqual(
            best["status"],
            "release_reassign_alias_without_cleanup_free_alias",
        )
        self.assertEqual(best["release_same_object_matches"], [0x10000])
        self.assertEqual(best["cleanup_values"], [0x20000])

    def test_alias_free_relation_requires_same_release_reassign_cleanup_pointer(self):
        audit = load_module(AUDIT_PATH, "gpac3403_alias_relation_audit_complete")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            lift = root / "b7.normalized.lift"
            runtime = root / "runtime.jsonl"
            write_lift(lift)
            runtime.write_text(
                json.dumps(
                    {
                        "components": [
                            component(1001, 0x30000),
                            component(1002, 0x30000),
                            component(1003, 0x30000),
                            component(1004, 1),
                            component(1005, 1),
                            component(1006, 1),
                        ],
                        "D_F_spec_lifted": 3,
                        "reached": True,
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            report = audit.build_report(lift, [runtime])

        self.assertEqual(report["verdict"]["status"], "alias_free_relation_proven")
        self.assertTrue(report["verdict"]["complete_alias_free_relation"])
        best = report["runtimes"][0]["best_record"]
        self.assertEqual(best["release_cleanup_matches"], [0x30000])
        self.assertEqual(best["same_object_cleanup_matches"], [0x30000])


if __name__ == "__main__":
    unittest.main()
