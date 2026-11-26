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
        from test_session import BASE, PROPOSED, TREE, post_policy
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
                return {"sha":PROPOSED,"tree":{"sha":TREE},"parents":[{"sha":BASE},{"sha":CANDIDATE}]}
            return original(method,path,body)
        with patch.object(self.api,"request",side_effect=request):
            with self.assertRaisesRegex(ValueError,"digest"):
                session.reconcile(self.api,self.state,247,"Owner integration",
                    policy={**policy,"archive_digest":"0"*64})
            # Matching parent pins and successful runs do not establish tree equality.
            for bad_tree in (None, {}, {"sha":"invalid"}, {"sha":"1"*40}):
                with self.subTest(actual_tree=bad_tree):
                    def wrong_tree(method,path,body=None):
                        result = request(method,path,body)
                        if method == "GET" and path.endswith("/git/commits/"+NEXT):
                            return {**result, "tree":bad_tree}
                        return result
                    with patch.object(self.api,"request",side_effect=wrong_tree):
                        with self.assertRaisesRegex(ValueError,"historical actual merge tree|Historical actual merge tree"):
                            session.reconcile(self.api,self.state,247,"Owner integration",policy=policy)
                    self.assertEqual(self.api.writes,[])
            ledger,handoff = session.reconcile(self.api,self.state,247,"Owner integration",policy=policy)
            self.assertEqual(ledger["issues"][0]["state"],"integrated")
            self.assertEqual(handoff["history"][:-1],archive)
            self.assertEqual(handoff["history"][-1]["handoff"]["fix_sha"],FIX)
            self.assertEqual(handoff["history"][-1]["merged_sha"],NEXT)
            self.assertEqual(session.save(self.api,self.state,ledger,handoff,issue=247,
                                          policy=policy)["status"],"planned")
            # A differing final preview tree must fail, even when run metadata
            # reports the exact preview rather than the branch head.
            preview_reads = [0]
            def changed_preview(method,path,body=None):
                result = request(method,path,body)
                if method == "GET" and path.endswith("/git/commits/"+PROPOSED):
                    preview_reads[0] += 1
                    if preview_reads[0] > 1:
                        return {**result, "tree":{"sha":"1"*40}}
                return result
            with patch.dict(self.api.pre_run, {"head_sha":PROPOSED}):
                with patch.object(self.api,"request",side_effect=changed_preview):
                    with self.assertRaisesRegex(ValueError,"Historical preview tree changed during review"):
                        session.reconcile(self.api,self.state,247,"Owner integration",policy=policy)
            self.assertEqual(preview_reads[0], 2)
            self.assertEqual(self.api.writes,[])
            # Revert only during the second (final) preview review.
            reads = [0]
            def rollback(method,path,body=None):
                result = request(method,path,body)
                if path.endswith("/actions/runs/123/attempts/1"):
                    reads[0] += 1
                    if reads[0] == 2:
                        self.api.product = BASE
                return result
            with patch.object(self.api,"request",side_effect=rollback):
                with self.assertRaises(ValueError):
                    session.reconcile(self.api,self.state,247,"Owner integration",policy=policy)
            self.assertEqual(reads[0], 2)
            self.api.product = NEXT
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

    def test_integration_archive_without_row_transition_refused(self):
        from test_session import post_policy
        self.reach_head()
        self.state["ledger"], self.state["handoff"] = session.finish(
            self.api, self.state, "staged", "Owner stages")
        self.api.pr.update(state="closed", merged=True, merge_commit_sha=NEXT)
        self.api.product = NEXT
        policy = post_policy(self.state)
        ledger, handoff = session.reconcile(self.api, self.state, 247, "Owner integrates", policy=policy)
        self.assertEqual(session.save(self.api,self.state,ledger,handoff,issue=247,policy=policy)["status"],"planned")
        ledger["issues"][0]["state"] = "staged"
        for apply in (False, True):
            with self.assertRaisesRegex(ValueError, "matching integrated row transition"):
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

    def test_expiry_after_final_remote_validation_refuses_patch(self):
        from unittest.mock import patch
        self.reach_head()
        decision = bounded_deferral(self.state, self.api, 248)
        approved = json.loads(decision[len(session.DEFERRAL_DECISION):])
        ledger, handoff = session.finish(self.api, self.state, "staged", decision,
                                         deferral_approved=True)
        clock = [approved["approved_at"]]
        journal = [False]
        original = session.verify_candidate_runs
        def verify(*args, **kwargs):
            result = original(*args, **kwargs)
            if journal[0]:
                clock[0] = approved["expires_at"]
            return result
        def ticket(_):
            journal[0] = True
        with patch.object(session.time, "time", side_effect=lambda: clock[0]), \
             patch.object(session, "verify_candidate_runs", side_effect=verify):
            with self.assertRaisesRegex(ValueError,"expired before publication"):
                session.save(self.api,self.state,ledger,handoff,True,issue=247,
                             deferral_approved=True,operation_id="a"*64,on_recovery_ticket=ticket)
        self.assertEqual([w[0] for w in self.api.writes], ["POST","POST"])
        self.assertEqual(self.api.ref, self.state["ref"])

    def test_pinless_deferral_cannot_hide_earlier_pinned_debt(self):
        self.reach_head()
        self.state["ledger"], self.state["handoff"] = session.finish(
            self.api, self.state, "deferred", "Earlier pinned debt")
        self.state["ledger"], self.state["handoff"] = session.claim(
            self.api, self.state, 247, ["test"], "Same issue recovery")
        self.state["ledger"], self.state["handoff"] = session.advance(
            self.api, self.state, "Head", return_to_head=True)
        decision = bounded_deferral(self.state, self.api, 248)
        self.state["ledger"], self.state["handoff"] = session.finish(
            self.api, self.state, "deferred", decision, deferral_approved=True)
        with self.assertRaisesRegex(ValueError, "Unbounded integration debt"):
            session.claim(self.api, self.state, 248, ["next"], "Unrelated")
        self.assertEqual(self.api.writes, [])

    def test_deferred_archive_after_integration_refused(self):
        from test_session import post_policy
        self.reach_head()
        self.state["ledger"], self.state["handoff"] = session.finish(
            self.api, self.state, "staged", "Owner stages")
        self.api.pr.update(state="closed", merged=True, merge_commit_sha=NEXT)
        self.api.product = NEXT
        policy = post_policy(self.state)
        ledger, handoff = session.reconcile(self.api, self.state, 247, "Owner integrates", policy=policy)
        handoff["history"].append({**copy.deepcopy(handoff["history"][-1]),
                                   "disposition": "deferred", "merged_sha": None,
                                   "decision": "Conflicting disposition"})
        for apply in (False, True):
            with self.assertRaisesRegex(ValueError, "Final archive disposition"):
                session.save(self.api,self.state,ledger,handoff,apply,issue=247,policy=policy)
        self.assertEqual(self.api.writes, [])

    def test_recovery_propagates_lineage_and_deferral_throttle(self):
        from tools import install
        from unittest.mock import patch
        self.reach_head()
        self.state["ledger"], self.state["handoff"] = session.finish(
            self.api, self.state, "deferred", "Legacy debt")
        for name in ("require_product_lineage", "require_integration_debt_clear"):
            error = install.ApiError(429, "GET", "compare", 17)
            with patch.object(session, name, side_effect=error):
                with self.assertRaises(install.ApiError) as caught:
                    session.recovery_plan(self.api,self.state,248)
                self.assertEqual(caught.exception.retry_after,17)
        self.assertEqual(self.api.writes, [])

    def test_staged_row_without_archive_refused(self):
        self.reach_head()
        ledger, handoff = session.finish(self.api,self.state,"staged","Owner stages")
        handoff["history"] = copy.deepcopy(self.state["handoff"]["history"])
        for apply in (False, True):
            with self.assertRaisesRegex(ValueError,"matching final staged archive"):
                session.save(self.api,self.state,ledger,handoff,apply,issue=247)
        self.assertEqual(self.api.writes,[])

    def test_expired_pinless_deferral_can_be_renewed(self):
        from unittest.mock import patch
        self.state["ledger"],self.state["handoff"] = session.claim(self.api,self.state,247,["test"],"Fix")
        self.state["ledger"],self.state["handoff"] = session.advance(self.api,self.state,"Head",return_to_head=True)
        first = bounded_deferral(self.state,self.api,248)
        self.state["ledger"],self.state["handoff"] = session.finish(self.api,self.state,"deferred",first,deferral_approved=True)
        original = copy.deepcopy(self.state["handoff"]["history"])
        expiry = json.loads(first[len(session.DEFERRAL_DECISION):])["expires_at"]
        with patch.object(session.time,"time",return_value=expiry+1):
            with self.assertRaisesRegex(ValueError,"expired"):
                session.claim(self.api,self.state,248,["next"],"Blocked")
            self.state["ledger"],self.state["handoff"] = session.claim(self.api,self.state,247,["test"],"Renew")
            self.state["ledger"],self.state["handoff"] = session.advance(self.api,self.state,"Head",return_to_head=True)
            second = bounded_deferral(self.state,self.api,248)
            self.state["ledger"],self.state["handoff"] = session.finish(self.api,self.state,"deferred",second,deferral_approved=True)
            ledger,handoff = session.claim(self.api,self.state,248,["next"],"Approved")
            self.assertEqual(handoff["active"]["issue"],248)
            self.assertEqual(handoff["history"][:len(original)],original)
        self.assertEqual(self.api.writes,[])

    def test_integration_does_not_clear_other_fix(self):
        from test_session import post_policy, FIX2
        self.reach_head()
        self.state["ledger"],self.state["handoff"] = session.finish(self.api,self.state,"deferred","Prior fix")
        old = copy.deepcopy(self.state["handoff"]["history"][0])
        # Simulate a separate reviewed fix for the same issue, using valid pins.
        self.state["ledger"],self.state["handoff"] = session.claim(self.api,self.state,247,["test"],"Rework")
        for kwargs in (dict(fix=FIX2,candidate=CANDIDATE,pr=8),dict(evidence=[RUN]),{}):
            self.state["ledger"],self.state["handoff"] = session.advance(self.api,self.state,"next",**kwargs)
        self.state["ledger"],self.state["handoff"] = session.finish(self.api,self.state,"staged","New fix")
        self.api.pr.update(state="closed",merged=True,merge_commit_sha=NEXT)
        self.api.product=NEXT
        policy=post_policy(self.state)
        ledger,handoff=session.reconcile(self.api,self.state,247,"Integrate second fix",policy=policy)
        proposed={**self.state,"ledger":ledger,"handoff":handoff}
        self.assertEqual(session.outstanding_integration_records(proposed)[247],[old])
        for apply in (False,True):
            with self.assertRaisesRegex(ValueError,"different historical fix unresolved"):
                session.save(self.api,self.state,ledger,handoff,apply,issue=247,policy=policy)
        self.assertEqual(self.api.writes,[])

    def test_expired_pinned_deferral_can_be_renewed_for_same_fix(self):
        from unittest.mock import patch
        self.reach_head()
        first=bounded_deferral(self.state,self.api,248)
        self.state["ledger"],self.state["handoff"]=session.finish(
            self.api,self.state,"deferred",first,deferral_approved=True)
        old=copy.deepcopy(self.state["handoff"]["history"])
        expiry=json.loads(first[len(session.DEFERRAL_DECISION):])["expires_at"]
        with patch.object(session.time,"time",return_value=expiry+1):
            with self.assertRaisesRegex(ValueError,"expired"):
                session.claim(self.api,self.state,248,["next"],"Blocked")
            self.reach_head()
            second=bounded_deferral(self.state,self.api,248)
            ledger,handoff=session.finish(self.api,self.state,"deferred",second,deferral_approved=True)
            self.assertEqual(session.save(self.api,self.state,ledger,handoff,issue=247,
                                          deferral_approved=True)["status"],"planned")
            self.state.update(ledger=ledger,handoff=handoff)
            _,next_handoff=session.claim(self.api,self.state,248,["next"],"Approved")
            self.assertEqual(next_handoff["active"]["issue"],248)
            self.assertEqual(next_handoff["history"][:len(old)],old)
        self.assertEqual(self.api.writes,[])

    def test_direct_deferral_cannot_erase_active_head_pins(self):
        self.reach_head()
        original=copy.deepcopy(self.state)
        forged=copy.deepcopy(self.state)
        active=forged["handoff"]["active"]
        active.update(fix_sha=None,candidate_sha=None,pull_request=None,evidence=[])
        active.pop("integration_base_sha")
        active.pop("integration_merge_sha")
        decision=bounded_deferral(forged,self.api,248)
        ledger,handoff=session.finish(self.api,forged,"deferred",decision,deferral_approved=True)
        for apply in (False,True):
            with self.assertRaisesRegex(ValueError,"preserve the original active Head handoff"):
                session.save(self.api,self.state,ledger,handoff,apply,issue=247,deferral_approved=True)
        self.assertEqual(self.state,original)
        self.assertEqual(self.api.writes,[])
