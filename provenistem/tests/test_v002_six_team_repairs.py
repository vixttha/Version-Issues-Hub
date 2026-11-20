"""Six-team source regression: bounded nesting, Schema semantics, and Governance stop.

Synthetic inputs only. No network, production adopter writes or external reviewers.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import library
import adopter


class SixTeamRepairs(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        self.host = self.base / "host"
        for section, singular in (("ideas", "idea"), ("features", "feature")):
            records = self.host / section / "records"
            records.mkdir(parents=True)
            schema = self.host / section / "schema" / "v1"
            schema.mkdir(parents=True)
            original = ROOT / section / "schema" / "v1" / (singular + ".schema.json")
            (schema / original.name).write_bytes(original.read_bytes())
            (self.host / section / "INDEX.md").write_text(
                library.index(section, {}), encoding="utf-8")

    def test_red_large_depth_below_size_cap_is_normal_failure(self):
        path = self.host / "ideas/records/IDEA-000001.json"
        nested = "[" * 1100 + "0" + "]" * 1100
        self.assertLess(len(nested), library.MAX_RECORD_BYTES)
        path.write_text(nested, encoding="utf-8")
        issues, ideas, features = library.validate(self.host)
        self.assertTrue(issues)
        self.assertEqual((ideas, features), ({}, {}))
        self.assertTrue(
            any("bad JSON" in issue or "JSON nesting exceeds" in issue
                for issue in issues), issues)

    def test_red_parseable_nested_record_rejected_at_depth_limit(self):
        path = self.host / "ideas/records/IDEA-000001.json"
        nested = "[" * (library.MAX_JSON_DEPTH + 5) + "0" + "]" * (library.MAX_JSON_DEPTH + 5)
        path.write_text(nested, encoding="utf-8")
        issues, _, _ = library.validate(self.host)
        self.assertIn("JSON nesting exceeds", " ".join(issues))

    def test_red_deep_schema_fails_without_recursion(self):
        path = self.host / "ideas/schema/v1/idea.schema.json"
        row = json.loads(path.read_text(encoding="utf-8"))
        child = {"type": "string"}
        for i in range(library.MAX_JSON_DEPTH + 10):
            child = {"type": "array", "items": child}
        row["properties"]["title"] = child
        path.write_text(json.dumps(row), encoding="utf-8")
        issues, _, _ = library.validate(self.host)
        self.assertIn("schema nesting exceeds", " ".join(issues))

    def test_blue_unanchored_pattern_search_and_explicit_anchors(self):
        self.assertEqual(library.shape("copycat", {"type": "string", "pattern": "cat"}, "field"), [])
        self.assertIn("invalid format", " ".join(
            library.shape("copycat", {"type": "string", "pattern": "^cat$"}, "field")))
        self.assertEqual(library.shape("cat", {"type": "string", "pattern": "^cat$"}, "field"), [])

    def test_blue_uniqueitems_object_key_order_and_numeric_equality(self):
        spec = {"type": "array", "uniqueItems": True}
        a = {"a": 1, "b": {"nested": ["x", {"n": 2}]}}
        b = {"b": {"nested": ["x", {"n": 2}]}, "a": 1}
        self.assertIn("duplicate entries", " ".join(library.shape([a, b], spec, "item")))
        self.assertIn("duplicate entries", " ".join(library.shape([1, 1.0], spec, "item")))
        self.assertEqual(library.shape([True, 1], spec, "item"), [])
        self.assertEqual(library.shape([{"k": 1}, {"k": 2}], spec, "item"), [])

    def test_purple_governance_yaml_namespace_collision(self):
        (self.host / "ideas/library.yaml").write_text("kind: governance-catalog\n", encoding="utf-8")
        result = adopter.plan(ROOT, self.host)
        self.assertEqual(result["status"], "NAMESPACE_COLLISION")
        self.assertFalse(result["writes"])
        self.assertEqual(result["entries"], [])
        self.assertIn("ideas/library.yaml", result["markers"])

    def test_purple_governance_schema_uid_collision(self):
        schema = self.host / "ideas/schema/v1/idea.schema.json"
        content = json.loads(schema.read_text(encoding="utf-8"))
        content["properties"]["uid"] = {"type": "string"}
        content["required"].append("uid")
        schema.write_text(json.dumps(content), encoding="utf-8")
        result = adopter.plan(ROOT, self.host)
        self.assertEqual(result["status"], "NAMESPACE_COLLISION")
        self.assertEqual(result["entries"], [])

    def test_purple_existing_governance_runtime_collision(self):
        (self.host / "src/governance_branch/libraries").mkdir(parents=True)
        (self.host / "src/governance_branch/libraries/ideas.py").write_text(
            "# Synthetic collision marker\n", encoding="utf-8")
        result = adopter.plan(ROOT, self.host)
        self.assertEqual(result["status"], "NAMESPACE_COLLISION")
        self.assertEqual(result["entries"], [])

    def test_purple_no_false_collision_from_adopter_agents_doc(self):
        (self.host / "AGENTS.md").write_text(
            "Host mentions Governance-Branch as separate, unrelated software.\n",
            encoding="utf-8")
        result = adopter.plan(ROOT, self.host)
        self.assertNotEqual(result["status"], "NAMESPACE_COLLISION")
        self.assertFalse(result["writes"])

    def test_purple_isolated_child_under_governed_parent_allowed(self):
        parent = self.base / "governed-project"
        (parent / "ideas").mkdir(parents=True)
        (parent / "ideas/library.yaml").write_text("kind: governance\n", encoding="utf-8")
        child = parent / "isolated-optional-library"
        result = adopter.plan(ROOT, child)
        self.assertEqual(result["status"], "NEW_DESTINATION")
        self.assertFalse(child.exists())
        self.assertFalse(result["writes"])


if __name__ == "__main__":
    unittest.main()
