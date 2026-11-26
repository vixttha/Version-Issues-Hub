"""Generate three exact engineering-merge AST graphs; verify and retain append-only.
No product source execution, semantic model, historical test replay or release claim."""
import hashlib, importlib.metadata, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path.cwd()
ROWS = json.loads((ROOT / "tools/engineering-graphs-40-42.json").read_bytes())
REPO = "vixttha/Version-Issues-Hub"
OUT = Path(os.environ["RUNNER_TEMP"]) / "engineering-code-graphs-40-42"
assert [r["version"] for r in ROWS] == [f"v0.0.0.{n}" for n in range(40,43)]
assert [r["issue"] for r in ROWS] == [86,92,94]
def read(path):
    return json.loads(path.read_bytes())
def dump(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=True)+"\n", encoding="utf-8")
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def git(repo, *args):
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()
def verify(folder, current_run=True):
    index=read(folder/"index.json")
    assert index["schema"]==1 and index["repository"]==REPO and not index["failures"]
    assert len(index["results"])==len(ROWS)
    assert {p.name for p in folder.iterdir()}=={"index.json", *[r["version"] for r in ROWS]}
    for row, r in zip(ROWS,index["results"]):
        path=folder/row["version"]
        assert {p.name for p in path.iterdir()}=={"receipt.json","graph.json"}
        assert read(path/"receipt.json")==r and all(r[k]==v for k,v in row.items())
        assert r["source_kind"]=="actual_engineering_merge" and r["production_integrated"] is False
        assert r["historical_test_claim"] is False and r["graphify_version"]=="0.9.109" and r["mode"]=="code-only AST"
        assert digest(path/"graph.json")==r["graph_sha256"]
        graph=read(path/"graph.json")
        ids={n["id"] for n in graph["nodes"]}
        assert graph["built_at_commit"]==r["source"]
        assert len(ids)==len(graph["nodes"])==r["nodes"]>0 and len(graph["links"])==r["edges"]
        assert all(e["source"] in ids and e["target"] in ids for e in graph["links"])
        assert all(isinstance(r[k],str) and r[k].isascii() and r[k].isdigit() and int(r[k])>0 for k in ("run","attempt"))
        if current_run:
            assert r["run"]==os.environ["GITHUB_RUN_ID"] and r["attempt"]==os.environ["GITHUB_RUN_ATTEMPT"]
    return index
def build():
    assert importlib.metadata.version("graphifyy")=="0.9.109"
    source=Path(os.environ["GITHUB_WORKSPACE"])/"source"
    OUT.mkdir()
    results=[]
    for row in ROWS:
        assert git(source,"rev-parse",row["source"])==row["source"]
        assert git(source,"rev-parse",row["source"]+"^{tree}")==row["tree"]
        assert git(source,"merge-base","--is-ancestor",row["source"],"HEAD")=="" 
        with tempfile.TemporaryDirectory() as tmp:
            work=Path(tmp)/"snapshot"
            git(source,"worktree","add","--detach",str(work),row["source"])
            try:
                assert git(work,"rev-parse","HEAD")==row["source"]
                subprocess.run(["graphify","extract",".","--code-only"],cwd=work,check=True,timeout=180)
                dest=OUT/row["version"]; dest.mkdir()
                shutil.copyfile(work/"graphify-out/graph.json",dest/"graph.json")
                g=read(dest/"graph.json")
                r={**row,"source_kind":"actual_engineering_merge","production_integrated":False,
                   "historical_test_claim":False,"graphify_version":"0.9.109","mode":"code-only AST",
                   "nodes":len(g["nodes"]),"edges":len(g["links"]),"graph_sha256":digest(dest/"graph.json"),
                   "run":os.environ["GITHUB_RUN_ID"],"attempt":os.environ["GITHUB_RUN_ATTEMPT"]}
                dump(dest/"receipt.json",r); results.append(r)
            finally:
                git(source,"worktree","remove","--force",str(work))
    dump(OUT/"index.json",{"schema":1,"repository":REPO,"results":results,"failures":[]})
    verify(OUT)
def native(archive, r, command, good=True):
    p=subprocess.run(["node","veraphifiy.mjs",command,"--archive",str(archive),"--project",REPO,
        "--version",r["version"],"--scope","engineering","--source",r["source"],"--graph-sha256",r["graph_sha256"]],
        capture_output=True,text=True)
    assert (p.returncode==0)==good,p.stderr
    return json.loads(p.stdout) if good else None
def retain():
    ix=verify(OUT)
    dest=ROOT/"archives/engineering-code-graphs-40-42"
    if dest.exists():
        raise ValueError("Refusing to overwrite an existing engineering archive")
    shutil.copytree(OUT,dest)
    assert verify(dest)==ix
    validate_native(dest,ix)
def validate_native(dest,ix):
    for r in ix["results"]:
        assert native(ROOT/"archives",r,"code-verify")==r
        assert native(ROOT/"archives",r,"code-graph")=={"receipt":r,"graph":read(dest/r["version"]/"graph.json")}
        native(ROOT/"archives",{**r,"source":"0"*40},"code-verify",False)
        native(ROOT/"archives",{**r,"graph_sha256":"0"*64},"code-verify",False)
        with tempfile.TemporaryDirectory() as tmp:
            bad=Path(tmp)/dest.name
            shutil.copytree(dest,bad)
            raw=bad/r["version"]/"graph.json"
            raw.write_bytes(raw.read_bytes()+b" ")
            native(Path(tmp),r,"code-verify",False)
        print(r["version"],r["source"],r["nodes"],r["edges"],r["graph_sha256"],flush=True)
    print("3 exact merge graphs; 6 positive and 9 negative native checks")
def validate_existing():
    dest=ROOT/"archives/engineering-code-graphs-40-42"
    validate_native(dest,verify(dest,current_run=False))
if __name__=="__main__":
    {"build":build,"retain":retain,"validate-existing":validate_existing}[sys.argv[1]]()
