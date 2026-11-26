"""Batch 17: replay historical vault in scratch against independently pinned repaired candidate."""
import hashlib,json,os,re,shutil,subprocess,sys,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
VAULT=HERE.parents[1]
PRODUCT=Path(os.environ["VIB_CHECKOUT"]).resolve()
PIN="5a6074d77ec37823f81c6d7ebb1f4593d969cd71"
OLD="7ae6626e44d01d29b11968da28e6debd816f8c06"
ROOT=Path(os.environ["RUNNER_TEMP"])/"batch17"
SCRATCH=ROOT/"scratch"
EVIDENCE=ROOT/"evidence"
def require(ok,msg):
    if not ok:raise RuntimeError(msg)
def head(p):return subprocess.check_output(["git","-C",str(p),"rev-parse","HEAD"],text=True).strip()
def clean(p):return not subprocess.check_output(["git","-C",str(p),"status","--porcelain","--untracked-files=all"])
def dump(p,v):p.write_text(json.dumps(v,indent=2)+"\n",encoding="utf-8")
def load(p):return json.loads(p.read_text(encoding="utf-8"))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def baseline():
    sys.path.insert(0,str(PRODUCT))
    sys.path.insert(0,str(SCRATCH/"vib/issue54"))
    from record import Result,flatten,verdict
    expected=sorted(x for v in load(HERE/"baseline.json").values() for x in v)
    suite=unittest.defaultTestLoader.discover(str(PRODUCT/"tests"))
    actual=sorted(t.id() for t in flatten(suite))
    require(actual==expected,"Original test inventory changed")
    result=unittest.TextTestRunner(verbosity=2,resultclass=Result).run(suite)
    dump(ROOT/"baseline-result.json",{"passed":sorted(result.passed),"expected":expected,"tests_run":result.testsRun})
    raise SystemExit(0 if verdict(expected,result.passed,result.testsRun,result.wasSuccessful()) else 1)
