"""Q01-Q04/Q10: install ambiguity, stale scope, archive and adopter lifecycle.
All writes are synthetic API requests or disposable Git objects.
"""
import copy
import unittest
from unittest.mock import patch
import test_core as c
import test_completion as f
from tools import install,lifecycle,session,checkpoint,gate
from record import run_suite
i=f.load("install")
g=f.g

class Install(unittest.TestCase):
    def setUp(self):
        self.api=i.FakeGitHub()
        self.original=self.api.request
        self.calls=[]
    def apply(self):
        return install.install(self.api,i.TARGET,i.PIN,"v1.0.6",True)
    def fault(self,suffix,after):
        def request(m,p,b=None):
            self.calls.append((m,p))
            if m=="POST" and p.endswith(suffix):
                if after: self.original(m,p,b)
                raise TimeoutError("ambiguous synthetic write")
            return self.original(m,p,b)
        self.api.request=request
        with self.assertRaises(TimeoutError): self.apply()
        self.assertEqual(sum(m=="POST" and p.endswith(suffix) for m,p in self.calls),1)
        self.assertEqual(self.api.refs["trunk"],i.PRODUCT)
        if suffix=="/git/refs" and after:
            self.assertEqual(self.api.refs[install.BRANCH],i.INSTALLED)
            with self.assertRaisesRegex(ValueError,"already exists"): self.apply()
            self.assertEqual(sum(m=="POST" and p.endswith(suffix) for m,p in self.calls),1)
        else:
            self.assertNotIn(install.BRANCH,self.api.refs)
    def test_tree_before(self): self.fault("/git/trees",False)
    def test_tree_after(self): self.fault("/git/trees",True)
    def test_commit_before(self): self.fault("/git/commits",False)
    def test_commit_after(self): self.fault("/git/commits",True)
    def test_ref_before(self): self.fault("/git/refs",False)
    def test_ref_after(self): self.fault("/git/refs",True)
    def bad(self,suffix,value):
        def request(m,p,b=None):
            result=self.original(m,p,b)
            if m=="POST" and p.endswith(suffix): return {"sha":value}
            return result
        self.api.request=request
        with self.assertRaises(ValueError): self.apply()
        self.assertNotIn(install.BRANCH,self.api.refs)
        self.assertEqual(self.api.refs["trunk"],i.PRODUCT)
    def test_bad_tree(self): self.bad("/git/trees","short")
    def test_bad_commit(self): self.bad("/git/commits","short")
    def test_readback_wrong_tree(self):
        def request(m,p,b=None):
            result=self.original(m,p,b)
            if m=="GET" and p==i.PREFIX+"/git/commits/"+i.INSTALLED:
                return dict(result,tree={"sha":i.PRODUCT})
            return result
        self.api.request=request
        with self.assertRaisesRegex(ValueError,"read-back mismatch"): self.apply()
        self.assertEqual(self.api.refs[install.BRANCH],i.INSTALLED)
        self.assertEqual(len(self.api.writes),3)
    def test_product_advance_after_creation(self):
        def request(m,p,b=None):
            result=self.original(m,p,b)
            if m=="POST" and p.endswith("/git/refs"): self.api.refs["trunk"]="e"*40
            return result
        self.api.request=request
        with self.assertRaisesRegex(ValueError,"Product ref changed"): self.apply()
        self.assertEqual(self.api.refs["trunk"],"e"*40)
        self.assertEqual(self.api.refs[install.BRANCH],i.INSTALLED)

class Scope(unittest.TestCase):
    def setUp(self):
        self.policy,self.state=g.fixture()
        self.api=g.Fake()
        p=patch.object(session,"load",return_value=self.state);p.start();self.addCleanup(p.stop)
    def reject(self):
        before=copy.deepcopy(self.state)
        with self.assertRaises(ValueError): gate.evaluate(self.api,g.REPO,self.policy)
        self.assertEqual(self.state,before)
        self.assertEqual(self.api.writes,[])
    def test_positive_shared_run_explicitly_linked(self):
        result=gate.evaluate(self.api,g.REPO,self.policy)
        self.assertEqual([x["issue"] for x in result["issues"]],[247,248])
        self.assertEqual(self.api.writes,[])
    def test_only_other_issue_has_run(self):
        self.state["handoff"]["history"][1]["handoff"]["evidence"]=[g.RUN.replace("/123/","/124/")]
        self.reject()
    def test_unrelated_issue_not_included(self):
        self.policy["issues"].pop()
        self.state["handoff"]["history"][1]["handoff"]["pull_request"]=9
        result=gate.evaluate(self.api,g.REPO,self.policy)
        self.assertEqual([x["issue"] for x in result["issues"]],[247])
    def test_foreign_version(self):
        self.policy["issues"][1]["version"]="v1.0.6.3";self.reject()
    def test_foreign_fix(self):
        self.policy["issues"][1]["fix_sha"]=g.SOURCE;self.reject()
    def test_foreign_criterion(self):
        self.policy["issues"][1]["criteria"][0]["text"]="Other";self.reject()
    def test_stale_base(self):
        self.api.pr["base"]["sha"]=g.SOURCE;self.reject()
    def test_stale_head(self):
        self.api.pr["head"]["sha"]=g.SOURCE;self.reject()
    def test_stale_product_ref(self):
        self.api.refs["trunk"]=g.SOURCE;self.reject()
    def test_stale_state_ref(self):
        self.api.refs[install.BRANCH]=g.SOURCE;self.reject()
    def test_stale_attempt(self):
        self.api.run["run_attempt"]=2;self.reject()
    def test_stale_merge(self):
        self.api.pr["merge_commit_sha"]=g.SOURCE;self.reject()
    def test_stale_second_issue_candidate(self):
        self.state["handoff"]["history"][1]["handoff"]["candidate_sha"]=g.SOURCE;self.reject()

