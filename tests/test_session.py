import copy
import json
import unittest
from unittest.mock import patch
from tools import install, session

REPO = "example/existing"
PIN = "a" * 40
HEAD = "b" * 40
FIX = "c" * 40
CANDIDATE = "d" * 40
TREE = "e" * 40
NEXT = "f" * 40
RUN = "https://github.com/" + REPO + "/actions/runs/123/attempts/1"

def state():
    return {"prefix": "/repos/" + REPO, "ref": HEAD, "product_sha": HEAD,
            "manifest": {"baseline_version": "v1.0.6", "target_version": "v1.0.7",
                         "product_branch": "trunk", "target_repository_id": 42},
            "ledger": {"schema_version": 1, "repository": REPO, "issues": []},
            "handoff": {"schema_version": 1, "active": None, "history": []}}

class Fake:
    def __init__(self):
        self.ref = HEAD
        self.writes = []
        self.pr = {"number": 8, "head": {"sha": CANDIDATE},
                   "base": {"ref": "trunk", "repo": {"id": 42}},
                   "merged": False, "merge_commit_sha": NEXT}
    def request(self, method, path, body=None):
        if method != "GET":
            self.writes.append((method, path, body))
        if method == "GET" and "/issues/" in path:
            return {"number": int(path.split("/")[-1]), "state": "open", "title": "Issue"}
        if method == "GET" and "/pulls/" in path:
            return self.pr
        if method == "GET" and "/git/ref/heads/" in path:
            return {"ref": "refs/heads/" + install.BRANCH, "object": {"type": "commit", "sha": self.ref}}
        if method == "GET" and path.endswith("/git/commits/" + HEAD):
            return {"sha": HEAD, "tree": {"sha": TREE}}
        if method == "POST" and path.endswith("/git/trees"):
            assert body["base_tree"] == TREE
            assert {x["path"] for x in body["tree"]} == {session.LEDGER, session.HANDOFF}
            return {"sha": TREE}
        if method == "POST" and path.endswith("/git/commits"):
            assert body["parents"] == [HEAD]
            return {"sha": NEXT}
        if method == "PATCH" and path.endswith("/git/refs/heads/" + install.BRANCH):
            assert body == {"sha": NEXT, "force": False}
            self.ref = NEXT
            return {}
        raise AssertionError((method, path))

