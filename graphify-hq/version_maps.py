"""Build or verify the README HQ maps through the pinned Graphify HQ template."""

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
HQ = ROOT / "graphify-hq"
TEMPLATE = HQ / "template/v0.0.8/evidence_map.py"
CHECKER = "tools/check_readme_hq.py"
CATALOG = "graphify-hq/catalog.json"


def source_bytes(commit, path):
    return subprocess.check_output(["git", "show", f"{commit}:{path}"], cwd=ROOT)


def reference(commit, path, change=False):
    lines = source_bytes(commit, path).decode("utf-8").splitlines()
    stripped = [line.strip() for line in lines]
    occurrences = Counter(stripped)
    headings = ("# ", "<h1 ", "<h1>", "## ")
    prefixes = ("- ", *headings) if change else headings
    for prefix in prefixes:
        for number, line in enumerate(stripped, 1):
            if line.startswith(prefix) and len(line) <= 500 and occurrences[line] == 1:
                return {"path": path, "anchor": line}, number
    raise ValueError(f"No unique source anchor at {commit}:{path}")


def version_manifest(repository, commit, version, records):
    files = {CHECKER}
    features = []
    outline = []
    for record in records:
        references = [reference(commit, path) for path in record["documented_in"]]
        changes, change_line = reference(commit, record["changed_in"], change=True)
        for ref, _ in references:
            files.add(ref["path"])
        files.add(changes["path"])
        features.append({
            "id": f"{record['id']}-{version.replace('.', '-')}",
            "label": record["title"],
            "documented_in": [ref for ref, _ in references],
            "changed_in": [changes],
            "tested_by": [{"path": CHECKER, "anchor": "def check_history(errors):"}],
        })
        outline.append((record, references, (changes, change_line)))
    return {
        "repository": repository, "source_commit": commit,
        "title": f"README HQ {version} version history", "source_files": sorted(files),
        "features": features,
    }, outline


def render_outline(version, repository, receipt, outline):
    commit = receipt["source_commit"]
    def link(path, line, label):
        return f"[{label}](https://github.com/{repository}/blob/{commit}/{quote(path)}#L{line})"

    heading = [
        f"# README HQ {version} map",
        "",
        f"{len(outline)} records · {receipt['nodes']} nodes · {receipt['edges']} edges",
        "",
        f"[Source commit](https://github.com/{repository}/commit/{commit}) · [Graph](graph.json) · [Receipt](receipt.json) · [Map index](../../README.md)",
        "",
        "| Record | What changed | Source evidence |",
        "| --- | --- | --- |",
    ]
    for record, docs, (change, line) in outline:
        references = [link(ref["path"], number, f"Source {i}") for i, (ref, number) in enumerate(docs, 1)]
        references.append(link(change["path"], line, "Change record"))
        heading.append(f"| {record['title']} | {record['summary']} | {' · '.join(references)} |")
    return "\n".join(heading) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--output", type=Path, help="build into an empty output directory")
    args = parser.parse_args()
    commit = (HQ / "source-commit.txt").read_text(encoding="ascii").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        parser.error("source-commit.txt must contain a full Git commit SHA")
    catalog_bytes = (ROOT / CATALOG).read_bytes()
    if catalog_bytes != source_bytes(commit, CATALOG):
        parser.error("catalog differs from the pinned source commit")
    catalog = json.loads(catalog_bytes)
    versions = catalog["versions"]
    index = (ROOT / "versions/README.md").read_text(encoding="utf-8")
    if catalog["schema"] != 1 or set(versions) != set(re.findall(r"^\| (v\d+(?:\.\d+)+) \|", index, re.M)):
        parser.error("Graphify catalog and README HQ version index disagree")
    target = (args.output or HQ / "maps").resolve()
    if args.output and target.exists() and any(target.iterdir()):
        parser.error("output directory must be empty")
    if args.check and {p.name for p in target.iterdir()} != set(versions):
        parser.error("map directories and catalog disagree")

    for version, records in versions.items():
        folder = target / version
        manifest, outline = version_manifest(catalog["repository"], commit, version, records)
        content = (json.dumps(manifest, indent=2) + "\n").encode()
        manifest_path = folder / "manifest.json"
        if args.check:
            if manifest_path.read_bytes() != content:
                raise ValueError(f"{version}: source manifest drift")
        else:
            folder.mkdir(parents=True)
            manifest_path.write_bytes(content)
        cmd = [sys.executable, str(TEMPLATE), str(manifest_path), str(folder)]
        if args.check:
            cmd.append("--check")
        subprocess.run(cmd, cwd=ROOT, check=True)
        receipt = json.loads((folder / "receipt.json").read_bytes())
        outline_bytes = render_outline(version, catalog["repository"], receipt, outline).encode()
        outline_path = folder / "README.md"
        if args.check:
            if outline_path.read_bytes() != outline_bytes:
                raise ValueError(f"{version}: map outline drift")
        else:
            outline_path.write_bytes(outline_bytes)
    print(f"Graphify verified {len(versions)} maps covering {sum(map(len, versions.values()))} version records.")


if __name__ == "__main__":
    main()
