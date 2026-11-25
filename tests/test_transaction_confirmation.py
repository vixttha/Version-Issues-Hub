"""Production session transaction qualification; no external writes."""
import io
import unittest
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
            if self.outcome in ("descendant","lost_descendant","divergent","wrong_tree"):
                self.ref = LATER
            if self.outcome in ("lost","lost_descendant"):
                raise install.ApiTransportError("PATCH","git/refs",True)
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
                    "parents":[{"sha":HEAD}]}
        return super().request(method,path,body)

class TransactionTests(unittest.TestCase):
    def save(self, api):
        s = state()
        ledger,handoff = session.claim(api,s,247,["test"],"Fix")
        return session.save(api,s,ledger,handoff,True)

    def test_descendant_and_lost_response_confirm_once(self):
        for outcome in ("descendant","lost","lost_descendant"):
            with self.subTest(outcome=outcome):
                api=Remote(outcome)
                result=self.save(api)
                self.assertEqual(result["installed_sha"],NEXT)
                self.assertEqual(result["observed_sha"],api.ref)
                self.assertEqual(result["recovered_response"],outcome.startswith("lost"))
                self.assertEqual(sum(m=="PATCH" for m,_,_ in api.writes),1)

    def test_unconfirmed_commit_never_resubmitted(self):
        for outcome in ("lost_before","divergent","wrong_tree"):
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
