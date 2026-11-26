"""Audit inferred relationships from immutable Graphify JSON against exact Git sources.
Conservative static evidence only: unresolved dynamic binding is never confirmed.
"""
import ast
import hashlib
import json
import re
import subprocess
from collections import Counter
from functools import lru_cache
from pathlib import Path

SCOPES = (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)
DEFS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

@lru_cache(maxsize=128)
def source_tree(repo, sha, path):
    if not re.fullmatch(r"[0-9a-f]{40}",sha) or not path or path.startswith("/") or ".." in Path(path).parts:
        raise ValueError("Invalid source identity")
    code = subprocess.check_output(["git","show",f"{sha}:{path}"],cwd=repo).decode("utf-8")
    tree = ast.parse(code,filename=path) if path.endswith(".py") else None
    parents = {child:parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)} if tree else {}
    return code,tree,parents

def enclosing(node, parents):
    while node in parents:
        node=parents[node]
        if isinstance(node,SCOPES):
            yield node

def own_nodes(scope):
    stack=list(ast.iter_child_nodes(scope))
    while stack:
        n=stack.pop()
        yield n
        if not isinstance(n,SCOPES):
            stack.extend(ast.iter_child_nodes(n))

def bindings(scope,name):
    found=[]
    if isinstance(scope,(ast.FunctionDef,ast.AsyncFunctionDef,ast.Lambda)):
        args=scope.args
        for arg in [*args.posonlyargs,*args.args,*args.kwonlyargs,args.vararg,args.kwarg]:
            if arg is not None and arg.arg==name: found.append(("parameter",arg.lineno))
    for n in own_nodes(scope):
        if isinstance(n,DEFS) and n.name==name: found.append(("definition",n.lineno))
        elif isinstance(n,(ast.Import,ast.ImportFrom)):
            for a in n.names:
                if (a.asname or a.name.split(".")[0])==name:
                    kind="module" if isinstance(n,ast.Import) or (isinstance(n,ast.ImportFrom) and n.module=="tools" and name=="install") else "import"
                    found.append((kind,n.lineno))
        elif isinstance(n,ast.Name) and isinstance(n.ctx,(ast.Store,ast.Del)) and n.id==name:
            found.append(("other",n.lineno))
        elif isinstance(n,(ast.Global,ast.Nonlocal)) and name in n.names:
            found.append(("other",n.lineno))
    return found

def resolve_name(node,name,parents):
    for scope in enclosing(node,parents):
        # A function does not close over the class namespace.
        if isinstance(scope,ast.ClassDef): continue
        found=bindings(scope,name)
        if found:
            return found[0] if len(found)==1 else ("ambiguous",None)
    return ("unbound",None)

def label(n):
    return n["label"].strip(".").removesuffix("()")

def line_no(location):
    m=re.fullmatch(r"L(\d+)",location or "")
    if not m: raise ValueError(f"Invalid anchor: {location}")
    return int(m[1])

def classify(repo,sha,e,target):
    path=e["source_file"]; line=line_no(e["source_location"])
    target_path=target["source_file"]; target_line=line_no(target["source_location"])
    name=label(target)
    code,tree,parents=source_tree(repo,sha,path)
    target_code,target_tree,_=source_tree(repo,sha,target_path)
    lines=code.splitlines()
    if not (1<=line<=len(lines) and 1<=target_line<=len(target_code.splitlines())):
        raise ValueError("Source anchor outside pinned blob")
    result={"source_line":lines[line-1],"target_line_text":target_code.splitlines()[target_line-1],"verdict":"unverified_dynamic","reason":"Anchor exists; target binding not established by supported static rules."}
    if tree is None or target_tree is None:
        return result
    if not any(isinstance(n,DEFS) and n.name==name and n.lineno==target_line for n in ast.walk(target_tree)):
        result.update(verdict="unverified_target_definition",reason="Target anchor is not a matching Python definition.")
        return result
    if e["relation"]=="indirect_call":
        # Use exact Name AST anchors, not a sliding text window.
        candidates=[n for n in ast.walk(tree) if isinstance(n,ast.Name) and isinstance(n.ctx,ast.Load) and n.id==name and n.lineno==line]
        if e.get("context")=="assignment":
            candidates=[n for n in candidates if isinstance(parents.get(n),(ast.Assign,ast.AnnAssign)) and parents[n].value is n]
        elif e.get("context")=="argument":
            candidates=[n for n in candidates if isinstance(parents.get(n),(ast.Call,ast.keyword)) and (isinstance(parents[n],ast.keyword) or n in parents[n].args)]
        if candidates:
            resolved={resolve_name(n,name,parents) for n in candidates}
            if len(resolved)==1:
                kind,definition=resolved.pop()
                result["resolved_binding"]={"kind":kind,"line":definition,"file":path}
                if kind=="definition" and definition<=line:
                    if path==target_path and definition==target_line:
                        result.update(verdict="supported_lexical_reference",reason="Name resolves to the exact definition in its lexical scope; not runtime invocation proof.")
                    else:
                        result.update(verdict="rejected_wrong_lexical_target",reason="Name resolves to a different source definition.")
                elif kind in ("module","parameter"):
                    result.update(verdict="rejected_nonfunction_binding",reason="Name denotes a module or parameter, not the claimed statically resolved function.")
    elif e["relation"]=="calls":
        # Record direct syntactic evidence without guessing runtime receiver type.
        calls=[n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and n.func.attr==name and n.lineno<=line<=n.end_lineno]
        if calls: result.update(verdict="unverified_receiver",reason="Method call syntax matches; exact dynamic receiver target not proven.")
    elif e["relation"]=="uses":
        result.update(verdict="unverified_symbol_use",reason="Symbol-use anchor exists; imported class identity needs separate resolution.")
    return result

