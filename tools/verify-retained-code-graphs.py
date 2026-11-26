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
# Source-reviewed view is derived independently; original raw graphs are untouched.
overlay=read(archive/"cumulative-code-graphs/inferred-review-v0.0.0.36.json")
assert sha(archive/"cumulative-code-graphs/inferred-review-v0.0.0.36.json")=="c737ba73081449f48e60293f52c29a1b8165ce60d66158a50e8a20b8ceea689a"
original=read(archive/"code-graphs/v0.0.0.36/graph.json")
cumulative=read(archive/"cumulative-code-graphs/v0.0.0.36/graph.json")
assert overlay["source"]==original["built_at_commit"] and overlay["graph_sha256"]==old["results"][-1]["graph_sha256"]
assert {k:v for k,v in original.items() if k!="built_at_commit"}=={k:v for k,v in cumulative.items() if k!="built_at_commit"}
def edge(e):return (e["source"],e["target"],e["relation"],e["source_file"],e["source_location"])
def reviewed(e):return (e["source"],e["target"],e["relation"],e["source_file"],"L"+str(e["line"]))
decisions={reviewed(e):e for e in overlay["relationships"]}
inferred={edge(e) for e in original["links"] if e["confidence"]=="INFERRED"}
assert len(decisions)==len(inferred)==51 and set(decisions)==inferred
rejected={k for k,e in decisions.items() if e["verdict"].startswith("rejected_")}
assert len(rejected)==16
result={**cumulative,"links":[e for e in cumulative["links"] if not (e.get("confidence")=="INFERRED" and edge(e) in rejected)]}
assert len(result["links"])==1212
out=Path(os.environ["RUNNER_TEMP"])/"retained-graph-audit";out.mkdir(exist_ok=True)
(out/"v0.0.0.36-reviewed-graph.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
report={"status":"pass","historical_graphs":36,"cumulative_graphs":36,"native_positive":144,"native_negative":10,"inferred_reviewed":51,"false_inferred_removed":16,"reviewed_graph_edges":1212,"raw_graphs_preserved":True,"reviewed_source":cumulative["built_at_commit"],"reviewed_graph_sha256":sha(out/"v0.0.0.36-reviewed-graph.json"),"run":os.environ["GITHUB_RUN_ID"],"attempt":os.environ["GITHUB_RUN_ATTEMPT"],"checkout":git("rev-parse","HEAD")}
(out/"report.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report))
