"""Independent pre-upload evidence audit. Integrity is not a passing verdict."""
import hashlib
import json
import os
from pathlib import Path
import re

PIN="7ae6626e44d01d29b11968da28e6debd816f8c06"
PYTHON={"python":67,"diagnostic":13,"faults":38,"evidence":12,"schema":47,
        "mutation":14,"receipt":24,"completion":60,"ancestry":14,"partial":9,
        "interruptions":41,"artifact":24}
def inventory(os_name):
    if os_name=="Linux": prefix="bash"
    elif os_name=="Windows": prefix="powershell"
    else: raise ValueError("Unsupported runner")
    return dict(PYTHON,**{prefix:15, prefix+"2":19,prefix+"3":12,
                          prefix+"4":14,prefix+"5":12,prefix+"6":12})

def strict_object(pairs):
    result={}
    for key,value in pairs:
        if key in result: raise ValueError("Duplicate JSON key")
        result[key]=value
    return result

def read_json(path):
    if not path.is_file() or path.is_symlink():
        raise ValueError("Missing regular evidence file")
    return json.loads(path.read_text(encoding="utf-8"),object_pairs_hook=strict_object)

def verify(root,kind,count,vault,product,run,attempt):
    if type(count) is not int or count<=0: raise ValueError("Invalid expected count")
    if not re.fullmatch(r"[0-9a-f]{40}",vault) or not re.fullmatch(r"[0-9a-f]{40}",product):
        raise ValueError("Invalid revision")
    data=read_json(root/(kind+".json"))
    for key,value in {"kind":kind,"vault_sha":vault,"product_sha":product,
                      "run_id":run,"attempt":attempt}.items():
        if data.get(key)!=value: raise ValueError("Evidence identity mismatch: "+key)
    if type(data.get("expected_count")) is not int or data["expected_count"]!=count:
        raise ValueError("Evidence inventory mismatch")
    ids=data.get("passed_ids")
    if not isinstance(ids,list) or any(not isinstance(x,str) or not x.strip() for x in ids):
        raise ValueError("Invalid test identities")
    if len(set(ids))!=len(ids) or len(ids)>count:
        raise ValueError("Duplicate or excessive test identities")
    log=root/(kind+".log")
    if not log.is_file() or log.is_symlink(): raise ValueError("Missing regular log")
    if hashlib.sha256(log.read_bytes()).hexdigest()!=data.get("log_sha256"):
        raise ValueError("Log digest mismatch")
    code=data.get("exit_code")
    if type(code) is not int: raise ValueError("Invalid exit code")
    if data.get("outcome") not in ("pass","fail"): raise ValueError("Invalid outcome")
    if data["outcome"]=="pass" and (code!=0 or len(ids)!=count):
        raise ValueError("False passing verdict")
    if kind in PYTHON and kind!="python":
        if read_json(root/(kind+"-identities.json"))!=ids:
            raise ValueError("Recorded identities disagree")
    return {"kind":kind,"expected":count,"passed":len(ids),"outcome":data["outcome"]}

def main():
    root=Path(os.environ["RUNNER_TEMP"])/"issue54"
    expected=inventory(os.environ["RUNNER_OS"])
    results=[verify(root,k,n,os.environ["GITHUB_SHA"],PIN,
                    os.environ["GITHUB_RUN_ID"],os.environ["GITHUB_RUN_ATTEMPT"])
             for k,n in expected.items()]
    summary={"vault_sha":os.environ["GITHUB_SHA"],"product_sha":PIN,
             "run_id":os.environ["GITHUB_RUN_ID"],"attempt":os.environ["GITHUB_RUN_ATTEMPT"],
             "expected":sum(x["expected"] for x in results),
             "passed":sum(x["passed"] for x in results),
             "failing_suites":[x["kind"] for x in results if x["outcome"]=="fail"],
             "integrity":"verified-pre-upload","suites":results}
    (root/"integrity.json").write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary),flush=True)

if __name__=="__main__": main()
