"""Integration staleness and non-destructive refresh through production session."""
import copy
import unittest
from tools import session
from test_session import Fake, state, FIX, CANDIDATE, BASE, NEXT, RUN, PROPOSED

NEW_BASE = "4"*40
NEW_MERGE = "5"*40
NEW_RUN = RUN.replace("/123/", "/125/")

class StaleIntegrationTests(unittest.TestCase):
    def setup_case(self, staged=False):
        api,s=Fake(),state()
        s["ledger"],s["handoff"]=session.claim(api,s,247,["test"],"Fix")
        for kw in ({"fix":FIX,"candidate":CANDIDATE,"pr":8},{"evidence":[RUN]},{}):
            s["ledger"],s["handoff"]=session.advance(api,s,"next",**kw)
        if staged:
            s["ledger"],s["handoff"]=session.finish(api,s,"staged","stage")
        return api,s

    def move_base(self,api):
        api.product=NEW_BASE
        api.pr["base"]["sha"]=NEW_BASE
        api.pr["merge_commit_sha"]=NEW_MERGE

    def test_other_merge_invalidates_active_and_staged_without_mutation(self):
        for staged in (False,True):
            api,s=self.setup_case(staged)
            before=copy.deepcopy(s)
            self.move_base(api)
            self.assertEqual(session.inspect(api,s,247)["status"],"stale_integration_evidence")
            if not staged:
                with self.assertRaisesRegex(ValueError,"Stale"):
                    session.finish(api,s,"staged","old")
            self.assertEqual(s,before)
            self.assertEqual(api.writes,[])

    def test_refresh_keeps_fix_version_and_history_and_rejects_old_run(self):
        api,s=self.setup_case()
        old=copy.deepcopy(s["handoff"]["active"])
        self.move_base(api)
        s["ledger"],s["handoff"]=session.advance(api,s,"refresh",refresh=True)
        active=s["handoff"]["active"]
        self.assertEqual(active["fix_sha"],FIX)
        self.assertEqual(active["version"],old["version"])
        self.assertEqual(active["candidate_sha"],CANDIDATE)
        self.assertEqual(active["phase"],"Validate")
        self.assertEqual(active["evidence"],[])
        self.assertEqual(s["handoff"]["history"][-1]["handoff"],old)
        before=copy.deepcopy(s)
        with self.assertRaisesRegex(ValueError,"association"):
            session.advance(api,s,"old run",evidence=[RUN])
        self.assertEqual(s,before)
        # Different exact run, now bound to the new base/head.
        original=api.request
        def request(method,path,body=None):
            if "/actions/runs/125" in path:
                return {**api.pre_run,"id":125,"pull_requests":[
                    {"number":8,"head":{"sha":CANDIDATE},"base":{"sha":NEW_BASE}}]}
            return original(method,path,body)
        api.request=request
        s["ledger"],s["handoff"]=session.advance(api,s,"fresh",evidence=[NEW_RUN])
        s["ledger"],s["handoff"]=session.advance(api,s,"audit")
        ledger,handoff=session.finish(api,s,"staged","accept fresh")
        self.assertEqual(ledger["issues"][0]["state"],"staged")
        self.assertEqual(handoff["history"][-1]["handoff"]["evidence"],[NEW_RUN])
        self.assertEqual(handoff["history"][-1]["handoff"]["integration_base_sha"],NEW_BASE)

    def test_staged_reclaim_preserves_original_fix_and_slot(self):
        api,s=self.setup_case(True)
        old=copy.deepcopy(s["handoff"]["history"])
        self.move_base(api)
        ledger,handoff=session.claim(api,s,247,["test"],"refresh staged")
        self.assertEqual(handoff["active"]["fix_sha"],FIX)
        self.assertEqual(handoff["active"]["version"],"v1.0.6.1")
        self.assertEqual(handoff["active"]["evidence"],[])
        self.assertEqual(handoff["history"],old)
        self.assertEqual(ledger["issues"][0]["state"],"in_progress")

    def test_changed_head_missing_fix_refuses_refresh(self):
        api,s=self.setup_case()
        api.pr["head"]["sha"]="6"*40
        before=copy.deepcopy(s)
        with self.assertRaisesRegex(ValueError,"ancestor"):
            session.advance(api,s,"refresh",refresh=True)
        self.assertEqual(s,before)
        self.assertEqual(api.writes,[])

    def test_legacy_active_without_pins_remains_readable_but_cannot_stage(self):
        api,s=self.setup_case()
        for key in session.PIN_KEYS:
            s["handoff"]["active"].pop(key)
        session.validate_handoff(s["handoff"],s["ledger"])
        self.assertEqual(session.inspect(api,s)["status"],"stale_integration_evidence")
        with self.assertRaisesRegex(ValueError,"unpinned"):
            session.finish(api,s,"staged","old")
        ledger,handoff=session.advance(api,s,"refresh",refresh=True)
        self.assertEqual(handoff["active"]["fix_sha"],FIX)

    def test_base_changes_during_run_read_cannot_advance(self):
        api,s=self.setup_case()
        original=api.request
        def request(method,path,body=None):
            result=original(method,path,body)
            if "/actions/runs/123/attempts/1" in path:
                self.move_base(api)
            return result
        api.request=request
        before=copy.deepcopy(s)
        with self.assertRaisesRegex(ValueError,"Stale"):
            session.finish(api,s,"staged","race")
        self.assertEqual(s,before)
        self.assertEqual(api.writes,[])

    def test_unrelated_installed_state_is_not_product_base(self):
        api,s=self.setup_case()
        s["ref"]="7"*40
        self.assertEqual(session.inspect(api,s)["status"],"resume")