def main():
    require(head(VAULT)==os.environ["GITHUB_SHA"] and head(PRODUCT)==PIN,"Wrong exact checkout")
    require(clean(VAULT) and clean(PRODUCT),"Dirty input checkout")
    require(not ROOT.exists(),"Reused scratch")
    EVIDENCE.mkdir(parents=True)
    shutil.copytree(VAULT/"vib",SCRATCH/"vib")
    overlay=[]
    def edit(relative,old,new):
        p=SCRATCH/"vib"/relative
        before=digest(p);src=p.read_text(encoding="utf-8")
        require(src.count(old)==1,"Overlay anchor drift: "+relative)
        p.write_text(src.replace(old,new,1),encoding="utf-8")
        overlay.append({"path":relative,"original_sha256":before,"adapted_sha256":digest(p),"old":old,"new":new})
    edit("issue54/test_core.py",OLD,PIN)
    edit("issue54/audit_evidence.py",OLD,PIN)
    edit("issue54/diagnostic.py","len(expected) != 13","len(expected) != 15")
    # Artifact control's expected platform count stays historical: inventory self-test is unchanged.
    dump(EVIDENCE/"overlay.json",overlay)
    rc=ROOT/"coverage.ini"
    rc.write_text("[run]\nbranch = True\nparallel = True\npatch = subprocess\nsource =\n    "+str(PRODUCT/"tools")+"\ndata_file = "+str(ROOT/".coverage")+"\n",encoding="utf-8")
    env=dict(os.environ,RUNNER_TEMP=str(ROOT),COVERAGE_RCFILE=str(rc),PYTHONDONTWRITEBYTECODE="1",PYTHONUTF8="1",GH_TOKEN="",GITHUB_TOKEN="")
    py=[sys.executable,"-m","coverage","run","--rcfile="+str(rc)]
    rows=[]
    def run(kind,cmd,expected,read_ids):
        log=EVIDENCE/(kind+".log")
        try:
            proc=subprocess.run(cmd,cwd=PRODUCT,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=360)
            log.write_bytes(proc.stdout);code=proc.returncode
        except subprocess.TimeoutExpired as exc:
            log.write_bytes(exc.stdout or b"");code=124
        raw=log.read_text(encoding="utf-8",errors="replace")
        try:ids=read_ids(raw)
        except (OSError,ValueError,KeyError) as exc:
            ids=[];print("Identity read failed",kind,str(exc),flush=True)
        expected=sorted(expected);ids=sorted(ids)
        valid=len(set(ids))==len(ids) and set(ids).issubset(expected)
        row={"kind":kind,"expected":expected,"passed":ids,"missing":sorted(set(expected)-set(ids)),"exit_code":code,"log_sha256":digest(log),"outcome":"pass" if valid and ids==expected and code==0 else "fail","identity_valid":valid}
        dump(EVIDENCE/(kind+".json"),row);rows.append(row)
        print("BATCH17 "+json.dumps({"kind":kind,"passed":len(ids),"expected":len(expected),"outcome":row["outcome"],"missing":row["missing"],"exit_code":code}),flush=True)
    core=load(HERE/"core.json");baseline_ids=[x for v in load(HERE/"baseline.json").values() for x in v]
    run("baseline",py+[str(__file__),"baseline"],baseline_ids,lambda _:load(ROOT/"baseline-result.json")["passed"])
    sources={"python":"test_core.py","diagnostic":"diagnostic.py","faults":"test_faults.py","evidence":"test_evidence.py","schema":"test_schema.py","mutation":"test_mutation.py","receipt":"test_receipt.py","completion":"test_completion.py","ancestry":"test_ancestry.py","partial":"test_partial_metadata.py","interruptions":"test_interruptions.py","artifact":"test_artifact.py","traces":"test_traces.py","qualification":"test_qualification.py","high":"test_high.py"}
    for kind,filename in sources.items():
        read=(lambda raw:re.findall(r"^test_[^\s]+ \(([^)]*)\) \.\.\. ok",raw,re.M)) if kind=="python" else (lambda raw,k=kind:load(ROOT/"issue54"/(k+"-identities.json")))
        run(kind,py+[str(SCRATCH/"vib/issue54"/filename)],core[kind],read)
    # Run historical shell controls unchanged; use independent frozen identities.
    iswin=os.environ["RUNNER_OS"]=="Windows"
    prefix="powershell" if iswin else "bash"
    suffix=".ps1" if iswin else ".sh"
    shell=["pwsh","-NoProfile","-File"] if iswin else ["bash"]
    for i,name in enumerate(("core","platform","attrs","history","paths","transactions","races"),1):
        kind=prefix+("" if i==1 else str(i))
        run(kind,shell+[str(SCRATCH/"vib/issue54"/(name+suffix))],core[kind],lambda raw:re.findall(r"^PASS ((?:BA|PS)\d*-\S+)",raw,re.M))
    cat=load(SCRATCH/"vib/advanced/catalog.json")
    for batch in sorted(cat):
        run("advanced-"+batch,py+[str(SCRATCH/"vib/advanced/qualify.py"),batch],cat[batch],lambda raw,b=batch:load(ROOT/"vib-advanced"/(b+".json"))["passed"])
    ps="PS" if iswin else "BA"
    names=["12-worktree","12-isolation"]+(["12-junction","12-lock"] if iswin else ["12-shallow","12-symlink"])+["16-git","16-digest","16-empty-git","16-empty-digest"]
    run("advanced-platform",shell+[str(SCRATCH/"vib/advanced"/("platform"+suffix))],[ps+x for x in names],lambda raw:re.findall(r"^PASS ((?:BA|PS)\d+-\S+)",raw,re.M))
    data=list(ROOT.glob(".coverage.*"))
    require(len(data)>1,"Missing parallel coverage data")
    subprocess.run([sys.executable,"-m","coverage","combine","--keep"],cwd=PRODUCT,env=env,check=True,timeout=120)
    subprocess.run([sys.executable,"-m","coverage","json","-o",str(EVIDENCE/"coverage.json")],cwd=PRODUCT,env=env,check=True,timeout=120)
    cov=load(EVIDENCE/"coverage.json")
    require(cov["meta"]["branch_coverage"] and cov["files"],"Missing branch coverage")
    require(head(VAULT)==os.environ["GITHUB_SHA"] and head(PRODUCT)==PIN and clean(VAULT) and clean(PRODUCT),"Checkout drift")
    for row in rows:
        require(digest(EVIDENCE/(row["kind"]+".log"))==row["log_sha256"],"Log digest")
    report={"vault_sha":head(VAULT),"product_sha":PIN,"historical_product":OLD,"run":os.environ["GITHUB_RUN_ID"],"attempt":os.environ["GITHUB_RUN_ATTEMPT"],"os":os.environ["RUNNER_OS"],"expected":sum(len(r["expected"]) for r in rows),"passed":sum(len(r["passed"]) for r in rows),"suites":[{"kind":r["kind"],"expected":len(r["expected"]),"passed":len(r["passed"]),"outcome":r["outcome"],"missing":r["missing"]} for r in rows],"coverage":cov["totals"],"parallel_data_files":len(data),"coverage_scope":"Python parent and normally exiting subprocesses; forcibly killed process data may be lost","integrity":"verified" if all(r["identity_valid"] for r in rows) else "invalid"}
    dump(EVIDENCE/"summary.json",report);print("BATCH17_SUMMARY "+json.dumps(report),flush=True)
    raise SystemExit(0 if all(r["outcome"]=="pass" for r in rows) else 1)
if __name__=="__main__":
    if len(sys.argv)>1 and sys.argv[1]=="baseline":baseline()
    else:main()
