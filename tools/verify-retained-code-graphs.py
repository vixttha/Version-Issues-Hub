"""Independent retained archive verification; no product or ref writes."""
import hashlib,json,subprocess,sys,os
from pathlib import Path
root=Path.cwd()
archive=root/"archives"
def read(p):return json.loads(p.read_bytes())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(["git",*args],text=True).strip()
def ancestor(a,b):
    p=subprocess.run(["git","merge-base","--is-ancestor",a,b])
    assert p.returncode in (0,1)
    return p.returncode==0
old=read(archive/"code-graphs/index.json")
new=read(archive/"cumulative-code-graphs/index.json")
assert len(old["results"])==len(new["results"])==36 and not old["failures"] and not new["failures"]
# Git objects are fetched explicitly, not inferred from metadata.
for ref in ("26e9fe8c019a33c5f84f77a37da70925505204e3","a472e04f4c2cc781c654000d6c0567e703f32791","365a53437882e50d37a62b2940fab898b220ae9b"):
    subprocess.run(["git","fetch","--no-tags","origin",ref],check=True)
prev=None;prefix=set()
for i,(a,b) in enumerate(zip(old["results"],new["results"]),1):
    assert a["version"]==b["version"]==f"v0.0.0.{i}" and a["issue"]==b["issue"]
    if a["issue"]!=40:prefix.add(a["source"])
    assert b["original_fix_source"]==a["source"] and set(b["covered_fix_sources"])==prefix
    assert b["operational_exclusion"]==(i==23)
    assert all(ancestor(x,b["source"]) for x in prefix)
    if prev:assert ancestor(prev,b["source"])
    prev=b["source"]
    for scope,r in [("code-graphs",a),("cumulative-code-graphs",b)]:
        assert git("rev-parse",r["source"]+"^{tree}")==r["tree"]
        p=archive/scope/r["version"]
        assert read(p/"receipt.json")==r and sha(p/"graph.json")==r["graph_sha256"]
        graph=read(p/"graph.json");ids={x["id"] for x in graph["nodes"]}
        assert graph["built_at_commit"]==r["source"]
        assert len(ids)==len(graph["nodes"])==r["nodes"] and len(graph["links"])==r["edges"]
        assert all(e["source"] in ids and e["target"] in ids for e in graph["links"])
assert new["results"][-1]["source"]=="26e9fe8c019a33c5f84f77a37da70925505204e3"
assert old["results"][22]["source_kind"]=="operational_preflight_revision"
assert old["results"][25]["source"]==old["results"][26]["source"]==old["results"][27]["source"]
assert len({old["results"][i]["issue"] for i in (25,26,27)})==3
assert ancestor(old["results"][23]["source"],old["results"][21]["source"])
assert ancestor(old["results"][29]["source"],old["results"][28]["source"])
# Original archive blobs stay exactly the same.
assert git("diff","--name-only","365a53437882e50d37a62b2940fab898b220ae9b","HEAD","--","archives/code-graphs","archives/candidates","archives/README.md")==""
# Full native CLI reads and negative probes.
subprocess.run([sys.executable,"tools/test-code-graph-retrieval.py"],check=True)
# Old overlay is immutable historical evidence, superseded by fresh all-version audit.
assert sha(archive/"cumulative-code-graphs/inferred-review-v0.0.0.36.json")=="c737ba73081449f48e60293f52c29a1b8165ce60d66158a50e8a20b8ceea689a"
assert git("diff","--name-only","77071651bca0421361e15643d3ed68d8c32c9814","HEAD","--","archives/cumulative-code-graphs")==""
import importlib.util
spec=importlib.util.spec_from_file_location("audit",root/"tools/audit-inferred-graphs.py")
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
out=Path(os.environ["RUNNER_TEMP"])/"retained-graph-audit";out.mkdir(exist_ok=True)
result=audit.audit(root,archive,out/"source-review")
report={"status":"pass","historical_graphs":36,"cumulative_graphs":36,"native_positive":144,"native_negative":10,"scope_regressions":7,"inferred_total":result["inferred_total"],"counts":result["counts"],"raw_graphs_preserved":True,"review_index_sha256":sha(out/"source-review/index.json"),"run":os.environ["GITHUB_RUN_ID"],"attempt":os.environ["GITHUB_RUN_ATTEMPT"],"checkout":git("rev-parse","HEAD")}
(out/"report.json").write_bytes((json.dumps(report,indent=2)+"\n").encode("utf-8"))
print(json.dumps(report))
