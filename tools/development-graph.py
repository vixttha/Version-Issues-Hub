"""VIB development graph intake; never executes project source or promotes final archives."""
import hashlib, importlib.metadata, json, os, re, shutil, subprocess, sys
from pathlib import Path
ROOT=Path.cwd()
REQ=json.loads((ROOT/"development-graph-request.json").read_text(encoding="utf-8"))
REPO="vixttha/Version-Issues-Hub"
SHA=re.compile(r"[0-9a-f]{40}")
VERSION=re.compile(r"v0\.0\.0\.[1-9][0-9]{0,8}")
assert set(REQ)=={"repository","version","issue","branch","source","tree","canonical"}
assert REQ["repository"]==REPO and VERSION.fullmatch(REQ["version"])
assert type(REQ["issue"]) is int and REQ["issue"]>0
assert REQ["branch"]=="plan/checkpoint-"+REQ["version"]
assert all(SHA.fullmatch(REQ[k]) for k in ("source","tree","canonical"))
REL=Path("development-code-graphs")/REQ["version"]/REQ["source"]
DEST=ROOT/"archives"/REL
OUT=Path(os.environ["RUNNER_TEMP"])/"development-snapshot"
def git(repo,*args):
    return subprocess.check_output(["git","-C",str(repo),*args],text=True).strip()
def read(path):
    return json.loads(path.read_bytes())
def dump(path,data):
    path.write_bytes((json.dumps(data,indent=2,ensure_ascii=True)+"\n").encode())
def validate(folder, current_run=False):
    assert folder.is_dir() and not folder.is_symlink()
    assert {p.name for p in folder.iterdir()}=={"graph.json","receipt.json"}
    assert all(p.is_file() and not p.is_symlink() for p in folder.iterdir())
    r=read(folder/"receipt.json")
    assert all(r[k]==v for k,v in REQ.items())
    assert r["schema"]==1 and r["source_kind"]=="development_snapshot"
    assert r["finalized"] is False and r["production_integrated"] is False and r["historical_test_claim"] is False
    assert r["graphify_version"]=="0.9.109" and r["mode"]=="code-only AST"
    assert all(isinstance(r[k],str) and re.fullmatch("[1-9][0-9]*",r[k]) for k in ("run","attempt"))
    if current_run:
        assert r["run"]==os.environ["GITHUB_RUN_ID"] and r["attempt"]==os.environ["GITHUB_RUN_ATTEMPT"]
    raw=(folder/"graph.json").read_bytes()
    assert 0<len(raw)<=8*1024*1024 and hashlib.sha256(raw).hexdigest()==r["graph_sha256"]
    g=json.loads(raw)
    ids={n["id"] for n in g["nodes"]}
    assert all(isinstance(i,str) and i for i in ids)
    assert g["built_at_commit"]==r["source"] and len(ids)==len(g["nodes"])==r["nodes"]>0
    assert len(g["links"])==r["edges"] and all(e["source"] in ids and e["target"] in ids for e in g["links"])
    return r
def native(archive,r,command,good=True):
    p=subprocess.run(["node","veraphifiy.mjs",command,"--archive",str(archive),"--project",r["repository"],"--version",r["version"],"--scope","development","--source",r["source"],"--graph-sha256",r["graph_sha256"]],capture_output=True,text=True,encoding="utf-8")
    assert (p.returncode==0)==good,p.stderr
    return json.loads(p.stdout) if good else None
def replay(folder):
    import tempfile
    r=validate(folder)
    with tempfile.TemporaryDirectory() as temp:
        archive=Path(temp); dest=archive/REL
        dest.parent.mkdir(parents=True); shutil.copytree(folder,dest)
        assert native(archive,r,"code-verify")==r
        assert native(archive,r,"code-graph")=={"receipt":r,"graph":read(dest/"graph.json")}
        for k,v in [("source","0"*40),("graph_sha256","0"*64),("repository","other/repo"),("version","v0.0.0.999999999")]:
            native(archive,{**r,k:v},"code-verify",False)
        raw=dest/"graph.json"; saved=raw.read_bytes(); raw.write_bytes(saved+b" ")
        native(archive,r,"code-verify",False); raw.write_bytes(saved)
        receipt=dest/"receipt.json"; original=receipt.read_bytes()
        dump(receipt,{**r,"finalized":True}); native(archive,r,"code-verify",False)
        receipt.write_bytes(original)
    print("Verified development graph",r["source"],r["nodes"],r["edges"],r["graph_sha256"],flush=True)
def build():
    workspace=Path(os.environ["GITHUB_WORKSPACE"])
    source=workspace/"source"; canonical=workspace/"canonical"
    assert git(source,"rev-parse","HEAD")==REQ["source"]
    assert git(source,"rev-parse","HEAD^{tree}")==REQ["tree"]
    assert git(canonical,"rev-parse","HEAD")==REQ["canonical"]
    worker=read(source/"ledger/self-use-worker.json")
    assert worker["issue"]==REQ["issue"] and worker["version"]==REQ["version"] and worker["installed_sha"]==REQ["canonical"]
    ledger=read(canonical/"ledger/issue-versions.json")
    assert ledger["repository"]==REPO
    matches=[r for r in ledger["issues"] if r["issue"]==REQ["issue"] or r["version"]==REQ["version"]]
    assert len(matches)==1 and matches[0]["issue"]==REQ["issue"] and matches[0]["version"]==REQ["version"] and matches[0]["state"]=="in_progress"
    active=read(canonical/"ledger/handoff.json")["active"]
    assert active["issue"]==REQ["issue"] and active["version"]==REQ["version"]
    assert importlib.metadata.version("graphifyy")=="0.9.109"
    assert not (source/"graphify-out").exists()
    subprocess.run(["graphify","extract",".","--code-only"],cwd=source,check=True,timeout=240)
    OUT.mkdir()
    shutil.copyfile(source/"graphify-out/graph.json",OUT/"graph.json")
    g=read(OUT/"graph.json")
    r={**REQ,"schema":1,"source_kind":"development_snapshot","finalized":False,"production_integrated":False,"historical_test_claim":False,"graphify_version":"0.9.109","mode":"code-only AST","nodes":len(g["nodes"]),"edges":len(g["links"]),"graph_sha256":hashlib.sha256((OUT/"graph.json").read_bytes()).hexdigest(),"run":os.environ["GITHUB_RUN_ID"],"attempt":os.environ["GITHUB_RUN_ATTEMPT"]}
    dump(OUT/"receipt.json",r); validate(OUT,True)
def retain():
    validate(OUT,True); replay(OUT)
    if DEST.exists() or DEST.is_symlink():
        raise ValueError("Existing snapshot: use replay, never overwrite")
    for parent in (DEST.parent,DEST.parent.parent,DEST.parent.parent.parent):
        if parent.is_symlink(): raise ValueError("Invalid archive parent")
    DEST.parent.mkdir(parents=True,exist_ok=True); shutil.copytree(OUT,DEST)
    assert validate(DEST,True)==validate(OUT,True)
    assert (DEST/"graph.json").read_bytes()==(OUT/"graph.json").read_bytes()
    replay(DEST)
if __name__=="__main__":
    {"build":build,"verify":lambda:replay(OUT),"retain":retain,"existing":lambda:replay(DEST)}[sys.argv[1]]()