def audit(repo,archive,out):
    out.mkdir(parents=True,exist_ok=True)
    summary=[]
    for scope,folder in (("fix","code-graphs"),("cumulative","cumulative-code-graphs")):
        index=json.loads((archive/folder/"index.json").read_bytes())
        for r in index["results"]:
            raw=(archive/folder/r["version"]/"graph.json").read_bytes()
            if digest(raw)!=r["graph_sha256"]: raise ValueError("Raw graph digest mismatch")
            g=json.loads(raw)
            if g["built_at_commit"]!=r["source"]: raise ValueError("Raw graph source mismatch")
            nodes={n["id"]:n for n in g["nodes"]}
            rows=[]; retained=[]
            for e in g["links"]:
                if e.get("confidence")!="INFERRED":
                    retained.append(e);continue
                target=nodes[e["target"]]
                decision=classify(repo,r["source"],e,target)
                rows.append({"edge":e,"target_file":target["source_file"],"target_location":target["source_location"],**decision})
                if decision["verdict"].startswith("supported_"): retained.append(e)
            counts=dict(sorted(Counter(row["verdict"] for row in rows).items()))
            dest=out/scope/r["version"];dest.mkdir(parents=True)
            view={**g,"links":retained}
            (dest/"reviewed-graph.json").write_bytes((json.dumps(view,indent=2,ensure_ascii=True)+"\n").encode("utf-8"))
            record={"scope":scope,"version":r["version"],"source":r["source"],"raw_sha256":r["graph_sha256"],"counts":counts,"inferred":len(rows),"reviewed_edges":len(retained),"reviewed_sha256":digest((dest/"reviewed-graph.json").read_bytes()),"relationships":rows}
            (dest/"audit.json").write_bytes((json.dumps(record,indent=2,ensure_ascii=True)+"\n").encode("utf-8"))
            summary.append({k:v for k,v in record.items() if k!="relationships"})
    assert len(summary)==72
    # Explicit regression: the six false cross-test callback bindings must be rejected.
    latest=json.loads((out/"fix/v0.0.0.36/audit.json").read_bytes())
    wrong=[x for x in latest["relationships"] if x["edge"]["source_file"]=="tests/test_gate.py" and x["edge"].get("context")=="assignment" and x["verdict"]=="rejected_wrong_lexical_target"]
    assert sorted(line_no(x["edge"]["source_location"]) for x in wrong)==[241,288,302,314,329,343],wrong
    assert latest["inferred"]==51
    total=Counter()
    for row in summary: total.update(row["counts"])
    result={"graphs":summary,"inferred_total":sum(total.values()),"counts":dict(sorted(total.items())),"raw_graphs_unchanged":True,"policy":"Only source-supported lexical inferred references retained; unresolved relationships are omitted, not declared false. Other extracted edges unchanged."}
    (out/"index.json").write_bytes((json.dumps(result,indent=2,ensure_ascii=True)+"\n").encode("utf-8"))
    return result
