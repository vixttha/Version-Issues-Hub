"""Independent diagnostic, exact candidate, real disposable Git + simulated API.
A reproduction PASS means the observed defect reproduced, NOT candidate acceptance.
"""
import json, os, sys, tempfile, unittest
from pathlib import Path
root=Path(os.environ["GITHUB_WORKSPACE"])
candidate=root/"candidate"
sys.path[:0]=[str(candidate),str(candidate/"tests")]
from test_contention_recovery import RecoveryTests, A, B, C, REPO
from tools import session, install, checkpoint
class Independent(RecoveryTests):
    def test_rd002_tampered_initial_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=[]
            result=self.recover(lambda s:self.claim(s,B),B,
                on_pending_intent=lambda x:paths.append(session.persist_pending_intent(directory,x)),
                on_recovery_ticket=lambda x:session.persist_recovery_ticket(directory,x))
            fresh=session.load(self.api,REPO)
            original=json.loads(paths[0].read_bytes())
            writes=list(self.api.writes)
            valid=session.inspect_pending(self.api,fresh,paths[0])
            self.assertEqual(valid["candidates"][0]["status"],"published")
            # Actual descendant of the original parent, cannot be the initial ancestor
            # of its own publication parent. No fake SHA and no altered candidate.
            wrong=result["installed_sha"]
            self.assertNotEqual(wrong,original["initial_sha"])
            paths[0].write_text(json.dumps({**original,"initial_sha":wrong}),encoding="utf-8")
            observed=session.inspect_pending(self.api,fresh,paths[0])
            self.assertEqual(observed["initial_sha"],wrong)
            self.assertEqual(observed["candidates"][0]["status"],"published")
            self.assertFalse(observed["automatic_replay"])
            self.assertEqual(self.api.writes,writes)
            print("RD-002 REPRODUCED: altered initial revision echoed with valid published candidate; no replay or remote write",flush=True)
    def test_input_guards(self):
        for raw in ('{"a":1,"a":2}','{"a":NaN}','{"a":1e999}'):
            with self.subTest(raw=raw), self.assertRaises(ValueError):checkpoint.parse_json(raw)
        for repo in ("owner/..","owner/.","owner/name/extra"):
            with self.subTest(repo=repo),self.assertRaises(ValueError):install.repo_path(repo)

if __name__=="__main__":
    names=["test_rd002_tampered_initial_revision","test_input_guards","test_idempotent_claim_does_not_create_pending_journal_or_ticket","test_automatic_real_git_conflict_preserves_both_claims","test_same_issue_change_stops_without_replaying","test_pending_inventory_recovers_published_candidate_without_mutation","test_pending_inventory_stops_on_api_throttle","test_malformed_rejected_write_recovery_retains_candidate","test_journal_failure_prevents_publication","test_recovery_ticket_rejects_unrelated_tree_mutation","test_retry_source_cache_never_caches_installed_bytes","test_bounded_exhaustion_no_infinite_retry"]
    suite=unittest.TestSuite(Independent(n) for n in names)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    out=Path(os.environ["RUNNER_TEMP"])/"independent-vib-audit"
    out.mkdir(exist_ok=True)
    (out/"recovery.json").write_text(json.dumps({"source":"e8359a4acaf2e956332585aa69a109e3242dad50","tests":result.testsRun,"failures":len(result.failures),"errors":len(result.errors),"rd002_reproduction":result.wasSuccessful(),"scope":"disposable real Git, simulated API; reproduction is not acceptance"},indent=2),encoding="utf-8")
    sys.exit(not result.wasSuccessful())
