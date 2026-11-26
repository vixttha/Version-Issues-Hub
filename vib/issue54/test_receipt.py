"""Exercise actual receipt metadata and atomic file replacement; no live API."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import test_schema as schema
from record import run_suite
from tools import checkpoint

class Receipt(unittest.TestCase):
    def setUp(self):
        self.ledger=schema.ledger()
        self.version="v1.0.0.1"
        self.checkout="c"*40
        self.fix="a"*40
        self.env={"GITHUB_SHA":self.checkout,"GITHUB_REPOSITORY":"example/product","GITHUB_EVENT_NAME":"push",
                  "GITHUB_RUN_ID":"123","GITHUB_RUN_ATTEMPT":"2","GITHUB_WORKFLOW":"fixture","GITHUB_JOB":"fixture"}
        self.event={"repository":{"full_name":"example/product"},"after":self.checkout}
        self.parents=[]
    def receipt(self):
        return checkpoint.receipt(self.ledger,self.version,self.checkout,self.env,self.event,self.parents,fix_sha=self.fix)
    def as_pr(self):
        self.env["GITHUB_EVENT_NAME"]="pull_request"
        self.event["pull_request"]={"head":{"sha":"b"*40},"base":{"sha":"a"*40},"number":7}
        self.parents=["a"*40,"b"*40]
    def test_valid_push(self):
        result=self.receipt()
        self.assertEqual((result["candidate_sha"],result["tested_sha"],result["fix_sha"]),(self.checkout,self.checkout,self.fix))
        self.assertEqual(result["run_url"],"https://github.com/example/product/actions/runs/123/attempts/2")
        self.assertIsNone(result["pull_request"])
    def test_valid_pr(self):
        self.as_pr()
        result=self.receipt()
        self.assertEqual((result["base_sha"],result["candidate_sha"],result["tested_sha"],result["pull_request"]),("a"*40,"b"*40,self.checkout,7))
    def test_wrong_event_repository(self):
        self.event["repository"]["full_name"]="example/other"
        with self.assertRaises(ValueError): self.receipt()
    def test_wrong_push(self):
        self.event["after"]="d"*40
        with self.assertRaises(ValueError): self.receipt()
    def test_missing_version(self):
        self.version="v1.0.0.2"
        with self.assertRaises(ValueError): self.receipt()
    def test_invalid_fix(self):
        self.fix="short"
        with self.assertRaises(ValueError): self.receipt()
    def test_pr_reversed_parents(self):
        self.as_pr(); self.parents.reverse()
        with self.assertRaises(ValueError): self.receipt()
    def test_pr_extra_parent(self):
        self.as_pr(); self.parents.append("d"*40)
        with self.assertRaises(ValueError): self.receipt()
    def test_pr_missing_parent(self):
        self.as_pr(); self.parents.pop()
        with self.assertRaises(ValueError): self.receipt()
    def test_pr_bool_number(self):
        self.as_pr(); self.event["pull_request"]["number"]=True
        with self.assertRaises(ValueError): self.receipt()
    def test_pr_short_head(self):
        self.as_pr(); self.event["pull_request"]["head"]["sha"]="short"
        with self.assertRaises(ValueError): self.receipt()
    def test_pr_short_base(self):
        self.as_pr(); self.event["pull_request"]["base"]["sha"]="short"
        with self.assertRaises(ValueError): self.receipt()

def env_case(key,value):
    def test(self):
        self.env[key]=value
        with self.assertRaises(ValueError): self.receipt()
    return test
for name,key,value in [
    ("wrong_checkout","GITHUB_SHA","d"*40),("wrong_repo","GITHUB_REPOSITORY","example/other"),
    ("wrong_event","GITHUB_EVENT_NAME","workflow_dispatch"),("zero_run","GITHUB_RUN_ID","0"),
    ("leading_zero_run","GITHUB_RUN_ID","0123"),("numeric_run","GITHUB_RUN_ID",123),
    ("zero_attempt","GITHUB_RUN_ATTEMPT","0"),("malformed_attempt","GITHUB_RUN_ATTEMPT","2.0")]:
    setattr(Receipt,"test_"+name,env_case(key,value))

class AtomicFile(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(prefix="vib54 [receipt] ")
        self.addCleanup(t.cleanup)
        self.root=Path(t.name); self.path=self.root/"receipt.json"
    def test_utf8_lf(self):
        data={"text":"caf\u00e9 \u6c34","count":1}
        checkpoint.write_json(self.path,data)
        raw=self.path.read_bytes()
        self.assertEqual(raw,(json.dumps(data,indent=2)+"\n").encode("utf-8"))
        self.assertEqual(json.loads(raw),data)
    def test_replace(self):
        self.path.write_bytes(b"long old content\n")
        checkpoint.write_json(self.path,{"new":1})
        self.assertEqual(json.loads(self.path.read_bytes()),{"new":1})
        self.assertEqual(list(self.root.iterdir()),[self.path])
    def test_failed_replace_preserves_old(self):
        self.path.write_bytes(b"previous\n")
        with patch.object(Path,"replace",side_effect=OSError("synthetic replacement failure")):
            with self.assertRaises(OSError): checkpoint.write_json(self.path,{"new":1})
        self.assertEqual(self.path.read_bytes(),b"previous\n")
        self.assertEqual(list(self.root.iterdir()),[self.path])
    def test_failed_first_write_no_partial_file(self):
        with patch.object(Path,"replace",side_effect=OSError("synthetic replacement failure")):
            with self.assertRaises(OSError): checkpoint.write_json(self.path,{"new":1})
        self.assertFalse(self.path.exists())
        self.assertEqual(list(self.root.iterdir()),[])

if __name__=="__main__":
    loader=unittest.defaultTestLoader
    run_suite(unittest.TestSuite([loader.loadTestsFromTestCase(Receipt),loader.loadTestsFromTestCase(AtomicFile)]),24,"receipt")
