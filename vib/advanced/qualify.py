"""Bounded qualification for batches 7-16. No remote writes."""
import ast
import copy
import hashlib
import io
import itertools
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
import zipfile

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"issue54"))
import test_core as c
import test_completion as f
import test_schema as schema
import test_artifact as artifact
from test_mutation import mutation_case
from tools import checkpoint,install,lifecycle,session,gate
from record import Result,flatten,verdict
import archive

P=c.PRODUCT
def ledger(): return {"schema_version":1,"repository":"example/product","issues":[]}

class B07(unittest.TestCase):
    def test_exact_catalog(self):
        self.assertTrue(verdict(["one","two"],["two","one"],2,True))
        self.assertFalse(verdict(["one","two"],["one","other"],2,True))
    def test_optimized_catalog(self):
        code="from record import verdict; raise SystemExit(0 if not verdict(['one'],['other'],1,True) else 1)"
        env=dict(os.environ,PYTHONPATH=str(HERE.parent/"issue54"))
        self.assertEqual(subprocess.run([sys.executable,"-O","-B","-c",code],env=env,timeout=20).returncode,0)
    def test_original_harness_optimized_guard(self):
        # Extract actual assertion AST into a harmless isolated child, not a live runner.
        source=(HERE.parents[1]/"vib/run_cases.py").read_text(encoding="utf-8")
        node=next(n for n in ast.walk(ast.parse(source)) if isinstance(n,ast.If) and "Product checkout mismatch" in ast.unparse(n))
        fragment=ast.unparse(node)
        script="product_sha='wrong'; plan={'product_sha':'expected'}\n"+fragment
        normal=subprocess.run([sys.executable,"-B","-c",script],capture_output=True,timeout=20)
        optimized=subprocess.run([sys.executable,"-O","-B","-c",script],capture_output=True,timeout=20)
        self.assertNotEqual(normal.returncode,0)
        self.assertNotEqual(optimized.returncode,0,"actual baseline SHA guard disappears under -O")
    def test_original_auditor_substitution(self):
        fixture=artifact.Artifact("test_positive")
        fixture.setUp()
        try:
            fixture.verify()
            fixture.data["passed_ids"]=["invented-one","invented-two"]
            fixture.save()
            with self.assertRaises(ValueError): fixture.verify()
        finally: fixture.doCleanups()

class B08(unittest.TestCase):
    def matrix(self,head,base,run,job,step):
        g=f.g; policy,state=g.fixture(); api=g.Fake()
        if not head: api.pr["head"]["sha"]=g.SOURCE
        if not base: api.pr["base"]["sha"]=g.SOURCE
        if not run: api.run["conclusion"]="failure"
        if not job: api.jobs[0]["conclusion"]="failure"
        if not step: api.jobs[0]["steps"][0]["conclusion"]="failure"
        before=copy.deepcopy(state)
        with patch.object(session,"load",return_value=state):
            if all((head,base,run,job,step)):
                self.assertEqual(gate.evaluate(api,g.REPO,policy)["status"],"pass")
            else:
                with self.assertRaises(ValueError): gate.evaluate(api,g.REPO,policy)
        self.assertEqual(state,before);self.assertEqual(api.writes,[])
    def sequence(self,order):
        s=f.s; api=s.Fake(); state=s.state()
        state["ledger"],state["handoff"]=session.claim(api,state,247,["test"],"Fix")
        accepted=[]
        for action in order:
            before=copy.deepcopy(state)
            phase=state["handoff"]["active"]["phase"]
            allowed={"Worker":"candidate","Validate":"evidence","Internal Auditor":"audit"}.get(phase)
            # Plain advance at Worker/Validate must reject missing data. Extra
            # candidate arguments at later phases are not a distinct transition;
            # use only sequences of actual commands with an independent phase oracle.
            if action=="candidate":
                kw={"fix":s.FIX,"candidate":s.CANDIDATE,"pr":8}
            elif action=="evidence": kw={"evidence":[s.RUN]}
            else: kw={}
            if phase=="Worker":
                success=action=="candidate"
            elif phase=="Validate":
                success=action=="evidence"
            elif phase=="Internal Auditor": success=True
            else: success=False
            if success:
                l,h=session.advance(api,state,"step",**kw)
                self.assertEqual(state,before)
                state["ledger"],state["handoff"]=l,h
                accepted.append(action)
                self.assertEqual(h["active"]["phase"],{"Worker":"Validate","Validate":"Internal Auditor","Internal Auditor":"Head"}[phase])
            else:
                with self.assertRaises(ValueError): session.advance(api,state,"step",**kw)
                self.assertEqual(state,before)
        self.assertEqual(api.writes,[])
        session.validate_handoff(state["handoff"],state["ledger"])

