"""Offline standard-library regression tests for the optional template."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import library


def example(kind):
    return json.loads((ROOT / "templates" / f"{kind}.example.json").read_text(encoding="utf-8"))


class LibraryTemplateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for kind in ("ideas", "features"):
            (self.root / kind / "records").mkdir(parents=True)
            schema = (self.root / kind / "schema" / "v1")
            schema.mkdir(parents=True)
            src = ROOT / kind / "schema" / "v1" / f"{'idea' if kind == 'ideas' else 'feature'}.schema.json"
            (schema / src.name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            (self.root / kind / "INDEX.md").write_text(library.index(kind, {}), encoding="utf-8")

    def write(self, kind, row):
        (self.root / kind / "records" / (row["id"] + ".json")).write_text(
            json.dumps(row, indent=2) + "\n", encoding="utf-8")

    def test_current_library_is_valid_even_when_populated(self):
        self.assertEqual(library.run(ROOT, "check"), 0)

    def test_examples_pass_schema(self):
        self.assertFalse(library.shape(example("idea"), json.loads(
            (ROOT / "ideas/schema/v1/idea.schema.json").read_text()), "idea"))
        self.assertFalse(library.shape(example("feature"), json.loads(
            (ROOT / "features/schema/v1/feature.schema.json").read_text()), "feature"))

    def test_round_trip_indexes(self):
        idea = example("idea")
        feature = example("feature")
        feature["idea_ids"] = [idea["id"]]
        self.write("ideas", idea)
        self.write("features", feature)
        self.assertEqual(library.run(self.root, "build"), 0)
        self.assertEqual(library.run(self.root, "check"), 0)
        self.assertIn(idea["title"], (self.root / "ideas/INDEX.md").read_text())

    def test_stale_index_is_rejected(self):
        self.write("ideas", example("idea"))
        self.assertEqual(library.run(self.root, "check"), 1)

    def test_missing_idea_link_is_rejected(self):
        feature = example("feature")
        feature["idea_ids"] = ["IDEA-000999"]
        self.write("features", feature)
        self.assertIn("unresolved idea", " ".join(library.validate(self.root)[0]))

    def test_decision_needed_for_adoption(self):
        idea = example("idea")
        idea["lifecycle_status"] = "adopted"
        self.write("ideas", idea)
        self.assertIn("without recorded decision", " ".join(library.validate(self.root)[0]))

    def test_false_verified_feature_rejected(self):
        feat = example("feature")
        feat["lifecycle_status"] = "verified"
        self.write("features", feat)
        self.assertIn("unsupported verified", " ".join(library.validate(self.root)[0]))

    def test_unsafe_evidence_path_rejected(self):
        feat = example("feature")
        feat["evidence"] = [{"kind":"test", "claim":"test", "source_sha":"a"*40,
                             "source_path":"../outside", "receipt":"claimed"}]
        self.write("features", feat)
        self.assertIn("unsafe evidence path", " ".join(library.validate(self.root)[0]))

    def test_unknown_root_field_rejected(self):
        idea = example("idea")
        idea["automatic_release"] = True
        self.write("ideas", idea)
        self.assertIn("unknown field automatic_release", " ".join(library.validate(self.root)[0]))

    def test_wrong_filename_rejected(self):
        p = self.root / "ideas/records/IDEA-999999.json"
        p.write_text(json.dumps(example("idea")), encoding="utf-8")
        self.assertIn("mismatched ID", " ".join(library.validate(self.root)[0]))

    def test_generic_examples_have_no_source_product_records(self):
        for kind in ("idea", "feature"):
            self.assertNotIn("PRIVATE-HOST-RECORD-DO-NOT-SHIP", json.dumps(example(kind)))
        self.assertNotIn("Governance-Branch", json.dumps(example("idea")))


if __name__ == "__main__":
    unittest.main()
