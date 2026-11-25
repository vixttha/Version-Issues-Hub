"""Run named issue-54 probes and preserve exact log and identity."""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

here=Path(__file__).resolve().parent
vault=here.parents[1]
product=vault.parent/"product"
def head(root):
    return subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"]).decode().strip()
pin="7ae6626e44d01d29b11968da28e6debd816f8c06"
v=head(vault)
if v != os.environ["GITHUB_SHA"] or head(product)!=pin:
    raise RuntimeError("Checkout identity mismatch")
kind=sys.argv[1]
cmd={"python":[sys.executable,"-B",str(here/"test_core.py")],
     "diagnostic":[sys.executable,"-B",str(here/"diagnostic.py")],
     "completion":[sys.executable,"-B",str(here/"test_completion.py")],
     "bash4":["bash",str(here/"history.sh")],
     "powershell4":["pwsh","-NoProfile","-File",str(here/"history.ps1")],
     "receipt":[sys.executable,"-B",str(here/"test_receipt.py")],
     "schema":[sys.executable,"-B",str(here/"test_schema.py")],
     "mutation":[sys.executable,"-B",str(here/"test_mutation.py")],
     "bash3":["bash",str(here/"attrs.sh")],
     "powershell3":["pwsh","-NoProfile","-File",str(here/"attrs.ps1")],
     "faults":[sys.executable,"-B",str(here/"test_faults.py")],
     "evidence":[sys.executable,"-B",str(here/"test_evidence.py")],
     "bash2":["bash",str(here/"platform.sh")],
     "powershell2":["pwsh","-NoProfile","-File",str(here/"platform.ps1")],
     "bash":["bash",str(here/"core.sh")],
     "powershell":["pwsh","-NoProfile","-File",str(here/"core.ps1")]}[kind]
env=dict(os.environ,VIB_CHECKOUT=str(product),PYTHONDONTWRITEBYTECODE="1",PYTHONUTF8="1")
out=Path(os.environ["RUNNER_TEMP"])/"issue54"
out.mkdir(exist_ok=True)
result=subprocess.run(cmd,cwd=product,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=240)
raw=result.stdout
(out/(kind+".log")).write_bytes(raw)
log=raw.decode("utf-8",errors="replace")
print(log,flush=True)
if kind=="python" and (out/"transport.json").is_file():
    print("VIB54_TRANSPORT "+(out/"transport.json").read_text(encoding="utf-8"),flush=True)
if kind in ("python","diagnostic","faults","evidence","schema","mutation","receipt","completion"):
    ids=re.findall(r"^test_[^\s]+ \(([^)]*)\) \.\.\. ok",log,re.M)
    if kind!="python":
        identity_file=out/(kind+"-identities.json")
        ids=json.loads(identity_file.read_text(encoding="utf-8")) if identity_file.is_file() else []
    expected={"python":67,"diagnostic":13,"faults":38,"evidence":12,"schema":47,"mutation":14,"receipt":24,"completion":60}[kind]
    passed=len(ids)==expected and len(set(ids))==expected and not re.search(r"\b(skipped|expected failures|unexpected successes)=",log)
else:
    ids=re.findall(r"^PASS ((?:BA4|PS4|BA3|PS3|BA2|PS2|BA|PS)-\S+)",log,re.M)
    expected=14 if kind in ("bash4","powershell4") else 12 if kind in ("bash3","powershell3") else 19 if kind in ("bash2","powershell2") else 15
    passed=len(ids)==expected and len(set(ids))==expected
passed=passed and result.returncode==0 and head(vault)==v and head(product)==pin
report={"vault_sha":v,"product_sha":pin,"run_id":os.environ["GITHUB_RUN_ID"],"attempt":os.environ["GITHUB_RUN_ATTEMPT"],"os":platform.platform(),"python":platform.python_version(),"kind":kind,"expected_count":expected,"passed_ids":ids,"exit_code":result.returncode,"log_sha256":hashlib.sha256(raw).hexdigest(),"outcome":"pass" if passed else "fail"}
(out/(kind+".json")).write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report),flush=True)
raise SystemExit(0 if passed else 1)
