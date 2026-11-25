import copy
import unittest
from unittest.mock import patch
from tools import gate, install, session

REPO = "example/existing"
PREFIX = "/repos/" + REPO
SOURCE = "a" * 40
STATE = "b" * 40
BASE = "c" * 40
HEAD = "d" * 40
MERGE = "e" * 40
FIX = "f" * 40
RUN_HEAD = "1" * 40
RUN = "https://github.com/" + REPO + "/actions/runs/123/attempts/1"
TEST = {"name": "Product / acceptance", "app_id": 87, "workflow_id": 52,
        "run_head_sha": RUN_HEAD, "job_name": "product-test", "steps": ["Run acceptance"]}

def fixture():
    policy = {"schema_version": 1, "repository": REPO, "repository_id": 42,
              "product_branch": "trunk", "source_sha": SOURCE, "installed_sha": STATE,
              "pull_request": 8, "head_sha": HEAD, "base_sha": BASE, "merge_sha": MERGE,
              "publisher_app_id": 88, "issues": []}
    ledger = {"schema_version": 1, "repository": REPO, "issues": []}
    history = []
    for issue, version in [(247, "v1.0.6.1"), (248, "v1.0.6.2")]:
        policy["issues"].append({"issue": issue, "version": version, "fix_sha": FIX,
                                 "criteria": [{"text": "Check", "checks": [copy.deepcopy(TEST)]}]})
        ledger["issues"].append({"issue": issue, "version": version, "state": "staged", "acceptance": ["Check"]})
        active = {"issue": issue, "version": version, "phase": "Head", "next_action": "Owner decision",
                  "fix_sha": FIX, "candidate_sha": HEAD, "pull_request": 8, "evidence": [RUN],
                  "integration_base_sha": BASE, "integration_merge_sha": MERGE}
        history.append({"handoff": active, "disposition": "staged", "decision": "Owner stages", "merged_sha": None})
    state = {"prefix": PREFIX, "ref": STATE, "product_sha": BASE,
             "manifest": {"target_repository_id": 42, "target_repository": REPO,
                          "product_branch": "trunk", "source_sha": SOURCE},
             "ledger": ledger, "handoff": {"schema_version": 1, "active": None, "history": history}}
    return policy, state

class Fake:
    def __init__(self):
        self.refs = {"trunk": BASE, install.BRANCH: STATE}
        self.pr = {"number": 8, "state": "open", "merged": False, "merge_commit_sha": MERGE,
                   "base": {"ref": "trunk", "sha": BASE, "repo": {"id": 42}},
                   "head": {"sha": HEAD, "repo": {"id": 42}}}
        self.parents = [BASE, HEAD]
        self.ancestor = True
        self.checks = [{"id": 99, "name": TEST["name"], "head_sha": MERGE,
                        "app": {"id": 87, "slug": "trusted-test-app"}, "status": "completed",
                        "conclusion": "success", "details_url": RUN}]
        self.run = {"id": 123, "run_attempt": 1, "workflow_id": 52, "head_sha": RUN_HEAD,
                    "repository": {"id": 42}, "status": "completed", "conclusion": "success"}
        self.jobs = [{"id": 456, "name": "product-test", "status": "completed", "conclusion": "success",
                      "steps": [{"name": "Run acceptance", "status": "completed", "conclusion": "success"}]}]
        self.writes = []
        self.gate_checks = []
        self.publisher_app = 88
    def request(self, method, path, body=None):
        if method == "POST" and path == PREFIX + "/check-runs":
            self.writes.append(body)
            check = {**body, "id": 100, "app": {"id": self.publisher_app, "slug": "trusted-vib-app"}, "conclusion": None}
            self.gate_checks.append(check)
            return copy.deepcopy(check)
        if method == "PATCH" and path == PREFIX + "/check-runs/100":
            self.writes.append(body)
            self.gate_checks[0].update(body)
            return copy.deepcopy(self.gate_checks[0])
        if method != "GET":
            raise AssertionError("Unexpected mutation")
        if path == PREFIX:
            return {"id": 42, "full_name": REPO}
        if path == PREFIX + "/check-runs/100":
            return copy.deepcopy(self.gate_checks[0])
        if path.startswith(PREFIX + "/commits/" + MERGE + "/check-runs?filter=all"):
            return {"total_count": len(self.gate_checks), "check_runs": copy.deepcopy(self.gate_checks)}
        if path == PREFIX + "/pulls/8":
            return self.pr
        if path.startswith(PREFIX + "/git/ref/heads/"):
            name = path.split("/heads/")[-1]
            return {"ref": "refs/heads/" + name, "object": {"type": "commit", "sha": self.refs[name]}}
        if path == PREFIX + "/git/commits/" + MERGE:
            return {"sha": MERGE, "parents": [{"sha": s} for s in self.parents]}
        if path.startswith(PREFIX + "/issues/"):
            return {"number": int(path.rsplit("/", 1)[-1]), "state": "open"}
        if path == PREFIX + "/compare/" + FIX + "..." + HEAD:
            return {"status": "ahead" if self.ancestor else "diverged", "merge_base_commit": {"sha": FIX}}
        if path.startswith(PREFIX + "/commits/" + MERGE + "/check-runs?"):
            return {"total_count": len(self.checks), "check_runs": self.checks}
        if path in (PREFIX + "/actions/runs/123", PREFIX + "/actions/runs/123/attempts/1"):
            return self.run
        if path == PREFIX + "/actions/runs/123/attempts/1/jobs?per_page=100":
            return {"total_count": len(self.jobs), "jobs": self.jobs}
        raise AssertionError(path)

