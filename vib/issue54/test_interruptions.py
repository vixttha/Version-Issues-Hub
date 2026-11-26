"""Gate publication, revocation and handoff writes under interrupted responses.

All GitHub operations use synthetic API fixtures. No real check/ref is written.
"""
import copy
import unittest
from unittest.mock import patch
import test_completion as fixtures
from tools import gate, install, session
from record import run_suite

g=fixtures.g
s=fixtures.s

class Publication(unittest.TestCase):
    def setUp(self):
        self.policy,self.state=g.fixture()
        self.api=g.Fake()
        self.original=self.api.request
        self.calls=[]
        p=patch.object(session,"load",return_value=self.state)
        p.start(); self.addCleanup(p.stop)
    def intercept(self,fn):
        def request(m,p,b=None):
            self.calls.append((m,p))
            return fn(m,p,b)
        self.api.request=request
    def publish(self):
        return gate.publish(self.api,self.api,g.REPO,self.policy)
    def revoke(self):
        return gate.revoke(self.api,self.api,g.REPO,self.policy,100)
    def interrupt(self,method,after=False):
        def request(m,p,b):
            if m==method and "/check-runs" in p:
                if after: self.original(m,p,b)
                raise TimeoutError("synthetic ambiguous response")
            return self.original(m,p,b)
        self.intercept(request)
        with self.assertRaises(TimeoutError): self.publish()
        self.assertEqual(sum(m==method for m,p in self.calls),1)
        self.assertEqual(len(self.api.writes), (0 if method=="POST" else 1)+int(after))
        if self.api.gate_checks:
            self.assertEqual(self.api.gate_checks[0]["conclusion"],"success" if method=="PATCH" and after else None)
    def test_post_before(self): self.interrupt("POST")
    def test_post_after(self): self.interrupt("POST",True)
    def test_patch_before(self): self.interrupt("PATCH")
    def test_patch_after(self): self.interrupt("PATCH",True)
    def test_pending_read_timeout(self):
        def request(m,p,b):
            if m=="GET" and p.endswith("/check-runs/100"): raise TimeoutError("pending read")
            return self.original(m,p,b)
        self.intercept(request)
        with self.assertRaises(TimeoutError): self.publish()
        self.assertEqual(len(self.api.writes),1)
        self.assertIsNone(self.api.gate_checks[0]["conclusion"])
    def pending_bad(self,change):
        def request(m,p,b):
            result=self.original(m,p,b)
            if m=="GET" and p.endswith("/check-runs/100"): change(result)
            return result
        self.intercept(request)
        with self.assertRaises(ValueError): self.publish()
        self.assertEqual(len(self.api.writes),1)
        self.assertIsNone(self.api.gate_checks[0]["conclusion"])
    def test_pending_wrong_id(self): self.pending_bad(lambda r:r.update(id=101))
    def test_pending_wrong_sha(self): self.pending_bad(lambda r:r.update(head_sha=g.SOURCE))
    def test_pending_wrong_external_id(self): self.pending_bad(lambda r:r.update(external_id="wrong"))
    def test_pending_wrong_name(self): self.pending_bad(lambda r:r.update(name="wrong"))
    def test_pending_wrong_app(self): self.pending_bad(lambda r:r["app"].update(id=999))
    def test_pending_wrong_status(self): self.pending_bad(lambda r:r.update(status="completed"))
    def test_pending_nonnull_conclusion(self): self.pending_bad(lambda r:r.update(conclusion="neutral"))
    def test_pending_base_advance(self):
        def request(m,p,b):
            result=self.original(m,p,b)
            if m=="POST": self.api.refs["trunk"]=g.SOURCE
            return result
        self.intercept(request)
        with self.assertRaises(ValueError): self.publish()
        self.assertEqual(len(self.api.writes),1)
        self.assertIsNone(self.api.gate_checks[0]["conclusion"])
    def test_pending_evidence_revoked(self):
        def request(m,p,b):
            result=self.original(m,p,b)
            if m=="POST": self.api.checks[0]["conclusion"]="failure"
            return result
        self.intercept(request)
        with self.assertRaises(ValueError): self.publish()
        self.assertEqual(len(self.api.writes),1)
        self.assertIsNone(self.api.gate_checks[0]["conclusion"])
    def test_patch_response_mismatch(self):
        def request(m,p,b):
            result=self.original(m,p,b)
            if m=="PATCH": result["conclusion"]="neutral"
            return result
        self.intercept(request)
        with self.assertRaises(ValueError): self.publish()
        self.assertEqual(len(self.api.writes),2)
    def test_success_readback_mismatch(self):
        def request(m,p,b):
            result=self.original(m,p,b)
            if m=="GET" and p.endswith("/check-runs/100") and len(self.api.writes)==2:
                result["conclusion"]="neutral"
            return result
        self.intercept(request)
        with self.assertRaises(ValueError): self.publish()
        self.assertEqual(len(self.api.writes),2)
    def revoke_interrupt(self,after):
        self.publish()
        def request(m,p,b):
            if m=="PATCH":
                if after: self.original(m,p,b)
                raise TimeoutError("revoke response")
            return self.original(m,p,b)
        self.intercept(request)
        with self.assertRaises(TimeoutError): self.revoke()
        self.assertEqual(sum(m=="PATCH" for m,p in self.calls),1)
        self.assertEqual(self.api.gate_checks[0]["conclusion"],"failure" if after else "success")
    def test_revoke_before(self): self.revoke_interrupt(False)
    def test_revoke_after(self): self.revoke_interrupt(True)
    def test_revoke_wrong_repository(self):
        self.publish()
        def request(m,p,b):
            result=self.original(m,p,b)
            if p==g.PREFIX: result["id"]=43
            return result
        self.intercept(request)
        with self.assertRaises(ValueError): self.revoke()
        self.assertEqual(len(self.api.writes),2)
        self.assertEqual(self.api.gate_checks[0]["conclusion"],"success")
    def test_revoke_duplicate_confirmation(self):
        self.publish()
        def request(m,p,b):
            result=self.original(m,p,b)
            if m=="PATCH": self.api.gate_checks.append(dict(self.api.gate_checks[0],id=101))
            return result
        self.intercept(request)
        with self.assertRaises(ValueError): self.revoke()
        self.assertEqual(len(self.api.writes),3)
    def test_revoke_wrong_readback(self):
        self.publish()
        def request(m,p,b):
            result=self.original(m,p,b)
            if m=="GET" and p.endswith("/check-runs/100") and len(self.api.writes)==3:
                result["conclusion"]="success"
            return result
        self.intercept(request)
        with self.assertRaises(ValueError): self.revoke()
        self.assertEqual(len(self.api.writes),3)

