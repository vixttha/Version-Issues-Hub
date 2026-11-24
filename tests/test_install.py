import base64
import hashlib
import json
import unittest
from tools import install, checkpoint

PIN = "a" * 40
PRODUCT = "b" * 40
TREE = "c" * 40
INSTALLED = "d" * 40
TARGET = "example/existing"
PREFIX = "/repos/" + TARGET

class FakeGitHub:
    def __init__(self):
        self.refs = {"trunk": PRODUCT}
        self.writes = []
        self.entries = {}
        self.metadata = {"id": 42, "full_name": TARGET, "default_branch": "trunk"}
        self.bad_blob = False
        self.package = dict(install.PACKAGE)

    def request(self, method, path, body=None):
        if method == "POST":
            self.writes.append((path, body))
            if path == PREFIX + "/git/trees":
                assert set(body) == {"tree"}
                self.entries = {e["path"]: e["content"] for e in body["tree"]}
                return {"sha": TREE}
            if path == PREFIX + "/git/commits":
                assert body["parents"] == [PRODUCT] and body["tree"] == TREE
                return {"sha": INSTALLED}
            if path == PREFIX + "/git/refs":
                branch = body["ref"].removeprefix("refs/heads/")
                if branch in self.refs:
                    raise install.ApiError(422)
                self.refs[branch] = body["sha"]
                return {}
        if path == PREFIX:
            return self.metadata
        if path.startswith(PREFIX + "/git/ref/heads/"):
            name = path.removeprefix(PREFIX + "/git/ref/heads/")
            if name not in self.refs:
                raise install.ApiError(404)
            return {"ref": "refs/heads/" + name, "object": {"type": "commit", "sha": self.refs[name]}}
        if path == PREFIX + "/git/commits/" + INSTALLED:
            return {"sha": INSTALLED, "tree": {"sha": TREE}}
        source = "/repos/" + install.SOURCE
        if path == source + "/git/commits/" + PIN:
            return {"sha": PIN}
        if path.startswith(source + "/contents/"):
            name, ref = path.removeprefix(source + "/contents/").split("?ref=")
            assert ref == PIN and name in install.PACKAGE
            raw = (("PACKAGE = " + repr(self.package) + "\n") if name == "tools/install.py" else ("sample " + name + "\n")).encode()
            sha = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            return {"type": "file", "path": name, "encoding": "base64",
                    "content": base64.b64encode(raw).decode(), "sha": "0" * 40 if self.bad_blob else sha}
        raise AssertionError((method, path))

class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.api = FakeGitHub()

    def test_install_isolated_branch(self):
        result = install.install(self.api, TARGET, PIN, "v1.0.6", True)
        self.assertEqual(result["installed_sha"], INSTALLED)
        self.assertEqual(self.api.refs, {"trunk": PRODUCT, install.BRANCH: INSTALLED})
        self.assertEqual(set(self.api.entries), set(install.PACKAGE.values()) |
                         {"vib-install.json", "ledger/issue-versions.json", "ledger/handoff.json"})
        ledger = json.loads(self.api.entries["ledger/issue-versions.json"])
        self.assertEqual(ledger["repository"], TARGET)
        self.assertEqual(ledger["issues"], [])
        self.assertEqual(checkpoint.register(ledger, 247, "v1.0.6", ["Check."]), ("v1.0.6.1", True))
        manifest = json.loads(self.api.entries["vib-install.json"])
        self.assertEqual(manifest["target_version"], "v1.0.7")
        self.assertEqual(manifest["enforcement"], "disabled")
        for name, digest in manifest["package_files_sha256"].items():
            self.assertEqual(hashlib.sha256(self.api.entries[name].encode()).hexdigest(), digest)

    def test_dry_run_has_no_writes(self):
        self.assertEqual(install.install(self.api, TARGET, PIN, "v0.0.0")["status"], "planned")
        self.assertEqual(self.api.writes, [])

    def test_occupied_branch_refused_including_repeat(self):
        install.install(self.api, TARGET, PIN, "v0.0.0", True)
        previous = list(self.api.writes)
        with self.assertRaisesRegex(ValueError, "already exists"):
            install.install(self.api, TARGET, PIN, "v0.0.0", True)
        self.assertEqual(self.api.writes, previous)

    def test_empty_or_wrong_repo_refused(self):
        self.api.refs = {}
        with self.assertRaisesRegex(ValueError, "Initialize"):
            install.install(self.api, TARGET, PIN, "v0.0.0", True)
        self.api.metadata["full_name"] = "example/other"
        with self.assertRaisesRegex(ValueError, "identity"):
            install.install(self.api, TARGET, PIN, "v0.0.0", True)
        self.assertEqual(self.api.writes, [])

    def test_invalid_source_and_corrupt_blob_refused(self):
        with self.assertRaisesRegex(ValueError, "full source"):
            install.install(self.api, TARGET, "main", "v0.0.0", True)
        self.api.bad_blob = True
        with self.assertRaisesRegex(ValueError, "integrity"):
            install.install(self.api, TARGET, PIN, "v0.0.0", True)
        self.assertEqual(self.api.writes, [])

    def test_branch_race_cannot_overwrite(self):
        original = self.api.request
        def race(method, path, body=None):
            if method == "POST" and path.endswith("/git/refs"):
                self.api.refs[install.BRANCH] = "e" * 40
            return original(method, path, body)
        self.api.request = race
        with self.assertRaises(install.ApiError):
            install.install(self.api, TARGET, PIN, "v0.0.0", True)
        self.assertEqual(self.api.refs[install.BRANCH], "e" * 40)
        self.assertEqual(self.api.refs["trunk"], PRODUCT)

    def test_default_branch_collision_refused(self):
        self.api.metadata["default_branch"] = install.BRANCH
        with self.assertRaisesRegex(ValueError, "product default"):
            install.install(self.api, TARGET, PIN, "v0.0.0", True)
        self.assertEqual(self.api.writes, [])


    def test_historical_package_pin_does_not_require_future_files(self):
        self.api.package.pop("tools/standard.py")
        self.api.package.pop("install/branch/STANDARD.md")
        result = install.install(self.api, TARGET, PIN, "v1.0.6", True)
        self.assertNotIn("STANDARD.md", result["paths"])
        self.assertNotIn("tools/standard.py", self.api.entries)
        self.assertEqual(set(result["manifest"]["package_files_sha256"]), set(self.api.package.values()))

    def test_pinned_package_rejects_dynamic_or_unknown_paths(self):
        for source in ("PACKAGE = dict()", "PACKAGE = {'evil': 'README.md'}",
                       "PACKAGE = {}; PACKAGE = {}", "PACKAGE = {'x': 'a', 'x': 'b'}"):
            with self.subTest(source=source), self.assertRaises(ValueError):
                install.pinned_package(source)


if __name__ == "__main__":
    unittest.main()
