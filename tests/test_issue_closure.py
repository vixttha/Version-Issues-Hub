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
                    patch.object(session, "save", return_value={"status": "saved"}) as save:
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
