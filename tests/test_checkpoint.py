import copy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from tools import checkpoint


def ledger_with(*records):
    return {
        "schema_version": 1,
        "repository": "vixttha/Version-Issues-Hub",
        "issues": list(records),
    }


def row(issue, version, state="assigned"):
    return {"issue": issue, "version": version, "state": state, "acceptance": ["Check the fix."]}


class LedgerTests(unittest.TestCase):
    def test_first_live_issue_is_stable_on_registration_retry(self):
        ledger = checkpoint.parse_json(Path(checkpoint.LEDGER).read_text(encoding="utf-8"))
        original = copy.deepcopy(ledger)
        self.assertEqual(checkpoint.bindings(ledger)[1], "v0.0.0.1")
        self.assertEqual(checkpoint.register(ledger, 1, "v0.0.0", []), ("v0.0.0.1", False))
        self.assertEqual(ledger, original)
        with self.assertRaisesRegex(ValueError, "already belongs"):
            checkpoint.register(ledger, 1, "v0.0.1", ["A changed line."])

    def test_allocation_is_numeric_and_keeps_retired_versions_reserved(self):
        ledger = ledger_with(row(10, "v0.0.2.10"), row(9, "v0.0.2.9"),
                             row(150, "v0.0.2.150", "retired"), row(151, "v0.0.3.1"))
        self.assertEqual(checkpoint.register(ledger, 500, "v0.0.2", ["Check the fix."]),
                         ("v0.0.2.151", True))
        self.assertEqual([r["issue"] for r in ledger["issues"]], [9, 10, 150, 500, 151])

    def test_rejects_duplicate_assignments_and_invalid_records(self):
        examples = (
            (ledger_with(row(1, "v0.0.0.1"), row(2, "v0.0.0.1")), "Duplicate version"),
            (ledger_with(row(1, "v0.0.0.1"), row(1, "v0.0.0.2")), "Duplicate issue"),
            (ledger_with(row(1, "v0.0.0.01")), "Invalid issue version"),
            (ledger_with(row(True, "v0.0.0.1")), "Invalid GitHub issue"),
        )
        for ledger, message in examples:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                checkpoint.bindings(ledger)
        with self.assertRaisesRegex(ValueError, "Duplicate JSON key"):
            checkpoint.parse_json('{"issue": 1, "issue": 2}')

    def test_allows_state_changes_but_rejects_deletion_and_renumbering(self):
        before = ledger_with(row(1, "v0.0.0.1"))
        checkpoint.check_history(ledger_with(row(1, "v0.0.0.1", "retired")), before)
        for after in (ledger_with(), ledger_with(row(1, "v0.0.0.2"))):
            with self.assertRaisesRegex(ValueError, "Historical assignment changed"):
                checkpoint.check_history(after, before)


