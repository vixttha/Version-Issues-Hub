"""Execute real VIB claim/save with a local Git-backed API adapter; no network."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

HERE=Path(__file__).resolve().parent
PRODUCT=Path(os.environ["VIB_CHECKOUT"]).resolve()
sys.path.insert(0,str(PRODUCT))
from tools import install,session

def require(ok,msg):
    if not ok:raise RuntimeError(msg)
def git(repo,*args,data=None,env=None):
    return subprocess.run(["git","-C",str(repo),*args],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=20,env=env).stdout
def oid(repo,*args,**kw):return git(repo,*args,**kw).decode("ascii").strip()
def dump(path,obj):path.write_bytes((json.dumps(obj,ensure_ascii=True,sort_keys=True,indent=2)+"\n").encode())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def bash():
    if os.name!="nt":return shutil.which("bash")
    for p in (Path(shutil.which("git")).resolve().parents[1]/"bin/bash.exe",Path(os.environ.get("ProgramFiles","C:/Program Files"))/"Git/bin/bash.exe"):
        if p.is_file():return str(p)
    raise RuntimeError("native Git Bash absent")
def runbash(*args):
    return subprocess.run([bash(),"--noprofile","--norc",str(HERE/"challenger.sh"),*map(str,args)],capture_output=True,timeout=30)
def tree(repo,base,files):
    with tempfile.TemporaryDirectory() as d:
        env=dict(os.environ,GIT_INDEX_FILE=str(Path(d)/"index"))
        if base:git(repo,"read-tree",base,env=env)
        for path,content in files.items():
            blob=oid(repo,"hash-object","-w","--stdin",data=content.encode("utf-8"))
            git(repo,"update-index","--add","--cacheinfo","100644",blob,path,env=env)
        return oid(repo,"write-tree",env=env)
def commit(repo,t,parent=None):
    return oid(repo,"commit-tree",t,*(["-p",parent] if parent else []),"-m","synthetic VIB")
class Adapter:
    def __init__(self,repo,fault="none",events=None):
        self.repo=repo;self.fault=fault;self.events=[] if events is None else events
    def snapshot(self):
        ref=oid(self.repo,"rev-parse","refs/heads/"+install.BRANCH)
        def read(p):return json.loads(git(self.repo,"show",ref+":"+p))
        return {"prefix":"/repos/example/adopter","ref":ref,"product_sha":oid(self.repo,"rev-parse","refs/heads/main"),"manifest":{"baseline_version":"v1.0.6","target_version":"v1.0.7","product_branch":"main","target_repository_id":42},"ledger":read(session.LEDGER),"handoff":read(session.HANDOFF)}
    def request(self,method,path,body=None):
        prefix="/repos/example/adopter"
        require(path.startswith(prefix+"/"),"unexpected API path")
        route=path[len(prefix):]
        if method=="GET" and route.startswith("/issues/"):
            return {"number":int(route.rsplit("/",1)[1]),"state":"open"}
        if method=="GET" and route=="/git/ref/heads/"+install.BRANCH:
            return {"ref":"refs/heads/"+install.BRANCH,"object":{"type":"commit","sha":oid(self.repo,"rev-parse","refs/heads/"+install.BRANCH)}}
        if method=="GET" and route.startswith("/git/commits/"):
            ref=route.rsplit("/",1)[1];return {"sha":ref,"tree":{"sha":oid(self.repo,"rev-parse",ref+"^{tree}")}}
        if method=="POST" and route=="/git/trees":
            require({x["path"] for x in body["tree"]}=={session.LEDGER,session.HANDOFF},"unexpected tree paths")
            require(all(x["mode"]=="100644" and x["type"]=="blob" for x in body["tree"]),"unexpected mode")
            return {"sha":tree(self.repo,body["base_tree"],{x["path"]:x["content"] for x in body["tree"]})}
        if method=="POST" and route=="/git/commits":
            require(len(body["parents"])==1,"single parent")
            return {"sha":commit(self.repo,body["tree"],body["parents"][0])}
        if method=="PATCH" and route=="/git/refs/heads/"+install.BRANCH:
            require(body["force"] is False,"force forbidden")
            fault,self.fault=self.fault,"none"
            if fault=="compete":
                other=Adapter(self.repo,events=self.events)
                apply(other,102)
            event={"method":"PATCH","sha":body["sha"],"force":body["force"]}
            if fault=="before":
                event["result"]="lost-before";self.events.append(event)
                raise TimeoutError("synthetic response absent before publication")
            r=runbash("publish",self.repo,install.BRANCH,body["sha"])
            if r.returncode==23:
                event["result"]="conflict";self.events.append(event)
                raise install.ApiError(422)
            require(r.returncode==0,"Bash publication error: "+repr(r.stderr))
            event["result"]="lost-after" if fault=="after" else "published";self.events.append(event)
            if fault=="after":raise TimeoutError("synthetic response lost after publication")
            return {}
        raise RuntimeError("Unexpected API method/path: "+method+" "+route)
def apply(api,issue):
    state=api.snapshot()
    ledger,handoff=session.claim(api,state,issue,["preserve state"],"repair")
    return session.save(api,state,ledger,handoff,apply=True)
def main():
    c=json.loads((HERE/"contract.json").read_bytes())
    require(oid(PRODUCT,"rev-parse","HEAD")==c["product"],"pin mismatch")
    require(not git(PRODUCT,"status","--porcelain","--untracked-files=all"),"dirty product")
    output=Path(os.environ["RUNNER_TEMP"])/"tri-adversarial"
    output.mkdir()
    config=output/"empty.config";config.write_bytes(b"")
    os.environ.update(GIT_CONFIG_NOSYSTEM="1",GIT_CONFIG_GLOBAL=str(config),GIT_AUTHOR_NAME="fixture",GIT_AUTHOR_EMAIL="fixture@example.invalid",GIT_COMMITTER_NAME="fixture",GIT_COMMITTER_EMAIL="fixture@example.invalid",GH_TOKEN="",GITHUB_TOKEN="")
    for spec in c["scenarios"]:
        folder=output/spec["id"];folder.mkdir()
        with tempfile.TemporaryDirectory(prefix="tri [fixture] ") as d:
            repo=Path(d)/"repo";subprocess.run(["git","init","--bare","--object-format=sha1","-q",str(repo)],check=True,timeout=20)
            initial={session.LEDGER:install.render({"schema_version":1,"repository":"example/adopter","issues":[]}),session.HANDOFF:install.render({"schema_version":1,"active":None,"history":[]})}
            base=commit(repo,tree(repo,None,initial))
            for branch in ("main",install.BRANCH):git(repo,"update-ref","refs/heads/"+branch,base)
            api=Adapter(repo,spec["fault"])
            try:
                first=apply(api,101)
                require(spec["fault"]=="none" and first["status"]=="saved","unexpected initial success")
            except TimeoutError:
                require(spec["fault"] in ("before","after"),"unexpected timeout")
            except install.ApiError as exc:
                require(spec["fault"]=="compete" and exc.status==422,"unexpected rejection")
            # A new adapter observes the authoritative ref and reconstructs state.
            fresh=Adapter(repo,events=api.events)
            try:recovery=apply(fresh,101)["status"]
            except ValueError as exc:
                require(spec["fault"]=="compete" and "Another issue" in str(exc),"unexpected recovery rejection")
                recovery="blocked"
            require(recovery==spec["recovery"],"recovery mismatch")
            final=fresh.snapshot()["ref"]
            require(final!=base,"no publication")
            require(oid(repo,"rev-parse","refs/heads/main")==base,"main changed")
            (folder/"base.txt").write_bytes(base.encode());(folder/"final.txt").write_bytes(final.encode())
            for path,name in [(session.LEDGER,"ledger.json"),(session.HANDOFF,"handoff.json")]:
                (folder/name).write_bytes(git(repo,"show",final+":"+path))
            git(repo,"bundle","create",str(folder/"repo.bundle"),"--all")
            receipt={"id":spec["id"],"product":c["product"],"vault":os.environ["GITHUB_SHA"],"run":os.environ["GITHUB_RUN_ID"],"attempt":os.environ["GITHUB_RUN_ATTEMPT"],"os":os.environ["RUNNER_OS"],"final":final,"recovery":recovery,"events":api.events,"hashes":{f.name:sha(f) for f in folder.iterdir()}}
            dump(folder/"receipt.json",receipt)
            print("TR_CASE "+json.dumps({"id":spec["id"],"recovery":recovery,"events":api.events}),flush=True)
    config.unlink()
    require(not git(PRODUCT,"status","--porcelain","--untracked-files=all"),"product drift")
if __name__=="__main__":main()
