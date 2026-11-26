"""Second-pass inferred edge review. Exact source anchors; conservative lexical evidence.
No mutation of original graphs; class constructor evidence does not prove runtime dispatch."""
import ast,collections,importlib.util,json,os
from pathlib import Path
root=Path(os.environ["GITHUB_WORKSPACE"]);repo=root/"archive";out=Path(os.environ["RUNNER_TEMP"])/"independent-vib-audit"
spec=importlib.util.spec_from_file_location("review",repo/"tools/audit-inferred-graphs.py");review=importlib.util.module_from_spec(spec);spec.loader.exec_module(review)
rows=json.loads((out/"inferred-review.json").read_bytes())["occurrences"]
def lexical_import(node,name,parents,expected_module,expected_name):
    kind,line=review.resolve_name(node,name,parents)
    if kind!="import" or line is None or line>=node.lineno:return False
    return any(isinstance(n,ast.ImportFrom) and n.level==0 and n.module==expected_module and n.lineno==line and any(a.name==expected_name and (a.asname or a.name)==name for a in n.names) for scope in review.enclosing(node,parents) for n in review.own_nodes(scope))
def class_for_constructor(call,tree,parents,path,target_path,target_class):
    if isinstance(call.func,ast.Name):
        name=call.func.id;kind,line=review.resolve_name(call.func,name,parents)
        if path==target_path and name==target_class and kind=="definition":
            return any(isinstance(n,ast.ClassDef) and n.name==target_class and n.lineno==line for n in ast.walk(tree))
        module=target_path.removesuffix(".py").replace("/",".")
        return lexical_import(call.func,name,parents,module,target_class) or (target_path.startswith("tests/") and lexical_import(call.func,name,parents,Path(target_path).stem,target_class))
    if isinstance(call.func,ast.Attribute) and isinstance(call.func.value,ast.Name) and call.func.attr==target_class:
        alias=call.func.value.id;kind,line=review.resolve_name(call.func.value,alias,parents)
        if kind not in ("module","import") or line is None:return False
        module=target_path.removesuffix(".py").replace("/",".")
        parent,_,leaf=module.rpartition(".")
        return any(isinstance(n,ast.ImportFrom) and n.level==0 and n.module==parent and n.lineno==line and any(a.name==leaf and (a.asname or a.name)==alias for a in n.names) for scope in review.enclosing(call.func,parents) for n in review.own_nodes(scope))
    return False
def refine(row):
    e,t=row["edge"],row["target"];sha=row["source"];path=e["source_file"];tpath=t["source_file"]
    _,tree,parents=review.source_tree(repo,sha,path);_,tt,tp=review.source_tree(repo,sha,tpath)
    line=review.line_no(e["source_location"]);tl=review.line_no(t["source_location"])
    if tree is None or tt is None:return "unresolved_non_python",None
    target_name=review.label(t)
    if row["verdict"]=="unverified_symbol_use":
        classes=[n for n in ast.walk(tt) if isinstance(n,ast.ClassDef) and n.name==target_name and n.lineno==tl]
        if len(classes)!=1:return "unresolved_target_class",None
        module=tpath.removesuffix(".py").replace("/",".")
        refs=[n for n in ast.walk(tree) if isinstance(n,ast.Name) and n.id==target_name and isinstance(n.ctx,ast.Load) and n.lineno==line]
        if refs and all(lexical_import(n,target_name,parents,module,target_name) or (tpath.startswith("tests/") and lexical_import(n,target_name,parents,Path(tpath).stem,target_name)) for n in refs):
            return "supported_explicit_class_import","matching import binding and anchored class reference; not runtime identity guarantee"
        return "unresolved_symbol_binding",None
    methods=[n for n in ast.walk(tt) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name==target_name and n.lineno==tl and isinstance(tp.get(n),ast.ClassDef)]
    if len(methods)!=1:return "unresolved_target_method",None
    cls=tp[methods[0]].name
    calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr==target_name and n.lineno<=line<=n.end_lineno]
    if len(calls)!=1:return "unresolved_call_anchor",None
    recv=calls[0].func.value
    if not isinstance(recv,ast.Name):return "unresolved_attribute_receiver",None
    kind,binding=review.resolve_name(recv,recv.id,parents)
    if kind=="parameter":return "unresolved_injected_receiver",None
    if kind!="other" or binding is None or binding>=line:return "unresolved_receiver_binding",None
    # Only an unconditional assignment in the same function body, not branch/loop or field inference.
    scopes=list(review.enclosing(recv,parents))
    if not scopes or not isinstance(scopes[0],(ast.FunctionDef,ast.AsyncFunctionDef)):return "unresolved_receiver_binding",None
    matches=[n for n in scopes[0].body if isinstance(n,ast.Assign) and n.lineno==binding and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and n.targets[0].id==recv.id and isinstance(n.value,ast.Call)]
    if len(matches)==1 and class_for_constructor(matches[0].value,tree,parents,path,tpath,cls):
        return "supported_local_constructor","matching direct local construction and static method definition; runtime substitution not excluded"
    return "unresolved_receiver_binding",None
results=[]
for row in rows:
    if not row["verdict"].startswith("unverified"):continue
    disposition,reason=refine(row)
    results.append({"scope":row["scope"],"version":row["version"],"source":row["source"],"edge":row["edge"],"target":row["target"],"prior":row["verdict"],"disposition":disposition,"reason":reason})
assert len(results)==601
counts=dict(sorted(collections.Counter(r["disposition"] for r in results).items()))
(out/"inferred-second-pass.json").write_bytes((json.dumps({"counts":counts,"rows":results,"policy":"narrow source-supported lexical references only; dynamic dispatch remains unresolved"},indent=2)+"\n").encode())
print("601 unresolved occurrences investigated",counts,flush=True)
