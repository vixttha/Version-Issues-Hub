"""Strict repair qualification, not a defect-reproduction PASS. No live API."""
import ast,base64,hashlib,json,os,sys,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
candidate=Path(sys.argv[1]).resolve()
out=Path(sys.argv[2]).resolve()
mode=sys.argv[3]
out.mkdir(parents=True,exist_ok=True)
source=subprocess.check_output(["git","-C",str(candidate),"rev-parse","HEAD"],text=True).strip()
assert source == ({"before":"b68796db12681fe4d43b562c8647deca38fa819c","after":"041e187dc1d383082c1a4805e6d4743eec97e535"}[mode])
sys.path[:0]=[str(candidate),str(candidate/"tests")]
from tools import install,lifecycle,session,gate,standard
from test_contention_recovery import RecoveryTests,B,REPO
prefix="/repos/example/test";sha="a"*40;tree="b"*40
state={"prefix":prefix,"manifest":{"product_branch":"main","target_repository_id":1}}
active={"pull_request":2,"candidate_sha":sha}
policy={"repository_id":1,"head_sha":sha,"merge_sha":tree,"base_sha":"c"*40,"pull_request":2}
rows=[]
def record(boundary,case,actual,wanted):
    rows.append({"boundary":boundary,"case":case,"outcome":actual,"expected":wanted,"pass":actual==wanted})
def probe(name,fn,payloads,expected=None):
    for case,values in payloads.items():
        api=Mock();api.request.side_effect=values
        try:
            fn(api)
        except ValueError:
            actual="controlled_rejection"
        except Exception as exc:
            actual=type(exc).__name__
        else:
            actual="accepted"
        assert all(c.args[0]=="GET" for c in api.request.call_args_list)
        record(name,case,actual,"accepted" if case.startswith("valid") else "controlled_rejection")
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

ref={"ref":"refs/heads/main","object":{"type":"commit","sha":sha}}
probe("install.read_ref",lambda api:install.read_ref(api,prefix,"main"),
    {"null":[None],"array":[[]],"string":["bad"],"missing_object":[{"ref":ref["ref"]}],
    "null_object":[{**ref,"object":None}],"list_object":[{**ref,"object":[]}],
    "missing_type":[{**ref,"object":{"sha":sha}}],"missing_sha":[{**ref,"object":{"type":"commit"}}],
    "wrong_ref":[{**ref,"ref":"refs/heads/other"}],"wrong_type":[{**ref,"object":{"type":"tag","sha":sha}}],
    "bad_sha":[{**ref,"object":{"type":"commit","sha":"bad"}}],"valid":[ref]})
probe("install.wait_ref",lambda api:install.wait_ref(api,prefix,"main",sha),
    {"null":[None],"array":[[]],"string":["bad"],"valid":[ref]})
probe("install.read_text.extra",lambda api:install.read_text(api,prefix,"file",sha),
    {"wrong_path":[{**item,"path":"different"}],"wrong_type":[{**item,"type":"symlink"}],
    "wrong_encoding":[{**item,"encoding":"utf8"}],"invalid_utf8":[{**item,"content":"/w==","sha":hashlib.sha1(b"blob 1\0\xff").hexdigest()}]})
probe("lifecycle.tree_entries.extra",lambda api:lifecycle.tree_entries(api,prefix,sha),
    {"wrong_mode":[commit,{**valid_tree,"tree":[{**valid_tree["tree"][0],"mode":"160000"}]}],
    "parent_path":[commit,{**valid_tree,"tree":[{**valid_tree["tree"][0],"path":"../file"}]}],
    "absolute_path":[commit,{**valid_tree,"tree":[{**valid_tree["tree"][0],"path":"/file"}]}],
    "empty_path":[commit,{**valid_tree,"tree":[{**valid_tree["tree"][0],"path":""}]}]})
probe("session.get_issue.extra",lambda api:session.get_issue(api,state,1),
    {name:[{"number":v,"state":"open"}] for name,v in [("float",1.0),("string","1"),("zero",0),("negative",-1),("null_id",None)]})
