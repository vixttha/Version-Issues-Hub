"""Qualification only: production session functions over a locked in-memory Git API.

Objects and ancestry are simulated; no remote API, actual LLM, or production write.
Real Git regression tests in test_contention_recovery and test_lifecycle remain required.
"""
import copy
import hashlib
import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from tools import checkpoint, install, lifecycle, session
from test_lifecycle import GitApi, OLD, NEW, OLD_FILES, NEW_FILES, REPO, PREFIX

PACKAGE = {"tools/session.py": "PARALLEL_HANDOFF_SCHEMA = 2\n"}
RETIRED = {"issue": 7, "version": "v1.0.5.1", "state": "retired", "acceptance": ["preserve"]}


def oid(value):
    return hashlib.sha1(json.dumps(value, sort_keys=True).encode()).hexdigest()


class MemoryGit:
    def __init__(self):
        self.lock = threading.RLock()
        self.trees, self.commits = {}, {}
        self.product = self.commit(self.tree({"product.txt": "unchanged"}), [])
        manifest = {"schema_version":1, "package":install.BRANCH, "source_repository":install.SOURCE,
                    "source_sha":OLD, "target_repository":REPO,"target_repository_id":42,
                    "product_branch":"main", "product_baseline_sha":self.product,
                    "install_branch":install.BRANCH,"baseline_version":"v1.0.6",
                    "target_version":"v1.0.7","enforcement":"disabled",
                    "package_files_sha256":lifecycle.digest_files(PACKAGE)}
        self.initial = self.commit(self.tree({**PACKAGE, "vib-install.json":install.render(manifest),
             session.LEDGER:install.render({"schema_version":1,"repository":REPO,"issues":[RETIRED]}),
             session.HANDOFF:install.render({"schema_version":2,"active":[],"history":[]}),
             "notes/custom.md":"keep me"}), [self.product])
        self.head = self.initial
        self.published, self.rejected = [], 0

    def tree(self, files):
        sha=oid(files)
        self.trees[sha]=copy.deepcopy(files)
        return sha

    def commit(self, tree, parents):
        sha=oid([tree,parents])
        self.commits[sha]={"sha":sha,"tree":{"sha":tree},"parents":[{"sha":p} for p in parents]}
        return sha

    def read(self, rev, path):
        with self.lock:
            return self.trees[self.commits[rev]["tree"]["sha"]][path]

    def distance(self, ancestor, rev):
        count=0
        while rev != ancestor:
            parents=self.commits[rev]["parents"]
            if len(parents)!=1:
                return None
            rev=parents[0]["sha"]
            count+=1
        return count

    def request(self, method, path, body=None):
        with self.lock:
            if method=="GET" and path==PREFIX:
                return {"id":42,"full_name":REPO,"private":False,"default_branch":"main"}
            if method=="GET" and path.startswith(PREFIX+"/git/ref/heads/"):
                name=path.split("/heads/",1)[1]
                return {"ref":"refs/heads/"+name,"object":{"type":"commit","sha":self.product if name=="main" else self.head}}
            if method=="GET" and "/issues/" in path:
                return {"number":int(path.rsplit("/",1)[1]),"state":"open"}
            if method=="GET" and "/git/commits/" in path:
                return copy.deepcopy(self.commits[path.rsplit("/",1)[1]])
            if method=="GET" and "/git/trees/" in path:
                sha=path.rsplit("/",1)[1].split("?")[0]
                return {"sha":sha,"truncated":False,"tree":[{"path":p,"type":"blob","mode":"100644","sha":lifecycle.blob_id(v)} for p,v in self.trees[sha].items()]}
            if method=="GET" and "/compare/" in path:
                a,b=path.rsplit("/",1)[1].split("...")
                distance=self.distance(a,b)
                return {"status":"ahead" if distance else "identical" if distance==0 else "diverged",
                        "ahead_by":distance,"behind_by":0,"base_commit":{"sha":a},"merge_base_commit":{"sha":a}}
            if method=="POST" and path==PREFIX+"/git/trees":
                files={**self.trees[body["base_tree"]],**{row["path"]:row["content"] for row in body["tree"]}}
                return {"sha":self.tree(files)}
            if method=="POST" and path==PREFIX+"/git/commits":
                return {"sha":self.commit(body["tree"],body["parents"])}
            if method=="PATCH" and path==PREFIX+"/git/refs/heads/"+install.BRANCH:
                assert body["force"] is False
                candidate=body["sha"]
                if self.distance(self.head,candidate) is None:
                    self.rejected+=1
                    raise install.ApiError(422)
                if candidate != self.head:
                    self.head=candidate
                    self.published.append(candidate)
                return {}
            raise AssertionError((method,path))


