"""Run targeted offline historical suites at exact cumulative graph source revisions."""
import json,os,re,subprocess,sys,tempfile
from pathlib import Path
root=Path(os.environ["GITHUB_WORKSPACE"]);repo=root/"archive";out=Path(os.environ["RUNNER_TEMP"])/"independent-vib-audit"
plans={2:["test_checkpoint.py"],8:["test_gate.py"],19:["test_acceptance_snapshot.py"],20:["test_pilot_refs.py","test_session.py"],33:["test_self_use_preflight.py"]}
rows=[]
with tempfile.TemporaryDirectory(prefix="historical-vib-") as t:
    for version,tests in plans.items():
        r=json.loads((repo/"archives/cumulative-code-graphs"/f"v0.0.0.{version}"/"receipt.json").read_bytes());sha=r["source"];dst=Path(t)/f"v{version}"
        subprocess.run(["git","-C",str(repo),"worktree","add","--detach",str(dst),sha],check=True,capture_output=True)
        try:
            for pattern in tests:
                assert (dst/"tests"/pattern).is_file()
                result=subprocess.run([sys.executable,"-B","-m","unittest","discover","-s","tests","-p",pattern,"-v"],cwd=dst,capture_output=True,encoding="utf-8",timeout=180,env={**os.environ,"GH_TOKEN":"","GITHUB_TOKEN":""})
                print(result.stderr,flush=True)
                m=re.search(r"Ran (\d+) tests?",result.stderr)
                rows.append({"version":r["version"],"source":sha,"suite":pattern,"tests":int(m[1]) if m else 0,"exit_code":result.returncode})
        finally:subprocess.run(["git","-C",str(repo),"worktree","remove","--force",str(dst)],check=True,capture_output=True)
(out/"historical-tests.json").write_bytes((json.dumps(rows,indent=2)+"\n").encode())
assert all(r["exit_code"]==0 and r["tests"]>0 for r in rows),rows
print("Historical selected test executions",sum(r["tests"] for r in rows),flush=True)
