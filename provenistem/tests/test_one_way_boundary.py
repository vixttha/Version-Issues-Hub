"""One-way, optional side-template non-interference regressions.

No third-party packages or GitHub runner needed. Static guards are not a proof
against every future edit; source/branch permissions still govern writes.
"""
import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
ALLOWED = {
    "argparse", "json", "re", "decimal", "pathlib", "copy", "sys", "tempfile",
    "unittest", "shutil", "check_idea_feature_library", "library"
}
FORBIDDEN_ROOT = (
    "AGENTS.md", "GOVERNANCE-START.md", "governance", "src", "skills",
    "policy_v002", "plugin.json", ".codex-plugin",
    "requirements.txt", "pyproject.toml"
)


class OneWayBoundaryTests(unittest.TestCase):
    def test_template_schemas_do_not_depend_on_host_permissions(self):
        self.assertTrue((ROOT / "ideas/schema/v1/idea.schema.json").is_file())
        self.assertTrue((ROOT / "features/schema/v1/feature.schema.json").is_file())

    def test_no_upstream_imports_or_remote_write_helpers(self):
        for tool in (TOOLS / "library.py", TOOLS / "adopter.py"):
            if not tool.is_file():
                continue  # Legacy adopters may not have the optional planner.
            source = tool.read_text(encoding="utf-8")
            tree = ast.parse(source, filename=str(tool))
            with self.subTest(script=tool.name):
                # A source-side literal collision marker is allowed. Imports and
                # executable connections to upstream Governance are NOT allowed.
                self.assertNotIn("import governance_branch", source.lower())
                self.assertNotIn("from governance_branch", source.lower())
                self.assertNotIn("governance/catalog", source.lower())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            self.assertIn(alias.name.split(".")[0], ALLOWED, alias.name)
                    elif isinstance(node, ast.ImportFrom):
                        self.assertIn((node.module or "").split(".")[0], ALLOWED)
                    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                        self.assertNotIn(node.func.id, {"eval", "exec", "__import__"})

    def test_records_are_host_local_and_not_upstream_runtime(self):
        for kind in ("ideas", "features"):
            with self.subTest(kind=kind):
                folder = ROOT / kind / "records"
                self.assertTrue(folder.is_dir())
                self.assertFalse(folder.is_symlink())
        # Host-owned Governance files are not side-template runtime dependencies.

    def test_one_way_rule_is_explicit(self):
        text = (ROOT / "docs" / "ONE-WAY-BOUNDARY.md").read_text(encoding="utf-8")
        for rule in ("No upstream registration", "No upstream modification",
                     "No runtime dependency", "NAMESPACE_COLLISION",
                     "No automatic synchronization"):
            self.assertIn(rule, text)


if __name__ == "__main__":
    unittest.main()
