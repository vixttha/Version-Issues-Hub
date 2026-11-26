"""Cross-language evidence verification; not independent product execution."""
import copy,json,os,shutil,subprocess,sys
from pathlib import Path
here=Path(__file__).resolve().parent
work=Path(sys.argv[2]).resolve();work.mkdir(parents=True,exist_ok=True)
report=json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
contract=json.loads((here/"contract.json").read_text(encoding="utf-8"))
def run(cmd,expected=True):
    p=subprocess.run([str(x) for x in cmd],capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=180)
    if (p.returncode==0)!=expected:raise RuntimeError(f"unexpected result {cmd}: {p.returncode} {p.stdout} {p.stderr}")
    return p.stdout.strip()
versions={x:run([x,"--version"]) for x in ("node","dotnet","javac")}
tsc=shutil.which("tsc")
if not tsc:raise RuntimeError("TypeScript compiler unavailable; no compile qualification")
# Windows npm installs the compiler as a .cmd shim; invoke via cmd explicitly.
tc=["cmd","/d","/c",tsc] if os.name=="nt" else [tsc]
versions["tsc"]=run(tc+["--version"])
run(tc+["--noEmit","--strict","--target","ES2022","--module","ESNext",here/"verify.ts"])
# Copy source to temp; no generated binaries or obj paths in the audit checkout.
csdir=work/"csharp";shutil.copytree(here/"csharp",csdir,dirs_exist_ok=True)
run(["dotnet","build",csdir/"Verify.csproj","-o",work/"dotnet"])
run(["javac","-d",work,here/"Verify.java"])
def scalar(v):
    return v if isinstance(v,str) else json.dumps(v,separators=(",",":"))
def projection(r):
    c=r["counts"]
    return "\n".join(["\t".join(map(scalar,[r["source"],r["mode"],c["total"],c["passed"],c["failed"]]))]+["\t".join(map(scalar,[x["boundary"]+"/"+x["case"],x["expected"],x["outcome"],x["pass"]])) for x in r["cases"]])+"\n"
ct=work/"contract.tsv";ct.write_bytes((contract["source"]+"\n"+"\n".join(k+"\t"+v for k,v in contract["cases"].items())+"\n").encode())
variants={"valid":report}
def changed(name,fn):
    x=copy.deepcopy(report);fn(x);variants[name]=x
changed("wrong_sha",lambda x:x.update(source="0"*40))
changed("duplicate",lambda x:x["cases"].__setitem__(1,copy.deepcopy(x["cases"][0])))
changed("omitted",lambda x:x["cases"].pop())
changed("wrong_outcome",lambda x:x["cases"][0].update(outcome="accepted" if x["cases"][0]["outcome"]!="accepted" else "unconfirmed"))
changed("forged_expected",lambda x:x["cases"][0].update(expected="forged",outcome="forged"))
changed("false_pass",lambda x:x["cases"][0].update({"pass":False}))
changed("wrong_count",lambda x:x["counts"].update(total=0))
rows=[]
for name,r in variants.items():
    j=work/(name+".json");j.write_bytes(json.dumps(r,sort_keys=True).encode())
    t=work/(name+".tsv");t.write_bytes(projection(r).encode())
    commands={"javascript":["node",here/"verify.mjs",here/"contract.json",j],"typescript":["node",here/"verify-ts.mjs",here/"contract.json",j],"csharp":["dotnet",work/"dotnet"/"Verify.dll",here/"contract.json",j],"java":["java","-cp",work,"Verify",ct,t]}
    for language,cmd in commands.items():
        run(cmd,expected=name=="valid")
        rows.append({"language":language,"case":name,"expected":"accept" if name=="valid" else "reject"})
(work/"polyglot.json").write_bytes((json.dumps({"source":contract["source"],"results":rows,"versions":versions,"java_scope":"TSV projection, not raw JSON","typescript":"compiler plus runtime checks"},indent=2)+"\n").encode())
print("Cross-language oracle controls",len(rows))
