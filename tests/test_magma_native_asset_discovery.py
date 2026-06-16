import importlib.util
import json
import os
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


class MagmaNativeAssetDiscoveryTest(unittest.TestCase):
    def test_discovers_formtrig_native_site_map_name(self):
        discovery = load_tool("discover_magma_native_assets")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            site_map = root / "out" / "formtrig_native" / "formtrig_sites.tsv"
            site_map.parent.mkdir(parents=True)
            site_map.write_text("", encoding="utf-8")

            files = discovery.walk_files([root], max_files=20)

            self.assertEqual(discovery.site_map_paths(files), [site_map])

    def test_selector_match_accepts_suffix_paths_and_small_line_drift(self):
        discovery = load_tool("discover_magma_native_assets")

        self.assertTrue(
            discovery.selector_matches_row(
                {
                    "kind": "cmp",
                    "function": "_TIFFVSetField",
                    "file": "libtiff/tif_dir.c",
                    "line": "312",
                    "column": "8",
                },
                {
                    "kind": "cmp",
                    "function": "_TIFFVSetField",
                    "file": "tif_dir.c",
                    "line": "313",
                    "column": "13",
                },
            )
        )

        self.assertFalse(
            discovery.selector_matches_row(
                {
                    "kind": "cmp",
                    "function": "_TIFFVSetField",
                    "file": "libtiff/tif_dir.c",
                    "line": "312",
                },
                {
                    "kind": "cmp",
                    "function": "_TIFFVSetField",
                    "file": "tif_dir.c",
                    "line": "400",
                    "column": "13",
                },
            )
        )

    def test_discovers_runnable_assets_when_all_native_inputs_match(self):
        discovery = load_tool("discover_magma_native_assets")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = root / "PDF003.native_draft.yml"
            manifest = root / "PDF003.manifest.template"
            seed_dir = root / "rnt" / "PDF003" / "seeds"
            build_dir = root / "native-build"
            site_map = build_dir / "site_map.tsv"
            target_dir = build_dir / "out"
            executable = target_dir / "pdfimages"

            seed_dir.mkdir(parents=True)
            target_dir.mkdir(parents=True)
            executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            os.chmod(executable, 0o755)
            site_map.write_text(
                "101\tcmp\tFoFiTrueType::readPostTable\t7\ticmp\t/poppler/FoFiTrueType.cc\t1713\t9\n",
                encoding="utf-8",
            )
            spec.write_text(
                "\n".join(
                    [
                        "tc_id: PDF003",
                        "conditions:",
                        "  - id: post_table_null",
                        "    observe_at:",
                        "      kind: cmp",
                        "      function: FoFiTrueType::readPostTable",
                        "      file: FoFiTrueType.cc",
                        "      line: 1713",
                        "      column: 9",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            manifest.write_text(
                "\n".join(
                    [
                        "target_id: PDF003",
                        "category: binary-null",
                        f"seed_dir: {seed_dir}",
                        f"binding_spec: {spec}",
                        "site_map: TODO_FORMTRIG_NATIVE_SITE_MAP_FOR_PDF003.tsv",
                        "target_cwd: TODO_FORMTRIG_NATIVE_TARGET_CWD_FOR_PDF003",
                        "target_cmd: TODO_FORMTRIG_MAGMA_POPPLER_PDFIMAGES_BINARY @@ /tmp/pdf-out",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            drafts = root / "drafts.json"
            drafts.write_text(
                json.dumps(
                    {
                        "drafts": [
                            {
                                "target_id": "PDF003",
                                "project": "poppler",
                                "program": "pdfimages",
                                "category": "binary-state-null",
                                "binding_spec": str(spec),
                                "manifest_template": str(manifest),
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            rnt_status = root / "rnt_status.json"
            rnt_status.write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "target_id": "PDF003",
                                "status": "formal_ready",
                                "seed_dir_exists": "true",
                                "seed_dir": str(seed_dir),
                                "seed_files": "12",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            report, assets = discovery.build_discovery(
                drafts_path=drafts,
                rnt_status_path=rnt_status,
                search_roots=[root],
                max_files=100,
                source_discovery_path=root / "discovery.json",
            )

            self.assertEqual(report["runnable_candidate_count"], 1)
            row = report["targets"][0]
            self.assertTrue(row["runnable_candidate"])
            self.assertEqual(row["best_site_map"]["matched_selectors"], 1)
            self.assertEqual(row["executable_candidates"], [str(executable)])
            target = assets["targets"]["PDF003"]
            self.assertEqual(target["seed_dir"], str(seed_dir))
            self.assertEqual(target["site_map"], str(site_map))
            self.assertEqual(target["target_cwd"], str(target_dir))
            self.assertEqual(target["target_cmd"], f"{executable} @@ /tmp/pdf-out")
            self.assertEqual(target["runner_category"], "binary-null")
            self.assertEqual(target["discovery_status"], "runnable_candidate")
            self.assertEqual(target["discovery_blockers"], [])
            self.assertEqual(assets["source_discovery"], str(root / "discovery.json"))

    def test_keeps_todo_assets_when_rnt_site_map_or_executable_is_missing(self):
        discovery = load_tool("discover_magma_native_assets")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = root / "SSL011.native_draft.yml"
            manifest = root / "SSL011.manifest.template"
            spec.write_text(
                "\n".join(
                    [
                        "tc_id: SSL011",
                        "conditions:",
                        "  - id: asn1_state",
                        "    observe_at:",
                        "      kind: cmp",
                        "      function: asn1_item_embed_d2i",
                        "      file: tasn_dec.c",
                        "      line: 514",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            manifest.write_text(
                "\n".join(
                    [
                        "target_id: SSL011",
                        "category: binary-null",
                        "seed_dir: TODO_FORMAL_RNT_SEED_DIR_FOR_SSL011",
                        f"binding_spec: {spec}",
                        "site_map: TODO_FORMTRIG_NATIVE_SITE_MAP_FOR_SSL011.tsv",
                        "target_cwd: TODO_FORMTRIG_NATIVE_TARGET_CWD_FOR_SSL011",
                        "target_cmd: TODO_FORMTRIG_MAGMA_OPENSSL_ASN1_BINARY @@",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            drafts = root / "drafts.json"
            drafts.write_text(
                json.dumps(
                    {
                        "drafts": [
                            {
                                "target_id": "SSL011",
                                "project": "openssl",
                                "program": "asn1",
                                "category": "binary-state-null",
                                "binding_spec": str(spec),
                                "manifest_template": str(manifest),
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            rnt_status = root / "rnt_status.json"
            rnt_status.write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "target_id": "SSL011",
                                "status": "excluded",
                                "seed_dir_exists": "false",
                                "seed_dir": "",
                                "seed_files": "",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            report, assets = discovery.build_discovery(
                drafts_path=drafts,
                rnt_status_path=rnt_status,
                search_roots=[root],
                max_files=100,
            )

            self.assertEqual(report["runnable_candidate_count"], 0)
            row = report["targets"][0]
            self.assertFalse(row["runnable_candidate"])
            self.assertIn("formal RNT seed corpus is not ready: excluded", row["blockers"])
            self.assertIn("no site_map.tsv matched the BindingSpec source selectors", row["blockers"])
            self.assertIn("no executable found for program asn1", row["blockers"])
            target = assets["targets"]["SSL011"]
            self.assertEqual(target["seed_dir"], "TODO_FORMAL_RNT_SEED_DIR_FOR_SSL011")
            self.assertEqual(target["site_map"], "TODO_FORMTRIG_NATIVE_SITE_MAP_FOR_SSL011.tsv")
            self.assertEqual(target["target_cwd"], "TODO_FORMTRIG_NATIVE_TARGET_CWD_FOR_SSL011")
            self.assertEqual(target["target_cmd"], "TODO_FORMTRIG_MAGMA_OPENSSL_ASN1_BINARY @@")
            self.assertEqual(target["discovery_status"], "blocked")


if __name__ == "__main__":
    unittest.main()
