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
                                     "confirmed", owner_approved=True, execution_id="1" * 32)
        self.assertFalse(self.api.writes)

    def test_confirmation_requires_matching_readback(self):
        archive = self.state["handoff"]["history"][-1]
        with patch.object(session, "verify_closure_basis", return_value=archive):
            ledger, handoff = session.closure_plan(self.api, self.state, 247, self.policy,
                                                    "pending", owner_approved=True)
            self.state.update(ledger=ledger, handoff=handoff)
            execution = "1" * 32
            ledger, handoff = session.closure_plan(self.api, self.state, 247, self.policy,
                        "executing", owner_approved=True, execution_id=execution)
            self.state.update(ledger=ledger, handoff=handoff)
            with patch.object(session, "get_issue", return_value={"number": 247, "state": "closed", "state_reason": "not_planned"}):
                with self.assertRaises(ValueError):
                    session.closure_plan(self.api, self.state, 247, self.policy, "confirmed", owner_approved=True, execution_id="1" * 32)
            with patch.object(session, "get_issue", return_value={"number": 247, "state": "closed", "state_reason": "completed"}):
                ledger, handoff = session.closure_plan(self.api, self.state, 247, self.policy,
                                                        "confirmed", owner_approved=True, execution_id="1" * 32)
            self.assertEqual(ledger, self.state["ledger"])
            self.assertEqual(handoff["history"][:-1], self.state["handoff"]["history"])
            result = session.closure_status({**self.state, "handoff": handoff},
                                            {"number": 247, "state": "closed", "state_reason": "completed"})
            self.assertEqual(result["closure_synchronization"], "state_matches_historical_receipt")
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
            with patch.object(session, "save_closure", side_effect=ValueError("lost acquisition response")):
                with self.assertRaisesRegex(ValueError, "partial"):
                    session.complete_closure(self.api, self.state, 247, self.policy,
                                             owner_approved=True, apply=True)
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
        self.exercise_publication(cancel=False)

    def test_cancel_stale_intent_and_resume_work(self):
        self.exercise_publication(cancel=True)

    def test_competing_cancel_wins_execution_cas(self):
        self.exercise_publication(cancel=False, interleave="cancel_wins")

    def test_competing_completion_wins_cancel_cas(self):
        self.exercise_publication(cancel=False, interleave="complete_wins")

    def test_restart_after_lost_issue_response_requires_recovery(self):
        self.exercise_publication(cancel=False, interleave="lost_issue_response")

    def exercise_publication(self, *, cancel, interleave=None):
        import base64
        import hashlib
        import json
        from test_session import BASE, HEAD, NEXT, TREE
        from test_engineering_completion import BRANCH

        prefix = self.state["prefix"]
        historical_ref = self.state["ref"]
        pending_ref, executing_ref, confirmed_ref = "8" * 40, "7" * 40, "9" * 40
        current = {"number": 247, "state": "open", "state_reason": None}
        contents = {historical_ref: {session.LEDGER: install.render(self.state["ledger"]),
                    session.HANDOFF: install.render(self.state["handoff"]),
                    "vib-install.json": install.render({**self.state["manifest"],
                        "target_repository": self.state["ledger"]["repository"]})}}
        staged = {}
        parents = {}
        rival = {}
        original_request = self.api.request
        def request(method, path, body=None):
            if method == "GET" and path == prefix + "/issues/247":
                return copy.deepcopy(current)
            if method == "PATCH" and path == prefix + "/issues/247":
                self.assertEqual(body, {"state": "closed", "state_reason": "completed"})
                self.api.writes.append((method, path, copy.deepcopy(body)))
                current.update(body)
                if interleave == "lost_issue_response":
                    raise OSError("issue response lost after mutation")
                return copy.deepcopy(current)
            if method == "GET" and path == prefix + "/git/ref/heads/trunk":
                return {"ref": "refs/heads/trunk", "object": {"type": "commit", "sha": BASE}}
            if method == "GET" and "/compare/" in path:
                first, last = path.rsplit("/", 1)[1].split("...")
                if first == last or (first == historical_ref and last in (pending_ref, executing_ref, confirmed_ref)):
                    return {"status": "identical" if first == last else "ahead",
                            "merge_base_commit": {"sha": first}}
            if method == "GET" and path.startswith(prefix + "/contents/"):
                filename, ref = path[len(prefix + "/contents/"):].split("?ref=")
                raw = contents[ref][filename].encode("utf-8")
                return {"type": "file", "encoding": "base64", "path": filename,
                        "content": base64.b64encode(raw).decode("ascii"),
                        "sha": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()}
            if method == "GET" and path in (prefix + "/git/commits/" + pending_ref,
                                             prefix + "/git/commits/" + executing_ref,
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
                history = json.loads(staged[session.HANDOFF])["history"]
                status = session.closure_receipt(history[-1])["status"]
                new = {"pending": pending_ref, "executing": executing_ref,
                       "confirmed": confirmed_ref, "cancelled": confirmed_ref}[status]
                contents[new] = {**contents[self.api.ref], **staged}
                parents[new] = body["parents"][0]
                return {"sha": new}
            if method == "PATCH" and path == prefix + "/git/refs/heads/" + install.BRANCH:
                self.assertFalse(body["force"])
                self.api.writes.append((method, path, copy.deepcopy(body)))
                new = body["sha"]
                if interleave == "cancel_wins" and new == executing_ref:
                    contents[confirmed_ref] = {**contents[pending_ref],
                        session.HANDOFF: install.render(rival["handoff"])}
                    parents[confirmed_ref] = pending_ref
                    self.api.ref = confirmed_ref
                elif interleave == "complete_wins" and new == confirmed_ref and self.api.ref == pending_ref:
                    contents[executing_ref] = {**contents[pending_ref],
                        session.HANDOFF: install.render(rival["handoff"])}
                    parents[executing_ref] = pending_ref
                    self.api.ref = executing_ref
                if parents[new] != self.api.ref:
                    raise install.ApiError(422)
                self.api.ref = new
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
            if interleave == "cancel_wins":
                _, rival["handoff"] = session.cancel_closure_plan(
                    self.api, pending, 247, self.policy, "Owner cancels", owner_approved=True)
                with self.assertRaisesRegex(ValueError, "partial"):
                    session.complete_closure(self.api, pending, 247, self.policy,
                                             owner_approved=True, apply=True)
                final = restored(confirmed_ref)
                self.assertEqual(session.closure_records(final["handoff"], 247)[-1]["status"], "cancelled")
                self.assertIsNone(session.pending_closure(final["handoff"]))
                self.assertEqual(current["state"], "open")
                self.assertFalse(any(method == "PATCH" and "/issues/" in path
                                     for method, path, _ in self.api.writes))
                return
            if interleave == "complete_wins":
                _, rival["handoff"] = session.closure_plan(
                    self.api, pending, 247, self.policy, "executing",
                    owner_approved=True, execution_id="1" * 32)
                ledger, handoff = session.cancel_closure_plan(
                    self.api, pending, 247, self.policy, "Owner cancels", owner_approved=True)
                with self.assertRaises(install.ApiError):
                    session.save_closure(self.api, pending, ledger, handoff, 247,
                                         apply=True, owner_approved=True)
                executing = restored(executing_ref)
                self.assertEqual(session.pending_closure(executing["handoff"])["execution_id"], "1" * 32)
                with self.assertRaisesRegex(ValueError, "already acquired"):
                    session.complete_closure(self.api, executing, 247, self.policy,
                                             owner_approved=True, apply=True)
                self.assertEqual(current["state"], "open")
                self.assertFalse(any(method == "PATCH" and "/issues/" in path
                                     for method, path, _ in self.api.writes))
                return
            if interleave == "lost_issue_response":
                with self.assertRaisesRegex(ValueError, "partial"):
                    session.complete_closure(self.api, pending, 247, self.policy,
                                             owner_approved=True, apply=True)
                restarted = restored(executing_ref)
                execution = session.pending_closure(restarted["handoff"])["execution_id"]
                self.assertEqual(current["state"], "closed")
                before = copy.deepcopy(self.api.writes)
                with self.assertRaisesRegex(ValueError, "already acquired"):
                    session.complete_closure(self.api, restarted, 247, self.policy,
                                             owner_approved=True, apply=True)
                with self.assertRaises(ValueError):
                    session.cancel_closure_plan(self.api, restarted, 247, self.policy,
                                                "Owner recovery", owner_approved=True)
                self.assertEqual(before, self.api.writes)
                ledger, handoff = session.cancel_closure_plan(
                    self.api, restarted, 247, self.policy, "Owner stopped executor and inspected closed issue",
                    owner_approved=True, recovery_execution=execution)
                session.save_closure(self.api, restarted, ledger, handoff, 247,
                                     apply=True, owner_approved=True)
                final = restored(confirmed_ref)
                last = session.closure_records(final["handoff"], 247)[-1]
                self.assertEqual(last["execution_id"], execution)
                self.assertEqual(last["cancellation"]["state"], "closed")
                self.assertEqual(session.closure_status(final, current)["closure_synchronization"], "cancelled")
                self.assertEqual(sum(method == "PATCH" and "/issues/" in path
                                     for method, path, _ in self.api.writes), 1)
                return
            if cancel:
                self.api.run["run_attempt"] = 2
                with self.assertRaises(ValueError):
                    session.complete_closure(self.api, pending, 247, self.policy,
                                             owner_approved=True, apply=True)
                self.assertEqual(session.inspect(self.api, pending)["pending_closure"]["issue"], 247)
                self.assertEqual(session.inspect(self.api, pending)["status"], "closure_reconciliation_required")
                with self.assertRaises(ValueError):
                    session.claim(self.api, pending, 248, ["new"], "Next")
                with self.assertRaises(ValueError):
                    session.cancel_closure_plan(self.api, pending, 247, self.policy, "Cancel")
                with self.assertRaises(ValueError):
                    session.cancel_closure_plan(self.api, pending, 247, {**self.policy, "owner_decision": "Different"},
                                                "Cancel", owner_approved=True)
                current.update(state="closed", state_reason="not_planned")
                decision = "Owner abandoned stale intent; no concurrent closure execution"
                ledger, handoff = session.cancel_closure_plan(self.api, pending, 247, self.policy,
                                                               decision, owner_approved=True)
                second = session.save_closure(self.api, pending, ledger, handoff, 247,
                                               apply=True, owner_approved=True)
                self.assertEqual(second["installed_sha"], confirmed_ref)
                final = restored(confirmed_ref)
                self.assertEqual(final["ledger"], self.state["ledger"])
                self.assertEqual(final["handoff"]["history"][:-1], pending["handoff"]["history"])
                receipt = session.closure_records(final["handoff"], 247)[-1]
                self.assertEqual(receipt["status"], "cancelled")
                self.assertEqual(receipt["policy"], self.policy)
                self.assertEqual(receipt["cancellation"], {"owner_decision": decision,
                                 "state": "closed", "state_reason": "not_planned"})
                self.assertEqual(session.closure_status(final, current)["closure_synchronization"], "cancelled")
                self.assertIsNone(session.pending_closure(final["handoff"]))
                self.assertFalse(session.closure_status(final, current)["production_integrated"])
                before = copy.deepcopy(self.api.writes)
                self.assertEqual(session.cancel_closure_plan(self.api, final, 247, self.policy, decision,
                                     owner_approved=True), (final["ledger"], final["handoff"]))
                with self.assertRaises(ValueError):
                    session.complete_closure(self.api, final, 247, self.policy, owner_approved=True, apply=True)
                self.assertEqual(self.api.writes, before)
                self.assertFalse(any(method == "PATCH" and "/issues/" in path
                                     for method, path, _ in self.api.writes))
                new_ledger, new_handoff = session.claim(self.api, final, 248, ["new"], "Next")
                self.assertEqual(new_handoff["active"]["issue"], 248)
                self.assertEqual(new_ledger["issues"][0], final["ledger"]["issues"][0])
                return
            second = session.complete_closure(self.api, pending, 247, self.policy,
                                               owner_approved=True, apply=True)
            self.assertEqual(second["installed_sha"], confirmed_ref)
            final = restored(confirmed_ref)
            self.assertEqual(final["ledger"], self.state["ledger"])
            self.assertEqual(final["handoff"]["history"][:-3], self.state["handoff"]["history"])
            receipts = session.closure_records(final["handoff"], 247)
            self.assertEqual([r["status"] for r in receipts], ["pending", "executing", "confirmed"])
            self.assertEqual(receipts[1]["execution_id"], receipts[2]["execution_id"])
            self.assertFalse(session.closure_status(final, current)["closure_event_verified"])
            self.assertEqual(session.closure_status(final, current)["closure_synchronization"], "state_matches_historical_receipt")
            self.assertEqual(install.read_ref(self.api, prefix, "trunk"), BASE)
            self.assertEqual(install.read_ref(self.api, prefix, BRANCH), NEXT)
            self.assertFalse(session.closure_status(final, current)["production_integrated"])
            before = copy.deepcopy(self.api.writes)
            self.assertEqual(session.complete_closure(self.api, final, 247, self.policy,
                                                       owner_approved=True, apply=True)["status"], "historical_receipt_matches_state")
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

    def test_cancelled_intent_cannot_be_replayed(self):
        archive = self.state["handoff"]["history"][-1]
        with patch.object(session, "verify_closure_basis", return_value=archive):
            ledger, handoff = session.closure_plan(self.api, self.state, 247, self.policy,
                                                    "pending", owner_approved=True)
            self.state.update(ledger=ledger, handoff=handoff)
            ledger, handoff = session.cancel_closure_plan(self.api, self.state, 247, self.policy,
                                                           "Owner cancelled", owner_approved=True)
            self.state.update(ledger=ledger, handoff=handoff)
            with self.assertRaises(ValueError):
                session.complete_closure(self.api, self.state, 247, self.policy, owner_approved=True, apply=True)
            with self.assertRaises(ValueError):
                session.closure_plan(self.api, self.state, 247, self.policy, "pending", owner_approved=True)
            replacement = {**self.policy, "owner_decision": "New reviewed closure intent"}
            ledger, handoff = session.closure_plan(self.api, self.state, 247, replacement,
                                                    "pending", owner_approved=True)
            self.assertEqual(handoff["history"][:-1], self.state["handoff"]["history"])
            self.assertEqual(session.pending_closure(handoff)["policy_digest"], session.closure_digest(replacement))
            self.state.update(ledger=ledger, handoff=handoff)
            with self.assertRaises(ValueError):
                session.cancel_closure_plan(self.api, self.state, 247, self.policy, "Old",
                                            owner_approved=True)
        self.assertFalse(self.api.writes)

    def test_reclaimed_issue_cannot_report_confirmed_closure(self):
        archive = self.state["handoff"]["history"][-1]
        with patch.object(session, "verify_closure_basis", return_value=archive):
            ledger, handoff = session.closure_plan(self.api, self.state, 247, self.policy,
                                                    "pending", owner_approved=True)
            self.state.update(ledger=ledger, handoff=handoff)
            ledger, handoff = session.closure_plan(self.api, self.state, 247, self.policy,
                        "executing", owner_approved=True, execution_id="1" * 32)
            self.state.update(ledger=ledger, handoff=handoff)
            closed = {"number": 247, "state": "closed", "state_reason": "completed"}
            with patch.object(session, "get_issue", return_value=closed):
                ledger, handoff = session.closure_plan(self.api, self.state, 247, self.policy,
                                                        "confirmed", owner_approved=True, execution_id="1" * 32)
            self.state.update(ledger=ledger, handoff=handoff)
            self.assertEqual(session.closure_status(self.state, closed)["closure_synchronization"], "state_matches_historical_receipt")
            # External reopen and reclose with no ledger transition is not event proof.
            reopened = {**closed, "state": "open", "state_reason": "reopened"}
            self.assertEqual(session.closure_status(self.state, reopened)["closure_synchronization"], "conflict")
            reclosed = session.closure_status(self.state, closed)
            self.assertFalse(reclosed["closure_event_verified"])
            self.assertTrue(reclosed["historical_confirmation_recorded"])
            ledger, handoff = session.claim(self.api, self.state, 247, ["test"], "Reopened work")
            self.state.update(ledger=ledger, handoff=handoff)
            result = session.closure_status(self.state, closed)
            self.assertEqual(result["closure_synchronization"], "conflict")
            self.assertEqual(result["engineering_completion"], "unverified")
            self.assertEqual(result["ledger_state"], "in_progress")
            self.assertFalse(result["production_integrated"])
            with patch.object(session, "get_issue", return_value=closed):
                self.assertEqual(session.inspect(self.api, self.state, 247)["lifecycle"], result)
        self.assertFalse(self.api.writes)

    def test_execution_claim_blocks_replay_cancel_and_lifecycle(self):
        from tools import lifecycle
        self.state["manifest"]["enforcement"] = "disabled"
        archive = self.state["handoff"]["history"][-1]
        with patch.object(session, "verify_closure_basis", return_value=archive):
            ledger, handoff = session.closure_plan(self.api, self.state, 247, self.policy,
                                                    "pending", owner_approved=True)
            self.state.update(ledger=ledger, handoff=handoff)
            for stage in ("pending", "executing"):
                with self.assertRaisesRegex(ValueError, "unresolved closure"):
                    session.reconcile(self.api, self.state, 248, "Unrelated integration")
                proposed = copy.deepcopy(self.state["ledger"])
                proposed["issues"].append({"issue": 248, "version": "v1.0.6.2",
                                           "state": "assigned", "acceptance": ["Other"]})
                with self.assertRaisesRegex(ValueError, "unresolved closure"):
                    session.save(self.api, self.state, proposed, self.state["handoff"], issue=248)
                with patch.object(session, "load", return_value=self.state):
                    with self.assertRaisesRegex(ValueError, "unresolved closure"):
                        lifecycle.upgrade(self.api, self.state["ledger"]["repository"],
                                          self.state["ref"], "5" * 40)
                    with self.assertRaisesRegex(ValueError, "unresolved closure"):
                        lifecycle.prepare_retirement(self.api, self.state["ledger"]["repository"],
                                                     self.state["ref"])
                if stage == "pending":
                    ledger, handoff = session.closure_plan(self.api, self.state, 247, self.policy,
                            "executing", owner_approved=True, execution_id="1" * 32)
                    self.state.update(ledger=ledger, handoff=handoff)
            self.assertEqual(session.pending_closure(self.state["handoff"])["execution_id"], "1" * 32)
            with self.assertRaisesRegex(ValueError, "already acquired"):
                session.complete_closure(self.api, self.state, 247, self.policy,
                                         owner_approved=True, apply=True)
            with self.assertRaises(ValueError):
                session.closure_plan(self.api, self.state, 247, self.policy, "executing",
                                     owner_approved=True, execution_id="2" * 32)
            for recovery in (None, "2" * 32):
                with self.assertRaises(ValueError):
                    session.cancel_closure_plan(self.api, self.state, 247, self.policy, "Owner recovery",
                              owner_approved=True, recovery_execution=recovery)
            ledger, handoff = session.cancel_closure_plan(self.api, self.state, 247, self.policy,
                "Owner stopped executor and reconciled issue", owner_approved=True,
                recovery_execution="1" * 32)
            self.assertEqual(handoff["history"][:-1], self.state["handoff"]["history"])
            self.assertIsNone(session.pending_closure(handoff))
            self.assertEqual(session.closure_records(handoff, 247)[-1]["execution_id"], "1" * 32)
            self.state.update(ledger=ledger, handoff=handoff)
            _, claimed = session.claim(self.api, self.state, 248, ["new"], "Resume work")
            self.assertEqual(claimed["active"]["issue"], 248)
        self.assertFalse(self.api.writes)

    def test_reserved_prefix_compatibility_fails_closed(self):
        archive = self.state["handoff"]["history"][-1]
        with patch.object(session, "verify_closure_basis", return_value=archive):
            _, handoff = session.closure_plan(self.api, self.state, 247, self.policy,
                                               "pending", owner_approved=True)
        with self.assertRaisesRegex(ValueError, "prefix"):
            session.require_closure_compatible_history(handoff, False)
        session.require_closure_compatible_history(handoff, True)
        session.require_closure_compatible_history(self.state["handoff"], False)
        self.assertFalse(session.supports_closure_execution({"tools/session.py": session.CLOSURE_DECISION}))
        self.assertFalse(self.api.writes)

    def test_ambiguous_or_lost_execution_acquisition_never_patches_issue(self):
        archive = self.state["handoff"]["history"][-1]
        with patch.object(session, "verify_closure_basis", return_value=archive):
            ledger, handoff = session.closure_plan(self.api, self.state, 247, self.policy,
                                                    "pending", owner_approved=True)
            self.state.update(ledger=ledger, handoff=handoff)
            for result in ({"status": "saved", "installed_sha": self.state["ref"],
                            "recovered_response": True},
                           {"status": "saved", "installed_sha": "8" * 40}):
                with self.subTest(result=result), \
                        patch.object(session, "save_closure", return_value=result):
                    with self.assertRaisesRegex(ValueError, "partial"):
                        session.complete_closure(self.api, self.state, 247, self.policy,
                                                 owner_approved=True, apply=True)
            with patch.object(session, "save_closure", side_effect=session.HandoffStale("competing writer")):
                with self.assertRaisesRegex(ValueError, "partial"):
                    session.complete_closure(self.api, self.state, 247, self.policy,
                                             owner_approved=True, apply=True)
        self.assertFalse(self.api.writes)
