"""Production session transaction qualification; no external writes."""
import io
import json
import unittest
from http.client import IncompleteRead
from urllib.error import HTTPError
from unittest.mock import patch
from tools import install, session
from test_session import Fake, state, HEAD, NEXT, TREE, REPO

LATER = "1" * 40

class Remote(Fake):
    def __init__(self, outcome):
        super().__init__()
        self.outcome = outcome
    def request(self, method, path, body=None):
        if method == "PATCH":
            result = super().request(method,path,body)
            if self.outcome in ("descendant","lost_descendant","divergent","wrong_tree","wrong_parent"):
                self.ref = LATER
            if self.outcome in ("lost","lost_descendant"):
                raise install.ApiTransportError("PATCH","git/refs",True)
            if self.outcome == "lost_http":
                raise install.ApiError(503)
            if self.outcome == "bad_json":
                raise json.JSONDecodeError("response","",0)
            if self.outcome == "lost_before":
                self.ref = HEAD
                raise install.ApiTransportError("PATCH","git/refs",True)
            if self.outcome == "denied":
                self.ref = HEAD
                raise install.ApiError(403)
            if self.outcome == "limited":
                self.ref = HEAD
                raise install.ApiError(429,retry_after=120)
            return result
        if method == "GET" and "/compare/" in path:
            if not path.endswith(NEXT+"..."+LATER):
                raise AssertionError(path)
            return {"status":"diverged" if self.outcome=="divergent" else "ahead",
                    "behind_by":0,"ahead_by":1,"base_commit":{"sha":NEXT},
                    "merge_base_commit":{"sha":NEXT}}
        if method == "GET" and path.endswith("/git/commits/"+NEXT):
            return {"sha":NEXT,"tree":{"sha":HEAD if self.outcome=="wrong_tree" else TREE},
                    "parents":[{"sha":LATER if self.outcome=="wrong_parent" else HEAD}]}
        return super().request(method,path,body)

