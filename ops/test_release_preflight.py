"""Deterministic regressions for PR49 review; no network or writes."""
import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch

class RevisionGuardTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location(
            "release_preflight", Path(__file__).with_name("release-preflight.py"))
        self.p = importlib.util.module_from_spec(spec)
        with patch.dict(os.environ, {"GITHUB_SHA": "test", "GITHUB_RUN_ID": "1",
                                     "GITHUB_RUN_ATTEMPT": "1", "RUNNER_TEMP": "."}):
            spec.loader.exec_module(self.p)
        self.good = {"product_sha": self.p.M["main"], "installed_sha": self.p.M["installed_state"]}

    def test_matching_inspections(self):
        self.p.check_inspected_revisions(self.good, self.good)
        self.assertEqual(len(self.p.report["checks"]), 2)
        self.assertTrue(all(x["pass"] for x in self.p.report["checks"]))

    def test_active_and_competing_product_drift(self):
        for active, other in ((dict(self.good, product_sha="changed"), self.good),
                              (self.good, dict(self.good, product_sha="changed"))):
            with self.subTest(active=active, other=other):
                with self.assertRaisesRegex(ValueError, "product revision"):
                    self.p.check_inspected_revisions(active, other)
        self.assertEqual(self.p.report["mechanical"], "failed")

    def test_active_and_competing_install_drift(self):
        for active, other in ((dict(self.good, installed_sha="changed"), self.good),
                              (self.good, dict(self.good, installed_sha="changed"))):
            with self.subTest(active=active, other=other):
                with self.assertRaisesRegex(ValueError, "installed revision"):
                    self.p.check_inspected_revisions(active, other)

    def test_final_matching_refs(self):
        with patch.object(self.p, "branch", side_effect=[self.good["product_sha"], self.good["installed_sha"]]):
            self.p.check_final_refs()

    def test_final_main_drift(self):
        with patch.object(self.p, "branch", return_value="changed"):
            with self.assertRaisesRegex(ValueError, "main still frozen"):
                self.p.check_final_refs()

    def test_final_install_drift(self):
        with patch.object(self.p, "branch", side_effect=[self.good["product_sha"], "changed"]):
            with self.assertRaisesRegex(ValueError, "installed state still frozen"):
                self.p.check_final_refs()

    def test_per_run_attempt_pins(self):
        seen = []
        def fake_api(path):
            seen.append(path)
            if "/jobs?" in path:
                return {"total_count": 1, "jobs": [{"name": "test", "status": "completed", "conclusion": "success", "runner_group_name": "GitHub Actions", "labels": ["ubuntu-24.04"]}]}
            return {"head_sha": "head", "run_attempt": 2 if path.endswith("/2") else 1, "status": "completed", "conclusion": "success"}
        with patch.object(self.p, "api", side_effect=fake_api):
            self.p.receipt("test", {"head": "head", "runs": [1, 2], "attempts": {"2": 2}, "jobs": 2})
            with self.assertRaisesRegex(ValueError, "attempt 1 success"):
                self.p.receipt("test", {"head": "head", "runs": [2], "jobs": 1})
        self.assertIn("/actions/runs/2/attempts/2/jobs?per_page=100", seen)

    def test_scope_receipt_requires_both_named_jobs(self):
        job = {"status": "completed", "conclusion": "success",
               "runner_group_name": "GitHub Actions", "labels": ["ubuntu-24.04"]}
        spec = {"head": "head", "runs": [1], "jobs": 2,
                "job_names": {"1": ["live (core)", "live (external)"]}}
        run = {"head_sha": "head", "run_attempt": 1, "status": "completed", "conclusion": "success"}
        for names in (["live (core)", "live (external)"], ["live (core)", "live (core)"], ["live (core)"]):
            with self.subTest(names=names):
                jobs = {"total_count": len(names), "jobs": [dict(job, name=n) for n in names]}
                with patch.object(self.p, "api", side_effect=[run, jobs]):
                    if names == ["live (core)", "live (external)"]:
                        self.p.receipt("split", spec)
                    else:
                        with self.assertRaisesRegex(ValueError, "exact job names"):
                            self.p.receipt("split", spec)

    def checkpoint(self, status="stale_candidate", candidate="historical"):
        return {"status": status, "active": {"issue": 40, "version": "v0.0.0.23",
                    "phase": "Head", "pull_request": 49, "candidate_sha": candidate}}

    def test_head_stale_is_observed_not_resumed(self):
        pr = {"head": {"sha": self.p.M["pipeline_review_head"]}, "state": "open",
              "draft": True, "merged": False}
        other = {"status": "blocked_other_active_issue"}
        with patch.object(self.p, "api", return_value=pr):
            self.p.check_active_checkpoint(self.checkpoint(), other)
            self.assertIn("Head handoff references historical PR49 revision; reconcile before integration", self.p.report["blockers"])
            with self.assertRaisesRegex(ValueError, "Head recovery status"):
                self.p.check_active_checkpoint(self.checkpoint(status="resume"), other)
            self.p.check_active_checkpoint(self.checkpoint("resume", self.p.M["pipeline_review_head"]), other)
        self.assertEqual(self.p.report["release"], "BLOCKED")

    def test_pr_review_ref_drift_and_closed_pr_fail(self):
        good = {"head": {"sha": self.p.M["pipeline_review_head"]}, "state": "open",
                "draft": True, "merged": False}
        for bad in (dict(good, head={"sha": "changed"}), dict(good, state="closed"),
                    dict(good, draft=False), dict(good, merged=True)):
            with patch.object(self.p, "api", return_value=bad):
                with self.assertRaisesRegex(ValueError, "pipeline review revision"):
                    self.p.check_pipeline_pr()

    def test_wrong_phase_and_competing_issue_fail(self):
        active = self.checkpoint()
        active["active"]["phase"] = "Worker"
        with self.assertRaisesRegex(ValueError, "sole active release checkpoint"):
            self.p.check_active_checkpoint(active, {"status": "blocked_other_active_issue"})
        pr = {"head": {"sha": self.p.M["pipeline_review_head"]}, "state": "open",
              "draft": True, "merged": False}
        with patch.object(self.p, "api", return_value=pr):
            with self.assertRaisesRegex(ValueError, "competing issue refused"):
                self.p.check_active_checkpoint(self.checkpoint(), {"status": "resume"})

    def review_case(self, rows, total=None):
        with patch.object(self.p, "api", return_value={"total_count": len(rows) if total is None else total, "check_runs": rows}):
            self.p.record_review("test", "head")
        return self.p.report["reviews"][-1]

    def valid_review(self):
        return {"id": 123, "name": "CodeRabbit", "head_sha": "head",
                "app": {"slug": "coderabbitai", "id": 347564},
                "status": "completed", "conclusion": "success"}

    def test_exact_trusted_review(self):
        self.assertEqual(self.review_case([self.valid_review()])["conclusion"], "success")

    def test_wrong_app_rejected(self):
        self.assertEqual(self.review_case([dict(self.valid_review(), app={"slug": "coderabbitai", "id": 1})])["status"], "missing")

    def test_wrong_revision_rejected(self):
        self.assertEqual(self.review_case([dict(self.valid_review(), head_sha="old")])["status"], "missing")

    def test_incomplete_inventory_rejected(self):
        self.assertEqual(self.review_case([self.valid_review()], 101)["status"], "incomplete")

    def test_multiple_exact_reviews_blocked(self):
        self.assertEqual(self.review_case([self.valid_review(), dict(self.valid_review(), id=124)])["status"], "ambiguous")

    def test_failed_review_blocks(self):
        self.assertEqual(self.review_case([dict(self.valid_review(), conclusion="failure")])["conclusion"], "failure")
        self.assertIn("test CodeRabbit review not successful", self.p.report["blockers"])

    def test_pending_review_blocks(self):
        self.assertEqual(self.review_case([dict(self.valid_review(), status="in_progress", conclusion=None)])["status"], "in_progress")
        self.assertIn("test CodeRabbit review not successful", self.p.report["blockers"])

if __name__ == "__main__":
    unittest.main()
