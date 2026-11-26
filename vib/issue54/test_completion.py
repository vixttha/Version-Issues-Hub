"""Completion and gate rejection tests; synthetic GitHub responses, no network."""
import copy
import importlib.util
import json
import unittest
from unittest.mock import patch
import test_core as core
from tools import gate,session
from record import run_suite

def load(name):
    spec=importlib.util.spec_from_file_location("fixture_"+name,core.PRODUCT/("tests/test_"+name+".py"))
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
g=load("gate")
s=load("session")

class Gate(unittest.TestCase):
    def setUp(self):
        self.policy,self.state=g.fixture()
        self.api=g.Fake()
        p=patch.object(session,"load",return_value=self.state)
        p.start(); self.addCleanup(p.stop)
    def evaluate(self):
        return gate.evaluate(self.api,g.REPO,self.policy)
    def rejected(self):
        before=copy.deepcopy(self.state)
        with self.assertRaises(ValueError): self.evaluate()
        self.assertEqual(self.api.writes,[])
        self.assertEqual(self.state,before)
    def test_valid_control(self):
        result=self.evaluate()
        self.assertEqual(result["status"],"pass")
        self.assertFalse(result["published"])
        self.assertEqual(self.api.writes,[])
    def test_duplicate_check(self):
        self.api.checks.append(copy.deepcopy(self.api.checks[0]))
        self.rejected()
    def test_duplicate_job(self):
        self.api.jobs.append(copy.deepcopy(self.api.jobs[0]))
        self.rejected()
    def test_duplicate_step(self):
        self.api.jobs[0]["steps"]*=2
        self.rejected()
    def test_incomplete_check_collection(self):
        self.incomplete("check_runs")
    def test_incomplete_job_collection(self):
        self.incomplete("jobs")
    def incomplete(self,key):
        original=self.api.request
        def request(method,path,body=None):
            result=original(method,path,body)
            if key in result:
                result=copy.deepcopy(result)
                result["total_count"]+=1
            return result
        with patch.object(self.api,"request",side_effect=request): self.rejected()
    def test_latest_attempt_only_stale(self):
        original=self.api.request
        def request(method,path,body=None):
            result=original(method,path,body)
            if path.endswith("/actions/runs/123"):
                return dict(result,run_attempt=2)
            return result
        with patch.object(self.api,"request",side_effect=request): self.rejected()
    def test_exact_attempt_only_failed(self):
        original=self.api.request
        def request(method,path,body=None):
            result=original(method,path,body)
            if path.endswith("/attempts/1"):
                return dict(result,conclusion="failure")
            return result
        with patch.object(self.api,"request",side_effect=request): self.rejected()
    def test_wrong_merge_base(self):
        original=self.api.request
        def request(method,path,body=None):
            result=original(method,path,body)
            if "/compare/" in path:
                return dict(result,merge_base_commit={"sha":g.BASE})
            return result
        with patch.object(self.api,"request",side_effect=request): self.rejected()

def change_case(path,value):
    def test(self):
        target=self.api
        for part in path[:-1]:
            target=getattr(target,part) if target is self.api else target[part]
        if target is self.api: setattr(target,path[-1],value)
        else: target[path[-1]]=value
        self.rejected()
    return test
for name,path,value in json.loads(r'''[["check_wrong_sha",["checks",0,"head_sha"],"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"],["check_pending",["checks",0,"status"],"in_progress"],["check_neutral",["checks",0,"conclusion"],"neutral"],["check_missing_app",["checks",0,"app"],null],["check_missing_slug",["checks",0,"app","slug"],null],["check_wrong_name",["checks",0,"name"],"unrelated"],["check_wrong_details",["checks",0,"details_url"],"https://github.com/example/existing/actions/runs/123/attempts/2"],["check_bool_id",["checks",0,"id"],true],["run_wrong_id",["run","id"],124],["run_wrong_repo",["run","repository","id"],43],["run_wrong_workflow",["run","workflow_id"],53],["run_wrong_head",["run","head_sha"],"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"],["run_cancelled",["run","conclusion"],"cancelled"],["run_pending",["run","status"],"in_progress"],["job_wrong_name",["jobs",0,"name"],"different"],["job_pending",["jobs",0,"status"],"in_progress"],["job_cancelled",["jobs",0,"conclusion"],"cancelled"],["job_bool_id",["jobs",0,"id"],true],["step_wrong_name",["jobs",0,"steps",0,"name"],"different"],["step_pending",["jobs",0,"steps",0,"status"],"in_progress"],["step_neutral",["jobs",0,"steps",0,"conclusion"],"neutral"],["step_missing",["jobs",0,"steps"],[]],["pr_wrong_number",["pr","number"],9],["pr_wrong_target",["pr","base","ref"],"elsewhere"],["pr_wrong_base_repo",["pr","base","repo","id"],43],["pr_wrong_head_repo",["pr","head","repo","id"],43],["pr_wrong_merge",["pr","merge_commit_sha"],"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"],["pr_reversed_parents",["parents"],["dddddddddddddddddddddddddddddddddddddddd","cccccccccccccccccccccccccccccccccccccccc"]],["pr_extra_parent",["parents"],["cccccccccccccccccccccccccccccccccccccccc","dddddddddddddddddddddddddddddddddddddddd","aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"]]]'''):
    setattr(Gate,"test_"+name,change_case(path,value))