class QualificationTests(unittest.TestCase):
    def test_bounded_concurrent_workloads(self):
        real_sleep=time.sleep
        for count in (1,2,5,10,25,50,100):
            with self.subTest(clients=count):
                api=MemoryGit()
                workers=min(4,count)
                numbers=list(range(1000,1000+count))
                metrics={"clients":count,"workers":workers,"initial_success":0,"deferred":0,
                         "harness_resubmitted":0,"contention_retries":0}
                start=time.perf_counter()
                with patch.object(install,"source_files",return_value=PACKAGE), \
                     patch.object(install,"read_text",side_effect=lambda api,prefix,path,ref:api.read(ref,path)), \
                     patch.object(install.time,"sleep",side_effect=lambda delay:real_sleep(delay/1000)):
                    for phase in ("claim","head","finish"):
                        barrier=threading.Barrier(workers)
                        def plan(s,number):
                            if phase=="claim":
                                return session.claim(api,s,number,["proof"],"claim")
                            if phase=="head":
                                return session.advance(api,s,"return to Head",issue=number,return_to_head=True)
                            return session.finish(api,s,"blocked","test decision",issue=number)
                        def execute(number,synchronize=False):
                            s=session.load(api,REPO)
                            if synchronize:
                                barrier.wait(timeout=30)
                            try:
                                result=session.recover_save(api,REPO,s,lambda current:plan(current,number),number)
                            except ValueError as err:
                                if str(err)!="Contention retry budget exhausted; no unconfirmed write replayed":
                                    raise
                                return None
                            self.assertEqual(result["status"],"saved")
                            return result.get("contention_retries",0)
                        with ThreadPoolExecutor(max_workers=workers) as pool:
                            results=list(pool.map(lambda n:execute(n,n<1000+workers),numbers))
                        deferred=[n for n,result in zip(numbers,results) if result is None]
                        metrics["initial_success"]+=count-len(deferred)
                        metrics["deferred"]+=len(deferred)
                        metrics["contention_retries"]+=sum(x for x in results if x is not None)
                        # Explicit test-harness retry, NOT automatic product recovery.
                        for n in deferred:
                            self.assertEqual(execute(n),0)
                            metrics["harness_resubmitted"]+=1
                    final=session.load(api,REPO)
                self.assertEqual(final["handoff"]["active"],[])
                self.assertEqual(final["ledger"]["issues"][0],RETIRED)
                self.assertEqual({r["issue"] for r in final["ledger"]["issues"]},{7,*numbers})
                self.assertEqual(len(set(checkpoint.bindings(final["ledger"]).values())),count+1)
                self.assertEqual({r["state"] for r in final["ledger"]["issues"][1:]},{"blocked"})
                self.assertEqual(sorted(r["handoff"]["issue"] for r in final["handoff"]["history"]),numbers)
                self.assertEqual(len(api.published),count*3)
                self.assertEqual(api.read(api.head,"notes/custom.md"),"keep me")
                self.assertEqual(api.read(api.product,"product.txt"),"unchanged")
                if count>1:
                    self.assertGreater(metrics["contention_retries"]+metrics["deferred"],0)
                metrics.update(published=len(api.published),rejected_patches=api.rejected,
                               elapsed_seconds=round(time.perf_counter()-start,3))
                print("VIB53_SCALE "+json.dumps(metrics,sort_keys=True),flush=True)

    def test_starvation_counterexample_with_real_production_retry(self):
        api=MemoryGit()
        with patch.object(install,"source_files",return_value=PACKAGE), \
             patch.object(install,"read_text",side_effect=lambda api,prefix,path,ref:api.read(ref,path)), \
             patch.object(install.time,"sleep"):
            state=session.load(api,REPO)
            original=api.request
            competitors=iter(range(2000,2004))
            def race(method,path,body=None):
                if method=="PATCH":
                    n=next(competitors,None)
                    if n is not None:
                        api.request=original
                        fresh=session.load(api,REPO)
                        session.save(api,fresh,*session.claim(api,fresh,n,["proof"],"winner"),True,issue=n)
                        api.request=race
                return original(method,path,body)
            api.request=race
            with self.assertRaisesRegex(ValueError,"budget exhausted"):
                session.recover_save(api,REPO,state,lambda s:session.claim(api,s,1000,["proof"],"loser"),1000)
            final=session.load(api,REPO)
            self.assertEqual([a["issue"] for a in final["handoff"]["active"]],list(range(2000,2004)))
            self.assertEqual(len(api.published),4)
            self.assertEqual(api.rejected,4)
            self.assertIsNone(session.issue_view(final["ledger"],final["handoff"],1000)[0])
            print("VIB53_STARVATION bounded refusal after four competing wins; no automatic durable resumption",flush=True)

    def test_fresh_process_claim_replay_has_no_durable_intent_identity(self):
        api=MemoryGit()
        with patch.object(install,"source_files",return_value=PACKAGE), \
             patch.object(install,"read_text",side_effect=lambda api,prefix,path,ref:api.read(ref,path)):
            s=session.load(api,REPO)
            session.save(api,s,*session.claim(api,s,1000,["proof"],"original"),True,issue=1000)
            committed=session.load(api,REPO)
        # A separate Python process receives only persisted state, not original invocation.
        script = """
import json, sys
from tools import session
class IssueAPI:
    def request(self, method, path, body=None):
        assert method == 'GET' and '/issues/' in path
        return {'number':1000,'state':'open'}
s=json.load(sys.stdin)
api=IssueAPI()
for note in ('original','different intent'):
    plan=session.claim(api,s,1000,['proof'],note)
    print(json.dumps(session.save(api,s,*plan,True,issue=1000)))
"""
        result=subprocess.run([sys.executable,"-B","-c",script],input=json.dumps(committed),
                              capture_output=True,text=True,check=True)
        receipts=[json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(receipts),2)
        self.assertEqual(receipts[0],receipts[1])
        self.assertEqual(receipts[0]["status"],"unchanged")
        self.assertEqual(receipts[0]["installed_sha"],committed["ref"])
        print("VIB53_RESTART replay does not duplicate claim; different note is also unchanged; durable operation identity not established",flush=True)

    def test_real_git_legacy_upgrade_and_parallel_opt_in(self):
        class Remote(GitApi):
            def request(self, method, path, body=None):
                if method=="GET" and "/issues/" in path:
                    return {"number":int(path.rsplit("/",1)[1]),"state":"open"}
                return super().request(method,path,body)
        with tempfile.TemporaryDirectory() as tmp:
            api=Remote(tmp)
            candidate={**NEW_FILES,"tools/session.py":Path(session.__file__).read_text(encoding="utf-8")}
            with patch.object(install,"source_files",side_effect=lambda api,sha:{OLD:OLD_FILES,NEW:candidate}[sha]), \
                 patch.object(install,"read_text",side_effect=lambda api,prefix,path,ref:api.read(ref,path)):
                legacy=session.load(api,REPO,api.old)
                self.assertEqual(legacy["handoff"]["schema_version"],1)
                result=lifecycle.upgrade(api,REPO,api.old,NEW,apply=True,owner_approved=True)
                upgraded=session.load(api,REPO,result["installed_sha"])
                self.assertEqual(upgraded["ledger"],legacy["ledger"])
                self.assertEqual(upgraded["handoff"],legacy["handoff"])
                for path in (session.LEDGER,session.HANDOFF,"notes/custom.md"):
                    self.assertEqual(api.read(api.old,path),api.read(upgraded["ref"],path))
                result=session.save(api,upgraded,*session.claim(api,upgraded,1000,["proof"],"solo"),True,issue=1000)
                solo=session.load(api,REPO,result["installed_sha"])
                self.assertEqual(solo["handoff"]["schema_version"],1)
                result=session.save(api,solo,*session.claim(api,solo,1001,["proof"],"parallel",parallel=True),True,issue=1001)
                parallel=session.load(api,REPO,result["installed_sha"])
                self.assertEqual(parallel["handoff"]["schema_version"],2)
                self.assertEqual(session.select_active(parallel["handoff"],1000),solo["handoff"]["active"])
                self.assertEqual(parallel["handoff"]["history"],legacy["handoff"]["history"])
                self.assertEqual(parallel["ledger"]["issues"][0],legacy["ledger"]["issues"][0])
                self.assertEqual(api.ref("main"),api.product)
                self.assertEqual(api.read(parallel["ref"],"notes/custom.md"),"keep me\n")
                before=list(api.writes)
                with self.assertRaisesRegex(ValueError,"active work"):
                    lifecycle.upgrade(api,REPO,parallel["ref"],"c"*40,apply=True,owner_approved=True)
                self.assertEqual(api.writes,before)
