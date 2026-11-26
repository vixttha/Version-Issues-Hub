"""All remaining removed pairs and inferred occurrences, immutable source audit."""
import ast,collections,hashlib,importlib.util,json,os,subprocess
from pathlib import Path
root=Path(os.environ["GITHUB_WORKSPACE"]);repo=root/"archive";arc=repo/"archives";out=Path(os.environ["RUNNER_TEMP"])/"independent-vib-audit";out.mkdir(exist_ok=True)
def git(*args):return subprocess.check_output(["git",*args],cwd=repo).decode("utf-8").strip()
spec=importlib.util.spec_from_file_location("review",repo/"tools/audit-inferred-graphs.py");review=importlib.util.module_from_spec(spec);spec.loader.exec_module(review)
def pairs(g):
    n={x["id"]:x for x in g["nodes"]}
    return {(n[e["source"]]["source_file"],n[e["source"]]["label"],n[e["target"]]["source_file"],n[e["target"]]["label"]) for e in g["links"] if e["confidence"]=="EXTRACTED" and e["relation"]=="calls" and n[e["source"]]["source_file"].startswith("tools/") and n[e["target"]]["source_file"].startswith("tools/")}
def functions(sha,path):
    t=ast.parse(git("show",sha+":"+path))
    return {n.name:n for n in ast.walk(t) if isinstance(n,ast.FunctionDef)}
def call_names(n):
    return {c.func.id if isinstance(c.func,ast.Name) else c.func.attr for c in ast.walk(n) if isinstance(c,ast.Call) and isinstance(c.func,(ast.Name,ast.Attribute))}
changes=[]; inferred=[]; previous=None
for scope,folder in (("fix","code-graphs"),("cumulative","cumulative-code-graphs")):
    idx=json.loads((arc/folder/"index.json").read_bytes())
    assert len(idx["results"])==36
    for r in idx["results"]:
        p=arc/folder/r["version"]; raw=(p/"graph.json").read_bytes()
        assert hashlib.sha256(raw).hexdigest()==r["graph_sha256"] and json.loads((p/"receipt.json").read_bytes())==r
        g=json.loads(raw);assert g["built_at_commit"]==r["source"] and git("rev-parse",r["source"]+"^{tree}")==r["tree"]
        nodes={n["id"]:n for n in g["nodes"]}
        for e in g["links"]:
            if e["confidence"]!="INFERRED":continue
            target=nodes[e["target"]]; verdict=review.classify(repo,r["source"],e,target)
            inferred.append({"scope":scope,"version":r["version"],"source":r["source"],"edge":e,"target":target,**verdict})
        if scope=="cumulative":
            curr=pairs(g)
            if previous:
                old,old_pairs=previous
                for path,caller,tpath,callee in sorted(old_pairs-curr):
                    name=caller.removesuffix("()");targetname=callee.removesuffix("()")
                    before=functions(old["source"],path)
                    try: after=functions(r["source"],path)
                    except subprocess.CalledProcessError:after={}
                    changes.append({"from":old["version"],"to":r["version"],"old_source":old["source"],"source":r["source"],"caller":caller,"callee":callee,"path":path,"target_path":tpath,"old_body":ast.unparse(before[name]) if name in before else None,"new_body":ast.unparse(after[name]) if name in after else None,"new_callers_same_file":sorted(k for k,v in after.items() if targetname in call_names(v)),"disposition":"source evidence; manual semantic review required"})
            previous=(r,curr)
assert len(changes)==17
counts=dict(sorted(collections.Counter(i["verdict"] for i in inferred).items()))
(out/"historical-removals.json").write_bytes((json.dumps(changes,indent=2)+"\n").encode())
(out/"inferred-review.json").write_bytes((json.dumps({"counts":counts,"occurrences":inferred,"policy":"replayed existing lexical rules; not runtime proof"},indent=2)+"\n").encode())
print("Historical removals",len(changes),"inferred counts",counts,flush=True)