class GateTests(unittest.TestCase):
    def setUp(self):
        self.policy, self.state = fixture()
        self.api = Fake()
        self.patcher = patch.object(session, "load", return_value=self.state)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def evaluate(self):
        return gate.evaluate(self.api, REPO, self.policy)

    def test_two_issue_gate_and_opt_in_publish(self):
        verdict = self.evaluate()
        self.assertEqual(verdict["status"], "pass")
        self.assertEqual([r["issue"] for r in verdict["issues"]], [247, 248])
        self.assertFalse(verdict["published"])
        self.assertEqual(self.api.writes, [])
        self.assertTrue(gate.publish(self.api, self.api, REPO, self.policy)["published"])
        self.assertEqual(self.api.writes[0]["head_sha"], MERGE)

    def test_incomplete_scope(self):
        self.policy["issues"].pop()
        with self.assertRaisesRegex(ValueError, "all staged"):
            self.evaluate()

    def test_missing_or_spoofed_app(self):
        self.api.checks[0]["app"]["id"] = 999
        with self.assertRaisesRegex(ValueError, "independently published"):
            self.evaluate()
        self.api.checks[0]["app"] = {"id": 87, "slug": "github-actions"}
        with self.assertRaisesRegex(ValueError, "not trusted"):
            self.evaluate()

    def test_stale_candidate_and_base(self):
        self.api.pr["head"]["sha"] = SOURCE
        with self.assertRaisesRegex(ValueError, "stale"):
            self.evaluate()
        self.api.pr["head"]["sha"] = HEAD
        self.api.refs["trunk"] = SOURCE
        with self.assertRaisesRegex(ValueError, "base changed"):
            self.evaluate()

    def test_skipped_job_and_step(self):
        self.api.jobs[0]["steps"][0]["conclusion"] = "skipped"
        with self.assertRaisesRegex(ValueError, "step"):
            self.evaluate()
        self.api.jobs[0]["steps"][0]["conclusion"] = "success"
        self.api.jobs[0]["conclusion"] = "skipped"
        with self.assertRaisesRegex(ValueError, "job"):
            self.evaluate()

    def test_stale_attempt(self):
        self.api.run["run_attempt"] = 2
        with self.assertRaisesRegex(ValueError, "attempt"):
            self.evaluate()

    def test_failed_gate_never_publishes(self):
        self.api.checks[0]["conclusion"] = "failure"
        with self.assertRaises(ValueError):
            gate.publish(self.api, self.api, REPO, self.policy)
        self.assertEqual(self.api.writes, [])

    def test_wrong_fix_ancestry_and_missing_criterion(self):
        self.api.ancestor = False
        with self.assertRaisesRegex(ValueError, "ancestor"):
            self.evaluate()
        self.api.ancestor = True
        self.policy["issues"][0]["criteria"][0]["text"] = "Different"
        with self.assertRaisesRegex(ValueError, "criterion"):
            self.evaluate()

    def test_stale_staged_handoff_and_state(self):
        self.state["handoff"]["history"][0]["handoff"]["candidate_sha"] = SOURCE
        with self.assertRaisesRegex(ValueError, "staged PR"):
            self.evaluate()
        self.state["handoff"]["history"][0]["handoff"]["candidate_sha"] = HEAD
        self.api.refs[install.BRANCH] = SOURCE
        with self.assertRaisesRegex(ValueError, "state advanced"):
            self.evaluate()

    def test_wrong_merge_parents_and_unlinked_evidence(self):
        self.api.parents = [HEAD, BASE]
        with self.assertRaisesRegex(ValueError, "parents"):
            self.evaluate()
        self.api.parents = [BASE, HEAD]
        self.api.checks[0]["details_url"] = RUN.replace("/123/", "/124/")
        with self.assertRaisesRegex(ValueError, "staged issue evidence"):
            self.evaluate()

    def test_empty_scope_and_self_check(self):
        self.policy["issues"][0]["criteria"][0]["checks"][0]["name"] = gate.CHECK
        with self.assertRaisesRegex(ValueError, "itself"):
            self.evaluate()
        self.policy["issues"] = []
        with self.assertRaisesRegex(ValueError, "scope"):
            self.evaluate()


    def test_wrong_publisher_never_creates_green_check(self):
        self.api.publisher_app = 999
        with self.assertRaisesRegex(ValueError, "wrong identity"):
            gate.publish(self.api, self.api, REPO, self.policy)
        self.assertEqual(len(self.api.writes), 1)
        self.assertEqual(self.api.writes[0]["status"], "in_progress")
        self.assertIsNone(self.api.gate_checks[0]["conclusion"])

    def test_existing_gate_cannot_be_shadowed(self):
        gate.publish(self.api, self.api, REPO, self.policy)
        with self.assertRaisesRegex(ValueError, "Existing trusted gate"):
            gate.publish(self.api, self.api, REPO, self.policy)
        self.assertEqual(len(self.api.gate_checks), 1)

    def test_revoke_previous_green_even_after_state_changed(self):
        verdict = gate.publish(self.api, self.api, REPO, self.policy)
        self.api.refs[install.BRANCH] = SOURCE
        result = gate.revoke(self.api, self.api, REPO, self.policy, verdict["check_id"])
        self.assertEqual(result["status"], "revoked")
        self.assertEqual(self.api.gate_checks[0]["conclusion"], "failure")

    def test_revoke_rejects_wrong_policy(self):
        verdict = gate.publish(self.api, self.api, REPO, self.policy)
        changed = copy.deepcopy(self.policy)
        changed["installed_sha"] = SOURCE
        with self.assertRaisesRegex(ValueError, "wrong identity"):
            gate.revoke(self.api, self.api, REPO, changed, verdict["check_id"])
        self.assertEqual(self.api.gate_checks[0]["conclusion"], "success")

    def test_changed_state_after_pending_never_turns_green(self):
        original = self.api.request
        def race(method, path, body=None):
            result = original(method, path, body)
            if method == "POST" and path == PREFIX + "/check-runs":
                self.api.refs[install.BRANCH] = SOURCE
            return result
        self.api.request = race
        with self.assertRaisesRegex(ValueError, "state advanced"):
            gate.publish(self.api, self.api, REPO, self.policy)
        self.assertIsNone(self.api.gate_checks[0]["conclusion"])
        self.assertEqual(len(self.api.writes), 1)

    def test_duplicate_gate_after_pending_refuses_success(self):
        original = self.api.request
        def race(method, path, body=None):
            result = original(method, path, body)
            if method == "POST" and path == PREFIX + "/check-runs":
                self.api.gate_checks.append({**self.api.gate_checks[0], "id": 101})
            return result
        self.api.request = race
        with self.assertRaisesRegex(ValueError, "Ambiguous"):
            gate.publish(self.api, self.api, REPO, self.policy)
        self.assertTrue(all(c["conclusion"] is None for c in self.api.gate_checks))
