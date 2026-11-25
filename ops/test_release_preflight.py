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

    def test_active_checkpoint_matches_pinned_phase(self):
        active = {"status": "resume", "active": {"issue": 40, "version": "v0.0.0.23",
                                                 "phase": self.p.M["installed_phase"], "pull_request": None}}
        self.p.check_active_checkpoint(active, {"status": "blocked_other_active_issue"})

    def test_active_checkpoint_rejects_stale_phase(self):
        active = {"status": "resume", "active": {"issue": 40, "version": "v0.0.0.23",
                                                 "phase": "Internal Auditor"}}
        with self.assertRaisesRegex(ValueError, "sole active release checkpoint"):
            self.p.check_active_checkpoint(active, {"status": "blocked_other_active_issue"})

    def test_competing_checkpoint_still_rejected(self):
        active = {"status": "resume", "active": {"issue": 40, "version": "v0.0.0.23",
                                                 "phase": self.p.M["installed_phase"], "pull_request": None}}
        with self.assertRaisesRegex(ValueError, "competing issue refused"):
            self.p.check_active_checkpoint(active, {"status": "resume"})

    def test_live_matrix_requires_both_jobs_and_artifacts(self):
        run_id = 123
        both_jobs = [{"name": n, "status": "completed", "conclusion": "success"} for n in ("live (core)", "live (external)")]
        both_artifacts = [{"name": f"live-acceptance-{n}-{run_id}-1", "expired": False, "size_in_bytes": 10} for n in ("core", "external")]
        def make_api(path):
            if "/jobs?" in path:
                return {"total_count": 2, "jobs": both_jobs}
            return {"total_count": 2, "artifacts": both_artifacts}
        with patch.object(self.p, "api", side_effect=make_api):
            self.p.check_live_acceptance_matrix({"live_runs": [run_id], "attempt": 1})

    def test_live_matrix_rejects_core_only(self):
        run_id = 123
        def make_api(path):
            if "/jobs?" in path:
                return {"total_count": 1, "jobs": [{"name": "live (core)", "status": "completed", "conclusion": "success"}]}
            return {"total_count": 1, "artifacts": [{"name": f"live-acceptance-core-{run_id}-1", "expired": False, "size_in_bytes": 10}]}
        with patch.object(self.p, "api", side_effect=make_api):
            with self.assertRaisesRegex(ValueError, "core and external jobs"):
                self.p.check_live_acceptance_matrix({"live_runs": [run_id], "attempt": 1})

    def test_live_matrix_rejects_missing_external_artifact(self):
        run_id = 123
        def make_api(path):
            if "/jobs?" in path:
                return {"total_count": 2, "jobs": [{"name": name, "status": "completed", "conclusion": "success"} for name in ("live (core)", "live (external)")]}
            return {"total_count": 1, "artifacts": [{"name": f"live-acceptance-core-{run_id}-1", "expired": False, "size_in_bytes": 10}]}
        with patch.object(self.p, "api", side_effect=make_api):
            with self.assertRaisesRegex(ValueError, "exact scoped artifacts"):
                self.p.check_live_acceptance_matrix({"live_runs": [run_id], "attempt": 1})

    def test_receipt_archives_require_push_and_proposed_merge(self):
        spec = {"receipt_runs": [{"run": 1, "event": "push"}, {"run": 2, "event": "pull_request"}], "attempt": 1}
        def fake(path):
            run_id = 1 if "/1/" in path else 2
            event = "push" if run_id == 1 else "pull_request"
            return {"total_count": 2, "artifacts": [
                {"name": f"{kind}-{event}-{run_id}-1", "expired": False, "size_in_bytes": 10}
                for kind in ("issue-receipts", "vib-evidence")]}
        with patch.object(self.p, "api", side_effect=fake):
            self.p.check_acceptance_receipt_archives(spec)

    def test_receipt_archives_reject_missing_graphify(self):
        spec = {"receipt_runs": [{"run": 1, "event": "pull_request"}], "attempt": 1}
        with patch.object(self.p, "api", return_value={"total_count": 1,
                "artifacts": [{"name": "issue-receipts-pull_request-1-1",
                               "expired": False, "size_in_bytes": 10}]}):
            with self.assertRaisesRegex(ValueError, "exact two archives"):
                self.p.check_acceptance_receipt_archives(spec)

    def test_head_self_reference_reports_stale_candidate(self):
        self.p.M["installed_phase"] = "Head"
        active = {"status": "stale_candidate", "active": {"issue": 40, "version": "v0.0.0.23",
                   "phase": "Head", "pull_request": 49, "candidate_sha": "historical"}}
        pr = {"head": {"sha": "test"}, "state": "open", "draft": True, "merged": False}
        with patch.object(self.p, "api", return_value=pr):
            self.p.check_active_checkpoint(active, {"status": "blocked_other_active_issue"})
            active["status"] = "resume"
            with self.assertRaisesRegex(ValueError, "Head recovery status"):
                self.p.check_active_checkpoint(active, {"status": "blocked_other_active_issue"})
        self.assertEqual(self.p.report["release"], "BLOCKED")

    def test_integrated_acceptance_pr_rejects_wrong_merge(self):
        spec = {"head": "head", "merged": True, "integrated_sha": "actual"}
        p = {"head": {"sha": "head"}, "state": "closed", "merged": True,
             "merge_commit_sha": "actual"}
        self.p.check_pr_revision("acceptance", spec, p)
        with self.assertRaisesRegex(ValueError, "integrated PR"):
            self.p.check_pr_revision("acceptance", spec, dict(p, merge_commit_sha="other"))

    def test_historical_license_is_not_current_integration(self):
        spec = {"head": "head", "merge": "old-merge", "historical_base": "old"}
        p = {"head": {"sha": "head"}, "base": {"sha": "new"}, "state": "open",
             "draft": True, "merged": False, "merge_commit_sha": None}
        self.p.check_pr_revision("license", spec, p)
        self.assertIn("license requires fresh integration review", self.p.report["blockers"])

    def test_merged_ledger_preserves_prior_mapping(self):
        rows = [{"issue": n, "version": f"v0.0.0.{v}", "state": "assigned",
                 "acceptance": ["test"]} for n, v in [(12, 6), (14, 8), (34, 32), (40, 23)]]
        for row in rows[:3]:
            row["state"] = "deferred"
        self.p.M["closed_checkpoints"] = [{"issue": r["issue"], "version": r["version"]} for r in rows[:3]]
        installed = {"issues": rows}
        source = {"issues": [dict(r, state="staged") for r in rows]}
        self.p.check_ledger_mappings(installed, source)
        with self.assertRaisesRegex(ValueError, "canonical mappings"):
            self.p.check_ledger_mappings(installed, {"issues": list(reversed(source["issues"]))})

    def test_ledger_rejects_changed_criteria(self):
        row = {"issue": 40, "version": "v0.0.0.23", "state": "in_progress", "acceptance": ["keep"]}
        with self.assertRaisesRegex(ValueError, "canonical mappings"):
            self.p.check_ledger_mappings({"issues": [row]},
                {"issues": [dict(row, acceptance=["changed"])]})

    def test_current_matrix_rejects_missing_windows(self):
        spec = {"receipt_runs": [{"run": 1, "event": "push"}, {"run": 2, "event": "pull_request"}]}
        def fake(path):
            if "/jobs?" in path:
                return {"total_count": 2, "jobs": [{"name": "verify"}, {"name": "graphify"}]}
            return {"event": "push"}
        with patch.object(self.p, "api", side_effect=fake):
            with self.assertRaisesRegex(ValueError, "three exact jobs"):
                self.p.check_current_engineering_matrix(spec)


    def test_archive_rejects_wrong_source(self):
        record = {"source":"wrong","version":"v0.0.0.36","versions":[],"operational_exclusions":["v0.0.0.23"]}
        with self.assertRaisesRegex(ValueError,"source and full version"):
            self.p.check_archive_scope(dict(record, shards=[]), {"issues":[]},{"versions":[]})

    def test_archive_rejects_missing_shard(self):
        record = {"source":self.p.M["engineering"]["head"],"version":"v0.0.0.36","versions":[],"operational_exclusions":["v0.0.0.23"],"shards":[],"lookups":{}}
        with self.assertRaisesRegex(ValueError,"two shards"):
            self.p.check_archive_scope(record,{"issues":[]},{"versions":[]})

    def test_reconciled_dispositions_reject_assigned_closed(self):
        with self.assertRaisesRegex(ValueError,"historical closure dispositions"):
            self.p.check_canonical_dispositions({"issues":[{"issue":40,"state":"in_progress"}]+[{"issue":r["issue"],"state":"assigned"} for r in self.p.M["closed_checkpoints"]]}, {"history":[]})

if __name__ == "__main__":
    unittest.main()
