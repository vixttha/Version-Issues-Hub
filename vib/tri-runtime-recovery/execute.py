"""Execute actual VIB claim/save/recovery via disposable Git fixture and simulated API.
Frozen contract is separate; Bash and PowerShell independently replay evidence."""
import json,os,subprocess,sys
from pathlib import Path
root=Path(os.environ["GITHUB_WORKSPACE"]);product=root/"product";here=Path(__file__).resolve().parent
sys.path[:0]=[str(product),str(product/"tests")]
from test_contention_recovery import RecoveryTests,REPO
from tools import session,install
contract=json.loads((here/"scenarios.json").read_bytes())
assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=product).decode().strip()==contract["source"]
out=Path(os.environ["RUNNER_TEMP"])/"vib63";out.mkdir(exist_ok=False)
for spec in contract["scenarios"]:
    case=RecoveryTests();case.setUp()
    try:
        api=case.api;initial=case.s["ref"];main=api.ref("main");before=len(api.writes)
        assert api.git("remote")=="" # never a live remote
        req=spec["requests"];mode=spec["mode"];results=[];tickets=[]
        if mode=="conflict":
            case.inject(lambda:session.save(api,case.s,*case.claim(case.s,req[1]),True,issue=req[1]))
            results.append(case.recover(lambda st:case.claim(st,req[0]),req[0],on_recovery_ticket=tickets.append))
        elif mode=="lost":
            original=api.request
            def lose(method,path,body=None):
                if method=="PATCH":
                    assert tickets and tickets[-1]["candidate_sha"]==body["sha"]
                    original(method,path,body)
                    raise install.ApiTransportError("PATCH","git/refs",True)
                return original(method,path,body)
            api.request=lose
            results.append(case.recover(lambda st:case.claim(st,req[0]),req[0],on_recovery_ticket=tickets.append))
            api.request=original
            fresh=session.load(api,REPO);writes=list(api.writes)
            assert session.inspect_operation(api,fresh,tickets[-1])["status"]=="published"
            assert api.writes==writes
        elif mode=="sink":
            def fail(ticket):
                tickets.append(ticket);raise OSError("fixture journal unavailable")
            try:case.recover(lambda st:case.claim(st,req[0]),req[0],on_recovery_ticket=fail)
            except OSError as e:
                assert "fixture journal" in str(e);results.append({"status":"journal_failure"})
            else:raise AssertionError("journal sink accepted")
        else:
            for number in req:
                case.s=session.load(api,REPO)
                results.append(case.recover(lambda st,n=number:case.claim(st,n),number,on_recovery_ticket=tickets.append))
        final=api.ref(install.BRANCH)
        receipt={"schema":1,"source":contract["source"],"run":os.environ["GITHUB_RUN_ID"],"attempt":os.environ["GITHUB_RUN_ATTEMPT"],"runner":os.environ["RUNNER_OS"],"scenario":spec["name"],"initial":initial,"final":final,"main":main,"patches":sum(m=="PATCH" for m,_,_ in api.writes[before:]),"retries":sum(r.get("contention_retries",0) for r in results),"recovered":any(r.get("recovered_response",False) for r in results),"results":results,"tickets":tickets}
        dest=out/spec["name"];dest.mkdir()
        (dest/"receipt.json").write_bytes((json.dumps(receipt,indent=2)+"\n").encode())
        (dest/"pins.txt").write_bytes((initial+"\n"+final+"\n"+main+"\n").encode())
        api.git("bundle","create",str(dest/"objects.bundle"),"refs/heads/"+install.BRANCH,"refs/heads/main")
        assert api.ref("main")==main
        print("Executed",spec["name"],"PATCH",receipt["patches"],"retry",receipt["retries"],flush=True)
    finally:case.doCleanups()
