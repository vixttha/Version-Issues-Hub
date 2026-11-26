"""Adversarial partial API metadata: explicit fail-closed requirements.

These probes intentionally remain red if the pinned product accepts incomplete or
contradictory PR metadata. They are not expectedFailure and do not perform writes.
"""
import copy
import unittest
from unittest.mock import patch
import test_completion as fixtures
from tools import gate, session
from record import run_suite

class Partial(unittest.TestCase):
    def gate_reject(self,change):
        policy,state=fixtures.g.fixture()
        api=fixtures.g.Fake()
        change(api)
        with patch.object(session,"load",return_value=state):
            before=copy.deepcopy(state)
            with self.assertRaises(ValueError):
                gate.evaluate(api,fixtures.g.REPO,policy)
            self.assertEqual(state,before)
        self.assertEqual(api.writes,[])
    def stage_reject(self,change):
        c=fixtures.Completion("test_finish_worker")
        c.setUp()
        c.head()
        change(c.api)
        c.reject(lambda:c.finish("staged"))
    def test_gate_missing_merged(self): self.gate_reject(lambda a:a.pr.pop("merged"))
    def test_gate_null_merged(self): self.gate_reject(lambda a:a.pr.update(merged=None))
    def test_gate_string_merged(self): self.gate_reject(lambda a:a.pr.update(merged="false"))
    def test_stage_missing_merged(self): self.stage_reject(lambda a:a.pr.pop("merged"))
    def test_stage_null_merged(self): self.stage_reject(lambda a:a.pr.update(merged=None))
    def test_stage_string_merged(self): self.stage_reject(lambda a:a.pr.update(merged="false"))
    def test_collection_boolean_total(self):
        api=fixtures.g.Fake()
        with patch.object(api,"request",return_value={"total_count":True,"jobs":[{"id":1}]}):
            with self.assertRaises(ValueError): gate.exact_collection(api,"/synthetic","jobs")
    def test_integrated_open_pr_contradiction(self):
        c=fixtures.Completion("test_finish_worker")
        c.setUp(); c.head()
        c.api.pr.update(state="open",merged=True)
        c.reject(c.finish)
    def test_reconcile_open_pr_contradiction(self):
        c=fixtures.Completion("test_finish_worker")
        c.setUp(); c.staged()
        c.api.pr.update(state="open",merged=True)
        c.reject(c.reconcile)

if __name__=="__main__":
    run_suite(unittest.defaultTestLoader.loadTestsFromTestCase(Partial),9,"partial")
