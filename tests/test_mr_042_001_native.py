"""Isolated MR-042-001 qualification. Never writes a canonical or product ref."""
import subprocess
import unittest
from tools import checkpoint, session

OLD = "3d011c9cd4ca8879351898801d376905c21b40b6"
PREPARED = "b1aac7dc2daba811a22abe3f431d29bc7922d27f"
SOURCE_REF = "refs/heads/audit/mr-042-001-prepared"

def git(*args):
    return subprocess.check_output(["git", *args], text=True, encoding="utf-8").strip()

def read(rev, path):
    return checkpoint.parse_json(git("show", rev + ":" + path))

class HistoricalClosureCorrectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run(["git", "fetch", "--no-tags", "origin", SOURCE_REF], check=True)
        if git("rev-parse", "FETCH_HEAD") != PREPARED:
            raise AssertionError("Prepared qualification ref changed")
        cls.old = read(OLD, session.HANDOFF)
        cls.new = read(PREPARED, session.HANDOFF)
        cls.ledger = read(PREPARED, session.LEDGER)

    def test_original_fails_unmodified_native_validator(self):
        with self.assertRaisesRegex(ValueError, "Invalid closure execution identity"):
            session.validate_handoff(self.old, self.ledger)

    def test_corrected_state_passes_unmodified_native_validator(self):
        session.validate_handoff(self.new, self.ledger)
        self.assertIsNone(session.pending_closure(self.new))
        self.assertEqual(self.new["active"]["issue"], 94)
        self.assertEqual(self.new["active"]["phase"], "Worker")
        result = session.closure_status(
            {"ledger": self.ledger, "handoff": self.new},
            {"number": 92, "state": "closed", "state_reason": "completed"})
        self.assertEqual(result["closure_synchronization"], "state_matches_historical_receipt")
        self.assertTrue(result["historical_confirmation_recorded"])
        self.assertFalse(result["production_integrated"])

    def test_exact_parent_and_only_two_identifier_corrections(self):
        self.assertEqual(git("show", "-s", "--format=%P", PREPARED), OLD)
        self.assertEqual(git("diff", "--name-only", OLD, PREPARED), session.HANDOFF)
        before = git("show", OLD + ":" + session.HANDOFF)
        after = git("show", PREPARED + ":" + session.HANDOFF)
        self.assertEqual(before.count("69955682064249faa2f5b2f48cf3c342d"), 2)
        self.assertEqual(after, before.replace(
            "69955682064249faa2f5b2f48cf3c342d", "69955682064249faa2f5b2f48cf3c342"))
        self.assertEqual(read(OLD, session.LEDGER), self.ledger)