class HandoffWrites(unittest.TestCase):
    def setUp(self):
        self.api=s.Fake(); self.state=s.state()
        self.ledger,self.handoff=session.claim(self.api,self.state,247,["test"],"Fix")
        self.before=copy.deepcopy(self.state)
        self.original=self.api.request
        self.calls=[]
    def intercept(self,fn):
        def request(m,p,b=None):
            self.calls.append((m,p))
            return fn(m,p,b)
        self.api.request=request
    def save(self): return session.save(self.api,self.state,self.ledger,self.handoff,True)
    def fault(self,method,suffix,after):
        def request(m,p,b):
            if m==method and p.endswith(suffix):
                if after: self.original(m,p,b)
                raise TimeoutError("ambiguous write")
            return self.original(m,p,b)
        self.intercept(request)
        with self.assertRaises(TimeoutError): self.save()
        self.assertEqual(sum(m==method and p.endswith(suffix) for m,p in self.calls),1)
        self.assertEqual(self.api.ref,s.NEXT if method=="PATCH" and after else s.HEAD)
        self.assertEqual(self.state,self.before)
        self.assertFalse(any(m=="DELETE" for m,p in self.calls))
    def test_tree_before(self): self.fault("POST","/git/trees",False)
    def test_tree_after(self): self.fault("POST","/git/trees",True)
    def test_commit_before(self): self.fault("POST","/git/commits",False)
    def test_commit_after(self): self.fault("POST","/git/commits",True)
    def test_ref_before(self): self.fault("PATCH","/heads/"+install.BRANCH,False)
    def test_ref_after(self): self.fault("PATCH","/heads/"+install.BRANCH,True)
    def bad_response(self,method,suffix,value):
        def request(m,p,b):
            result=self.original(m,p,b)
            if m==method and p.endswith(suffix): return dict(result,sha=value)
            return result
        self.intercept(request)
        with self.assertRaises(ValueError): self.save()
        self.assertFalse(any(m=="PATCH" for m,p in self.calls))
        self.assertEqual(self.api.ref,s.HEAD)
        self.assertEqual(self.state,self.before)
    def test_wrong_commit_read(self): self.bad_response("GET","/git/commits/"+s.HEAD,s.NEXT)
    def test_bad_tree_sha(self): self.bad_response("POST","/git/trees","short")
    def test_bad_commit_sha(self): self.bad_response("POST","/git/commits","short")
    def test_noop_apply(self):
        result=session.save(self.api,self.state,self.state["ledger"],self.state["handoff"],True)
        self.assertEqual(result,{"status":"unchanged","installed_sha":s.HEAD})
        self.assertEqual(self.api.writes,[])
    def test_stale_ref_no_object_creation(self):
        self.api.ref=s.NEXT
        with self.assertRaises(ValueError): self.save()
        self.assertEqual(self.api.writes,[])
    def test_postwrite_unexpected_ref(self):
        def request(m,p,b):
            result=self.original(m,p,b)
            if m=="PATCH": self.api.ref=s.FIX
            return result
        self.intercept(request)
        with self.assertRaisesRegex(ValueError,"Unexpected ref"): self.save()
        self.assertEqual(sum(m=="PATCH" for m,p in self.calls),1)
        self.assertEqual(self.api.ref,s.FIX)
        self.assertEqual(self.state,self.before)

