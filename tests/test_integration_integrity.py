"""Regression reproductions for stranded product integration (#96)."""
import copy
import json
import unittest

from tools import session
from test_session import Fake, state, bounded_deferral, FIX, CANDIDATE, RUN, NEXT


class IntegrationIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.api = Fake()
        self.state = state()

    def reach_head(self):
        self.state["ledger"], self.state["handoff"] = session.claim(
            self.api, self.state, 247, ["test"], "Fix")
        for kwargs in (dict(fix=FIX, candidate=CANDIDATE, pr=8),
                       dict(evidence=[RUN]), {}):
            self.state["ledger"], self.state["handoff"] = session.advance(
                self.api, self.state, "next", **kwargs)

    def test_unbounded_deferred_work_blocks_unrelated_claim(self):
        self.reach_head()
        self.state["ledger"], self.state["handoff"] = session.finish(
            self.api, self.state, "deferred", "Engineering complete, integration later")
        before = copy.deepcopy(self.state)
        with self.assertRaisesRegex(ValueError, "integration debt"):
            session.claim(self.api, self.state, 248, ["test second"], "New work")
        self.assertEqual(self.state, before)
        self.assertEqual(self.api.writes, [])

    def test_unbounded_staged_work_blocks_unrelated_claim(self):
        self.reach_head()
        self.state["ledger"], self.state["handoff"] = session.finish(
            self.api, self.state, "staged", "Owner stages")
        before = copy.deepcopy(self.state)
        with self.assertRaisesRegex(ValueError, "integration debt"):
            session.claim(self.api, self.state, 248, ["test second"], "New work")
        self.assertEqual(self.state, before)
        self.assertEqual(self.api.writes, [])

    def test_same_deferred_issue_can_be_recovered(self):
        self.reach_head()
        self.state["ledger"], self.state["handoff"] = session.finish(
            self.api, self.state, "deferred", "Engineering complete, integration later")
        ledger, handoff = session.claim(
            self.api, self.state, 247, ["test"], "Reconcile original issue")
        self.assertEqual(handoff["active"]["issue"], 247)
        self.assertEqual(ledger["issues"][0]["version"], "v1.0.6.1")
        self.assertEqual(handoff["history"], self.state["handoff"]["history"])

    def test_explicit_bounded_staging_authorizes_only_named_next_issue(self):
        self.reach_head()
        decision = bounded_deferral(self.state, self.api, 248)
        with self.assertRaisesRegex(ValueError, "owner approval"):
            session.finish(self.api, self.state, "staged", decision)
        ledger, handoff = session.finish(self.api, self.state, "staged", decision,
                                         deferral_approved=True)
        with self.assertRaisesRegex(ValueError, "owner approval"):
            session.save(self.api, self.state, ledger, handoff, issue=247)
        self.assertEqual(session.save(self.api, self.state, ledger, handoff, issue=247,
                                      deferral_approved=True)["status"], "planned")
        self.state.update(ledger=ledger, handoff=handoff)
        with self.assertRaisesRegex(ValueError, "integration debt"):
            session.claim(self.api, self.state, 249, ["other"], "Wrong scope")
        ledger, handoff = session.claim(self.api, self.state, 248, ["next"], "Approved")
        self.assertEqual(handoff["active"]["issue"], 248)
        self.assertEqual(session.save(self.api, self.state, ledger, handoff, issue=248)["status"],
                         "planned")
        self.assertEqual(self.api.writes, [])

    def test_expired_changed_target_and_stale_lease_refused(self):
        self.reach_head()
        decision = bounded_deferral(self.state, self.api, 248)
        policy = json.loads(decision[len(session.DEFERRAL_DECISION):])
        policy["approved_at"] -= 7200
        policy["expires_at"] -= 7200
        with self.assertRaisesRegex(ValueError, "expired"):
            session.finish(self.api, self.state, "staged",
                session.DEFERRAL_DECISION + json.dumps(policy), deferral_approved=True)
        self.state["ledger"], self.state["handoff"] = session.finish(
            self.api, self.state, "staged", decision, deferral_approved=True)
        self.api.product = NEXT
        with self.assertRaisesRegex(ValueError, "stale"):
            session.claim(self.api, self.state, 248, ["next"], "New work")
        self.api.ref = NEXT
        with self.assertRaisesRegex(ValueError, "advanced"):
            session.claim(self.api, self.state, 248, ["next"], "New work")
        self.assertEqual(self.api.writes, [])

    def test_direct_publication_cannot_bypass_claim_guard(self):
        self.reach_head()
        self.state["ledger"], self.state["handoff"] = session.finish(
            self.api, self.state, "deferred", "Unbounded legacy decision")
        ledger, handoff = copy.deepcopy(self.state["ledger"]), copy.deepcopy(self.state["handoff"])
        ledger["issues"].append({"issue": 248, "version": "v1.0.6.2",
                                 "state": "in_progress", "acceptance": ["test second"]})
        handoff["active"] = {"issue": 248, "version": "v1.0.6.2", "phase": "Worker",
                             "next_action": "forged", "fix_sha": None, "candidate_sha": None,
                             "pull_request": None, "evidence": []}
        for apply in (False, True):
            with self.assertRaisesRegex(ValueError, "integration debt"):
                session.save(self.api, self.state, ledger, handoff, apply, issue=248)
        self.assertEqual(self.api.writes, [])

    def test_recovery_plan_reports_outstanding_integration_debt(self):
        self.reach_head()
        self.state["ledger"], self.state["handoff"] = session.finish(
            self.api, self.state, "deferred", "Legacy unbounded decision")
        before = copy.deepcopy(self.state)
        result = session.recovery_plan(self.api, self.state, 248)
        self.assertEqual(result["recovery_status"], "integration_debt_reconciliation_required")
        self.assertEqual(result["integration_debt"], [
            {"issue": 247, "version": "v1.0.6.1", "state": "deferred"}])
        self.assertEqual(self.state, before)
        self.assertEqual(self.api.writes, [])

    def test_deferral_rechecks_original_run_attempt(self):
        self.reach_head()
        decision = bounded_deferral(self.state, self.api, 248)
        self.state["ledger"], self.state["handoff"] = session.finish(
            self.api, self.state, "staged", decision, deferral_approved=True)
        self.api.pre_run["run_attempt"] = 2
        with self.assertRaises(ValueError):
            session.claim(self.api, self.state, 248, ["next"], "New work")
        self.assertEqual(self.api.writes, [])
