import json
import tempfile
import unittest
from pathlib import Path

from tools.audit_real_cve_readiness import (
    harness_admissibility_blocker,
    harness_admissibility_records,
    harness_rejects_core_evidence,
)


class RealCveReadinessAuditTest(unittest.TestCase):
    def test_harness_admissibility_rejects_core_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "raw" / "libxml2_1107_harness_admissibility.json"
            path.parent.mkdir()
            path.write_text(
                json.dumps(
                    {
                        "schema": "formtrig_harness_admissibility_v1",
                        "target_id": "LIBXML2_1107",
                        "status": "inadmissible_core_evidence",
                        "core_evidence_allowed": False,
                        "summary": "harness exposes an artificial trigger-control knob",
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            records = harness_admissibility_records("LIBXML2_1107", root=root)

        self.assertEqual(len(records), 1)
        self.assertTrue(harness_rejects_core_evidence(records))
        blocker = harness_admissibility_blocker(records)
        self.assertIn("inadmissible_core_evidence", blocker)
        self.assertIn("artificial trigger-control knob", blocker)


if __name__ == "__main__":
    unittest.main()
