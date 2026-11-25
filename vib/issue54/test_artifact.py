"""Adversarial controls for the independent pre-upload audit."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import audit_evidence as audit
from record import run_suite

class Artifact(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(prefix="vib54 evidence ")
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.kind="artifact"
        self.vault="a"*40
        self.product="b"*40
        self.log=self.root/"artifact.log"
        self.report=self.root/"artifact.json"
        self.ids=self.root/"artifact-identities.json"
        self.log.write_bytes(b"synthetic log\n")
        self.data={"kind":self.kind,"vault_sha":self.vault,"product_sha":self.product,
                   "run_id":"123","attempt":"2","expected_count":2,"passed_ids":["a","b"],
                   "exit_code":0,"outcome":"pass",
                   "log_sha256":hashlib.sha256(self.log.read_bytes()).hexdigest()}
        self.save()
    def save(self):
        self.report.write_text(json.dumps(self.data),encoding="utf-8")
        self.ids.write_text(json.dumps(self.data["passed_ids"]),encoding="utf-8")
    def verify(self):
        return audit.verify(self.root,self.kind,2,self.vault,self.product,"123","2")
    def rejected(self):
        with self.assertRaises(ValueError): self.verify()
    def test_positive(self):
        self.assertEqual(self.verify(),{"kind":"artifact","expected":2,"passed":2,"outcome":"pass"})
    def test_red_evidence_preserved(self):
        self.data.update(passed_ids=["a"],exit_code=1,outcome="fail")
        self.save()
        self.assertEqual(self.verify()["outcome"],"fail")
        self.assertEqual(self.verify()["passed"],1)
    def test_corrupted_log(self):
        self.log.write_bytes(b"changed")
        self.rejected()
    def test_missing_log(self):
        self.log.unlink(); self.rejected()
    def test_missing_report(self):
        self.report.unlink(); self.rejected()
    def test_missing_identity_list(self):
        self.ids.unlink(); self.rejected()
    def test_changed_identity_list(self):
        self.ids.write_text('["a","c"]',encoding="utf-8")
        self.rejected()
    def test_duplicate_json_key(self):
        raw=self.report.read_text(encoding="utf-8")
        self.report.write_text(raw[:-1]+',"kind":"artifact"}',encoding="utf-8")
        self.rejected()
    def test_truncated_json(self):
        self.report.write_text("{",encoding="utf-8")
        self.rejected()
    def test_wrong_runner_inventory(self):
        with self.assertRaises(ValueError): audit.inventory("Unknown")
    def test_platform_inventory(self):
        self.assertEqual(sum(audit.inventory("Linux").values()),542)
        self.assertEqual(sum(audit.inventory("Windows").values()),542)
        self.assertNotIn("powershell",audit.inventory("Linux"))
        self.assertNotIn("bash",audit.inventory("Windows"))

def changed(key,value):
    def test(self):
        self.data[key]=value
        self.save()
        self.rejected()
    return test
for name,key,value in [
    ("vault","vault_sha","c"*40),("product","product_sha","c"*40),
    ("run","run_id","124"),("attempt","attempt","1"),("suite","kind","other"),
    ("count","expected_count",3),("count_float","expected_count",2.0),
    ("duplicate_ids","passed_ids",["a","a"]),("missing_pass","passed_ids",["a"]),
    ("extra_ids","passed_ids",["a","b","c"]),("blank_id","passed_ids",["a"," "]),
    ("exit_code","exit_code",1),("bool_exit_code","exit_code",False)]:
    setattr(Artifact,"test_"+name,changed(key,value))

if __name__=="__main__":
    run_suite(unittest.defaultTestLoader.loadTestsFromTestCase(Artifact),24,"artifact")
