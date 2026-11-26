"""Ordinary singleton recovery guidance and exact evidence reuse regressions."""
import copy
import unittest
from unittest.mock import patch
from tools import session, install
from test_session import Fake, state, FIX, FIX2, CANDIDATE, RUN, BASE


class RecoveryPlanTests(unittest.TestCase):
    def setUp(self):
        self.api = Fake()
        self.state = state()
        self.state["ledger"], self.state["handoff"] = session.claim(
            self.api, self.state, 247, ["test"], "claim")

    def advance(self, **kwargs):
        self.state["ledger"], self.state["handoff"] = session.advance(
            self.api, self.state, "next", **kwargs)

    def plan(self, issue=None):
        before = copy.deepcopy(self.state)
        writes = list(self.api.writes)
        result = session.recovery_plan(self.api, self.state, issue)
        self.assertEqual(before, self.state)
        self.assertEqual(writes, self.api.writes)
        self.assertTrue(result["read_only"])
        self.assertFalse(result["evidence_verified"])
        return result

    def audited(self):
        self.advance(fix=FIX, candidate=CANDIDATE, pr=8)
        self.advance(evidence=[RUN])

    def test_worker_and_other_issue_guidance_is_read_only(self):
        result = self.plan()
        self.assertEqual(result["recovery_status"], "resume")
        self.assertIn("Implement only", result["recommended_next_action"])
        self.assertEqual(result["evidence_reuse"]["status"], "not_available")
        self.assertEqual(self.plan(248)["recovery_status"], "blocked_other_active_issue")

    def test_same_issue_exact_run_revalidated_without_advancing(self):
        self.audited()
        result = self.plan()
        self.assertEqual(result["active"]["phase"], "Internal Auditor")
        self.assertEqual(result["evidence_reuse"]["status"], "exact_run_revalidated")
        self.assertEqual(result["evidence_reuse"]["links"], [RUN])
        self.assertEqual(result["evidence_reuse"]["fix_sha"], FIX)
        self.assertEqual(result["evidence_reuse"]["integration_base_sha"], BASE)
        self.assertEqual(self.plan(248)["evidence_reuse"]["links"], [])

    def test_changed_run_and_candidate_never_reused(self):
        self.audited()
        self.api.pre_run["run_attempt"] = 2
        self.assertEqual(self.plan()["evidence_reuse"]["status"], "refused")
        self.api.pr["head"]["sha"] = "9" * 40
        result = self.plan()
        self.assertEqual(result["recovery_status"], "stale_candidate")
        self.assertEqual(result["evidence_reuse"]["links"], [])

    def test_other_fix_history_and_wrong_lease_refused(self):
        self.audited()
        previous = copy.deepcopy(self.state["handoff"]["active"])
        previous["fix_sha"] = FIX2
        self.state["handoff"]["history"].append(
            {"handoff": previous, "disposition": "rework", "decision": "prior", "merged_sha": None})
        self.assertEqual(self.plan()["evidence_reuse"]["status"], "refused")
        self.api.ref = "9" * 40
        with self.assertRaisesRegex(ValueError, "Installed state advanced"):
            session.recovery_plan(self.api, self.state)
        self.assertEqual(self.api.writes, [])

    def test_merged_and_closed_pr_require_owner_reconciliation(self):
        self.audited()
        self.api.pr.update(state="closed", merged=False)
        self.assertEqual(self.plan()["recovery_status"], "closed_pr_rework_required")
        self.api.pr["merged"] = True
        result = self.plan()
        self.assertEqual(result["recovery_status"], "merged_reconciliation_required")
        self.assertEqual(result["evidence_reuse"]["links"], [])

    def test_pending_closure_overrides_explicit_issue_guidance(self):
        self.audited()
        with patch.object(session, "pending_closure", return_value={"status": "executing"}):
            result = self.plan(247)
        self.assertEqual(result["recovery_status"], "closure_reconciliation_required")
        self.assertEqual(result["evidence_reuse"]["links"], [])

    def test_lease_advance_during_validation_refuses_advisory(self):
        self.audited()
        original = session.verify_candidate_runs
        def moved(api, current, active, links):
            original(api, current, active, links)
            api.ref = "9" * 40
        with patch.object(session, "verify_candidate_runs", side_effect=moved):
            with self.assertRaisesRegex(ValueError, "Installed state advanced"):
                session.recovery_plan(self.api, self.state)
        self.assertEqual(self.api.writes, [])


    def test_pr_changes_during_revalidation_refresh_guidance(self):
        self.audited()
        for merged, expected in (
                (True, "merged_reconciliation_required"),
                (False, "closed_pr_rework_required")):
            with self.subTest(merged=merged):
                self.api.pr.update(state="open", merged=False)
                def changed(api, current, active, links):
                    api.pr.update(state="closed", merged=merged)
                    raise ValueError("PR changed during evidence revalidation")
                with patch.object(session, "verify_candidate_runs", side_effect=changed):
                    result = self.plan()
                self.assertEqual(result["recovery_status"], expected)
                self.assertIn("Return to Head", result["recommended_next_action"])
                self.assertEqual(result["evidence_reuse"], {"status": "refused", "links": []})

    def test_refused_run_does_not_recommend_advancing(self):
        self.audited()
        self.api.pre_run["run_attempt"] = 2
        result = self.plan()
        self.assertEqual(result["recovery_status"], "evidence_revalidation_required")
        self.assertIn("do not advance", result["recommended_next_action"])

    def test_pr_closes_after_successful_run_revalidation(self):
        self.audited()
        original = session.verify_candidate_runs
        def changed(api, current, active, links):
            original(api, current, active, links)
            api.pr.update(state="closed", merged=True)
        with patch.object(session, "verify_candidate_runs", side_effect=changed):
            result = self.plan()
        self.assertEqual(result["recovery_status"], "merged_reconciliation_required")
        self.assertEqual(result["evidence_reuse"]["links"], [])
