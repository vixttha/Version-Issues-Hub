"""Check the standalone README HQ workspace without network access."""

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import unicodedata
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
VERSION = re.compile(r"v[0-9]+(?:\.[0-9]+){2,}")
SHA = re.compile(r"[0-9a-f]{40}")
MARKDOWN_LINK = re.compile(r"!?\[[^\[\]\n]*\]\((<[^>]+>|[^\s)]+)\)")
MARKDOWN_FENCE = re.compile(r" {0,3}(`{3,}|~{3,})(.*)")


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def normalize(value):
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(char for char in normalized if char.isalnum())


def check_registry(errors):
    data = read_json(ROOT / "techniques/registry.json")
    records = data["techniques"]
    if data["schema"] != 1 or not records:
        errors.append("technique registry must use schema 1 and contain at least one record")
    names = {}
    outcomes = {}
    ids = set()
    for record in records:
        slug = record["id"]
        if not SLUG.fullmatch(slug) or slug in ids:
            errors.append(f"invalid or duplicate technique ID: {slug}")
        ids.add(slug)
        if not SLUG.fullmatch(record["outcome_key"]):
            errors.append(f"{slug}: invalid outcome key")
        if record["status"] not in {"active", "retired"}:
            errors.append(f"{slug}: invalid technique status")
        keys = ("title", "problem", "practice", "outcome")
        if any(not record[key].strip() for key in keys):
            errors.append(f"{slug}: incomplete technique description")
        for value in [slug, record["title"], *record["aliases"]]:
            key = normalize(value)
            existing = names.setdefault(key, slug)
            if not key or existing != slug:
                errors.append(f"{slug}: technique name collision for {value!r} with {existing}")
        for value in (record["outcome_key"], record["outcome"]):
            key = normalize(value)
            existing = outcomes.setdefault(key, slug)
            if not key or existing != slug:
                errors.append(f"{slug}: technique outcome collision for {value!r} with {existing}")
        evidence = record["evidence"]
        urls = set()
        if not evidence:
            errors.append(f"{slug}: missing evidence")
        for item in evidence:
            url = urlsplit(item["url"])
            if url.scheme != "https" or not url.netloc or item["status"] not in {"observed", "verified"}:
                errors.append(f"{slug}: invalid evidence {item!r}")
            if item["url"] in urls:
                errors.append(f"{slug}: duplicate evidence URL {item['url']}")
            urls.add(item["url"])
    return records


def inside(parent, path):
    target = (parent / path).resolve()
    if not target.is_relative_to(parent):
        raise ValueError(f"path escapes {parent}: {path}")
    return target


def check_history(errors):
    data = read_json(ROOT / "history/sources.json")
    snapshots = data["snapshots"]
    if data["schema"] != 1 or not snapshots:
        errors.append("historical source manifest must use schema 1 and contain snapshots")
    history = ROOT / "history"
    archived = set()
    for snapshot in snapshots:
        prefix = inside(ROOT, snapshot["directory"])
        if prefix == history or not prefix.is_relative_to(history):
            errors.append(f"invalid snapshot directory: {snapshot['directory']}")
            continue
        if not SHA.fullmatch(snapshot["commit"]) or not snapshot["files"]:
            errors.append(f"{snapshot['directory']}: invalid commit SHA or empty snapshot")
        for record in snapshot["files"]:
            file = inside(prefix, record["path"])
            if file in archived:
                errors.append(f"repeated archive entry: {file.relative_to(ROOT)}")
            archived.add(file)
            if not file.is_file():
                errors.append(f"missing archived file: {file.relative_to(ROOT)}")
                continue
            content = file.read_bytes()
            header = f"blob {len(content)}\0".encode("ascii")
            if hashlib.sha1(header + content).hexdigest() != record["blob"]:
                errors.append(f"source blob mismatch: {file.relative_to(ROOT)}")
    wrapper = {history / "README.md", history / "sources.json"}
    actual = {path for path in history.rglob("*") if path.is_file()} - wrapper
    for path in sorted(actual - archived):
        errors.append(f"untracked archive provenance: {path.relative_to(ROOT)}")
    return len(archived)


def markdown_lines(path):
    fence = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        match = MARKDOWN_FENCE.match(line)
        if match:
            marker, tail = match.groups()
            if not fence:
                fence = marker
            elif marker.startswith(fence) and not tail.strip():
                fence = ""
        elif not fence:
            yield line


def headings(path):
    seen = set()
    counters = Counter()
    for line in markdown_lines(path):
        match = re.match(r" {0,3}#{1,6}\s+(.+?)\s*#*\s*$", line)
        if not match:
            continue
        label = re.sub(r"<[^>]*>|\[([^\]]+)\]\([^)]*\)", lambda m: m[1] or "", match[1])
        slug = "".join(c for c in label.lower().replace(" ", "-") if c.isalnum() or c in "-_")
        candidate = slug
        while candidate in seen:
            counters[slug] += 1
            candidate = f"{slug}-{counters[slug]}"
        seen.add(candidate)
    return seen


def check_navigation(errors):
    paths = [
        ROOT / "README.md", ROOT / "README-GUIDE.md", ROOT / "AGENTS.md",
        ROOT / "history/README.md", ROOT / "techniques/README.md",
        ROOT / "graphify-hq/README.md", *sorted((ROOT / "graphify-hq/maps").glob("*/README.md")),
        *sorted((ROOT / "audits").rglob("*.md")), *sorted((ROOT / "versions").rglob("*.md")),
        *sorted((ROOT / "workspace").rglob("*.md")),
    ]
    count = 0
    for path in paths:
        for line in markdown_lines(path):
            for raw in MARKDOWN_LINK.findall(line):
                url = urlsplit(raw.strip("<>"))
                if url.scheme or url.netloc:
                    continue
                base = path.relative_to(ROOT)
                target = inside(ROOT, path.parent / unquote(url.path)) if url.path else path
                fragment = unquote(url.fragment)
                if not target.exists():
                    errors.append(f"{base}: missing local target {raw}")
                elif fragment and target.suffix == ".md" and fragment not in headings(target):
                    errors.append(f"{base}: missing local heading {raw}")
                count += 1
    return count


def check_versions(errors):
    versions = ROOT / "versions"
    index = (versions / "README.md").read_text(encoding="utf-8")
    directories = sorted(path for path in versions.iterdir() if path.is_dir())
    if not directories:
        errors.append("missing standalone versions")
    for path in directories:
        if not VERSION.fullmatch(path.name):
            errors.append(f"invalid standalone version directory: {path.name}")
        if f"]({path.name}/README.md)" not in index:
            errors.append(f"version index is missing {path.name}")
        if not (path / "CHANGELOG.md").is_file():
            errors.append(f"missing changelog for {path.name}")
    return len(directories)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="print the technique index after validation")
    args = parser.parse_args()
    errors = []
    try:
        records = check_registry(errors)
        files = check_history(errors)
        versions = check_versions(errors)
        links = check_navigation(errors)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print(f"Validated {versions} standalone version(s), {len(records)} techniques, "
          f"{links} local links, and {files} imported files.")
    if args.list:
        for record in sorted(records, key=lambda item: item["id"]):
            print(f"{record['id']} [{record['status']}] — {record['title']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
