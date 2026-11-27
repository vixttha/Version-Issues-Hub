"""Focused owner-scope and experimental disposition controls; no remote writes."""
import copy
import hashlib
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
            (root/"transient").write_text("unapproved", encoding="utf-8")
            git("add", "."); git("commit", "-qm", "unapproved intermediate path")
            git("rm", "transient"); git("commit", "-qm", "revert intermediate path")
            head = git("rev-parse", "HEAD")
            self.assertNotIn("transient", scope.changed_paths(base, head, cwd=tmp))
            history = scope.scope_paths(base, head, cwd=tmp)
            self.assertEqual(history, paths | {"transient"})
            with self.assertRaisesRegex(ValueError, "transient"):
                scope.assert_scope_paths({**self.record, "allowed_paths": sorted(paths)}, history)
            with self.assertRaisesRegex(ValueError, "Unauthorized scope"):
                scope.assert_scope_paths({**self.record, "allowed_paths": ["allowed"]}, paths)

    def test_divergent_merge_excludes_baseline_only_and_retains_resolution(self):
        with tempfile.TemporaryDirectory() as tmp:
            def git(*args):
                return subprocess.check_output(["git", "-C", tmp, *args], text=True).strip()
            git("init", "-q", "-b", "baseline")
            git("config", "user.name", "VIB test")
            git("config", "user.email", "test@example.invalid")
            root = Path(tmp)
            (root/"README.md").write_text("old", encoding="utf-8")
            (root/"allowed").write_text("old", encoding="utf-8")
            git("add", "."); git("commit", "-qm", "fork")
            git("branch", "side")
            (root/"README.md").write_text("approved baseline", encoding="utf-8")
            git("commit", "-qam", "baseline change")
            base = git("rev-parse", "HEAD")
            git("switch", "side")
            (root/"allowed").write_text("approved change", encoding="utf-8")
            git("commit", "-qam", "allowed change")
            git("switch", "baseline")
            git("merge", "--no-ff", "-m", "ordinary merge", "side")
            head = git("rev-parse", "HEAD")
            record = {**self.record, "allowed_paths": ["allowed"]}
            self.assertEqual(scope.scope_paths(base, head, cwd=tmp), {"allowed"})
            scope.assert_scope_paths(record, scope.scope_paths(base, head, cwd=tmp))
            git("reset", "--hard", base)
            git("merge", "--no-ff", "--no-commit", "side")
            (root/"resolution").write_text("unapproved merge-only edit", encoding="utf-8")
            git("add", "resolution"); git("commit", "-qm", "merge resolution")
            git("rm", "resolution"); git("commit", "-qm", "revert resolution")
            head = git("rev-parse", "HEAD")
            self.assertEqual(scope.changed_paths(base, head, cwd=tmp), {"allowed"})
            self.assertEqual(scope.scope_paths(base, head, cwd=tmp), {"allowed", "resolution"})
            with self.assertRaisesRegex(ValueError, "resolution"):
                scope.assert_scope_paths(record, scope.scope_paths(base, head, cwd=tmp))

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
             patch.object(scope, "approval_change", side_effect=lambda rev, path: prior if rev == prior else pin) as latest, \
             patch.object(scope, "approval_parent", side_effect=lambda rev, path: prior if rev == pin else None) as parent, \
             patch.object(scope, "scope_paths", side_effect=lambda base, rev: {"tools/session.py"} if rev == "b"*40 else {"tools/extra.py"}):
            self.assertEqual(scope.verify_scope(pin, 92, "v0.0.0.41", head, current), amended)
            ancestry.assert_any_call(prior, pin)
            ancestry.assert_any_call("b"*40, head)
            with self.assertRaisesRegex(ValueError, "Stale scope"):
                scope.verify_scope(pin, 92, "v0.0.0.41", head, prior)
            latest.return_value = None
            latest.side_effect = lambda rev, path: "9"*40
            with self.assertRaisesRegex(ValueError, "Stale scope"):
                scope.verify_scope(pin, 92, "v0.0.0.41", head, current)
            latest.side_effect = lambda rev, path: pin
            parent.side_effect = lambda rev, path: None
            with self.assertRaisesRegex(ValueError, "predecessor"):
                scope.verify_scope(pin, 92, "v0.0.0.41", head, current)
            parent.side_effect = lambda rev, path: prior if rev == pin else None
            ancestry.side_effect = ValueError("not an ancestor")
            with self.assertRaisesRegex(ValueError, "not an ancestor"):
                scope.verify_scope(pin, 92, "v0.0.0.41", head, current)

    def test_malformed_043_scope_cannot_authorize_itself(self):
        record = {**self.record, "issue": 96, "version": "v0.0.0.43"}
        ledger = {**self.ledger, "issues": [{"issue": 96, "version": "v0.0.0.43",
                        "state": "in_progress", "acceptance": record["criteria"]}]}
        pin = scope.MALFORMED_043_SCOPE
        with patch.object(scope.checkpoint, "git", side_effect=lambda *args:
                json.dumps(ledger if args[1].endswith("issue-versions.json") else record)), \
             patch.object(scope, "approval_change", return_value=pin), \
             patch.object(scope, "ancestor"):
            with self.assertRaisesRegex(ValueError, "independent recovery"):
                scope.verify_scope(pin, 96, "v0.0.0.43", "d"*40, pin)

    def test_malformed_043_recovery_preserves_scope_and_exact_claim(self):
        record = {**self.record, "issue": 96, "version": "v0.0.0.43"}
        predecessor = scope.MALFORMED_043_SCOPE
        successor = {**record, "previous_approval_sha": predecessor,
                     "reviewed_sha": "e"*40, "owner_decision": "Reviewed forward correction"}
        path = "ledger/scope-approvals/v0.0.0.43.json"
        previous = {"issue":92, "version":"v0.0.0.41",
                    "state":"deferred", "acceptance":["bounded repair"]}
        old = {**self.ledger, "issues": [previous]}
        new = {**old, "issues": [previous, {"issue":96, "version":"v0.0.0.43",
                            "state":"in_progress", "acceptance":record["criteria"]}]}
        archive = {"handoff":{"issue":92,"version":"v0.0.0.41","phase":"Head",
                    "next_action":"Historical review","fix_sha":None,"candidate_sha":None,
                    "pull_request":None,"evidence":[]}, "disposition":"deferred",
                    "decision":"Preserved owner decision","merged_sha":None}
        before = {"schema_version":1, "active":None, "history":[archive]}
        active = {"issue":96, "version":"v0.0.0.43", "phase":"Worker",
                  "next_action":"Repair", "fix_sha":None, "candidate_sha":None,
                  "pull_request":None, "evidence":[]}
        after = {**before, "active":active}
        real_approval_parent = scope.approval_parent
        def read(*args):
            if args[1] == "-s":
                return scope.MALFORMED_043_PARENT
            rev, file = args[1].split(":",1)
            prior = rev == scope.MALFORMED_043_PARENT
            return json.dumps((old if prior else new) if file.endswith("issue-versions.json")
                              else (before if prior else after))
        with patch.object(scope.checkpoint, "git", side_effect=read), \
             patch.object(scope, "changed_paths", return_value={path,"ledger/issue-versions.json",
                                                               "ledger/handoff.json"}), \
             patch.object(scope, "approval_change", return_value=None), \
             patch.object(scope, "approval_parent", return_value=predecessor):
            scope.verify_043_scope_genesis(predecessor,path,record,successor,"f"*40)
            # Exercise the real entry point as well as the incident helper.
            def read_scope(*args):
                if args[1] == "-s":
                    return predecessor if args[-1] == "f"*40 else scope.MALFORMED_043_PARENT
                revision, file = args[1].split(":",1)
                if file == path:
                    return json.dumps(successor if revision == "f"*40 else record)
                return read(*args)
            with patch.object(scope.checkpoint,"git",side_effect=read_scope), \
                 patch.object(scope,"approval_change",side_effect=lambda rev,p:
                              "f"*40 if rev == "f"*40 else predecessor if rev == predecessor else None), \
                 patch.object(scope,"ancestor"), patch.object(scope,"scope_paths",return_value={"tools/session.py"}), \
                 patch.object(scope,"approval_parent", wraps=real_approval_parent), \
                 patch.object(scope,"changed_paths",side_effect=lambda base,head:
                              {path} if head == "f"*40 else {path,"ledger/issue-versions.json","ledger/handoff.json"}):
                with patch("builtins.print") as output:
                    self.assertEqual(scope.verify_scope("f"*40,96,"v0.0.0.43","d"*40,"f"*40),successor)
                    self.assertIn("OWNER AUTHORIZATION UNVERIFIED",output.call_args.args[0])
                with self.assertRaisesRegex(ValueError,"authorization.*not established"):
                    scope.verify_scope("f"*40,96,"v0.0.0.43","d"*40,"f"*40,require_recovery_authorization=True)
                with patch.object(scope,"changed_paths",return_value={path,"ledger/issue-versions.json"}):
                    with self.assertRaisesRegex(ValueError,"separate single-parent"):
                        scope.verify_scope("f"*40,96,"v0.0.0.43","d"*40,"f"*40)
            with self.assertRaisesRegex(ValueError,"retain exact original scope"):
                scope.verify_043_scope_genesis(predecessor,path,record,
                    {**successor,"allowed_paths":["new.py"]},"f"*40)
            with self.assertRaisesRegex(ValueError,"not eligible"):
                scope.verify_043_scope_genesis("1"*40,path,record,successor,"f"*40)
            after["history"] = [{**archive, "decision":"Changed owner decision"}]
            with self.assertRaisesRegex(ValueError, "changed historical state or Worker identity"):
                scope.verify_043_scope_genesis(predecessor,path,record,successor,"f"*40)

    def test_real_git_recovery_chain_retains_immediate_successor_and_later_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def git(*args):
                return subprocess.check_output(["git", "-C", tmp, *args], text=True).strip()
            def write(path, value):
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
            def commit(message):
                git("add", ".")
                git("commit", "-qm", message)
                return git("rev-parse", "HEAD")
            git("init", "-q")
            git("config", "user.name", "VIB test")
            git("config", "user.email", "test@example.invalid")
            write("tools/session.py", "original")
            base = commit("engineering baseline")
            git("checkout", "-qb", "engineering")
            write("tools/session.py", "first reviewed change")
            reviewed = commit("first review")
            write("tools/session.py", "second reviewed change")
            later_reviewed = commit("second review")
            write("docs/repair.md", "later authorized path")
            engineering_head = commit("worker head")
            git("checkout", "-qb", "canonical", base)
            old = {**self.ledger, "issues": []}
            before = {"schema_version": 1, "active": None, "history": []}
            write("ledger/issue-versions.json", old)
            write("ledger/handoff.json", before)
            parent = commit("canonical parent")
            record = {**self.record, "issue": 96, "version": "v0.0.0.43",
                      "base_sha": base, "reviewed_sha": base,
                      "allowed_paths": ["tools/session.py"]}
            path = "ledger/scope-approvals/v0.0.0.43.json"
            new = {**old, "issues": [{"issue": 96, "version": "v0.0.0.43",
                   "state": "in_progress", "acceptance": record["criteria"]}]}
            active = {"issue": 96, "version": "v0.0.0.43", "phase": "Worker",
                      "next_action": "Repair", "fix_sha": None, "candidate_sha": None,
                      "pull_request": None, "evidence": []}
            write(path, record)
            write("ledger/issue-versions.json", new)
            write("ledger/handoff.json", {**before, "active": active})
            genesis = commit("malformed combined claim")
            successor = {**record, "previous_approval_sha": genesis, "reviewed_sha": reviewed,
                         "owner_decision": "Structural recovery only"}
            write(path, successor)
            recovered = commit("independent structural successor")
            continuation = {**successor, "previous_approval_sha": recovered,
                            "reviewed_sha": later_reviewed,
                            "allowed_paths": ["docs/repair.md", "tools/session.py"],
                            "owner_decision": "Later bounded continuation"}
            write(path, continuation)
            current = commit("independent later continuation")
            real_changed, real_scope = scope.changed_paths, scope.scope_paths
            def ancestor(old_sha, new_sha):
                if subprocess.run(["git", "-C", tmp, "merge-base", "--is-ancestor",
                                   old_sha, new_sha], check=False).returncode:
                    raise ValueError("Scope approval or reviewed revision is not an ancestor")
            with patch.object(scope, "MALFORMED_043_SCOPE", genesis), \
                 patch.object(scope, "MALFORMED_043_PARENT", parent), \
                 patch.object(scope.checkpoint, "git", side_effect=git), \
                 patch.object(scope, "ancestor", side_effect=ancestor), \
                 patch.object(scope, "changed_paths", side_effect=lambda a,b,cwd=None: real_changed(a,b,tmp)), \
                 patch.object(scope, "scope_paths", side_effect=lambda a,b: real_scope(a,b,tmp)), \
                 patch.object(scope, "verify_043_scope_genesis",
                              wraps=scope.verify_043_scope_genesis) as incident:
                self.assertEqual(scope.verify_scope(current, 96, "v0.0.0.43",
                                                    engineering_head, current), continuation)
                incident.assert_called_once_with(genesis, path, record, successor, recovered)
                with self.assertRaisesRegex(ValueError, "authorization.*not established"):
                    scope.verify_scope(current, 96, "v0.0.0.43", engineering_head, current,
                                       require_recovery_authorization=True)
                with self.assertRaisesRegex(ValueError, "Stale scope approval"):
                    scope.verify_scope(recovered, 96, "v0.0.0.43", engineering_head, current)
                # Synthetic independent-Head source: a fixed decision is
                # constructed before validation, never inferred from a request.
                specification = b"synthetic reviewed recovery specification"
                gate_a = b"synthetic independently reviewed Gate A receipt"
                binding = {"repository": record["repository"], "issue": 96,
                    "version": "v0.0.0.43", "incident_parent_sha": parent,
                    "incident_sha": genesis, "recovery_successor_sha": recovered,
                    "scope_approval_sha": current, "canonical_revision": current,
                    "tested_head_sha": engineering_head, "engineering_base_sha": base,
                    "scope_sha256": session.closure_digest(continuation),
                    "specification_sha256": hashlib.sha256(specification).hexdigest(),
                    "gate_a_sha256": hashlib.sha256(gate_a).hexdigest(),
                    "operations": ["qualify_forward_recovery"]}
                approved = {"schema_version": 1, "status": "approved",
                            "decision_id": "synthetic-independent-head-decision",
                            "binding": binding, "approved_at": 100, "expires_at": 200}
                class SyntheticHead:
                    def __init__(self, decision):
                        self.decision = copy.deepcopy(decision)
                    def resolve_verified_forward_decision(self, requested):
                        return copy.deepcopy(self.decision)
                def strict(source, spec=specification, evidence=gate_a):
                    return scope.verify_scope(current, 96, "v0.0.0.43", engineering_head, current,
                        require_recovery_authorization=True, recovery_authority_source=source,
                        reviewed_specification=spec, gate_a_evidence=evidence)
                with patch.object(scope.time, "time", return_value=150):
                    self.assertEqual(strict(SyntheticHead(approved)), continuation)
                    for forged in (True, "approved", approved, None, SyntheticHead(True),
                                   SyntheticHead(None), SyntheticHead({"status": "approved"})):
                        with self.subTest(forged=type(forged).__name__), self.assertRaises(ValueError):
                            strict(forged)
                    for key in binding:
                        invalid = copy.deepcopy(approved)
                        invalid["binding"][key] = ("integrate_product" if key != "operations"
                                                   else ["qualify_forward_recovery", "integrate_product"])
                        with self.subTest(binding=key), self.assertRaises(ValueError):
                            strict(SyntheticHead(invalid))
                    for key, value in (("status", "revoked"), ("status", "ambiguous"),
                                       ("expires_at", 150), ("approved_at", 151),
                                       ("schema_version", True), ("decision_id", "")):
                        with self.subTest(receipt=key, value=value), self.assertRaises(ValueError):
                            strict(SyntheticHead({**approved, key: value}))
                    with self.assertRaises(ValueError):
                        strict(SyntheticHead(approved), spec=b"unreviewed specification")
                    with self.assertRaises(ValueError):
                        strict(SyntheticHead(approved), evidence=b"changed Gate A")
                self.assertEqual(git("show", genesis + ":" + path), json.dumps(record, sort_keys=True))
                self.assertEqual(git("show", recovered + ":" + path), json.dumps(successor, sort_keys=True))

    def test_legacy_explicit_preflight_cannot_bypass_scope(self):
        with patch("sys.argv", ["preflight", "--installed-ref", "a"*40, "--issue", "92"]), \
             patch.object(scope, "read_projection", return_value="v0.0.0.41"), \
             self.assertRaises(SystemExit) as result:
            scope.main()
        self.assertEqual(result.exception.code, 1)

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
