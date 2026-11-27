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
        return subprocess.check_output(["git","-C",self.path,*args],input=data.encode("utf-8") if data is not None else None,env=env).decode("utf-8").strip()
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
        return subprocess.check_output(["git","-C",self.path,"show",sha+":"+path]).decode("utf-8")
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

    def test_approved_notice_preserves_shared_law_exclusions_and_mit_text(self):
        root = Path(__file__).resolve().parents[1]
        notice = (root / "VIB-NOTICE.md").read_text(encoding="utf-8")
        self.assertIn("VIB_LICENSE_TERMS_APPROVED", notice)
        self.assertIn("excluded from the restrictive grant", notice)
        self.assertIn("Prior licensed revisions", notice)
        self.assertIn("Ownership and separate lawful permission", notice)
        # Verify embedded, verbatim MIT texts against immutable upstream Git blob IDs.
        import re
        notices = re.findall(r"```text\n(.*?)\n```", notice, re.DOTALL)
        self.assertEqual(len(notices), 3)
        self.assertEqual([lifecycle.blob_id(value + "\n") for value in notices],
                         ["1466aeaa07d9f7fd502ca697353b5feace5f4e5a","2fca5f35039b9b1eb3c3d193219411a9cf0765f1","30e65839065c0ea88ca00a2de47d65de4313e154"])
        laws = (root / "ENGINEERING-LAWS.md").read_text(encoding="utf-8")
        start, end = "<!-- engineering-laws:start -->", "<!-- engineering-laws:end -->"
        shared = laws[laws.index(start):laws.index(end) + len(end)]
        for name in ("README.md", "AGENTS.md"):
            self.assertIn(shared, (root / "install/branch" / name).read_text(encoding="utf-8"))

    def test_approved_legal_package_fresh_install_and_upgrade(self):
        # Real installer and lifecycle with disposable Git objects; no live GitHub writes.
        api = self.api
        root = Path(__file__).resolve().parents[1]
        package = {dest: (root / src).read_text(encoding="utf-8")
                   for src, dest in install.PACKAGE.items()}
        self.assertEqual(len(package), 14)
        self.assertIn("VIB_LICENSE_TERMS_APPROVED", package["VIB-NOTICE.md"])
        self.assertNotIn("LICENSE", package)
        with patch.object(install, "source_files", side_effect=lambda api, sha:
                          dict({OLD: OLD_FILES, NEW: package}[sha])):
            pin = self.change("LICENSE", "adopter-owned license\n")
            before = {p: api.read(pin, p) for p in
                      ("LICENSE", session.LEDGER, session.HANDOFF, "notes/custom.md")}
            upgraded = lifecycle.upgrade(api, REPO, pin, NEW, apply=True,
                                         owner_approved=True)["installed_sha"]
            self.assertEqual(api.ref("main"), api.product)
            self.assertEqual({p: api.read(upgraded, p) for p in before}, before)
            self.assertEqual(session.load(api, REPO, upgraded)["manifest"]
                             ["package_files_sha256"], lifecycle.digest_files(package))
            for path, content in package.items():
                self.assertEqual(api.read(upgraded, path), content)
            # Fresh-install path in the disposable fixture only.
            api.git("update-ref", "-d", "refs/heads/" + install.BRANCH, upgraded)
            fresh = install.install(api, REPO, NEW, "v1.0.6", True)["installed_sha"]
            self.assertEqual(api.ref("main"), api.product)
            self.assertEqual(api.git("rev-parse", fresh + "^"), api.product)
            observed = session.load(api, REPO, fresh)
            self.assertEqual(observed["manifest"]["package_files_sha256"],
                             lifecycle.digest_files(package))
            self.assertEqual(observed["ledger"]["issues"], [])
            for path, content in package.items():
                self.assertEqual(api.read(fresh, path), content)
        install.require_publishable_package(package)

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

    def test_upgrade_and_retirement_refuse_unverified_legacy_debt(self):
        api = self.api
        ledger, handoff = json.loads(api.ledger), json.loads(api.handoff)
        ledger["issues"][0]["state"] = "deferred"
        archive = handoff["history"][0]
        archive.update(disposition="deferred", merged_sha=None, decision="Legacy deferral")
        self.change(session.LEDGER, install.render(ledger))
        pin = self.change(session.HANDOFF, install.render(handoff))
        original = api.read(pin, session.HANDOFF)

        plan = lifecycle.upgrade(api, REPO, pin, NEW)
        self.assertEqual(plan["integration_debt_upgrade_blockers"], [7])
        self.assertFalse(plan["integration_debt_resolved"])
        with self.assertRaisesRegex(ValueError, "Reconcile unverified integration debt"):
            lifecycle.upgrade(api, REPO, pin, NEW, apply=True, owner_approved=True)
        with self.assertRaisesRegex(ValueError, "integration debt before retirement"):
            lifecycle.prepare_retirement(api, REPO, pin)
        self.assertEqual(api.writes, [])
        self.assertEqual(api.ref(install.BRANCH), pin)
        self.assertEqual(api.read(pin, session.HANDOFF), original)
        self.assertEqual(api.ref("main"), api.product)

    def test_upgrade_refuses_terminal_integrated_distinct_historical_fix(self):
        api = self.api
        handoff = json.loads(api.handoff)
        earlier = copy.deepcopy(handoff["history"][0])
        fix = api.commit(api.tree({"product.txt": "unintegrated older fix\n"}), [api.product])
        earlier["handoff"].update(fix_sha=fix, candidate_sha=fix)
        earlier.update(disposition="staged", merged_sha=None, decision="Earlier distinct fix staged")
        handoff["history"].insert(0, earlier)
        pin = self.change(session.HANDOFF, install.render(handoff))
        plan = lifecycle.upgrade(api, REPO, pin, NEW)
        self.assertEqual(plan["integration_debt_upgrade_blockers"], [7])
        self.assertEqual(plan["integration_debt_archive_blockers"], [{"issue": 7,
            "archive_sha256": session.closure_digest(earlier), "fix_sha": fix}])
        for prepare in (False, True):
            with self.assertRaisesRegex(ValueError, "Reconcile unverified integration debt"):
                lifecycle.upgrade(api, REPO, pin, NEW, apply=True, owner_approved=True,
                                  prepare_only=prepare)
        self.assertEqual(api.writes, [])
        self.assertEqual(api.ref(install.BRANCH), pin)
        self.assertEqual(api.ref("main"), api.product)
        self.assertEqual(api.read(pin, session.HANDOFF), install.render(handoff))

    def staged_upgrade_fixture(self):
        api = self.api
        ledger = json.loads(api.ledger)
        ledger["issues"][0]["state"] = "staged"
        history = json.loads(api.handoff)
        history["history"][0].update(disposition="staged", merged_sha=None)
        self.change(session.LEDGER, install.render(ledger))
        pin = self.change(session.HANDOFF, install.render(history))
        head = api.commit(api.tree({"product.txt":"later engineering work\\n"}), [api.product])
        pr = {"number":8, "state":"open", "merged":False,
              "base":{"ref":"main", "sha":api.product, "repo":{"id":42}},
              "head":{"sha":head, "repo":{"id":42}}}
        request = api.request
        def scoped(method, path, body=None):
            if method == "GET" and path == PREFIX + "/pulls/8":
                return copy.deepcopy(pr)
            if method == "GET" and path.startswith(PREFIX + "/compare/"):
                old, new = path.rsplit("/",1)[1].split("...")
                merge_base = api.git("merge-base", old, new)
                return {"status":"identical" if old == new else "ahead" if merge_base == old else "diverged",
                        "merge_base_commit":{"sha":merge_base}}
            return request(method, path, body)
        patch.object(api, "request", side_effect=scoped).start()
        actual_session = (Path(__file__).resolve().parents[1]/"tools/session.py").read_text(encoding="utf-8")
        patch.object(install, "source_files", side_effect=lambda api,sha:
                     dict({OLD:OLD_FILES, NEW:{**NEW_FILES,"tools/session.py":actual_session}}[sha])).start()
        return pin, pr

    def test_staged_preserving_upgrade_requires_exact_scope_and_preserves_bytes(self):
        api = self.api
        pin, pr = self.staged_upgrade_fixture()
        with self.assertRaisesRegex(ValueError,"active work"):
            lifecycle.upgrade(api,REPO,pin,NEW)
        with self.assertRaisesRegex(ValueError,"active work"):
            lifecycle.prepare_retirement(api,REPO,pin)
        plan = lifecycle.upgrade(api,REPO,pin,NEW,preserve_staged=True)
        self.assertFalse(plan["staged_integration_verified"])
        self.assertEqual(plan["staged_scope"]["staged"][0]["candidate_sha"],api.product)
        self.assertEqual(plan["staged_scope"]["staged"][0]["current_head"],pr["head"]["sha"])
        self.assertEqual(api.writes,[])
        digest = plan["staged_scope_sha256"]
        for scope in (None,"0"*64):
            with self.assertRaisesRegex(ValueError,"scope digest"):
                lifecycle.upgrade(api,REPO,pin,NEW,apply=True,owner_approved=True,
                                  preserve_staged=True,staged_scope_sha256=scope)
        with self.assertRaisesRegex(ValueError,"owner approval"):
            lifecycle.upgrade(api,REPO,pin,NEW,apply=True,preserve_staged=True,staged_scope_sha256=digest)
        self.assertEqual(api.writes,[])
        prepared = lifecycle.upgrade(api,REPO,pin,NEW,apply=True,owner_approved=True,
                                     prepare_only=True,preserve_staged=True,staged_scope_sha256=digest)
        self.assertEqual(api.ref(install.BRANCH),pin)
        self.assertFalse(prepared["ref_moved"])
        new = lifecycle.upgrade(api,REPO,pin,NEW,apply=True,owner_approved=True,
                                preserve_staged=True,staged_scope_sha256=digest)["installed_sha"]
        self.assertEqual(api.ref("main"),api.product)
        for path in (session.LEDGER,session.HANDOFF,"notes/custom.md"):
            self.assertEqual(api.git("rev-parse",pin+":"+path),api.git("rev-parse",new+":"+path))
        state = session.load(api,REPO,new)
        self.assertTrue(state["closure_supported"])
        self.assertEqual(state["ledger"]["issues"][0]["state"],"staged")
        self.assertEqual(state["handoff"]["schema_version"],1)

    def test_staged_preserving_upgrade_refuses_changed_pr_or_missing_capability(self):
        api = self.api
        pin, pr = self.staged_upgrade_fixture()
        plan = lifecycle.upgrade(api,REPO,pin,NEW,preserve_staged=True)
        digest = plan["staged_scope_sha256"]
        original = copy.deepcopy(pr)
        for changes in ({"merged":True}, {"state":"closed"}, {"base":{**pr["base"],"ref":"other"}},
                        {"head":{**pr["head"],"repo":{"id":43}}}):
            pr.update(changes)
            with self.assertRaisesRegex(ValueError,"PR identity"):
                lifecycle.upgrade(api,REPO,pin,NEW,apply=True,owner_approved=True,
                                  preserve_staged=True,staged_scope_sha256=digest)
            pr.clear(); pr.update(copy.deepcopy(original))
        pr["head"]["sha"] = api.commit(api.tree({"other":"unrelated"}), [])
        with self.assertRaises((ValueError,subprocess.CalledProcessError)):
            lifecycle.upgrade(api,REPO,pin,NEW,preserve_staged=True)
        pr.clear(); pr.update(copy.deepcopy(original))
        with patch.object(install,"source_files",side_effect=lambda api,sha:dict({OLD:OLD_FILES,NEW:NEW_FILES}[sha])):
            with self.assertRaisesRegex(ValueError,"closure capability"):
                lifecycle.upgrade(api,REPO,pin,NEW,preserve_staged=True)
        self.assertEqual(api.writes,[])
        self.assertEqual(api.ref(install.BRANCH),pin)

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

    def test_fixture_preserves_exact_utf8_and_line_endings(self):
        value = "é\nsecond\r\nlast\n"
        tree = self.api.tree({"byte-probe.txt": value})
        commit = self.api.commit(tree, [])
        self.assertEqual(self.api.read(commit, "byte-probe.txt"), value)
        self.assertEqual(self.api.git("rev-parse", commit + ":byte-probe.txt"),
                         lifecycle.blob_id(value))

    def test_upgrade_rejects_actual_package_byte_or_mode_tampering(self):
        api = self.api
        path = "README.md"
        for kind in ("bytes", "mode"):
            with self.subTest(kind=kind):
                api.ref(install.BRANCH, api.old)
                tree = api.git("rev-parse", api.old + "^{tree}")
                if kind == "bytes":
                    tree = api.tree({path: OLD_FILES[path].replace("\n", "\r\n")}, tree)
                else:
                    api.git("read-tree", tree)
                    blob = api.git("rev-parse", api.old + ":" + path)
                    api.git("update-index", "--cacheinfo", "100755", blob, path)
                    tree = api.git("write-tree")
                pin = api.commit(tree, [api.old])
                api.ref(install.BRANCH, pin)
                with self.assertRaises(ValueError):
                    lifecycle.upgrade(api, REPO, pin, NEW, apply=True, owner_approved=True)
                self.assertEqual(api.writes, [])
                self.assertEqual(api.ref(install.BRANCH), pin)
                self.assertEqual(api.ref("main"), api.product)

    def test_exact_041_package_reconciliation_then_idle_upgrade(self):
        # Disposable Git objects only; the real installed branch is never written.
        root = Path(__file__).resolve().parents[1]
        old_pin = "c7a4995c99fed8d1e87970a744c4cde378ebed1e"
        def git_blob(pin, path):
            return subprocess.check_output(["git","-C",str(root),"show",pin+":"+path]).decode("utf-8")
        available = subprocess.run(["git","-C",str(root),"cat-file","-e",old_pin+"^{commit}"],
                                   capture_output=True).returncode == 0
        if not available:
            if (os.environ.get("GITHUB_ACTIONS") != "true"
                    or os.environ.get("GITHUB_REPOSITORY") != install.SOURCE):
                self.skipTest("Exact historical source not present in shallow checkout")
            # Windows public CI uses a shallow checkout. Fetch only the immutable
            # historical pin, no branch/tag update or user-owned host dependency.
            subprocess.run(["git","-C",str(root),"fetch","--depth=1","--no-tags",
                            "--no-write-fetch-head","https://github.com/"+install.SOURCE+".git",old_pin],
                           check=True,timeout=60)
        old_map = install.pinned_package(git_blob(old_pin,"tools/install.py"))
        old_package = {dest:git_blob(old_pin,src) for src,dest in old_map.items()}
        new_pin = subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
        new_package = {dest:git_blob(new_pin,src) for src,dest in install.PACKAGE.items()}
        self.assertEqual(len(old_package),14)
        self.assertEqual(set(old_package),set(new_package))
        api = self.api
        base = api.product
        tree = api.tree({"product.txt":"reviewed product\n"})
        candidate = api.commit(tree,[base])
        preview = api.commit(tree,[base,candidate])
        merged = api.git("commit-tree",tree,"-p",base,"-p",candidate,data="actual product merge\n")
        run_link = "https://github.com/"+REPO+"/actions/runs/123/attempts/1"
        prior = json.loads(api.handoff)["history"][0]
        prior["handoff"].update(fix_sha=candidate,candidate_sha=candidate,evidence=[run_link])
        prior.update(disposition="staged",merged_sha=None)
        active = {**copy.deepcopy(prior["handoff"]),"issue":8,"version":"v1.0.6.2",
                  "integration_base_sha":base,"integration_merge_sha":preview}
        ledger = json.loads(api.ledger)
        ledger["issues"][0]["state"] = "staged"
        ledger["issues"].append({"issue":8,"version":"v1.0.6.2","state":"in_progress","acceptance":["test"]})
        handoff = {"schema_version":1,"active":active,"history":[prior]}
        manifest = {**api.manifest,"source_sha":old_pin,"package_files_sha256":lifecycle.digest_files(old_package)}
        pin = api.commit(api.tree({**old_package,"vib-install.json":install.render(manifest),
                    session.LEDGER:install.render(ledger),session.HANDOFF:install.render(handoff),
                    "notes/custom.md":"keep me\n"}),[api.old])
        api.ref(install.BRANCH,pin)
        pr = {"number":8,"state":"closed","merged":True,"merge_commit_sha":merged,
              "head":{"sha":candidate,"repo":{"id":42}},
              "base":{"sha":base,"ref":"main","repo":{"id":42}}}
        pre = {"id":123,"run_attempt":1,"repository":{"id":42},"event":"pull_request",
               "head_sha":preview,"status":"completed","conclusion":"success",
               "pull_requests":[{"number":8,"head":{"sha":candidate},"base":{"sha":base}}]}
        post = {"id":124,"run_attempt":1,"repository":{"id":42},"head_repository":{"id":42},
                "workflow_id":52,"event":"push","head_branch":"main","head_sha":merged,
                "status":"completed","conclusion":"success"}
        jobs = [{"id":987,"name":"test","run_id":124,"run_attempt":1,"head_sha":merged,
                 "status":"completed","conclusion":"success",
                 "steps":[{"name":"Run acceptance","status":"completed","conclusion":"success"}]}]
        original = api.request
        def scoped(method,path,body=None):
            if method == "GET" and path == "/repos/"+install.SOURCE+"/compare/"+old_pin+"..."+new_pin:
                return {"status":"ahead","merge_base_commit":{"sha":old_pin}}
            if method == "GET" and path.startswith(PREFIX+"/compare/"):
                a,b = path.rsplit("/",1)[1].split("...")
                ancestor = api.git("merge-base",a,b)
                return {"status":"identical" if a == b else "ahead" if ancestor == a else "diverged",
                        "merge_base_commit":{"sha":ancestor}}
            if method == "GET" and path == PREFIX+"/pulls/8":
                return copy.deepcopy(pr)
            if method == "GET" and path.endswith("/attempts/1/jobs?per_page=100"):
                return {"total_count":len(jobs),"jobs":copy.deepcopy(jobs)}
            if method == "GET" and "/actions/runs/" in path:
                run = int(path.split("/actions/runs/",1)[1].split("/")[0])
                return copy.deepcopy({123:pre,124:post}[run])
            result = original(method,path,body)
            if method == "GET" and path.startswith(PREFIX+"/git/commits/"):
                sha = path.rsplit("/",1)[1]
                result["parents"] = [{"sha":p} for p in api.git("rev-list","--parents","-n","1",sha).split()[1:]]
            return result
        def review(s, number, version):
            return {"schema_version":1,"repository":REPO,"repository_id":42,"product_branch":"main",
                    "source_sha":old_pin,"installed_sha":s["ref"],"pull_request":8,
                    "head_sha":candidate,"base_sha":base,"merge_sha":merged,
                    "issues":[{"issue":number,"version":version,"fix_sha":candidate,
                        "criteria":[{"text":"test","checks":[{"run":124,"attempt":1,"workflow_id":52,
                                        "job_name":"test","steps":["Run acceptance"]}]}]}]}
        def old_reader(s):
            # Run the exact .41 validator in an isolated import root, not the
            # candidate module. The subprocess has no API or credential use.
            with tempfile.TemporaryDirectory() as directory:
                folder = Path(directory)
                for path, content in old_package.items():
                    dest = folder/path
                    dest.parent.mkdir(parents=True,exist_ok=True)
                    dest.write_bytes(content.encode("utf-8"))
                (folder/"tools"/"__init__.py").write_text("",encoding="utf-8")
                code = ("import json,sys; from tools import session; "
                        "assert session.__file__.startswith(sys.argv[1]); "
                        "data=json.load(sys.stdin); session.validate_handoff(data['handoff'],data['ledger'])")
                subprocess.run([sys.executable,"-B","-c",code,str(folder)],cwd=folder,
                    input=json.dumps({"ledger":s["ledger"],"handoff":s["handoff"]}),
                    text=True,check=True,capture_output=True,timeout=60)
        with patch.object(api,"request",side_effect=scoped), patch.object(install,"source_files",
                side_effect=lambda _,sha:dict({old_pin:old_package,new_pin:new_package}[sha])):
            before = session.load(api,REPO,pin)
            old_reader(before)
            with self.assertRaisesRegex(ValueError,"active work"):
                lifecycle.upgrade(api,REPO,pin,new_pin)
            self.assertEqual(api.writes,[])
            api.ref("main",merged)  # simulate a separately approved product merge
            state = session.load(api,REPO,pin)
            policy = {"schema_version":1,"outcome":"historical_product_integration",
                      "archive_index":0,"archive_digest":session.closure_digest(prior),
                      "premerge":{"merge_sha":preview,"evidence":[run_link]},
                      "review":review(state,7,"v1.0.6.1")}
            l,h = session.reconcile(api,state,7,"Fixture owner reconciliation",policy=policy)
            self.assertEqual(h["active"],active)
            self.assertEqual(h["history"][0],prior)
            reconciled = session.save(api,state,l,h,True,issue=7,policy=policy)["installed_sha"]
            state = session.load(api,REPO,reconciled)
            self.assertEqual(state["handoff"]["active"],active)
            self.assertEqual(state["manifest"],manifest)
            for p,value in old_package.items():
                self.assertEqual(api.read(reconciled,p),value)
            old_reader(state)
            with self.assertRaisesRegex(ValueError,"active work"):
                lifecycle.upgrade(api,REPO,reconciled,new_pin)
            p = review(state,8,"v1.0.6.2")
            l,h = session.finish(api,state,"integrated","Fixture owner integrates",policy=p)
            idle = session.save(api,state,l,h,True,issue=8,policy=p)["installed_sha"]
            finished = session.load(api,REPO,idle)
            self.assertIsNone(finished["handoff"]["active"])
            self.assertEqual([row["state"] for row in finished["ledger"]["issues"]],["integrated","integrated"])
            old_reader(finished)
            plan = lifecycle.upgrade(api,REPO,idle,new_pin)
            self.assertEqual(plan["status"],"planned")
            self.assertNotIn("integration_debt",plan)
            upgraded = lifecycle.upgrade(api,REPO,idle,new_pin,apply=True,owner_approved=True)["installed_sha"]
            self.assertEqual(api.ref("main"),merged)
            for path in (session.LEDGER,session.HANDOFF,"notes/custom.md"):
                self.assertEqual(api.read(upgraded,path),api.read(idle,path))
            for path,value in new_package.items():
                self.assertEqual(api.read(upgraded,path),value)
            observed = session.load(api,REPO,upgraded)
            self.assertEqual(observed["manifest"]["source_sha"],new_pin)
            self.assertEqual(observed["handoff"],finished["handoff"])
