"""Synthetic cross-adopter compatibility fixtures; no private records copied."""
import json
import re
import shutil
import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import library
import adopter


class AdopterProfiles(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.host = self.root / "host"
        for section, singular in (("ideas", "idea"), ("features", "feature")):
            (self.host / section / "records").mkdir(parents=True)
            dst = self.host / section / "schema/v1"
            dst.mkdir(parents=True)
            original = ROOT / section / "schema/v1" / (singular + ".schema.json")
            (dst / original.name).write_bytes(original.read_bytes())
            (self.host / section / "INDEX.md").write_text(
                library.index(section, {}), encoding="utf-8")

    def example(self, kind):
        return json.loads((ROOT / "templates" / (kind + ".example.json")).read_text(encoding="utf-8"))

    def put(self, section, row):
        path = self.host / section / "records" / (row["id"] + ".json")
        path.write_text(json.dumps(row, indent=2), encoding="utf-8")

    def test_synthetic_host_schema_extension_and_maxlength(self):
        schema_path = self.host / "features/schema/v1/feature.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        schema["properties"]["limitations"] = {
            "type": "array", "items": {"type": "string", "minLength": 1}
        }
        schema["properties"]["project_milestone"] = {
            "type": "string", "minLength": 1, "maxLength": 80
        }
        schema_path.write_text(json.dumps(schema), encoding="utf-8")
        feature = self.example("feature")
        feature["limitations"] = ["No automatically synchronized external service"]
        feature["project_milestone"] = "Synthetic host milestone"
        self.put("features", feature)
        self.assertEqual(library.run(self.host, "build"), 0)
        self.assertEqual(library.run(self.host, "check"), 0)
        feature["project_milestone"] = "x" * 81
        self.put("features", feature)
        self.assertIn("text too long", " ".join(library.validate(self.host)[0]))

    def test_synthetic_populated_host_not_bound_to_default_counts(self):
        # Representative synthetic records: no actual adopter data or source repository.
        for i in range(1, 21):
            row = self.example("idea")
            row["id"] = f"IDEA-{i:06d}"
            row["title"] = f"Synthetic idea {i}"
            self.put("ideas", row)
        for i in range(1, 28):
            row = self.example("feature")
            row["id"] = f"FEAT-{i:06d}"
            row["title"] = f"Synthetic feature {i}"
            if i <= 12:
                row["implementation_status"] = "implemented"
                row["lifecycle_status"] = "implemented"
                row["evidence"] = [{
                    "kind": "implementation", "claim": "Synthetic code reference only",
                    "source_sha": "a" * 40, "source_path": "src/example.py",
                    "receipt": "Synthetic fixture, not evidence of implementation",
                }]
            elif i <= 14:
                row["implementation_status"] = "in_progress"
                row["lifecycle_status"] = "in_progress"
            if i % 2:
                row["idea_ids"] = [f"IDEA-{((i-1) % 20)+1:06d}"]
            self.put("features", row)
        self.assertEqual(library.run(self.host, "build"), 0)
        self.assertEqual(library.run(self.host, "check"), 0)
        problems, ideas, features = library.validate(self.host)
        self.assertEqual(problems, [])
        self.assertEqual((len(ideas), len(features)), (20, 27))

    def test_no_clobber_plan_on_existing_host(self):
        self.put("ideas", self.example("idea"))
        self.put("features", self.example("feature"))
        (self.host / "docs").mkdir()
        local = self.host / "docs/ADOPTION.md"
        local.write_text("HOST-OWNED", encoding="utf-8")
        before = local.read_bytes()
        record_before = (self.host / "ideas/records/IDEA-000001.json").read_bytes()
        result = adopter.plan(ROOT, self.host)
        actions = {r["path"]: r["action"] for r in result["entries"]}
        self.assertEqual(actions["docs/ADOPTION.md"], "REVIEW_LOCAL_DIFFERENCE")
        self.assertEqual(actions["ideas/records/.gitkeep"], "ADD")
        self.assertEqual(result["writes"], False)
        self.assertEqual(local.read_bytes(), before)
        self.assertEqual((self.host / "ideas/records/IDEA-000001.json").read_bytes(), record_before)

    def test_planner_includes_all_portable_regression_suites(self):
        expected = {
            "test_library.py",
            "test_one_way_boundary.py",
            "test_hardening.py",
            "test_adopter_profiles.py",
            "test_v002_six_team_repairs.py",
            "test_modularity_contract.py", "test_unicode_index_integrity.py",
        }
        listed = {
            p.name for p in adopter.candidates(ROOT)
            if p.parts[0] == "tests"
        }
        self.assertEqual(listed, expected)
        clean = self.root / "fresh-adopter"
        plan = adopter.plan(ROOT, clean)
        self.assertEqual(plan["status"], "NEW_DESTINATION")
        self.assertFalse(plan["writes"])
        self.assertIn(
            {"path": "tests/test_v002_six_team_repairs.py", "action": "ADD"},
            plan["entries"],
        )
        self.assertFalse(clean.exists())

    def test_documented_basic_copy_has_all_relative_links(self):
        for document in ("README.md", "docs/ADOPTION.md"):
            with self.subTest(document=document):
                text = (ROOT / document).read_text(encoding="utf-8")
                line = next(line for line in text.splitlines()
                            if "Copy " in line and "\x60ideas/\x60" in line)
                # The first sentence defines the basic copy inventory.
                inventory = re.findall(r"\x60([A-Za-z0-9_./-]+)\x60",
                                       line.split("Copy ", 1)[1].split(". ", 1)[0])
                dest = self.root / ("manual-" + Path(document).stem)
                dest.mkdir()
                for item in inventory:
                    src = ROOT / item
                    if src.is_dir():
                        shutil.copytree(src, dest / item)
                    else:
                        shutil.copy2(src, dest / item)
                for required in ("README.md", "LICENSE", "docs/LIFECYCLE.md",
                                 "docs/ISOLATION.md", "templates/idea.example.json",
                                 "templates/feature.example.json"):
                    self.assertTrue((dest / required).is_file(), required)
                self.assertEqual((dest / "LICENSE").read_bytes(),
                                 (ROOT / "LICENSE").read_bytes())
                for md in dest.rglob("*.md"):
                    for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)",
                                           md.read_text(encoding="utf-8")):
                        if "://" in link or link.startswith("#"):
                            continue
                        target = (md.parent / link.split("#", 1)[0]).resolve()
                        self.assertTrue(target.is_relative_to(dest.resolve()))
                        self.assertTrue(target.is_file(), f"{md.name}: {link}")
                self.assertFalse((dest / "tools").exists())
                self.assertFalse((dest / "tests").exists())

    def test_planned_copy_contains_complete_portable_package(self):
        dest = self.root / "planned-copy"
        plan = adopter.plan(ROOT, dest)
        self.assertEqual(plan["status"], "NEW_DESTINATION")
        self.assertFalse(plan["writes"])
        self.assertFalse(dest.exists())
        expected = {"README.md", "LICENSE", "LIBRARY-AGENT-GUIDE.md"}
        for folder in ("ideas", "features", "templates", "docs", "tools", "tests"):
            expected.update(p.relative_to(ROOT).as_posix() for p in (ROOT / folder).rglob("*")
                            if p.is_file() and "__pycache__" not in p.parts
                            and p.suffix != ".pyc")
        actual = {entry["path"] for entry in plan["entries"]}
        self.assertEqual(actual, expected)
        for entry in plan["entries"]:
            self.assertEqual(entry["action"], "ADD")
            target = dest / entry["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / entry["path"], target)
        self.assertEqual((dest / "LICENSE").read_bytes(), (ROOT / "LICENSE").read_bytes())
        self.assertEqual(library.run(dest, "check"), 0)
        for md in dest.rglob("*.md"):
            for link in re.findall(r"\[[^\]]+\]\(([^)]+)\)",
                                   md.read_text(encoding="utf-8")):
                if "://" not in link and not link.startswith("#"):
                    self.assertTrue((md.parent / link.split("#", 1)[0]).is_file(),
                                    f"{md.name}: {link}")

    def test_non_directory_parent_blocks_plan(self):
        dest = self.root / "blocked"
        dest.mkdir()
        (dest / "ideas").write_text("HOST", encoding="utf-8")
        result = adopter.plan(ROOT, dest)
        self.assertEqual(result["status"], "EXISTING_DESTINATION")
        actions = {x["path"]: x["action"] for x in result["entries"]}
        self.assertEqual(actions["ideas/schema/v1/idea.schema.json"], "CONFLICT_PARENT")
        self.assertEqual(actions["features/schema/v1/feature.schema.json"], "ADD")
        self.assertEqual(adopter.main([str(dest)]), 1)
        self.assertEqual((dest / "ideas").read_text(), "HOST")

    def test_clean_host_plan_never_writes(self):
        dest = self.root / "brand-new-root"
        result = adopter.plan(ROOT, dest)
        self.assertEqual(result["status"], "NEW_DESTINATION")
        self.assertFalse(result["writes"])
        self.assertFalse(dest.exists())
        self.assertTrue(any(x["path"] == "tools/library.py" for x in result["entries"]))

    def test_existing_symlink_cannot_be_planned_over(self):
        replacement = self.root / "external"
        replacement.mkdir()
        target = self.host / "templates"
        try:
            target.symlink_to(replacement, target_is_directory=True)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(str(exc))
        with self.assertRaises(ValueError):
            adopter.plan(ROOT, self.host)

    def test_indexes_have_exact_lf_bytes_after_build(self):
        row = self.example("idea")
        row["title"] = "Synthetic \u00e9vidence example"
        self.put("ideas", row)
        self.assertEqual(library.run(self.host, "build"), 0)
        for section in ("ideas", "features"):
            raw = (self.host / section / "INDEX.md").read_bytes()
            self.assertTrue(raw.endswith(b"\n"))
            self.assertNotIn(b"\r", raw, "Index must use LF, not platform CRLF")

    def test_schema_unsupported_keyword_is_still_rejected(self):
        schema_path = self.host / "features/schema/v1/feature.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        schema["properties"]["title"]["if"] = {"minLength": 10}
        schema_path.write_text(json.dumps(schema), encoding="utf-8")
        self.assertIn("unsupported schema keyword if", " ".join(library.validate(self.host)[0]))

    def test_empty_host_fixture_is_supported(self):
        problems, ideas, features = library.validate(self.host)
        self.assertEqual(problems, [])
        self.assertEqual(len(ideas) + len(features), 0)
        self.assertEqual(library.run(self.host, "check"), 0)


if __name__ == "__main__":
    unittest.main()
