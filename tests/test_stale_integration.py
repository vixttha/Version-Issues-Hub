"""Integration staleness and non-destructive refresh through production session."""
import copy
import unittest
from tools import session
from test_session import Fake, state, FIX, CANDIDATE, BASE, NEXT, RUN, PROPOSED

NEW_BASE = "4"*40
NEW_MERGE = "5"*40
NEW_RUN = RUN.replace("/123/", "/125/")

class StaleIntegrationTests(unittest.TestCase):
    def setup_case(self, staged=False):
        api,s=Fake(),state()
        s["ledger"],s["handoff"]=session.claim(api,s,247,["test"],"Fix")
        for kw in ({"fix":FIX,"candidate":CANDIDATE,"pr":8},{"evidence":[RUN]},{}):
            s["ledger"],s["handoff"]=session.advance(api,s,"next",**kw)
        if staged:
            s["ledger"],s["handoff"]=session.finish(api,s,"staged","stage")
        return api,s

    def move_base(self,api):
        api.product=NEW_BASE
        api.pr["base"]["sha"]=NEW_BASE
        api.pr["merge_commit_sha"]=NEW_MERGE

    def test_other_merge_invalidates_active_and_staged_without_mutation(self):
        for staged in (False,True):
            api,s=self.setup_case(staged)
            before=copy.deepcopy(s)
            self.move_base(api)
            self.assertEqual(session.inspect(api,s,247)["status"],"stale_integration_evidence")
            if not staged:
                with self.assertRaisesRegex(ValueError,"Stale"):
                    session.finish(api,s,"staged","old")
            self.assertEqual(s,before)
            self.assertEqual(api.writes,[])

    def test_refresh_keeps_fix_version_and_history_and_rejects_old_run(self):
        api,s=self.setup_case()
        old=copy.deepcopy(s["handoff"]["active"])
        self.move_base(api)
        s["ledger"],s["handoff"]=session.advance(api,s,"refresh",refresh=True)
        active=s["handoff"]["active"]
        self.assertEqual(active["fix_sha"],FIX)
        self.assertEqual(active["version"],old["version"])
        self.assertEqual(active["candidate_sha"],CANDIDATE)
        self.assertEqual(active["phase"],"Validate")
        self.assertEqual(active["evidence"],[])
        self.assertEqual(s["handoff"]["history"][-1]["handoff"],old)
        before=copy.deepcopy(s)
        with self.assertRaisesRegex(ValueError,"Archived run"):
            session.advance(api,s,"old run",evidence=[RUN])
        self.assertEqual(s,before)
        # Different exact run, now bound to the new base/head.
        original=api.request
        def request(method,path,body=None):
            if "/actions/runs/125" in path:
                return {**api.pre_run,"id":125,"pull_requests":[
                    {"number":8,"head":{"sha":CANDIDATE},"base":{"sha":NEW_BASE}}]}
            return original(method,path,body)
        api.request=request
        s["ledger"],s["handoff"]=session.advance(api,s,"fresh",evidence=[NEW_RUN])
        s["ledger"],s["handoff"]=session.advance(api,s,"audit")
        ledger,handoff=session.finish(api,s,"staged","accept fresh")
        self.assertEqual(ledger["issues"][0]["state"],"staged")
        self.assertEqual(handoff["history"][-1]["handoff"]["evidence"],[NEW_RUN])
        self.assertEqual(handoff["history"][-1]["handoff"]["integration_base_sha"],NEW_BASE)

    def active_recovery_fixture(self):
        from test_session import post_policy, TREE
        api, s = self.setup_case()
        original = copy.deepcopy(s["handoff"]["active"])
        self.move_base(api)
        api.product = NEXT
        api.pr.update(state="closed", merged=True, merge_commit_sha=NEXT)
        api.merge_parents = [{"sha": NEW_BASE}, {"sha": CANDIDATE}]
        request = api.request
        fresh_run = {**api.pre_run, "id": 125, "head_sha": NEW_MERGE,
                     "pull_requests": [{"number": 8, "head": {"sha": CANDIDATE},
                                        "base": {"sha": NEW_BASE}}]}
        def dispatch(method, path, body=None):
            if method == "GET" and path.endswith("/git/commits/" + NEW_MERGE):
                return {"sha": NEW_MERGE, "tree": {"sha": TREE},
                        "parents": [{"sha": NEW_BASE}, {"sha": CANDIDATE}]}
            if method == "GET" and "/actions/runs/125" in path:
                return fresh_run
            return request(method, path, body)
        api.request = dispatch
        review = post_policy(s)
        review["base_sha"] = NEW_BASE
        policy = {"schema_version": 1, "outcome": "active_head_recovery",
                  "head_digest": session.closure_digest(original),
                  "premerge": {"merge_sha": NEW_MERGE, "evidence": [NEW_RUN]},
                  "review": review}
        return api, s, original, policy, fresh_run

    def test_active_head_recovery_preserves_original_pins_and_accepts_fresh_proof(self):
        from test_session import POST_RUN
        api, s, original, policy, _ = self.active_recovery_fixture()
        snapshot = copy.deepcopy(s)
        with self.assertRaisesRegex(ValueError, "Stale"):
            session.finish(api, s, "integrated", "Ordinary integration", policy=policy["review"])
        ledger, handoff = session.finish(api, s, "integrated", "Owner reviewed recovery", policy=policy)
        record = handoff["history"][-1]
        self.assertEqual(record["handoff"], {**original, "evidence": [RUN, NEW_RUN, POST_RUN]})
        self.assertEqual(record["merged_sha"], NEXT)
        self.assertEqual(ledger["issues"][0]["state"], "integrated")
        self.assertIsNone(handoff["active"])
        self.assertEqual(session.save(api, s, ledger, handoff, issue=247, policy=policy)["status"],
                         "planned")
        self.assertEqual(s, snapshot)
        self.assertEqual(api.writes, [])
        self.assertEqual(session.save(api, s, ledger, handoff, True, issue=247,
                                      policy=policy)["installed_sha"], NEXT)
        self.assertEqual([w[0] for w in api.writes], ["POST", "POST", "PATCH"])

    def test_active_head_recovery_rejects_invalid_or_stale_proof_before_publication(self):
        for mutation in ("digest", "old_run", "wrong_base", "wrong_head", "wrong_merge",
                         "no_association", "rerun", "wrong_tree", "forged_archive"):
            with self.subTest(mutation=mutation):
                api, s, _, policy, fresh = self.active_recovery_fixture()
                snapshot = copy.deepcopy(s)
                if mutation == "digest":
                    policy["head_digest"] = "0"*64
                elif mutation == "old_run":
                    policy["premerge"]["evidence"] = [RUN]
                elif mutation == "wrong_base":
                    policy["review"]["base_sha"] = BASE
                elif mutation == "wrong_head":
                    policy["review"]["head_sha"] = "9"*40
                elif mutation == "wrong_merge":
                    api.merge_parents = [{"sha": BASE}, {"sha": CANDIDATE}]
                elif mutation == "no_association":
                    fresh["pull_requests"] = []
                elif mutation == "rerun":
                    fresh["run_attempt"] = 2
                elif mutation == "wrong_tree":
                    request = api.request
                    def different_tree(method, path, body=None):
                        result = request(method, path, body)
                        if method == "GET" and path.endswith("/git/commits/" + NEW_MERGE):
                            return {**result, "tree": {"sha": "9"*40}}
                        return result
                    api.request = different_tree
                if mutation == "forged_archive":
                    ledger, handoff = session.finish(api, s, "integrated", "Recovery", policy=policy)
                    handoff["history"][-1]["handoff"]["evidence"].append(
                        RUN.replace("/123/", "/999/"))
                    for apply in (False, True):
                        with self.assertRaisesRegex(ValueError, "differs from reviewed proof"):
                            session.save(api, s, ledger, handoff, apply, issue=247, policy=policy)
                else:
                    with self.assertRaises(ValueError):
                        session.finish(api, s, "integrated", "Recovery", policy=policy)
                self.assertEqual(s, snapshot)
                self.assertEqual(api.writes, [])

    def test_staged_reclaim_preserves_original_fix_and_slot(self):
        api,s=self.setup_case(True)
        old=copy.deepcopy(s["handoff"]["history"])
        self.move_base(api)
        ledger,handoff=session.claim(api,s,247,["test"],"refresh staged")
        self.assertEqual(handoff["active"]["fix_sha"],FIX)
        self.assertEqual(handoff["active"]["version"],"v1.0.6.1")
        self.assertEqual(handoff["active"]["evidence"],[])
        self.assertEqual(handoff["history"],old)
        self.assertEqual(ledger["issues"][0]["state"],"in_progress")

    def test_changed_head_missing_fix_refuses_refresh(self):
        api,s=self.setup_case()
        api.pr["head"]["sha"]="6"*40
        before=copy.deepcopy(s)
        with self.assertRaisesRegex(ValueError,"ancestor"):
            session.advance(api,s,"refresh",refresh=True)
        self.assertEqual(s,before)
        self.assertEqual(api.writes,[])

    def test_legacy_active_without_pins_remains_readable_but_cannot_stage(self):
        api,s=self.setup_case()
        for key in session.PIN_KEYS:
            s["handoff"]["active"].pop(key)
        session.validate_handoff(s["handoff"],s["ledger"])
        self.assertEqual(session.inspect(api,s)["status"],"stale_integration_evidence")
        with self.assertRaisesRegex(ValueError,"unpinned"):
            session.finish(api,s,"staged","old")
        ledger,handoff=session.advance(api,s,"refresh",refresh=True)
        self.assertEqual(handoff["active"]["fix_sha"],FIX)

    def test_base_changes_during_run_read_cannot_advance(self):
        api,s=self.setup_case()
        original=api.request
        def request(method,path,body=None):
            result=original(method,path,body)
            if "/actions/runs/123/attempts/1" in path:
                self.move_base(api)
            return result
        api.request=request
        before=copy.deepcopy(s)
        with self.assertRaisesRegex(ValueError,"Stale"):
            session.finish(api,s,"staged","race")
        self.assertEqual(s,before)
        self.assertEqual(api.writes,[])

    def test_unrelated_installed_state_is_not_product_base(self):
        api,s=self.setup_case()
        s["ref"]="7"*40
        self.assertEqual(session.inspect(api,s)["status"],"resume")


    def test_archived_run_cannot_be_relabelled_or_rerun(self):
        api,s=self.setup_case()
        self.move_base(api)
        s["ledger"],s["handoff"]=session.advance(api,s,"refresh",refresh=True)
        api.pre_run.update(run_attempt=2,pull_requests=[
            {"number":8,"head":{"sha":CANDIDATE},"base":{"sha":NEW_BASE}}])
        before=copy.deepcopy(s)
        with self.assertRaisesRegex(ValueError,"Archived run"):
            session.advance(api,s,"rerun old",evidence=[RUN.replace("/attempts/1","/attempts/2")])
        self.assertEqual(s,before)
        self.assertEqual(api.writes,[])

    def test_staged_plan_rechecked_before_write_and_ref_publish(self):
        for during_objects in (False,True):
            api,s=self.setup_case()
            ledger,handoff=session.finish(api,s,"staged","stage")
            before=copy.deepcopy(s)
            if during_objects:
                original=api.request
                def request(method,path,body=None):
                    result=original(method,path,body)
                    if method=="POST" and path.endswith("/git/commits"):
                        self.move_base(api)
                    return result
                api.request=request
            else:
                self.move_base(api)
            with self.assertRaisesRegex(ValueError,"Stale"):
                session.save(api,s,ledger,handoff,apply=True)
            self.assertEqual(s,before)
            self.assertFalse(any(method=="PATCH" for method,_,_ in api.writes))

    def test_real_git_other_merge_preserves_fix_but_invalidates_integration(self):
        from test_merge_history import MergeHistoryTests
        git=MergeHistoryTests()
        git.setUp()
        self.addCleanup(git.doCleanups)
        old_base=git.base
        git.git("checkout","-b","agent-b")
        fix=git.commit_file("b.txt","B\n","agent B")
        git.git("checkout","-b","old-merge",old_base)
        git.git("merge","--no-ff","-m","old proposal",fix)
        old_merge=git.git("rev-parse","HEAD")
        git.git("checkout","-b","agent-a",old_base)
        a=git.commit_file("a.txt","A\n","agent A")
        git.git("checkout","target")
        git.git("merge","--no-ff","-m","integrate A",a)
        new_base=git.git("rev-parse","HEAD")
        git.git("checkout","-b","new-merge",new_base)
        git.git("merge","--no-ff","-m","new proposal B",fix)
        new_merge=git.git("rev-parse","HEAD")
        api,s=Fake(),state()
        api.product=old_base
        api.pr["head"]["sha"]=fix
        api.pr["base"]["sha"]=old_base
        api.pr["merge_commit_sha"]=old_merge
        api.pre_run.update(head_sha=old_merge,pull_requests=[])
        original=api.request
        def request(method,path,body=None):
            if method=="GET" and "/git/commits/" in path:
                sha=path.rsplit("/",1)[1]
                return {"sha":sha,"parents":[{"sha":p} for p in git.git("show","-s","--format=%P",sha).split()]}
            if method=="GET" and "/compare/" in path:
                first,last=path.rsplit("/",1)[1].split("...")
                ancestor=git.git("merge-base",first,last)
                return {"status":"ahead" if ancestor==first else "diverged",
                        "merge_base_commit":{"sha":ancestor}}
            return original(method,path,body)
        api.request=request
        s["ledger"],s["handoff"]=session.claim(api,s,247,["test"],"Fix")
        for kw in ({"fix":fix,"candidate":fix,"pr":8},{"evidence":[RUN]},{}):
            s["ledger"],s["handoff"]=session.advance(api,s,"next",**kw)
        api.product=new_base
        api.pr["base"]["sha"]=new_base
        api.pr["merge_commit_sha"]=new_merge
        self.assertEqual(session.inspect(api,s)["status"],"stale_integration_evidence")
        s["ledger"],s["handoff"]=session.advance(api,s,"refresh",refresh=True)
        self.assertEqual(s["handoff"]["active"]["fix_sha"],fix)
        self.assertEqual(s["handoff"]["active"]["integration_merge_sha"],new_merge)
        self.assertEqual(s["handoff"]["history"][-1]["handoff"]["integration_merge_sha"],old_merge)
        self.assertEqual(git.git("show",new_merge+":a.txt"),"A")
        self.assertEqual(git.git("show",new_merge+":b.txt"),"B")
        self.assertEqual(api.writes,[])


    def test_earlier_premerge_run_rerun_during_later_run_rejected(self):
        api,s=self.setup_case()
        s["ledger"],s["handoff"]=session.advance(api,s,"refresh",refresh=True)
        original=api.request
        second={**api.pre_run,"id":125}
        def request(method,path,body=None):
            if "/actions/runs/125" in path:
                api.pre_run["run_attempt"]=2
                return second
            return original(method,path,body)
        api.request=request
        before=copy.deepcopy(s)
        with self.assertRaisesRegex(ValueError,"stale"):
            session.advance(api,s,"two runs",evidence=[RUN,NEW_RUN])
        self.assertEqual(s,before)
        self.assertEqual(api.writes,[])

    def test_unpinned_empty_validate_inspection_requires_refresh(self):
        api,s=Fake(),state()
        s["ledger"],s["handoff"]=session.claim(api,s,247,["test"],"Fix")
        self.assertEqual(session.inspect(api,s)["status"],"resume")
        s["ledger"],s["handoff"]=session.advance(api,s,"candidate",fix=FIX,candidate=CANDIDATE,pr=8)
        for key in session.PIN_KEYS:
            s["handoff"]["active"].pop(key)
        before=copy.deepcopy(s)
        self.assertEqual(session.inspect(api,s)["status"],"stale_integration_evidence")
        self.assertEqual(s,before)
        self.assertEqual(api.writes,[])
