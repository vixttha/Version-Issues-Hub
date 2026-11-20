"""Build or verify a deterministic feature evidence graph from a pinned Git commit."""

import argparse
import asyncio
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from importlib.metadata import version
from pathlib import Path, PurePosixPath

from graphify.build import build_from_json
from graphify.export import to_json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from github_provenance import COMMIT, REPOSITORY, verify_pull_request

TEMPLATE_VERSION = "v0.0.8"
RELATIONS = ("documented_in", "changed_in", "tested_by")
OPTIONAL_RELATION = "implemented_in"
FEATURE_ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
BRANCH = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,159}")
MAX_SOURCE_BYTES = 1_000_000


def valid_path(path):
    if not isinstance(path, str) or not 0 < len(path) <= 240 or not path.isprintable():
        return False
    candidate = PurePosixPath(path)
    return (
        not candidate.is_absolute() and candidate.as_posix() == path
        and not any(part in {".", "..", ".git"} for part in path.split("/"))
        and not any(char in path for char in "\\:")
    )


def validate_manifest(data):
    required = {"repository", "source_commit", "title", "features"}
    if not isinstance(data, dict) or set(data) - {"pull_request", "source_files"} != required:
        raise ValueError("Expected repository, source_commit, title, features and optional pull_request and source_files")
    if not isinstance(data["repository"], str) or not REPOSITORY.fullmatch(data["repository"]):
        raise ValueError("Expected a GitHub owner/repository")
    if not isinstance(data["source_commit"], str) or not COMMIT.fullmatch(data["source_commit"]):
        raise ValueError("Expected a full Git commit SHA")
    title = data["title"]
    if not isinstance(title, str) or not title.strip() or len(title) > 120 or not title.isprintable():
        raise ValueError("Invalid map title")
    inventory = data.get("source_files", [])
    if (
        not isinstance(inventory, list) or len(inventory) > 64
        or not all(valid_path(path) for path in inventory)
        or len(inventory) != len(set(inventory))
    ):
        raise ValueError("Expected up to 64 unique source file paths")
    if "pull_request" in data:
        pr = data["pull_request"]
        if (
            not isinstance(pr, dict) or set(pr) != {"number", "source_branch"}
            or type(pr["number"]) is not int or pr["number"] < 1
            or not isinstance(pr["source_branch"], str) or not BRANCH.fullmatch(pr["source_branch"])
            or any(token in pr["source_branch"] for token in ("..", "//"))
            or pr["source_branch"].endswith(("/", "."))
        ):
            raise ValueError("Expected a positive PR number and a plain source branch name")
    features = data["features"]
    if not isinstance(features, list) or len(features) > 32:
        raise ValueError("Expected at most 32 features")
    ids = set()
    for feature in features:
        if not isinstance(feature, dict) or set(feature) - {OPTIONAL_RELATION} != {"id", "label", *RELATIONS}:
            raise ValueError("Expected an ID, label and reference lists")
        identity, label = feature["id"], feature["label"]
        if (
            not isinstance(identity, str) or len(identity) > 80 or not FEATURE_ID.fullmatch(identity)
            or identity in ids
            or not isinstance(label, str) or not label.strip() or len(label) > 120 or not label.isprintable()
        ):
            raise ValueError("Invalid or duplicate feature")
        ids.add(identity)
        for relation in (*RELATIONS, OPTIONAL_RELATION):
            if relation not in feature:
                continue
            refs = feature[relation]
            if not isinstance(refs, list) or not 1 <= len(refs) <= 12:
                raise ValueError(f"{identity}: {relation} requires one to twelve references")
            seen = set()
            for ref in refs:
                if not isinstance(ref, dict) or set(ref) != {"path", "anchor"}:
                    raise ValueError("Expected a path and source anchor")
                path, anchor = ref["path"], ref["anchor"]
                if (
                    not valid_path(path)
                    or not isinstance(anchor, str) or not 0 < len(anchor) <= 500
                    or not anchor.isprintable() or anchor.strip() != anchor
                    or (path, anchor) in seen
                ):
                    raise ValueError("Invalid or duplicate source link")
                seen.add((path, anchor))
    return data


def git(*args):
    return subprocess.check_output(["git", *args])


def source_lines(commit, path):
    object_name = f"{commit}:{path}"
    if git("cat-file", "-t", object_name).strip() != b"blob":
        raise ValueError("Expected a source blob: " + path)
    if not 0 < int(git("cat-file", "-s", object_name)) <= MAX_SOURCE_BYTES:
        raise ValueError("Source blob is empty or exceeds the size limit: " + path)
    body = git("cat-file", "blob", object_name)
    return body.decode("utf-8").splitlines(), hashlib.sha256(body).hexdigest()


def locate(lines, anchor, path):
    matches = [i for i, line in enumerate(lines, 1) if line.strip() == anchor]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one match in {path}, found {len(matches)}: {anchor}")
    return matches[0]


