"""Issue-local transaction integrity through the existing session API."""
import copy
import json
import unittest
from tools import session, install
from test_session import Fake, state, post_policy, bounded_deferral, FIX, FIX2, CANDIDATE, BASE, NEXT, RUN, PROPOSED

A, B = 247, 248

class IssueIsolationTests(unittest.TestCase):
    def apply(self,s,result):
        s["ledger"],s["handoff"]=result

    def staged_then_active(self):
        api,s=Fake(),state()
        self.apply(s,session.claim(api,s,A,["test A"],"A"))
        for kw in ({"fix":FIX,"candidate":CANDIDATE,"pr":8},{"evidence":[RUN]},{}):
            self.apply(s,session.advance(api,s,"next",**kw))
        self.apply(s,session.finish(api,s,"staged",bounded_deferral(s,api,B),
                                    deferral_approved=True))
        self.apply(s,session.claim(api,s,B,["test B"],"B"))
        return api,s

    def issue_view(self,s,issue):
        return copy.deepcopy((next(r for r in s["ledger"]["issues"] if r["issue"]==issue),
            [r for r in s["handoff"]["history"] if r["handoff"]["issue"]==issue],
            s["handoff"]["active"] if (s["handoff"]["active"] or {}).get("issue")==issue else None))

    def transition(self,api,s,result,issue):
        ledger,handoff=result
        before=copy.deepcopy(s)
        self.assertEqual(session.save(api,s,ledger,handoff,issue=issue)["status"],"planned")
        self.assertEqual(s,before)
        self.apply(s,result)

    def test_validate_refresh_block_defer_and_stage_preserve_other_issue(self):
        for disposition in ("blocked","deferred","staged"):
            with self.subTest(disposition=disposition):
                api,s=self.staged_then_active()
                original=self.issue_view(s,A)
                for kw in ({"fix":FIX2,"candidate":CANDIDATE,"pr":8},{"evidence":[RUN]},{}):
                    self.transition(api,s,session.advance(api,s,"next",**kw),B)
                    self.assertEqual(self.issue_view(s,A),original)
                self.transition(api,s,session.advance(api,s,"refresh",refresh=True),B)
                self.assertEqual(self.issue_view(s,A),original)
                self.transition(api,s,session.advance(api,s,"verify",evidence=[RUN]),B)
                self.transition(api,s,session.advance(api,s,"audit"),B)
                self.transition(api,s,session.finish(api,s,disposition,"decision B"),B)
                self.assertEqual(self.issue_view(s,A),original)
                self.assertEqual(api.writes,[])

    def test_unrelated_ledger_tampering_rejected_before_any_write(self):
        api,s=self.staged_then_active()
        for field,value in (("state","blocked"),("acceptance",["wrong test"])):
            ledger,handoff=session.advance(api,s,"block B",return_to_head=True)
            ledger["issues"][0][field]=value
            before=copy.deepcopy(s)
            expected = "Historical acceptance criteria changed" if field == "acceptance" else "scope violation"
            for apply in (False,True):
                with self.assertRaisesRegex(ValueError,expected):
                    session.save(api,s,ledger,handoff,apply,issue=B)
            self.assertEqual(s,before)
        self.assertEqual(api.writes,[])

    def test_unrelated_archive_append_or_rewrite_rejected(self):
        api,s=self.staged_then_active()
        ledger,handoff=session.advance(api,s,"block B",return_to_head=True)
        for mutate in ("append","rewrite"):
            bad=copy.deepcopy(handoff)
            if mutate=="append":
                bad["history"].append(copy.deepcopy(bad["history"][0]))
            else:
                bad["history"][0]["handoff"]["evidence"]=[]
            expected = "Archived staged/integrated handoff requires" if mutate == "rewrite" else "scope violation"
            for apply in (False,True):
                with self.assertRaisesRegex(ValueError,expected):
                    session.save(api,s,ledger,bad,apply,issue=B)
        self.assertEqual(api.writes,[])

    def test_explicit_wrong_issue_and_active_slot_replacement_rejected(self):
        api,s=self.staged_then_active()
        ledger,handoff=session.advance(api,s,"block B",return_to_head=True)
        with self.assertRaisesRegex(ValueError,"scope violation"):
            session.save(api,s,ledger,handoff,True,issue=A)
        ledger=copy.deepcopy(s["ledger"])
        handoff=copy.deepcopy(s["handoff"])
        ledger["issues"][0]["state"]="in_progress"
        ledger["issues"][1]["state"]="blocked"
        handoff["active"]=copy.deepcopy(handoff["history"][0]["handoff"])
        with self.assertRaisesRegex(ValueError,"scope violation"):
            session.save(api,s,ledger,handoff,True,issue=B)
        self.assertEqual(api.writes,[])

    def test_existing_criteria_and_new_unrelated_issue_rejected(self):
        api,s=self.staged_then_active()
        ledger,handoff=session.advance(api,s,"block B",return_to_head=True)
        ledger["issues"][1]["acceptance"]=["different"]
        with self.assertRaisesRegex(ValueError,"criteria changed"):
            session.save(api,s,ledger,handoff,True,issue=B)
        ledger,handoff=session.advance(api,s,"block B",return_to_head=True)
        ledger["issues"].append({"issue":249,"version":"v1.0.6.3","state":"assigned","acceptance":["other"]})
        with self.assertRaisesRegex(ValueError,"scope violation"):
            session.save(api,s,ledger,handoff,True,issue=B)
        self.assertEqual(api.writes,[])

    def test_reconcile_staged_issue_preserves_unrelated_active_worker(self):
        api,s=self.staged_then_active()
        original=self.issue_view(s,B)
        api.pr.update(state="closed",merged=True,merge_commit_sha=NEXT)
        api.product=NEXT
        # post_policy helper normally selects the active issue; choose A's
        # archived handoff to build the same owner-reviewed policy.
        isolated=copy.deepcopy(s)
        isolated["handoff"]["active"]=None
        policy=post_policy(isolated,A)
        self.transition(api,s,session.reconcile(api,s,A,"integrate A",policy=policy),A)
        self.assertEqual(self.issue_view(s,B),original)
        self.assertEqual(self.issue_view(s,A)[0]["state"],"integrated")
        self.assertEqual(api.writes,[])
        # The unrelated worker can still return to Head and be blocked.
        self.transition(api,s,session.advance(api,s,"B blocked",return_to_head=True),B)
        integrated=self.issue_view(s,A)
        self.transition(api,s,session.finish(api,s,"blocked","B blocked"),B)
        self.assertEqual(self.issue_view(s,A),integrated)

    def test_wrong_issue_post_merge_policy_rejected_without_mutation(self):
        api,s=self.staged_then_active()
        api.pr.update(state="closed",merged=True,merge_commit_sha=NEXT)
        api.product=NEXT
        isolated=copy.deepcopy(s)
        isolated["handoff"]["active"]=None
        policy=post_policy(isolated,A)
        policy["issues"][0]["issue"]=B
        before=copy.deepcopy(s)
        with self.assertRaisesRegex(ValueError,"criterion"):
            session.reconcile(api,s,A,"wrong scope",policy=policy)
        self.assertEqual(s,before)
        self.assertEqual(api.writes,[])

    def test_stale_run_history_of_other_issue_does_not_poison_current_issue(self):
        api,s=self.staged_then_active()
        # A's archived pins differ from B's, but the current run qualifies
        # B's candidate. Other issue history must not blacklist the run.
        s["handoff"]["history"][0]["handoff"]["integration_merge_sha"]="6"*40
        original=self.issue_view(s,A)
        self.transition(api,s,session.advance(api,s,"B fix",fix=FIX2,candidate=CANDIDATE,pr=8),B)
        self.transition(api,s,session.advance(api,s,"B proof",evidence=[RUN]),B)
        self.assertEqual(self.issue_view(s,A),original)

    def test_serialized_write_preserves_unrelated_records(self):
        api,s=self.staged_then_active()
        original=self.issue_view(s,A)
        ledger,handoff=session.advance(api,s,"block B",return_to_head=True)
        self.assertEqual(session.save(api,s,ledger,handoff,True,issue=B)["installed_sha"],NEXT)
        tree=next(body for method,path,body in api.writes if method=="POST" and path.endswith("/git/trees"))
        files={x["path"]:json.loads(x["content"]) for x in tree["tree"]}
        published={**s,"ledger":files[session.LEDGER],"handoff":files[session.HANDOFF]}
        self.assertEqual(self.issue_view(published,A),original)
        self.assertEqual(sum(m=="PATCH" for m,_,_ in api.writes),1)

    def test_stale_writer_cannot_publish_after_unrelated_transaction(self):
        api,s=self.staged_then_active()
        ledger,handoff=session.advance(api,s,"block B",return_to_head=True)
        api.ref=NEXT
        before=copy.deepcopy(s)
        with self.assertRaisesRegex(ValueError,"advanced"):
            session.save(api,s,ledger,handoff,True,issue=B)
        self.assertEqual(s,before)
        self.assertEqual(api.writes,[])


    def test_distinct_pr_refresh_does_not_read_or_change_other_pr(self):
        api,s=self.staged_then_active()
        original=self.issue_view(s,A)
        pr_a=copy.deepcopy(api.pr)
        run_a=copy.deepcopy(api.pre_run)
        api.pr.update(number=9,head={"sha":NEXT,"repo":{"id":42}},merge_commit_sha="7"*40)
        api.pre_run.update(id=125,head_sha=NEXT,pull_requests=[
            {"number":9,"head":{"sha":NEXT},"base":{"sha":BASE}}])
        original_request=api.request
        reads=[]
        def request(method,path,body=None):
            reads.append(path)
            if method=="GET" and path.endswith("/pulls/8"):
                return pr_a
            if method=="GET" and path.endswith("/git/commits/"+pr_a["merge_commit_sha"]):
                return {"sha":pr_a["merge_commit_sha"],"parents":[{"sha":pr_a["base"]["sha"]},
                            {"sha":pr_a["head"]["sha"]}]}
            if method=="GET" and "/actions/runs/123" in path:
                return run_a
            return original_request(method,path,body)
        api.request=request
        run_b=RUN.replace("/123/","/125/")
        for kw in ({"fix":FIX2,"candidate":NEXT,"pr":9},{"evidence":[run_b]},{},
                   {"refresh":True},{"evidence":[run_b]},{}):
            self.transition(api,s,session.advance(api,s,"B",**kw),B)
        self.transition(api,s,session.finish(api,s,"staged","B staged"),B)
        self.assertEqual(self.issue_view(s,A),original)
        self.assertFalse(any("/pulls/8" in path or "/actions/runs/123" in path for path in reads))
        self.assertEqual(session.inspect(api,s,A)["status"],"staged")
        self.assertEqual(api.writes,[])

    def test_terminal_issue_and_acceptance_cannot_be_reopened_by_save(self):
        api,s=self.staged_then_active()
        api.pr.update(state="closed",merged=True,merge_commit_sha=NEXT)
        api.product=NEXT
        isolated=copy.deepcopy(s)
        isolated["handoff"]["active"]=None
        self.apply(s,session.reconcile(api,s,A,"integrate A",policy=post_policy(isolated,A)))
        ledger=copy.deepcopy(s["ledger"])
        ledger["issues"][0]["state"]="assigned"
        with self.assertRaisesRegex(ValueError,"terminal"):
            session.save(api,s,ledger,copy.deepcopy(s["handoff"]),True,issue=A)
        self.assertEqual(api.writes,[])

    def test_legacy_save_can_infer_staged_reconciliation_without_touching_active(self):
        api,s=self.staged_then_active()
        api.pr.update(state="closed",merged=True,merge_commit_sha=NEXT)
        api.product=NEXT
        isolated=copy.deepcopy(s)
        isolated["handoff"]["active"]=None
        ledger,handoff=session.reconcile(api,s,A,"integrate A",policy=post_policy(isolated,A))
        self.assertEqual(session.save(api,s,ledger,handoff)["status"],"planned")
        self.assertEqual(handoff["active"],s["handoff"]["active"])

    def test_cli_wrong_issue_refuses_before_transition(self):
        import contextlib
        import io
        from unittest.mock import patch
        api,s=self.staged_then_active()
        for command in (["advance","--issue",str(A),"--note","wrong"],
                        ["finish","blocked","--issue",str(A),"--decision","wrong","--owner-approved"]):
            with patch("sys.argv",["session","--target","example/existing",*command]), \
                 patch.object(session,"load",return_value=s), \
                 patch.object(session,"advance") as advance, patch.object(session,"finish") as finish, \
                 patch.object(session,"save") as save, contextlib.redirect_stderr(io.StringIO()) as err:
                with self.assertRaises(SystemExit) as exc:
                    session.main()
                self.assertEqual(exc.exception.code,1)
                self.assertIn("Requested issue does not own",err.getvalue())
                advance.assert_not_called()
                finish.assert_not_called()
                save.assert_not_called()
