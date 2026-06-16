import json
import importlib.util
import tempfile
from pathlib import Path
import unittest


def load_tool():
    path = Path(__file__).resolve().parents[1] / "tools" / "draft_magma_binding_specs.py"
    spec = importlib.util.spec_from_file_location("draft_magma_binding_specs", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class DraftMagmaBindingSpecsTest(unittest.TestCase):
    def test_drafts_spec_and_manifest_template_from_queue(self):
        drafts = load_tool()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            inventory = root / "inventory.json"
            queue = root / "queue.json"
            spec_dir = root / "specs"
            template_dir = root / "templates"
            inventory.write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "target_id": "PDF003",
                                "project": "poppler",
                                "program": "pdfimages",
                                "args_template": "@@ /tmp/out",
                                "initial_seed_corpus": "corpus/pdfimages",
                                "primary_tc_category": "binary-state-null",
                                "secondary_tc_category": "compound-sequence-lifecycle",
                                "canary_expression": "obj == nullptr",
                                "target_location": "utils/ImageOutputDev.cc:406:8#ImageOutputDev::writeImageFile",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            queue.write_text(
                json.dumps(
                    {
                        "top_targets": [
                            {
                                "target_id": "PDF003",
                                "source": "magma",
                                "lane": "binding_spec_first",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            payload = drafts.build_drafts(
                inventory_path=inventory,
                queue_path=queue,
                target_ids=[],
                limit=4,
                spec_dir=spec_dir,
                template_dir=template_dir,
                source_kind="cmp",
                max_locations=2,
                overwrite=False,
            )

            self.assertEqual(len(payload["drafts"]), 1)
            self.assertEqual(payload["inputs"]["selection_source"], "queue_binding_spec_first")
            self.assertEqual(payload["inputs"]["target_ids"], ["PDF003"])
            spec_path = Path(payload["drafts"][0]["binding_spec"])
            template_path = Path(payload["drafts"][0]["manifest_template"])
            spec = spec_path.read_text(encoding="utf-8")
            template = template_path.read_text(encoding="utf-8")
            self.assertIn("tc_id: 'PDF003'", spec)
            self.assertIn("function: 'ImageOutputDev::writeImageFile'", spec)
            self.assertIn("file: 'utils/ImageOutputDev.cc'", spec)
            self.assertIn("line: 406", spec)
            self.assertIn("site_map: TODO_FORMTRIG_NATIVE_SITE_MAP.tsv", template)
            self.assertIn("target_cmd: TODO_FORMTRIG_MAGMA_POPPLER_PDFIMAGES_BINARY @@ /tmp/out", template)


if __name__ == "__main__":
    unittest.main()