class SessionTests(unittest.TestCase):
    def setUp(self):
        self.api = Fake()
        self.state = state()

    def claim(self):
        self.state["ledger"], self.state["handoff"] = session.claim(self.api, self.state, 247, ["test"], "Fix")
        return self.state["handoff"]["active"]

    def advance(self, **kw):
        self.state["ledger"], self.state["handoff"] = session.advance(self.api, self.state, "next", **kw)

    def test_fresh_session_recovers_active_issue(self):
        active = self.claim()
        self.assertEqual(active["version"], "v1.0.6.1")
        self.assertEqual(session.inspect(self.api, self.state)["status"], "resume")
        self.assertEqual(session.inspect(self.api, self.state, 248)["status"], "blocked_other_active_issue")
        with self.assertRaisesRegex(ValueError, "Another issue"):
            session.claim(self.api, self.state, 248, ["test"], "Fix")
        self.assertEqual(session.claim(self.api, self.state, 247, ["test"], "Retry"),
                         (self.state["ledger"], self.state["handoff"]))

    def test_handoff_loop_and_owner_integration(self):
        self.claim()
        self.advance(fix=FIX, candidate=CANDIDATE, pr=8)
        self.advance(evidence=[RUN])
        self.advance()
        self.assertEqual(self.state["handoff"]["active"]["phase"], "Head")
        with self.assertRaisesRegex(ValueError, "merged"):
            session.finish(self.api, self.state, "integrated", "Owner accepted")
        self.api.pr["merged"] = True
        ledger, handoff = session.finish(self.api, self.state, "integrated", "Owner accepted")
        self.assertIsNone(handoff["active"])
        self.assertEqual(handoff["history"][0]["merged_sha"], NEXT)
        self.assertEqual(ledger["issues"][0]["state"], "integrated")

    def test_stale_pr_and_rework(self):
        self.claim()
        self.advance(fix=FIX, candidate=CANDIDATE, pr=8)
        self.api.pr["head"]["sha"] = NEXT
        self.assertEqual(session.inspect(self.api, self.state)["status"], "stale_candidate")
        with self.assertRaisesRegex(ValueError, "changed"):
            self.advance(evidence=[RUN])
        self.advance(rework=True)
        self.assertIsNone(self.state["handoff"]["active"]["candidate_sha"])
        self.assertEqual(self.state["handoff"]["active"]["evidence"], [])

    def test_evidence_required_and_repo_bound(self):
        self.claim()
        self.advance(fix=FIX, candidate=CANDIDATE, pr=8)
        with self.assertRaisesRegex(ValueError, "requires evidence"):
            self.advance()
        with self.assertRaisesRegex(ValueError, "run-attempt"):
            self.advance(evidence=["https://github.com/other/repo/actions/runs/1/attempts/1"])

    def test_blocked_handoff_preserved(self):
        self.claim()
        self.advance(return_to_head=True)
        ledger, handoff = session.finish(self.api, self.state, "blocked", "Missing access")
        self.assertIsNone(handoff["active"])
        self.assertEqual(ledger["issues"][0]["state"], "blocked")
        self.assertEqual(handoff["history"][0]["decision"], "Missing access")

    def test_atomic_save_and_stale_lease(self):
        ledger, handoff = session.claim(self.api, self.state, 247, ["test"], "Fix")
        self.assertEqual(session.save(self.api, self.state, ledger, handoff)["status"], "planned")
        self.assertEqual(self.api.writes, [])
        self.assertEqual(session.save(self.api, self.state, ledger, handoff, True)["installed_sha"], NEXT)
        with self.assertRaisesRegex(ValueError, "advanced"):
            session.save(self.api, self.state, ledger, handoff, True)
        self.assertEqual(len(self.api.writes), 3)

    def test_rejects_pr_as_issue(self):
        with patch.object(self.api, "request", return_value={"number": 247, "state": "open", "pull_request": {}}):
            with self.assertRaisesRegex(ValueError, "actual GitHub issue"):
                session.claim(self.api, self.state, 247, ["test"], "Fix")

    def test_invalid_active_mapping(self):
        self.claim()
        self.state["handoff"]["active"]["version"] = "v1.0.6.2"
        with self.assertRaisesRegex(ValueError, "mapping"):
            session.validate_handoff(self.state["handoff"], self.state["ledger"])

    def test_pinned_bootstrap_and_tampered_package(self):
        import hashlib
        package = {p: "content " + p for p in install.PACKAGE.values()}
        manifest = {**self.state["manifest"], "schema_version": 1, "package": install.BRANCH,
                    "source_repository": install.SOURCE, "source_sha": PIN,
                    "target_repository": REPO, "install_branch": install.BRANCH,
                    "product_baseline_sha": HEAD,
                    "package_files_sha256": {p: hashlib.sha256(v.encode()).hexdigest() for p, v in package.items()}}
        files = {**package, "vib-install.json": json.dumps(manifest),
                 session.LEDGER: json.dumps(self.state["ledger"]),
                 session.HANDOFF: json.dumps(self.state["handoff"])}
        with patch.object(self.api, "request", return_value={"id": 42, "full_name": REPO, "default_branch": "trunk"}), \
             patch.object(install, "read_ref", return_value=HEAD), \
             patch.object(install, "source_files", return_value=package), \
             patch.object(install, "read_text", side_effect=lambda api, prefix, path, ref: files[path]):
            self.assertEqual(session.load(self.api, REPO, HEAD)["ref"], HEAD)
            with self.assertRaisesRegex(ValueError, "advanced"):
                session.load(self.api, REPO, NEXT)
            files["AGENTS.md"] = "changed"
            with self.assertRaisesRegex(ValueError, "pinned source"):
                session.load(self.api, REPO, HEAD)