class Readback(unittest.TestCase):
    def wait(self,values,previous=s.HEAD):
        with patch.object(install,"read_ref",side_effect=values) as read, patch.object(install.time,"sleep") as sleep:
            result=install.wait_ref(None,"/synthetic",install.BRANCH,s.NEXT,previous)
            self.assertEqual(read.call_count,len(values))
            self.assertEqual(sleep.call_count,len(values)-1)
            return result
    def test_immediate(self): self.assertEqual(self.wait([s.NEXT]),s.NEXT)
    def test_old_then_new(self): self.assertEqual(self.wait([s.HEAD,s.NEXT]),s.NEXT)
    def test_absent_then_new(self): self.assertEqual(self.wait([None,None,s.NEXT],None),s.NEXT)
    def test_last_allowed_read(self): self.assertEqual(self.wait([s.HEAD]*5+[s.NEXT]),s.NEXT)
    def test_exhaustion(self):
        with patch.object(install,"read_ref",return_value=s.HEAD) as read, patch.object(install.time,"sleep") as sleep:
            with self.assertRaisesRegex(ValueError,"not confirmed"):
                install.wait_ref(None,"/synthetic",install.BRANCH,s.NEXT,s.HEAD)
            self.assertEqual(read.call_count,6)
            self.assertEqual(sleep.call_count,5)
    def test_unexpected_read_stops(self):
        with patch.object(install,"read_ref",side_effect=[s.FIX,s.NEXT]) as read, patch.object(install.time,"sleep") as sleep:
            with self.assertRaisesRegex(ValueError,"Unexpected"):
                install.wait_ref(None,"/synthetic",install.BRANCH,s.NEXT,s.HEAD)
            self.assertEqual(read.call_count,1)
            sleep.assert_not_called()
    def test_invalid_expected_no_reads(self):
        with patch.object(install,"read_ref") as read:
            with self.assertRaises(ValueError): install.wait_ref(None,"/synthetic",install.BRANCH,"short",s.HEAD)
            read.assert_not_called()
    def test_invalid_previous_no_reads(self):
        with patch.object(install,"read_ref") as read:
            with self.assertRaises(ValueError): install.wait_ref(None,"/synthetic",install.BRANCH,s.NEXT,"short")
            read.assert_not_called()

if __name__=="__main__":
    loader=unittest.defaultTestLoader
    run_suite(unittest.TestSuite([loader.loadTestsFromTestCase(c) for c in (Publication,HandoffWrites,Readback)]),41,"interruptions")