class TransactionTests(unittest.TestCase):
    def save(self, api):
        s = state()
        ledger,handoff = session.claim(api,s,247,["test"],"Fix")
        return session.save(api,s,ledger,handoff,True)

    def test_descendant_and_lost_response_confirm_once(self):
        for outcome in ("descendant","lost","lost_descendant","lost_http","bad_json"):
            with self.subTest(outcome=outcome):
                api=Remote(outcome)
                result=self.save(api)
                self.assertEqual(result["installed_sha"],NEXT)
                self.assertEqual(result["observed_sha"],api.ref)
                self.assertEqual(result["recovered_response"],outcome!="descendant")
                self.assertEqual(sum(m=="PATCH" for m,_,_ in api.writes),1)

    def test_unconfirmed_commit_never_resubmitted(self):
        for outcome in ("lost_before","divergent","wrong_tree","wrong_parent"):
            with self.subTest(outcome=outcome):
                api=Remote(outcome)
                with patch.object(install.time,"sleep"), self.assertRaises(session.HandoffUnconfirmed) as error:
                    self.save(api)
                self.assertEqual(error.exception.candidate_sha,NEXT)
                self.assertEqual(sum(m=="PATCH" for m,_,_ in api.writes),1)

    def test_denial_and_throttle_stop(self):
        for outcome in ("denied","limited"):
            api=Remote(outcome)
            with patch.object(session,"confirm_handoff") as confirm, self.assertRaises(install.ApiError):
                self.save(api)
            confirm.assert_not_called()
            self.assertEqual(sum(m=="PATCH" for m,_,_ in api.writes),1)

    def test_retry_delay(self):
        self.assertEqual(install.retry_delay(403,{},100),None)
        self.assertEqual(install.retry_delay(429,{"Retry-After":"120"},100),120)
        self.assertEqual(install.retry_delay(403,{"X-RateLimit-Remaining":"0","X-RateLimit-Reset":"500"},100),400)
        self.assertEqual(install.retry_delay(429,{"Retry-After":"invalid"},100),60)
        self.assertEqual(install.retry_delay(503,{"Retry-After":"Thu, 01 Jan 1970 00:05:00 GMT"},100),200)

    def test_throttle_header_never_retries_or_leaks(self):
        api=install.GitHub("secret")
        err=HTTPError("https://api.github.com/private",503,"private",
                      {"Retry-After":"120","X-Other":"secret"},io.BytesIO(b"secret"))
        with patch.object(api.opener,"open",side_effect=err) as call, patch.object(install.time,"sleep") as sleep:
            with self.assertRaises(install.ApiError) as raised:
                api.request("GET","/repos/example/private/contents/file")
            self.assertEqual(call.call_count,1)
            self.assertEqual(raised.exception.retry_after,120)
            self.assertNotIn("secret",str(raised.exception))
            sleep.assert_not_called()

    def test_readback_throttle_retains_delay_and_candidate(self):
        api=Remote("lost")
        with patch.object(session,"confirm_handoff",side_effect=install.ApiError(429,retry_after=180)):
            with self.assertRaises(session.HandoffUnconfirmed) as error:
                self.save(api)
        self.assertEqual(error.exception.candidate_sha,NEXT)
        self.assertEqual(error.exception.retry_after,180)
        self.assertEqual(sum(m=="PATCH" for m,_,_ in api.writes),1)


    def test_real_git_descendant_preserves_both_transactions(self):
        import tempfile
        import subprocess
        from test_lifecycle import GitApi, REPO as TARGET, PREFIX, OLD_FILES

        class GitRemote(GitApi):
            def request(self, method, path, body=None):
                if method=="GET" and "/issues/" in path:
                    return {"number":int(path.rsplit("/",1)[1]),"state":"open"}
                if method=="GET" and path.startswith(PREFIX+"/compare/"):
                    base,head=path.rsplit("/",1)[1].split("...")
                    ancestor=self.git("merge-base",base,head)
                    return {"status":"ahead" if ancestor==base else "diverged",
                            "base_commit":{"sha":base},"merge_base_commit":{"sha":ancestor},
                            "behind_by":int(self.git("rev-list","--count",head+".."+base)),
                            "ahead_by":int(self.git("rev-list","--count",base+".."+head))}
                if method=="GET" and path.startswith(PREFIX+"/git/commits/"):
                    data=super().request(method,path,body)
                    data["parents"]=[{"sha":p} for p in self.git("show","-s","--format=%P",data["sha"]).split()]
                    return data
                result=super().request(method,path,body)
                if method=="PATCH":
                    self.accepted=body["sha"]
                    tree=self.tree({"notes/unrelated.md":"other transaction\n"},self.git("rev-parse",self.accepted+"^{tree}"))
                    self.later=self.commit(tree,[self.accepted])
                    self.git("update-ref","refs/heads/"+install.BRANCH,self.later,self.accepted)
                    raise install.ApiTransportError("PATCH","git/refs",True)
                return result
        with tempfile.TemporaryDirectory() as temp:
            api=GitRemote(temp)
            with patch.object(install,"source_files",return_value=OLD_FILES), patch.object(install,"read_text",side_effect=lambda api,prefix,path,ref:api.read(ref,path)):
                s=session.load(api,TARGET,api.old)
                ledger,handoff=session.claim(api,s,247,["test"],"Fix")
                result=session.save(api,s,ledger,handoff,True)
                latest=session.load(api,TARGET,api.later)
            self.assertEqual(result["installed_sha"],api.accepted)
            self.assertEqual(result["observed_sha"],api.later)
            self.assertTrue(result["recovered_response"])
            self.assertEqual(latest["ledger"],ledger)
            self.assertEqual(latest["handoff"],handoff)
            self.assertEqual(api.read(api.later,"notes/unrelated.md"),"other transaction\n")
            self.assertEqual(api.ref("main"),api.product)
            self.assertEqual(sum(m=="PATCH" for m,_,_ in api.writes),1)


    def test_malformed_retry_after_preserves_reset_bound(self):
        for value in ("invalid", "Thu, 01 Jan 1970 00:05:00"):
            with self.subTest(value=value):
                self.assertEqual(install.retry_delay(403, {
                    "Retry-After":value,"X-RateLimit-Remaining":"0",
                    "X-RateLimit-Reset":"500"},100),400)
        self.assertEqual(install.retry_delay(429,{
            "Retry-After":"600","X-RateLimit-Remaining":"0",
            "X-RateLimit-Reset":"invalid"},100),600)

    def test_truncated_response_is_normalized_without_retry(self):
        class Broken(io.BytesIO):
            def read(self,*args):
                raise IncompleteRead(b"private-data",10)
        for method in ("PATCH","GET"):
            api=install.GitHub("token")
            with patch.object(api.opener,"open",return_value=Broken()) as call:
                with self.assertRaises(install.ApiTransportError) as error:
                    api.request(method,"/repos/example/private/git/refs/heads/test")
                self.assertEqual(call.call_count,1)
                self.assertNotIn("private-data",str(error.exception))

    def test_truncated_patch_and_readback_preserve_candidate(self):
        class Broken(io.BytesIO):
            def read(self,*args):
                raise IncompleteRead(b"private-data",10)
        for readback_fails in (False,True):
            transport=install.GitHub("token")
            api=Remote("normal")
            original=api.request
            def request(method,path,body=None):
                result=original(method,path,body)
                if method=="PATCH" or (readback_fails and method=="GET" and
                        "/git/ref/heads/" in path and api.ref==NEXT):
                    with patch.object(transport.opener,"open",return_value=Broken()):
                        return transport.request(method,path,body)
                return result
            api.request=request
            if readback_fails:
                with self.assertRaises(session.HandoffUnconfirmed) as error:
                    self.save(api)
                self.assertEqual(error.exception.candidate_sha,NEXT)
            else:
                result=self.save(api)
                self.assertEqual(result["installed_sha"],NEXT)
                self.assertTrue(result["recovered_response"])
            self.assertEqual(sum(m=="PATCH" for m,_,_ in api.writes),1)
