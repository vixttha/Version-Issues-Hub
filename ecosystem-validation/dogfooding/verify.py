"""Read-only historical evidence replay. No source/adopter mutations."""
import base64, hashlib, json, os, time, urllib.request, urllib.parse
from pathlib import Path
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).parent
evidence = json.loads((ROOT/"evidence.json").read_text())
token = os.environ.get("GH_TOKEN")
def get(path):
    req=urllib.request.Request("https://api.github.com"+path,headers={"Accept":"application/vnd.github+json","User-Agent":"dogfooding-audit","Authorization":"Bearer "+token} if token else {"Accept":"application/vnd.github+json","User-Agent":"dogfooding-audit"})
    for i in range(3):
        try:
            with urllib.request.urlopen(req,timeout=35) as response:
                return json.load(response)
        except (TimeoutError,URLError) as exc:
            if i==2 or isinstance(exc,HTTPError) and exc.code not in (500,502,503,504):
                raise
            time.sleep(i+1)
def check_file(row):
    path=urllib.parse.quote(row["path"],safe="/")
    item=get(f"/repos/vixttha/{row['repo']}/contents/{path}?ref={row['commit']}")
    assert item["type"]=="file" and item["path"]==row["path"] and item["encoding"]=="base64",row
    raw=base64.b64decode(item["content"])
    actual=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    assert actual==row["blob"]==item["sha"],row
    return raw
def check_run(row):
    item=get(f"/repos/vixttha/{row['repo']}/actions/runs/{row['run']}/attempts/{row['attempt']}")
    assert item["id"]==row["run"] and item["head_sha"]==row["head"] and item["run_attempt"]==row["attempt"],row
    assert item["status"]=="completed" and item["conclusion"]==row["conclusion"],row
    return {**row,"event":item["event"],"name":item["name"]}
def census(repo):
    rows=[]
    for page in range(1,11):
        batch=get(f"/repos/vixttha/{repo}/issues?state=all&per_page=100&page={page}")
        rows+=batch
        if len(batch)<100:
            break
    else:
        raise ValueError("census pagination cap exceeded")
    return {"total":len(rows),"issues":sum("pull_request" not in x for x in rows),"prs":sum("pull_request" in x for x in rows),"open_issues":sum("pull_request" not in x and x["state"]=="open" for x in rows),"open_prs":sum("pull_request" in x and x["state"]=="open" for x in rows),"records":[{"number":x["number"],"kind":"pr" if "pull_request" in x else "issue","state":x["state"],"title":x["title"]} for x in rows]}
def main():
    contents={(r["repo"],r["path"]):check_file(r) for r in evidence["files"]}
    checked=[check_run(r) for r in evidence["runs"]]
    vib=json.loads(contents[("Version-Issues-Hub","ledger/issue-versions.json")])
    bart=json.loads(contents[("Blender-Agent-Refinement-Toolkit","ledger/issue-versions.json")])
    receipt=json.loads(next(v for (r,p),v in contents.items() if r=="Version-Issues-Hub" and p.endswith("candidate-receipt.json")))
    assert len(vib["issues"])==17 and len(bart["issues"])==24
    assert {r["issue"]:r["state"] for r in bart["issues"]}[69]=="integrated"
    assert len(receipt["lookups"])==8 and receipt["status"]=="candidate_only"
    source=receipt["source"]
    assert source=="3b6951be81d2fc9468b5379aead57c7afc444754"
    archive_path="archives/candidates/"+source+"/45331511873-1/archive/253596b8399e7853745c1e50d09cfa3e240cedce793165959b45d9ed154e2307.json"
    url="https://raw.githubusercontent.com/vixttha/Version-Issues-Hub/829fdfae2ac0e8167d740e1a0ad8e8201295c34e/"+archive_path
    with urllib.request.urlopen(url,timeout=60) as response:
        archived=response.read(16*1024*1024+1)
    assert len(archived)<=16*1024*1024 and hashlib.sha256(archived).hexdigest()==receipt["archive_sha256"]
    for row in receipt["lookups"].values():
        assert row["source"]==source and row["archive_sha256"]==receipt["archive_sha256"]
        for cite in row["citations"]:
            item=get("/repos/vixttha/Version-Issues-Hub/contents/"+urllib.parse.quote(cite["path"],safe="/")+"?ref="+source)
            raw=base64.b64decode(item["content"])
            assert hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()==item["sha"]
            assert 1<=cite["line"]<=len(raw.splitlines())
    ver=json.loads(contents[("Veraphify","brand-identity/01-strategy/creative-decision.json")])
    assert ver["confirmation"]["product"]=="Veraphify" and len(ver["concepts"])==3
    assert json.loads(contents[("Veraphify","brand-identity/09-assets/manifest.json")])["assets"]==[]
    assert json.loads(contents[("Version-Issues-Hub","brand-identity/01-strategy/creative-decision.json")])["confirmation"] is None
    assert len(json.loads(contents[("Brand-Identity-Template","brand-identity/09-assets/manifest.json")])["assets"])==2
    self_record=json.loads(contents[("Provenistem","catalog/features/records/FEAT-000016.json")])
    assert self_record["lifecycle_status"]=="verified" and self_record["release_membership"]=="NOT_ASSERTED"
    repos=["Version-Issues-Hub","Provenistem","Lydite-Test-Vault-Template","Veraphify","README-HQ","Brand-Identity-Template"]
    inventory={repo:census(repo) for repo in repos}
    out={"schema_version":1,"checked_files":evidence["files"],"checked_runs":checked,"case_count":len(evidence["cases"]),"census":inventory,"archive_digest":receipt["archive_sha256"],"vib_candidate_citations":len(receipt["lookups"]),"vib_ledger_count":len(vib["issues"]),"bart_ledger_count":len(bart["issues"]),"limits":["metadata census only; not every issue body/commit","historical run metadata and selected logs; no claim of new replay of all old tests","pinned source integrity and semantic controls; not causal benchmark"]}
    Path(os.environ["RUNNER_TEMP"],"dogfooding-audit.json").write_text(json.dumps(out,indent=2)+"\n")
    print("Verified",len(contents),"pinned files,",len(checked),"exact run attempts;",len(evidence["cases"]),"case records.")
    print("Archive SHA-256 and eight citation positions verified:",receipt["archive_sha256"])
    print("Issue/PR census:",json.dumps({r:{k:v for k,v in c.items() if k!="records"} for r,c in inventory.items()}))
if __name__=="__main__":
    main()
