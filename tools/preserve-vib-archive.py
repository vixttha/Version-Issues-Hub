"""Preserve only verified public VIB candidate entries; never overwrite history."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path.cwd()
TEMP = Path(os.environ["RUNNER_TEMP"])
IDENTITY = "vixttha/Version-Issues-Hub"
HISTORICAL = "ee64cdd7019c3cd279213c490226eb3f89f5fb49"
CURRENT = "4fc9ac47462101b941ea2f78fc939d42a9de0032"

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

old = ROOT / "archives/candidates" / HISTORICAL / "45330366047-1"
preserve(TEMP / "historical" if not old.exists() else old, HISTORICAL, "v0.0.0.5", "45330366047", "1")
preserve(TEMP / "current", CURRENT, "v0.0.0.19", os.environ["GITHUB_RUN_ID"], os.environ["GITHUB_RUN_ATTEMPT"])
