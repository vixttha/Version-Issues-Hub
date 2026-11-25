"""Validate the pinned read-only inspect contract without granting resume authority."""
import copy
import json
import sys
import unittest
from pathlib import Path


def verify_recovery(observed, expected, installed_sha):
    if observed["installed_sha"] != installed_sha:
        raise ValueError("Installed revision drift")
    if observed["owner_merge_required"] is not True or observed["evidence_verified"] is not False:
        raise ValueError("Read-only recovery must not grant acceptance")
    if observed["repository"] != "vixttha/Version-Issues-Hub" or observed["active"] != expected:
        raise ValueError("Repository or active handoff mismatch")
    status = observed["status"]
    if expected is None:
        if status != "head_scope_required" or observed["issue"] is not None:
            raise ValueError("Expected Head scope")
        return status
    if observed["issue"]["number"] != expected["issue"] or observed["issue"]["version"] != expected["version"]:
        raise ValueError("Issue or version mismatch")
    if status == "resume":
        return status
    if status == "stale_candidate" and expected["pull_request"] is not None:
        # Pinned inspect reports this for a changed PR candidate or target.
        # It is a successful read-only blocker report, NOT a resumable state.
        return status
    raise ValueError("Unexpected recovery status")


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.active = {"issue": 40, "version": "v0.0.0.1", "pull_request": 2}
        self.observed = {"installed_sha": "a" * 40, "repository": "vixttha/Version-Issues-Hub",
                         "owner_merge_required": True, "evidence_verified": False,
                         "active": copy.deepcopy(self.active),
                         "issue": {"number": 40, "version": "v0.0.0.1"}, "status": "resume"}

    def check(self):
        return verify_recovery(self.observed, self.active, "a" * 40)

    def test_resume(self):
        self.assertEqual(self.check(), "resume")

    def test_stale_candidate_is_a_blocker_not_resume(self):
        self.observed["status"] = "stale_candidate"
        self.assertEqual(self.check(), "stale_candidate")

    def test_stale_without_pr_rejected(self):
        self.active["pull_request"] = None
        self.observed["active"] = copy.deepcopy(self.active)
        self.observed["status"] = "stale_candidate"
        with self.assertRaises(ValueError):
            self.check()

    def test_reject_wrong_authority_and_identity(self):
        for key, value in (("installed_sha", "b"*40), ("owner_merge_required", False),
                           ("evidence_verified", True), ("repository", "wrong"),
                           ("active", None), ("issue", {"number": 39, "version": "v0.0.0.1"}),
                           ("issue", {"number": 40, "version": "v0.0.0.2"}),
                           ("status", "blocked_other_active_issue")):
            with self.subTest(key=key, value=value):
                original = self.observed[key]
                self.observed[key] = value
                with self.assertRaises(ValueError):
                    self.check()
                self.observed[key] = original

    def test_no_active_requires_head_scope(self):
        self.active = None
        self.observed.update(active=None, issue=None, status="head_scope_required")
        self.assertEqual(self.check(), "head_scope_required")
        self.observed["status"] = "resume"
        with self.assertRaises(ValueError):
            self.check()


if __name__ == "__main__":
    if sys.argv[1:] == ["--self-test"]:
        unittest.main(argv=[sys.argv[0]], verbosity=2)
    else:
        sha, handoff, inspect = sys.argv[1:]
        expected = json.loads(Path(handoff).read_text(encoding="utf-8"))["active"]
        observed = json.loads(Path(inspect).read_text(encoding="utf-8"))
        status = verify_recovery(observed, expected, sha)
        print("Verified read-only recovery status:", status)
        if status == "stale_candidate":
            print("Blocked: reload and reverify; do not resume or advance.")
        print(json.dumps(observed, indent=2))