class B09(unittest.TestCase):
    def corpus(self,seed):
        rng=random.Random(seed); x=ledger(); expected={}
        for _ in range(80):
            issue=rng.randint(1,45); line="v1.0.0"
            prior=copy.deepcopy(x)
            v,new=checkpoint.register(x,issue,line,["unicode \u03b1"])
            if issue in expected: self.assertFalse(new);self.assertEqual(x,prior)
            else: expected[issue]=line+"."+str(len(expected)+1);self.assertTrue(new)
            self.assertEqual(v,expected[issue]);self.assertEqual(checkpoint.bindings(x),expected)
            checkpoint.check_history(x,prior)
        shuffled=copy.deepcopy(x);rng.shuffle(shuffled["issues"])
        self.assertEqual(checkpoint.bindings(shuffled),expected)
        checkpoint.check_history(shuffled,x)
        raw=json.dumps(x,ensure_ascii=False)
        self.assertEqual(checkpoint.parse_json(raw),x)
        # Generated malformed records, exact rejection and no mutation.
        for value in (True,False,0,-1,None,"1",1.5,[],{}):
            malformed=copy.deepcopy(x);malformed["issues"][0]["issue"]=value
            with self.assertRaises(ValueError): checkpoint.bindings(malformed)
    def test_schema_boolean(self):
        x=ledger();x["schema_version"]=True
        with self.assertRaises(ValueError):checkpoint.bindings(x)
    def test_nonfinite_nan(self):
        with self.assertRaises(ValueError): checkpoint.parse_json('{"n":NaN}')
    def test_nonfinite_inf(self):
        with self.assertRaises(ValueError): checkpoint.parse_json('{"n":Infinity}')
    def test_nonfinite_negative_inf(self):
        with self.assertRaises(ValueError): checkpoint.parse_json('{"n":-Infinity}')
    def test_invalid_utf8(self):
        with self.assertRaises(UnicodeDecodeError): checkpoint.parse_json(b'{"x":"\xff"}')
    def test_duplicate_escaped_key(self):
        with self.assertRaises(ValueError): checkpoint.parse_json(r'{"a":1,"\u0061":2}')
    def test_nonfinite_persistence(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"receipt.json"
            checkpoint.write_json(p,{"safe":1}); old=p.read_bytes()
            with self.assertRaises(ValueError): checkpoint.write_json(p,{"n":float("nan")})
            self.assertEqual(p.read_bytes(),old)

class B10(unittest.TestCase):
    def archive(self,entries,expected):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"fixture.zip"
            with zipfile.ZipFile(p,"w") as z:
                for name,data in entries:z.writestr(name,data)
            return archive.inspect_zip(p,expected,hashlib.sha256(p.read_bytes()).hexdigest())
    def test_valid(self):
        self.assertEqual(self.archive([("a.txt",b"x")],{"a.txt"}),{"a.txt":b"x"})
    def test_missing(self):
        with self.assertRaises(ValueError): self.archive([],{"a.txt"})
    def test_unexpected(self):
        with self.assertRaises(ValueError): self.archive([("b.txt",b"x")],{"a.txt"})
    def test_parent(self):
        with self.assertRaises(ValueError): self.archive([("../a.txt",b"x")],{"../a.txt"})
    def test_case_alias(self):
        with self.assertRaises(ValueError): self.archive([("a.txt",b"x"),("A.txt",b"y")],{"a.txt","A.txt"})
    def test_duplicate(self):
        with self.assertRaises(ValueError): self.archive([("a.txt",b"x"),("a.txt",b"y")],{"a.txt"})
    def test_reproducible_receipt_bytes(self):
        with tempfile.TemporaryDirectory() as d:
            a=Path(d)/"a";b=Path(d)/"b";data={"version":"v0.0.1.1","value":"\u00e9"}
            checkpoint.write_json(a,data);checkpoint.write_json(b,data)
            self.assertEqual(a.read_bytes(),b.read_bytes())
    def test_wrong_archive_digest(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"a.zip"
            with zipfile.ZipFile(p,"w") as z:z.writestr("a",b"x")
            with self.assertRaises(ValueError):archive.inspect_zip(p,{"a"},"0"*64)

class B11(unittest.TestCase):
    def test_real_loopback_response(self):
        # Real urllib HTTP wire parsing; local fixture only. Rewrite destination
        # within the test adapter; production Request method/body/header preserved.
        from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
        from threading import Thread
        from urllib.request import Request,build_opener
        seen=[]
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*a): pass
            def do_POST(self):
                raw=self.rfile.read(int(self.headers["Content-Length"]))
                seen.append((self.path,self.headers.get("Authorization"),json.loads(raw)))
                self.send_response(200);self.send_header("Content-Type","application/json");self.end_headers()
                self.wfile.write(b'{"ok":true}')
        server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        t=Thread(target=server.serve_forever,daemon=True);t.start()
        try:
            client=install.GitHub("synthetic-token")
            original=client.opener
            def local(req,timeout):
                return original.open(Request("http://127.0.0.1:"+str(server.server_port)+"/fixture",data=req.data,headers=dict(req.header_items()),method=req.method),timeout=timeout)
            with patch.object(client,"opener",type("Adapter",(),{"open":staticmethod(local)})()):
                self.assertEqual(client.request("POST","/repos/example/product/git/trees",{"value":"\u03b1"}),{"ok":True})
            self.assertEqual(seen,[("/fixture","Bearer synthetic-token",{"value":"\u03b1"})])
        finally:server.shutdown();server.server_close();t.join(5)
    def status(self,status,method):
        client=install.GitHub("synthetic-token")
        error=HTTPError("https://example.invalid",status,"fixture",{},io.BytesIO(b"synthetic body"))
        with patch.object(client.opener,"open",side_effect=error) as op,patch.object(install.time,"sleep"):
            with self.assertRaises(install.ApiError) as exc:client.request(method,"/repos/example/product/git/refs",{"test":1} if method!="GET" else None)
            self.assertEqual(exc.exception.status,status)
            self.assertNotIn("synthetic-token",str(exc.exception))
            self.assertEqual(op.call_count,3 if method=="GET" and status in (500,502,503,504) else 1)
    def test_redirect_policy(self):
        self.assertIsNone(install.NoRedirect().redirect_request(None,None,302,"",{},"https://example.invalid"))
    def test_wire_json_duplicate(self):
        client=install.GitHub(None)
        response=io.BytesIO(b'{"merged":true,"merged":false}')
        with patch.object(client.opener,"open",return_value=response):
            with self.assertRaises(ValueError):client.request("GET","/repos/example/product/pulls/1")
    def test_wire_malformed(self):
        client=install.GitHub(None)
        with patch.object(client.opener,"open",return_value=io.BytesIO(b'{"x":')):
            with self.assertRaises(ValueError):client.request("GET","/repos/example/product")
    def test_owner_denial(self):
        fixture=f.load("install");api=fixture.FakeGitHub()
        # A collision must not be bypassed even by apply.
        api.refs[install.BRANCH]=fixture.INSTALLED
        with self.assertRaises(ValueError):install.install(api,fixture.TARGET,fixture.PIN,"v1.0.6",True)
        self.assertEqual(api.writes,[])

class B12(unittest.TestCase):
    def test_hardlink_replacement(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"state";link=Path(d)/"alias"
            checkpoint.write_json(p,{"x":1});os.link(p,link)
            checkpoint.write_json(p,{"x":2})
            self.assertEqual(json.loads(link.read_bytes()),{"x":1})
            self.assertEqual(json.loads(p.read_bytes()),{"x":2})
    def test_parent_missing(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"missing"/"state"
            with self.assertRaises(OSError):checkpoint.write_json(p,{"x":1})
            self.assertFalse(p.exists())
    def test_directory_target(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"state";p.mkdir();(p/"keep").write_bytes(b"keep")
            with self.assertRaises(OSError):checkpoint.write_json(p,{"x":1})
            self.assertEqual((p/"keep").read_bytes(),b"keep")
            self.assertEqual(list(Path(d).iterdir()),[p])

class B13(unittest.TestCase): pass

class B14(unittest.TestCase):
    def history(self,sha):
        self.assertEqual(c.git(P,"cat-file","-t",sha).strip(),b"commit")
        subprocess.run(["git","-C",str(P),"merge-base","--is-ancestor",sha,c.PIN],check=True,timeout=20)
        mapping=install.pinned_package(c.git(P,"show",sha+":tools/install.py").decode())
        for src,dst in mapping.items():
            raw=c.git(P,"show",sha+":"+src)
            self.assertEqual(lifecycle.blob_id(raw.decode()),c.git(P,"rev-parse",sha+":"+src).decode().strip())
        self.assertEqual(len(mapping),len(set(mapping.values())))
    def test_parent(self):self.history("e28e8a2e7360baf840c40dacf12ab91d5d7abd63")
    def test_grandparent(self):self.history("44573ae95e143116caacd891c842065a6d32743f")
    def test_current(self):self.history(c.PIN)

class B15(unittest.TestCase):
    def growth(self,n):
        x=ledger();start=time.monotonic()
        for issue in range(1,n+1):
            self.assertEqual(checkpoint.register(x,issue,"v0.0.0",["verify"]),("v0.0.0."+str(issue),True))
        self.assertEqual(len(checkpoint.bindings(x)),n)
        elapsed=time.monotonic()-start
        print("VIB_GROWTH "+json.dumps({"records":n,"seconds":elapsed}),flush=True)
        self.assertLess(elapsed,90)
    def test_growth_250(self):self.growth(250)
    def test_growth_1000(self):self.growth(1000)
    def termination(self,after):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/"state.json";checkpoint.write_json(p,{"x":1})
            code="""from pathlib import Path
import sys,time
from tools import checkpoint
root=Path(sys.argv[1])
if sys.argv[2]=='after': checkpoint.write_json(root/'state.json',{'x':2})
(root/'ready').touch()
time.sleep(60)
"""
            env=dict(os.environ,PYTHONPATH=str(P),PYTHONDONTWRITEBYTECODE="1")
            proc=subprocess.Popen([sys.executable,"-B","-c",code,str(root),"after" if after else "before"],env=env)
            try:
                deadline=time.monotonic()+15
                while not (root/"ready").exists():
                    if proc.poll() is not None or time.monotonic()>deadline:self.fail("child failed before barrier")
                    time.sleep(.02)
                proc.kill();proc.wait(timeout=10)
                self.assertNotEqual(proc.returncode,0)
                self.assertEqual(json.loads(p.read_bytes()),{"x":2 if after else 1})
                checkpoint.write_json(p,{"x":3});self.assertEqual(json.loads(p.read_bytes()),{"x":3})
            finally:
                if proc.poll() is None:proc.kill();proc.wait(timeout=10)
    def test_kill_before(self):self.termination(False)
    def test_kill_after(self):self.termination(True)

class B16(unittest.TestCase):
    def test_frozen_vectors(self):
        vectors=json.loads((HERE/"vectors.json").read_text(encoding="utf-8"))
        for v in vectors:
            raw=bytes.fromhex(v["hex"])
            self.assertEqual(lifecycle.blob_id(raw.decode()),v["git"])
            self.assertEqual(lifecycle.digest_files({"x":raw.decode()})["x"],v["sha256"])

def bind(cls,name,fn,*args):
    def case(self):fn(self,*args)
    setattr(cls,"test_"+name,case)
for bits in itertools.product((False,True),repeat=5):
    bind(B08,"matrix_"+''.join(str(int(b)) for b in bits),B08.matrix,*bits)
for order in itertools.permutations(("candidate","evidence","audit")):
    bind(B08,"sequence_"+'_'.join(order),B08.sequence,order)
for seed in (7,9,42,54,1024,2026,20261125,99991):bind(B09,"seed_"+str(seed),B09.corpus,seed)
for status in (401,403,404,422,429,500,502,503,504):
    for method in ("GET","POST"):bind(B11,method.lower()+"_"+str(status),B11.status,status,method)
for name,module,fn,old,new,cls,test in [
    ("schema_version",checkpoint,"bindings",'or type(ledger["schema_version"]) is not int or ledger["schema_version"] != 1','or False',B09,"test_schema_boolean"),
    ("duplicate_json",checkpoint,"unique_keys",'if key in result:','if False:',B09,"test_duplicate_escaped_key"),
    ("archive_digest",sys.modules["archive"],"inspect_zip",'if hashlib.sha256(raw).hexdigest()!=digest:','if False:',B10,"test_wrong_archive_digest"),
    ("archive_inventory",sys.modules["archive"],"inspect_zip",'if set(result)!=expected:','if False:',B10,"test_missing"),
]:
    setattr(B13,"test_"+name,mutation_case(module,fn,old,new,cls,test))

def main():
    batch=sys.argv[1]
    cls=globals()["B"+batch]
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(cls)
    expected=json.loads((HERE/"catalog.json").read_text(encoding="utf-8"))[batch]
    actual=[x.id().split(".",1)[1] for x in flatten(suite)]
    if sorted(actual)!=expected or len(set(actual))!=len(actual):raise RuntimeError("Frozen inventory mismatch")
    stream=io.StringIO()
    result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
    log=stream.getvalue().encode("utf-8")
    print(stream.getvalue(),flush=True)
    passed=sorted(x.split(".",1)[1] for x in result.passed)
    out=Path(os.environ["RUNNER_TEMP"])/"vib-advanced";out.mkdir(exist_ok=True)
    (out/(batch+".log")).write_bytes(log)
    report={"log_sha256":hashlib.sha256(log).hexdigest(),"batch":batch,"vault_sha":os.environ["GITHUB_SHA"],"product_sha":c.PIN,"run":os.environ["GITHUB_RUN_ID"],"attempt":os.environ["GITHUB_RUN_ATTEMPT"],"expected":expected,"passed":passed,"failures":[x.id().split(".",1)[1] for x,_ in result.failures],"errors":[x.id().split(".",1)[1] for x,_ in result.errors],"skipped":[x.id().split(".",1)[1] for x,_ in result.skipped],"outcome":"pass" if verdict(expected,passed,result.testsRun,result.wasSuccessful()) else "fail"}
    (out/(batch+".json")).write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("VIB_ADVANCED "+json.dumps(report),flush=True)
    raise SystemExit(0 if report["outcome"]=="pass" else 1)
if __name__=="__main__":main()
