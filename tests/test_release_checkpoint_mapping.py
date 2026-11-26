"""Preserve historical mappings and evidence without freezing ledger growth."""
import unittest
from pathlib import Path
from tools import checkpoint

ROOT = Path(__file__).resolve().parent.parent


class ReleaseCheckpointMappingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ledger = checkpoint.parse_json((ROOT / "ledger/issue-versions.json").read_text(encoding="utf-8"))
        cls.scope = checkpoint.parse_json((ROOT / "ledger/receipt-scope.json").read_text(encoding="utf-8"))
        cls.graph = checkpoint.parse_json((ROOT / "docs/receipt-evidence.json").read_text(encoding="utf-8"))

    def test_issue_versions_unique_and_reserved_release_slot(self):
        versions = checkpoint.bindings(self.ledger)
        expected = {40: 23, 39: 24, 51: 25, 56: 26, 57: 27, 54: 28,
                    61: 29, 60: 30, 65: 31}
        for issue, suffix in expected.items():
            self.assertEqual(versions[issue], f"v0.0.0.{suffix}")
        self.assertEqual(len(versions), len(set(versions.values())))

    def test_historical_fix_pins_and_receipt_scope(self):
        checkpoint.check_receipt_scope(self.ledger, self.scope)
        expected = {
            "v0.0.0.24": "114a22196eab578b3053002f8eb7af935b26fe89",
            "v0.0.0.25": "d7a1efef88704be952f3ecefde1c018b1155fe9a",
            "v0.0.0.26": "82cfa7272ad83b044e7d4e9760133dc8a443f102",
            "v0.0.0.27": "82cfa7272ad83b044e7d4e9760133dc8a443f102",
            "v0.0.0.28": "82cfa7272ad83b044e7d4e9760133dc8a443f102",
            "v0.0.0.29": "6e428f222c7aa7a35a8d398bde2846ac0e3b9657",
            "v0.0.0.30": "a0039470d6742474232c050856a4be857f2360ac",
            "v0.0.0.31": "6e321de7cc488d548d56ed2bece08673a9a7f8b1",
        }
        for version, fix in expected.items():
            self.assertEqual(self.scope["fixes"][version], fix)
        # An allocated version without a fix receipt is not an integrated version.
        if "v0.0.0.23" not in self.scope["fixes"]:
            row = next(row for row in self.ledger["issues"] if row["issue"] == 40)
            self.assertIn(row["state"], ("assigned", "in_progress", "blocked", "deferred"))

    def test_graph_covers_all_pinned_checkpoint_versions_without_duplicates(self):
        ids = [f["id"] for f in self.graph["features"]]
        expected = {v.replace(".", "-") for v in self.scope["fixes"]}
        self.assertEqual(len(ids), len(set(ids)))
        # Explicit supplementary relationship nodes, not additional checkpoints.
        # Keep the allowlist exact: unknown, duplicate, or missing nodes still fail.
        if "v0-0-0-37" in expected:
            expected.update({"v0-0-0-37-review-recovery", "v0-0-0-37-api-boundaries"})
        if "v0-0-0-40" in expected:
            expected.update({"v0-0-0-40-execution", "v0-0-0-40-installed-compatibility"})
        if "v0-0-0-43" in expected:
            expected.add("v0-0-0-43-review")
        self.assertEqual(set(ids), expected)


if __name__ == "__main__":
    unittest.main()
