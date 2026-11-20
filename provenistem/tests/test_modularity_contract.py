"""Owner-ratified Provenistem modularity and neutral-product checks.

Static product checks, not certification of a real host adapter or external review.
"""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ModularityContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.policy = json.loads(
            (ROOT / "docs/PORTABILITY-AND-MODULE-CONTRACT.json").read_text(
                encoding="utf-8"
            )
        )
        cls.guide = (ROOT / "docs/PORTABILITY-AND-MODULE-CONTRACT.md").read_text(
            encoding="utf-8"
        )

    def test_owner_architecture_lock(self):
        p = self.policy
        self.assertEqual(p["schema"], "provenistem/standalone-and-optional-integration/v1")
        self.assertEqual(p["owner_decision_id"], "GB-PROVENISTEM-OPTIONAL-RELATIONSHIP-2026-11-12")
        self.assertEqual(p["owner_status"], "OWNER_RATIFIED_ARCHITECTURE")
        self.assertEqual(p["product_id"], "provenistem")
        self.assertEqual(p["architecture_state"], "LOCKED")
        self.assertEqual(p["adapter_implementation_status"], "NOT_IMPLEMENTED")
        self.assertTrue((ROOT / p["source_of_authority"]).is_file())

    def test_owner_locked_simple_ideas_features_scope(self):
        p = self.policy["product_scope"]
        self.assertEqual(p["decision_id"], "PROVENISTEM-SCOPE-2026-11-12")
        self.assertEqual(p["status"], "PRODUCT_SCOPE_LOCKED")
        self.assertEqual(p["primary_mission"], "TRACK_PROJECT_IDEAS_AND_FEATURES")
        self.assertEqual(p["tracks"], [
            "ideas", "features", "relationships", "status", "progress"])
        self.assertTrue(p["no_unapproved_scope_expansion"])
        self.assertTrue(p["later_narrow_scope_supersedes_earlier_broad_descriptions"])
        self.assertIn("general_knowledge_platform", p["excludes"])
        self.assertIn("evidence_attestation", p["excludes"])
        self.assertTrue((ROOT / p["authority"]).is_file())
        self.assertFalse(self.policy["optional_integration"]["adapter_required"])
        self.assertTrue(self.policy["optional_integration"][
            "prefer_minimal_compatible_host_integration"])
        scope = (ROOT / p["authority"]).read_text(encoding="utf-8")
        self.assertIn("Ideas & Features tracker", scope)

    def test_no_host_runtime_dependency(self):
        p = self.policy
        for key in ("standalone", "stores_project_local_ideas_and_features"):
            self.assertTrue(p["product"][key])
        for key in ("requires_host_framework", "requires_runner", "requires_network",
                    "requires_host_credentials", "runtime_imports_host_framework",
                    "can_grant_release_approval", "can_grant_work_authority",
                    "evidence_reference_is_authentication"):
            self.assertFalse(p["product"][key])
        self.assertIn("optional", self.guide.lower())

    def test_no_implicit_enablement_or_catalog_ownership_transfer(self):
        p = self.policy["optional_integration"]
        for key in ("adapter_owned_by_host", "explicit_host_opt_in",
                    "no_mandatory_runtime_dependency", "no_automatic_install",
                    "no_automatic_sync", "no_implicit_schema_conversion",
                    "no_dual_writer_canonical_records", "separate_namespace_on_conflict",
                    "read_only_preflight", "no_clobber_host_data",
                    "no_external_release_authority"):
            self.assertTrue(p[key], key)
        self.assertFalse(p["enabled_by_default"])
        self.assertIn("NAMESPACE_COLLISION", self.guide)

    def test_neutral_future_distribution(self):
        p = self.policy["neutral_distribution"]
        for key in ("ship_unrelated_project_names", "ship_historical_adopter_data",
                    "ship_private_repo_links", "ship_prior_ci_runner_names",
                    "ship_private_evidence_receipts", "ship_customer_data"):
            self.assertFalse(p[key])
        for key in ("use_synthetic_examples", "keep_internal_provenance_outside_package"):
            self.assertTrue(p[key])
        # Consumer Markdown must not contain real owner/repo GitHub links.
        for file in sorted(ROOT.rglob("*.md")):
            if ".git" in file.parts:
                continue
            with self.subTest(document=file.relative_to(ROOT)):
                text = file.read_text(encoding="utf-8")
                self.assertIsNone(
                    re.search(r"https?://github\.com/[A-Za-z0-9_-]+/[A-Za-z0-9_.-]+", text),
                    "External project-specific GitHub repository URL in neutral product doc",
                )

    def test_no_actual_adopter_records_or_authority_files_in_standalone_root(self):
        for section in ("ideas", "features"):
            self.assertFalse(list((ROOT / section / "records").glob("*.json")))
        for name in ("AGENTS.md", "GOVERNANCE-START.md", "src", "governance", ".github", "ops"):
            self.assertFalse((ROOT / name).exists(), name)

    def test_old_awareness_prohibition_is_superseded_narrowly(self):
        text = (ROOT / "docs/ONE-WAY-BOUNDARY.md").read_text(encoding="utf-8")
        self.assertIn("may know that Provenistem exists", text)
        self.assertIn("No upstream registration", text)
        self.assertIn("No upstream modification", text)
        self.assertIn("No runtime dependency", text)
        self.assertIn("No automatic synchronization", text)
        self.assertIn("NAMESPACE_COLLISION", text)
        self.assertNotIn("must remain **agnostic** to the existence", text)

    def test_v002_release_remains_historical(self):
        g = self.policy["release_guards"]
        self.assertTrue(g["v002_historical_tag_immutable"])
        self.assertTrue(g["forward_clean_candidate_required"])
        self.assertTrue(g["adapter_not_shipped_in_v002"])
        self.assertTrue(g["requires_new_owner_decision_for_architecture_change"])
        self.assertTrue(g["doc_lock_not_runtime_enforcement"])


if __name__ == "__main__":
    unittest.main()
