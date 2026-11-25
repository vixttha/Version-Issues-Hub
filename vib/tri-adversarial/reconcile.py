"""Fresh-job evidence reconciliation. Native checks mandatory; no producer verdict accepted."""
import json,os,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parent
contract=json.loads((root/"contract.json").read_bytes())
def need(ok,msg):
    if not ok:raise RuntimeError(msg)
def call(args,marker):
    p=subprocess.run(args,capture_output=True,text=True,timeout=60)
    need(p.returncode==0 and p.stdout.strip()==marker,str((args,p.returncode,p.stdout,p.stderr)))
def main():
    evidence=Path(sys.argv[1]).resolve()
    expected={s["id"] for s in contract["scenarios"]}
    need({p.name for p in evidence.iterdir()}=={"tr-ubuntu-24.04","tr-windows-latest"},"OS inventory")
    for label,osname in [("tr-ubuntu-24.04","Linux"),("tr-windows-latest","Windows")]:
        folder=evidence/label
        need({p.name for p in folder.iterdir()}==expected,"scenario inventory")
        for case in sorted(expected):
            casepath=folder/case
            need({p.name for p in casepath.iterdir()}=={"ledger.json","handoff.json","repo.bundle","base.txt","final.txt","receipt.json"},"file inventory")
            r=json.loads((casepath/"receipt.json").read_bytes())
            need((r["vault"],r["product"],r["run"],r["attempt"],r["os"])==(os.environ["GITHUB_SHA"],contract["product"],os.environ["GITHUB_RUN_ID"],os.environ["GITHUB_RUN_ATTEMPT"],osname),"scope")
            call(["bash",str(root/"challenger.sh"),"audit",str(casepath),"Version-Issues-Hub"],"BASH_VERIFIED")
            call(["pwsh","-NoProfile","-NonInteractive","-File",str(root/"auditor.ps1"),str(casepath),str(root/"contract.json"),case],"POWERSHELL_VERIFIED")
            print("TR_AUDIT "+label+" "+case+" PASS",flush=True)
if __name__=="__main__":main()
