import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("checker", Path(__file__).resolve().parents[1] / "tools/check_readme_hq.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)

class WorkspaceNavigation(unittest.TestCase):
    def test_workspace_link_and_anchor_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("README.md", "README-GUIDE.md", "AGENTS.md", "history/README.md", "techniques/README.md", "graphify-hq/README.md", "workspace/v0.0.1/DRAFT.md"):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# Present\n", encoding="utf-8")
            draft = root / "workspace/v0.0.1/DRAFT.md"
            draft.write_text("# Present\n[missing](missing.md)\n[anchor](#absent)\n[valid](#present)\n", encoding="utf-8")
            with patch.object(checker, "ROOT", root):
                errors = []
                self.assertEqual(checker.check_navigation(errors), 3)
                self.assertEqual(len(errors), 2)
                self.assertTrue(any("missing local target" in e for e in errors))
                self.assertTrue(any("missing local heading" in e for e in errors))
                draft.write_text("# Present\n[valid](#present)\n", encoding="utf-8")
                errors = []
                checker.check_navigation(errors)
                self.assertEqual(errors, [])
