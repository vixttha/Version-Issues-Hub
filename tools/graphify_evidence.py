"""Partition checkpoint evidence for the pinned Graphify template's 32-feature limit."""
import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys

from tools import checkpoint

LIMIT = 32


def partition(manifest):
    features = manifest["features"]
    if not isinstance(features, list) or not features:
        raise ValueError("Expected nonempty Graphify feature inventory")
    ids = [f["id"] for f in features]
    if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError("Invalid or duplicate Graphify feature IDs")
    return [{**manifest, "features": features[i:i + LIMIT]}
            for i in range(0, len(features), LIMIT)]


def verify_shard(manifest, receipt, graph_bytes):
    expected = {"feature:" + f["id"] for f in manifest["features"]}
    if (receipt["source_commit"] != manifest["source_commit"]
            or receipt["repository"] != manifest["repository"]
            or receipt["mcp_verified"] is not True
            or set(receipt["feature_links"]) != expected
            or receipt["graph_sha256"] != hashlib.sha256(graph_bytes).hexdigest()):
        raise ValueError("Graphify shard evidence does not match its manifest")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mapper", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    manifest = checkpoint.parse_json(Path("docs/receipt-evidence.json").read_text(encoding="utf-8"))
    manifest.update(repository=os.environ["GITHUB_REPOSITORY"], source_commit=os.environ["GITHUB_SHA"])
    shards = partition(manifest)
    args.output.mkdir(parents=True, exist_ok=False)
    checkpoint.write_json(args.output / "manifest.json", manifest)
    index = []
    for number, shard in enumerate(shards, 1):
        folder = args.output if len(shards) == 1 else args.output / f"shard-{number:04d}"
        folder.mkdir(exist_ok=True)
        path = folder / "manifest.json"
        if len(shards) > 1:
            checkpoint.write_json(path, shard)
        subprocess.run([sys.executable, str(args.mapper), str(path), str(folder)], check=True)
        receipt_bytes = (folder / "receipt.json").read_bytes()
        receipt = checkpoint.parse_json(receipt_bytes)
        verify_shard(shard, receipt, (folder / "graph.json").read_bytes())
        index.append({"directory": folder.relative_to(args.output).as_posix(),
                      "features": [f["id"] for f in shard["features"]],
                      "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest()})
    checkpoint.write_json(args.output / "shards.json", {
        "schema_version": 1, "repository": manifest["repository"],
        "source_commit": manifest["source_commit"], "feature_count": len(manifest["features"]),
        "shards": index})
    print(f"Graphify verified all {len(manifest['features'])} features across {len(shards)} shard(s)")


if __name__ == "__main__":
    main()
