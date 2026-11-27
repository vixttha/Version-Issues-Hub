import copy
import hashlib
import unittest

from tools import graphify_evidence


class GraphifyEvidenceTests(unittest.TestCase):
    def test_version_debt_gate_history_from_veraphify_pins(self):
        """Read all archived cumulative/engineering snapshots, never execute old code."""
        import ast
        import subprocess
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        def git(*args):
            return subprocess.check_output(
                ["git", "--no-replace-objects", "-C", str(root), *args], text=True).strip()
        if git("rev-parse", "--is-shallow-repository") == "true":
            self.skipTest("Historical source scan requires full Git history; Ubuntu verify runs it")
        # Pinned Veraphify indexes at 3ad1297ab05d8377806bec0f5d6800a1116ea562; historical prefixes are
        # reconstructed, not certified historical release/test executions.
        pins = (
            ("v0.0.0.1", "f767cc133f8dba5ebb68b6530e8601dc66879e81", "3543f940ad6bb9dcca30e487521de59110ab49b3", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.2", "fee90e84d981740938989c1a53f70a9570ae2293", "2d171dca028cbe36ae072acadf3f145cefe8d8f0", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.3", "fbb76a77f896fb39290a1b862e7dde1a74ae3a8a", "f36994d00d7d9896ad7653d457bd98400c2ef600", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.4", "1a53dc83cd578faa26b8253e0699646ea58e2dbb", "6b8ea3d8c2aeec0fcb14f1170fdc998a4010dbbe", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.5", "87930df3c14b277cb4ab092ca672df7b0623b763", "7c1b39e49ee32b9a16de6e27bd40500c30a16227", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.6", "cc5de51d5ca2e03622ac18d2c3bf0933f33e252e", "33bc8e8e68dee61c812e5ffd5675d159149f01f2", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.7", "d6df358c67c4fecaefaa725dd7b4687a2f3b89cd", "5ffe3d96cadd6fe368a9b642d2c1d6eebb643d87", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.8", "d5272dbfbe63f721820d01316d0e932503b53062", "30af5b8c1143cd621e0564e1dd09c005c9efedc9", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.9", "0bb2cae91c1673231645e6301c95d333a4a35afd", "5be3be7710da14c21a3945a435c8a398785bfefd", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.10", "65dc35530f98d489b15b0b4fbf147818e1bdf5eb", "eecd80e974222f256a3db454f8177104f5fb239b", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.11", "e3f5f917307f38372277b7aecae3652c85935f80", "15ff438df0efca039e69453b90da1aa1e8c96ab3", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.12", "78decbe8d6ff4eb9ab7e19394cec8790a12ecfae", "ff27fe10d3271e1c4a14e454bd25298b2a312630", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.13", "b6b9d281e55bfed85729533087838f202ae30530", "19ecca06492cb313899c4f2c4bd2c4c1ff085f41", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.14", "9fdbd365702c52850cc6448c71684c9b130a4efd", "e819481ff5208c5a85f49cb8c7111b8f6af207f7", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.15", "cddcb935a2e71bcf167c2096674c4292ea72d232", "f808a31ff437381540be5b1f3981d01159949bf3", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.16", "f2b2620b4f34744f8422a509994547b471cdfc6b", "d4ec1905ee10a431a39ac72cd59aadee18d94f53", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.17", "15396556f7674f27b039520a7538fa76f7ac49c1", "42f39e5c04d2fd78141e1525edd12d9c5477c423", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.18", "8b447acda070c288c8c546c02b041bd726befea1", "a3115bb6da2ea52dea35060db5e947882c2a41c3", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.19", "733a4e51357df6acb8ffc2ddedaede664df22c35", "b7b9397c9fd6ceb3f4edf0c846902f628e8c48e1", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.20", "983e60e7328c9f524633d29e80ca03395fb1d14e", "fd11c73872968929fc3c010ff8494df5062d00bc", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.21", "bdceeb11eb4b33a36065d6db2a74eb48817804c6", "c47fec1abc369afd690a66f35c9b2cd13355f0c0", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.22", "af4ddbd797899d6c68ee7d8d1e92f03bda65f450", "cf15a9a3417a597739de52251ce7a438c5a8d5b4", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.23", "af4ddbd797899d6c68ee7d8d1e92f03bda65f450", "cf15a9a3417a597739de52251ce7a438c5a8d5b4", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.24", "af4ddbd797899d6c68ee7d8d1e92f03bda65f450", "cf15a9a3417a597739de52251ce7a438c5a8d5b4", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.25", "75a16c185f404400b453d3a8a4b5a7becfdea024", "384d040ccf67d3ce7fec6fd8e80b44cb5b078015", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.26", "5a6074d77ec37823f81c6d7ebb1f4593d969cd71", "80222c4f3fd9bb68954b055490c32698ffbb7b77", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.27", "5a6074d77ec37823f81c6d7ebb1f4593d969cd71", "80222c4f3fd9bb68954b055490c32698ffbb7b77", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.28", "5a6074d77ec37823f81c6d7ebb1f4593d969cd71", "80222c4f3fd9bb68954b055490c32698ffbb7b77", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.29", "449e4b493daa1f9906396dae49877a32333c418d", "b45960ee740615821e23e24ec8a41b25307e63b0", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.30", "449e4b493daa1f9906396dae49877a32333c418d", "b45960ee740615821e23e24ec8a41b25307e63b0", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.31", "95e05af7b2a675491a01f8450fb20db8871b1f41", "775517010a1e9622b7b0cab2e7ea36c3f70e8fbf", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.32", "1e85153765c0ca908f2ee44f2973ba59b0669c23", "f771b305338b0bf15d699364595f067b40533c59", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.33", "a7ba4267f65a264c0c50c36bb2bedc3433f019ca", "79ebc42c62a316126dc9d0c67625794ad29d8327", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.34", "635377fbe9165859ad486469aef295e3052d5af9", "39e96bb79ea2ae4c4a27aa7bd7bf16cd16a5ef00", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.35", "07a73f55a2b1f7ecbf873a3921f1e397034a88e6", "c0319ec75fecc2b578057b23c9f518fb3c68083a", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.36", "26e9fe8c019a33c5f84f77a37da70925505204e3", "8d7f57a55d9c5eb905965132bde68a1fca533db0", "reconstructed_cumulative_engineering_prefix"),
            ("v0.0.0.37", "4ebeb16ed99ed2697309343b9ae5b1f54c341ff2", "cb800cdd46108293de31c70ccdb3a72d4945acdd", "actual_engineering_merge"),
            ("v0.0.0.38", "26243de4d616598989bdbc15ac74966241bd9a6c", "97d98cd75e3a0a337e084573675f3c5e16640cbb", "actual_engineering_merge"),
            ("v0.0.0.39", "998c5f4113cd22a6fab1a833ef006acdb0da918d", "32b3f941d1446faaeb7f93f6053533b1dbe5dc16", "actual_engineering_merge"),
            ("v0.0.0.40", "43ef2b660aae5ccee00009e900509158f0137d0f", "413b10757a3f06b16ed61f8a2555233eab3870f4", "actual_engineering_merge"),
            ("v0.0.0.41", "c7a4995c99fed8d1e87970a744c4cde378ebed1e", "7b01c3427f677b5bbdd8b9f23f8d524d3bf6a3e7", "actual_engineering_merge"),
            ("v0.0.0.42", "3160df17f60b3eaa9a9e70e1ca13bffcfe2eb4e8", "90a44d350830bea35eac9f85d523d4ed058b5f49", "actual_engineering_merge"),
        )
        self.assertEqual([v for v, _, _, _ in pins], [f"v0.0.0.{n}" for n in range(1, 43)])
        for version, sha, tree, kind in pins:
            with self.subTest(version=version, revision=sha):
                self.assertEqual(git("rev-parse", sha + "^{tree}"), tree)
                if not git("ls-tree", "--name-only", sha, "--", "tools/session.py"):
                    print("VIB-HISTORY", version, sha, kind, "no-session")
                    continue
                source = git("show", sha + ":tools/session.py")
                nodes = ast.parse(source).body
                functions = {node.name: node for node in nodes if isinstance(node, ast.FunctionDef)}
                claim = functions.get("claim")
                called = {n.func.id for n in ast.walk(claim) if isinstance(n, ast.Call)
                          and isinstance(n.func, ast.Name)} if claim is not None else set()
                self.assertNotIn("require_integration_debt_clear", functions)
                self.assertNotIn("require_integration_debt_clear", called)
                print("VIB-HISTORY", version, sha, kind,
                      "claim-without-debt-gate" if claim is not None else "no-claim")
        prior = "3160df17f60b3eaa9a9e70e1ca13bffcfe2eb4e8"
        head = git("rev-parse", "HEAD")
        self.assertIn("def require_integration_debt_clear(", git("show", head + ":tools/session.py"))
        introductions = git("log", "--format=%H", "--reverse", "-S",
                            "def require_integration_debt_clear(", prior + ".." + head,
                            "--", "tools/session.py").splitlines()
        self.assertEqual(introductions, ["f442a1c21386c6ac1734e8eb15ad48513284fcfd"])
        print("VIB-HISTORY debt-gate-change-commits", ",".join(introductions))
        print("VIB-HISTORY verified", len(pins), "historical source snapshots")

        # Execute the narrow claim/defer reproducer in four immutable source
        # checkouts, using only each revision's own simulated GitHub API.
        import io
        import sys
        import tarfile
        import tempfile
        reproduce = r"""
import json
import sys
from unittest.mock import patch
from pathlib import Path
sys.path[:0] = [str(Path.cwd()), str(Path.cwd() / "tests")]
from tools import session
from test_session import Fake, state
api, s = Fake(), state()
original = api.request
def read_only(method, path, body=None):
    assert method == "GET", (method, path)
    return original(method, path, body)
api.request = read_only
s["ledger"], s["handoff"] = session.claim(api, s, 247, ["first"], "First")
s["ledger"], s["handoff"] = session.advance(api, s, "Review", return_to_head=True)
if sys.argv[1] == "legacy":
    s["ledger"], s["handoff"] = session.finish(api, s, "deferred", "Unbounded")
    _, next_handoff = session.claim(api, s, 248, ["second"], "Unrelated")
    assert next_handoff["active"]["issue"] == 248
    print("unbounded-unrelated-claim-reproduced")
else:
    from test_session import bounded_deferral
    decision = bounded_deferral(s, api, 248)
    expires = json.loads(decision[len(session.DEFERRAL_DECISION):])["expires_at"]
    s["ledger"], s["handoff"] = session.finish(api, s, "deferred", decision, deferral_approved=True)
    s["ledger"], s["handoff"] = session.claim(api, s, 248, ["second"], "Bounded")
    s["ledger"], s["handoff"] = session.advance(api, s, "Review", return_to_head=True)
    s["ledger"], s["handoff"] = session.finish(api, s, "deferred", "Unbounded second")
    with patch.object(session.time, "time", return_value=expires):
        for issue in (247, 248, 249):
            try:
                _, planned = session.claim(api, s, issue, [], "Recovery")
            except ValueError:
                assert issue == 249 or sys.argv[1] == "deadlock", issue
            else:
                assert sys.argv[1] == "broad-exemption" and issue in (247, 248), issue
                assert planned["active"]["issue"] == issue
    print(sys.argv[1] + "-reproduced")
assert not api.writes
"""
        for revision, mode in (
            ("1a53dc83cd578faa26b8253e0699646ea58e2dbb", "legacy"),
            (prior, "legacy"),
            ("f8eb6f42032664acfe50f063d29e401253fea2b0", "broad-exemption"),
            ("974008907a2a3dd5bebb54faa901b34adeedb9b2", "deadlock"),
        ):
            with self.subTest(revision=revision, mode=mode), tempfile.TemporaryDirectory() as tmp:
                archive = subprocess.check_output(["git", "--no-replace-objects", "-C",
                    str(root), "archive", revision, "tools", "tests/test_session.py"])
                with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tf:
                    tf.extractall(tmp, filter="data")
                result = subprocess.run([sys.executable, "-I", "-B", "-c", reproduce, mode],
                    cwd=tmp, text=True, capture_output=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("reproduced", result.stdout)
                print("VIB-HISTORY executable", revision, mode, result.stdout.strip())


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
        import subprocess
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        revision = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
        from functools import lru_cache
        @lru_cache(maxsize=None)
        def blob(path):
            return subprocess.check_output(["git", "-C", str(root), "show", revision + ":" + path]).decode("utf-8")
        manifest = json.loads(blob("docs/receipt-evidence.json"))
        expected = {"v0-0-0-43", "v0-0-0-43-review", "v0-0-0-43-publication", "v0-0-0-43-cbr"}
        groups = [f for f in manifest["features"] if f["id"] in expected]
        self.assertEqual({f["id"] for f in groups}, expected)
        self.assertEqual(len(groups), len(expected))
        for group in manifest["features"]:
            for relation in ("documented_in", "changed_in", "implemented_in", "tested_by"):
                seen = set()
                for ref in group[relation]:
                    lines = blob(ref["path"]).splitlines()
                    with self.subTest(feature=group["id"], relation=relation, path=ref["path"], anchor=ref["anchor"]):
                        self.assertTrue(1 <= len(ref["anchor"]) <= 500 and ref["anchor"].strip() == ref["anchor"] and ref["anchor"].isprintable())
                        key = (ref["path"], ref["anchor"])
                        self.assertNotIn(key, seen)
                        seen.add(key)
                        self.assertEqual(sum(line.strip() == ref["anchor"] for line in lines), 1)
