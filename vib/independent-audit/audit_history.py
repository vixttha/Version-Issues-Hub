"""Read all historical Graphify raw graphs, identify central shared call sites and changes.
No graph-based runtime bug claims; compare semantic endpoint identities, not line-number shifts.
"""
import hashlib,json,os,subprocess,re
from pathlib import Path
from collections import Counter
from functools import lru_cache
root=Path(os.environ["GITHUB_WORKSPACE"]); archive=root/"archive"/"archives"; repo=root/"archive"
out=Path(os.environ["RUNNER_TEMP"])/"independent-vib-audit";out.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_bytes())
def git(*args):return subprocess.check_output(["git",*args],cwd=repo).decode("utf-8").strip()
@lru_cache(maxsize=256)
def source(sha,path):return subprocess.check_output(["git","show",sha+":"+path],cwd=repo).decode("utf-8").splitlines()
def key(n):return (n.get("source_file",""),n.get("label",""))
targets={"require()","repo_path()","read_ref()","parse_json()","bindings()","load()","save()","finish()","reconcile()"}
rows=[]; observations=[]; previous=None; prev_version=None
for scope,folder in (("fix","code-graphs"),("cumulative","cumulative-code-graphs")):
    ix=read(archive/folder/"index.json")
    assert len(ix["results"])==36 and not ix["failures"]
    for i,r in enumerate(ix["results"],1):
        assert r["version"]==f"v0.0.0.{i}"
        path=archive/folder/r["version"];raw=(path/"graph.json").read_bytes()
        assert hashlib.sha256(raw).hexdigest()==r["graph_sha256"]
        assert read(path/"receipt.json")==r and git("rev-parse",r["source"]+"^{tree}")==r["tree"]
        g=json.loads(raw); nodes={n["id"]:n for n in g["nodes"]}
        assert g["built_at_commit"]==r["source"] and len(nodes)==len(g["nodes"])==r["nodes"] and len(g["links"])==r["edges"]
        counts=Counter(); selected=[]; relationships=set()
        for e in g["links"]:
            assert e["source"] in nodes and e["target"] in nodes
            a,b=nodes[e["source"]],nodes[e["target"]]
            if e.get("confidence")!="EXTRACTED" or e["relation"]!="calls":continue
            ka,kb=key(a),key(b)
            if not ka[0].startswith("tools/") or not kb[0].startswith("tools/"):continue
            relationships.add((ka,kb))
            counts[kb]+=1
            if kb[1] in targets:
                m=re.fullmatch(r"L(\d+)",e.get("source_location",""))
                if not m:continue
                loc=int(m[1]); file=e["source_file"];lines=source(r["source"],file)
                assert 1<=loc<=len(lines)
                selected.append({"caller":ka,"callee":kb,"file":file,"line":loc,"text":lines[loc-1],"confidence":"extracted; source anchor exists, runtime dispatch not proved"})
        row={"scope":scope,"version":r["version"],"source":r["source"],"nodes":len(nodes),"edges":len(g["links"]),"production_call_pairs":len(relationships),"top_incoming":[{"target":k,"count":n} for k,n in counts.most_common(8)],"selected_source_anchors":len(selected)}
        if scope=="cumulative":
            if previous is not None: row["delta"]={"previous":prev_version,"added":len(relationships-previous),"removed":len(previous-relationships)}
            previous=relationships;prev_version=r["version"]
        rows.append(row);observations.append({"scope":scope,"version":r["version"],"source":r["source"],"relationships":selected})
assert len(rows)==72
(out/"historical.json").write_bytes((json.dumps({"graphs":rows,"source_anchors":sum(r["selected_source_anchors"] for r in rows),"scope":"structural and selected anchor audit only; no runtime or exhaustive semantic claim"},indent=2)+"\n").encode("utf-8"))
(out/"relationships.json").write_bytes((json.dumps(observations,indent=2)+"\n").encode("utf-8"))
print("72 historical graphs audited; selected source anchors:",sum(r["selected_source_anchors"] for r in rows))
