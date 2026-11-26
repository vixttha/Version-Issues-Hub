"""Boundary tests for actual VIB ledger, handoff and receipt-scope validators."""
import copy
import sys
import unittest
import test_core
from tools import checkpoint,session
from record import run_suite

def ledger():
    return {"schema_version":1,"repository":"example/product","issues":[{"issue":1,"version":"v1.0.0.1","state":"in_progress","acceptance":["test"]}]}
def active():
    return {"issue":1,"version":"v1.0.0.1","phase":"Worker","next_action":"test","fix_sha":None,"candidate_sha":None,"pull_request":None,"evidence":[]}
def handoff():
    return {"schema_version":1,"active":active(),"history":[]}
def scope():
    return {"fixes":{"v1.0.0.1":"a"*40},"versions":["v1.0.0.1"]}
class Ledger(unittest.TestCase):
    def test_valid(self): self.assertEqual(checkpoint.bindings(ledger()),{1:"v1.0.0.1"})
    def test_duplicate_json(self):
        with self.assertRaises(ValueError): checkpoint.parse_json('{"x":1,"x":2}')
    def test_duplicate_issue(self):
        data=ledger(); data["issues"].append(dict(data["issues"][0],version="v1.0.0.2"))
        with self.assertRaisesRegex(ValueError,"Duplicate issue"): checkpoint.bindings(data)
    def test_duplicate_version(self):
        data=ledger(); data["issues"].append(dict(data["issues"][0],issue=2))
        with self.assertRaisesRegex(ValueError,"Duplicate version"): checkpoint.bindings(data)
    def test_history_removed(self):
        before=ledger(); after=ledger(); after["issues"]=[]
        with self.assertRaisesRegex(ValueError,"Historical assignment changed"): checkpoint.check_history(after,before)
    def test_history_changed(self):
        before=ledger(); after=ledger(); after["issues"][0]["version"]="v1.0.0.2"
        with self.assertRaisesRegex(ValueError,"Historical assignment changed"): checkpoint.check_history(after,before)
    def test_register_numeric_order(self):
        data=ledger(); data["issues"][0]["version"]="v1.0.0.9"
        self.assertEqual(checkpoint.register(data,2,"v1.0.0",["test"]),("v1.0.0.10",True))
        self.assertEqual(checkpoint.register(data,3,"v1.0.0",["test"]),("v1.0.0.11",True))
        self.assertEqual([x["version"] for x in data["issues"]],["v1.0.0.9","v1.0.0.10","v1.0.0.11"])
    def test_register_wrong_line(self):
        data=ledger(); before=copy.deepcopy(data)
        with self.assertRaises(ValueError): checkpoint.register(data,1,"v1.0.1",["test"])
        self.assertEqual(data,before)
def ledger_case(field,value):
    def test(self):
        data=ledger(); data["issues"][0][field]=value
        with self.assertRaises(ValueError): checkpoint.bindings(data)
    return test
for name,field,value in [
    ("bool_issue","issue",True),("zero_issue","issue",0),("negative_issue","issue",-1),
    ("float_issue","issue",1.0),("leading_zero_version","version","v1.0.0.01"),
    ("zero_checkpoint","version","v1.0.0.0"),("invalid_state","state","done"),
    ("empty_criteria","acceptance",[]),("blank_criteria","acceptance",["  "]),
    ("nonstring_criteria","acceptance",[1])]:
    setattr(Ledger,"test_"+name,ledger_case(field,value))
class Handoff(unittest.TestCase):
    def test_valid(self): session.validate_handoff(handoff(),ledger())
    def test_orphan(self):
        data=handoff(); data["active"]=None
        with self.assertRaisesRegex(ValueError,"Orphan"): session.validate_handoff(data,ledger())
    def test_two_active_rows(self):
        data=ledger(); data["issues"].append(dict(data["issues"][0],issue=2,version="v1.0.0.2"))
        with self.assertRaisesRegex(ValueError,"sole in-progress"): session.validate_handoff(handoff(),data)
    def test_worker_stale(self):
        data=active(); data.update(fix_sha="a"*40,candidate_sha="b"*40,pull_request=2)
        with self.assertRaisesRegex(ValueError,"stale verification"): session.validate_active(data,ledger())
    def test_auditor_no_evidence(self):
        data=active(); data.update(phase="Internal Auditor",fix_sha="a"*40,candidate_sha="b"*40,pull_request=2)
        with self.assertRaisesRegex(ValueError,"requires evidence"): session.validate_active(data,ledger())
def active_case(field,value):
    def test(self):
        data=active(); data[field]=value
        with self.assertRaises(ValueError): session.validate_active(data,ledger())
    return test
for name,field,value in [
    ("unknown_phase","phase","Manager"),("wrong_issue","issue",2),("wrong_version","version","v1.0.0.2"),
    ("blank_action","next_action"," "),("partial_fix","fix_sha","a"*40),("validate_missing","phase","Validate"),
    ("worker_evidence","evidence",["https://github.com/example/product/actions/runs/1/attempts/1"])]:
    setattr(Handoff,"test_"+name,active_case(field,value))
class Scope(unittest.TestCase):
    def test_valid(self): checkpoint.check_receipt_scope(ledger(),scope())
    def test_duplicate_selected(self):
        data=scope(); data["versions"]*=2
        with self.assertRaisesRegex(ValueError,"duplicate"): checkpoint.check_receipt_scope(ledger(),data)
    def test_historical_fix(self):
        data=scope(); data["fixes"]["v1.0.0.1"]="b"*40
        with self.assertRaisesRegex(ValueError,"Historical fix"): checkpoint.check_receipt_scope(ledger(),data,scope())
    def test_unknown_fix(self):
        data=scope(); data["fixes"]["v1.0.0.2"]="b"*40
        with self.assertRaises(ValueError): checkpoint.check_receipt_scope(ledger(),data)
    def test_no_fix(self):
        data=scope(); data["fixes"]={}
        with self.assertRaises(ValueError): checkpoint.check_receipt_scope(ledger(),data)
    def test_bad_sha(self):
        data=scope(); data["fixes"]["v1.0.0.1"]="short"
        with self.assertRaises(ValueError): checkpoint.check_receipt_scope(ledger(),data)
    def test_no_selection(self):
        data=scope(); data["versions"]=[]
        with self.assertRaises(ValueError): checkpoint.check_receipt_scope(ledger(),data)
class Links(unittest.TestCase):
    def test_valid(self): self.assertEqual(session.evidence_links("example/product",["https://github.com/example/product/actions/runs/1/attempts/1"]),["https://github.com/example/product/actions/runs/1/attempts/1"])
    def test_duplicates(self):
        with self.assertRaisesRegex(ValueError,"Duplicate"): session.evidence_links("example/product",["https://github.com/example/product/actions/runs/1/attempts/1"]*2)
def link_case(value):
    def test(self):
        with self.assertRaises(ValueError): session.evidence_links("example/product",[value])
    return test
for name,value in {"foreign":"https://github.com/example/other/actions/runs/1/attempts/1","no_attempt":"https://github.com/example/product/actions/runs/1","zero_run":"https://github.com/example/product/actions/runs/0/attempts/1","zero_attempt":"https://github.com/example/product/actions/runs/1/attempts/0","query":"https://github.com/example/product/actions/runs/1/attempts/1?x=1","http":"http://github.com/example/product/actions/runs/1/attempts/1","wrong_host":"https://example.invalid/example/product/actions/runs/1/attempts/1","nonstring":1}.items():
    setattr(Links,"test_"+name,link_case(value))
if __name__=="__main__":
    run_suite(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]),47,"schema")