def build(manifest, folder):
    commit = manifest["source_commit"]
    if git("cat-file", "-t", commit).strip() != b"commit":
        raise ValueError("Pinned SHA must identify a commit")
    nodes, edges = {}, []
    cache, evidence = {}, {}
    inventory = set(manifest.get("source_files", []))
    linked_refs = set()
    root = "source:" + commit

    def add_node(identity, label, kind, path="", line=None):
        nodes[identity] = {
            "id": identity, "label": label, "file_type": kind,
            "source_file": path, "source_location": f"L{line}" if line else None,
        }

    def add_edge(start, end, relation, path="", line=None):
        edges.append({
            "source": start, "target": end, "relation": relation, "source_file": path,
            "source_location": f"L{line}" if line else None, "confidence": "EXTRACTED",
            "confidence_score": 1.0, "weight": 1.0,
        })

    add_node(root, manifest["title"], "concept")
    for path in sorted(inventory):
        cache[path] = source_lines(commit, path)
        add_node("file:" + path, path, "file", path)
        add_edge(root, "file:" + path, "contains_source", path)
    for feature in sorted(manifest["features"], key=lambda feature: feature["id"]):
        feature_id = "feature:" + feature["id"]
        evidence[feature_id] = {}
        add_node(feature_id, feature["label"], "concept")
        add_edge(root, feature_id, "contains_feature")
        for relation in (*RELATIONS, OPTIONAL_RELATION):
            if relation not in feature:
                continue
            refs = sorted(feature[relation], key=lambda ref: (ref["path"], ref["anchor"]))
            evidence[feature_id][relation] = len(refs)
            for ref in refs:
                path, anchor = ref["path"], ref["anchor"]
                if path not in cache:
                    cache[path] = source_lines(commit, path)
                lines, _ = cache[path]
                line = locate(lines, anchor, path)
                ref_id = f"{relation}:{path}:L{line}"
                kind = "code" if relation in ("tested_by", OPTIONAL_RELATION) else "document"
                add_node(ref_id, f"{path} L{line}", kind, path, line)
                add_edge(feature_id, ref_id, relation, path, line)
                if path in inventory and ref_id not in linked_refs:
                    add_edge(ref_id, "file:" + path, "located_in", path, line)
                    linked_refs.add(ref_id)

    graph = build_from_json(
        {"nodes": list(nodes.values()), "edges": edges}, directed=True, dedup=False,
    )
    graph.graph.update(template_version=TEMPLATE_VERSION, scope="feature-evidence")
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "graph.json"
    to_json(graph, {0: list(graph)}, str(path), built_at_commit=commit)
    receipt = {
        "schema_version": 1,
        "template_version": TEMPLATE_VERSION,
        "repository": manifest["repository"],
        "source_commit": commit,
        "pull_request": manifest.get("pull_request"),
        "scope": "feature-evidence",
        "graphify_version": version("graphifyy"),
        "graph_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "feature_links": evidence,
        "source_files": sorted(inventory),
        "source_sha256": {key: value[1] for key, value in sorted(cache.items())},
    }
    return path, receipt


async def verify_mcp(graph, receipt):
    params = StdioServerParameters(command=sys.executable, args=["-m", "graphify.serve", str(graph)])
    async with asyncio.timeout(30), stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            await session.initialize()

            async def query(tool, args):
                result = await session.call_tool(tool, args)
                if result.is_error:
                    raise ValueError("Graphify MCP call failed: " + tool)
                return "\n".join(item.text for item in result.content if item.type == "text")

            stats = await query("graph_stats", {})
            expected = {
                f"Nodes: {receipt['nodes']}", f"Edges: {receipt['edges']}",
                f"Built at commit: {receipt['source_commit']}",
            }
            if not expected <= set(stats.splitlines()):
                raise ValueError("Graphify MCP returned different graph statistics or source SHA")
            for node, relations in receipt["feature_links"].items():
                neighbors = await query("get_neighbors", {"node_id": node, "token_budget": 8000})
                for relation, count in relations.items():
                    found = sum(f"[{relation}]" in line and "-->" in line for line in neighbors.splitlines())
                    if found != count:
                        raise ValueError(f"Graphify MCP {node} {relation}: expected {count}, found {found}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--verify-pr", action="store_true", help="Print a separate live GitHub observation")
    parser.add_argument("--check", action="store_true", help="Rebuild and compare the existing output bytes")
    args = parser.parse_args()
    manifest = validate_manifest(json.loads(args.manifest.read_text(encoding="utf-8")))
    if args.verify_pr:
        if "pull_request" not in manifest:
            parser.error("--verify-pr requires pull_request in the manifest")
        observation = verify_pull_request(
            manifest["repository"], manifest["source_commit"], manifest["pull_request"],
        )
        print("GitHub pull request provenance:\n" + json.dumps(observation, indent=2))

    with tempfile.TemporaryDirectory() as temporary:
        path, receipt = build(manifest, Path(temporary))
        asyncio.run(verify_mcp(path, receipt))
        receipt["mcp_verified"] = True
        files = {"graph.json": path.read_bytes(), "receipt.json": (json.dumps(receipt, indent=2) + "\n").encode()}
        if args.check:
            for name, expected in files.items():
                if (args.output / name).read_bytes() != expected:
                    raise ValueError("Deterministic rebuild differs: " + name)
        else:
            args.output.mkdir(parents=True, exist_ok=True)
            for name, data in files.items():
                (args.output / name).write_bytes(data)
    print(f"Graphify MCP verified {receipt['nodes']} nodes and {receipt['edges']} edges at {receipt['source_commit']}")


if __name__ == "__main__":
    main()
