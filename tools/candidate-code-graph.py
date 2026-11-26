"""Build an immutable raw candidate graph and query its recovery/evidence relationships.
No execution of VIB source, no semantic model, no changes to historical snapshots."""
import hashlib, importlib.metadata, json, os, shutil, subprocess, sys
from pathlib import Path

SOURCE = os.environ["VIB_SOURCE"]
VERSION = "v0.0.0.37"
REPO = "vixttha/Version-Issues-Hub"
TEMP = Path(os.environ["RUNNER_TEMP"])
def read(p): return json.loads(p.read_bytes())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,obj): p.write_bytes((json.dumps(obj, indent=2, ensure_ascii=True)+"\n").encode())
def git(repo,*args): return subprocess.check_output(["git",*args],cwd=repo,text=True).strip()
def native(vault, archive, receipt, command, good=True):
    args=["node",str(vault/"veraphifiy.mjs"),command,"--archive",str(archive),"--project",REPO,"--scope","candidate","--version",VERSION,"--source",SOURCE,"--graph-sha256",receipt["graph_sha256"] if good else "0"*64]
    p=subprocess.run(args,capture_output=True,text=True)
    if good:
        p.check_returncode()
        return json.loads(p.stdout)
    assert p.returncode!=0
def validate(folder):
    r=read(folder/"receipt.json"); g=read(folder/"graph.json")
    assert r["source"]==SOURCE and r["version"]==VERSION and r["issue"]==53
    assert r["source_kind"]=="unmerged_engineering_candidate" and r["historical_test_claim"] is False
    assert r["graph_sha256"]==sha(folder/"graph.json") and r["query_sha256"]==sha(folder/"debug-relationships.json")
    ids={n["id"] for n in g["nodes"]}
    assert g["built_at_commit"]==SOURCE and len(ids)==len(g["nodes"])==r["nodes"] and len(g["links"])==r["edges"]
    assert all(e["source"] in ids and e["target"] in ids for e in g["links"])
    return r,g
def build():
    root=Path.cwd(); repo=root/"vib"; vault=root/"veraphify"
    assert git(repo,"rev-parse","HEAD")==SOURCE
    assert importlib.metadata.version("graphifyy")=="0.9.109"
    subprocess.run(["graphify","extract",".","--code-only"],cwd=repo,check=True,timeout=180)
    graph=repo/"graphify-out/graph.json"
    dest=TEMP/"vib-candidate-archive"/"candidate-code-graphs"/VERSION/SOURCE
    dest.mkdir(parents=True)
    shutil.copyfile(graph,dest/"graph.json")
    g=read(graph); nodes={n["id"]:n for n in g["nodes"]}
    focus={"recover_save","retry_scope","save","inspect_pending","inspect_operation","verify_candidate_runs","confirm_handoff","check_issue_delta","persist_pending_intent","persist_recovery_ticket"}
    chosen={n["id"] for n in nodes.values() if n.get("source_file")=="tools/session.py" and n["label"].strip(".").removesuffix("()") in focus}
    assert chosen, "No recovery functions in graph"
    edges=[e for e in g["links"] if e["source"] in chosen or e["target"] in chosen]
    neighbors={e[k] for e in edges for k in ("source","target")}
    report={"source":SOURCE,"scope":"direct adjacency, not runtime proof","focus_nodes":[nodes[n] for n in sorted(chosen)],"neighbor_nodes":[nodes[n] for n in sorted(neighbors)],"relationships":edges,"inferred_edges":sum(e.get("confidence")=="INFERRED" for e in edges)}
    write(dest/"debug-relationships.json",report)
    receipt={"repository":REPO,"version":VERSION,"issue":53,"source":SOURCE,"tree":git(repo,"rev-parse","HEAD^{tree}"),"source_kind":"unmerged_engineering_candidate","historical_test_claim":False,"graphify_version":"0.9.109","mode":"code-only AST","nodes":len(nodes),"edges":len(g["links"]),"graph_sha256":sha(dest/"graph.json"),"query_sha256":sha(dest/"debug-relationships.json"),"run":os.environ["GITHUB_RUN_ID"],"attempt":os.environ["GITHUB_RUN_ATTEMPT"]}
    write(dest/"receipt.json",receipt)
    validate(dest)
    assert native(vault,TEMP/"vib-candidate-archive",receipt,"code-graph")=={"receipt":receipt,"graph":g}
    native(vault,TEMP/"vib-candidate-archive",receipt,"code-verify",False)
    print("VIB37_GRAPH",json.dumps({**receipt,"focus_nodes":len(chosen),"adjacent_edges":len(edges),"inferred_edges":report["inferred_edges"]}),flush=True)
def preserve():
    root=Path.cwd()
    relative=Path("candidate-code-graphs")/VERSION/SOURCE
    origin=TEMP/"current"/relative
    receipt,g=validate(origin)
    assert str(receipt["run"])==os.environ["GITHUB_RUN_ID"] and str(receipt["attempt"])==os.environ["GITHUB_RUN_ATTEMPT"]
    assert native(root,TEMP/"current",receipt,"code-graph")=={"receipt":receipt,"graph":g}
    target=root/"archives"/relative
    files={"receipt.json","graph.json","debug-relationships.json"}
    assert {p.name for p in origin.iterdir()}==files
    if target.exists():
        # A repeated run for this immutable source may differ in run metadata.
        prior,_=validate(target)
        assert prior["tree"]==receipt["tree"] and prior["graph_sha256"]==receipt["graph_sha256"] and prior["query_sha256"]==receipt["query_sha256"]
    else:
        shutil.copytree(origin,target)
    retained,_=validate(target)
    assert native(root,root/"archives",retained,"code-verify")==retained
    print("VIB37_RETAINED",json.dumps(retained),flush=True)
if __name__=="__main__":
    {"build":build,"preserve":preserve}[sys.argv[1]]()