probe("gate.exact_collection.extra",lambda api:gate.exact_collection(api,prefix,"check_runs"),
    {"row_string":[{"total_count":1,"check_runs":["x"]}],"row_array":[{"total_count":1,"check_runs":[[]]}],
    "negative_count":[{"total_count":-1,"check_runs":[]}],"float_count":[{"total_count":1.0,"check_runs":[{}]}],
    "valid_empty":[{"total_count":0,"check_runs":[]}]})
class Origin(RecoveryTests):
    def test_origin_matrix(self):
        with tempfile.TemporaryDirectory() as folder:
            paths=[]
            result=self.recover(lambda s:self.claim(s,B),B,
              on_pending_intent=lambda x:paths.append(session.persist_pending_intent(folder,x)),
              on_recovery_ticket=lambda x:session.persist_recovery_ticket(folder,x))
            fresh=session.load(self.api,REPO)
            original=json.loads(paths[0].read_bytes())
            before=list(self.api.writes)
            request=self.api.request
            def real_compare(method,path,body=None):
                if "/compare/" not in path:
                    return request(method,path,body)
                left,right=path.rsplit("/",1)[1].split("...")
                try:
                    common=self.api.git("merge-base",left,right)
                    ahead=int(self.api.git("rev-list","--count",left+".."+right))
                    behind=int(self.api.git("rev-list","--count",right+".."+left))
                except subprocess.CalledProcessError:
                    raise install.ApiError(404) from None
                return {"status":"ahead" if ahead and not behind else "behind" if behind and not ahead else "identical" if not ahead and not behind else "diverged",
                        "ahead_by":ahead,"behind_by":behind,"base_commit":{"sha":left},"merge_base_commit":{"sha":common}}
            for name,origin,wanted in [("valid_parent",original["initial_sha"],"published"),("descendant",result["installed_sha"],"unconfirmed"),("nonexistent","0"*40,"unconfirmed")]:
                paths[0].write_text(json.dumps({**original,"initial_sha":origin}),encoding="utf-8")
                with patch.object(self.api,"request",side_effect=real_compare):
                    observed=session.inspect_pending(self.api,fresh,paths[0])
                actual=observed["candidates"][0]["status"]
                if mode=="after":
                    self.assertFalse(observed["origin_intent_authenticated"])
                    self.assertEqual(observed["candidates"][0]["origin_ancestry_verified"],wanted=="published")
                self.assertFalse(observed["automatic_replay"])
                record("session.inspect_pending",name,actual,wanted)
            self.assertEqual(self.api.writes,before)
suite=unittest.TestSuite([Origin("test_origin_matrix")])
result=unittest.TextTestRunner(verbosity=2).run(suite)
assert result.wasSuccessful(), "origin harness failed; not a qualification outcome"
assert len({(r["boundary"],r["case"]) for r in rows})==len(rows)
inventory=[]
for f in sorted((candidate/"tests").glob("test_*.py")):
    for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
        if isinstance(n,ast.FunctionDef) and n.name.startswith("test_"):
            inventory.append({"file":f.name,"method":n.name,"line":n.lineno})
report={"source":source,"mode":mode,"cases":rows,"native_test_methods":inventory,"counts":{"total":len(rows),"passed":sum(r["pass"] for r in rows),"failed":sum(not r["pass"] for r in rows)}}
(out/"report.json").write_bytes((json.dumps(report,sort_keys=True,indent=2)+"\n").encode())
print(report["counts"],flush=True)
if mode=="before":
    assert all(not next(r["pass"] for r in rows if r["boundary"]==b and r["case"]==c) for b,c in [
        ("session.inspect_pending","descendant"),("session.inspect_pending","nonexistent"),("install.read_ref","null"),
        ("install.read_text","null_content"),("lifecycle.tree_entries","invalid_leaf_sha"),("session.get_issue","bool_number"),
        ("gate.exact_collection","null_row"),("standard.check_pr_run","malformed_prs")])
else:
    assert all(r["pass"] for r in rows), [(r["boundary"],r["case"],r["outcome"]) for r in rows if not r["pass"]]
