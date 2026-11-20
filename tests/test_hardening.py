"""Portable v0.0.2 offline negative tests. No release or external trust claims."""
import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import library


class HardeningTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "host"
        for kind, singular in (("ideas", "idea"), ("features", "feature")):
            (self.root / kind / "records").mkdir(parents=True)
            schema = self.root / kind / "schema" / "v1"
            schema.mkdir(parents=True)
            src = ROOT / kind / "schema" / "v1" / (singular + ".schema.json")
            (schema / src.name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            (self.root / kind / "INDEX.md").write_text(
                library.index(kind, {}), encoding="utf-8")

    def example(self, kind):
        return json.loads((ROOT / "templates" / (kind + ".example.json")).read_text(encoding="utf-8"))

    def write(self, kind, row):
        (self.root / kind / "records" / (row["id"] + ".json")).write_text(
            json.dumps(row, indent=2) + "\n", encoding="utf-8")

    def test_baseline_still_valid(self):
        self.assertEqual(library.run(ROOT, "check"), 0)

    def test_roundtrip(self):
        self.write("ideas", self.example("idea"))
        feature = self.example("feature")
        feature["idea_ids"] = ["IDEA-000001"]
        self.write("features", feature)
        self.assertEqual(library.run(self.root, "build"), 0)
        self.assertEqual(library.run(self.root, "check"), 0)

    def test_bad_idea_types_fail_without_exception(self):
        for field, bad in (
            ("lifecycle_status", ["adopted"]),
            ("testing", ["tested"]),
            ("related_ideas", 42),
            ("evidence", ["not-an-object"]),
        ):
            with self.subTest(field=field):
                row = self.example("idea")
                row[field] = bad
                self.write("ideas", row)
                errors, _, _ = library.validate(self.root)
                self.assertTrue(any("expected " in e for e in errors), errors)

    def test_bad_feature_types_fail_without_exception(self):
        for field, bad in (
            ("idea_ids", 42),
            ("testing", ["tested"]),
            ("evidence", ["not-an-object"]),
        ):
            with self.subTest(field=field):
                row = self.example("feature")
                row[field] = bad
                self.write("features", row)
                errors, _, _ = library.validate(self.root)
                self.assertTrue(any("expected " in e for e in errors), errors)

    def test_premature_outcome_rejected(self):
        for kind in ("idea", "feature"):
            with self.subTest(kind=kind):
                row = self.example(kind)
                row["testing"] = {"status": "planned", "outcome": "pass", "refs": ["claim"]}
                self.write(kind + "s", row)
                errors, _, _ = library.validate(self.root)
                self.assertIn("premature testing outcome", " ".join(errors))

    def test_unsupported_schema_keywords_rejected(self):
        for kind, singular, keyword, value in (
            ("ideas", "idea", "$ref", "https://untrusted.invalid/schema.json"),
            ("features", "feature", "oneOf", [{"minLength": 4}]),
        ):
            with self.subTest(keyword=keyword):
                p = self.root / kind / "schema" / "v1" / (singular + ".schema.json")
                spec = json.loads(p.read_text(encoding="utf-8"))
                if kind == "ideas":
                    spec[keyword] = value
                else:
                    spec["properties"]["title"][keyword] = value
                p.write_text(json.dumps(spec), encoding="utf-8")
                errors, _, _ = library.validate(self.root)
                self.assertIn("unsupported schema keyword " + keyword, " ".join(errors))

    def test_evidence_paths_reject_windows_drives_controls_and_traversal(self):
        for value in ("C:secret", "C:/secret", "foo:bar", "../outside",
                      "a//b", "a\\b", "x\nname", "x?name", "/etc/passwd"):
            with self.subTest(value=value):
                self.assertFalse(library.safe_repo_path(value))
        self.assertTrue(library.safe_repo_path("src/examples/Example File.md"))

    def _link_or_skip(self, path, target):
        try:
            path.symlink_to(target)
        except (OSError, NotImplementedError) as exc:
            self.skipTest("symlinks unavailable here: " + str(exc))

    def test_build_rejects_symlinked_index_without_overwriting_target(self):
        target = Path(self.temp.name) / "external-index.md"
        target.write_text("UNCHANGED", encoding="utf-8")
        p = self.root / "ideas/INDEX.md"
        p.unlink()
        self._link_or_skip(p, target)
        self.assertEqual(library.run(self.root, "build"), 1)
        self.assertEqual(target.read_text(encoding="utf-8"), "UNCHANGED")

    def test_rejects_symlink_record(self):
        target = Path(self.temp.name) / "external-record.json"
        target.write_text(json.dumps(self.example("idea")), encoding="utf-8")
        self._link_or_skip(self.root / "ideas/records/IDEA-000001.json", target)
        errors, _, _ = library.validate(self.root)
        self.assertIn("symlink record entry forbidden", " ".join(errors))

    def test_rejects_schema_symlink_before_open(self):
        target = Path(self.temp.name) / "external-schema.json"
        target.write_text("not a JSON schema", encoding="utf-8")
        p = self.root / "ideas/schema/v1/idea.schema.json"
        p.unlink()
        self._link_or_skip(p, target)
        errors, _, _ = library.validate(self.root)
        self.assertIn("symlink component forbidden", " ".join(errors))

    def test_oversized_record_rejected(self):
        row = self.example("idea")
        row["summary"] = "X" * (library.MAX_RECORD_BYTES + 1)
        self.write("ideas", row)
        errors, _, _ = library.validate(self.root)
        self.assertIn("oversize record", " ".join(errors))

    def test_nonfinite_json_constant_rejected(self):
        path = self.root / "ideas/records/IDEA-000001.json"
        path.write_text('{"id":"IDEA-000001","title":NaN}', encoding="utf-8")
        errors, _, _ = library.validate(self.root)
        self.assertIn("bad JSON", " ".join(errors))

    def test_schema_maxlength_bad_contract_is_rejected(self):
        p = self.root / "features/schema/v1/feature.schema.json"
        spec = json.loads(p.read_text(encoding="utf-8"))
        spec["properties"]["title"]["minLength"] = 10
        spec["properties"]["title"]["maxLength"] = 2
        p.write_text(json.dumps(spec), encoding="utf-8")
        errors, _, _ = library.validate(self.root)
        self.assertIn("maxLength below minLength", " ".join(errors))

    def test_markdown_title_is_escaped_as_data(self):
        tick = chr(96)
        raw = "[Click](https://example.invalid) *bold* " + tick + "code" + tick
        rendered = library.index("ideas", {
            "IDEA-000001": {"title": raw, "lifecycle_status": "captured",
                            "implementation_status": "not_planned"}
        })
        self.assertNotIn(raw, rendered)
        self.assertIn(r"\[Click\]\(https://example.invalid\)", rendered)
        self.assertIn(r"\*bold\*", rendered)
        self.assertIn("\\" + tick + "code" + "\\" + tick, rendered)


if __name__ == "__main__":
    unittest.main()
