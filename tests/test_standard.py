import copy
import unittest
from unittest.mock import patch
from tools import standard, session
from test_gate import Fake, fixture, REPO, HEAD, BASE, SOURCE, PREFIX

class StandardTests(unittest.TestCase):
    def setUp(self):
        self.policy, self.state = fixture()
        self.policy.pop("publisher_app_id")
        for row in self.policy["issues"]:
            row["criteria"][0]["checks"] = [{"run":123, "attempt":1, "workflow_id":52,
                "job_name":"product-test", "steps":["Run acceptance"]}]
        self.api = Fake()
        self.api.run.update(head_sha=HEAD, event="pull_request", pull_requests=[
            {"number":8,"head":{"sha":HEAD},"base":{"sha":BASE}}])
        original = self.api.request
        self.api.request = lambda method,path,body=None: (
            {"id":42,"full_name":REPO,"private":False} if method=="GET" and path==PREFIX
            else original(method,path,body))
        patcher = patch.object(session,"load",return_value=self.state)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_standard_needs_no_app_and_never_publishes(self):
        result = standard.evaluate(self.api, REPO, self.policy)
        self.assertEqual(result["status"], "review_required")
        self.assertFalse(result["merge_enforced"])
        self.assertFalse(result["published"])
        self.assertEqual(len(result["issues"]),2)
        self.assertEqual(self.api.writes,[])

    def test_stale_run_rejected(self):
        self.api.run["run_attempt"]=2
        with self.assertRaisesRegex(ValueError,"stale"):
            standard.evaluate(self.api,REPO,self.policy)

    def test_wrong_pr_rejected(self):
        self.api.run["pull_requests"][0]["number"]=9
        with self.assertRaisesRegex(ValueError,"association"):
            standard.evaluate(self.api,REPO,self.policy)

    def test_skipped_step_rejected(self):
        self.api.jobs[0]["steps"][0]["conclusion"]="skipped"
        with self.assertRaisesRegex(ValueError,"step"):
            standard.evaluate(self.api,REPO,self.policy)

    def test_incomplete_scope_rejected(self):
        self.policy["issues"].pop()
        with self.assertRaisesRegex(ValueError,"all staged"):
            standard.evaluate(self.api,REPO,self.policy)

    def test_stale_candidate_rejected(self):
        self.api.pr["head"]["sha"]=SOURCE
        with self.assertRaisesRegex(ValueError,"stale"):
            standard.evaluate(self.api,REPO,self.policy)

    def test_private_target_refused(self):
        self.api.request=lambda method,path,body=None: {"id":42,"private":True}
        with self.assertRaisesRegex(ValueError,"public target"):
            standard.evaluate(self.api,REPO,self.policy)


    def test_head_only_run_without_base_association_rejected(self):
        self.api.run["pull_requests"]=[]
        with self.assertRaisesRegex(ValueError,"association"):
            standard.evaluate(self.api,REPO,self.policy)

    def test_legacy_unpinned_stage_requires_refresh(self):
        self.state["handoff"]["history"][0]["handoff"].pop("integration_base_sha")
        self.state["handoff"]["history"][0]["handoff"].pop("integration_merge_sha")
        with self.assertRaisesRegex(ValueError,"unpinned"):
            standard.evaluate(self.api,REPO,self.policy)


    def test_unrelated_ledger_revision_requires_repin_not_new_run(self):
        before=copy.deepcopy(self.state["handoff"]["history"])
        self.assertEqual(standard.evaluate(self.api,REPO,self.policy)["status"],"review_required")
        self.state["ledger"]["issues"].append({"issue":249,"version":"v1.0.6.3",
                                               "state":"blocked","acceptance":["Other work"]})
        new_ref="2"*40
        self.state["ref"]=new_ref
        self.api.refs["Version-Issues-Hub"]=new_ref
        # The old policy is still pinned to the old installed revision.
        with self.assertRaisesRegex(ValueError,"Installed state advanced"):
            standard.evaluate(self.api,REPO,self.policy)
        self.policy["installed_sha"]=new_ref
        self.assertEqual(standard.evaluate(self.api,REPO,self.policy)["status"],"review_required")
        self.assertEqual(self.state["handoff"]["history"],before)
        self.assertEqual(self.api.writes,[])
