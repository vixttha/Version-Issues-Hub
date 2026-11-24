"""Read-only historical evidence verification, not a product or benchmark."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).parent
data = json.loads((ROOT / "dogfooding-evidence.json").read_text(encoding="utf-8"))
def get(url):
    for attempt in range(3):
        try:
            req = Request(url, headers={"User-Agent":"ecosystem-evidence-verifier","Accept":"application/vnd.github+json"})
            # Read public resources only; no credentials leave runner.
            with urlopen(req, timeout=25) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError) as e:
            if attempt == 2 or isinstance(e, HTTPError) and e.code not in (429,500,502,503,504):
                raise
            time.sleep(attempt+1)
def safe_source(s):
    assert re.fullmatch(r"vixttha/[A-Za-z0-9_.-]+",s["repository"])
    assert re.fullmatch(r"[0-9a-f]{40}",s["commit"])
    assert re.fullmatch(r"[0-9a-f]{40}",s["blob"])
    assert all(part not in ("",".","..") for part in s["path"].split("/"))
def main():
    sources, runs, rows = {}, {}, []
    for c in data["cases"]:
        s = c["source"]
        safe_source(s)
        key = (s["repository"],s["commit"],s["path"])
        if key not in sources:
            raw = get("https://raw.githubusercontent.com/"+s["repository"]+"/"+s["commit"]+"/"+quote(s["path"],safe="/"))
            blob = hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
            sources[key] = blob
        assert sources[key] == s["blob"], c["id"]
        run = c["run"]
        if run:
            assert re.fullmatch(r"vixttha/[A-Za-z0-9_.-]+",run["repository"])
            assert type(run["id"]) is int and type(run["attempt"]) is int
            keyrun=(run["repository"],run["id"],run["attempt"])
            if keyrun not in runs:
                url=f'https://api.github.com/repos/{run["repository"]}/actions/runs/{run["id"]}/attempts/{run["attempt"]}'
                value=json.loads(get(url))
                assert value["id"]==run["id"] and value["run_attempt"]==run["attempt"]
                runs[keyrun]=(value["head_sha"],value["status"],value["conclusion"])
            assert runs[keyrun]==(run["head"],"completed",run["conclusion"]), c["id"]
        rows.append({"id":c["id"],"source_blob":s["blob"],"run_metadata":"verified" if run else "not_claimed","status":"pass"})
        print(c["id"], "source verified; historical run metadata", "verified" if run else "not claimed")
    assert len({c["id"] for c in data["cases"]})==len(rows)==data["counts"]["cases"]
    assert len(sources)==data["counts"]["source_pins"]
    assert len(runs)==data["counts"]["distinct_runs"]
    edges={(c["provider"],c["beneficiary"]) for c in data["cases"] if c["provider"]!=c["beneficiary"] and c["classification"] not in ("feedback","external-adopter")}
    assert len(edges)==data["counts"]["internal_cross_product_operational_edges"]
    out={"kind":"historical_reference_readback","counts":data["counts"],"rows":rows,"limitations":"Validates immutable source bytes and run metadata, not historical log semantics or runtime behavior; no productivity claim."}
    (Path(os.environ["RUNNER_TEMP"])/"dogfooding-verification.json").write_text(json.dumps(out,indent=2)+"\n",encoding="utf-8")
    print("PASS:",len(rows),"cases;",len(sources),"pinned source files;",len(runs),"historical run attempts;",len(edges),"internal operational edges")
if __name__=="__main__":
    main()
