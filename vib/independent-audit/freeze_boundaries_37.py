"""Audit-only exact-source controls. No remote API or product state mutation."""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

root = Path(os.environ["GITHUB_WORKSPACE"])
source = "041e187dc1d383082c1a4805e6d4743eec97e535"
canonical = "382714357d68d1883706c51ce3acbf7e7ebb538f"
base = "26e9fe8c019a33c5f84f77a37da70925505204e3"
repo = "vixttha/Version-Issues-Hub"
prefix = "/repos/" + repo
installed = root / "installed"
candidate = root / "candidate"
def head(path):
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=path, text=True).strip()
assert head(installed) == canonical and head(candidate) == source
manifest = json.loads((installed / "vib-install.json").read_bytes())
ledger = json.loads((installed / "ledger/issue-versions.json").read_bytes())
handoff = json.loads((installed / "ledger/handoff.json").read_bytes())
assert manifest["product_branch"] == "main" and handoff["active"]["issue"] == 53 and handoff["active"]["phase"] == "Worker"
assert handoff["active"]["candidate_sha"] is None and handoff["active"]["pull_request"] is None
# Recorded PR identity snapshots; the hypothetical future PR2 head is a positive
# control only, not a claim of integration or authorization.
test_target = """
import json, sys
from unittest.mock import patch
from tools import session, lifecycle
state=json.loads(sys.stdin.read())
source=state.pop("test_source")
base=state.pop("test_base")
rid=state["manifest"]["target_repository_id"]
class API:
    def __init__(self, pr): self.pr=pr; self.reads=[]
    def request(self, method, path, body=None):
        assert method == "GET" and path.endswith("/pulls/"+str(self.pr["number"]))
        self.reads.append(path)
        return self.pr
def pr(n, ref, sha):
    return {"number":n,"base":{"ref":ref,"sha":base,"repo":{"id":rid}},"head":{"sha":sha,"repo":{"id":rid}},"state":"open","merged":False}
def probe(p, expected, allow):
    api=API(p)
    a={"pull_request":p["number"],"candidate_sha":expected}
    try:
        observed=session.get_pr(api,state,a)
    except ValueError:
        assert not allow
    else:
        assert allow and observed["head"]["sha"] == expected
    assert len(api.reads)==1
probe(pr(79,"plan/v0.0.0.1",source),source,False)
probe(pr(2,"main",base),source,False)
probe(pr(2,"main",base),base,True)
probe(pr(2,"main",source),source,True)
with patch.object(session,"load",return_value=state):
    try: lifecycle.idle_state(None,state["manifest"]["target_repository"],state["ref"])
    except ValueError as e: assert "active work" in str(e)
    else: raise AssertionError("active lifecycle accepted")
print(json.dumps({"target_controls":5,"actual_engineering_target_rejected":True,"existing_release_head_not_current_candidate":True,"hypothetical_main_route_only":True,"active_lifecycle_rejected":True}))
"""
state={"prefix":prefix,"ref":canonical,"manifest":manifest,"ledger":ledger,"handoff":handoff,"test_source":source,"test_base":base}
reports={}
for name,path in [("installed",installed),("candidate",candidate)]:
    result=subprocess.run([sys.executable,"-B","-c",test_target],cwd=path,input=json.dumps(state),text=True,capture_output=True,check=True)
    reports[name]=json.loads(result.stdout)
# Real abrupt exit in a child using production recover_save, after flushing
# pending identity and before any candidate save. The Git API is a disposable
# fixture; no credentials, no network. Retained journal must not imply replay.
child = """
import os, sys
from unittest.mock import patch
sys.path.insert(0,"tests")
from test_contention_recovery import RecoveryTests, B
from tools import session
fixture=RecoveryTests()
fixture.setUp()
with patch.object(session,"save",side_effect=lambda *a,**k:os._exit(73)):
    fixture.recover(lambda s:fixture.claim(s,B),B,on_pending_intent=lambda i:session.persist_pending_intent(sys.argv[1],i))
raise AssertionError("exit control not reached")
"""
inspect = """
import json, sys
from pathlib import Path
from tools import session
path=Path(sys.argv[1]); intent=json.loads(path.read_bytes())
class NoAPI:
    def request(self,*a,**k): raise AssertionError("unexpected API call")
before=path.read_bytes()
r=session.inspect_pending(NoAPI(),{"prefix":intent["repository"]},path)
assert r["candidates"]==[] and r["read_only"] is True and r["automatic_replay"] is False
assert r["origin_intent_authenticated"] is False and path.read_bytes()==before
print(json.dumps(r))
"""
with tempfile.TemporaryDirectory() as t:
    path=Path(t)
    child_result=subprocess.run([sys.executable,"-B","-c",child,t],cwd=candidate,capture_output=True,text=True)
    assert child_result.returncode==73,(child_result.returncode,child_result.stderr)
    files=list(path.glob("*.pending.json"))
    assert len(files)==1 and len(list(path.iterdir()))==1
    retained=subprocess.run([sys.executable,"-B","-c",inspect,str(files[0])],cwd=candidate,text=True,capture_output=True,check=True)
    r=json.loads(retained.stdout)
    assert r["status"]=="inspection_only"
    # Model complete loss of host journal, then prove missing evidence is not
    # classified as saved or automatically replayed by the inspector.
    missing=files[0].with_name("lost") / files[0].name
    lost=subprocess.run([sys.executable,"-B","-c",inspect,str(missing)],cwd=candidate,text=True,capture_output=True)
    assert lost.returncode!=0 and "FileNotFoundError" in lost.stderr
report={"source":source,"installed":canonical,"engineering_base":base,"target_controls":reports,"abrupt_exit":73,"pending_retained":True,"candidate_count":0,"read_only":True,"automatic_replay":False,"missing_journal_refused":True,"remote_writes":0,"starvation_freedom":False,"independent_agent_trial":False,"status":"PASS"}
(Path(os.environ["RUNNER_TEMP"])/"freeze-boundaries.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report),flush=True)
