"""Q05-Q09: mutation, concurrent file writers, bounded benchmarks, CLI."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import tracemalloc
import unittest
import test_core as c
import test_completion as comp
import test_receipt as rec
import test_interruptions as intr
import test_qualification as qual
from test_mutation import mutation_case
from tools import checkpoint,gate,install,lifecycle,session
from record import run_suite

class Mutants(unittest.TestCase): pass
mutants=[
    ("receipt_checkout",checkpoint,"receipt",'if checkout != require(SHA, env["GITHUB_SHA"], "workflow checkout"):','if False:',rec.Receipt,"test_wrong_checkout"),
    ("receipt_push",checkpoint,"receipt",'if candidate_sha != checkout:','if False:',rec.Receipt,"test_wrong_push"),
    ("receipt_parent_order",checkpoint,"receipt",'if list(parents) != [base_sha, candidate_sha]:','if False:',rec.Receipt,"test_pr_reversed_parents"),
    ("stale_gate_base",gate,"assert_current_pr",'if install.read_ref(api, prefix, policy["product_branch"]) != policy["base_sha"]:','if False:',qual.Scope,"test_stale_product_ref"),
    ("gate_evidence",gate,"check_test",'if details not in evidence:','if False:',qual.Scope,"test_only_other_issue_has_run"),
    ("archive_collision",lifecycle,"prepare_retirement",'if existing not in (None,expected_sha):','if False:',qual.Archive,"test_archive_collision"),
    ("archive_owner",lifecycle,"prepare_retirement",'if not owner_approved:','if False:',qual.Archive,"test_no_approval"),
    ("ref_readback_unexpected",install,"wait_ref",'if observed != previous:','if False:',intr.Readback,"test_unexpected_read_stops"),
]
for name,module,fn,old,new,cls,method in mutants:
    setattr(Mutants,"test_"+name,mutation_case(module,fn,old,new,cls,method))

class LedgerBench(unittest.TestCase):
    def bench(self,n):
        ledger={"schema_version":1,"repository":"example/product","issues":[
            {"issue":i,"version":"v1.0.0."+str(i),"state":"integrated","acceptance":["verified"]}
            for i in range(1,n+1)]}
        start=time.perf_counter()
        tracemalloc.start()
        try:
            bindings=checkpoint.bindings(ledger)
            self.assertEqual(len(bindings),n)
            self.assertEqual(bindings[n],"v1.0.0."+str(n))
            before=copy.deepcopy(ledger)
            self.assertEqual(checkpoint.register(ledger,n+1,"v1.0.0",["next"]),("v1.0.0."+str(n+1),True))
            checkpoint.check_history(ledger,before)
            raw=json.dumps(ledger)
            self.assertEqual(checkpoint.bindings(checkpoint.parse_json(raw))[n+1],"v1.0.0."+str(n+1))
            elapsed=time.perf_counter()-start
            peak=tracemalloc.get_traced_memory()[1]
        finally: tracemalloc.stop()
        print("VIB_BENCH "+json.dumps({"records":n,"elapsed_seconds":round(elapsed,4),"peak_traced_bytes":peak,"serialized_bytes":len(raw.encode())}),flush=True)
        self.assertLess(elapsed,120)
        self.assertLess(peak,256*1024*1024)
    def test_1000(self): self.bench(1000)
    def test_10000(self): self.bench(10000)
    def test_50000(self): self.bench(50000)
    def test_large_payload(self):
        text="a"*(2*1024*1024)
        self.assertEqual(checkpoint.parse_json(json.dumps({"payload":text}))["payload"],text)
        self.assertEqual(lifecycle.digest_files({"payload":text})["payload"],hashlib.sha256(text.encode()).hexdigest())
    def test_large_numeric_rejection(self):
        with self.assertRaises(ValueError): checkpoint.parse_json('{"n":'+"9"*5000+"}")
    def test_truncated_large_payload(self):
        with self.assertRaises(ValueError): checkpoint.parse_json('{"payload":"'+("a"*1024*1024))
    def test_subprocess_timeout(self):
        with self.assertRaises(subprocess.TimeoutExpired):
            subprocess.run([sys.executable,"-c","import time;time.sleep(30)"],capture_output=True,timeout=1)
    def test_large_output_transport(self):
        r=subprocess.run([sys.executable,"-c","import sys;sys.stdout.buffer.write(b'x'*1048576);sys.stderr.buffer.write(b'y'*1048576)"],capture_output=True,timeout=20,check=True)
        self.assertEqual(r.stdout,b"x"*1048576);self.assertEqual(r.stderr,b"y"*1048576)

class CLI(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory(prefix="vib54 cli ")
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.path=self.root/checkpoint.LEDGER
        self.path.parent.mkdir(parents=True)
        self.original={"schema_version":1,"repository":"example/product","issues":[]}
        checkpoint.write_json(self.path,self.original)
        self.env=dict(os.environ,PYTHONPATH=str(c.PRODUCT),PYTHONUTF8="1",PYTHONDONTWRITEBYTECODE="1",GH_TOKEN="",GITHUB_TOKEN="")
    def invoke(self,module,args):
        return subprocess.run([sys.executable,"-B","-m","tools."+module,*args],cwd=self.root,env=self.env,capture_output=True,timeout=20)
    def rejected(self,module,args,code):
        before=self.path.read_bytes()
        result=self.invoke(module,args)
        self.assertEqual(result.returncode,code,result.stderr.decode(errors="replace"))
        self.assertEqual(self.path.read_bytes(),before)
        self.assertFalse(list(self.root.glob("*.json")))
    def test_positive_register(self):
        result=self.invoke("checkpoint",["register","1","v0.0.0","--acceptance","check"])
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(self.path.read_bytes())["issues"][0]["version"],"v0.0.0.1")
    def test_positive_check(self):
        self.assertEqual(self.invoke("checkpoint",["check"]).returncode,0)
    def test_invalid_previous_sha(self): self.rejected("checkpoint",["check","--previous-ref","short"],1)
    def test_empty_acceptance(self): self.rejected("checkpoint",["register","1","v0.0.0"],1)
    def test_negative_issue(self): self.rejected("checkpoint",["register","-1","v0.0.0","--acceptance","check"],1)
    def test_zero_issue(self): self.rejected("checkpoint",["register","0","v0.0.0","--acceptance","check"],1)
    def test_invalid_line(self): self.rejected("checkpoint",["register","1","v0.0","--acceptance","check"],1)
    def test_nonnumeric_issue(self): self.rejected("checkpoint",["register","one","v0.0.0"],2)
    def test_unknown_command(self): self.rejected("checkpoint",["unknown"],2)
    def test_missing_command(self): self.rejected("checkpoint",[],2)
    def test_unknown_option(self): self.rejected("checkpoint",["check","--invented"],2)
    def test_install_missing_token(self): self.rejected("install",["--target","example/product","--source-sha","a"*40,"--baseline","v0.0.0","--apply"],2)
    def test_install_missing_baseline(self): self.rejected("install",["--target","example/product","--source-sha","a"*40],2)
    def test_lifecycle_missing_token(self): self.rejected("lifecycle",["--target","example/product","--expected-sha","a"*40,"prepare-retirement","--apply"],2)
    def test_lifecycle_missing_expected(self): self.rejected("lifecycle",["--target","example/product","prepare-retirement"],2)
    def test_session_bad_disposition(self): self.rejected("session",["--target","example/product","finish","unknown","--decision","test"],2)
    def test_session_missing_note(self): self.rejected("session",["--target","example/product","advance"],2)
    def test_session_bad_issue(self): self.rejected("session",["--target","example/product","claim","abc","--note","test"],2)

class Writers(unittest.TestCase):
    def writers(self,n):
        with tempfile.TemporaryDirectory(prefix="vib54 writers ") as tmp:
            root=Path(tmp); target=root/"receipt.json"
            checkpoint.write_json(target,{"writer":-1,"body":"initial"})
            env=dict(os.environ,PYTHONPATH=str(c.PRODUCT),PYTHONDONTWRITEBYTECODE="1",PYTHONUTF8="1")
            code="""import sys,time
