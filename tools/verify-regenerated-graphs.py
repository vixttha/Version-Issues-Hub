"""Verify fresh extraction against immutable retained graph bytes without importing."""
import hashlib,json,os
from pathlib import Path
origin=Path(os.environ["RUNNER_TEMP"])/"graphs"
target=Path("archives/cumulative-code-graphs")
fresh=json.loads((origin/"index.json").read_bytes())
old=json.loads((target/"index.json").read_bytes())
assert not fresh["failures"] and not old["failures"]
assert len(fresh["results"])==len(old["results"])==36
for i,(a,b) in enumerate(zip(fresh["results"],old["results"]),1):
    assert a["version"]==b["version"]==f"v0.0.0.{i}"
    for base,r in ((origin,a),(target,b)):
        p=base/r["version"]
        assert json.loads((p/"receipt.json").read_bytes())==r
        assert hashlib.sha256((p/"graph.json").read_bytes()).hexdigest()==r["graph_sha256"]
    assert {k:v for k,v in a.items() if k not in ("run","attempt")}=={k:v for k,v in b.items() if k not in ("run","attempt")},a["version"]
    assert (origin/a["version"]/"graph.json").read_bytes()==(target/b["version"]/"graph.json").read_bytes()
print("36 regenerated graphs match retained raw bytes; no archive writes.")
