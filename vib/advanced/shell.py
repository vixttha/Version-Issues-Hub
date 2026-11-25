import hashlib,json,os,re,subprocess
from pathlib import Path
here=Path(__file__).resolve().parent
root=Path(os.environ["RUNNER_TEMP"])/"vib-advanced";root.mkdir(exist_ok=True)
windows=os.environ["RUNNER_OS"]=="Windows"
if windows:
    prefix="PS";cmd=["pwsh","-NoProfile","-File",str(here/"platform.ps1")]
    names=["12-worktree","12-isolation","12-junction","12-lock"]
else:
    prefix="BA";cmd=["bash",str(here/"platform.sh")]
    names=["12-worktree","12-isolation","12-shallow","12-symlink"]
expected=sorted(prefix+x for x in names+["16-git","16-digest","16-empty-git","16-empty-digest"])
p=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
raw=p.stdout;(root/"shell.log").write_bytes(raw);print(raw.decode("utf-8",errors="replace"))
ids=sorted(re.findall(r"^PASS ((?:BA|PS)\d+-[a-z-]+)\r?$",raw.decode("utf-8",errors="replace"),re.M))
ok=ids==expected and p.returncode==0
report={"vault_sha":os.environ["GITHUB_SHA"],"product_sha":"7ae6626e44d01d29b11968da28e6debd816f8c06","run":os.environ["GITHUB_RUN_ID"],"attempt":os.environ["GITHUB_RUN_ATTEMPT"],"expected":expected,"passed":ids,"exit_code":p.returncode,"outcome":"pass" if ok else "fail","log_sha256":hashlib.sha256(raw).hexdigest()}
(root/"shell.json").write_text(json.dumps(report,indent=2)+"\n")
raise SystemExit(0 if ok else 1)
