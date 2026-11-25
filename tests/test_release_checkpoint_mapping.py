"""Protect retroactive review-only checkpoints and preserve release coordination slot."""
import json
import unittest
from pathlib import Path
from tools import checkpoint

ROOT = Path(__file__).resolve().parent.parent

class ReleaseCheckpointMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = checkpoint.parse_json((ROOT / "ledger/issue-versions.json").read_text())
        cls.scope = checkpoint.parse_json((ROOT / "ledger/receipt-scope.json").read_text())
        cls.graph = checkpoint.parse_json((ROOT / "docs/receipt-evidence.json").read_text())

    def test_issue_versions_unique_and_reserved_release_slot(self):
        versions = checkpoint.bindings(self.ledger)
        self.assertEqual(versions[39], "v0.0.0.24")
        self.assertEqual(versions[51], "v0.0.0.25")
        self.assertNotIn("v0.0.0.23", versions.values())
        self.assertNotIn(40, versions)
        self.assertEqual(len(versions), 24)

    def test_two_new_fix_pins_and_receipt_scope(self):
        checkpoint.check_receipt_scope(self.ledger, self.scope)
        self.assertEqual(self.scope["fixes"]["v0.0.0.24"], "114a22196eab578b3053002f8eb7af935b26fe89")
        self.assertEqual(self.scope["fixes"]["v0.0.0.25"], "d7a1efef88704be952f3ecefde1c018b1155fe9a")
        self.assertEqual(len(self.scope["versions"]), 24)
        self.assertEqual(len(set(self.scope["versions"])), 24)

    def test_graph_has_exact_24_independent_mappings(self):
        ids = [f["id"] for f in self.graph["features"]]
        self.assertEqual(len(ids), 24)
        self.assertEqual(len(set(ids)), 24)
        self.assertIn("v0-0-0-24", ids)
        self.assertIn("v0-0-0-25", ids)

if __name__ == "__main__":
    unittest.main()
