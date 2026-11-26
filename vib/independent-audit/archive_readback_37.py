"""Read-only independent audit of exact .37 candidate and retained archive."""
import hashlib, json, os, shutil, subprocess, tempfile
from pathlib import Path

root = Path(os.environ["GITHUB_WORKSPACE"])
repo = root / "archive"
candidate = root / "candidate"
arc = repo / "archives"
source = "041e187dc1d383082c1a4805e6d4743eec97e535"
archive = "0cd6d9fdf59d1f796ebe6b2aedff8f7a3c17d1c1"
prior = "eb2830b8614c795045ba000879d055f434c4a565"
def git(repo, *args):
    return subprocess.check_output(["git", *args], cwd=repo)
def read(p):
    return json.loads(p.read_bytes())
def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
assert git(candidate, "rev-parse", "HEAD").decode().strip() == source
assert git(repo, "rev-parse", "HEAD").decode().strip() == archive
graph_path = arc / "candidate-code-graphs/v0.0.0.37" / source
r = read(graph_path / "receipt.json")
assert (r["issue"], r["version"], r["source"], r["source_kind"], r["historical_test_claim"]) == (53, "v0.0.0.37", source, "unmerged_engineering_candidate", False)
assert r["tree"] == git(candidate, "rev-parse", "HEAD^{tree}").decode().strip()
assert digest(graph_path / "graph.json") == r["graph_sha256"] == "fced47a40679035017b52180f3488362fa4c851dbbd277155295b663990e647a"
assert digest(graph_path / "debug-relationships.json") == r["query_sha256"] == "c56967b0bdcff4a9544298a8cb3c9634cd9ce5bbded0f1d097e5c601a2e8747e"
g = read(graph_path / "graph.json")
ids = {n["id"] for n in g["nodes"]}
assert len(ids) == len(g["nodes"]) == r["nodes"] == 852
assert len(g["links"]) == r["edges"] == 2532
assert all(e["source"] in ids and e["target"] in ids for e in g["links"])
p = arc / "candidates" / source / "45791210804-1"
receipt = read(p / "candidate-receipt.json")
assert receipt["source"] == source and len(receipt["lookups"]) == 38
files = sorted(p.glob("shard-*/archive/*.json"))
assert len(files) == 2
assert [digest(f) for f in files] == ["340d395271b0e45c7fedf1e8a4efb6c794eceaa1b862c4722d6fb7e58fb6e149", "fc63c09e0e9b993330acece28bff33b05aae39408a38cc9594637f0339eadca9"]
assert [len(s["features"]) for s in receipt["shards"]] == [32, 6]
def tree(ref):
    result = {}
    for line in git(repo, "ls-tree", "-rz", ref, "--", "archives").split(b"\0"):
        if line:
            meta, path = line.split(b"\t", 1)
            result[path] = meta
    return result
old, new = tree(prior), tree(archive)
assert len(old) == 187 and all(new.get(path) == meta for path, meta in old.items())
assert len(new) == len(old) + 6
def invoke(path, src=source, sha=r["graph_sha256"]):
    return subprocess.run(["node", "veraphifiy.mjs", "code-graph", "--archive", str(path),
        "--project", "vixttha/Version-Issues-Hub", "--version", "v0.0.0.37",
        "--scope", "candidate", "--source", src, "--graph-sha256", sha],
        cwd=repo, capture_output=True)
actual = invoke(arc)
assert actual.returncode == 0, actual.stderr
assert json.loads(actual.stdout) == {"receipt": r, "graph": g}
assert invoke(arc, sha="0"*64).returncode != 0
assert invoke(arc, src="0"*40).returncode != 0
with tempfile.TemporaryDirectory() as tmp:
    d = Path(tmp) / graph_path.relative_to(arc)
    shutil.copytree(graph_path, d)
    raw = (d / "graph.json").read_bytes()
    (d / "graph.json").write_bytes(raw + b"\n")
    assert invoke(Path(tmp)).returncode != 0
    (d / "graph.json").write_bytes(raw)
    (d / "receipt.json").write_text(json.dumps({**r, "issue": 54}), encoding="utf-8")
    assert invoke(Path(tmp)).returncode != 0
report = {"source": source, "archive": archive, "prior": prior, "preserved": len(old),
          "added": len(new)-len(old), "features": 38, "nodes": len(ids), "edges": len(g["links"]),
          "graph_sha256": r["graph_sha256"], "query_sha256": r["query_sha256"],
          "shard_sha256": [digest(f) for f in files], "native_reads": 1, "negative_controls": 4,
          "status": "PASS", "independent_agent_trial": False}
(Path(os.environ["RUNNER_TEMP"]) / "archive-readback.json").write_bytes((json.dumps(report, indent=2)+"\n").encode())
print(json.dumps(report), flush=True)
