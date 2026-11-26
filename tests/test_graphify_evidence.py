import copy
import hashlib
import unittest

from tools import graphify_evidence


class GraphifyEvidenceTests(unittest.TestCase):
    def test_partition_preserves_every_feature_in_order(self):
        for count, sizes in ((1, [1]), (32, [32]), (33, [32, 1]), (65, [32, 32, 1])):
            with self.subTest(count=count):
                manifest = {"features": [{"id": f"f-{i}"} for i in range(count)], "source_commit": "a" * 40}
                original = copy.deepcopy(manifest)
                shards = graphify_evidence.partition(manifest)
                self.assertEqual([len(s["features"]) for s in shards], sizes)
                self.assertEqual([f for s in shards for f in s["features"]], manifest["features"])
                self.assertTrue(all(s["source_commit"] == manifest["source_commit"] for s in shards))
                self.assertEqual(manifest, original)

    def test_duplicate_cross_shard_and_empty_inventory_refused(self):
        for features in ([], [{"id": str(i)} for i in range(32)] + [{"id": "0"}]):
            with self.assertRaises(ValueError):
                graphify_evidence.partition({"features": features})

    def test_shard_receipt_must_cover_exact_manifest_and_graph(self):
        graph = b"graph"
        manifest = {"features": [{"id": "f-1"}], "source_commit": "a" * 40, "repository": "owner/repo"}
        receipt = {"source_commit": manifest["source_commit"], "repository": manifest["repository"],
                   "mcp_verified": True, "feature_links": {"feature:f-1": {}},
                   "graph_sha256": hashlib.sha256(graph).hexdigest()}
        graphify_evidence.verify_shard(manifest, receipt, graph)
        for key, value in (("source_commit", "b" * 40), ("repository", "other/repo"),
                           ("mcp_verified", 1), ("feature_links", {}), ("graph_sha256", "0" * 64)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                graphify_evidence.verify_shard(manifest, {**receipt, key: value}, graph)

    def test_closure_graph_groups_cover_all_tests_within_mapper_limit(self):
        import ast
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root / "docs/receipt-evidence.json").read_text(encoding="utf-8"))
        groups = [f for f in manifest["features"] if f["id"] in ("v0-0-0-40", "v0-0-0-40-execution")]
        self.assertEqual(len(groups), 2)
        source = ast.parse((root / "tests/test_issue_closure.py").read_text(encoding="utf-8"))
        expected = {f"def {node.name}(self):" for node in ast.walk(source)
                    if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")}
        actual = [ref["anchor"] for group in groups for ref in group["tested_by"]
                  if ref["path"] == "tests/test_issue_closure.py"]
        self.assertEqual(set(actual), expected)
        self.assertEqual(len(actual), len(expected))
        for group in manifest["features"]:
            for relation in ("documented_in", "changed_in", "implemented_in", "tested_by"):
                self.assertTrue(1 <= len(group[relation]) <= 12, (group["id"], relation))

    def test_integration_integrity_graph_anchors_match_exact_source(self):
        import json
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        manifest = json.loads((root / "docs/receipt-evidence.json").read_text(encoding="utf-8"))
        groups = [f for f in manifest["features"] if f["id"] == "v0-0-0-43"]
        self.assertEqual(len(groups), 1)
        for relation in ("documented_in", "changed_in", "implemented_in", "tested_by"):
            for ref in groups[0][relation]:
                lines = (root / ref["path"]).read_text(encoding="utf-8").splitlines()
                with self.subTest(relation=relation, path=ref["path"], anchor=ref["anchor"]):
                    self.assertEqual(sum(ref["anchor"] in line for line in lines), 1)
