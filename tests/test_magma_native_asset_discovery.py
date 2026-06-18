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

    def test_selector_match_accepts_magma_macro_line_drift_with_exact_function(self):
        discovery = load_tool("discover_magma_native_assets")

        self.assertTrue(
            discovery.selector_matches_row(
                {
                    "kind": "cmp",
                    "function": "PKCS7_dataDecode",
                    "file": "crypto/pkcs7/pk7_doit.c",
                    "line": "440",
                },
                {
                    "kind": "cmp",
                    "function": "PKCS7_dataDecode",
                    "file": "crypto/pkcs7/pk7_doit.c",
                    "line": "436",
                    "column": "5",
                },
            )
        )
        self.assertFalse(
            discovery.selector_matches_row(
                {
                    "kind": "cmp",
                    "function": "PKCS7_dataDecode",
                    "file": "crypto/pkcs7/pk7_doit.c",
                    "line": "440",
                },
                {
                    "kind": "cmp",
                    "function": "PKCS7_dataInit",
                    "file": "crypto/pkcs7/pk7_doit.c",
                    "line": "436",
                    "column": "5",
                },
            )
        )

    def test_selector_match_accepts_itanium_mangled_cpp_member_names(self):
        discovery = load_tool("discover_magma_native_assets")

        self.assertEqual(
            discovery.itanium_member_prefix(
                "_ZN14ImageOutputDev14writeImageFileEP9ImgWriterNS_11ImageFormatEPKcP6StreamiiP16GfxImageColorMap"
            ),
            "ImageOutputDev::writeImageFile",
        )
        self.assertTrue(
            discovery.selector_matches_row(
                {
                    "kind": "cmp",
                    "function": "ImageOutputDev::writeImageFile",
                    "file": "utils/ImageOutputDev.cc",
                    "line": "406",
                },
                {
                    "kind": "cmp",
                    "function": "_ZN14ImageOutputDev14writeImageFileEP9ImgWriterNS_11ImageFormatEPKcP6StreamiiP16GfxImageColorMap",
                    "file": "/work/poppler/repo/utils/ImageOutputDev.cc",
                    "line": "407",
                    "column": "9",
                },
            )
        )
        self.assertFalse(
            discovery.selector_matches_row(
                {
                    "kind": "cmp",
                    "function": "ImageOutputDev::writeImageFile",
                    "file": "utils/ImageOutputDev.cc",
                    "line": "406",
                },
                {
                    "kind": "cmp",
                    "function": "_ZN14ImageOutputDev20getInlineImageLengthEP6StreamiiP16GfxImageColorMap",
                    "file": "/work/poppler/repo/utils/ImageOutputDev.cc",
                    "line": "407",
                    "column": "9",
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
                        "afl_args: -t 5000",
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
            self.assertEqual(target["afl_args"], "-t 5000")
            self.assertEqual(target["runner_category"], "binary-null")
            self.assertEqual(target["discovery_status"], "runnable_candidate")
            self.assertEqual(target["discovery_blockers"], [])
            self.assertEqual(assets["source_discovery"], str(root / "discovery.json"))

    def test_prefers_site_map_from_same_native_build_as_executable(self):
        discovery = load_tool("discover_magma_native_assets")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = root / "SSL011.native_draft.yml"
            manifest = root / "SSL011.manifest.template"
            seed_dir = root / "rnt" / "SSL011" / "seeds"
            builds = root / "artifacts" / "formtrig_native_readiness" / "magma_native_builds"
            stale_site_map = builds / "SSL011" / "out" / "formtrig_native" / "formtrig_sites.tsv"
            selected_site_map = builds / "SSL011_pkcs7_decode" / "out" / "formtrig_native" / "formtrig_sites.tsv"
            target_dir = builds / "SSL011_pkcs7_decode" / "out" / "afl"
            executable = target_dir / "pkcs7_decode"

            seed_dir.mkdir(parents=True)
            stale_site_map.parent.mkdir(parents=True)
            selected_site_map.parent.mkdir(parents=True)
            target_dir.mkdir(parents=True)
            executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            os.chmod(executable, 0o755)
            row = "688326304\tcmp\tPKCS7_dataDecode\t295\ticmp\tcrypto/pkcs7/pk7_doit.c\t514\t9\n"
            stale_site_map.write_text(row, encoding="utf-8")
            selected_site_map.write_text(row, encoding="utf-8")
            spec.write_text(
                "\n".join(
                    [
                        "tc_id: SSL011",
                        "conditions:",
                        "  - id: ssl011_canary",
                        "    observe_at:",
                        "      kind: cmp",
                        "      function: PKCS7_dataDecode",
                        "      file: crypto/pkcs7/pk7_doit.c",
                        "      line: 514",
                        "      column: 9",
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
                        f"seed_dir: {seed_dir}",
                        f"binding_spec: {spec}",
                        "site_map: TODO_FORMTRIG_NATIVE_SITE_MAP_FOR_SSL011.tsv",
                        "target_cwd: TODO_FORMTRIG_NATIVE_TARGET_CWD_FOR_SSL011",
                        "target_cmd: TODO_FORMTRIG_MAGMA_OPENSSL_PKCS7_DECODE_BINARY -",
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
                                "program": "pkcs7_decode",
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
                                "program": "pkcs7_decode",
                                "status": "formal_ready",
                                "seed_dir_exists": "true",
                                "seed_dir": str(seed_dir),
                                "seed_files": "1",
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
                search_roots=[builds],
                max_files=100,
                source_discovery_path=root / "discovery.json",
            )

            self.assertEqual(report["runnable_candidate_count"], 1)
            target = assets["targets"]["SSL011"]
            self.assertEqual(target["site_map"], str(selected_site_map))
            self.assertTrue(report["targets"][0]["best_site_map"]["same_build_as_executable"])

    def test_same_program_assets_prefer_target_native_build(self):
        discovery = load_tool("discover_magma_native_assets")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            builds = root / "artifacts" / "formtrig_native_readiness" / "magma_native_builds"
            seed_root = root / "rnt"
            draft_rows = []
            records = []

            def write_target(target_id: str, build_name: str, line: int) -> tuple[Path, Path]:
                spec = root / f"{target_id}.yml"
                manifest = root / f"{target_id}.manifest.template"
                seed_dir = seed_root / target_id / "seeds"
                build = builds / build_name
                site_map = build / "out" / "formtrig_native" / "formtrig_sites.tsv"
                target_dir = build / "out" / "afl"
                executable = target_dir / "pkcs7_decode"

                seed_dir.mkdir(parents=True)
                site_map.parent.mkdir(parents=True)
                target_dir.mkdir(parents=True)
                executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
                os.chmod(executable, 0o755)
                site_map.write_text(
                    f"101\tcmp\tPKCS7_dataDecode\t7\ticmp\tcrypto/pkcs7/pk7_doit.c\t{line}\t5\n",
                    encoding="utf-8",
                )
                spec.write_text(
                    "\n".join(
                        [
                            f"tc_id: {target_id}",
                            "conditions:",
                            "  - id: pkcs7_state",
                            "    observe_at:",
                            "      kind: cmp",
                            "      function: PKCS7_dataDecode",
                            "      file: crypto/pkcs7/pk7_doit.c",
                            f"      line: {line}",
                        ]
                    )
                    + "\n",
                    encoding="utf-8",
                )
                manifest.write_text(
                    "\n".join(
                        [
                            f"target_id: {target_id}",
                            "category: binary-null",
                            f"seed_dir: {seed_dir}",
                            f"binding_spec: {spec}",
                            f"site_map: {site_map}",
                            f"target_cwd: {target_dir}",
                            "target_cmd: TODO_FORMTRIG_MAGMA_OPENSSL_PKCS7_DECODE_BINARY -",
                        ]
                    )
                    + "\n",
                    encoding="utf-8",
                )
                draft_rows.append(
                    {
                        "target_id": target_id,
                        "project": "openssl",
                        "program": "pkcs7_decode",
                        "category": "binary-state-null",
                        "binding_spec": str(spec),
                        "manifest_template": str(manifest),
                    }
                )
                records.append(
                    {
                        "target_id": target_id,
                        "program": "pkcs7_decode",
                        "status": "formal_ready",
                        "seed_dir_exists": "true",
                        "seed_dir": str(seed_dir),
                        "seed_files": "1",
                    }
                )
                return site_map, executable

            ssl011_site, ssl011_exe = write_target("SSL011", "SSL011_pkcs7_decode", 514)
            ssl015_site, ssl015_exe = write_target("SSL015", "SSL015", 436)
            drafts = root / "drafts.json"
            drafts.write_text(json.dumps({"drafts": draft_rows}) + "\n", encoding="utf-8")
            rnt_status = root / "rnt_status.json"
            rnt_status.write_text(json.dumps({"records": records}) + "\n", encoding="utf-8")

            _report, assets = discovery.build_discovery(
                drafts_path=drafts,
                rnt_status_path=rnt_status,
                search_roots=[builds],
                max_files=100,
            )

            self.assertEqual(assets["targets"]["SSL011"]["site_map"], str(ssl011_site))
            self.assertEqual(assets["targets"]["SSL011"]["target_cmd"], f"{ssl011_exe} -")
            self.assertEqual(assets["targets"]["SSL015"]["site_map"], str(ssl015_site))
            self.assertEqual(assets["targets"]["SSL015"]["target_cmd"], f"{ssl015_exe} -")

    def test_blocks_formal_rnt_from_different_program(self):
        discovery = load_tool("discover_magma_native_assets")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = root / "SSL011.native_draft.yml"
            manifest = root / "SSL011.manifest.template"
            seed_dir = root / "rnt" / "SSL011" / "seeds"
            build_dir = root / "native-build"
            site_map = build_dir / "formtrig_sites.tsv"
            target_dir = build_dir / "out"
            executable = target_dir / "pkcs7_decode"

            seed_dir.mkdir(parents=True)
            target_dir.mkdir(parents=True)
            executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            os.chmod(executable, 0o755)
            site_map.write_text(
                "101\tcmp\tPKCS7_dataDecode\t7\ticmp\tcrypto/pkcs7/pk7_doit.c\t436\t5\n",
                encoding="utf-8",
            )
            spec.write_text(
                "\n".join(
                    [
                        "tc_id: SSL011",
                        "conditions:",
                        "  - id: pkcs7_state",
                        "    observe_at:",
                        "      kind: cmp",
                        "      function: PKCS7_dataDecode",
                        "      file: crypto/pkcs7/pk7_doit.c",
                        "      line: 440",
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
                        "seed_dir: TODO_FORMAL_RNT_SEED_DIR_FOR_SSL011_PKCS7_DECODE",
                        f"binding_spec: {spec}",
                        "site_map: TODO_FORMTRIG_NATIVE_SITE_MAP_FOR_SSL011.tsv",
                        "target_cwd: TODO_FORMTRIG_NATIVE_TARGET_CWD_FOR_SSL011",
                        "target_cmd: TODO_FORMTRIG_MAGMA_OPENSSL_PKCS7_DECODE_BINARY @@",
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
                                "program": "pkcs7_decode",
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
                                "program": "asn1",
                                "status": "formal_ready",
                                "seed_dir_exists": "true",
                                "seed_dir": str(seed_dir),
                                "seed_files": "3",
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
            self.assertIn(
                "formal RNT seed corpus is not ready for program pkcs7_decode",
                "; ".join(row["blockers"]),
            )
            target = assets["targets"]["SSL011"]
            self.assertEqual(target["seed_dir"], "TODO_FORMAL_RNT_SEED_DIR_FOR_SSL011_PKCS7_DECODE")
            self.assertEqual(target["site_map"], str(site_map))
            self.assertEqual(target["target_cmd"], f"{executable} @@")

    def test_draft_category_takes_precedence_over_stale_manifest_category(self):
        discovery = load_tool("discover_magma_native_assets")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            spec = root / "PHP009.yml"
            manifest = root / "PHP009.manifest.template"
            seed_dir = root / "rnt" / "PHP009" / "seeds"
            build_dir = root / "native-build"
            site_map = build_dir / "formtrig_sites.tsv"
            target_dir = build_dir / "out"
            executable = target_dir / "exif"

            seed_dir.mkdir(parents=True)
            target_dir.mkdir(parents=True)
            executable.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            os.chmod(executable, 0o755)
            site_map.write_text(
                "101\tcmp\texif_process_IFD_in_TIFF\t7\ticmp\text/exif/exif.c\t123\t5\n",
                encoding="utf-8",
            )
            spec.write_text(
                "\n".join(
                    [
                        "tc_id: PHP009",
                        "conditions:",
                        "  - id: margin",
                        "    observe_at:",
                        "      kind: cmp",
                        "      function: exif_process_IFD_in_TIFF",
                        "      file: ext/exif/exif.c",
                        "      line: 123",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            manifest.write_text(
                "\n".join(
                    [
                        "target_id: PHP009",
                        "category: lifecycle",
                        f"seed_dir: {seed_dir}",
                        f"binding_spec: {spec}",
                        "site_map: TODO_FORMTRIG_NATIVE_SITE_MAP.tsv",
                        "target_cwd: TODO_FORMTRIG_NATIVE_TARGET_CWD",
                        "target_cmd: TODO_FORMTRIG_MAGMA_PHP_EXIF_BINARY @@",
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
                                "target_id": "PHP009",
                                "project": "php",
                                "program": "exif",
                                "category": "numeric-margin",
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
                                "target_id": "PHP009",
                                "program": "exif",
                                "status": "formal_ready",
                                "seed_dir_exists": "true",
                                "seed_dir": str(seed_dir),
                                "seed_files": "3",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            _report, assets = discovery.build_discovery(
                drafts_path=drafts,
                rnt_status_path=rnt_status,
                search_roots=[root],
                max_files=100,
            )

            self.assertEqual(assets["targets"]["PHP009"]["category"], "numeric-margin")
            self.assertEqual(assets["targets"]["PHP009"]["runner_category"], "numeric")

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
            self.assertEqual(target["seed_dir"], "TODO_FORMAL_RNT_SEED_DIR_FOR_SSL011_ASN1")
            self.assertEqual(target["site_map"], "TODO_FORMTRIG_NATIVE_SITE_MAP_FOR_SSL011.tsv")
            self.assertEqual(target["target_cwd"], "TODO_FORMTRIG_NATIVE_TARGET_CWD_FOR_SSL011")
            self.assertEqual(target["target_cmd"], "TODO_FORMTRIG_MAGMA_OPENSSL_ASN1_BINARY @@")
            self.assertEqual(target["discovery_status"], "blocked")


if __name__ == "__main__":
    unittest.main()
