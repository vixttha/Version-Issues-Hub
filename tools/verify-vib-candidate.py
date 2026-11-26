"""Build a disposable, commit-pinned VIB candidate archive and check every citation."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
from archive_scope import scope

root = Path.cwd()
project = root / "vib"
producer = root / "producer"
source = os.environ["VIB_SOURCE"]
identity = "vixttha/Version-Issues-Hub"
ledger = json.loads(subprocess.check_output(["git", "show", f"{source}:ledger/issue-versions.json"], cwd=project))
if ledger["repository"] != identity:
    raise ValueError("Ledger identity mismatch")
versions = [record["version"] for record in ledger["issues"]]
if not versions or len(set(versions)) != len(versions):
    raise ValueError("Empty or duplicate ledger versions")
version = max(versions, key=lambda value: tuple(map(int, value[1:].split("."))))
output = Path(os.environ["RUNNER_TEMP"]) / "vib-candidate-archive"
output.mkdir(exist_ok=True)

def git(directory, *args):
    return subprocess.check_output(["git", *args], cwd=directory)

for directory, pin in [(project, source), (producer, os.environ["PRODUCER_SHA"])]:
    if git(directory, "rev-parse", "HEAD").decode().strip() != pin:
        raise ValueError("Checkout pin mismatch")

manifest = json.loads(git(project, "show", f"{source}:docs/receipt-evidence.json"))
manifest.update(repository=identity, source_commit=source)
features = manifest["features"]
expected = {}
inventory = set()
for feature in features:
    if feature["id"] in expected:
        raise ValueError("Duplicate feature mapping")
    citations = []
    for relation in ("implemented_in", "documented_in", "changed_in", "tested_by"):
        for ref in feature.get(relation, []):
            path, anchor = ref["path"], ref["anchor"]
            inventory.add(path)
            lines = git(project, "show", f"{source}:{path}").decode("utf-8").split("\n")
            matches = [i for i, line in enumerate(lines, 1) if anchor in line]
            if len(matches) != 1:
                raise ValueError(f"Non-unique anchor: {path} {anchor!r}")
            if relation == "implemented_in":
                citations.append({"path": path, "line": matches[0]})
    expected[feature["id"]] = citations
receipt_scope = json.loads(git(project, "show", f"{source}:ledger/receipt-scope.json"))
selected = receipt_scope["versions"]
if set(receipt_scope["fixes"]) != set(selected):
    raise ValueError("Fix scope mismatch")
partitions = scope(versions, selected, features)
if sum(len(git(project, "show", f"{source}:{p}")) for p in inventory) > 8 * 1024 * 1024:
    raise ValueError("Archive source budget exceeded")
cli = root / "veraphify/veraphifiy.mjs"
lookups = {}
shards = []
for index, part in enumerate(partitions, 1):
    folder = output / f"shard-{index:04d}"
    folder.mkdir()
    shard = {**manifest, "features": part}
    shard["source_files"] = sorted({ref["path"] for feature in part for ref in feature["implemented_in"]})
    manifest_path = folder / "manifest.json"
    manifest_path.write_text(json.dumps(shard), encoding="utf-8")
    evidence = folder / "graphify"
    subprocess.run(["python", str(producer / "versions/v0.0.8/evidence_map.py"), str(manifest_path), str(evidence)], cwd=project, check=True)
    receipt = json.loads((evidence / "receipt.json").read_text(encoding="utf-8"))
    ids = [f["id"] for f in part]
    if (receipt["source_commit"] != source or receipt["repository"] != identity or receipt["mcp_verified"] is not True
            or set(receipt["feature_links"]) != {"feature:" + i for i in ids}
            or receipt["graph_sha256"] != hashlib.sha256((evidence / "graph.json").read_bytes()).hexdigest()):
        raise ValueError("Graphify shard receipt mismatch")
    archive = folder / "archive"
    args = ["--archive", str(archive), "--project", identity, "--version", version, "--source", source]
    def call(command, *extra):
        return json.loads(subprocess.check_output(["node", str(cli), command, *args, *extra], text=True))
    imported = call("import", "--checkout", str(project), "--evidence", str(evidence))
    entries = list(archive.glob("*.json"))
    if len(entries) != 1:
        raise ValueError("Expected one archive entry per isolated shard")
    digest = hashlib.sha256(entries[0].read_bytes()).hexdigest()
    if digest != imported["archive_sha256"] or imported["veraphifiy_version"] != "v0.0.9":
        raise ValueError("Archive identity mismatch")
    pin = ("--archive-sha256", digest)
    if call("verify", *pin) != imported:
        raise ValueError("Archive verification mismatch")
    for feature in ids:
        result = call("lookup", *pin, "--feature", f"feature:{feature}")
        # Graphify may canonicalize edge order; compare exact citation multisets,
        # not presentation order. Missing, extra or wrong anchors still fail.
        canonical = lambda items: sorted(json.dumps(item, sort_keys=True) for item in items)
        if canonical(result["citations"]) != canonical(expected[feature]) or result["source"] != source:
            raise ValueError(f"Incorrect citation: {feature}; actual={result['citations']!r}; expected={expected[feature]!r}")
        lookups[feature] = result
    shards.append({"directory": folder.name, "features": ids, "archive_sha256": digest})
if set(lookups) != set(expected):
    raise ValueError("Incomplete archive lookups")
(output / "candidate-receipt.json").write_text(json.dumps({
    "schema_version": 2, "status": "candidate_only", "source": source, "version": version,
    "runner_id": os.environ["GITHUB_RUN_ID"], "runner_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
    "veraphify_source": git(root / "veraphify", "rev-parse", "HEAD").decode().strip(),
    "versions": versions, "operational_exclusions": sorted(set(versions)-set(selected)),
    "shards": shards, "lookups": lookups,
}, indent=2) + "\n", encoding="utf-8")
print(f"Verified {len(expected)} VIB candidate implementation citations across {len(shards)} shards; operational exclusions recorded separately")
