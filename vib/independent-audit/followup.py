"""Follow-up: exact candidate diagnostics, not acceptance tests."""
import json, os, sys, tempfile, unittest
from pathlib import Path
from unittest.mock import Mock, patch
root=Path(os.environ["GITHUB_WORKSPACE"]); candidate=root/"candidate"
sys.path[:0]=[str(candidate),str(candidate/"tests")]
from tools import install, session
from test_contention_recovery import RecoveryTests,B,REPO
out=Path(os.environ["RUNNER_TEMP"])/"independent-vib-audit";out.mkdir(exist_ok=True)
class Pending(RecoveryTests):
    def test_rd002_current(self):
        with tempfile.TemporaryDirectory() as directory:
            paths=[]
            result=self.recover(lambda s:self.claim(s,B),B,
                on_pending_intent=lambda x:paths.append(session.persist_pending_intent(directory,x)),
                on_recovery_ticket=lambda x:session.persist_recovery_ticket(directory,x))
            fresh=session.load(self.api,REPO); original=json.loads(paths[0].read_bytes()); writes=list(self.api.writes)
            self.assertEqual(session.inspect_pending(self.api,fresh,paths[0])["candidates"][0]["status"],"published")
            for wrong in (result["installed_sha"],"0"*40):
                with self.subTest(wrong=wrong):
                    paths[0].write_text(json.dumps({**original,"initial_sha":wrong}),encoding="utf-8")
                    observed=session.inspect_pending(self.api,fresh,paths[0])
                    self.assertEqual(observed["initial_sha"],wrong)
                    self.assertEqual(observed["candidates"][0]["status"],"published")
                    self.assertFalse(observed["automatic_replay"])
            self.assertEqual(self.api.writes,writes)
            print("RD-002 reproduced for descendant and nonexistent initial SHA",flush=True)
class RefBoundary(unittest.TestCase):
    def test_malformed_ref_matrix(self):
        ref="refs/heads/main"; sha="a"*40
        cases=[("null",None,AttributeError),("array",[],AttributeError),
            ("string","bad",AttributeError),("missing_object",{"ref":ref},KeyError),
            ("null_object",{"ref":ref,"object":None},TypeError),
            ("list_object",{"ref":ref,"object":[]},TypeError),
            ("missing_type",{"ref":ref,"object":{"sha":sha}},KeyError),
            ("missing_sha",{"ref":ref,"object":{"type":"commit"}},KeyError),
            ("wrong_ref",{"ref":"refs/heads/other","object":{"type":"commit","sha":sha}},ValueError),
            ("wrong_type",{"ref":ref,"object":{"type":"tag","sha":sha}},ValueError),
            ("bad_sha",{"ref":ref,"object":{"type":"commit","sha":"bad"}},ValueError)]
        rows=[]
        for name,payload,expected in cases:
            with self.subTest(case=name):
                api=Mock();api.request.return_value=payload
                with self.assertRaises(expected) as err:
                    install.read_ref(api,"/repos/example/test","main")
                api.request.assert_called_once_with("GET","/repos/example/test/git/ref/heads/main")
                rows.append({"case":name,"exception":type(err.exception).__name__})
        for name,payload,expected in cases[:3]:
            api=Mock();api.request.return_value=payload
            with self.assertRaises(expected):
                install.wait_ref(api,"/repos/example/test","main",sha)
            self.assertEqual(api.request.call_count,1)
        (out/"ref-boundary.json").write_bytes((json.dumps({"source":"b68796db12681fe4d43b562c8647deca38fa819c","cases":rows,"wait_ref_attribute_error_cases":3},indent=2)+"\n").encode())
        print("RD-003: 3 raw AttributeErrors, 3 KeyErrors, 2 TypeErrors, 3 controlled ValueErrors; all read-only",flush=True)
    def test_ref_controls(self):
        api=Mock();api.request.return_value={"ref":"refs/heads/main","object":{"type":"commit","sha":"a"*40}}
        self.assertEqual(install.read_ref(api,"/repos/example/test","main"),"a"*40)
        api.request.side_effect=install.ApiError(404);self.assertIsNone(install.read_ref(api,"/repos/example/test","main"))
        api.request.side_effect=install.ApiError(429)
        with self.assertRaises(install.ApiError):install.read_ref(api,"/repos/example/test","main")
    def test_session_cli_raw_attribute_error(self):
        # Mock only the external API transport; real CLI, load and read_ref paths.
        api=Mock();api.request.return_value=None
        with patch.object(install,"GitHub",return_value=api),patch.object(sys,"argv",["session","--target","example/test","inspect"]):
            with self.assertRaises(AttributeError):session.main()
        self.assertTrue(all(call.args[0]=="GET" for call in api.request.call_args_list))
if __name__=="__main__":
    suite=unittest.TestSuite([Pending("test_rd002_current"),*unittest.defaultTestLoader.loadTestsFromTestCase(RefBoundary)])
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    (out/"followup.json").write_bytes((json.dumps({"source":"b68796db12681fe4d43b562c8647deca38fa819c","tests":result.testsRun,"errors":len(result.errors),"failures":len(result.failures),"diagnostic_pass":result.wasSuccessful()},indent=2)+"\n").encode())
    sys.exit(not result.wasSuccessful())
