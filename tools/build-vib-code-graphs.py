"""Generate raw Graphify AST code graphs from exact historical VIB Git objects.
No historical code execution, no semantic LLM, no version remapping."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import importlib.metadata

root = Path(os.environ["GITHUB_WORKSPACE"])
vault = root / "vault"
repo = root / "source"
output = Path(os.environ["RUNNER_TEMP"]) / "vib-code-graphs"
output.mkdir()
inventory = json.loads((vault / "tools/vib-code-graph-inventory.json").read_text())
assert [r["version"] for r in inventory] == [f"v0.0.0.{n}" for n in range(1,37)]
assert len({r["issue"] for r in inventory}) == 36
assert importlib.metadata.version("graphifyy") == "0.9.109"
def run(*args, cwd=repo, **kwargs):
    return subprocess.check_output(args, cwd=cwd, **kwargs)
def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
help_result = subprocess.run(["graphify", "--help"], cwd=vault, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
(output/"cli-help.txt").write_text(help_result.stdout)
# The CLI help is not a reliable capability test; exercise explicit code-only extraction.
results = []
failures = []
for row in inventory:
    version, source = row["version"], row["source"]
    try:
        if run("git","rev-parse",source).decode().strip()!=source:
            raise ValueError("Source resolution mismatch")
        with tempfile.TemporaryDirectory(prefix="vib-graph-") as tmp:
            work = Path(tmp)/"snapshot"
            run("git","worktree","add","--detach",str(work),source)
            try:
                if run("git","rev-parse","HEAD",cwd=work).decode().strip()!=source:
                    raise ValueError("Wrong source checkout")
                tree = run("git","rev-parse","HEAD^{tree}",cwd=work).decode().strip()
                code_files = [p for p in run("git","ls-files","-z",cwd=work).decode().split("\0") if p.endswith((".py",".js",".mjs",".cjs",".ts",".sh"))]
                if not code_files:
                    raise ValueError("No tracked code files")
                # Explicit offline AST extraction. Do not run code from this checkout.
                cmd = ["graphify","extract",".","--code-only"]
                # Explicit flag remains mandatory; never fall back to semantic extraction.
                proc = subprocess.run(cmd,cwd=work,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
                print(version, source, proc.stdout[-4000:], flush=True)
                proc.check_returncode()
                graph = work/"graphify-out/graph.json"
                if not graph.is_file():
                    raise ValueError("Graphify did not write graph.json")
                data=json.loads(graph.read_bytes())
                nodes=data["nodes"]
                edges=data.get("links",data.get("edges"))
                if not isinstance(nodes,list) or not nodes or not isinstance(edges,list):
                    raise ValueError("Empty or invalid graph")
                ids={n["id"] for n in nodes}
                if len(ids)!=len(nodes):
                    raise ValueError("Duplicate graph node")
                if any(e["source"] not in ids or e["target"] not in ids for e in edges):
                    raise ValueError("Dangling graph edge")
                dest=output/version
                dest.mkdir()
                (dest/"graph.json").write_bytes(graph.read_bytes())
                receipt={**row,"tree":tree,"graphify_version":"0.9.109","mode":"code-only AST",
                         "reconstructed":True,"historical_test_claim":False,"nodes":len(nodes),"edges":len(edges),
                         "tracked_code_files":code_files,"graph_sha256":sha(dest/"graph.json"),
                         "run":os.environ["GITHUB_RUN_ID"],"attempt":os.environ["GITHUB_RUN_ATTEMPT"]}
                (dest/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n")
                results.append(receipt)
                print(f"{version}: {len(nodes)} nodes, {len(edges)} edges",flush=True)
            finally:
                run("git","worktree","remove","--force",str(work))
    except Exception as e:
        failures.append({"version":version,"source":source,"error":str(e)})
        print(f"FAILED {version}: {e}",flush=True)
(output/"index.json").write_text(json.dumps({"schema":1,"repository":"vixttha/Version-Issues-Hub","mode":"historical fix-source AST snapshots; not historical candidate tests","results":results,"failures":failures},indent=2)+"\n")
if failures or len(results)!=36:
    raise SystemExit(f"Only {len(results)}/36 code graphs produced; see index.json")
