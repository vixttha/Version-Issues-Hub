"""Focused owner-scope and experimental disposition controls; no remote writes."""
import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from tools import self_use_preflight as scope, session, gate, standard
from test_session import Fake, state
from test_gate import fixture, Fake as GateFake, REPO


class ScopeControlTests(unittest.TestCase):
    def setUp(self):
        self.ledger = {"schema_version": 1, "repository": "vixttha/Version-Issues-Hub",
            "issues": [{"issue": 92, "version": "v0.0.0.41", "state": "in_progress",
                        "acceptance": ["bounded repair"]}]}
        self.record = {"schema_version": 1, "repository": self.ledger["repository"],
            "issue": 92, "version": "v0.0.0.41", "base_sha": "a"*40,
            "reviewed_sha": "a"*40, "previous_approval_sha": None,
            "criteria": ["bounded repair"], "allowed_paths": ["docs/repair.md", "tools/session.py"],
            "qualification": "ordinary", "disposition": "engineering_only",
            "owner_decision": "Approve bounded repair"}

    def test_exact_scope_and_criteria_refuse_unauthorized_expansion(self):
        scope.validate_scope(self.record, self.ledger, 92, "v0.0.0.41")
        scope.assert_scope_paths(self.record, ["tools/session.py"])
        for paths in (["README.md"], ["tools/session.py", "tools/other.py"], ["docs/repair.md.bak"]):
            with self.subTest(paths=paths), self.assertRaisesRegex(ValueError, "Unauthorized scope"):
                scope.assert_scope_paths(self.record, paths)
        for key, value in (("issue", True), ("version", "v0.0.0.42"),
                ("repository", "other/project"), ("criteria", ["extra"]),
                ("qualification", "advanced"), ("disposition", "production"),
                ("allowed_paths", ["tools/*"]), ("allowed_paths", ["../outside"]),
                ("allowed_paths", ["tools/session.py", "tools/session.py"]),
                ("reviewed_sha", "b"*40), ("owner_decision", "")):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                scope.validate_scope({**self.record, key: value}, self.ledger, 92, "v0.0.0.41")

    def test_diff_detects_rename_deletion_and_unusual_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            def git(*args):
                return subprocess.check_output(["git", "-C", tmp, *args], text=True).strip()
            git("init", "-q")
            git("config", "user.name", "VIB test")
            git("config", "user.email", "test@example.invalid")
            root = Path(tmp)
            (root/"allowed").write_text("original", encoding="utf-8")
            (root/"remove").write_text("remove", encoding="utf-8")
            git("add", "."); git("commit", "-qm", "base")
            base = git("rev-parse", "HEAD")
            git("mv", "allowed", "renamed")
            git("rm", "remove")
            (root/"space name").write_text("extra", encoding="utf-8")
            git("add", "."); git("commit", "-qm", "candidate")
            paths = scope.changed_paths(base, git("rev-parse", "HEAD"), cwd=tmp)
            self.assertEqual(paths, {"allowed", "renamed", "remove", "space name"})
            with self.assertRaisesRegex(ValueError, "Unauthorized scope"):
                scope.assert_scope_paths({**self.record, "allowed_paths": ["allowed"]}, paths)

    def test_revision_bound_scope_amendment_and_stale_ref(self):
        pin, current, head, prior = "c"*40, "d"*40, "e"*40, "f"*40
        amended = {**self.record, "reviewed_sha": "b"*40, "previous_approval_sha": prior,
                   "allowed_paths": ["docs/repair.md", "tools/extra.py", "tools/session.py"]}
        def read(*args):
            if args[0] == "show":
                rev, path = args[1].split(":", 1)
                return json.dumps(self.ledger if path.endswith("issue-versions.json") else
                                  self.record if rev == prior else amended)
            raise AssertionError(args)
        with patch.object(scope.checkpoint, "git", side_effect=read), \
             patch.object(scope, "ancestor") as ancestry, \
             patch.object(scope, "changed_paths", return_value={"tools/extra.py"}):
            self.assertEqual(scope.verify_scope(pin, 92, "v0.0.0.41", head, current), amended)
            ancestry.assert_any_call(prior, pin)
            ancestry.assert_any_call("b"*40, head)
            with self.assertRaisesRegex(ValueError, "Stale scope"):
                scope.verify_scope(pin, 92, "v0.0.0.41", head, prior)
            ancestry.side_effect = ValueError("not an ancestor")
            with self.assertRaisesRegex(ValueError, "not an ancestor"):
                scope.verify_scope(pin, 92, "v0.0.0.41", head, current)

    def test_parallel_activation_and_forged_publication_refused(self):
        api, s = Fake(), state()
        s["parallel_supported"] = True
        s["manifest"]["enforcement"] = "disabled"
        original = copy.deepcopy(s)
        self.assertIs(session.EXPERIMENTAL_PARALLEL_ENABLED, False)
        with self.assertRaisesRegex(ValueError, "Experimental parallel"):
            session.claim(api, s, 247, ["test"], "activate", parallel=True)
        ledger, handoff = session.claim(api, s, 247, ["test"], "solo")
        handoff.update(schema_version=2, active=[handoff["active"]])
        for apply in (False, True):
            with self.assertRaisesRegex(ValueError, "Experimental parallel"):
                session.save(api, s, ledger, handoff, apply=apply, issue=247)
        self.assertEqual(s, original)
        self.assertEqual(api.writes, [])
        self.assertEqual(session.claim(api, s, 247, ["test"], "solo")[1]["schema_version"], 1)

    def test_held_issues_and_experimental_gate_refused(self):
        api, s = Fake(), state()
        s["ledger"]["repository"] = "vixttha/Version-Issues-Hub"
        for number in (37, 40, 53):
            with self.assertRaisesRegex(ValueError, "Owner-held"):
                session.claim(api, s, number, ["test"], "reclaim")
        self.assertEqual(api.writes, [])
        p, st = fixture()
        p.pop("publisher_app_id")
        st["handoff"].update(schema_version=2, active=[])
        with patch.object(session, "load", return_value=st):
            with self.assertRaisesRegex(ValueError, "Experimental parallel"):
                gate.evaluate_scope(GateFake(), REPO, p, lambda _:None, lambda *args:None)
        with self.assertRaisesRegex(ValueError, "Experimental parallel"):
            standard.verify_integration(api, st, {"issue": 247}, {}, None)


if __name__ == "__main__":
    unittest.main()
