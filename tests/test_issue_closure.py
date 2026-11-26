"""Ordinary closure controls; fake API only."""
import copy
import unittest
from unittest.mock import patch
from tools import gate, install, session
import test_engineering_completion


class ClosureTests(unittest.TestCase):
    def setUp(self):
        fixture = test_engineering_completion.EngineeringCompletionTests()
        fixture.setUp()
        self.api = fixture.api
        self.state = fixture.state
        ledger, handoff = fixture.finish()
        self.state.update(ledger=ledger, handoff=handoff, closure_supported=True)
        self.policy = {"schema_version": 1, "repository": ledger["repository"], "issue": 247,
                       "version": ledger["issues"][0]["version"], "archive_ref": self.state["ref"],
                       "archive_digest": session.closure_digest(handoff["history"][-1]),
                       "reason": "completed", "owner_decision": "Owner reviewed exact evidence",
                       "engineering": fixture.policy}

    def test_closure_status_independent(self):
        for state, reason in (("open", None), ("closed", "completed")):
            result = session.closure_status(self.state, {"number": 247, "state": state, "state_reason": reason})
            self.assertEqual(result["engineering_completion"], "recorded")
            self.assertEqual(result["github_state"], state)
            self.assertFalse(result["production_integrated"])
        self.assertEqual(result["closure_synchronization"], "historical_unverified")

    def test_owner_and_exact_archive_required(self):
        with self.assertRaises(ValueError):
            session.closure_plan(self.api, self.state, 247, self.policy, "pending")
        with self.assertRaises(ValueError):
            session.closure_plan(self.api, self.state, 247, {**self.policy, "issue": 248},
                                 "pending", owner_approved=True)
        self.assertFalse(self.api.writes)

    def test_intent_is_append_only_and_idempotent(self):
        before = copy.deepcopy(self.state)
        with patch.object(session, "verify_closure_basis", return_value=self.state["handoff"]["history"][-1]):
            ledger, handoff = session.closure_plan(self.api, self.state, 247, self.policy,
                                                    "pending", owner_approved=True)
            self.assertEqual(ledger, before["ledger"])
            self.assertEqual(handoff["history"][:-1], before["handoff"]["history"])
            self.assertEqual(self.state, before)
            self.state.update(ledger=ledger, handoff=handoff)
            self.assertEqual(session.closure_plan(self.api, self.state, 247, self.policy,
                                                  "pending", owner_approved=True), (ledger, handoff))
            with self.assertRaises(ValueError):
                session.claim(self.api, self.state, 248, ["test"], "Other")
            with self.assertRaises(ValueError):
                session.closure_plan(self.api, self.state, 247, self.policy,
                                     "confirmed", owner_approved=True)
        self.assertFalse(self.api.writes)

    def test_confirmation_requires_matching_readback(self):
        archive = self.state["handoff"]["history"][-1]
        with patch.object(session, "verify_closure_basis", return_value=archive):
            ledger, handoff = session.closure_plan(self.api, self.state, 247, self.policy,
                                                    "pending", owner_approved=True)
            self.state.update(ledger=ledger, handoff=handoff)
            with patch.object(session, "get_issue", return_value={"number": 247, "state": "closed", "state_reason": "not_planned"}):
                with self.assertRaises(ValueError):
                    session.closure_plan(self.api, self.state, 247, self.policy, "confirmed", owner_approved=True)
            with patch.object(session, "get_issue", return_value={"number": 247, "state": "closed", "state_reason": "completed"}):
                ledger, handoff = session.closure_plan(self.api, self.state, 247, self.policy,
                                                        "confirmed", owner_approved=True)
            self.assertEqual(ledger, self.state["ledger"])
            self.assertEqual(handoff["history"][:-1], self.state["handoff"]["history"])
            result = session.closure_status({**self.state, "handoff": handoff},
                                            {"number": 247, "state": "closed", "state_reason": "completed"})
            self.assertEqual(result["closure_synchronization"], "confirmed")
            self.assertFalse(result["production_integrated"])
        self.assertFalse(self.api.writes)

    def test_partial_failure_retains_pending_intent(self):
        archive = self.state["handoff"]["history"][-1]
        with patch.object(session, "verify_closure_basis", return_value=archive):
            ledger, handoff = session.closure_plan(self.api, self.state, 247, self.policy,
                                                    "pending", owner_approved=True)
            self.state.update(ledger=ledger, handoff=handoff)
            before = copy.deepcopy(self.state)
            with patch.object(self.api, "request", side_effect=OSError("lost response")), \
                    patch.object(session.install, "read_ref", return_value=self.state["ref"]), \
                    patch.object(session, "get_issue", return_value={"number": 247, "state": "open"}):
                with self.assertRaisesRegex(ValueError, "partial"):
                    session.complete_closure(self.api, self.state, 247, self.policy,
                                             owner_approved=True, apply=True)
            self.assertEqual(self.state, before)
            with patch.object(session, "get_issue", return_value={"number": 247, "state": "closed", "state_reason": "completed"}), \
                    patch.object(session, "save_closure", return_value={"status": "saved"}) as save:
                self.assertEqual(session.complete_closure(self.api, self.state, 247, self.policy,
                                                          owner_approved=True, apply=True)["status"], "saved")
                self.assertTrue(save.called)
        self.assertFalse(self.api.writes)

    def test_exact_evidence_and_historical_identity(self):
        historical = {session.HANDOFF: self.state["handoff"], session.LEDGER: self.state["ledger"],
                      "vib-install.json": {**self.state["manifest"], "target_repository": self.state["ledger"]["repository"]}}
        original_ancestry = gate.check_ancestry
        def ancestry(api, prefix, fix, head):
            if fix != head:
                return original_ancestry(api, prefix, fix, head)
        def read_text(api, prefix, path, ref):
            self.assertEqual(ref, self.policy["archive_ref"])
            return install.render(historical[path])
        with patch.object(install, "read_text", side_effect=read_text), \
                patch.object(gate, "check_ancestry", side_effect=ancestry):
            archive = session.verify_closure_basis(self.api, self.state, 247, self.policy)
            self.assertEqual(archive, self.state["handoff"]["history"][-1])
            self.api.run["conclusion"] = "failure"
            with self.assertRaises(ValueError):
                session.verify_closure_basis(self.api, self.state, 247, self.policy)
            self.api.run["conclusion"] = "success"
            with self.assertRaises(ValueError):
                session.verify_closure_basis(self.api, {**self.state, "closure_supported": False}, 247, self.policy)
            wrong = copy.deepcopy(self.policy)
            wrong["engineering"]["review"]["pull_request"] = 999
            with self.assertRaises(ValueError):
                session.verify_closure_basis(self.api, self.state, 247, wrong)
        self.assertFalse(self.api.writes)

    def test_full_fixture_apply_readback_and_idempotence(self):
        import base64
        import hashlib
        import json
        from test_session import BASE, HEAD, NEXT, TREE
        from test_engineering_completion import BRANCH

        prefix = self.state["prefix"]
        historical_ref = self.state["ref"]
        pending_ref, confirmed_ref = "8" * 40, "9" * 40
        current = {"number": 247, "state": "open", "state_reason": None}
        contents = {historical_ref: {session.LEDGER: install.render(self.state["ledger"]),
                    session.HANDOFF: install.render(self.state["handoff"]),
                    "vib-install.json": install.render({**self.state["manifest"],
                        "target_repository": self.state["ledger"]["repository"]})}}
        staged = {}
        original_request = self.api.request
        def request(method, path, body=None):
            if method == "GET" and path == prefix + "/issues/247":
                return copy.deepcopy(current)
            if method == "PATCH" and path == prefix + "/issues/247":
                self.assertEqual(body, {"state": "closed", "state_reason": "completed"})
                self.api.writes.append((method, path, copy.deepcopy(body)))
                current.update(body)
                return copy.deepcopy(current)
            if method == "GET" and path == prefix + "/git/ref/heads/trunk":
                return {"ref": "refs/heads/trunk", "object": {"type": "commit", "sha": BASE}}
            if method == "GET" and "/compare/" in path:
                first, last = path.rsplit("/", 1)[1].split("...")
                if first == last or (first == historical_ref and last in (pending_ref, confirmed_ref)):
                    return {"status": "identical" if first == last else "ahead",
                            "merge_base_commit": {"sha": first}}
            if method == "GET" and path.startswith(prefix + "/contents/"):
                filename, ref = path[len(prefix + "/contents/"):].split("?ref=")
                raw = contents[ref][filename].encode("utf-8")
                return {"type": "file", "encoding": "base64", "path": filename,
                        "content": base64.b64encode(raw).decode("ascii"),
                        "sha": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()}
            if method == "GET" and path in (prefix + "/git/commits/" + pending_ref,
                                             prefix + "/git/commits/" + confirmed_ref):
                return {"sha": path.rsplit("/", 1)[1], "tree": {"sha": TREE}}
            if method == "POST" and path == prefix + "/git/trees":
                self.assertEqual(body["base_tree"], TREE)
                self.api.writes.append((method, path, copy.deepcopy(body)))
                staged.update({entry["path"]: entry["content"] for entry in body["tree"]})
                return {"sha": TREE}
            if method == "POST" and path == prefix + "/git/commits":
                self.assertEqual(body["parents"], [self.api.ref])
                self.api.writes.append((method, path, copy.deepcopy(body)))
                new = pending_ref if self.api.ref == HEAD else confirmed_ref
                contents[new] = {**contents[self.api.ref], **staged}
                return {"sha": new}
            if method == "PATCH" and path == prefix + "/git/refs/heads/" + install.BRANCH:
                self.assertFalse(body["force"])
                self.api.writes.append((method, path, copy.deepcopy(body)))
                self.api.ref = body["sha"]
                return {}
            return original_request(method, path, body)
        def restored(pin):
            return {**self.state, "ref": pin, "product_sha": BASE,
                    "ledger": json.loads(install.read_text(self.api, prefix, session.LEDGER, pin)),
                    "handoff": json.loads(install.read_text(self.api, prefix, session.HANDOFF, pin))}
        with patch.object(self.api, "request", side_effect=request):
            ledger, handoff = session.closure_plan(self.api, self.state, 247, self.policy,
                                                    "pending", owner_approved=True)
            first = session.save_closure(self.api, self.state, ledger, handoff, 247,
                                          apply=True, owner_approved=True)
            self.assertEqual(first["installed_sha"], pending_ref)
            self.assertEqual(current["state"], "open")
            pending = restored(pending_ref)
            second = session.complete_closure(self.api, pending, 247, self.policy,
                                               owner_approved=True, apply=True)
            self.assertEqual(second["installed_sha"], confirmed_ref)
            final = restored(confirmed_ref)
            self.assertEqual(final["ledger"], self.state["ledger"])
            self.assertEqual(final["handoff"]["history"][:-2], self.state["handoff"]["history"])
            self.assertEqual(session.closure_status(final, current)["closure_synchronization"], "confirmed")
            self.assertEqual(install.read_ref(self.api, prefix, "trunk"), BASE)
            self.assertEqual(install.read_ref(self.api, prefix, BRANCH), NEXT)
            self.assertFalse(session.closure_status(final, current)["production_integrated"])
            before = copy.deepcopy(self.api.writes)
            self.assertEqual(session.complete_closure(self.api, final, 247, self.policy,
                                                       owner_approved=True, apply=True)["status"], "already_confirmed")
            self.assertEqual(self.api.writes, before)
            self.assertEqual(sum(method == "PATCH" and path.endswith("/issues/247")
                                 for method, path, _ in self.api.writes), 1)

    def test_legacy_closure_cannot_replace_archived_pins(self):
        review = self.policy["engineering"]["review"]
        expected = {"fix_sha": review["issues"][0]["fix_sha"],
                    "candidate_sha": review["head_sha"], "pull_request": review["pull_request"]}
        original = copy.deepcopy(self.state)
        for field, wrong in ((None, None), ("fix_sha", "7" * 40),
                             ("candidate_sha", "6" * 40), ("pull_request", 999),
                             ("empty", None)):
            with self.subTest(field=field):
                self.state = copy.deepcopy(original)
                archive = self.state["handoff"]["history"][-1]
                archive["decision"] = ("Owner reviewed PR #" + str(review["pull_request"])
                    + " fix " + expected["fix_sha"] + " candidate " + expected["candidate_sha"]
                    + " merge " + review["merge_sha"])
                archive["handoff"].update(expected)
                if field == "empty":
                    archive["handoff"].update({key: None for key in expected})
                    archive["handoff"]["evidence"] = []
                    for key in session.PIN_KEYS:
                        archive["handoff"].pop(key, None)
                elif field:
                    archive["handoff"][field] = wrong
                policy = {**self.policy, "archive_digest": session.closure_digest(archive)}
                historical = {session.HANDOFF: self.state["handoff"],
                              session.LEDGER: self.state["ledger"],
                              "vib-install.json": {**self.state["manifest"],
                                 "target_repository": self.state["ledger"]["repository"]}}
                with patch.object(install, "read_text", side_effect=lambda api, prefix, path, ref:
                                  install.render(historical[path])), \
                        patch.object(gate, "check_ancestry"), \
                        patch("tools.standard.verify_merged_destination") as verify:
                    if field in (None, "empty"):
                        self.assertEqual(session.verify_closure_basis(self.api, self.state, 247, policy), archive)
                        verify.assert_called_once()
                    else:
                        with self.assertRaisesRegex(ValueError, "archived handoff pin: " + field):
                            session.verify_closure_basis(self.api, self.state, 247, policy)
                        verify.assert_not_called()
        self.assertFalse(self.api.writes)
