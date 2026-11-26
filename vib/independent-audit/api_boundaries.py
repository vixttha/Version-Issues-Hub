"""Read-only fault injection on real candidate functions, no network or live writes."""
import ast,base64,hashlib,json,os,sys
from pathlib import Path
from unittest.mock import Mock
root=Path(os.environ["GITHUB_WORKSPACE"]);sys.path.insert(0,str(root/"candidate"))
from tools import install,lifecycle,session,gate,standard
out=Path(os.environ["RUNNER_TEMP"])/"independent-vib-audit";out.mkdir(exist_ok=True)
prefix="/repos/example/test";sha="a"*40;tree="b"*40
state={"prefix":prefix,"manifest":{"product_branch":"main","target_repository_id":1}}
active={"pull_request":2,"candidate_sha":sha}
policy={"repository_id":1,"head_sha":sha,"merge_sha":tree,"base_sha":"c"*40,"pull_request":2}
rows=[]
def probe(name,fn,payloads,expected):
    for case,values in payloads.items():
        api=Mock();api.request.side_effect=values
        try:
            value=fn(api)
        except (ValueError,TypeError,AttributeError,KeyError,install.ApiError) as exc:
            actual=type(exc).__name__
        else:actual="accepted"
        assert all(c.args[0]=="GET" for c in api.request.call_args_list)
        assert actual==expected[case],(name,case,actual,expected[case])
        rows.append({"boundary":name,"case":case,"outcome":actual})
raw=b"hello\n";blob=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
item={"type":"file","encoding":"base64","path":"file","content":base64.b64encode(raw).decode(),"sha":blob}
probe("install.read_text",lambda api:install.read_text(api,prefix,"file",sha),
      {"null":[None],"array":[[]],"missing_content":[{k:v for k,v in item.items() if k!="content"}],"null_content":[{**item,"content":None}],"numeric_content":[{**item,"content":1}],"invalid_base64":[{**item,"content":"!"}],"wrong_blob":[{**item,"sha":sha}],"valid":[item]},
      {"null":"AttributeError","array":"AttributeError","missing_content":"KeyError","null_content":"AttributeError","numeric_content":"AttributeError","invalid_base64":"Error","wrong_blob":"ValueError","valid":"accepted"})
commit={"sha":sha,"tree":{"sha":tree}}
valid_tree={"sha":tree,"truncated":False,"tree":[{"path":"file","type":"blob","mode":"100644","sha":blob}]}
probe("lifecycle.tree_entries",lambda api:lifecycle.tree_entries(api,prefix,sha),
      {"null_commit":[None],"missing_tree":[{"sha":sha}],"null_tree":[{**commit,"tree":None}],"null_result":[commit,None],"missing_entries":[commit,{k:v for k,v in valid_tree.items() if k!="tree"}],"null_entry":[commit,{**valid_tree,"tree":[None]}],"truncated":[commit,{**valid_tree,"truncated":True}],"duplicate":[commit,{**valid_tree,"tree":valid_tree["tree"]*2}],"invalid_leaf_sha":[commit,{**valid_tree,"tree":[{**valid_tree["tree"][0],"sha":"bad"}]}],"invalid_leaf_type":[commit,{**valid_tree,"tree":[{**valid_tree["tree"][0],"type":"garbage"}]}],"valid":[commit,valid_tree]},
      {"null_commit":"AttributeError","missing_tree":"KeyError","null_tree":"TypeError","null_result":"AttributeError","missing_entries":"KeyError","null_entry":"TypeError","truncated":"ValueError","duplicate":"ValueError","invalid_leaf_sha":"accepted","invalid_leaf_type":"accepted","valid":"accepted"})
probe("session.get_issue",lambda api:session.get_issue(api,state,1),
      {"null":[None],"array":[[]],"bool_number":[{"number":True}],"pr":[{"number":1,"pull_request":{}}],"wrong_number":[{"number":2}],"valid":[{"number":1,"state":"open"}]},
      {"null":"AttributeError","array":"AttributeError","bool_number":"accepted","pr":"ValueError","wrong_number":"ValueError","valid":"accepted"})
pr={"number":2,"base":{"ref":"main","repo":{"id":1}},"head":{"sha":sha},"state":"open","merged":False}
probe("session.require_open_pr",lambda api:session.require_open_pr(api,state,active),
      {"null":[None],"missing_base":[{"number":2}],"null_repo":[{**pr,"base":{"ref":"main","repo":None}}],"bool_repository":[{**pr,"base":{"ref":"main","repo":{"id":True}}}],"closed":[{**pr,"state":"closed"}],"valid":[pr]},
      {"null":"AttributeError","missing_base":"KeyError","null_repo":"TypeError","bool_repository":"accepted","closed":"ValueError","valid":"accepted"})
probe("gate.check_ancestry",lambda api:gate.check_ancestry(api,prefix,sha,tree),
      {"null":[None],"missing_merge_base":[{"status":"ahead"}],"null_merge_base":[{"status":"ahead","merge_base_commit":None}],"behind":[{"status":"behind"}],"valid":[{"status":"ahead","merge_base_commit":{"sha":sha}}]},
      {"null":"AttributeError","missing_merge_base":"KeyError","null_merge_base":"TypeError","behind":"ValueError","valid":"accepted"})
probe("gate.exact_collection",lambda api:gate.exact_collection(api,prefix,"check_runs"),
      {"null":[None],"bool_count":[{"total_count":True,"check_runs":[{}]}],"truncated":[{"total_count":2,"check_runs":[{}]}],"null_row":[{"total_count":1,"check_runs":[None]}],"valid":[{"total_count":1,"check_runs":[{}]}]},
      {"null":"ValueError","bool_count":"ValueError","truncated":"ValueError","null_row":"accepted","valid":"accepted"})
run={"id":1,"run_attempt":1,"repository":{"id":1},"event":"pull_request","head_sha":tree,"status":"completed","conclusion":"success","pull_requests":[]}
probe("standard.check_pr_run",lambda api:standard.check_pr_run(api.request("GET",prefix),policy,1,1),
      {"null":[None],"bool_id":[{**run,"id":True}],"bool_attempt":[{**run,"run_attempt":True}],"bool_repo":[{**run,"repository":{"id":True}}],"malformed_prs":[{**run,"pull_requests":[None]}],"wrong_event":[{**run,"event":"push"}],"valid":[run]},
      {"null":"AttributeError","bool_id":"accepted","bool_attempt":"accepted","bool_repo":"accepted","malformed_prs":"AttributeError","wrong_event":"ValueError","valid":"accepted"})
sites=[]
for file in sorted((root/"candidate/tools").glob("*.py")):
    t=ast.parse(file.read_text(encoding="utf-8"))
    for n in ast.walk(t):
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=="request":
            sites.append({"file":file.name,"line":n.lineno,"receiver":ast.unparse(n.func.value),"method":ast.unparse(n.args[0]) if n.args else "dynamic"})
report={"source":"b68796db12681fe4d43b562c8647deca38fa819c","cases":rows,"request_sites":sorted(sites,key=lambda x:(x["file"],x["line"])),"scope":"diagnostic expectations, no mutation; not acceptance; accepted malformed values are local boundary observations, not proven publication bypasses"}
(out/"api-boundaries.json").write_bytes((json.dumps(report,indent=2)+"\n").encode())
print("API diagnostic cases",len(rows),"request call sites",len(sites),flush=True)
