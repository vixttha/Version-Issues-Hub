"""Verify downloaded raw Graphify version graphs, then preserve only on review branch."""
import hashlib,json,os
from pathlib import Path
import shutil
root=Path.cwd()
origin=Path(os.environ["RUNNER_TEMP"])/"graphs"
index=json.loads((origin/"index.json").read_text())
expected=json.loads((root/"tools/vib-code-graph-inventory.json").read_text())
assert not index["failures"] and len(index["results"])==36
for row,receipt in zip(expected,index["results"]):
    assert all(receipt[k]==v for k,v in row.items())
    folder=origin/row["version"]
    assert json.loads((folder/"receipt.json").read_text())==receipt
    raw=(folder/"graph.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest()==receipt["graph_sha256"]
    graph=json.loads(raw)
    assert len(graph["nodes"])==receipt["nodes"]>0
    assert len(graph.get("links",graph.get("edges")))==receipt["edges"]
target=root/"archives/code-graphs"
if target.exists():
    raise ValueError("Refusing to replace existing raw version graph directory")
shutil.copytree(origin,target)
for p in origin.rglob("*"):
    if p.is_file(): assert p.read_bytes()==(target/p.relative_to(origin)).read_bytes()
print("Verified 36 distinct raw graph.json and receipt.json pairs")