from pathlib import Path
from tools import checkpoint
root=Path(sys.argv[1]); i=int(sys.argv[2])
deadline=time.monotonic()+15
while not (root/'go').exists():
    if time.monotonic()>deadline: raise TimeoutError('barrier')
    time.sleep(.01)
try:
    checkpoint.write_json(root/'receipt.json',{'writer':i,'body':str(i)*65536})
except OSError:
    raise SystemExit(3)
"""
            children=[]
            try:
                for i in range(n):
                    children.append(subprocess.Popen([sys.executable,"-B","-c",code,str(root),str(i)],env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE))
                (root/"go").touch()
                codes=[]
                for p in children:
                    out,err=p.communicate(timeout=30)
                    self.assertIn(p.returncode,(0,3),err)
                    codes.append(p.returncode)
                self.assertIn(0,codes)
                value=json.loads(target.read_bytes())
                winner=value["writer"]
                self.assertIn(winner,range(n))
                self.assertEqual(codes[winner],0)
                self.assertEqual(value["body"],str(winner)*65536)
                self.assertEqual({x.name for x in root.iterdir()},{"receipt.json","go"})
                print("VIB_WRITERS "+json.dumps({"writers":n,"successful":codes.count(0),"os_errors":codes.count(3),"final_writer":winner}),flush=True)
            finally:
                for p in children:
                    if p.poll() is None: p.kill();p.communicate()
    def test_two(self): self.writers(2)
    def test_eight(self): self.writers(8)
    def test_sixteen(self): self.writers(16)

if __name__=="__main__":
    loader=unittest.defaultTestLoader
    run_suite(unittest.TestSuite([loader.loadTestsFromTestCase(k) for k in (Mutants,LedgerBench,CLI,Writers)]),37,"high")
