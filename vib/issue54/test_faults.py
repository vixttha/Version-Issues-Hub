"""Batch 2: actual lifecycle fault injection, parser and transport guards."""
import contextlib
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch, Mock
from urllib.error import HTTPError, URLError
from test_core import original, install, lifecycle, session, LifecycleNegative

class Faults(unittest.TestCase):
    def setUp(self):
        LifecycleNegative.setUp(self)
        self.a = self.api
        self.initial = self.a.ref(install.BRANCH)
        self.product = self.a.ref("main")
        self.request = self.a.request
        self.calls = []

    def intercept(self, fn):
        def request(method, path, body=None):
            self.calls.append((method,path))
            return fn(method,path,body)
        self.a.request = request

    def upgrade(self, **kw):
        return lifecycle.upgrade(self.a, original.REPO, self.initial, original.NEW, **kw)

    def unchanged(self):
        self.assertEqual(self.a.ref(install.BRANCH),self.initial)
        self.assertEqual(self.a.ref("main"),self.product)
        self.assertFalse(any(m=="DELETE" for m,p in self.calls))

    def test_plan_repeat_no_writes(self):
        self.assertEqual(self.upgrade(),self.upgrade())
        self.assertEqual(self.a.writes,[])
        self.unchanged()

    def test_prepared_exact_parent_and_leaves(self):
        result=self.upgrade(apply=True,owner_approved=True,prepare_only=True)
        self.assertFalse(result["ref_moved"])
        sha=result["prepared_sha"]
        self.assertEqual(self.a.git("rev-parse",sha+"^"),self.initial)
        for path in (session.LEDGER,session.HANDOFF,"notes/custom.md"):
            self.assertEqual(self.a.git("rev-parse",sha+":"+path),self.a.git("rev-parse",self.initial+":"+path))
        self.assertEqual([m for m,p,b in self.a.writes],["POST","POST"])
        self.unchanged()

    def test_source_removal(self):
        new=dict(original.NEW_FILES)
        del new["README.md"]
        with patch.object(install,"source_files",side_effect=lambda a,s: dict(original.OLD_FILES if s==original.OLD else new)):
            with self.assertRaisesRegex(ValueError,"path removal"):
                self.upgrade(apply=True,owner_approved=True)
        self.assertEqual(self.a.writes,[])
        self.unchanged()

    def test_source_missing_lifecycle(self):
        new=dict(original.NEW_FILES)
        del new["tools/lifecycle.py"]
        with patch.object(install,"source_files",side_effect=lambda a,s: dict(original.OLD_FILES if s==original.OLD else new)):
            with self.assertRaisesRegex(ValueError,"lifecycle-compatible"):
                self.upgrade(apply=True,owner_approved=True)
        self.assertEqual(self.a.writes,[])
        self.unchanged()

    def test_same_source(self):
        with self.assertRaisesRegex(ValueError,"Already"):
            lifecycle.upgrade(self.a,original.REPO,self.initial,original.OLD)
        self.assertEqual(self.a.writes,[])
        self.unchanged()

    def test_wrong_merge_base(self):
        def fn(m,p,b):
            if "/compare/" in p:
                return {"status":"ahead","merge_base_commit":{"sha":"c"*40}}
            return self.request(m,p,b)
        self.intercept(fn)
        with self.assertRaisesRegex(ValueError,"advance"):
            self.upgrade()
        self.assertEqual(self.a.writes,[])
        self.unchanged()

    def fault(self, endpoint, after=False):
        def fn(m,p,b):
            if (m,p.rsplit("/",1)[-1])==endpoint:
                if after:
                    self.request(m,p,b)
                raise install.ApiTransportError(m,"fixture",True)
            return self.request(m,p,b)
        self.intercept(fn)
        with self.assertRaises(install.ApiTransportError):
            self.upgrade(apply=True,owner_approved=True)
        self.assertEqual(sum((m,p.rsplit("/",1)[-1])==endpoint for m,p in self.calls),1)
        self.assertFalse(any(m=="DELETE" for m,p in self.calls))
        self.assertEqual(self.a.ref("main"),self.product)
        if after and endpoint[0]=="PATCH":
            actual=self.a.ref(install.BRANCH)
            self.assertNotEqual(actual,self.initial)
            self.assertEqual(self.a.git("rev-parse",actual+"^"),self.initial)
        else:
            self.unchanged()

    def test_tree_timeout(self): self.fault(("POST","trees"))
    def test_commit_timeout(self): self.fault(("POST","commits"))
    def test_patch_timeout_before_write(self): self.fault(("PATCH",install.BRANCH))
    def test_patch_timeout_after_write(self): self.fault(("PATCH",install.BRANCH),True)

    def test_unrelated_proposed_content(self):
        def fn(m,p,b):
            if m=="POST" and p.endswith("/git/trees"):
                b=copy.deepcopy(b)
                b["tree"].append({"path":"notes/custom.md","mode":"100644","type":"blob","content":"unwanted\n"})
            return self.request(m,p,b)
        self.intercept(fn)
        with self.assertRaisesRegex(ValueError,"unrelated paths"):
            self.upgrade(apply=True,owner_approved=True)
        self.assertFalse(any(m=="PATCH" for m,p in self.calls))
        self.unchanged()

    def test_unrelated_proposed_new_path(self):
        def fn(m,p,b):
            if m=="POST" and p.endswith("/git/trees"):
                b=copy.deepcopy(b)
                b["tree"].append({"path":"unrequested.txt","mode":"100644","type":"blob","content":"extra\n"})
            return self.request(m,p,b)
        self.intercept(fn)
        with self.assertRaisesRegex(ValueError,"unrelated paths"):
            self.upgrade(apply=True,owner_approved=True)
        self.assertFalse(any(m=="PATCH" for m,p in self.calls))
        self.unchanged()

    def test_product_advance_before_publication(self):
        def fn(m,p,b):
            result=self.request(m,p,b)
            if m=="POST" and p.endswith("/git/commits"):
                self.a.ref("main",self.a.commit(self.a.tree({"product.txt":"other work\n"}),[self.product]))
            return result
        self.intercept(fn)
        with self.assertRaisesRegex(ValueError,"refs advanced"):
            self.upgrade(apply=True,owner_approved=True)
        self.assertEqual(self.a.ref(install.BRANCH),self.initial)
        self.assertNotEqual(self.a.ref("main"),self.product)
        self.assertFalse(any(m=="PATCH" for m,p in self.calls))

    def test_apply_missing_credential(self):
        with patch.dict(os.environ,{"GH_TOKEN":"","GITHUB_TOKEN":""}), patch.object(sys,"argv",["vib","--target",original.REPO,"--expected-sha",self.initial,"upgrade","--source-sha",original.NEW,"--apply","--owner-approved"]), patch.object(install,"GitHub") as api, contextlib.redirect_stderr(io.StringIO()) as stderr:
            with self.assertRaises(SystemExit) as caught:
                lifecycle.main()
            self.assertEqual(caught.exception.code,2)
            self.assertIn("credential",stderr.getvalue())
            api.assert_not_called()
        self.unchanged()

