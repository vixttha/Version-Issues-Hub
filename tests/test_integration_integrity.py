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
        with self.assertRaisesRegex(ValueError, "(?i)integration debt"):
            session.claim(self.api, self.state, 248, ["test second"], "New work")
        self.assertEqual(self.state, before)
        self.assertEqual(self.api.writes, [])

    def test_unbounded_staged_work_blocks_unrelated_claim(self):
        self.reach_head()
        self.state["ledger"], self.state["handoff"] = session.finish(
            self.api, self.state, "staged", "Owner stages")
        before = copy.deepcopy(self.state)
        with self.assertRaisesRegex(ValueError, "(?i)integration debt"):
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
        with self.assertRaisesRegex(ValueError, "(?i)integration debt"):
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
            with self.assertRaisesRegex(ValueError, "(?i)integration debt"):
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

    def test_blocked_rework_cannot_hide_historical_debt(self):
        self.reach_head()
        self.state["ledger"], self.state["handoff"] = session.finish(
            self.api, self.state, "deferred", "Legacy debt")
        self.state["ledger"], self.state["handoff"] = session.claim(
            self.api, self.state, 247, ["test"], "Rework")
        self.state["ledger"], self.state["handoff"] = session.advance(
            self.api, self.state, "Blocked", return_to_head=True)
        self.state["ledger"], self.state["handoff"] = session.finish(
            self.api, self.state, "blocked", "Unresolved blocker")
        self.assertEqual(session.unresolved_integration_debt(self.state)[0]["issue"],247)
        with self.assertRaisesRegex(ValueError, "(?i)integration debt"):
            session.claim(self.api, self.state, 248, ["next"], "Unrelated")
        self.assertEqual(self.api.writes, [])

    def test_ledger_only_integration_cannot_erase_debt(self):
        self.reach_head()
        self.state["ledger"], self.state["handoff"] = session.finish(
            self.api, self.state, "deferred", "Legacy debt")
        ledger, handoff = copy.deepcopy(self.state["ledger"]), copy.deepcopy(self.state["handoff"])
        ledger["issues"][0]["state"] = "integrated"
        for apply in (False, True):
            with self.assertRaisesRegex(ValueError,"exact integration archive"):
                session.save(self.api,self.state,ledger,handoff,apply,issue=247)
        self.assertEqual(self.api.writes, [])

    def test_default_target_mismatch_is_refused(self):
        from tools import install
        meta = {"id":42, "full_name":"example/existing", "default_branch":"trunk"}
        with self.assertRaisesRegex(ValueError,"without owner designation"):
            install.product_target(meta, {"product_branch":"release"})
        self.assertEqual(install.product_target(meta, {"product_branch":"trunk"}),"trunk")
        with self.assertRaisesRegex(ValueError,"collision"):
            install.product_target(meta, {"product_branch":install.BRANCH})

    def test_product_lineage_reset_blocks_claim_and_publication(self):
        from test_session import BASE
        self.state["manifest"]["product_baseline_sha"] = BASE
        self.state["product_sha"] = BASE
        ledger, handoff = session.claim(self.api, self.state, 247, ["test"], "New work")
        self.assertEqual(handoff["active"]["issue"],247)
        self.api.product = NEXT
        for apply in (False, True):
            with self.assertRaisesRegex(ValueError,"lineage target advanced"):
                session.save(self.api,self.state,ledger,handoff,apply,issue=247)
        self.state["product_sha"] = NEXT
        with self.assertRaisesRegex(ValueError,"no longer contains"):
            session.claim(self.api,self.state,247,["test"],"New work")
        self.assertEqual(self.api.writes,[])

    def test_stale_ordinary_claim_and_direct_save_fail_before_writes(self):
        from test_session import BASE
        self.state["manifest"]["product_baseline_sha"] = BASE
        self.state["product_sha"] = BASE
        ledger, handoff = session.claim(self.api, self.state, 247, ["test"], "New work")
        self.api.ref = NEXT
        with self.assertRaisesRegex(session.HandoffStale, "Installed state advanced"):
            session.claim(self.api, self.state, 247, ["test"], "New work")
        for apply in (False, True):
            with self.assertRaisesRegex(session.HandoffStale, "Installed state advanced"):
                session.save(self.api, self.state, ledger, handoff, apply, issue=247)
        self.assertEqual(self.api.writes, [])

    def test_historical_engineering_reconciliation_preserves_original_archive(self):
        from test_session import BASE, PROPOSED, post_policy
        from unittest.mock import patch
        self.state["ledger"], self.state["handoff"] = session.claim(
            self.api, self.state, 247, ["test"], "Fix")
        self.state["ledger"], self.state["handoff"] = session.advance(
            self.api, self.state, "Head review", return_to_head=True)
        self.state["ledger"], self.state["handoff"] = session.finish(
            self.api, self.state, "deferred",
            "Owner-approved engineering completion: PR #8; fix " + FIX +
            "; candidate " + CANDIDATE + "; merge " + NEXT + ".")
        archive = copy.deepcopy(self.state["handoff"]["history"])
        self.api.pr.update(state="closed",merged=True,merge_commit_sha=NEXT)
        self.api.product = NEXT
        review = post_policy(self.state)
        review["issues"][0]["fix_sha"] = FIX
        policy = {"schema_version":1, "outcome":"historical_product_integration",
                  "archive_index":0, "archive_digest":session.closure_digest(archive[0]),
                  "premerge":{"merge_sha":PROPOSED,"evidence":[RUN]}, "review":review}
        original = self.api.request
        def request(method,path,body=None):
            if method == "GET" and path.endswith("/git/commits/"+PROPOSED):
                return {"sha":PROPOSED,"parents":[{"sha":BASE},{"sha":CANDIDATE}]}
            return original(method,path,body)
        with patch.object(self.api,"request",side_effect=request):
            with self.assertRaisesRegex(ValueError,"digest"):
                session.reconcile(self.api,self.state,247,"Owner integration",
                    policy={**policy,"archive_digest":"0"*64})
            ledger,handoff = session.reconcile(self.api,self.state,247,"Owner integration",policy=policy)
            self.assertEqual(ledger["issues"][0]["state"],"integrated")
            self.assertEqual(handoff["history"][:-1],archive)
            self.assertEqual(handoff["history"][-1]["handoff"]["fix_sha"],FIX)
            self.assertEqual(handoff["history"][-1]["merged_sha"],NEXT)
            self.assertEqual(session.save(self.api,self.state,ledger,handoff,issue=247,
                                          policy=policy)["status"],"planned")
            self.api.pre_run["run_attempt"] = 2
            with self.assertRaises(ValueError):
                session.reconcile(self.api,self.state,247,"Owner integration",policy=policy)
        self.assertEqual(self.api.writes,[])

    def test_direct_integration_cannot_replace_archived_fix(self):
        from test_session import post_policy
        self.reach_head()
        self.state["ledger"], self.state["handoff"] = session.finish(
            self.api, self.state, "staged", "Owner stages")
        self.api.pr.update(state="closed", merged=True, merge_commit_sha=NEXT)
        self.api.product = NEXT
        policy = post_policy(self.state)
        ledger, handoff = session.reconcile(self.api, self.state, 247, "Owner integrates", policy=policy)
        self.assertEqual(session.save(self.api,self.state,ledger,handoff,issue=247,policy=policy)["status"],"planned")
        handoff["history"][-1]["handoff"]["fix_sha"] = "1"*40
        for apply in (False, True):
            with self.assertRaisesRegex(ValueError,"preserve original handoff pins"):
                session.save(self.api,self.state,ledger,handoff,apply,issue=247,policy=policy)
        self.assertEqual(self.api.writes, [])

    def test_historical_legacy_conflicting_pin_rejected(self):
        from test_session import post_policy, PROPOSED
        self.reach_head()
        self.state["ledger"], self.state["handoff"] = session.finish(
            self.api, self.state, "deferred",
            "Owner-approved engineering completion: PR #8; fix " + "1"*40 +
            "; candidate " + CANDIDATE + "; merge " + NEXT + ".")
        archive = self.state["handoff"]["history"][0]
        review = post_policy(self.state)
        review["issues"][0]["fix_sha"] = "1"*40
        policy = {"schema_version":1,"outcome":"historical_product_integration",
                  "archive_index":0,"archive_digest":session.closure_digest(archive),
                  "premerge":{"merge_sha":PROPOSED,"evidence":[RUN]},"review":review}
        with self.assertRaisesRegex(ValueError,"conflicts with archived handoff pin"):
            session.reconcile(self.api,self.state,247,"Owner integrates",policy=policy)
        self.assertEqual(self.api.writes, [])

    def test_archived_run_invalidated_when_preview_changes(self):
        self.reach_head()
        self.state["ledger"], self.state["handoff"] = session.finish(
            self.api, self.state, "staged", "Owner stages")
        active = copy.deepcopy(self.state["handoff"]["history"][0]["handoff"])
        self.assertEqual(session.invalidated_archive_runs(self.state, active), set())
        active["integration_merge_sha"] = "1"*40
        self.assertIn(session.evidence_run(self.state["ledger"]["repository"], RUN)[0],
                      session.invalidated_archive_runs(self.state, active))