class Archive(unittest.TestCase):
    def setUp(self):
        c.LifecycleNegative.setUp(self)
        self.a=self.api
        self.initial=self.a.old
        self.archive="archive/vib/"+self.initial
        self.original=self.a.request
    def prepare(self,apply=True,owner=True):
        return lifecycle.prepare_retirement(self.a,c.original.REPO,self.initial,apply=apply,owner_approved=owner)
    def unchanged(self):
        self.assertEqual(self.a.ref("main"),self.a.product)
        self.assertEqual(self.a.ref(install.BRANCH),self.initial)
    def test_dry_plan(self):
        self.assertEqual(self.prepare(False)["status"],"planned")
        self.assertEqual(self.a.writes,[]);self.unchanged()
    def test_no_approval(self):
        with self.assertRaises(ValueError): self.prepare(owner=False)
        self.assertEqual(self.a.writes,[]);self.unchanged()
    def test_exact_archive(self):
        result=self.prepare()
        self.assertEqual(result["status"],"archive_verified")
        self.assertFalse(result["installation_removed"])
        self.assertEqual(self.a.ref(self.archive),self.initial)
        self.unchanged()
    def test_repeat_no_new_write(self):
        self.prepare();before=copy.deepcopy(self.a.writes)
        self.prepare();self.assertEqual(self.a.writes,before);self.unchanged()
    def test_archive_collision(self):
        self.a.ref(self.archive,self.a.product)
        with self.assertRaisesRegex(ValueError,"occupied"): self.prepare()
        self.assertEqual(self.a.ref(self.archive),self.a.product);self.unchanged()
        self.assertEqual(self.a.writes,[])
    def fault(self,after):
        def request(m,p,b=None):
            if m=="POST" and p.endswith("/git/refs"):
                if after: self.original(m,p,b)
                raise TimeoutError("archive response")
            return self.original(m,p,b)
        self.a.request=request
        with self.assertRaises(TimeoutError): self.prepare()
        self.unchanged()
        self.a.request=self.original
        if after:
            self.assertEqual(self.a.ref(self.archive),self.initial)
            before=copy.deepcopy(self.a.writes);self.prepare();self.assertEqual(self.a.writes,before)
        else: self.assertIsNone(install.read_ref(self.a,c.original.PREFIX,self.archive))
    def test_archive_before_write(self): self.fault(False)
    def test_archive_after_write(self): self.fault(True)
    def test_restore_exact_bytes(self):
        self.prepare()
        self.a.git("update-ref","-d","refs/heads/"+install.BRANCH,self.initial)
        self.a.git("update-ref","refs/heads/"+install.BRANCH,self.a.ref(self.archive),"0"*40)
        self.unchanged()
        for path,value in self.a.initial.items():
            self.assertEqual(self.a.read(self.a.ref(install.BRANCH),path),value)
        self.assertEqual(session.load(self.a,c.original.REPO,self.initial)["ledger"]["issues"][0]["issue"],7)
    def adopter(self,baseline):
        a=self.a
        a.git("update-ref","-d","refs/heads/"+install.BRANCH,self.initial)
        package={dest:c.git(c.PRODUCT,"show",c.PIN+":"+src).decode("utf-8") for src,dest in install.PACKAGE.items()}
        with patch.object(install,"source_files",side_effect=lambda api,sha:dict(package)):
            plan=install.install(a,c.original.REPO,c.original.NEW,baseline)
            self.assertEqual(plan["status"],"planned")
            result=install.install(a,c.original.REPO,c.original.NEW,baseline,True)
            ref=result["installed_sha"]
            state=session.load(a,c.original.REPO,ref)
            self.assertEqual(state["ledger"]["issues"],[])
            self.assertEqual(state["manifest"]["baseline_version"],baseline)
            ledger=copy.deepcopy(state["ledger"])
            self.assertEqual(checkpoint.register(ledger,101,baseline,["test"]),(baseline+".1",True))
            saved=session.save(a,state,ledger,state["handoff"],True)
            self.assertEqual(saved["status"],"saved")
            self.assertEqual(a.git("rev-parse",saved["installed_sha"]+"^"),ref)
            self.assertEqual(a.git("rev-parse",ref+"^"),a.product)
            self.assertEqual(a.ref("main"),a.product)
            ref=saved["installed_sha"]
            retired=lifecycle.prepare_retirement(a,c.original.REPO,ref,apply=True,owner_approved=True)
            self.assertEqual(a.ref(retired["archive_branch"]),ref)
            self.assertEqual(a.ref(install.BRANCH),ref)
            a.git("update-ref","-d","refs/heads/"+install.BRANCH,ref)
            a.git("update-ref","refs/heads/"+install.BRANCH,a.ref(retired["archive_branch"]),"0"*40)
            restored=session.load(a,c.original.REPO,ref)
            self.assertEqual(restored["ledger"],ledger)
            self.assertEqual(a.ref("main"),a.product)
            for path,value in package.items(): self.assertEqual(a.read(ref,path),value)
    def test_adopter_zero(self): self.adopter("v0.0.0")
    def test_adopter_existing(self): self.adopter("v1.9.99")
    def test_adopter_major(self): self.adopter("v12.3.4")

if __name__=="__main__":
    loader=unittest.defaultTestLoader
    run_suite(unittest.TestSuite([loader.loadTestsFromTestCase(k) for k in (Install,Scope,Archive)]),34,"qualification")
