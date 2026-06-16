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


if __name__ == "__main__":
    unittest.main()
