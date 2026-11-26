import json,subprocess,tempfile,shutil,os
from pathlib import Path
root=Path.cwd()
archive=root/"archives"
def read(p):return json.loads(p.read_text())
def call(command,r,scope,base=archive,extra=(),ok=True):
    p=subprocess.run(["node","veraphifiy.mjs",command,"--archive",str(base),"--project","vixttha/Version-Issues-Hub","--version",r["version"],"--scope",scope,"--source",r["source"],"--graph-sha256",r["graph_sha256"],*extra],capture_output=True,text=True)
    assert (p.returncode==0)==ok,p.stderr
    return json.loads(p.stdout) if ok else None
for scope,folder in [("fix","code-graphs"),("cumulative","cumulative-code-graphs")]:
    ix=read(archive/folder/"index.json")
    assert not ix["failures"] and len(ix["results"])==36
    for r in ix["results"]:
        assert call("code-verify",r,scope)==r
        got=call("code-graph",r,scope)
        assert got["receipt"]==r and got["graph"]==read(archive/folder/r["version"]/"graph.json")
    r=ix["results"][0]
    call("code-verify",{**r,"source":"0"*40},scope,ok=False)
    call("code-verify",{**r,"graph_sha256":"0"*64},scope,ok=False)
    call("code-verify",r,scope,extra=["--source",r["source"]],ok=False)
    call("code-verify",{**r,"version":"v0.0.0.37"},scope,ok=False)
    with tempfile.TemporaryDirectory() as tmp:
        dest=Path(tmp)/folder;dest.mkdir()
        shutil.copy(archive/folder/"index.json",dest/"index.json")
        shutil.copytree(archive/folder/r["version"],dest/r["version"])
        p=dest/r["version"]/"graph.json";p.write_bytes(p.read_bytes()+b" ")
        call("code-verify",r,scope,base=Path(tmp),ok=False)
print("144 positive native retrievals (72 verify, 72 graph), 10 negative probes passed")
