"""Single-source tri-runtime transaction experiment. No real repository writes."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

PIN="5a6074d77ec37823f81c6d7ebb1f4593d969cd71"
PRODUCT=Path(os.environ["VIB_CHECKOUT"]).resolve()
VAULT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(PRODUCT))
from tools import checkpoint,lifecycle

BASH=r'''
set -euo pipefail
export LC_ALL=C
case "$1" in
worker)
  # Both native runtimes attempt the SAME expected-old revision.
  if git -C repo update-ref refs/heads/vib "$2" "$3" 2>bash-write.err; then
    echo WIN
  else
    cat bash-write.err >&2
    grep -qi 'cannot lock ref' bash-write.err || exit 3
    echo CONFLICT
    exit 2
  fi
  ;;
verify)
  base=$2; first=$3; final=$4; main=$5
  [[ $(git -C repo rev-parse refs/heads/main) == "$main" ]] || { echo REJECT-main; exit 21; }
  [[ $(git -C repo rev-parse refs/heads/vib) == "$final" ]] || { echo REJECT-ref; exit 21; }
  [[ $(git -C repo show -s --format=%P "$first") == "$base" ]] || { echo REJECT-parent; exit 21; }
  if [[ $first != "$final" ]]; then
    [[ $(git -C repo show -s --format=%P "$final") == "$first" ]] || { echo REJECT-parent; exit 21; }
  fi
  git -C repo cat-file blob "$final:ledger.json" > observed.bin
  cmp -s observed.bin ledger.json || { echo REJECT-bytes; exit 21; }
  blob=$(git -C repo hash-object --no-filters observed.bin)
  [[ $blob == "$(git -C repo rev-parse "$final:ledger.json")" ]] || { echo REJECT-blob; exit 21; }
  digest=$(sha256sum observed.bin | cut -d' ' -f1)
  echo "VERIFIED $blob $digest"
  ;;
*) exit 9;;
esac
'''
POWERSHELL=r'''
param([string]$Mode,[string]$New,[string]$Old)
$ErrorActionPreference='Stop'
$PSNativeCommandUseErrorActionPreference=$false
if($Mode -eq 'worker'){
    $out=& git -C repo update-ref refs/heads/vib $New $Old 2>&1
    $rc=$LASTEXITCODE
    if($rc -eq 0){Write-Output WIN;exit 0}
    $message=($out|Out-String)
    [Console]::Error.WriteLine($message)
    if($message -notmatch 'cannot lock ref'){exit 3}
    Write-Output CONFLICT
    exit 2
}
if($Mode -ne 'verify'){exit 9}
function Reject([string]$why){Write-Output "REJECT-$why";exit 22}
# Independent model: never import VIB or invoke Python.
$spec=Get-Content -LiteralPath 'scenario.json' -Raw -Encoding utf8|ConvertFrom-Json -AsHashtable
$actual=Get-Content -LiteralPath 'ledger.json' -Raw -Encoding utf8|ConvertFrom-Json -AsHashtable
$rows=[System.Collections.Generic.List[object]]::new()
foreach($row in $spec.initial.issues){$rows.Add($row)}
foreach($op in $spec.operations){
    $existing=@($rows|Where-Object {$_.issue -eq $op.issue})
    if($existing.Count -gt 0){
        if($existing.Count -ne 1 -or !$existing[0].version.StartsWith($op.line+'.',[StringComparison]::Ordinal)){Reject 'model'}
        continue
    }
    $max=0
    foreach($r in $rows){
        if($r.version.StartsWith($op.line+'.',[StringComparison]::Ordinal)){
            $value=[int]($r.version.Split('.')[-1])
            if($value -gt $max){$max=$value}
        }
    }
    $rows.Add(@{issue=$op.issue;version=($op.line+'.'+($max+1));state='assigned';acceptance=@($op.criteria)})
}
if($actual.schema_version -ne 1 -or $actual.repository -cne $spec.initial.repository -or $actual.Count -ne 3){Reject 'schema'}
if($actual.issues.Count -ne $rows.Count){Reject 'count'}
$seen=[System.Collections.Generic.HashSet[long]]::new()
foreach($r in $actual.issues){if(!$seen.Add([long]$r.issue)){Reject 'duplicate'}}
foreach($expected in $rows){
    $matching=@($actual.issues|Where-Object {$_.issue -eq $expected.issue})
    if($matching.Count -ne 1){Reject 'identity'}
    $r=$matching[0]
    if($r.Count -ne 4 -or $r.version -cne $expected.version -or $r.state -cne $expected.state){Reject 'state'}
    if($r.acceptance.Count -ne $expected.acceptance.Count){Reject 'criteria'}
    for($i=0;$i -lt $r.acceptance.Count;$i++){
        if($r.acceptance[$i] -cne $expected.acceptance[$i]){Reject 'criteria'}
    }
}
$raw=[IO.File]::ReadAllBytes((Join-Path (Get-Location) 'ledger.json'))
$header=[Text.Encoding]::ASCII.GetBytes("blob $($raw.Length)"+[char]0)
$blob=[Convert]::ToHexString([Security.Cryptography.SHA1]::HashData([byte[]]($header+$raw))).ToLowerInvariant()
$digest=(Get-FileHash -LiteralPath 'ledger.json' -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Output "VERIFIED $blob $digest"
'''
def need(condition,message):
    if not condition:raise RuntimeError(message)
def head(path):
    return subprocess.check_output(["git","-C",str(path),"rev-parse","HEAD"],text=True).strip()
def clean(path):
    return not subprocess.check_output(["git","-C",str(path),"status","--porcelain","--untracked-files=all"])
def git(root,*args,data=None):
    return subprocess.run(["git","-C",str(root/"repo"),*args],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True,timeout=20).stdout
def oid(root,*args):return git(root,*args).decode("ascii").strip()
def commit(root,ledger,parent=None):
    path=root/"staged.json"
    checkpoint.write_json(path,ledger)
    blob=oid(root,"hash-object","-w","--no-filters",str(path))
    tree=git(root,"mktree",data=("100644 blob "+blob+"\tledger.json\n").encode("ascii")).decode().strip()
    return oid(root,"commit-tree",tree,*((["-p",parent]) if parent else []),"-m","synthetic ledger")
def state(root,revision):
    return checkpoint.parse_json(git(root,"show",revision+":ledger.json").decode("utf-8"))
def candidate(root,old,op):
    before=state(root,old);after=copy.deepcopy(before)
    version,new=checkpoint.register(after,op["issue"],op["line"],op["criteria"])
    checkpoint.check_history(after,before)
    if not new:return old,version
    return commit(root,after,old),version
def bash_path():
    if os.name!="nt":
        return shutil.which("bash")
    gitexe=Path(shutil.which("git") or "").resolve()
    for path in (gitexe.parents[1]/"bin/bash.exe",Path(os.environ.get("ProgramFiles","C:/Program Files"))/"Git/bin/bash.exe"):
        if path.is_file():return str(path)
    raise RuntimeError("Git for Windows Bash not found; refusing WSL fallback")
def process(cmd,root):
    return subprocess.run(cmd,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=30)
def receipt(result):
    return {"exit_code":result.returncode,"stdout":result.stdout.decode("utf-8",errors="replace"),"stderr":result.stderr.decode("utf-8",errors="replace")}
def main():
    need(head(PRODUCT)==PIN and head(VAULT)==os.environ["GITHUB_SHA"],"Exact checkout")
    need(clean(PRODUCT) and clean(VAULT),"Dirty input")
    bash=bash_path();pwsh=shutil.which("pwsh")
    need(bool(bash and pwsh),"All three runtimes mandatory")
    out=Path(os.environ["RUNNER_TEMP"])/"tri-runtime"
    out.mkdir()
    # Isolate Git configuration and credentials. No remote is ever created.
    config=out/"empty.config";config.write_bytes(b"")
    os.environ.update(GIT_CONFIG_NOSYSTEM="1",GIT_CONFIG_GLOBAL=str(config),GIT_AUTHOR_NAME="fixture",GIT_AUTHOR_EMAIL="fixture@example.invalid",GIT_COMMITTER_NAME="fixture",GIT_COMMITTER_EMAIL="fixture@example.invalid",GH_TOKEN="",GITHUB_TOKEN="")
    rows=[]
    for name,mode,duplicate in [("bash-first","A",False),("powershell-first","B",False),("concurrent-distinct","race",False),("concurrent-idempotent","race",True)]:
        with tempfile.TemporaryDirectory(prefix="tri runtime [vib] ") as temp:
            root=Path(temp)
            (root/"worker.sh").write_text(BASH,encoding="utf-8",newline="\n")
            (root/"worker.ps1").write_text(POWERSHELL,encoding="utf-8",newline="\n")
            subprocess.run(["git","init","--bare","--object-format=sha1","-q",str(root/"repo")],check=True,timeout=20)
            initial={"schema_version":1,"repository":"example/product","issues":[{"issue":7,"version":"v1.0.0.9","state":"integrated","acceptance":["preserve"]}]}
            base=commit(root,initial)
            oid(root,"update-ref","refs/heads/main",base)
            oid(root,"update-ref","refs/heads/vib",base)
            ops=[{"issue":101,"line":"v1.0.0","criteria":["Unicode café 水","literal $ [ ]"]},{"issue":101 if duplicate else 102,"line":"v1.0.0","criteria":["Unicode café 水","literal $ [ ]"] if duplicate else ["CRLF\r\nand LF\n","another criterion"]}]
            a,_=candidate(root,base,ops[0]);b,_=candidate(root,base,ops[1])
            # Idempotent operations may generate identical commits, so use a
            # different commit message for the second proposal while retaining bytes.
            if a==b:
                tree=oid(root,"rev-parse",b+"^{tree}")
                b=oid(root,"commit-tree",tree,"-p",base,"-m","independent proposal")
            acmd=[bash,"--noprofile","--norc","worker.sh","worker",a,base]
            bcmd=[pwsh,"-NoProfile","-NonInteractive","-File","worker.ps1","worker",b,base]
            if mode=="A":ar=process(acmd,root);br=process(bcmd,root)
            elif mode=="B":br=process(bcmd,root);ar=process(acmd,root)
            else:
                pa=subprocess.Popen(acmd,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                pb=subprocess.Popen(bcmd,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                try:
                    ao,ae=pa.communicate(timeout=30);bo,be=pb.communicate(timeout=30)
                    ar=subprocess.CompletedProcess(acmd,pa.returncode,ao,ae)
                    br=subprocess.CompletedProcess(bcmd,pb.returncode,bo,be)
                finally:
                    for child in (pa,pb):
                        if child.poll() is None:child.kill();child.communicate()
            need(sorted([ar.returncode,br.returncode])==[0,2],"Exactly one publisher and one conflict: "+str([receipt(ar),receipt(br)]))
            winner=0 if ar.returncode==0 else 1
            need(mode=="race" or winner==(0 if mode=="A" else 1),"Deterministic schedule")
            first=(a,b)[winner]
            need(oid(root,"rev-parse","refs/heads/vib")==first,"Winner readback")
            # Explicit reconciliation after conflict; no repeat of stale commit.
            final,version=candidate(root,first,ops[1-winner])
            if final!=first:oid(root,"update-ref","refs/heads/vib",final,first)
            need((final==first)==duplicate,"Idempotent reconciliation")
            raw=git(root,"show",final+":ledger.json")
            (root/"ledger.json").write_bytes(raw)
            checkpoint.write_json(root/"scenario.json",{"initial":initial,"operations":[ops[winner],ops[1-winner]]})
            final_state=checkpoint.parse_json(raw.decode("utf-8"))
            checkpoint.check_history(final_state,initial)
            need(len(checkpoint.bindings(final_state))==(2 if duplicate else 3),"Expected final bindings")
            expected="VERIFIED "+lifecycle.blob_id(raw.decode("utf-8"))+" "+lifecycle.digest_files({"ledger":raw.decode("utf-8")})["ledger"]
            ba=[bash,"--noprofile","--norc","worker.sh","verify",base,first,final,base]
            ps=[pwsh,"-NoProfile","-NonInteractive","-File","worker.ps1","verify"]
            bv=process(ba,root);pv=process(ps,root)
            for r in (bv,pv):need(r.returncode==0 and receipt(r)["stdout"].strip()==expected,"Independent oracle disagreement "+str(receipt(r)))
            # Fault injection: same semantic ledger with changed raw bytes.
            (root/"ledger.json").write_bytes(raw+b"\n")
            corrupt=process(ba,root)
            need(corrupt.returncode==21 and "REJECT-bytes" in receipt(corrupt)["stdout"],"Bash byte oracle failed to reject")
            # Fault injection: valid JSON but illegal reassignment.
            altered=copy.deepcopy(final_state);altered["issues"][-1]["version"]="v1.0.0.999"
            checkpoint.write_json(root/"ledger.json",altered)
            semantic=process(ps,root)
            need(semantic.returncode==22 and "REJECT-state" in receipt(semantic)["stdout"],"PowerShell model failed to reject")
            try:checkpoint.check_history(altered,final_state)
            except ValueError:pass
            else:raise RuntimeError("Python history guard missed reassignment")
            (root/"ledger.json").write_bytes(raw)
            need(oid(root,"rev-parse","refs/heads/main")==base,"Product branch changed")
            row={"scenario":name,"winner":["Bash","PowerShell"][winner],"base":base,"first":first,"final":final,"binding_count":len(final_state["issues"]),"reconciled_version":version,"idempotent":duplicate,"publish":[receipt(ar),receipt(br)],"bash_oracle":receipt(bv),"powershell_oracle":receipt(pv),"byte_tamper":receipt(corrupt),"semantic_tamper":receipt(semantic),"python_history_tamper":"rejected","verdict":"pass"}
            rows.append(row);print("TRI_RUNTIME "+json.dumps(row,ensure_ascii=True),flush=True)
    need(clean(PRODUCT) and clean(VAULT) and head(PRODUCT)==PIN and head(VAULT)==os.environ["GITHUB_SHA"],"Checkout drift")
    report={"vault_sha":head(VAULT),"product_sha":PIN,"run":os.environ["GITHUB_RUN_ID"],"attempt":os.environ["GITHUB_RUN_ATTEMPT"],"os":os.environ["RUNNER_OS"],"scenarios":rows,"expected":4,"passed":len(rows)}
    checkpoint.write_json(out/"report.json",report)
    print("TRI_RUNTIME_SUMMARY "+json.dumps({"passed":len(rows),"expected":4,"os":report["os"]}),flush=True)
if __name__=="__main__":main()