class Completion(unittest.TestCase):
    def setUp(self):
        self.api=s.Fake()
        self.state=s.state()
        self.assign(session.claim(self.api,self.state,247,["test"],"Fix"))
    def assign(self,result):
        self.state["ledger"],self.state["handoff"]=result
    def advance(self,**kw):
        self.assign(session.advance(self.api,self.state,"next",**kw))
    def head(self):
        self.advance(fix=s.FIX,candidate=s.CANDIDATE,pr=8)
        self.advance(evidence=[s.RUN])
        self.advance()
    def staged(self):
        self.head()
        self.assign(session.finish(self.api,self.state,"staged","Owner decision"))
    def reject(self,call):
        before=copy.deepcopy(self.state)
        with self.assertRaises(ValueError): call()
        self.assertEqual(self.state,before)
        self.assertEqual(self.api.writes,[])
    def finish(self,disposition="integrated",decision="Owner decision"):
        return session.finish(self.api,self.state,disposition,decision)
    def reconcile(self,number=247,decision="Owner decision"):
        return session.reconcile(self.api,self.state,number,decision)
    def test_finish_worker(self): self.reject(self.finish)
    def test_finish_validate(self):
        self.advance(fix=s.FIX,candidate=s.CANDIDATE,pr=8)
        self.reject(self.finish)
    def test_finish_auditor(self):
        self.advance(fix=s.FIX,candidate=s.CANDIDATE,pr=8)
        self.advance(evidence=[s.RUN])
        self.reject(self.finish)
    def test_head_no_evidence(self):
        self.advance(return_to_head=True)
        self.reject(self.finish)
    def test_head_invalid_disposition(self):
        self.head(); self.reject(lambda:self.finish("verified"))
    def test_head_blank_decision(self):
        self.head(); self.reject(lambda:self.finish("blocked"," "))
    def test_stage_closed(self):
        self.head(); self.api.pr["state"]="closed"
        self.reject(lambda:self.finish("staged"))
    def test_stage_merged(self):
        self.head(); self.api.pr["merged"]=True
        self.reject(lambda:self.finish("staged"))
    def test_merge_invalid_sha(self):
        self.head(); self.api.pr.update(state="closed",merged=True,merge_commit_sha="short")
        self.reject(self.finish)
    def test_merge_nonbool(self):
        self.head(); self.api.pr.update(state="closed",merged=1)
        self.reject(self.finish)
    def test_reconcile_active(self): self.reject(self.reconcile)
    def test_reconcile_wrong_issue(self):
        self.staged(); self.reject(lambda:self.reconcile(248))
    def test_reconcile_no_history(self):
        self.staged(); self.state["handoff"]["history"]=[]
        self.reject(self.reconcile)
    def test_reconcile_invalid_sha(self):
        self.staged(); self.api.pr.update(state="closed",merged=True,merge_commit_sha="short")
        self.reject(self.reconcile)
    def test_reconcile_blank_decision(self):
        self.staged(); self.api.pr.update(state="closed",merged=True)
        self.reject(lambda:self.reconcile(decision=" "))
    def test_reconcile_wrong_repo(self):
        self.staged(); self.api.pr.update(state="closed",merged=True)
        self.api.pr["base"]["repo"]["id"]=43
        self.reject(self.reconcile)
    def test_reconcile_no_double_completion(self):
        self.staged(); self.api.pr.update(state="closed",merged=True)
        prior=copy.deepcopy(self.state["handoff"]["history"])
        self.assign(self.reconcile())
        self.assertEqual(self.state["handoff"]["history"][:-1],prior)
        self.assertEqual(self.state["ledger"]["issues"][0]["state"],"integrated")
        self.reject(self.reconcile)
    def test_rework_clears_all_candidate_fields(self):
        self.head(); self.advance(rework=True)
        active=self.state["handoff"]["active"]
        self.assertEqual([active[x] for x in ("fix_sha","candidate_sha","pull_request","evidence")],[None,None,None,[]])
        self.assertEqual(self.state["handoff"]["history"][0]["handoff"]["evidence"],[s.RUN])
        self.assertEqual(self.api.writes,[])
    def test_rework_merged(self):
        self.head(); self.api.pr.update(state="closed",merged=True)
        self.reject(lambda:self.advance(rework=True))
    def test_conflicting_transition(self):
        self.head(); self.reject(lambda:self.advance(rework=True,return_to_head=True))
    def test_head_no_automatic_advance(self):
        self.head(); self.reject(self.advance)
    def test_claim_changed_criteria(self):
        self.reject(lambda:session.claim(self.api,self.state,247,["changed"],"Retry"))

if __name__=="__main__":
    loader=unittest.defaultTestLoader
    run_suite(unittest.TestSuite([loader.loadTestsFromTestCase(Gate),loader.loadTestsFromTestCase(Completion)]),60,"completion")
