"""Regression reproductions for stranded product integration (#96)."""
import copy
import unittest

from tools import session
from test_session import Fake, state, FIX, CANDIDATE, RUN


class IntegrationIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.api = Fake()
        self.state = state()

    def reach_head(self):
        self.state["ledger"], self.state["handoff"] = session.claim(
            self.api, self.state, 247, ["test"], "Fix")
        for kwargs in (dict(fix=FIX, candidate=CANDIDATE, pr=8),
                       dict(evidence=[RUN]), {}):
            self.state["ledger"], self.state["handoff"] = session.advance(
                self.api, self.state, "next", **kwargs)

    def test_unbounded_deferred_work_blocks_unrelated_claim(self):
        self.reach_head()
        self.state["ledger"], self.state["handoff"] = session.finish(
            self.api, self.state, "deferred", "Engineering complete, integration later")
        before = copy.deepcopy(self.state)
        with self.assertRaisesRegex(ValueError, "integration debt"):
            session.claim(self.api, self.state, 248, ["test second"], "New work")
        self.assertEqual(self.state, before)
        self.assertEqual(self.api.writes, [])

    def test_unbounded_staged_work_blocks_unrelated_claim(self):
        self.reach_head()
        self.state["ledger"], self.state["handoff"] = session.finish(
            self.api, self.state, "staged", "Owner stages")
        before = copy.deepcopy(self.state)
        with self.assertRaisesRegex(ValueError, "integration debt"):
            session.claim(self.api, self.state, 248, ["test second"], "New work")
        self.assertEqual(self.state, before)
        self.assertEqual(self.api.writes, [])

    def test_same_deferred_issue_can_be_recovered(self):
        self.reach_head()
        self.state["ledger"], self.state["handoff"] = session.finish(
            self.api, self.state, "deferred", "Engineering complete, integration later")
        ledger, handoff = session.claim(
            self.api, self.state, 247, ["test"], "Reconcile original issue")
        self.assertEqual(handoff["active"]["issue"], 247)
        self.assertEqual(ledger["issues"][0]["version"], "v1.0.6.1")
        self.assertEqual(handoff["history"], self.state["handoff"]["history"])
