import json,hashlib,os,shutil,subprocess
from pathlib import Path
root=Path.cwd()
origin=Path(os.environ["RUNNER_TEMP"])/"graphs"
ix=json.loads((origin/"index.json").read_text())
assert not ix["failures"] and len(ix["results"])==36
for i,r in enumerate(ix["results"],1):
    assert r["version"]==f"v0.0.0.{i}" and r["source_kind"]=="reconstructed_cumulative_engineering_prefix"
    p=origin/r["version"]
    assert json.loads((p/"receipt.json").read_text())==r
    raw=(p/"graph.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest()==r["graph_sha256"]
    assert json.loads(raw)["built_at_commit"]==r["source"]
target=root/"archives/cumulative-code-graphs"
assert not target.exists()
shutil.copytree(origin,target)
assert all(p.read_bytes()==(target/p.relative_to(origin)).read_bytes() for p in origin.rglob("*") if p.is_file())
subprocess.run(["python3","tools/test-code-graph-retrieval.py"],check=True)
