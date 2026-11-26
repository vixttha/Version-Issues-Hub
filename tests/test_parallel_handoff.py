"""Parallel handoff candidate: independent issue loops, legacy compatibility."""
import copy
import unittest
from unittest.mock import patch
from tools import session, lifecycle, standard, gate
from test_session import Fake, state, post_policy, FIX, FIX2, CANDIDATE, NEXT, RUN
from test_gate import fixture, Fake as GateFake, REPO, PREFIX, HEAD, BASE

A,B=247,248

class ParallelTests(unittest.TestCase):
    def apply(self,s,result,issue):
        ledger,handoff=result
        before=copy.deepcopy(s)
        self.assertIn(session.save(self.api,s,ledger,handoff,issue=issue)["status"],("planned","unchanged"))
        self.assertEqual(s,before)
        s["ledger"],s["handoff"]=result

    def setup_two(self):
        self.api=Fake()
        s=state()
        s["parallel_supported"]=True
        s["manifest"]["enforcement"]="disabled"
        self.apply(s,session.claim(self.api,s,A,["A"],"first"),A)
        original=copy.deepcopy(s["handoff"]["active"])
        self.apply(s,session.claim(self.api,s,B,["B"],"second",parallel=True),B)
        self.assertEqual(s["handoff"]["schema_version"],2)
        self.assertEqual(session.select_active(s["handoff"],A),original)
        return s

    def test_parallel_opt_in_keeps_legacy_solo_and_existing_assignment(self):
        s=self.setup_two()
        self.assertEqual([a["version"] for a in session.active_rows(s["handoff"])],["v1.0.6.1","v1.0.6.2"])
        self.assertEqual(session.inspect(self.api,s)["status"],"issue_selection_required")
        self.assertEqual(session.inspect(self.api,s)["active_issues"],[A,B])
        self.assertEqual(session.inspect(self.api,s,A)["active"]["issue"],A)
        self.assertEqual(session.inspect(self.api,s,B)["active"]["issue"],B)
        self.assertEqual(session.claim(self.api,s,A,["A"],"resume"),(s["ledger"],s["handoff"]))
        self.assertEqual(session.inspect(self.api,s,249)["status"],"head_scope_required")

    def test_independent_transitions_and_completion(self):
        s=self.setup_two()
        first=copy.deepcopy(session.select_active(s["handoff"],A))
        for kw in ({"fix":FIX2,"candidate":CANDIDATE,"pr":8},{"evidence":[RUN]},{},{"refresh":True},{"evidence":[RUN]},{}):
            self.apply(s,session.advance(self.api,s,"second",issue=B,**kw),B)
            self.assertEqual(session.select_active(s["handoff"],A),first)
        self.apply(s,session.finish(self.api,s,"staged","stage B",issue=B),B)
        self.assertEqual(session.active_rows(s["handoff"]),[first])
        self.assertEqual(session.inspect(self.api,s,B)["status"],"staged")
        self.apply(s,session.advance(self.api,s,"block A",issue=A,return_to_head=True),A)
        self.apply(s,session.finish(self.api,s,"blocked","block A",issue=A),A)
        self.assertEqual(session.active_rows(s["handoff"]),[])
        self.assertEqual([r["state"] for r in s["ledger"]["issues"]],["blocked","staged"])
        self.assertEqual([r["handoff"]["issue"] for r in s["handoff"]["history"]],[B,B,A])

    def test_explicit_selection_even_when_only_one_parallel_issue(self):
        s=self.setup_two()
        before=copy.deepcopy(s)
        for issue, diagnostic in ((None, "explicit"), (999, "does not own")):
            with self.assertRaisesRegex(ValueError, diagnostic):
                session.advance(self.api,s,"wrong",issue=issue,return_to_head=True)
        self.assertEqual(s,before)
        for issue in (A,B):
            self.apply(s,session.advance(self.api,s,"head",issue=issue,return_to_head=True),issue)
        at_head=copy.deepcopy(s)
        for issue, diagnostic in ((None, "explicit"), (999, "does not own")):
            with self.assertRaisesRegex(ValueError, diagnostic):
                session.finish(self.api,s,"blocked","wrong",issue=issue)
        self.assertEqual(s,at_head)
        self.apply(s,session.finish(self.api,s,"blocked","B",issue=B),B)
        with self.assertRaisesRegex(ValueError,"explicit"):
            session.advance(self.api,s,"wrong",return_to_head=True)
        self.assertEqual(self.api.writes,[])

    def test_parallel_tampering_and_downgrade_refused_before_write(self):
        s=self.setup_two()
        ledger,handoff=session.advance(self.api,s,"head",issue=B,return_to_head=True)
        session.select_active(handoff,A)["next_action"]="corrupted A"
        with self.assertRaisesRegex(ValueError,"scope violation"):
            session.save(self.api,s,ledger,handoff,True,issue=B)
        broken=copy.deepcopy(s["handoff"])
        broken["active"].append(copy.deepcopy(broken["active"][0]))
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            session.validate_handoff(broken,s["ledger"])
        broken=copy.deepcopy(s["handoff"])
        broken["active"].pop()
        with self.assertRaisesRegex(ValueError,"unmatched"):
            session.validate_handoff(broken,s["ledger"])
        self.apply(s,session.advance(self.api,s,"head",issue=B,return_to_head=True),B)
        self.apply(s,session.finish(self.api,s,"blocked","B",issue=B),B)
        broken={**s["handoff"],"schema_version":1,"active":s["handoff"]["active"][0]}
        with self.assertRaisesRegex(ValueError,"downgrade"):
            session.save(self.api,s,s["ledger"],broken,True,issue=A)
        self.assertEqual(self.api.writes,[])

    def test_stale_writer_rejected_and_fresh_claim_keeps_distinct_versions(self):
        s=self.setup_two()
        result=session.claim(self.api,s,249,["C"],"third")
        self.api.ref=NEXT
        with self.assertRaisesRegex(ValueError,"advanced"):
            session.save(self.api,s,*result,True,issue=249)
        self.assertEqual(self.api.writes,[])
        # Model the competing committed claim, then reload/replan the loser.
        self.apply(s,session.claim(self.api,s,250,["D"],"fourth"),250)
        self.apply(s,session.claim(self.api,s,249,["C"],"third"),249)
        self.assertEqual([r["version"] for r in s["ledger"]["issues"]],["v1.0.6.1","v1.0.6.2","v1.0.6.3","v1.0.6.4"])
        self.assertEqual(len(session.active_rows(s["handoff"])),4)

    def test_one_hundred_issue_records_without_global_slot(self):
        s=self.setup_two()
        for issue in range(249,347):
            self.apply(s,session.claim(self.api,s,issue,["test"],"work"),issue)
        self.assertEqual(len(session.active_rows(s["handoff"])),100)
        self.assertEqual(len(set(r["version"] for r in s["ledger"]["issues"])),100)
        old=copy.deepcopy(s["handoff"])
        self.apply(s,session.advance(self.api,s,"head",issue=300,return_to_head=True),300)
        self.apply(s,session.finish(self.api,s,"blocked","one blocker",issue=300),300)
        self.assertEqual(session.active_rows(s["handoff"]),[a for a in old["active"] if a["issue"]!=300])
        self.assertEqual(self.api.writes,[])

    def test_parallel_reconcile_preserves_other_active(self):
        s=self.setup_two()
        for kw in ({"fix":FIX,"candidate":CANDIDATE,"pr":8},{"evidence":[RUN]},{}):
            self.apply(s,session.advance(self.api,s,"A",issue=A,**kw),A)
        self.apply(s,session.finish(self.api,s,"staged","A",issue=A),A)
        other=copy.deepcopy(session.select_active(s["handoff"],B))
        self.api.pr.update(state="closed",merged=True,merge_commit_sha=NEXT)
        self.api.product=NEXT
        legacy=copy.deepcopy(s)
        legacy["handoff"]["active"]=None
        policy=post_policy(legacy,A)
        self.apply(s,session.reconcile(self.api,s,A,"integrate A",policy=policy),A)
        self.assertEqual(session.select_active(s["handoff"],B),other)
        self.assertEqual(s["ledger"]["issues"][0]["state"],"integrated")

    def test_parallel_claim_refuses_enabled_gate_and_lifecycle_busy(self):
        self.api=Fake()
        s=state()
        s["manifest"]["enforcement"]="enabled"
        s["parallel_supported"]=True
        with self.assertRaisesRegex(ValueError,"disabled"):
            session.claim(self.api,s,A,["A"],"A",parallel=True)
        s=self.setup_two()
        s["manifest"]["enforcement"]="disabled"
        with patch.object(session,"load",return_value=s), self.assertRaisesRegex(ValueError,"active work"):
            lifecycle.idle_state(self.api,"example/existing",s["ref"])

    def test_standard_unrelated_parallel_active_does_not_block_same_pr_does(self):
        p,s=fixture()
        p.pop("publisher_app_id")
        for row in p["issues"]:
            row["criteria"][0]["checks"]=[{"run":123,"attempt":1,"workflow_id":52,
                                         "job_name":"product-test","steps":["Run acceptance"]}]
        api=GateFake()
        api.run.update(head_sha=HEAD,event="pull_request",pull_requests=[
            {"number":8,"head":{"sha":HEAD},"base":{"sha":BASE}}])
        original=api.request
        api.request=lambda method,path,body=None: (
            {"id":42,"full_name":REPO,"private":False} if method=="GET" and path==PREFIX
            else original(method,path,body))
        s["ledger"]["issues"].append({"issue":249,"version":"v1.0.6.3","state":"in_progress","acceptance":["Other"]})
        other={**s["handoff"]["history"][0]["handoff"],"issue":249,"version":"v1.0.6.3","pull_request":9}
        s["handoff"].update(schema_version=2,active=[other])
        with patch.object(session,"load",return_value=s):
            self.assertEqual(standard.evaluate(api,REPO,p)["status"],"review_required")
            other["pull_request"]=8
            with self.assertRaisesRegex(ValueError,"relevant active"):
                standard.evaluate(api,REPO,p)
            p["publisher_app_id"]=88
            # Exercise optional gate's scope check independently of policy shape.
            with self.assertRaisesRegex(ValueError,"not qualified"):
                gate.evaluate_scope(api,REPO,p,lambda _:None,lambda *args:None)
        self.assertEqual(api.writes,[])


    def test_legacy_package_cannot_be_promoted_by_newer_cli(self):
        self.api=Fake()
        s=state()
        s["manifest"]["enforcement"]="disabled"
        for files in ({}, {"tools/session.py":"# PARALLEL_HANDOFF_SCHEMA = 2\n"},
                      {"tools/session.py":"PARALLEL_HANDOFF_SCHEMA = True\n"}):
            self.assertFalse(session.supports_parallel_package(files))
        self.assertTrue(session.supports_parallel_package({"tools/session.py":"PARALLEL_HANDOFF_SCHEMA = 2\n"}))
        self.assertFalse(session.supports_parallel_package({"tools/session.py":
                          "PARALLEL_HANDOFF_SCHEMA = 2\nPARALLEL_HANDOFF_SCHEMA = 1\n"}))
        before=copy.deepcopy(s)
        with self.assertRaisesRegex(ValueError,"upgrade"):
            session.claim(self.api,s,A,["A"],"A",parallel=True)
        self.assertEqual(s,before)
        self.assertEqual(self.api.writes,[])

    def test_parallel_idle_upgrade_refuses_incompatible_reader(self):
        from test_lifecycle import OLD, NEW, OLD_FILES, NEW_FILES
        s=state()
        s["handoff"].update(schema_version=2,active=[])
        s["manifest"].update(enforcement="disabled",source_sha=OLD)
        api=Fake()
        with patch.object(lifecycle,"idle_state",return_value=s), \
             patch.object(api,"request",return_value={"status":"ahead","merge_base_commit":{"sha":OLD}}), \
             patch.object(session.install,"source_files",side_effect=lambda api,sha:{OLD:OLD_FILES,NEW:NEW_FILES}[sha]):
            with self.assertRaisesRegex(ValueError,"lacks parallel"):
                lifecycle.upgrade(api,"example/existing",s["ref"],NEW)
        self.assertEqual(api.writes,[])

    def test_real_git_parallel_conflict_preserves_winner_and_reloaded_loser(self):
        import tempfile
        import json
        from pathlib import Path
        from test_lifecycle import GitApi, OLD_FILES, REPO as TARGET
        from tools import install

        class Remote(GitApi):
            def request(self,method,path,body=None):
                if method=="GET" and "/issues/" in path:
                    return {"number":int(path.rsplit("/",1)[1]),"state":"open"}
                return super().request(method,path,body)

        with tempfile.TemporaryDirectory() as tmp:
            api=Remote(tmp)
            package={**OLD_FILES,"tools/session.py":Path(session.__file__).read_text(encoding="utf-8")}
            manifest={**api.manifest,"package_files_sha256":lifecycle.digest_files(package)}
            tree=api.tree({"tools/session.py":package["tools/session.py"],
                           "vib-install.json":install.render(manifest)},api.git("rev-parse",api.old+"^{tree}"))
            pin=api.commit(tree,[api.old])
            api.ref(install.BRANCH,pin)
            with patch.object(install,"source_files",return_value=package), \
                 patch.object(install,"read_text",side_effect=lambda api,prefix,path,ref:api.read(ref,path)):
                s=session.load(api,TARGET,pin)
                self.assertTrue(s["parallel_supported"])
                initial_history=copy.deepcopy(s["handoff"]["history"])
                first=session.claim(api,s,A,["A"],"first")
                one=session.save(api,s,*first,True,issue=A)["installed_sha"]
                s=session.load(api,TARGET,one)
                a=copy.deepcopy(s["handoff"]["active"])
                left=session.claim(api,s,B,["B"],"left",parallel=True)
                right=session.claim(api,s,249,["C"],"right",parallel=True)
                original=api.request
                winner=[]
                def race(method,path,body=None):
                    if method=="PATCH" and not winner:
                        api.request=original
                        winner.append(session.save(api,s,*right,True,issue=249)["installed_sha"])
                    return original(method,path,body)
                api.request=race
                with self.assertRaises(install.ApiError) as exc:
                    session.save(api,s,*left,True,issue=B)
                self.assertEqual(exc.exception.status,422)
                fresh=session.load(api,TARGET,winner[0])
                self.assertEqual(session.select_active(fresh["handoff"],A),a)
                self.assertEqual([x["issue"] for x in fresh["handoff"]["active"]],[A,249])
                left=session.claim(api,fresh,B,["B"],"reload left")
                final=session.save(api,fresh,*left,True,issue=B)["installed_sha"]
                latest=session.load(api,TARGET,final)
                self.assertEqual([x["issue"] for x in latest["handoff"]["active"]],[A,B,249])
                self.assertEqual(len(set(x["version"] for x in latest["ledger"]["issues"])),4)
                self.assertEqual(latest["handoff"]["history"],initial_history)
                self.assertEqual(session.select_active(latest["handoff"],249),
                                 session.select_active(fresh["handoff"],249))
                self.assertEqual(api.ref("main"),api.product)
                self.assertEqual(api.read(final,"notes/custom.md"),"keep me\n")
                self.assertEqual(sum(m=="PATCH" for m,_,_ in api.writes),4)
