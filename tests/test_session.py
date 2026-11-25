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
                   "state": "open", "merged": False, "merge_commit_sha": NEXT}
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
        self.api.pr.update(state="closed", merged=True)
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


    def test_stage_two_issues_and_reconcile_only_after_merge(self):
        self.claim()
        self.advance(fix=FIX, candidate=CANDIDATE, pr=8)
        self.advance(evidence=[RUN])
        self.advance()
        self.state["ledger"], self.state["handoff"] = session.finish(
            self.api, self.state, "staged", "Owner stages first issue")
        self.assertEqual(self.state["ledger"]["issues"][0]["state"], "staged")
        self.assertIsNone(self.state["handoff"]["active"])
        self.state["ledger"], self.state["handoff"] = session.claim(
            self.api, self.state, 248, ["test second"], "Fix second")
        self.assertEqual(self.state["handoff"]["active"]["version"], "v1.0.6.2")
        self.advance(fix=NEXT, candidate=CANDIDATE, pr=8)
        self.advance(evidence=[RUN])
        self.advance()
        self.state["ledger"], self.state["handoff"] = session.finish(
            self.api, self.state, "staged", "Owner stages second issue")
        with self.assertRaisesRegex(ValueError, "merged"):
            session.reconcile(self.api, self.state, 247, "Owner integrates")
        self.api.pr.update(state="closed", merged=True)
        for issue in (247, 248):
            self.state["ledger"], self.state["handoff"] = session.reconcile(
                self.api, self.state, issue, "Owner integrates")
        self.assertEqual([r["state"] for r in self.state["ledger"]["issues"]], ["integrated", "integrated"])
        self.assertEqual([r["disposition"] for r in self.state["handoff"]["history"]],
                         ["staged", "staged", "integrated", "integrated"])

    def test_staged_stale_candidate_refused_and_prior_evidence_retained(self):
        self.claim()
        self.advance(fix=FIX, candidate=CANDIDATE, pr=8)
        self.advance(evidence=[RUN])
        self.advance()
        self.state["ledger"], self.state["handoff"] = session.finish(
            self.api, self.state, "staged", "Owner stages")
        self.api.pr["head"]["sha"] = NEXT
        self.api.pr.update(state="closed", merged=True)
        with self.assertRaisesRegex(ValueError, "changed"):
            session.reconcile(self.api, self.state, 247, "Owner integrates")
        self.api.pr.update(state="open", merged=False)
        self.claim()
        self.assertEqual(self.state["handoff"]["active"]["version"], "v1.0.6.1")
        self.advance(fix=FIX, candidate=NEXT, pr=8)
        self.advance(evidence=[RUN])
        self.advance(rework=True)
        old = self.state["handoff"]["history"]
        self.assertEqual(old[0]["handoff"]["fix_sha"], FIX)
        self.assertEqual(old[0]["handoff"]["evidence"], [RUN])
        self.assertEqual(old[-1]["disposition"], "rework")
        self.assertEqual(old[-1]["handoff"]["candidate_sha"], NEXT)


    def test_inspect_distinguishes_closed_and_merged_pr(self):
        self.claim()
        self.advance(fix=FIX, candidate=CANDIDATE, pr=8)
        self.api.pr.update(state="closed", merged=True)
        before = copy.deepcopy(self.state)
        self.assertEqual(session.inspect(self.api, self.state)["status"], "merged_reconciliation_required")
        with self.assertRaisesRegex(ValueError, "merged"):
            self.advance(evidence=[RUN])
        self.assertEqual(self.state, before)
        self.api.pr.update(state="closed", merged=False)
        self.assertEqual(session.inspect(self.api, self.state)["status"], "closed_pr_rework_required")
        with self.assertRaisesRegex(ValueError, "not open"):
            self.advance(evidence=[RUN])
        self.api.pr.update(state="open", merged=False, draft=True)
        self.assertEqual(session.inspect(self.api, self.state)["status"], "resume")
        self.api.pr["head"]["sha"] = NEXT
        self.assertEqual(session.inspect(self.api, self.state)["status"], "stale_candidate")
        self.assertEqual(session.inspect(self.api, self.state, 248)["status"], "blocked_other_active_issue")
        self.assertEqual(self.api.writes, [])

    def test_closed_issue_requires_head_reconciliation(self):
        self.claim()
        with patch.object(self.api, "request", return_value={"number": 247, "state": "closed"}):
            self.assertEqual(session.inspect(self.api, self.state)["status"], "issue_reconciliation_required")
            with self.assertRaisesRegex(ValueError, "not open"):
                self.advance(fix=FIX, candidate=CANDIDATE, pr=8)
            self.advance(return_to_head=True)
        self.assertEqual(self.state["handoff"]["active"]["phase"], "Head")
        self.assertEqual(self.api.writes, [])


    def test_orphan_in_progress_rows_fail_closed(self):
        self.state["ledger"]["issues"].append({"issue": 247, "version": "v1.0.6.1",
            "state": "in_progress", "acceptance": ["test"]})
        before = copy.deepcopy(self.state)
        with self.assertRaisesRegex(ValueError, "Orphan"):
            session.validate_handoff(self.state["handoff"], self.state["ledger"])
        with self.assertRaisesRegex(ValueError, "Orphan"):
            session.claim(self.api, self.state, 248, ["test"], "New work")
        self.assertEqual(self.state, before)
        self.assertEqual(self.api.writes, [])

    def test_multiple_in_progress_rows_fail_closed(self):
        self.claim()
        self.state["ledger"]["issues"].append({"issue": 248, "version": "v1.0.6.2",
            "state": "in_progress", "acceptance": ["test"]})
        with self.assertRaisesRegex(ValueError, "sole in-progress"):
            session.validate_handoff(self.state["handoff"], self.state["ledger"])
        with self.assertRaisesRegex(ValueError, "sole in-progress"):
            session.advance(self.api, self.state, "next", return_to_head=True)
        self.state["ledger"]["issues"][1]["state"] = "assigned"
        session.validate_handoff(self.state["handoff"], self.state["ledger"])
        self.state["ledger"]["issues"][0]["state"] = "assigned"
        with self.assertRaisesRegex(ValueError, "sole in-progress"):
            session.validate_handoff(self.state["handoff"], self.state["ledger"])
        self.assertEqual(self.api.writes, [])


    def test_explicit_prior_line_recovery_preserves_assignment(self):
        for old_state in ("assigned", "blocked", "deferred"):
            with self.subTest(old_state=old_state):
                s = state()
                s["ledger"]["issues"].append({"issue": 247, "version": "v1.0.5.7",
                    "state": old_state, "acceptance": ["original"]})
                before = copy.deepcopy(s)
                with self.assertRaisesRegex(ValueError, "resume-prior-line"):
                    session.claim(self.api, s, 247, [], "Resume")
                with self.assertRaisesRegex(ValueError, "criteria differ"):
                    session.claim(self.api, s, 247, ["changed"], "Resume", resume_prior_line=True)
                ledger, handoff = session.claim(self.api, s, 247, [], "Resume", resume_prior_line=True)
                self.assertEqual(s, before)
                self.assertEqual(ledger["issues"][0]["version"], "v1.0.5.7")
                self.assertEqual(ledger["issues"][0]["acceptance"], ["original"])
                self.assertEqual(handoff["active"]["version"], "v1.0.5.7")
                session.validate_handoff(handoff, ledger)
                self.assertEqual(session.save(self.api, s, ledger, handoff)["status"], "planned")
        self.assertEqual(self.api.writes, [])

    def test_prior_line_recovery_refuses_terminal_future_and_new_rows(self):
        for version, old_state in (("v1.0.5.7", "integrated"), ("v1.0.5.7", "retired"),
                                   ("v1.0.5.7", "staged"), ("v1.0.7.1", "assigned")):
            with self.subTest(version=version, old_state=old_state):
                s = state()
                s["ledger"]["issues"].append({"issue": 247, "version": version,
                    "state": old_state, "acceptance": ["original"]})
                with self.assertRaises(ValueError):
                    session.claim(self.api, s, 247, [], "Resume", resume_prior_line=True)
        with self.assertRaisesRegex(ValueError, "existing eligible"):
            session.claim(self.api, state(), 247, ["test"], "Resume", resume_prior_line=True)
        self.assertEqual(self.api.writes, [])


    def test_rework_requires_open_issue_and_unmerged_pr(self):
        self.claim()
        self.advance(fix=FIX, candidate=CANDIDATE, pr=8)
        before = copy.deepcopy(self.state)
        for status in ({"state": "closed", "merged": True},
                       {"state": "closed", "merged": True, "head": {"sha": NEXT}},
                       {"state": "open", "merged": None}):
            with self.subTest(status=status):
                self.api.pr.update(status)
                with self.assertRaisesRegex(ValueError, "owner reconciliation"):
                    self.advance(rework=True)
                self.assertEqual(self.state, before)
        self.api.pr.update(state="closed", merged=False, head={"sha": CANDIDATE})
        with patch.object(session, "get_issue", return_value={"number":247, "state":"closed"}):
            with self.assertRaisesRegex(ValueError, "Issue is not open"):
                self.advance(rework=True)
            self.assertEqual(self.state, before)
        self.advance(rework=True)
        self.assertEqual(self.state["handoff"]["active"]["phase"], "Worker")
        self.assertEqual(self.state["handoff"]["history"][-1]["disposition"], "rework")
        self.assertEqual(self.api.writes, [])

    def test_stage_rejects_unverified_pr_flags_without_writes(self):
        self.claim()
        self.advance(fix=FIX, candidate=CANDIDATE, pr=8)
        self.advance(evidence=[RUN])
        self.advance()
        before = copy.deepcopy(self.state)
        for flag in (None, "false", "true", 0, 1, True):
            with self.subTest(flag=flag):
                self.api.pr["merged"] = flag
                with self.assertRaises(ValueError):
                    session.finish(self.api, self.state, "staged", "Owner")
                self.assertEqual(self.state, before)
                self.assertEqual(self.api.writes, [])
        del self.api.pr["merged"]
        with self.assertRaises(ValueError):
            session.finish(self.api, self.state, "staged", "Owner")
        self.assertEqual(self.state, before)
        self.assertEqual(self.api.writes, [])
        self.api.pr["merged"] = False
        ledger, _ = session.finish(self.api, self.state, "staged", "Owner")
        self.assertEqual(ledger["issues"][0]["state"], "staged")

    def test_finish_and_reconcile_require_coherent_closed_merged_pr(self):
        self.claim()
        self.advance(fix=FIX, candidate=CANDIDATE, pr=8)
        self.advance(evidence=[RUN])
        self.advance()
        before = copy.deepcopy(self.state)
        self.api.pr.update(state="open", merged=True)
        with self.assertRaisesRegex(ValueError, "merged"):
            session.finish(self.api, self.state, "integrated", "Owner")
        self.assertEqual(self.state, before)
        self.assertEqual(self.api.writes, [])
        self.api.pr.update(state="open", merged=False)
        self.state["ledger"], self.state["handoff"] = session.finish(
            self.api, self.state, "staged", "Owner")
        before = copy.deepcopy(self.state)
        for status, flag in (("open", True), (None, True), ("closed", None),
                             ("closed", "true"), ("closed", 1), ("closed", False)):
            with self.subTest(status=status, flag=flag):
                self.api.pr.update(state=status, merged=flag)
                with self.assertRaises(ValueError):
                    session.reconcile(self.api, self.state, 247, "Owner")
                self.assertEqual(self.state, before)
                self.assertEqual(self.api.writes, [])
        self.api.pr.update(state="closed", merged=True)
        ledger, _ = session.reconcile(self.api, self.state, 247, "Owner")
        self.assertEqual(ledger["issues"][0]["state"], "integrated")

    def test_archived_success_requires_candidate_and_evidence(self):
        self.claim()
        self.advance(fix=FIX, candidate=CANDIDATE, pr=8)
        self.advance(evidence=[RUN])
        self.advance()
        for disposition in ("staged", "integrated"):
            self.api.pr.update(state="closed" if disposition == "integrated" else "open",
                               merged=disposition == "integrated")
            ledger, handoff = session.finish(self.api, self.state, disposition, "Owner")
            session.validate_handoff(handoff, ledger)
            for changes in (
                {"fix_sha": None, "candidate_sha": None, "pull_request": None, "evidence": []},
                {"evidence": []},
                {"fix_sha": None}, {"candidate_sha": None}, {"pull_request": None},
                {"evidence": [RUN.replace("/attempts/1", "")]},
                {"evidence": [RUN, RUN]},
            ):
                with self.subTest(disposition=disposition, changes=changes):
                    broken = copy.deepcopy(handoff)
                    broken["history"][0]["handoff"].update(changes)
                    with self.assertRaises(ValueError):
                        session.validate_handoff(broken, ledger)
            self.assertEqual(handoff["history"][0]["handoff"]["evidence"], [RUN])

    def test_archived_nonsuccess_dispositions_preserve_unverified_history(self):
        self.claim()
        self.advance(return_to_head=True)
        for disposition in ("blocked", "deferred"):
            ledger, handoff = session.finish(self.api, self.state, disposition, "Owner")
            session.validate_handoff(handoff, ledger)
            self.assertEqual(handoff["history"][0]["handoff"]["evidence"], [])
        self.state["handoff"]["active"]["phase"] = "Worker"
        self.advance(fix=FIX, candidate=CANDIDATE, pr=8)
        self.advance(rework=True)
        session.validate_handoff(self.state["handoff"], self.state["ledger"])
        self.assertEqual(self.state["handoff"]["history"][0]["disposition"], "rework")
