"""Reconcile eight removed .8 -> .9 extracted call pairs with the exact Git AST."""
import ast, hashlib,json,os,subprocess
from pathlib import Path
root=Path(os.environ["GITHUB_WORKSPACE"]); repo=root/"archive"; out=Path(os.environ["RUNNER_TEMP"])/"independent-vib-audit";out.mkdir(exist_ok=True)
def git(*args):return subprocess.check_output(["git",*args],cwd=repo).decode("utf-8")
def graph(i):
    p=repo/"archives/cumulative-code-graphs"/f"v0.0.0.{i}"
    r=json.loads((p/"receipt.json").read_bytes());raw=(p/"graph.json").read_bytes()
    assert hashlib.sha256(raw).hexdigest()==r["graph_sha256"]
    g=json.loads(raw);assert g["built_at_commit"]==r["source"]
    assert git("rev-parse",r["source"]+"^{tree}").strip()==r["tree"]
    n={x["id"]:x for x in g["nodes"]}
    pairs={(n[e["source"]]["source_file"],n[e["source"]]["label"],n[e["target"]]["source_file"],n[e["target"]]["label"]) for e in g["links"] if e["confidence"]=="EXTRACTED" and e["relation"]=="calls" and n[e["source"]]["source_file"].startswith("tools/") and n[e["target"]]["source_file"].startswith("tools/")}
    return r,pairs
a,x=graph(8);b,y=graph(9);lost=sorted(x-y);assert len(lost)==8 and all(t[:2]==("tools/gate.py","evaluate()") for t in lost)
def function(sha,name,file="tools/gate.py"):
    tree=ast.parse(git("show",sha+":"+file));return next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name==name)
old=function(a["source"],"evaluate");new=function(b["source"],"evaluate_scope");wrapper=function(b["source"],"evaluate")
class Normalize(ast.NodeTransformer):
    def visit_Name(self,node):
        node.id={"validate_policy":"validate","check_test":"verify_test"}.get(node.id,node.id)
        return node
assert ast.dump(ast.Module(body=[Normalize().visit(n) for n in old.body],type_ignores=[]))==ast.dump(ast.Module(body=new.body,type_ignores=[]))
assert ast.dump(ast.Module(body=wrapper.body,type_ignores=[]))==ast.dump(ast.parse("return evaluate_scope(api, target, policy, validate_policy, check_test)"))
standard=function(b["source"],"evaluate","tools/standard.py")
assert any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr=="evaluate_scope" for n in ast.walk(standard))
report={"from":a["source"],"to":b["source"],"removed_pairs":lost,"added_pairs":len(y-x),"classification":"all eight old caller relationships relocated by extraction of evaluate_scope; two injected callbacks; normalized function body AST identical","unchanged_gate_wrapper":True,"standard_advisory_reuses_scope":True}
(out/"historical-09.json").write_bytes((json.dumps(report,indent=2)+"\n").encode())
print("All eight .9 removals reconciled: equivalent normalized body; legacy callback wrapper unchanged")
