"""Bounded contention recovery, using actual Git objects and a simulated API."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools import session, install, lifecycle
from test_lifecycle import GitApi, OLD_FILES, REPO
from test_session import Fake, state

A, B, C = 247, 248, 249

class Remote(GitApi):
    def request(self, method, path, body=None):
        if method == "GET" and "/issues/" in path:
            return {"number": int(path.rsplit("/", 1)[1]), "state": "open"}
        result = super().request(method, path, body)
        if method == "GET" and "/git/commits/" in path:
            result["parents"] = [{"sha": p} for p in self.git(
                "show", "-s", "--format=%P", result["sha"]).split()]
        return result

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.api = Remote(tmp.name)
        api = self.api
        package = {**OLD_FILES, "tools/session.py": Path(session.__file__).read_text(encoding="utf-8")}
        manifest = {**api.manifest, "package_files_sha256": lifecycle.digest_files(package)}
        tree = api.tree({"tools/session.py": package["tools/session.py"],
                         "vib-install.json": install.render(manifest)}, api.git("rev-parse", api.old+"^{tree}"))
        pin = api.commit(tree, [api.old])
        api.ref(install.BRANCH, pin)
        self.addCleanup(patch.stopall)
        patch.object(install, "source_files", return_value=package).start()
        patch.object(install, "read_text", side_effect=lambda api,prefix,path,ref:api.read(ref,path)).start()
        patch.object(install.time, "sleep").start()
        s = session.load(api, REPO, pin)
        first = session.claim(api, s, A, ["A"], "A", parallel=True)
        pin = session.save(api, s, *first, True, issue=A)["installed_sha"]
        self.s = session.load(api, REPO, pin)

    def claim(self, s, issue):
        return session.claim(self.api, s, issue, ["test"], "claim")

    def recover(self, plan, issue, **kw):
        return session.recover_save(self.api, REPO, self.s, plan, issue, **kw)

    def inject(self, competing):
        api = self.api
        original = api.request
        def race(method,path,body=None):
            if method == "PATCH":
                api.request = original
                competing()
            return original(method,path,body)
        api.request = race

    def test_automatic_real_git_conflict_preserves_both_claims(self):
        self.inject(lambda: session.save(self.api, self.s, *self.claim(self.s,C),True,issue=C))
        result = self.recover(lambda s:self.claim(s,B),B)
        self.assertEqual(result["contention_retries"],1)
        fresh=session.load(self.api,REPO,result["installed_sha"])
        self.assertEqual([r["issue"] for r in fresh["handoff"]["active"]],[A,B,C])
        self.assertEqual(len(set(r["version"] for r in fresh["ledger"]["issues"])),4)
        self.assertEqual(session.issue_view(fresh["ledger"],fresh["handoff"],A),
                         session.issue_view(self.s["ledger"],self.s["handoff"],A))
        self.assertEqual(self.api.ref("main"),self.api.product)
        self.assertEqual(self.api.read(fresh["ref"],"notes/custom.md"),"keep me\n")

    def test_same_issue_change_stops_without_replaying(self):
        self.inject(lambda: session.save(self.api,self.s,*self.claim(self.s,B),True,issue=B))
        with self.assertRaisesRegex(ValueError,"Issue or archive changed"):
            self.recover(lambda s:self.claim(s,B),B)
        latest=session.load(self.api,REPO)
        self.assertEqual([r["issue"] for r in latest["handoff"]["active"]],[A,B])
        self.assertEqual(sum(m=="PATCH" for m,_,_ in self.api.writes),3)

    def test_advance_replans_only_unchanged_issue(self):
        self.inject(lambda: session.save(self.api,self.s,*self.claim(self.s,C),True,issue=C))
        result=self.recover(lambda s:session.advance(self.api,s,"owner decision",issue=A,return_to_head=True),A)
        self.assertEqual(result["contention_retries"],1)
        latest=session.load(self.api,REPO)
        self.assertEqual(session.select_active(latest["handoff"],A)["phase"],"Head")
        self.assertEqual(session.select_active(latest["handoff"],C)["phase"],"Worker")

    def test_prepublication_conflict_recovers_without_repeating_old_patch(self):
        session.save(self.api,self.s,*self.claim(self.s,C),True,issue=C)
        result=self.recover(lambda s:self.claim(s,B),B)
        self.assertEqual(result["contention_retries"],1)
        self.assertEqual(sum(m=="PATCH" for m,_,_ in self.api.writes),3)

    def test_ambiguous_and_rate_limited_writes_never_replay(self):
        for error in (session.HandoffUnconfirmed("a"*40),install.ApiError(403),
                      install.ApiError(422,retry_after=120),install.ApiError(429,retry_after=60)):
            with self.subTest(error=type(error).__name__), patch.object(session,"save",side_effect=error) as save:
                with self.assertRaises(type(error)):
                    self.recover(lambda s:self.claim(s,B),B)
                self.assertEqual(save.call_count,1)

    def test_bounded_exhaustion_no_infinite_retry(self):
        with patch.object(session,"save",side_effect=session.HandoffStale("advanced")) as save, \
             patch.object(session,"load",return_value=self.s), \
             patch.object(session,"retry_scope",return_value=None):
            with self.assertRaisesRegex(ValueError,"budget exhausted"):
                self.recover(lambda s:self.claim(s,B),B)
            self.assertEqual(save.call_count,4)

    def test_unchanged_ref_rejects_422_not_contention(self):
        error=session.HandoffRejected(install.ApiError(422),"a"*40,"b"*40)
        with patch.object(session,"save",side_effect=error) as save:
            with self.assertRaises(session.HandoffRejected):
                self.recover(lambda s:self.claim(s,B),B)
            self.assertEqual(save.call_count,1)

    def test_intermediate_change_then_revert_is_not_safe(self):
        s=self.s
        changed=copy.deepcopy(s["handoff"])
        session.select_active(changed,A)["next_action"]="temporary change"
        tree=self.api.tree({session.HANDOFF:install.render(changed)}, self.api.git("rev-parse",s["ref"]+"^{tree}"))
        middle=self.api.commit(tree,[s["ref"]])
        final=self.api.commit(self.api.git("rev-parse",s["ref"]+"^{tree}"),[middle])
        self.api.ref(install.BRANCH,final)
        fresh=session.load(self.api,REPO)
        with self.assertRaisesRegex(ValueError,"Issue or archive changed"):
            session.retry_scope(self.api,s,fresh,A,session.HandoffStale("advanced"))

    def test_exact_committed_candidate_not_replayed(self):
        result=session.save(self.api,self.s,*self.claim(self.s,B),True,issue=B)
        published=result["installed_sha"]
        tree=self.api.git("rev-parse",published+"^{tree}")
        current=session.load(self.api,REPO)
        session.save(self.api,current,*self.claim(current,C),True,issue=C)
        error=session.HandoffRejected(install.ApiError(422),published,tree)
        with patch.object(session,"save",side_effect=error) as save:
            result=self.recover(lambda s:self.claim(s,B),B)
        self.assertEqual(result["installed_sha"],published)
        self.assertTrue(result["recovered_response"])
        self.assertEqual(save.call_count,1)

    def test_replan_changed_intent_refused(self):
        session.save(self.api,self.s,*self.claim(self.s,C),True,issue=C)
        def plan(s):
            return session.claim(self.api,s,B,["test"],"original" if s["ref"]==self.s["ref"] else "changed")
        with self.assertRaisesRegex(ValueError,"intent changed"):
            self.recover(plan,B)
        self.assertEqual(sum(m=="PATCH" for m,_,_ in self.api.writes),2)
