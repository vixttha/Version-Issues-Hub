"""Public, credential-free source-byte verification; historic run metadata checked separately."""
import hashlib
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT=Path(__file__).parent
data=json.loads((ROOT/"dogfooding-evidence.json").read_text(encoding="utf-8"))
def get(url):
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={"User-Agent":"ecosystem-evidence-verifier"}),timeout=25) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            if attempt==2 or isinstance(exc, HTTPError) and exc.code not in (429,500,502,503,504):
                raise
            time.sleep(attempt+1)
def main():
    sources,runs,rows={},set(),[]
    for c in data["cases"]:
        s=c["source"]
        assert re.fullmatch(r"vixttha/[A-Za-z0-9_.-]+",s["repository"])
        assert re.fullmatch(r"[0-9a-f]{40}",s["commit"])
        assert re.fullmatch(r"[0-9a-f]{40}",s["blob"])
        assert all(p not in ("",".","..") for p in s["path"].split("/"))
        key=(s["repository"],s["commit"],s["path"])
        if key not in sources:
            raw=get("https://raw.githubusercontent.com/"+s["repository"]+"/"+s["commit"]+"/"+quote(s["path"],safe="/"))
            sources[key]=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
        assert sources[key]==s["blob"],c["id"]
        run=c["run"]
        if run:
            assert re.fullmatch(r"vixttha/[A-Za-z0-9_.-]+",run["repository"])
            assert re.fullmatch(r"[0-9a-f]{40}",run["head"])
            assert type(run["id"]) is int and run["id"]>0
            assert type(run["attempt"]) is int and run["attempt"]>0
            assert run["conclusion"]=="success"
            runs.add((run["repository"],run["id"],run["attempt"]))
        rows.append({"id":c["id"],"source_blob":s["blob"],"source_readback":"verified","run_metadata":"connector_verified_not_requeried" if run else "not_claimed"})
        print(c["id"],"source bytes verified")
    assert len({c["id"] for c in data["cases"]})==len(rows)==data["counts"]["cases"]
    assert len(sources)==data["counts"]["source_pins"]
    assert len(runs)==data["counts"]["distinct_runs"]
    edges={(c["provider"],c["beneficiary"]) for c in data["cases"] if c["provider"]!=c["beneficiary"] and c["classification"] not in ("feedback","external-adopter")}
    assert len(edges)==data["counts"]["internal_cross_product_operational_edges"]
    out={"kind":"source_byte_readback","counts":data["counts"],"rows":rows,"limitations":"Verified source bytes; historic run metadata checked separately by connector, not requeried or rerun by this workflow."}
    (Path(os.environ["RUNNER_TEMP"])/"dogfooding-verification.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print("PASS:",len(rows),"cases;",len(sources),"verified source blobs;",len(runs),"registered historical runs;",len(edges),"internal operational edges")
if __name__=="__main__":
    main()
