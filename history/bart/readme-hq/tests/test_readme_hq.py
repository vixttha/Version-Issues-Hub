"""Negative regression checks for the README HQ validator."""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from check_readme_hq import REQUIRED, validate  # noqa: E402


class ReadmeHQTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for rel in REQUIRED:
            target = self.root / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, target)
        shutil.copytree(ROOT / "versions", self.root / "versions", dirs_exist_ok=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_clean_baseline(self):
        self.assertEqual([], validate(self.root))

    def test_archive_drift_rejected(self):
        (self.root / "readme-hq/versions/v0.0.1/README.md").write_text("# Wrong\n", encoding="utf-8")
        self.assertTrue(any("drift" in x for x in validate(self.root)))

    def test_missing_draft_rejected(self):
        (self.root / "workspace/v0.0.1/DRAFT.md").unlink()
        self.assertTrue(any("missing required" in x for x in validate(self.root)))

    def test_broken_branch_link_rejected(self):
        p = self.root / "graphify/README.md"
        p.write_text(p.read_text() + "\n[Missing](../no-such-file.md)\n")
        self.assertTrue(any("broken local link" in x for x in validate(self.root)))

    def test_secret_rejected(self):
        p = self.root / "graphify/README.md"
        p.write_text(p.read_text() + "\napi_key=abcdefghijklmnop\n")
        self.assertTrue(any("credential-like" in x for x in validate(self.root)))


if __name__ == "__main__":
    unittest.main()
