"""Source-check each inferred edge of .36, preserving the original graph unchanged."""
import ast,json,hashlib,os,subprocess
from pathlib import Path
root=Path(os.environ["GITHUB_WORKSPACE"])
repo=root/"source"
vault=root/"vault"
folder=vault/"archives/code-graphs/v0.0.0.36"
receipt=json.loads((folder/"receipt.json").read_text())
raw=(folder/"graph.json").read_bytes()
assert hashlib.sha256(raw).hexdigest()==receipt["graph_sha256"]
g=json.loads(raw)
assert g["built_at_commit"]==receipt["source"]
nodes={n["id"]:n for n in g["nodes"]}
def source(path):
    return subprocess.check_output(["git","show",receipt["source"]+":"+path],cwd=repo).decode()
def excerpt(path,location):
    n=int(location.removeprefix("L"))
    lines=source(path).splitlines()
    assert 1<=n<=len(lines)
    return n,lines[n-1], "\n".join(lines[max(0,n-3):n+2])
def definition(node):
    path=node["source_file"]; n=int(node["source_location"].removeprefix("L"))
    tree=ast.parse(source(path))
    label=node["label"].strip(".").removesuffix("()")
    assert any(isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef,ast.ClassDef)) and x.name==label and x.lineno==n for x in ast.walk(tree)), (path,n,label)
rows=[]
for e in g["links"]:
    if e["confidence"]!="INFERRED": continue
    a,b=nodes[e["source"]],nodes[e["target"]]
    path=e["source_file"]; line,code,context=excerpt(path,e["source_location"])
    definition(b)
    label=b["label"].strip(".").removesuffix("()")
    rel=e["relation"]
    if rel=="indirect_call" and label=="install" and "patch.object(install," in context.replace(" ",""):
        verdict="rejected_module_not_function"; reason="patch.object receives the imported install module, not the install() function."
    elif rel=="indirect_call" and label=="install" and "patch.object(install," in context.replace(" ", ""):
        raise AssertionError("unreachable")
    elif rel=="indirect_call" and label=="ref" and path=="tests/test_lifecycle.py" and line==109:
        assert "api.read(ref,path)" in context
        verdict="rejected_wrong_target";reason="Lambda calls api.read; ref is a parameter, not GitApi.ref."
    elif rel=="indirect_call" and e.get("context")=="assignment":
        assert label=="race"
        caller=source(path).splitlines()
        assert any("request" in q and "= race" in q.replace("=race","= race") for q in caller[max(0,line-1):line+14])
        verdict="confirmed_callback_assignment";reason="Local race function is assigned as request replacement; not a direct invocation at the anchor."
    elif rel=="indirect_call" and path.startswith("tools/"):
        assert label in context
        verdict="confirmed_callback_reference";reason="Function is passed as an argument; execution depends on receiving API."
    elif rel=="calls":
        assert "."+label+"(" in code.replace(" ","")
        if path=="tests/test_install.py" or path=="tools/live_lifecycle.py":
            assert label=="request" and b["source_file"]=="tools/install.py"
            assert "api = install.GitHub(" in source(path)
        elif path=="tests/test_lifecycle.py":
            assert b["source_file"]==path and "self.api=GitApi(" in source(path)
        elif path=="tests/test_live_acceptance.py":
            assert label=="request" and b["source_file"]=="tools/live_acceptance.py" and "api = live.ReadOnlyGitHub(" in source(path)
        else: raise AssertionError("Unexpected inferred call")
        verdict="confirmed_static_call";reason="Source has the method call and a matching receiver construction and target definition; not runtime trace."
    elif rel=="uses":
        assert label in code
        assert label in source(path)
        verdict="confirmed_symbol_use";reason="Source uses the imported class; not a call-graph certainty."
    else: raise ValueError((path,line,label,rel,context))
    rows.append({"source":e["source"],"target":e["target"],"relation":rel,"source_file":path,"line":line,"source_line":code,"target_file":b["source_file"],"target_location":b["source_location"],"verdict":verdict,"reason":reason})
from collections import Counter
counts=dict(Counter(x["verdict"] for x in rows))
assert len(rows)==51
assert counts=={"rejected_module_not_function":15,"rejected_wrong_target":1,"confirmed_callback_reference":6,"confirmed_callback_assignment":9,"confirmed_static_call":18,"confirmed_symbol_use":2},counts
out=Path(os.environ["RUNNER_TEMP"])/"vib-cumulative-graphs"/"inferred-review-v0.0.0.36.json"
out.write_text(json.dumps({"source":receipt["source"],"graph_sha256":receipt["graph_sha256"],"counts":counts,"relationships":rows,"raw_graph_unchanged":True},indent=2)+"\n")
print(counts)
