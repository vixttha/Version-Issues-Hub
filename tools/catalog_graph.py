"""Describe catalog navigation at the exact checked-out revision."""
import json
from pathlib import Path
import subprocess
import sys


def git(*args):
    return subprocess.check_output(["git", *args], text=True).strip()


def reference(path, anchor):
    return {"path": path, "anchor": anchor}


commit = git("rev-parse", "HEAD")
features = []
for path in sorted(git("ls-files", "--", "features/records/*.json").splitlines()):
    feature = json.loads(git("show", f"{commit}:{path}"))
    idea_refs = [
        reference(f"ideas/records/{idea}.json", f'"id": "{idea}",')
        for idea in feature["idea_ids"]
    ]
    features.append({
        "id": feature["id"].lower(),
        "label": feature["title"],
        "documented_in": [reference(path, f'"id": "{feature["id"]}",'), *idea_refs],
        "changed_in": [reference(path, '"acceptance_criteria": [')],
        "tested_by": [reference(
            ".github/workflows/provenistem.yml",
            "- name: Verify the populated project catalog",
        )],
    })
manifest = {
    "repository": git("config", "--get", "remote.origin.url").removesuffix(".git").split("github.com/")[-1],
    "source_commit": commit,
    "title": "Provenistem planned capabilities and catalog validation",
    "features": features,
}
Path(sys.argv[1]).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
