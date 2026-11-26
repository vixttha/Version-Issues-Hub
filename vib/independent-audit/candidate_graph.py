"""Candidate graph readback with independent Git tree, digest, native CLI and negative probes."""
import hashlib,json,os,subprocess,tempfile,shutil
from pathlib import Path
root=Path(os.environ["GITHUB_WORKSPACE"]);repo=root/"archive";arc=repo/"archives";out=Path(os.environ["RUNNER_TEMP"])/"independent-vib-audit"
s="b68796db12681fe4d43b562c8647deca38fa819c";p=arc/"candidate-code-graphs/v0.0.0.37"/s;r=json.loads((p/"receipt.json").read_bytes());raw=(p/"graph.json").read_bytes()
assert r["source"]==s and r["source_kind"]=="unmerged_engineering_candidate" and r["historical_test_claim"] is False
assert hashlib.sha256(raw).hexdigest()==r["graph_sha256"]
assert subprocess.check_output(["git","rev-parse",s+"^{tree}"],cwd=root/"candidate").decode().strip()==r["tree"]
assert hashlib.sha256((p/"debug-relationships.json").read_bytes()).hexdigest()==r["query_sha256"]
def invoke(archive,source=s,digest=r["graph_sha256"]):
    return subprocess.run(["node","veraphifiy.mjs","code-graph","--archive",str(archive),"--project","vixttha/Version-Issues-Hub","--version","v0.0.0.37","--scope","candidate","--source",source,"--graph-sha256",digest],cwd=repo,capture_output=True)
q=invoke(arc);assert q.returncode==0,q.stderr
assert json.loads(q.stdout)=={"receipt":r,"graph":json.loads(raw)}
assert invoke(arc,digest="0"*64).returncode!=0
assert invoke(arc,source="0"*40).returncode!=0
with tempfile.TemporaryDirectory() as tmp:
    d=Path(tmp)/p.relative_to(arc);shutil.copytree(p,d)
    (d/"graph.json").write_bytes(raw+b"\n")
    assert invoke(Path(tmp)).returncode!=0
    (d/"graph.json").write_bytes(raw)
    (d/"receipt.json").write_text(json.dumps({**r,"issue":54}),encoding="utf-8")
    assert invoke(Path(tmp)).returncode!=0
(out/"candidate-graph.json").write_bytes((json.dumps({"receipt":r,"native_reads":1,"negative_probes":4},indent=2)+"\n").encode())
print("Actual .37 candidate graph verified",r["nodes"],r["edges"])
