"""Post-merge acceptance through both existing session entry points."""
import copy
import json
import unittest
from tools import session
from test_session import Fake, state, post_policy, FIX, CANDIDATE, NEXT, HEAD, BASE, RUN, POST_RUN

class IntegrationTests(unittest.TestCase):
    def setup_case(self, staged):
        api, s = Fake(), state()
        s["ledger"],s["handoff"] = session.claim(api,s,247,["test"],"Fix")
        for kwargs in ({"fix":FIX,"candidate":CANDIDATE,"pr":8},{"evidence":[RUN]},{}):
            s["ledger"],s["handoff"] = session.advance(api,s,"next",**kwargs)
        if staged:
            s["ledger"],s["handoff"] = session.finish(api,s,"staged","Stage")
        api.pr.update(state="closed",merged=True,merge_commit_sha=NEXT)
        api.product=NEXT
        return api,s,post_policy(s)

    def integrate(self, api, s, staged, policy):
        if staged:
            return session.reconcile(api,s,247,"Owner reviewed checkout and criteria",policy=policy)
        return session.finish(api,s,"integrated","Owner reviewed checkout and criteria",policy=policy)

    def test_both_paths_require_policy_and_preserve_original_state(self):
        for staged in (False,True):
            api,s,p=self.setup_case(staged)
            before=copy.deepcopy(s)
            with self.assertRaisesRegex(ValueError,"post-merge policy"):
                self.integrate(api,s,staged,None)
            self.assertEqual(s,before)
            self.assertEqual(api.writes,[])

    def test_both_paths_archive_post_merge_evidence_and_exact_mapping(self):
        for staged in (False,True):
            api,s,p=self.setup_case(staged)
            api.product=HEAD  # later descendant, not the actual merged SHA
            before=copy.deepcopy(s)
            ledger,handoff=self.integrate(api,s,staged,p)
            self.assertEqual(ledger["issues"][0]["state"],"integrated")
            self.assertEqual(handoff["history"][-1]["merged_sha"],NEXT)
            self.assertEqual(handoff["history"][-1]["handoff"]["evidence"],[RUN,POST_RUN])
            self.assertEqual(json.loads(handoff["history"][-1]["decision"].split("Post-merge policy: ")[1]),p)
            self.assertEqual(handoff["history"][:len(before["handoff"]["history"])],before["handoff"]["history"])
            session.validate_handoff(handoff,ledger)
            self.assertEqual(session.save(api,s,ledger,handoff)["status"],"planned")
            self.assertEqual(s,before)
            self.assertEqual(api.writes,[])

    def test_invalid_run_job_or_step_rejected_on_both_paths(self):
        cases=[
            lambda a,p:a.run.update(head_sha=CANDIDATE),
            lambda a,p:a.run.update(run_attempt=2),
            lambda a,p:a.run.update(conclusion="failure"),
            lambda a,p:a.run.update(conclusion="cancelled"),
            lambda a,p:a.run.update(conclusion="skipped"),
            lambda a,p:a.run.update(status="in_progress"),
            lambda a,p:a.run.update(repository={"id":43}),
            lambda a,p:a.run.update(head_repository={"id":43}),
            lambda a,p:a.run.update(workflow_id=53),
            lambda a,p:a.run.update(event="pull_request"),
            lambda a,p:a.run.update(head_branch="other"),
            lambda a,p:a.jobs.clear(),
            lambda a,p:a.jobs[0].update(head_sha=CANDIDATE),
            lambda a,p:a.jobs[0].update(run_id=999),
            lambda a,p:a.jobs[0].update(run_attempt=2),
            lambda a,p:a.jobs[0].update(conclusion="skipped"),
            lambda a,p:a.jobs[0]["steps"][0].update(conclusion="skipped"),
            lambda a,p:a.jobs[0]["steps"].clear(),
        ]
        for staged in (False,True):
            for index,mutate in enumerate(cases):
                with self.subTest(staged=staged,case=index):
                    api,s,p=self.setup_case(staged)
                    before=copy.deepcopy(s)
                    mutate(api,p)
                    with self.assertRaises(ValueError):
                        self.integrate(api,s,staged,p)
                    self.assertEqual(s,before)
                    self.assertEqual(api.writes,[])

    def test_wrong_scope_or_merge_history_rejected(self):
        cases=[
            lambda a,p:p.update(merge_sha=CANDIDATE),
            lambda a,p:p.update(installed_sha=CANDIDATE),
            lambda a,p:p.update(source_sha=CANDIDATE),
            lambda a,p:p["issues"][0].update(issue=248),
            lambda a,p:p["issues"][0].update(fix_sha=BASE),
            lambda a,p:p["issues"][0]["criteria"][0].update(text="different"),
            lambda a,p:p["issues"][0]["criteria"].clear(),
            lambda a,p:a.merge_parents.pop(),
            lambda a,p:a.pr.update(state="open"),
            lambda a,p:setattr(a,"product",BASE),
            lambda a,p:setattr(a,"ref",BASE),
        ]
        for staged in (False,True):
            for index,mutate in enumerate(cases):
                with self.subTest(staged=staged,case=index):
                    api,s,p=self.setup_case(staged)
                    before=copy.deepcopy(s)
                    mutate(api,p)
                    with self.assertRaises(ValueError):
                        self.integrate(api,s,staged,p)
                    self.assertEqual(s,before)
                    self.assertEqual(api.writes,[])

    def test_rerun_during_job_read_is_not_accepted(self):
        for staged in (False,True):
            api,s,p=self.setup_case(staged)
            original=api.request
            def changed(method,path,body=None):
                result=original(method,path,body)
                if path.endswith("/jobs?per_page=100"):
                    api.run["run_attempt"]=2
                return result
            api.request=changed
            with self.assertRaisesRegex(ValueError,"changed"):
                self.integrate(api,s,staged,p)
            self.assertEqual(api.writes,[])

    def test_dispatch_at_actual_revision_supported(self):
        api,s,p=self.setup_case(False)
        api.run["event"]="workflow_dispatch"
        ledger,_=self.integrate(api,s,False,p)
        self.assertEqual(ledger["issues"][0]["state"],"integrated")


    def test_earlier_mapped_run_rerun_during_later_mapping_rejected(self):
        for staged in (False,True):
            api,s,p=self.setup_case(staged)
            checks=p["issues"][0]["criteria"][0]["checks"]
            checks.append({**checks[0],"run":126})
            original=api.request
            second={**api.run,"id":126}
            def request(method,path,body=None):
                if "/actions/runs/126" in path:
                    if path.endswith("/jobs?per_page=100"):
                        api.run["run_attempt"]=2
                        return {"total_count":1,"jobs":[{**api.jobs[0],"run_id":126}]}
                    return second
                return original(method,path,body)
            api.request=request
            before=copy.deepcopy(s)
            with self.assertRaisesRegex(ValueError,"changed"):
                self.integrate(api,s,staged,p)
            self.assertEqual(s,before)
            self.assertEqual(api.writes,[])

    def test_actual_merge_must_match_pinned_preview_on_both_paths(self):
        from test_session import PROPOSED
        for staged in (False, True):
            for fault in ("wrong_tree", "missing_tree", "wrong_parents", "changed_at_final_read"):
                with self.subTest(staged=staged, fault=fault):
                    api,s,p=self.setup_case(staged)
                    before=copy.deepcopy(s)
                    original=api.request
                    reads=0
                    def request(method,path,body=None):
                        nonlocal reads
                        result=original(method,path,body)
                        if method=="GET" and path.endswith("/git/commits/"+PROPOSED):
                            reads+=1
                            if fault=="wrong_tree" or (fault=="changed_at_final_read" and reads>1):
                                return {**result,"tree":{"sha":BASE}}
                            if fault=="missing_tree":
                                return {**result,"tree":None}
                            if fault=="wrong_parents":
                                return {**result,"parents":[{"sha":BASE},{"sha":FIX}]}
                        return result
                    api.request=request
                    with self.assertRaises(ValueError):
                        self.integrate(api,s,staged,p)
                    self.assertEqual(s,before)
                    self.assertEqual(api.writes,[])

    def test_unpinned_or_wrong_base_requires_historical_reconciliation(self):
        for staged in (False, True):
            for bad_base in (None, FIX):
                api,s,p=self.setup_case(staged)
                active=s["handoff"]["history"][-1]["handoff"] if staged else s["handoff"]["active"]
                if bad_base is None:
                    active.pop("integration_base_sha")
                    active.pop("integration_merge_sha")
                else:
                    active["integration_base_sha"]=bad_base
                with self.assertRaisesRegex(ValueError,"historical reconciliation"):
                    self.integrate(api,s,staged,p)
                self.assertEqual(api.writes,[])
