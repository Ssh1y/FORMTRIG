import subprocess
import tempfile
from pathlib import Path
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]


class BindingSpecCompileSourceMatchingTest(unittest.TestCase):
    def build_tool(self, root: Path) -> Path:
        tool = root / "formtrig_binding_spec_compile"
        subprocess.run(
            [
                "cc",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-I",
                str(REPO_ROOT / "formtrig" / "include"),
                str(REPO_ROOT / "formtrig" / "tools" / "formtrig_binding_spec_compile.c"),
                "-o",
                str(tool),
            ],
            check=True,
        )
        return tool

    def build_lift_audit_tool(self, root: Path) -> Path:
        tool = root / "formtrig_lift_spec_audit"
        subprocess.run(
            [
                "cc",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-I",
                str(REPO_ROOT / "formtrig" / "include"),
                str(REPO_ROOT / "formtrig" / "tools" / "formtrig_lift_spec_audit.c"),
                "-o",
                str(tool),
            ],
            check=True,
        )
        return tool

    def write_spec(self, path: Path, *, line: int) -> None:
        path.write_text(
            "\n".join(
                [
                    "tc_id: TIF012",
                    "tc:",
                    "  category: binary-state-null",
                    "  expression: synthetic",
                    "atoms:",
                    "  - id: 1",
                    "    expr: synthetic",
                    "    kind: binary-state-null",
                    "    root: v",
                    "bindings:",
                    "  - id: tif012_source",
                    "    atom: 1",
                    "    role: root_observe",
                    "    expr: source selector",
                    "    observe_at:",
                    "      kind: cmp",
                    "      function: _TIFFVSetField",
                    "      file: libtiff/tif_dir.c",
                    f"      line: {line}",
                    "      column: 8",
                    "    component: root_state",
                    "    priority: 10",
                    "    direction: higher",
                    "    value_mode: outcome",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

    def test_compiler_accepts_suffix_path_line_drift_and_column_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tool = self.build_tool(root)
            site_map = root / "formtrig_sites.tsv"
            spec = root / "TIF012.yml"
            site_map.write_text(
                "123\tcmp\t_TIFFVSetField\t460\ticmp\ttif_dir.c\t313\t13\n",
                encoding="utf-8",
            )
            self.write_spec(spec, line=312)

            proc = subprocess.run(
                [str(tool), "--site-map", str(site_map), str(spec)],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("role_component 7 123", proc.stdout)
            self.assertIn("relaxed_line_column", proc.stderr)

    def test_compiler_rejects_large_line_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tool = self.build_tool(root)
            site_map = root / "formtrig_sites.tsv"
            spec = root / "TIF012.yml"
            site_map.write_text(
                "123\tcmp\t_TIFFVSetField\t460\ticmp\ttif_dir.c\t313\t13\n",
                encoding="utf-8",
            )
            self.write_spec(spec, line=400)

            proc = subprocess.run(
                [str(tool), "--site-map", str(site_map), str(spec)],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.assertNotEqual(proc.returncode, 0)
            self.assertIn("source mapping is missing", proc.stderr)

    def test_compiler_accepts_cpp_itanium_member_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tool = self.build_tool(root)
            site_map = root / "formtrig_sites.tsv"
            spec = root / "PDF003.yml"
            site_map.write_text(
                "\n".join(
                    [
                        "1856372469\tcmp\t_ZN14ImageOutputDev14writeImageFileEP9ImgWriterNS_11ImageFormatEPKcP6StreamiiP16GfxImageColorMap\t144\ticmp\t/home/cwh/poppler/utils/ImageOutputDev.cc\t407\t9",
                        "1806039612\tcmp\t_ZN14ImageOutputDev14writeImageFileEP9ImgWriterNS_11ImageFormatEPKcP6StreamiiP16GfxImageColorMap\t147\ticmp\t/home/cwh/poppler/utils/ImageOutputDev.cc\t407\t9",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            spec.write_text(
                "\n".join(
                    [
                        "tc_id: PDF003",
                        "tc:",
                        "  category: binary-state-null",
                        "  expression: synthetic",
                        "atoms:",
                        "  - id: 1",
                        "    expr: synthetic",
                        "    kind: binary-state-null",
                        "    root: colorMap",
                        "bindings:",
                        "  - id: pdf003_source",
                        "    atom: 1",
                        "    role: root_observe",
                        "    expr: source selector",
                        "    observe_at:",
                        "      kind: cmp",
                        "      function: ImageOutputDev::writeImageFile",
                        "      file: utils/ImageOutputDev.cc",
                        "      line: 407",
                        "      inst_no: 144",
                        "      column: 9",
                        "    component: root_state",
                        "    priority: 10",
                        "    direction: higher",
                        "    value_mode: outcome",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            proc = subprocess.run(
                [str(tool), "--site-map", str(site_map), str(spec)],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("role_component 7 1856372469", proc.stdout)

    def test_gpac3403_lifecycle_spec_compiles_without_role_collapse(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            compile_tool = self.build_tool(root)
            audit_tool = self.build_lift_audit_tool(root)
            site_map = root / "gpac_sites.tsv"
            lift_spec = root / "gpac.lift"
            site_map.write_text(
                "\n".join(
                    [
                        "2074894587\tbinary\tMedia_GetSample\t795\tadd\tisomedia/media.c\t633\t47",
                        "2693650777\tbranch\tcat_isomedia_file\t1189\tbr\tfileimport.c\t3139\t8",
                        "3030846436\tbranch\tgf_isom_sample_del\t22\tbr\tisomedia/isom_read.c\t112\t6",
                        "3232240958\tbranch\tgf_bs_new_cbk_buffer\t34\tbr\tutils/bitstream.c\t296\t6",
                        "3837068185\tbranch\tmdia_box_del\t25\tbr\tisomedia/box_code_base.c\t3310\t6",
                        "65063371\tcmp\tgf_bs_del\t47\ticmp\tutils/bitstream.c\t372\t48",
                        "3299351434\tcmp\tgf_bs_new_cbk_buffer\t30\ticmp\tutils/bitstream.c\t296\t6",
                        "2708309825\tbranch\tcat_isomedia_file\t1178\tbr\tfileimport.c\t3136\t3",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            compile_proc = subprocess.run(
                [
                    str(compile_tool),
                    "--site-map",
                    str(site_map),
                    "--out",
                    str(lift_spec),
                    str(
                        REPO_ROOT
                        / "artifacts"
                        / "binding_specs"
                        / "GPAC_3403.native_b1_bitstream_lifecycle_candidate.yml"
                    ),
                ],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(compile_proc.returncode, 0, compile_proc.stderr)

            lift_text = lift_spec.read_text(encoding="utf-8")
            self.assertIn("role_component 7 3299351434 same_object", lift_text)
            self.assertIn(
                "same_object_relation 1 lifecycle_event use "
                "GF_ISOSample.data==GF_BitStream.original",
                lift_text,
            )

            audit_proc = subprocess.run(
                [str(audit_tool), "--category", "lifecycle", str(lift_spec)],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            self.assertEqual(audit_proc.returncode, 0, audit_proc.stderr)
            self.assertIn(
                "1,compound-sequence-lifecycle,B4,true,0x000001e9,9,0,0,ok",
                audit_proc.stdout,
            )


if __name__ == "__main__":
    unittest.main()
