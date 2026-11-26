"""Targeted source mutations in memory. Only assertion failures kill a mutant."""
import inspect
import io
import sys
import unittest
from unittest.mock import patch
import test_core as c
import test_schema as s
from record import run_suite
MUTANTS = [
    ("blob_normalization",c.lifecycle,"blob_id",'raw = value.encode("utf-8")','raw = value.replace("\\r\\n","\\n").encode("utf-8")',c.Bytes,"test_bytes_crlf"),
    ("digest_normalization",c.lifecycle,"digest_files",'s.encode("utf-8")','s.replace("\\r\\n","\\n").encode("utf-8")',c.Bytes,"test_bytes_crlf"),
    ("source_hash",c.install,"read_text",'if blob != item.get("sha"):','if False:',c.SourceResponse,"test_reject_sha"),
    ("tree_duplicate",c.lifecycle,"tree_entries",'if path in entries:','if False:',c.TreeResponse,"test_duplicate"),
    ("tree_commit",c.lifecycle,"tree_entries",'if commit.get("sha") != sha:','if False:',c.TreeResponse,"test_wrong_commit"),
    ("json_duplicate",s.checkpoint,"unique_keys",'if key in result:','if False:',s.Ledger,"test_duplicate_json"),
    ("ledger_duplicate_issue",s.checkpoint,"bindings",'if issue in result:','if False:',s.Ledger,"test_duplicate_issue"),
    ("ledger_duplicate_version",s.checkpoint,"bindings",'if version in used_versions:','if False:',s.Ledger,"test_duplicate_version"),
    ("ledger_history",s.checkpoint,"check_history",'if current.get(issue) != version:','if False:',s.Ledger,"test_history_changed"),
    ("scope_duplicate",s.checkpoint,"check_receipt_scope",'if len(set(selected)) != len(selected):','if False:',s.Scope,"test_duplicate_selected"),
    ("scope_history",s.checkpoint,"check_receipt_scope",'if fixes.get(version) != fix:','if False:',s.Scope,"test_historical_fix"),
    ("links_duplicate",s.session,"evidence_links",'if len(set(links)) != len(links):','if False:',s.Links,"test_duplicates"),
    ("handoff_orphan",s.session,"validate_handoff",'elif in_progress:','elif False:',s.Handoff,"test_orphan"),
    ("worker_stale",s.session,"validate_active",'if active["phase"] == "Worker" and (any(v is not None for v in fields) or active["evidence"]):','if False:',s.Handoff,"test_worker_stale"),
]
class Mutation(unittest.TestCase): pass
def mutation_case(module,name,old,new,cls,test):
    def check(self):
        def execute():
            return unittest.TextTestRunner(stream=io.StringIO(),verbosity=0).run(cls(test))
        baseline=execute()
        self.assertEqual(baseline.testsRun,1)
        self.assertTrue(baseline.wasSuccessful(),str(baseline.errors+baseline.failures))
        self.assertFalse(baseline.skipped or baseline.expectedFailures or baseline.unexpectedSuccesses)
        source=inspect.getsource(getattr(module,name))
        self.assertEqual(source.count(old),1,"mutation anchor changed")
        ns=dict(vars(module))
        exec(compile(source.replace(old,new,1),"<isolated mutant>","exec"),ns)
        with patch.object(module,name,ns[name]):
            result=execute()
        self.assertEqual(result.testsRun,1)
        self.assertEqual(result.errors,[],"infrastructure error is not a killed mutant")
        self.assertEqual(len(result.failures),1,"mutant survived")
        self.assertFalse(result.skipped or result.expectedFailures or result.unexpectedSuccesses)
        self.assertTrue(execute().wasSuccessful(),"original guard was not restored")
    return check
for ident,module,name,old,new,cls,test in MUTANTS:
    setattr(Mutation,"test_kill_"+ident,mutation_case(module,name,old,new,cls,test))
if __name__=="__main__":
    run_suite(unittest.defaultTestLoader.loadTestsFromTestCase(Mutation),14,"mutation")
