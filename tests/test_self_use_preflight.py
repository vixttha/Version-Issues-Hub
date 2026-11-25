import copy
import unittest

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
