"""Build and check Graphify maps for the approved README HQ templates."""

import argparse
import asyncio
import base64
import gzip
import hashlib
import json
import re
import runpy
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path
from urllib.parse import quote, unquote

from graphify.build import build_from_json
from graphify.export import to_json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = Path(__file__).resolve().parents[2]
MAPS = ROOT / "Graphify HQ"
ARCHIVE = Path("readme-hq/versions")
SOURCES = {"README.md": "Landing page", "GUIDE.md": "Folder guide", "CHANGELOG.md": "Changelog"}
VERSION = re.compile(r"v\d+\.\d+\.\d+")


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def archive_blob(data):
    return hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()


def document_id(name):
    return f"hq:document:{name}"


def read_sources(tag, record):
    sources = {}
    for name in SOURCES:
        path = ARCHIVE / tag / name
        data = (ROOT / path).read_bytes()
        blob = archive_blob(data)
        entry = {"archive_path": path.as_posix(), "blob_sha1": blob}
        if name != "CHANGELOG.md":
            commit = record["source_commits"][name]
            original = record["source_paths"][name]
            if record["snapshots"][name] != blob or git("show", f"{commit}:{original}") != data:
                raise ValueError(f"{path} differs from its pinned template source")
            entry.update(source_commit=commit, source_path=original)
        sources[name] = (entry, data.decode())
    return sources


