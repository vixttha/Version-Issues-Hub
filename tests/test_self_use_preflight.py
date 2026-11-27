import copy
import json
import unittest
from unittest.mock import patch
from subprocess import CompletedProcess

from tools import self_use_preflight


class SelfUsePreflightTests(unittest.TestCase):
    def setUp(self):
        self.ledger = {"schema_version": 1, "repository": "vixttha/Version-Issues-Hub",
                       "issues": [{"issue": 65, "version": "v0.0.0.31",
                                   "state": "in_progress", "acceptance": ["recover"]},
                                  {"issue": 61, "version": "v0.0.0.29",
                                   "state": "assigned", "acceptance": ["wire"]}]}
        self.handoff = {"schema_version": 1, "history": [],
                        "active": {"issue": 65, "version": "v0.0.0.31",
                                   "phase": "Worker", "next_action": "recover",
                                   "fix_sha": None, "candidate_sha": None,
                                   "pull_request": None, "evidence": []}}

    def test_committed_projection_rejects_replacement_object(self):
        import tempfile
        from pathlib import Path
        from subprocess import check_output
        from tools import checkpoint
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def git(*args):
                return check_output(["git", "-C", tmp, *args], text=True).strip()
            git("init", "-q", "-b", "baseline")
            git("config", "user.name", "VIB test")
            git("config", "user.email", "vib@example.invalid")
            (root / "ledger").mkdir()
            path = root / "ledger/issue-versions.json"
            path.write_text(json.dumps(self.ledger), encoding="utf-8")
            (root / "ledger/handoff.json").write_text(json.dumps(self.handoff), encoding="utf-8")
            git("add", ".")
            git("commit", "-qm", "canonical")
            pin = git("rev-parse", "HEAD")
            bad = copy.deepcopy(self.ledger)
            bad["issues"][0]["acceptance"] = ["drift"]
            path.write_text(json.dumps(bad), encoding="utf-8")
            git("add", ".")
            git("commit", "-qm", "bad tested revision")
            tested = git("rev-parse", "HEAD")
            path.write_text(json.dumps(self.ledger), encoding="utf-8")
            git("add", ".")
            git("commit", "-qm", "replacement correction")
            replacement = git("rev-parse", "HEAD")
            git("replace", tested, replacement)
            self.assertEqual(json.loads(git("show", tested + ":ledger/issue-versions.json")), self.ledger)
            actual_git = checkpoint.git
            with patch.object(checkpoint, "git", side_effect=lambda *args: actual_git("-C", tmp, *args)):
                with self.assertRaisesRegex(ValueError, "acceptance criteria differ"):
                    self_use_preflight.read_projection(pin, 65, tested_head=tested)

    def test_valid_projection(self):
        self.assertEqual(self_use_preflight.validate_projection(
            self.ledger, copy.deepcopy(self.ledger), self.handoff, 65), "v0.0.0.31")

    def test_missing_mapping_and_changed_criteria_fail(self):
        for mutation in ("missing", "renumber", "extra", "criteria", "repository"):
            with self.subTest(mutation=mutation):
                other = copy.deepcopy(self.ledger)
                if mutation == "missing":
                    other["issues"].pop()
                elif mutation == "renumber":
                    other["issues"][1]["version"] = "v0.0.0.32"
                elif mutation == "extra":
                    other["issues"].append({"issue": 99, "version": "v0.0.0.99",
                                            "state": "assigned", "acceptance": ["extra"]})
                elif mutation == "criteria":
                    other["issues"][1]["acceptance"] = ["changed"]
                else:
                    other["repository"] = "other/project"
                with self.assertRaises(ValueError):
                    self_use_preflight.validate_projection(self.ledger, other, self.handoff, 65)

    def test_wrong_issue_or_nonworker_phase_fails(self):
        with self.assertRaisesRegex(ValueError, "does not own"):
            self_use_preflight.validate_projection(self.ledger, self.ledger, self.handoff, 61)
        handoff = copy.deepcopy(self.handoff)
        handoff["active"]["phase"] = "Head"
        with self.assertRaisesRegex(ValueError, "Worker phase"):
            self_use_preflight.validate_projection(self.ledger, self.ledger, handoff, 65)

    def test_orphan_in_progress_fails(self):
        ledger = copy.deepcopy(self.ledger)
        ledger["issues"][1]["state"] = "in_progress"
        with self.assertRaises(ValueError):
            self_use_preflight.validate_projection(ledger, ledger, self.handoff, 65)

    def test_projection_state_drift_fails(self):
        for state in ("in_progress", "integrated", "retired"):
            with self.subTest(state=state):
                projection = copy.deepcopy(self.ledger)
                projection["issues"][1]["state"] = state
                with self.assertRaisesRegex(ValueError, "checkpoint states differ"):
                    self_use_preflight.validate_projection(self.ledger, projection, self.handoff, 65)

    def test_matching_foreign_repository_fails(self):
        ledger = copy.deepcopy(self.ledger)
        ledger["repository"] = "other/project"
        with self.assertRaisesRegex(ValueError, "VIB product repository"):
            self_use_preflight.validate_projection(ledger, ledger, self.handoff, 65)

    def test_generic_worker_record_is_exact(self):
        record = {"schema_version": 1, "issue": 65, "version": "v0.0.0.31",
                  "installed_sha": "a" * 40}
        branch = "plan/checkpoint-v0.0.0.31"
        self.assertEqual(self_use_preflight.worker_record(record, branch),
                         ("a" * 40, 65, "v0.0.0.31"))
        for key, value in (("schema_version", True), ("issue", True),
                           ("version", "v0.0.0.32"), ("installed_sha", "--upload-pack=x")):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    self_use_preflight.worker_record({**record, key: value}, branch)
        for invalid in ({}, {**record, "extra": 1}):
            with self.assertRaises(ValueError):
                self_use_preflight.worker_record(invalid, branch)
        with self.assertRaisesRegex(ValueError, "does not match"):
            self_use_preflight.worker_record(record, "plan/checkpoint-wrong")

    @patch("tools.self_use_preflight.checkpoint.git")
    @patch("tools.self_use_preflight.WORKER_RECORD")
    @patch("tools.self_use_preflight.subprocess.run")
    @patch("tools.self_use_preflight.read_projection")
    def test_generic_branch_checks_canonical_ancestry_and_version(self, read, run, record, git):
        git.return_value = "b"*40 + "\trefs/heads/Version-Issues-Hub"
        record.read_text.return_value = '{"schema_version":1,"issue":65,"version":"v0.0.0.31","installed_sha":"' + "a" * 40 + '"}'
        run.return_value = CompletedProcess([], 0)
        read.return_value = "v0.0.0.31"
        branch = "plan/checkpoint-v0.0.0.31"
        self.assertEqual(self_use_preflight.verify_checkpoint_branch(branch),
                         ("a" * 40, 65, "v0.0.0.31"))
        read.assert_called_once_with("a" * 40, 65)
        run.assert_any_call(["git", "fetch", "--no-tags", "--no-write-fetch-head", "origin", "b"*40], check=True)
        run.assert_any_call(["git", "--no-replace-objects", "merge-base", "--is-ancestor", "a"*40, "b"*40], check=False)
        read.return_value = "v0.0.0.32"
        with self.assertRaisesRegex(ValueError, "differs"):
            self_use_preflight.verify_checkpoint_branch(branch)
        run.return_value = CompletedProcess([], 1)
        with self.assertRaisesRegex(ValueError, "not in canonical"):
            self_use_preflight.verify_checkpoint_branch(branch)
        record.read_text.side_effect = FileNotFoundError
        with self.assertRaises(FileNotFoundError):
            self_use_preflight.verify_checkpoint_branch(branch)

    @patch("tools.self_use_preflight.verify_scope")
    @patch("tools.self_use_preflight.checkpoint.git")
    @patch("tools.self_use_preflight.WORKER_RECORD")
    @patch("tools.self_use_preflight.subprocess.run")
    @patch("tools.self_use_preflight.read_projection")
    def test_scope_uses_same_observed_revision_as_ancestry(self, read, run, record, git, verify):
        record.read_text.return_value = '{"schema_version":1,"issue":96,"version":"v0.0.0.43","installed_sha":"' + "a"*40 + '"}'
        git.side_effect = ["b"*40 + "\trefs/heads/Version-Issues-Hub", "c"*40]
        read.return_value = "v0.0.0.43"
        run.return_value = CompletedProcess([], 0)
        with patch.dict("os.environ", {"VIB_PR_BASE_SHA": "d"*40}), patch("builtins.print") as output:
            self.assertEqual(self_use_preflight.verify_checkpoint_branch("plan/checkpoint-v0.0.0.43"),
                             ("a"*40, 96, "v0.0.0.43"))
        output.assert_any_call(f"VIB observed canonical revision: {'b'*40}; Worker pin: {'a'*40}")
        verify.assert_called_once_with("a"*40, 96, "v0.0.0.43", "c"*40, "b"*40, "d"*40)
        run.assert_any_call(["git", "--no-replace-objects", "merge-base", "--is-ancestor", "a"*40, "b"*40], check=False)
        self.assertEqual(git.call_count, 2)

    @patch("tools.self_use_preflight.checkpoint.git")
    @patch("tools.self_use_preflight.WORKER_RECORD")
    @patch("tools.self_use_preflight.subprocess.run")
    @patch("tools.self_use_preflight.read_projection")
    def test_ls_remote_matches_exact_canonical_ref_only(self, read, run, record, git):
        record.read_text.return_value = '{"schema_version":1,"issue":65,"version":"v0.0.0.31","installed_sha":"' + "a"*40 + '"}'
        read.return_value = "v0.0.0.31"
        run.return_value = CompletedProcess([],0)
        exact = "b"*40 + "\trefs/heads/Version-Issues-Hub"
        extra = "c"*40 + "\trefs/heads/x/refs/heads/Version-Issues-Hub"
        git.return_value = extra + "\n" + exact
        branch = "plan/checkpoint-v0.0.0.31"
        self_use_preflight.verify_checkpoint_branch(branch)
        run.assert_any_call(["git","fetch","--no-tags","--no-write-fetch-head","origin","b"*40],check=True)
        for invalid in (extra, exact+"\n"+exact):
            run.reset_mock()
            git.return_value = invalid
            with self.assertRaisesRegex(ValueError,"missing or ambiguous"):
                self_use_preflight.verify_checkpoint_branch(branch)
            run.assert_not_called()

    @patch("tools.self_use_preflight.Path.read_text", side_effect=AssertionError("read working tree"))
    @patch("tools.self_use_preflight.verify_scope")
    @patch("tools.self_use_preflight.subprocess.run")
    @patch("tools.self_use_preflight.checkpoint.git")
    def test_strict_branch_reads_worker_and_projection_from_tested_commit(self, git, run, verify, read):
        pin, current, tested = "a" * 40, "b" * 40, "c" * 40
        worker = {"schema_version": 1, "issue": 96, "version": "v0.0.0.43", "installed_sha": pin}
        self.ledger["issues"][0].update(issue=96, version="v0.0.0.43")
        self.handoff["active"].update(issue=96, version="v0.0.0.43")
        blobs = {tested + ":ledger/self-use-worker.json": worker,
                 pin + ":ledger/issue-versions.json": self.ledger,
                 pin + ":ledger/handoff.json": self.handoff,
                 tested + ":ledger/issue-versions.json": copy.deepcopy(self.ledger)}

        def read_git(*args):
            if args == ("rev-parse", "HEAD"):
                return tested
            if args[0] == "ls-remote":
                return current + "\trefs/heads/Version-Issues-Hub"
            if args[0] == "show":
                return json.dumps(blobs[args[1]])
            raise AssertionError(args)

        git.side_effect = read_git
        run.return_value = CompletedProcess([], 0)
        branch = "plan/checkpoint-v0.0.0.43"
        with patch.dict("os.environ", {"VIB_PR_BASE_SHA": ""}):
            self.assertEqual(self_use_preflight.verify_checkpoint_branch(
                branch, require_recovery_authorization=True), (pin, 96, "v0.0.0.43"))
            verify.assert_called_once_with(pin, 96, "v0.0.0.43", tested, current, None,
                                           require_recovery_authorization=True)
            blobs[tested + ":ledger/issue-versions.json"]["issues"][0]["acceptance"] = ["drift"]
            with self.assertRaisesRegex(ValueError, "acceptance criteria differ"):
                self_use_preflight.verify_checkpoint_branch(branch, require_recovery_authorization=True)
        read.assert_not_called()
