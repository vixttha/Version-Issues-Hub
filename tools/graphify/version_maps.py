"""Rebuild and verify the maps for archived Test Vault template versions."""

import argparse
import ast
import asyncio
import base64
import hashlib
import json
import posixpath
import re
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit

from graphify.build import build_from_json
from graphify.export import to_json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "versions"
MAPS = ROOT / "Graphify HQ"
UPSTREAM = "https://github.com/vixttha/AlderVale-Pact-of-Ten.git"
VERSION = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+")
HEADING = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)\s*#*\s*$")
FENCE = re.compile(r"^ {0,3}(\x60{3,}|~{3,})")
LINK = re.compile(r"\[[^\]\n]+\]\(([^()\s]+)(?:\s+[^()]*)?\)")


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def fetch_source(commit):
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("expected a full pinned upstream commit")
    query = subprocess.run(
        ["git", "-C", str(ROOT), "cat-file", "-e", f"{commit}^{{commit}}"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False,
    )
    if query.returncode:
        git("fetch", "--no-tags", "--depth=1", UPSTREAM, commit)
        git("cat-file", "-e", f"{commit}^{{commit}}")


def read_archive(tag, record):
    commit, source = record["source_commit"], record["source_path"]
    if not re.fullmatch(r"[0-9a-f]{40}", commit) or not source or source.startswith("/") or ".." in PurePosixPath(source).parts:
        raise ValueError(f"{tag}: expected a pinned commit and a relative source directory")
    tree = git("ls-tree", "-r", "-z", f"{commit}:{source}")
    expected = {}
    for entry in tree.split(b"\0"):
        if not entry:
            continue
        meta, name = entry.decode().split("\t", 1)
        mode, kind, blob = meta.split()
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise ValueError(f"{tag}: unsupported archived file {name}")
        expected[name] = (mode, blob)
    directory = ARCHIVE / tag
    archived = {p.relative_to(directory).as_posix(): p for p in directory.rglob("*") if p.is_file()}
    if not expected or archived.keys() != expected.keys():
        raise ValueError(f"{tag}: archived file inventory differs from {commit}:{source}")
    tracked_modes = {}
    relative_directory = directory.relative_to(ROOT).as_posix()
    for entry in git("ls-files", "--stage", "-z", "--", relative_directory + "/").split(b"\0"):
        if not entry:
            continue
        meta, path = entry.decode().split("\t", 1)
        mode, _, stage = meta.split()
        if stage != "0":
            raise ValueError(f"{tag}: unmerged archive file {path}")
        tracked_modes[path.removeprefix(relative_directory + "/")] = mode
    if tracked_modes.keys() != expected.keys():
        raise ValueError(f"{tag}: tracked archive inventory differs from {commit}:{source}")
    sources = {}
    for name, (mode, digest) in sorted(expected.items()):
        if tracked_modes[name] != mode:
            raise ValueError(
                f"{tag}: archived Git mode differs for {name} "
                f"(expected {mode}, found {tracked_modes[name]})"
            )
        path = archived[name]
        data = path.read_bytes()
        if path.is_symlink() or hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest() != digest:
            raise ValueError(f"{tag}: archived bytes differ for {name}")
        sources[name] = (path.relative_to(ROOT).as_posix(), digest, data.decode("utf-8"))
    return sources


def file_id(name):
    return f"file:{name}"


def markdown_sections(content):
    fence = None
    for number, line in enumerate(content.splitlines(), 1):
        delimiter = FENCE.match(line)
        if delimiter:
            token = delimiter[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence) and not line[delimiter.end():].strip():
                fence = None
            continue
        if not fence and (heading := HEADING.match(line)):
            yield number, len(heading[1]), heading[2]


def build_map(tag, record, sources, output):
    nodes, edges = {}, {}

    def node(key, label, kind, path="", line=None):
        nodes[key] = {"id": key, "label": label, "file_type": kind, "source_file": path,
                      "source_location": f"L{line}" if line else None}

    def edge(start, end, relation, path, line=None):
        edges[start, end, relation] = {
            "source": start, "target": end, "relation": relation, "source_file": path,
            "source_location": f"L{line}" if line else None, "confidence": "EXTRACTED",
            "confidence_score": 1.0, "weight": 1.0,
        }

    node(tag, f"Test Vault template {tag}", "concept")
    for name, (path, _, content) in sources.items():
        key = file_id(name)
        kind = "document" if name.endswith(".md") else "code"
        node(key, name, kind, path, 1)
        edge(tag, key, "contains_file", path, 1)
        if name.endswith(".md"):
            stack = []
            for number, level, title in markdown_sections(content):
                while stack and stack[-1][0] >= level:
                    stack.pop()
                child = f"{key}:L{number}"
                node(child, title, "concept", path, number)
                edge(stack[-1][1] if stack else key, child, "contains_section", path, number)
                stack.append((level, child))
            for link in LINK.findall(content):
                parsed = urlsplit(link)
                if parsed.scheme or parsed.netloc or not parsed.path or parsed.path.startswith("/"):
                    continue
                target = posixpath.normpath(posixpath.join(posixpath.dirname(name), unquote(parsed.path)))
                if target in sources and target != name:
                    edge(key, file_id(target), "links_to", path)
        elif name.endswith(".py"):
            for item in ast.parse(content, filename=path).body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    child = f"{key}:L{item.lineno}"
                    node(child, item.name, "code", path, item.lineno)
                    edge(key, child, "defines", path, item.lineno)

    graph = build_from_json({"nodes": list(nodes.values()), "edges": list(edges.values())},
                            directed=True, dedup=False)
    graph.graph.update(template_version=tag, scope="test_vault_template")
    output.mkdir(parents=True)
    graph_path = output / "graph.json"
    to_json(graph, {0: list(graph)}, str(graph_path), built_at_commit=record["source_commit"])
    receipt = {
        "schema_version": 1,
        "template_version": tag,
        "source_commit": record["source_commit"],
        "source_path": record["source_path"],
        "graphify_version": version("graphifyy"),
        "graph_sha256": hashlib.sha256(graph_path.read_bytes()).hexdigest(),
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "sources": {name: {"archive_path": path, "blob_sha1": blob} for name, (path, blob, _) in sources.items()},
    }
    (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    lines = [f"# Test Vault template {tag}", "",
             "[Graphify map](graph.json) · [Source receipt](receipt.json) · [All versions](../README.md)", "",
             "## Indexed files", ""]
    lines.extend(f"- [{name}](../../{entry['archive_path']})" for name, entry in receipt["sources"].items())
    (output / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return receipt


async def verify(output, receipt):
    server = StdioServerParameters(command=sys.executable, args=["-m", "graphify.serve", str(output / "graph.json")])
    async with asyncio.timeout(30), stdio_client(server) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()
            result = await session.call_tool("graph_stats", {})
            stats = {line for item in result.content if item.type == "text" for line in item.text.splitlines()}
            expected = {f"Nodes: {receipt['nodes']}", f"Edges: {receipt['edges']}",
                        f"Built at commit: {receipt['source_commit']}"}
            if result.is_error or not expected <= stats:
                raise ValueError(f"{output.name}: Graphify MCP statistics differ from the export")
            for name, entry in receipt["sources"].items():
                result = await session.call_tool("get_node", {"node_id": file_id(name)})
                reply = "\n".join(item.text for item in result.content if item.type == "text")
                if result.is_error or f"Source: {entry['archive_path']} L1" not in reply:
                    raise ValueError(f"{output.name}: Graphify MCP could not resolve {name}: {reply[:400]}")


def compare(output, export_missing):
    expected = {p.relative_to(output).as_posix(): p for p in output.rglob("*") if p.is_file()}
    current = {p.relative_to(MAPS).as_posix(): p for p in MAPS.rglob("*") if p.is_file()}
    extra = sorted(current.keys() - expected.keys())
    changed = sorted(key for key in current.keys() & expected.keys()
                     if current[key].is_symlink() or current[key].read_bytes() != expected[key].read_bytes())
    missing = sorted(expected.keys() - current.keys())
    for label, paths in (("Unexpected", extra), ("Changed", changed), ("Missing", missing)):
        for path in paths:
            print(f"{label}: {MAPS.name}/{path}")
    updates = missing + (["README.md"] if "README.md" in changed else [])
    if export_missing and updates:
        payload = json.dumps({key: expected[key].read_text(encoding="utf-8") for key in updates})
        encoded = base64.b64encode(payload.encode()).decode()
        if len(encoded) > 300_000:
            raise ValueError("Map export exceeded the bootstrap log budget")
        for index, offset in enumerate(range(0, len(encoded), 3000)):
            print(f"TEST_VAULT_MAP_EXPORT {index:04d} {encoded[offset:offset + 3000]}")
    return bool(extra or changed or missing)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--export-missing", action="store_true", help="Emit missing map files and an updated index in CI logs")
    parser.add_argument("--fetch-upstream", action="store_true", help="fetch the pinned public AlderVale commits")
    args = parser.parse_args()
    output = args.output.resolve()
    if output == MAPS or output.is_relative_to(MAPS) or (output.exists() and (not output.is_dir() or any(output.iterdir()))):
        parser.error("output must be an empty directory outside Graphify HQ")
    manifest = json.loads((ARCHIVE / "manifest.json").read_text(encoding="utf-8"))
    versions = manifest["versions"]
    frames = {path.name for path in ARCHIVE.iterdir() if path.is_dir()}
    if (manifest["schema_version"] != 1 or manifest["current"] not in versions or frames != versions.keys()
            or not all(VERSION.fullmatch(tag) for tag in versions)):
        raise ValueError("Version manifest and archive folders do not match")
    sorted_versions = sorted(versions, key=lambda tag: tuple(map(int, tag[1:].split("."))), reverse=True)
    for tag in sorted_versions:
        record = versions[tag]
        if args.fetch_upstream:
            fetch_source(record["source_commit"])
        sources = read_archive(tag, record)
        receipt = build_map(tag, record, sources, output / tag)
        asyncio.run(verify(output / tag, receipt))
        print(f"{tag}: Graphify MCP verified {len(sources)} archived files, {receipt['nodes']} nodes, "
              f"{receipt['edges']} edges, SHA-256 {receipt['graph_sha256']}")
    index = ["# Graphify HQ", "", "Maps for the [archived Test Vault templates](../versions/README.md).", "",
             f"Current archived version is **{manifest['current']}**.", ""]
    index.extend(f"- [{tag}]({tag}/README.md)" for tag in sorted_versions)
    (output / "README.md").write_text("\n".join(index) + "\n", encoding="utf-8")
    if args.check and compare(output, args.export_missing):
        sys.exit("Commit the matching Graphify HQ map, outline, and receipt for every archived version")
    if args.check:
        print(f"All {len(versions)} committed template maps match their verified rebuilds.")


if __name__ == "__main__":
    main()