def map_template(tag, sources, checker, out):
    nodes = {}
    edges = {}
    outlines = {name: [] for name in SOURCES}

    def node(key, label, kind, path="", line=None):
        nodes[key] = {"id": key, "label": label, "file_type": kind, "source_file": path,
                      "source_location": f"L{line}" if line else None}

    def edge(start, end, relation, evidence, line=None):
        edges[start, end, relation] = {
            "source": start, "target": end, "relation": relation,
            "source_file": evidence, "source_location": f"L{line}" if line else None,
            "confidence": "EXTRACTED", "confidence_score": 1.0, "weight": 1.0,
        }

    node(tag, f"README HQ template {tag}", "concept")
    for name, (entry, markdown) in sources.items():
        path = entry["archive_path"]
        document = document_id(name)
        node(document, SOURCES[name], "document", path, 1)
        edge(tag, document, "contains_document", path, 1)
        stack = []
        for number, depth, title, slug in checker["markdown_headings"](markdown):
            while stack and stack[-1][0] >= depth:
                stack.pop()
            key = f"{name}:L{number}"
            node(key, title, "concept", path, number)
            edge(stack[-1][1] if stack else document, key, "contains_section", path, number)
            stack.append((depth, key))
            if depth > 1:
                label = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", title)
                label = re.sub(r"([\\\[\]])", r"\\\1", label)
                outlines[name].append((label, quote(slug, safe="-_")))

        for href in checker["markdown_links"](markdown):
            url = checker["parse_link_url"](href, path)
            github = checker["github_target"](url)
            target = checker["workspace_target"](ROOT, ROOT / path, url, github)
            if target is not None and target.resolve().is_relative_to(ROOT):
                reference = target.resolve().relative_to(ROOT).as_posix()
                if reference == path:
                    continue
            elif github:
                reference = f"{github[1]}:{unquote(github[2])}"
            elif url.netloc == "github.com" and re.fullmatch(
                re.escape(checker["REPO_PREFIX"]) + r"pull/\d+", url.path
            ):
                reference = f"PR #{url.path.rsplit('/', 1)[1]}"
            else:
                continue
            archived = Path(reference)
            if archived.parent == ARCHIVE / tag and archived.name in sources:
                destination = document_id(archived.name)
            else:
                destination = f"reference:{reference}"
                node(destination, reference, "concept")
            edge(document, destination, "links_to", path)

    graph = build_from_json({"nodes": list(nodes.values()), "edges": list(edges.values())},
                            directed=True, dedup=False)
    graph.graph.update(template_version=tag, scope="readme_hq_template")
    out.mkdir(parents=True)
    graph_path = out / "graph.json"
    to_json(graph, {0: list(graph)}, str(graph_path), built_at_commit="")
    receipt = {
        "schema_version": 1,
        "template_version": tag,
        "source_ref": "refs/heads/readme-hq",
        "graphify_version": version("graphifyy"),
        "graph_sha256": hashlib.sha256(graph_path.read_bytes()).hexdigest(),
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "sources": {name: entry for name, (entry, _) in sources.items()},
    }
    (out / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    lines = [f"# README HQ template {tag}", "",
             "[Graphify map](graph.json) · [Source receipt](receipt.json) · [All versions](../README.md)", ""]
    for name, title in SOURCES.items():
        entry = receipt["sources"][name]
        lines.extend([f"## {title}", "", f"[Archived {title.lower()}](../../{entry['archive_path']})", ""])
        lines.extend(f"- [{label}](../../{entry['archive_path']}#{slug})" for label, slug in outlines[name])
        if outlines[name]:
            lines.append("")
    (out / "README.md").write_text("\n".join(lines), encoding="utf-8")
    return receipt


async def verify(out, receipt):
    graph_path = out / "graph.json"
    params = StdioServerParameters(command=sys.executable, args=["-m", "graphify.serve", str(graph_path)])
    async with asyncio.timeout(30), stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            result = await session.call_tool("graph_stats", {})
            stats = "\n".join(item.text for item in result.content if item.type == "text")
            if result.is_error or not {f"Nodes: {receipt['nodes']}", f"Edges: {receipt['edges']}"} <= set(stats.splitlines()):
                raise ValueError(f"{out.name}: Graphify MCP statistics differ from the export")
            for name, entry in receipt["sources"].items():
                result = await session.call_tool("get_node", {"node_id": document_id(name)})
                source = f"Source: {entry['archive_path']} L1"
                reply = "\n".join(item.text for item in result.content if item.type == "text")
                if result.is_error or source not in reply:
                    raise ValueError(f"{out.name}: Graphify MCP could not locate {name}: {reply[:600]}")


def compare(output):
    expected = {p.relative_to(output): p for p in output.rglob("*") if p.is_file()}
    current = {p.relative_to(MAPS): p for p in MAPS.rglob("*") if p.is_file()}
    extra = sorted(current.keys() - expected.keys())
    changed = sorted(path for path in current.keys() & expected.keys()
                     if current[path].read_bytes() != expected[path].read_bytes())
    missing = sorted(expected.keys() - current.keys())
    for label, paths in (("Unexpected", extra), ("Changed", changed), ("Missing", missing)):
        for path in paths:
            print(f"{label}: {MAPS.name}/{path.as_posix()}")
    updates = missing + ([Path("README.md")] if Path("README.md") in changed else [])
    if updates:
        payload = json.dumps({path.as_posix(): expected[path].read_text(encoding="utf-8") for path in updates},
                             ensure_ascii=False).encode()
        encoded = base64.b64encode(gzip.compress(payload, mtime=0)).decode()
        if len(encoded) <= 100_000:
            for offset in range(0, len(encoded), 4_000):
                print(f"GRAPHIFY_MAPS_EXPORT {encoded[offset:offset + 4_000]}")
    return bool(extra or changed or missing)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Empty output directory outside Graphify HQ")
    parser.add_argument("--check", action="store_true", help="Require committed maps to match the rebuild")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        parser.error("output must be absent or empty")
    checker = runpy.run_path(str(ROOT / "tools/check_readme_hq.py"))
    manifest = json.loads((ROOT / "tools/readme_hq_baselines.json").read_bytes())["readme_hq"]
    archives = {p.name for p in (ROOT / ARCHIVE).iterdir() if p.is_dir()}
    if not manifest or archives != manifest.keys() or not all(VERSION.fullmatch(tag) for tag in archives):
        raise ValueError("README HQ archive folders do not match the template baseline manifest")
    for tag, record in sorted(manifest.items()):
        out = output / tag
        receipt = map_template(tag, read_sources(tag, record), checker, out)
        asyncio.run(verify(out, receipt))
        print(f"{tag}: Graphify MCP passed for three frozen template documents, "
              f"{receipt['nodes']} nodes, {receipt['edges']} edges, SHA-256 {receipt['graph_sha256']}")
    lines = ["# Graphify HQ", "",
             "Open a map for an approved [README HQ template version](../readme-hq/versions/README.md).",
             "Each graph indexes that version’s archived landing page, folder guide, and changelog.",
             "Links to other repository files appear as references.", ""]
    for tag in sorted(archives, key=lambda item: tuple(map(int, item[1:].split("."))), reverse=True):
        lines.append(f"- [{tag}]({tag}/README.md)")
    lines.extend(["", "[Generate a map for the next approved version](../tools/graphify/README.md)", ""])
    (output / "README.md").write_text("\n".join(lines), encoding="utf-8")
    if args.check and compare(output):
        sys.exit("Commit one matching Graphify HQ folder for every approved README HQ template version")


if __name__ == "__main__":
    main()
