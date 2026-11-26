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
def coherent_controls(source,osname):
    """Give the semantic oracle a fully rehashed, valid Git history that lies."""
    def revise(folder,mutator):
        ledger=json.loads((folder/"ledger.json").read_bytes())
        handoff=json.loads((folder/"handoff.json").read_bytes())
        mutator(ledger,handoff)
        for name,obj in (("ledger.json",ledger),("handoff.json",handoff)):
            (folder/name).write_bytes((json.dumps(obj,ensure_ascii=True,sort_keys=True,indent=2)+"\n").encode())
        r=json.loads((folder/"receipt.json").read_bytes())
        base=(folder/"base.txt").read_text().strip();old=r["final"]
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp)/"repo";index=Path(tmp)/"index"
            env=dict(os.environ,GIT_INDEX_FILE=str(index),GIT_CONFIG_NOSYSTEM="1",GIT_CONFIG_GLOBAL=os.devnull,GIT_AUTHOR_NAME="synthetic adversary",GIT_AUTHOR_EMAIL="fixture@example.invalid",GIT_COMMITTER_NAME="synthetic adversary",GIT_COMMITTER_EMAIL="fixture@example.invalid")
            subprocess.run(["git","clone","--bare","--quiet",str(folder/"repo.bundle"),str(repo)],check=True,timeout=30,env=env)
            def g(*args,data=None):
                return subprocess.run(["git","-C",str(repo),*args],input=data,capture_output=True,check=True,timeout=30,env=env).stdout.decode("ascii").strip()
            g("read-tree",old+"^{tree}")
            for name,path in (("ledger.json","ledger/issue-versions.json"),("handoff.json","ledger/handoff.json")):
                blob=g("hash-object","-w","--stdin",data=(folder/name).read_bytes())
                g("update-index","--add","--cacheinfo","100644",blob,path)
            tree=g("write-tree");new=g("commit-tree",tree,"-p",base,"-m","synthetic forged evidence")
            g("update-ref","refs/heads/Version-Issues-Hub",new,old)
            (folder/"repo.bundle").unlink();g("bundle","create",str(folder/"repo.bundle"),"--all")
        (folder/"final.txt").write_bytes(new.encode())
        r["final"]=new
        for e in r["events"]:
            if e["sha"]==old:e["sha"]=new
        for e in r["observations"]:
            if e.get("sha")==old:e["sha"]=new
        r["hashes"]={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in folder.iterdir() if f.name!="receipt.json"}
        (folder/"receipt.json").write_bytes(json.dumps(r,ensure_ascii=True).encode())
    def wrong_winner(l,h):l["issues"][0]["issue"]=999;h["active"]["issue"]=999
    def wrong_version(l,h):l["issues"][0]["version"]="v1.0.6.999";h["active"]["version"]="v1.0.6.999"
    def phase(l,h):h["active"]["phase"]="Head"
    def stale_evidence(l,h):h["active"]["evidence"]=["https://github.com/example/adopter/actions/runs/1/attempts/1"]
    def stale_candidate(l,h):h["active"]["candidate_sha"]="a"*40
    def criteria(l,h):l["issues"][0]["acceptance"]=["replaced acceptance"]
    def history(l,h):h["history"]=[{"handoff":h["active"],"disposition":"integrated","decision":"fabricated","merged_sha":"a"*40}]
    def second_claim(l,h):l["issues"].append({"issue":102,"version":"v1.0.6.2","state":"in_progress","acceptance":["preserve state"]})
    faults=[("wrong-winner",wrong_winner,"allocation"),("wrong-version",wrong_version,"allocation"),("phase",phase,"handoff"),("stale-evidence",stale_evidence,"handoff"),("stale-candidate",stale_candidate,"handoff"),("criteria",criteria,"criteria value"),("history",history,"handoff schema"),("second-claim",second_claim,"singleton")]
    verify_case(source,"normal",osname)
    for name,mutator,expected in faults:
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/"case";shutil.copytree(source,folder);revise(folder,mutator)
            # The first independent checker must ACCEPT the coherent Git evidence.
            call(["bash",str(root/"challenger.sh"),"audit",str(folder),"Version-Issues-Hub"],"BASH_VERIFIED")
            # The second must REJECT the specific semantic violation, not just fail.
            args=["pwsh","-NoProfile","-NonInteractive","-File",str(root/"auditor.ps1"),str(folder),str(root/"contract.json"),"normal"]
            proc=subprocess.run(args,capture_output=True,text=True,timeout=60)
            need(proc.returncode!=0 and expected in proc.stderr,"Semantic oracle missed or misclassified "+name+": "+proc.stderr)
            print("TR_COHERENT_FORGERY "+osname+" "+name+" BASH_ACCEPTED POWERSHELL_REJECTED "+expected,flush=True)
    verify_case(source,"normal",osname)

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
    coherent_controls(evidence/"tr-ubuntu-24.04"/"normal","Linux")
    coherent_controls(evidence/"tr-windows-latest"/"normal","Windows")
    print(f"TR_AUDIT_SUMMARY {len(expected)*2} positive 27 negative (16 coherent semantic forgeries)",flush=True)
if __name__=="__main__":main()
