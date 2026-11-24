"""Build a disposable, commit-pinned VIB candidate archive and check every citation."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

root = Path.cwd()
project = root / "vib"
producer = root / "producer"
source = os.environ["VIB_SOURCE"]
identity = "vixttha/Version-Issues-Hub"
version = "v0.0.0.5"
output = Path(os.environ["RUNNER_TEMP"]) / "vib-candidate-archive"
output.mkdir()

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
if set(expected) != {f"v0-0-0-{i}" for i in range(1, 6)}:
    raise ValueError("Unexpected checkpoint scope")
if sum(len(git(project, "show", f"{source}:{p}")) for p in inventory) > 8 * 1024 * 1024:
    raise ValueError("Archive source budget exceeded")
manifest["source_files"] = sorted({ref["path"] for feature in features for ref in feature["implemented_in"]})
manifest_path = output / "manifest.json"
manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
evidence = output / "graphify"
subprocess.run(["python", str(producer / "versions/v0.0.8/evidence_map.py"), str(manifest_path), str(evidence)], cwd=project, check=True)
receipt = json.loads((evidence / "receipt.json").read_text(encoding="utf-8"))
if receipt["source_commit"] != source or not receipt["mcp_verified"]:
    raise ValueError("Graphify receipt not verified")
archive = output / "archive"
cli = root / "veraphify/veraphifiy.mjs"
args = ["--archive", str(archive), "--project", identity, "--version", version, "--source", source]

def call(command, *extra):
    return json.loads(subprocess.check_output(["node", str(cli), command, *args, *extra], text=True))

imported = call("import", "--checkout", str(project), "--evidence", str(evidence))
entries = list(archive.glob("*.json"))
if len(entries) != 1:
    raise ValueError("Expected a single candidate archive")
digest = hashlib.sha256(entries[0].read_bytes()).hexdigest()
if digest != imported["archive_sha256"] or imported["veraphifiy_version"] != "v0.0.9":
    raise ValueError("Unexpected archive hash or runtime")
pin = ("--archive-sha256", digest)
if call("verify", *pin) != imported:
    raise ValueError("Archive verification mismatch")
lookups = {}
for feature, citations in expected.items():
    result = call("lookup", *pin, "--feature", f"feature:{feature}")
    if result["citations"] != citations or result["source"] != source:
        raise ValueError(f"Incorrect citation: {feature}")
    lookups[feature] = result
(output / "candidate-receipt.json").write_text(json.dumps({
    "status": "candidate_only", "source": source, "archive_sha256": digest,
    "runner_id": os.environ["GITHUB_RUN_ID"], "runner_attempt": os.environ["GITHUB_RUN_ATTEMPT"],
    "veraphify_source": git(root / "veraphify", "rev-parse", "HEAD").decode().strip(),
    "lookups": lookups,
}, indent=2) + "\n", encoding="utf-8")
print("Verified five VIB candidate implementation citations")
