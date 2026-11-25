"""Fresh-job evidence reconstruction and negative controls."""
import hashlib,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
root=Path(__file__).resolve().parent
contract=json.loads((root/"contract.json").read_bytes())
def need(ok,msg):
    if not ok:raise RuntimeError(msg)
def call(args,marker):
    p=subprocess.run(args,capture_output=True,text=True,timeout=60)
    need(p.returncode==0 and p.stdout.strip()==marker,str((args,p.returncode,p.stdout,p.stderr)))
def verify_case(casepath,case,osname):
    need({p.name for p in casepath.iterdir()}=={"ledger.json","handoff.json","repo.bundle","base.txt","final.txt","receipt.json"},"file inventory")
    r=json.loads((casepath/"receipt.json").read_bytes())
    need((r["vault"],r["product"],r["run"],r["attempt"],r["os"],r["id"])==(os.environ["GITHUB_SHA"],contract["product"],os.environ["GITHUB_RUN_ID"],os.environ["GITHUB_RUN_ATTEMPT"],osname,case),"scope")
    call(["bash",str(root/"challenger.sh"),"audit",str(casepath),"Version-Issues-Hub"],"BASH_VERIFIED")
    call(["pwsh","-NoProfile","-NonInteractive","-File",str(root/"auditor.ps1"),str(casepath),str(root/"contract.json"),case],"POWERSHELL_VERIFIED")
def controls(source,other):
    def change_receipt(p,fn):
        f=p/"receipt.json";r=json.loads(f.read_bytes());fn(r);f.write_text(json.dumps(r),encoding="utf-8")
    def change_file(p,name,fn):
        f=p/name;data=json.loads(f.read_bytes());fn(data);f.write_text(json.dumps(data),encoding="utf-8")
        change_receipt(p,lambda r:r["hashes"].update({name:hashlib.sha256(f.read_bytes()).hexdigest()}))
    def missing(p):(p/"ledger.json").unlink()
    def corrupt(p):
        f=p/"ledger.json";f.write_bytes(f.read_bytes()+b"\n")
    def swap(p):shutil.copyfile(other/"repo.bundle",p/"repo.bundle")
    cases=[("missing",missing),("byte-tamper",corrupt),("swapped-bundle",swap),
           ("stale-attempt",lambda p:change_receipt(p,lambda r:r.update(attempt="0"))),
           ("wrong-product",lambda p:change_receipt(p,lambda r:r.update(product="0"*40))),
           ("wrong-scenario",lambda p:change_receipt(p,lambda r:r.update(id="fake"))),
           ("forged-recovery",lambda p:change_receipt(p,lambda r:r.update(recovery="saved"))),
           ("omitted-publication",lambda p:change_receipt(p,lambda r:r.update(events=[]))),
           ("forced-write",lambda p:change_receipt(p,lambda r:r["events"][0].update(force=True))),
           ("forged-ledger-with-digest",lambda p:change_file(p,"ledger.json",lambda r:r["issues"][0].update(version="v1.0.6.999"))),
           ("forged-handoff-with-digest",lambda p:change_file(p,"handoff.json",lambda r:r["active"].update(phase="Head")))]
    for name,mutate in cases:
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"case";shutil.copytree(source,p);mutate(p)
            try:verify_case(p,"normal","Linux")
            except RuntimeError as exc:
                print("TR_NEGATIVE "+name+" REJECTED "+str(exc)[:200],flush=True)
            else:raise RuntimeError("False green: "+name)
    verify_case(source,"normal","Linux")
def main():
    evidence=Path(sys.argv[1]).resolve()
    expected={s["id"] for s in contract["scenarios"]}
    need({p.name for p in evidence.iterdir()}=={"tr-ubuntu-24.04","tr-windows-latest"},"OS inventory")
    for label,osname in [("tr-ubuntu-24.04","Linux"),("tr-windows-latest","Windows")]:
        folder=evidence/label
        need({p.name for p in folder.iterdir()}==expected,"scenario inventory")
        for case in sorted(expected):
            verify_case(folder/case,case,osname)
            print("TR_AUDIT "+label+" "+case+" PASS",flush=True)
    controls(evidence/"tr-ubuntu-24.04"/"normal",evidence/"tr-ubuntu-24.04"/"competing-claim")
    print("TR_AUDIT_SUMMARY 8 positive 11 negative",flush=True)
if __name__=="__main__":main()
