"""Preserve only verified public VIB candidate entries; never overwrite history."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from archive_scope import feature_ids

ROOT = Path.cwd()
TEMP = Path(os.environ["RUNNER_TEMP"])
IDENTITY = "vixttha/Version-Issues-Hub"
HISTORICAL = "ee64cdd7019c3cd279213c490226eb3f89f5fb49"
CURRENT = os.environ["VIB_SOURCE"]

def preserve(origin, source, version, run, attempt):
    receipt_path = origin / "candidate-receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if (receipt["status"], receipt["source"], str(receipt["runner_id"]), str(receipt["runner_attempt"])) != ("candidate_only", source, run, attempt):
        raise ValueError("Receipt identity mismatch")
    if receipt.get("version", version) != version:
        raise ValueError("Version mismatch")
    archive = origin / "archive"
    entries = list(archive.glob("*.json"))
    if len(entries) != 1 or not re.fullmatch(r"[0-9a-f]{64}\.json", entries[0].name):
        raise ValueError("Unexpected archive inventory")
    entry = entries[0]
    digest = hashlib.sha256(entry.read_bytes()).hexdigest()
    if digest != receipt["archive_sha256"]:
        raise ValueError("Archive digest mismatch")
    args = ["node", str(ROOT / "veraphifiy.mjs"), "verify", "--archive", str(archive), "--project", IDENTITY, "--version", version, "--source", source, "--archive-sha256", digest]
    subprocess.run(args, check=True)
    target = ROOT / "archives/candidates" / source / f"{run}-{attempt}"
    items = [(entry, Path("archive") / entry.name), (receipt_path, Path("candidate-receipt.json"))]
    if target.exists():
        for file, relative in items:
            if not (target / relative).is_file() or (target / relative).read_bytes() != file.read_bytes():
                raise ValueError("Refusing to replace historical evidence")
        return
    for file, relative in items:
        dest = target / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(file, dest)
    subprocess.run([str(target / "archive") if arg == str(archive) else arg for arg in args], check=True)

def preserve_sharded(origin, source, run, attempt):
    receipt_path = origin / "candidate-receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if (receipt.get("schema_version"), receipt["status"], receipt["source"], str(receipt["runner_id"]), str(receipt["runner_attempt"])) != (2, "candidate_only", source, run, attempt):
        raise ValueError("Sharded receipt identity mismatch")
    version = receipt["version"]
    versions = receipt["versions"]
    if len(versions) != len(set(versions)) or version != max(versions, key=lambda v: tuple(map(int,v[1:].split(".")))) or receipt["operational_exclusions"] != ["v0.0.0.23"]:
        raise ValueError("Invalid version scope")
    expected = feature_ids([v for v in versions if v not in receipt["operational_exclusions"]])
    seen = set()
    items = [(receipt_path, Path("candidate-receipt.json"))]
    for number, shard in enumerate(receipt["shards"], 1):
        name = f"shard-{number:04d}"
        ids = shard["features"]
        if shard["directory"] != name or not 0 < len(ids) <= 32 or len(set(ids)) != len(ids) or seen.intersection(ids):
            raise ValueError("Invalid shard inventory")
        seen.update(ids)
        archive = origin / name / "archive"
        entries = list(archive.glob("*.json"))
        if len(entries) != 1 or not re.fullmatch(r"[0-9a-f]{64}\.json", entries[0].name):
            raise ValueError("Invalid shard archive")
        digest = hashlib.sha256(entries[0].read_bytes()).hexdigest()
        if digest != shard["archive_sha256"]:
            raise ValueError("Shard digest mismatch")
        args = ["node", str(ROOT / "veraphifiy.mjs"), "verify", "--archive", str(archive), "--project", IDENTITY, "--version", version, "--source", source, "--archive-sha256", digest]
        subprocess.run(args, check=True)
        for feature in ids:
            lookup = json.loads(subprocess.check_output([*args[:2], "lookup", *args[3:], "--feature", "feature:" + feature], text=True))
            if lookup != receipt["lookups"][feature]:
                raise ValueError("Preservation lookup mismatch")
        items.append((entries[0], Path(name) / "archive" / entries[0].name))
    if seen != expected or set(receipt["lookups"]) != expected:
        raise ValueError("Missing or excess shard features")
    target = ROOT / "archives/candidates" / source / f"{run}-{attempt}"
    if target.exists():
        if {p.relative_to(target) for p in target.rglob("*") if p.is_file()} != {p for _,p in items}:
            raise ValueError("Existing archive inventory differs")
        for file, relative in items:
            if (target / relative).read_bytes() != file.read_bytes():
                raise ValueError("Refusing to replace historical evidence")
        return
    for file, relative in items:
        dest = target / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(file, dest)
        if dest.read_bytes() != file.read_bytes():
            raise ValueError("Preserved bytes changed")

old = ROOT / "archives/candidates" / HISTORICAL / "45330366047-1"
preserve(TEMP / "historical" if not old.exists() else old, HISTORICAL, "v0.0.0.5", "45330366047", "1")
preserve_sharded(TEMP / "current", CURRENT, os.environ["GITHUB_RUN_ID"], os.environ["GITHUB_RUN_ATTEMPT"])
