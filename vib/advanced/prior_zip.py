"""Read only prior public artifacts, validate API digest and actual ZIP members."""
import hashlib,json,os,sys,tempfile,subprocess
from pathlib import Path
from archive import inspect_zip
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"issue54"))
import audit_evidence as audit
repo="vixttha/Version-Issues-Hub"
run="45680605695";vault="2f2f29d801956d021aa8ae8d272a804a4212a35e"
for ident,os_name,digest in [
    (15054156538,"Linux","4a6541072b5c14b238356c79ac832a21ad974817222e585e5e2151f5cd6d561d"),
    (15054916015,"Windows","e90a98f28fbd7cce3cf9461e2c558f72f55f458f5d207fb7dec0b5dc51170193"),
]:
    with tempfile.TemporaryDirectory() as d:
        root=Path(d);p=root/"artifact.zip"
        endpoint=f"repos/{repo}/actions/artifacts/{ident}"
        meta=json.loads(subprocess.check_output(["gh","api",endpoint],timeout=30))
        if meta.get("digest")!="sha256:"+digest or str(meta["workflow_run"]["id"])!=run or meta["workflow_run"]["head_sha"]!=vault:raise ValueError("Artifact identity")
        with p.open("wb") as out:subprocess.run(["gh","api",endpoint+"/zip"],stdout=out,check=True,timeout=60)
        kinds=audit.inventory(os_name)
        expected={"integrity.json","transport.json"}
        for kind in kinds:
            expected.update({kind+".json",kind+".log"})
            if kind in audit.PYTHON and kind!="python":expected.add(kind+"-identities.json")
        # diagnostic script may create additional transport diagnostics; inventory is explicit.
        members=inspect_zip(p,expected,digest)
        data=root/"verified";data.mkdir()
        for name,raw in members.items():(data/name).write_bytes(raw)
        rows=[audit.verify(data,k,n,vault,audit.PIN,run,"1") for k,n in kinds.items()]
        summary=json.loads(members["integrity.json"])
        if sum(x["passed"] for x in rows)!=533 or sum(x["expected"] for x in rows)!=542 or summary["passed"]!=533:raise ValueError("Historical verdict mismatch")
        print("VIB_PRIOR_ZIP "+json.dumps({"artifact":ident,"os":os_name,"digest":digest,"members":len(members),"passed":533,"expected":542,"status":"verified"}),flush=True)