def identity_case(key,value):
    def test(self):
        state=lifecycle.idle_state(self.a,original.REPO,self.initial)
        self.a.meta[key]=value
        with self.assertRaisesRegex(ValueError,"identity or default branch"):
            lifecycle.current(self.a,state)
        self.assertEqual(self.a.writes,[])
        self.unchanged()
    return test
for key,value in {"id":43,"full_name":"example/other","default_branch":"elsewhere","archived":True,"disabled":True}.items():
    setattr(Faults,"test_identity_"+key,identity_case(key,value))

class Parser(unittest.TestCase):
    def test_literal_package(self):
        self.assertEqual(install.pinned_package("PACKAGE = "+repr(install.PACKAGE)),install.PACKAGE)

def invalid_package(source):
    def test(self):
        with self.assertRaises(ValueError):
            install.pinned_package(source)
    return test
required={"install/branch/README.md":"README.md","install/branch/WORKFLOW.md":"WORKFLOW.md","tools/checkpoint.py":"tools/checkpoint.py"}
for name,source in {
    "empty":"", "syntax":"PACKAGE = {", "computed":"PACKAGE = dict()", "unpack":"PACKAGE = {**{}}",
    "twice":"PACKAGE = {}\nPACKAGE = {}", "duplicate":"PACKAGE = {'tools/checkpoint.py':'tools/checkpoint.py','tools/checkpoint.py':'tools/checkpoint.py'}",
    "missing":"PACKAGE = {}", "unsupported":"PACKAGE = "+repr(dict(required, extra="extra")),
    "wrong_dest":"PACKAGE = "+repr(dict(required, **{"tools/checkpoint.py":"other.py"})),
    "nonstring":"PACKAGE = "+repr(dict(required, **{"tools/checkpoint.py":1})),
}.items():
    setattr(Parser,"test_package_"+name,invalid_package(source))

class Transport(unittest.TestCase):
    def check_error(self,method,error,attempts,cls):
        api=install.GitHub("synthetic-token")
        api.opener=Mock()
        api.opener.open.side_effect=error
        with patch.object(install.time,"sleep") as sleep:
            with self.assertRaises(cls) as caught:
                api.request(method,"/repos/example/product/git/refs/heads/private-fixture")
        self.assertEqual(api.opener.open.call_count,attempts)
        self.assertEqual(sleep.call_count,attempts-1)
        self.assertNotIn("synthetic-token",str(caught.exception))
        self.assertNotIn("private-fixture",str(caught.exception))
        if method!="GET" and cls is install.ApiTransportError:
            self.assertIn("inspect before retrying",str(caught.exception))

def transport_case(method,kind):
    def test(self):
        error=TimeoutError("synthetic") if kind=="timeout" else URLError("synthetic")
        self.check_error(method,error,3 if method=="GET" and kind=="timeout" else 1,install.ApiTransportError)
    return test
for method in ("GET","POST","PATCH","DELETE"):
    for kind in ("timeout","network"):
        setattr(Transport,"test_"+method.lower()+"_"+kind,transport_case(method,kind))

if __name__=="__main__":
    from record import run_suite
    run_suite(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]),38,"faults")
