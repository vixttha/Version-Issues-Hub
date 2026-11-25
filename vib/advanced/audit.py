import json,os,subprocess
from pathlib import Path
here=Path(__file__).resolve().parent
root=Path(os.environ["RUNNER_TEMP"])/"vib-advanced"
catalog=json.loads((here/"catalog.json").read_text())
def require(condition,message):
    if not condition:raise ValueError(message)
def head(p):return subprocess.check_output(["git","-C",str(p),"rev-parse","HEAD"],text=True).strip()
pin="7ae6626e44d01d29b11968da28e6debd816f8c06"
require(head(here.parents[1])==os.environ["GITHUB_SHA"],"vault identity")
require(head(Path(os.environ["VIB_CHECKOUT"]))==pin,"product identity")
results=[]
for batch,ids in catalog.items():
    r=json.loads((root/(batch+".json")).read_text())
    require(r["expected"]==ids and r["batch"]==batch,"inventory")
    require(r["vault_sha"]==os.environ["GITHUB_SHA"] and r["product_sha"]==pin and r["run"]==os.environ["GITHUB_RUN_ID"] and r["attempt"]==os.environ["GITHUB_RUN_ATTEMPT"],"run identity")
    all_ids=r["passed"]+r["failures"]+r["errors"]+r["skipped"]
    require(sorted(all_ids)==ids and len(set(all_ids))==len(ids),"partition")
    require((r["outcome"]=="pass")== (r["passed"]==ids),"verdict")
    results.append({"batch":batch,"passed":len(r["passed"]),"expected":len(ids),"outcome":r["outcome"]})
cov=json.loads((root/"coverage.json").read_text())
require(bool(cov["meta"]["branch_coverage"]) and bool(cov["files"]),"branch coverage missing")
summary={"integrity":"verified","results":results,"coverage":cov["totals"],"scope":"baseline and advanced Python in-process coverage only; subprocesses not instrumented"}
(root/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
print("VIB_ADVANCED_AUDIT "+json.dumps(summary))
