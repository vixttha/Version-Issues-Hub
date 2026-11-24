"""Exercise lifecycle operations against real disposable Git objects, with a simulated GitHub API."""
import copy
import contextlib
import io
import sys
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from tools import install, lifecycle, session

REPO="example/product"
PREFIX="/repos/"+REPO
OLD="a"*40
NEW="b"*40
OLD_FILES={"README.md":"old guide\n","tools/install.py":"old installer\n","tools/session.py":"old session\n"}
NEW_FILES={**OLD_FILES,"README.md":"new guide\n","tools/lifecycle.py":"new lifecycle\n","LIFECYCLE.md":"guide\n"}

class GitApi:
    def __init__(self, path):
        self.path=path
        self.writes=[]
        self.git("init","--bare","-q")
        self.meta={"full_name":REPO,"id":42,"default_branch":"main","private":False}
        self.product=self.commit(self.tree({"product.txt":"unchanged\n"}),[])
        self.ref("main",self.product)
        self.manifest={"schema_version":1,"package":install.BRANCH,"source_repository":install.SOURCE,
            "source_sha":OLD,"target_repository":REPO,"target_repository_id":42,"product_branch":"main",
            "product_baseline_sha":self.product,"install_branch":install.BRANCH,"baseline_version":"v1.0.6",
            "target_version":"v1.0.7","enforcement":"disabled","package_files_sha256":lifecycle.digest_files(OLD_FILES)}
        self.ledger='{"schema_version":1,"repository":"example/product","issues":[{"issue":7,"version":"v1.0.6.1","state":"integrated","acceptance":["test"]}]}\n'
        self.handoff=install.render({"schema_version":1,"active":None,"history":[{"handoff":{
            "issue":7,"version":"v1.0.6.1","phase":"Head","next_action":"done","fix_sha":self.product,
            "candidate_sha":self.product,"pull_request":8,"evidence":["https://github.com/example/product/actions/runs/1/attempts/1"]},
            "disposition":"integrated","decision":"owner accepted","merged_sha":self.product}]})
        self.initial={**OLD_FILES,"vib-install.json":install.render(self.manifest),
                      session.LEDGER:self.ledger,session.HANDOFF:self.handoff,"notes/custom.md":"keep me\n"}
        self.old=self.commit(self.tree(self.initial),[self.product])
        self.ref(install.BRANCH,self.old)
        self.ahead=True
    def git(self,*args,data=None):
        env={**os.environ,"GIT_AUTHOR_NAME":"VIB test","GIT_AUTHOR_EMAIL":"vib@example.invalid",
             "GIT_COMMITTER_NAME":"VIB test","GIT_COMMITTER_EMAIL":"vib@example.invalid",
             "GIT_INDEX_FILE":str(Path(self.path)/"fixture-index")}
        return subprocess.check_output(["git","-C",self.path,*args],input=data,text=True,env=env).strip()
    def tree(self,files,base=None):
        self.git("read-tree",base or "--empty")
        for p,s in files.items():
            blob=self.git("hash-object","-w","--stdin",data=s)
            self.git("update-index","--add","--cacheinfo","100644",blob,p)
        return self.git("write-tree")
    def commit(self,tree,parents):
        args=["commit-tree",tree]
        for p in parents: args.extend(["-p",p])
        return self.git(*args,data="fixture\n")
    def ref(self,name,sha=None):
        if sha:
            self.git("update-ref","refs/heads/"+name,sha)
        else:
            return self.git("rev-parse","--verify","refs/heads/"+name)
    def read(self,sha,path):
        return subprocess.check_output(["git","-C",self.path,"show",sha+":"+path],text=True)
    def request(self,method,path,body=None):
        if method!="GET": self.writes.append((method,path,body))
        if path==PREFIX: return self.meta
        if path.startswith("/repos/"+install.SOURCE+"/compare/"):
            return {"status":"ahead" if self.ahead else "diverged","merge_base_commit":{"sha":OLD}}
        if method=="GET" and path.startswith(PREFIX+"/git/ref/heads/"):
            name=path.split("/heads/",1)[1]
            try: sha=self.ref(name)
            except subprocess.CalledProcessError: raise install.ApiError(404) from None
            return {"ref":"refs/heads/"+name,"object":{"type":"commit","sha":sha}}
        if method=="GET" and path.startswith(PREFIX+"/git/commits/"):
            sha=path.rsplit("/",1)[1]
            return {"sha":sha,"tree":{"sha":self.git("rev-parse",sha+"^{tree}")}}
        if method=="GET" and path.startswith(PREFIX+"/git/trees/"):
            sha=path.rsplit("/",1)[1].split("?")[0]
            rows=[]
            for line in self.git("ls-tree","-r","-t",sha).splitlines():
                meta,p=line.split("\t",1); mode,kind,blob=meta.split()
                rows.append({"path":p,"type":kind,"mode":mode,"sha":blob})
            return {"sha":sha,"tree":rows,"truncated":False}
        if method=="POST" and path==PREFIX+"/git/trees":
            return {"sha":self.tree({r["path"]:r["content"] for r in body["tree"]},body.get("base_tree"))}
        if method=="POST" and path==PREFIX+"/git/commits":
            return {"sha":self.commit(body["tree"],body["parents"])}
        if method=="PATCH" and path==PREFIX+"/git/refs/heads/"+install.BRANCH:
            assert body["force"] is False
            old=self.ref(install.BRANCH)
            try: self.git("merge-base","--is-ancestor",old,body["sha"])
            except subprocess.CalledProcessError: raise install.ApiError(422) from None
            self.git("update-ref","refs/heads/"+install.BRANCH,body["sha"],old)
            return {}
        if method=="POST" and path==PREFIX+"/git/refs":
            self.git("update-ref",body["ref"],body["sha"],"0"*40)
            return {}
        raise AssertionError((method,path))

class LifecycleTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        self.api=GitApi(tmp.name)
        self.addCleanup(patch.stopall)
        patch.object(install,"source_files",side_effect=lambda api,sha: dict({OLD:OLD_FILES,NEW:NEW_FILES}[sha])).start()
        patch.object(install,"read_text",side_effect=lambda api,prefix,path,ref:api.read(ref,path)).start()

    def change(self,path,value):
        api=self.api
        old=api.ref(install.BRANCH)
        tree=api.tree({path:value},api.git("rev-parse",old+"^{tree}"))
        new=api.commit(tree,[old]);api.ref(install.BRANCH,new)
        return new

    def test_upgrade_preserves_real_git_state_and_product(self):
        api=self.api
        plan=lifecycle.upgrade(api,REPO,api.old,NEW)
        self.assertEqual(plan["status"],"planned")
        self.assertEqual(api.writes,[])
        result=lifecycle.upgrade(api,REPO,api.old,NEW,apply=True,owner_approved=True)
        self.assertEqual(result["status"],"upgraded")
        new=result["installed_sha"]
        self.assertEqual(api.git("rev-parse",new+"^"),api.old)
        self.assertEqual(api.ref("main"),api.product)
        for p in (session.LEDGER,session.HANDOFF,"notes/custom.md"):
            self.assertEqual(api.git("rev-parse",api.old+":"+p),api.git("rev-parse",new+":"+p))
        self.assertEqual(session.load(api,REPO,new)["manifest"]["source_sha"],NEW)

    def test_legal_review_upgrade_is_plan_only_and_preserves_adopter_license(self):
        api = self.api
        pin = self.change("LICENSE", "adopter-owned license\n")
        candidate = {**NEW_FILES, "VIB-LICENSE.md": "reference only\n",
                     "VIB-NOTICE.md": "REVIEW_ONLY_NOT_A_GRANT\n"}
        with patch.object(install, "source_files", side_effect=lambda api, sha:
                          dict({OLD: OLD_FILES, NEW: candidate}[sha])):
            plan = lifecycle.upgrade(api, REPO, pin, NEW)
            self.assertIn("VIB-LICENSE.md", plan["changed_paths"])
            self.assertIn("VIB-NOTICE.md", plan["changed_paths"])
            self.assertNotIn("LICENSE", plan["changed_paths"])
            for prepare in (False, True):
                with self.assertRaisesRegex(ValueError, "not authorized"):
                    lifecycle.upgrade(api, REPO, pin, NEW, apply=True,
                                      owner_approved=True, prepare_only=prepare)
            self.assertEqual(api.writes, [])
            self.assertEqual(api.ref(install.BRANCH), pin)
            self.assertEqual(api.ref("main"), api.product)
            self.assertEqual(api.read(pin, "LICENSE"), "adopter-owned license\n")
            for p in (session.LEDGER, session.HANDOFF, "notes/custom.md"):
                self.assertEqual(api.read(pin, p), api.read(api.old, p))
            collided = self.change("VIB-NOTICE.md", "adopter-owned\n")
            with self.assertRaisesRegex(ValueError, "collides"):
                lifecycle.upgrade(api, REPO, collided, NEW)
            self.assertEqual(api.writes, [])

    def test_upgrade_requires_owner_and_current_revision(self):
        api=self.api
        with self.assertRaisesRegex(ValueError,"owner approval"):
            lifecycle.upgrade(api,REPO,api.old,NEW,apply=True)
        self.change("notes/custom.md","changed")
        with self.assertRaisesRegex(ValueError,"advanced"):
            lifecycle.upgrade(api,REPO,api.old,NEW)
        self.assertEqual(api.writes,[])

    def test_non_descendant_and_collision_refused(self):
        api=self.api;api.ahead=False
        with self.assertRaisesRegex(ValueError,"advance"):
            lifecycle.upgrade(api,REPO,api.old,NEW)
        api.ahead=True
        new=self.change("LIFECYCLE.md","adopter-owned")
        with self.assertRaisesRegex(ValueError,"collides"):
            lifecycle.upgrade(api,REPO,new,NEW,apply=True,owner_approved=True)
        self.assertEqual(api.writes,[])

    def test_active_or_staged_and_enabled_refused(self):
        api=self.api
        ledger=json.loads(api.ledger);ledger["issues"][0]["state"]="staged"
        new=self.change(session.LEDGER,install.render(ledger))
        with self.assertRaisesRegex(ValueError,"active work"):
            lifecycle.prepare_retirement(api,REPO,new)
        api.ref(install.BRANCH,api.old)
        new=self.change("vib-install.json",install.render({**api.manifest,"enforcement":"enabled"}))
        with self.assertRaisesRegex(ValueError,"enforced mode"):
            lifecycle.upgrade(api,REPO,new,NEW)
        self.assertEqual(api.writes,[])

    def test_archive_preserves_exact_history_without_deletion(self):
        api=self.api
        plan=lifecycle.prepare_retirement(api,REPO,api.old)
        self.assertEqual(api.writes,[])
        result=lifecycle.prepare_retirement(api,REPO,api.old,apply=True,owner_approved=True)
        self.assertEqual(result["status"],"archive_verified")
        self.assertFalse(result["installation_removed"])
        self.assertEqual(api.ref(result["archive_branch"]),api.old)
        self.assertEqual(api.ref(install.BRANCH),api.old)
        self.assertEqual(api.ref("main"),api.product)
        lifecycle.prepare_retirement(api,REPO,api.old,apply=True,owner_approved=True)
        self.assertEqual(len(api.writes),1)

    def test_archive_collision_refused(self):
        api=self.api;api.ref("archive/vib/"+api.old,api.product)
        with self.assertRaisesRegex(ValueError,"occupied"):
            lifecycle.prepare_retirement(api,REPO,api.old,apply=True,owner_approved=True)
        self.assertEqual(api.writes,[])


    def test_fresh_cli_install_upgrade_archive_remove_restore(self):
        api=self.api
        # Only a disposable fixture ref is deleted. The initialized product is retained.
        api.git("update-ref","-d","refs/heads/"+install.BRANCH,api.old)
        def cli(entry, args):
            stdout=io.StringIO()
            with patch.object(install,"GitHub",return_value=api), \
                 patch.object(sys,"argv",["vib"]+args), \
                 patch.dict(os.environ,{"GH_TOKEN":"fixture-only"}), \
                 contextlib.redirect_stdout(stdout):
                entry()
            return json.loads(stdout.getvalue())
        args=["--target",REPO,"--source-sha",OLD,"--baseline","v1.0.6"]
        plan=cli(install.main,args)
        self.assertEqual(plan["status"],"planned")
        self.assertEqual(api.writes,[])
        installed=cli(install.main,args+["--apply"])
        first=installed["installed_sha"]
        self.assertEqual(api.ref(install.BRANCH),first)
        self.assertEqual(api.git("rev-parse",first+"^"),api.product)
        self.assertEqual(session.load(api,REPO,first)["ledger"]["issues"],[])
        before={p:api.git("rev-parse",first+":"+p) for p in (session.LEDGER,session.HANDOFF)}
        new=cli(lifecycle.main,["--target",REPO,"--expected-sha",first,"upgrade",
                    "--source-sha",NEW,"--apply","--owner-approved"])["installed_sha"]
        archive=cli(lifecycle.main,["--target",REPO,"--expected-sha",new,"prepare-retirement",
                    "--apply","--owner-approved"])
        self.assertEqual(api.ref(archive["archive_branch"]),new)
        self.assertEqual(api.ref(install.BRANCH),new)
        # Simulate separate owner-authorized removal with Git's exact expected-old ref.
        api.git("update-ref","-d","refs/heads/"+install.BRANCH,new)
        with self.assertRaisesRegex(ValueError,"not installed"):
            session.load(api,REPO)
        self.assertEqual(api.ref(archive["archive_branch"]),new)
        api.git("update-ref","refs/heads/"+install.BRANCH,new,"0"*40)
        self.assertEqual(session.load(api,REPO,new)["manifest"]["source_sha"],NEW)
        self.assertEqual(before,{p:api.git("rev-parse",new+":"+p) for p in before})
        self.assertEqual(api.ref("main"),api.product)

    def test_competing_writer_during_upgrade_cannot_be_overwritten(self):
        api=self.api
        original=api.request
        competing=[]
        def race(method,path,body=None):
            if method=="PATCH":
                competing.append(self.change("notes/custom.md","concurrent work\n"))
            return original(method,path,body)
        api.request=race
        with self.assertRaises(install.ApiError):
            lifecycle.upgrade(api,REPO,api.old,NEW,apply=True,owner_approved=True)
        self.assertEqual(api.ref(install.BRANCH),competing[0])
        self.assertEqual(api.read(competing[0],"notes/custom.md"),"concurrent work\n")
        self.assertEqual(api.ref("main"),api.product)


    def test_prepared_upgrade_moves_no_ref_and_can_be_confirmed_after_external_advance(self):
        api=self.api
        result=lifecycle.upgrade(api,REPO,api.old,NEW,apply=True,owner_approved=True,prepare_only=True)
        self.assertEqual(result["status"],"prepared")
        self.assertFalse(result["ref_moved"])
        self.assertEqual(api.ref(install.BRANCH),api.old)
        self.assertEqual(api.ref("main"),api.product)
        self.assertEqual([w[0] for w in api.writes],["POST","POST"])
        new=result["prepared_sha"]
        self.assertEqual(api.git("rev-parse",new+"^"),api.old)
        for p in (session.LEDGER,session.HANDOFF,"notes/custom.md"):
            self.assertEqual(api.git("rev-parse",api.old+":"+p),api.git("rev-parse",new+":"+p))
        api.request("PATCH",PREFIX+"/git/refs/heads/"+install.BRANCH,{"sha":new,"force":False})
        self.assertEqual(session.load(api,REPO,new)["manifest"]["source_sha"],NEW)
        archive=lifecycle.prepare_retirement(api,REPO,new,apply=True,owner_approved=True)
        self.assertEqual(api.ref(archive["archive_branch"]),new)

    def test_prepare_requires_explicit_apply_and_owner(self):
        with self.assertRaisesRegex(ValueError,"Prepare-only requires"):
            lifecycle.upgrade(self.api,REPO,self.api.old,NEW,prepare_only=True)
        with self.assertRaisesRegex(ValueError,"owner approval"):
            lifecycle.upgrade(self.api,REPO,self.api.old,NEW,apply=True,prepare_only=True)
        self.assertEqual(self.api.writes,[])