class StrictJSONTests(unittest.TestCase):
    def test_nonfinite_parse_rejects_tokens_and_float_overflow(self):
        for token in ("NaN", "Infinity", "-Infinity", "1e999", "-1e999"):
            for raw in (token, '{"nested":[' + token + ']}'):
                with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, "Nonfinite"):
                    checkpoint.parse_json(raw)

    def test_nonfinite_persistence_preserves_existing_bytes(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            original = b'{ "value": 17 }\r\n'
            path.write_bytes(original)
            for number in (float("nan"), float("inf"), -float("inf")):
                with self.subTest(number=number), self.assertRaises(ValueError):
                    checkpoint.write_json(path, {"nested": [number]})
                self.assertEqual(path.read_bytes(), original)
                self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_finite_json_round_trip(self):
        data = {"values": [0, -9, 1.25, 1e-100, 1e100, True, None], "literal": "NaN"}
        with TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            checkpoint.write_json(path, data)
            self.assertEqual(checkpoint.parse_json(path.read_bytes()), data)


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.ledger = ledger_with(row(1, "v0.0.0.1"))
        self.event = {"repository": {"full_name": self.ledger["repository"]}}
        self.tested = "a" * 40
        self.fix = "d" * 40
        self.env = {
            "GITHUB_REPOSITORY": self.ledger["repository"],
            "GITHUB_SHA": self.tested,
            "GITHUB_RUN_ID": "100",
            "GITHUB_RUN_ATTEMPT": "2",
            "GITHUB_WORKFLOW": "Verify issue checkpoint",
            "GITHUB_JOB": "verify",
        }

    def test_push_receipt_links_issue_checkout_and_attempt(self):
        self.env["GITHUB_EVENT_NAME"] = "push"
        self.event["after"] = self.tested
        result = checkpoint.receipt(self.ledger, "v0.0.0.1", self.tested, self.env, self.event,
                                    fix_sha=self.fix)
        self.assertEqual(result["issue"], 1)
        self.assertEqual(result["baseline_version"], "v0.0.0")
        self.assertEqual(result["target_version"], "v0.0.1")
        self.assertEqual(result["issue_url"],
                         "https://github.com/vixttha/Version-Issues-Hub/issues/1")
        self.assertEqual(result["fix_sha"], self.fix)
        self.assertEqual(result["candidate_sha"], self.tested)
        self.assertEqual(result["tested_sha"], self.tested)
        self.assertEqual(result["attempt"], 2)
        self.assertTrue(result["run_url"].endswith("/runs/100/attempts/2"))

    def test_receipt_targets_the_next_project_version_on_each_baseline(self):
        self.env["GITHUB_EVENT_NAME"] = "push"
        self.event["after"] = self.tested
        for version, baseline, target in (
            ("v0.0.1.1", "v0.0.1", "v0.0.2"),
            ("v0.0.1.150", "v0.0.1", "v0.0.2"),
            ("v0.0.9.3", "v0.0.9", "v0.0.10"),
        ):
            with self.subTest(version=version):
                result = checkpoint.receipt(
                    ledger_with(row(1, version)), version, self.tested, self.env, self.event,
                    fix_sha=self.fix,
                )
                self.assertEqual(result["baseline_version"], baseline)
                self.assertEqual(result["target_version"], target)

    def test_pr_receipt_distinguishes_candidate_base_and_tested_commit(self):
        self.env["GITHUB_EVENT_NAME"] = "pull_request"
        self.event["pull_request"] = {"number": 2, "head": {"sha": "b" * 40},
                                      "base": {"sha": "c" * 40}}
        with self.assertRaisesRegex(ValueError, "expected base and head parents"):
            checkpoint.receipt(self.ledger, "v0.0.0.1", self.tested, self.env, self.event,
                               fix_sha=self.fix)
        result = checkpoint.receipt(
            self.ledger, "v0.0.0.1", self.tested, self.env, self.event, ["c" * 40, "b" * 40],
            fix_sha=self.fix,
        )
        self.assertEqual(result["pull_request"], 2)
        self.assertEqual(result["fix_sha"], self.fix)
        self.assertEqual(result["candidate_sha"], "b" * 40)
        self.assertEqual(result["base_sha"], "c" * 40)
        self.assertEqual(result["tested_sha"], self.tested)

    def test_refuses_a_wrong_checkout_and_wrong_repository(self):
        with self.assertRaisesRegex(ValueError, "does not match GITHUB_SHA"):
            checkpoint.receipt(self.ledger, "v0.0.0.1", "f" * 40, self.env, self.event,
                               fix_sha=self.fix)
        self.event["repository"]["full_name"] = "example/another"
        with self.assertRaisesRegex(ValueError, "repository does not match"):
            checkpoint.receipt(self.ledger, "v0.0.0.1", self.tested, self.env, self.event,
                               fix_sha=self.fix)

    @patch.object(checkpoint, "verify_fix_ancestry")
    def test_batch_keeps_both_issue_fix_pairs_when_the_candidate_changes(self, check_ancestry):
        self.ledger["issues"].append(row(7, "v0.0.0.2"))
        fixes = {"v0.0.0.1": self.fix, "v0.0.0.2": "e" * 40}
        scope = {"fixes": fixes, "versions": list(fixes)}
        self.env["GITHUB_EVENT_NAME"] = "pull_request"
        for candidate, checkout in (("b" * 40, self.tested), ("1" * 40, "2" * 40)):
            base = "c" * 40
            self.event["pull_request"] = {
                "number": 2, "head": {"sha": candidate}, "base": {"sha": base},
            }
            self.env["GITHUB_SHA"] = checkout
            records = checkpoint.receipts(self.ledger, scope, checkout, self.env, self.event,
                                          [base, candidate], previous=scope)
            self.assertEqual([(r["issue"], r["version"], r["fix_sha"]) for r in records],
                             [(1, "v0.0.0.1", self.fix), (7, "v0.0.0.2", "e" * 40)])
            self.assertEqual({r["candidate_sha"] for r in records}, {candidate})
            self.assertEqual({r["tested_sha"] for r in records}, {checkout})
            for version, fix in fixes.items():
                check_ancestry.assert_any_call(version, fix, candidate)
        self.assertEqual(check_ancestry.call_count, 4)

    def test_scope_rejects_missing_duplicate_and_reassigned_fixes(self):
        version = "v0.0.0.1"
        previous = {"fixes": {version: self.fix}, "versions": [version]}
        for scope, message in (
            ({"fixes": {}, "versions": [version]}, "No fix revision"),
            ({"fixes": {version: self.fix}, "versions": [version, version]}, "duplicate versions"),
            ({"fixes": {version: "e" * 40}, "versions": [version]}, "Historical fix revision changed"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                checkpoint.check_receipt_scope(self.ledger, scope, previous)


    @patch.object(checkpoint, "verify_fix_ancestry")
    def test_live_scope_has_one_receipt_per_selected_version(self, check_ancestry):
        ledger = checkpoint.parse_json(Path(checkpoint.LEDGER).read_text(encoding="utf-8"))
        scope = checkpoint.parse_json(Path(checkpoint.RECEIPT_SCOPE).read_text(encoding="utf-8"))
        self.env["GITHUB_EVENT_NAME"] = "push"
        self.event["after"] = self.tested
        results = checkpoint.receipts(ledger, scope, self.tested, self.env, self.event)
        self.assertEqual(len(results), len(scope["versions"]))
        self.assertEqual({r["version"] for r in results}, set(scope["versions"]))
        self.assertEqual({r["version"]: r["fix_sha"] for r in results},
                         {v: scope["fixes"][v] for v in scope["versions"]})
        self.assertEqual(check_ancestry.call_count, len(scope["versions"]))


if __name__ == "__main__":
    unittest.main()
