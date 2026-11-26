"""Replay older Python suites under the same coverage data file; no new test count."""
import hashlib,json,os,subprocess,sys
from pathlib import Path
root=Path(os.environ["RUNNER_TEMP"])/"vib-advanced"
root.mkdir(exist_ok=True)
old=Path(__file__).resolve().parents[1]/"issue54"
files=["test_core.py","diagnostic.py","test_faults.py","test_evidence.py","test_schema.py","test_mutation.py","test_receipt.py","test_completion.py","test_ancestry.py","test_partial_metadata.py","test_interruptions.py","test_artifact.py","test_traces.py","test_qualification.py","test_high.py"]
rows=[]
for name in files:
    p=subprocess.run([sys.executable,"-m","coverage","run","--append","--branch","--source=tools",str(old/name)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=300)
    (root/("coverage-prior-"+name+".log")).write_bytes(p.stdout)
    rows.append({"suite":name,"exit_code":p.returncode,"log_sha256":hashlib.sha256(p.stdout).hexdigest()})
    print("VIB_COVERAGE_REPLAY "+json.dumps(rows[-1]),flush=True)
(root/"coverage-prior.json").write_text(json.dumps(rows,indent=2)+"\n")
# Existing nine regression probes remain red. Unexpected suite errors are
# visible separately in rows and fail this replay as well.
raise SystemExit(0 if all(r["exit_code"]==0 for r in rows) else 1)
