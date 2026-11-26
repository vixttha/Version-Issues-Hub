"""Select monotonically cumulative real first-parent snapshots, without rewriting Git."""
import json,subprocess,os
from pathlib import Path
root=Path(os.environ["GITHUB_WORKSPACE"])
repo=root/"source"
vault=root/"vault"
head="26e9fe8c019a33c5f84f77a37da70925505204e3"
def git(*args): return subprocess.check_output(["git",*args],cwd=repo,text=True).strip()
def contains(a,b):
    p=subprocess.run(["git","merge-base","--is-ancestor",a,b],cwd=repo)
    if p.returncode not in (0,1): raise ValueError("Ancestry check failed")
    return p.returncode==0
assert git("rev-parse","HEAD")==head
history=git("rev-list","--first-parent","--reverse",head).splitlines()
original=json.loads((vault/"tools/vib-code-graph-inventory.json").read_text())
out=[]; required=[]; last=0
for row in original:
    if row["issue"]!=40: required.append(row["source"])
    while last<len(history) and not all(contains(p,history[last]) for p in required): last+=1
    if last==len(history): raise ValueError("No cumulative source covers prefix")
    selected=head if row["version"]=="v0.0.0.36" else history[last]
    assert all(contains(p,selected) for p in required)
    if out: assert contains(out[-1]["source"],selected)
    out.append({"version":row["version"],"issue":row["issue"],"source":selected,
                "source_kind":"reconstructed_cumulative_engineering_prefix",
                "original_fix_source":row["source"],"covered_fix_sources":list(dict.fromkeys(required)),
                "operational_exclusion":row["issue"]==40,"not_historical_release":True})
(root/"cumulative-inventory.json").write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps(out,indent=2))
