"""Focused engineering-only completion controls; no live writes or scale experiments."""
import copy
import unittest
from unittest.mock import patch
from tools import session
from test_session import Fake, state, post_policy, BASE, CANDIDATE, FIX, NEXT, REPO, HEAD

BRANCH = "plan/development"


class EngineeringAPI(Fake):
    def request(self, method, path, body=None):
        if method == "GET" and path.endswith("/git/ref/heads/" + BRANCH):
            return {"ref": "refs/heads/" + BRANCH,
                    "object": {"type": "commit", "sha": self.product}}
        return super().request(method, path, body)


class EngineeringCompletionTests(unittest.TestCase):
    def setUp(self):
        self.api = EngineeringAPI()
        self.state = state()
        self.state["ledger"], self.state["handoff"] = session.claim(
            self.api, self.state, 247, ["test"], "Fix")
        self.state["ledger"], self.state["handoff"] = session.advance(
            self.api, self.state, "Owner reviews engineering evidence", return_to_head=True)
        self.api.pr.update(state="closed", merged=True, merge_commit_sha=NEXT)
        self.api.pr["base"]["ref"] = BRANCH
        self.api.product = NEXT
        self.api.run["head_branch"] = BRANCH
        review = post_policy(self.state)
        review.update(product_branch=BRANCH)
        review["issues"][0]["fix_sha"] = FIX
        self.policy = {"schema_version": 1, "outcome": "engineering_complete",
                       "production_branch": "trunk", "engineering_branch": BRANCH,
                       "review": review}

    def finish(self):
        return session.finish_engineering(self.api, self.state, "Owner accepted engineering",
            policy=self.policy, owner_approved=True, issue=247)

    def test_engineering_completion_keeps_production_deferred(self):
        original = copy.deepcopy(self.state)
        ledger, handoff = self.finish()
        self.assertEqual(self.state, original)
        self.assertEqual(ledger["issues"][0]["state"], "deferred")
        self.assertIsNone(handoff["active"])
        record = handoff["history"][-1]
        self.assertIsNone(record["merged_sha"])
        self.assertIsNone(record["handoff"]["candidate_sha"])
        self.assertEqual(session.engineering_receipt(record, ledger)["policy"], self.policy)
        self.assertEqual(record["disposition"], "deferred")
        session.validate_handoff(handoff, ledger)
        planned = session.save(self.api, self.state, ledger, handoff, issue=247)
        self.assertEqual(planned["status"], "planned")
        observed = session.inspect(self.api, {**self.state, "ledger": ledger, "handoff": handoff}, 247)
        self.assertEqual(observed["status"], "engineering_complete")
        self.assertIs(observed["production_integrated"], False)
        self.assertFalse(self.api.writes)

    def test_schema_two_and_other_lane_preserved(self):
        active = self.state["handoff"]["active"]
        self.state["handoff"].update(schema_version=2, active=[active])
        self.state["parallel_supported"] = True
        self.state["manifest"]["enforcement"] = "disabled"
        self.state["ledger"], self.state["handoff"] = session.claim(
            self.api, self.state, 248, ["other"], "Other work")
        before = copy.deepcopy(session.select_active(self.state["handoff"], 248))
        ledger, handoff = self.finish()
        self.assertEqual(handoff["schema_version"], 2)
        self.assertEqual(handoff["active"], [before])
        session.check_issue_delta(self.state, ledger, handoff, 247)

    def test_wrong_target_unmerged_stale_and_wrong_repo_refused(self):
        for key, value in (("state", "open"), ("merged", False), ("merge_commit_sha", BASE)):
            with self.subTest(key=key):
                previous = self.api.pr[key]
                self.api.pr[key] = value
                with self.assertRaises(ValueError):
                    self.finish()
                self.api.pr[key] = previous
        for obj, key, value in ((self.api.pr["base"], "ref", "trunk"),
                                (self.api.pr["head"], "sha", BASE),
                                (self.api.pr["head"]["repo"], "id", 43)):
            with self.subTest(key=key):
                previous = obj[key]
                obj[key] = value
                with self.assertRaises(ValueError):
                    self.finish()
                obj[key] = previous
        self.assertFalse(self.api.writes)

    def test_wrong_policy_and_missing_owner_refused(self):
        with self.assertRaisesRegex(ValueError, "owner approval"):
            session.finish_engineering(self.api, self.state, "no", policy=self.policy)
        for key, value in (("engineering_branch", "trunk"),
                           ("production_branch", "wrong"), ("outcome", "integrated")):
            with self.subTest(key=key):
                previous = self.policy[key]
                self.policy[key] = value
                with self.assertRaises(ValueError):
                    self.finish()
                self.policy[key] = previous
        self.policy["review"]["issues"][0]["criteria"][0]["text"] = "different"
        with self.assertRaises(ValueError):
            self.finish()
        self.assertFalse(self.api.writes)

    def test_contradictory_evidence_refused_before_publication(self):
        ledger, handoff = self.finish()
        with self.assertRaisesRegex(ValueError, "owner approval"):
            session.save(self.api, self.state, ledger, handoff, True, issue=247)
        self.api.jobs[0]["steps"][0]["conclusion"] = "skipped"
        with self.assertRaises(ValueError):
            session.save(self.api, self.state, ledger, handoff, True,
                         issue=247, engineering_approved=True)
        self.assertFalse(self.api.writes)

    def test_ordinary_production_path_cannot_accept_engineering_pr(self):
        with self.assertRaises(ValueError):
            session.get_pr(self.api, self.state, {"pull_request": 8, "candidate_sha": CANDIDATE})
        ledger, handoff = self.finish()
        with self.assertRaisesRegex(ValueError, "dedicated engineering"):
            session.finish(self.api, self.state, "deferred", handoff["history"][-1]["decision"])
        malformed = copy.deepcopy(handoff)
        malformed["history"][-1]["merged_sha"] = NEXT
        with self.assertRaises(ValueError):
            session.validate_handoff(malformed, ledger)

    def test_engineering_completion_apply_and_readback(self):
        # Use distinct fixture revisions for production, engineering and publication.
        import base64
        import hashlib
        import json
        from tools import install

        saved = "9" * 40
        prefix = self.state["prefix"]
        original_request = self.api.request
        files = {}

        def request(method, path, body=None):
            if method == "GET" and path == prefix + "/git/ref/heads/trunk":
                return {"ref": "refs/heads/trunk",
                        "object": {"type": "commit", "sha": BASE}}
            if method == "POST" and path == prefix + "/git/trees":
                response = original_request(method, path, body)
                files.update({item["path"]: item["content"] for item in body["tree"]})
                return response
            if method == "POST" and path == prefix + "/git/commits":
                original_request(method, path, body)
                return {"sha": saved}
            if method == "PATCH" and path == prefix + "/git/refs/heads/" + install.BRANCH:
                self.assertEqual(body, {"sha": saved, "force": False})
                self.api.writes.append((method, path, copy.deepcopy(body)))
                self.api.ref = saved
                return {}
            if method == "GET" and path.startswith(prefix + "/contents/"):
                filename, revision = path[len(prefix + "/contents/"):].split("?ref=")
                self.assertEqual(revision, self.api.ref)
                raw = files[filename].encode("utf-8")
                return {"type": "file", "encoding": "base64", "path": filename,
                        "content": base64.b64encode(raw).decode("ascii"),
                        "sha": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()}
            return original_request(method, path, body)

        with patch.object(self.api, "request", side_effect=request):
            ledger, handoff = self.finish()
            result = session.save(self.api, self.state, ledger, handoff, True,
                                  issue=247, engineering_approved=True)
            self.assertEqual(result, {"status": "saved", "installed_sha": saved})
            self.assertEqual([method for method, _, _ in self.api.writes],
                             ["POST", "POST", "PATCH"])
            self.assertEqual(install.read_ref(self.api, prefix, install.BRANCH), saved)
            self.assertEqual(install.read_ref(self.api, prefix, BRANCH), NEXT)
            product = install.read_ref(self.api, prefix, "trunk")
            self.assertEqual(product, BASE)
            restored = {**self.state, "ref": saved, "product_sha": product,
                        "ledger": json.loads(install.read_text(self.api, prefix, session.LEDGER, saved)),
                        "handoff": json.loads(install.read_text(self.api, prefix, session.HANDOFF, saved))}
            self.assertEqual((restored["ledger"], restored["handoff"]), (ledger, handoff))
            observed = session.inspect(self.api, restored, 247)
            self.assertEqual(observed["status"], "engineering_complete")
            self.assertIs(observed["production_integrated"], False)
            self.assertEqual(observed["engineering_completion"]["policy"], self.policy)
            self.assertIsNone(restored["handoff"]["active"])
            self.assertEqual(observed["issue"]["state"], "open")
