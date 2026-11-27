"""Small source-level controls; never execute advanced qualification bodies."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent
SUSPENDED = {
    "test_bounded_concurrent_workloads",
    "test_full_lifecycle_with_one_hundred_distinct_issue_lanes",
    "test_matched_serial_and_parallel_protocol_cost",
    "test_starvation_counterexample_with_real_production_retry",
}

class QualificationPolicyTests(unittest.TestCase):
    def test_advanced_methods_are_unconditionally_skipped(self):
        tree = ast.parse((ROOT / "tests/test_vib53_qualification.py").read_text(encoding="utf-8"))
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "QualificationTests")
        methods = {node.name: node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")}
        def suspended(method):
            return any(isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute)
                       and isinstance(d.func.value, ast.Name) and d.func.value.id == "unittest"
                       and d.func.attr == "skip" and len(d.args) == 1
                       and isinstance(d.args[0], ast.Constant)
                       and "VIB-LAW-OWNER-QUALIFICATION-001" in str(d.args[0].value)
                       for d in method.decorator_list)
        self.assertEqual({name for name, method in methods.items() if suspended(method)}, SUSPENDED)
        self.assertIn("test_real_git_legacy_upgrade_and_parallel_opt_in", methods)
        self.assertIn("test_fresh_process_claim_replay_has_no_durable_pending_identity", methods)

    def test_historical_experiment_is_not_an_active_workflow(self):
        self.assertFalse((ROOT / ".github/workflows/vib53-implementation.yml").exists())
        self.assertTrue((ROOT / "docs/qualification/vib53-implementation.yml").is_file())

    def test_law_is_discoverable(self):
        for name in ("AGENTS.md", "ENGINEERING-LAWS.md", "docs/v0.0.0.38.md"):
            self.assertIn("VIB-LAW-OWNER-QUALIFICATION-001", (ROOT / name).read_text(encoding="utf-8"))
