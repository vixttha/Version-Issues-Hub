import base64
import hashlib
import json
import io
from urllib.error import HTTPError, URLError
from pathlib import Path
import unittest
from unittest.mock import patch
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
        self.package = {k: v for k, v in install.PACKAGE.items()
                        if v not in {"VIB-LICENSE.md", "VIB-NOTICE.md"}}

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
            assert ref == PIN and name in self.package
            if name == "tools/install.py":
                content = "PACKAGE = " + repr(self.package) + "\n"
            elif name in {"LICENSE", "VIB-NOTICE.md"}:
                content = (Path(__file__).resolve().parents[1] / name).read_text(encoding="utf-8")
            else:
                content = "sample " + name + "\n"
            raw = content.encode()
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
        self.assertEqual(set(self.api.entries), set(self.api.package.values()) |
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

    def test_review_legal_paths_are_hashed_and_apply_is_refused(self):
        self.api.package.update(install.HISTORICAL_LEGAL_PATHS)
        plan = install.install(self.api, TARGET, PIN, "v0.0.0")
        self.assertEqual(len(plan["manifest"]["package_files_sha256"]), 14)
        for name in ("VIB-LICENSE.md", "VIB-NOTICE.md"):
            self.assertIn(name, plan["manifest"]["package_files_sha256"])
        self.assertNotIn("LICENSE", plan["paths"])
        self.assertEqual(self.api.writes, [])
        with self.assertRaisesRegex(ValueError, "not authorized"):
            install.install(self.api, TARGET, PIN, "v0.0.0", True)
        self.assertEqual(self.api.writes, [])
        self.assertEqual(self.api.refs, {"trunk": PRODUCT})

    def test_approved_license_package_installs_and_preserves_notice_bytes(self):
        self.api.package = dict(install.PACKAGE)
        result = install.install(self.api, TARGET, PIN, "v0.0.0", True)
        root = Path(__file__).resolve().parents[1]
        for name, source in (("VIB-LICENSE.md", "LICENSE"), ("VIB-NOTICE.md", "VIB-NOTICE.md")):
            expected = (root / source).read_text(encoding="utf-8")
            self.assertEqual(self.api.entries[name], expected)
            self.assertEqual(result["manifest"]["package_files_sha256"][name],
                             hashlib.sha256(expected.encode()).hexdigest())
        self.assertNotIn("LICENSE", self.api.entries)
        self.assertEqual(self.api.refs["trunk"], PRODUCT)
    
    def test_incomplete_or_tampered_legal_pair_refused(self):
        root = Path(__file__).resolve().parents[1]
        license_text = (root / "LICENSE").read_text(encoding="utf-8")
        notice = (root / "VIB-NOTICE.md").read_text(encoding="utf-8")
        for files in ({"VIB-LICENSE.md": license_text}, {"VIB-NOTICE.md": notice},
                      {"VIB-LICENSE.md": license_text + "changed", "VIB-NOTICE.md": notice},
                      {"VIB-LICENSE.md": license_text, "VIB-NOTICE.md": notice + "changed"},
                      {"VIB-LICENSE.md": license_text, "VIB-NOTICE.md": "REVIEW_ONLY_NOT_A_GRANT"}):
            with self.subTest(files=list(files)), self.assertRaisesRegex(ValueError, "not authorized"):
                install.require_publishable_package(files)
        self.assertEqual(self.api.writes, [])
    
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



    def test_wait_ref_tolerates_only_expected_previous_state(self):
        with patch.object(install, "read_ref", side_effect=[None, None, INSTALLED]) as read, \
             patch.object(install.time, "sleep"):
            self.assertEqual(install.wait_ref(self.api,PREFIX,install.BRANCH,INSTALLED),INSTALLED)
            self.assertEqual(read.call_count,3)
        with patch.object(install,"read_ref",side_effect=[PRODUCT,INSTALLED]), \
             patch.object(install.time,"sleep"):
            self.assertEqual(install.wait_ref(self.api,PREFIX,install.BRANCH,INSTALLED,PRODUCT),INSTALLED)
        self.assertEqual(self.api.writes,[])

    def test_wait_ref_rejects_divergent_and_exhausted_readback(self):
        with patch.object(install,"read_ref",return_value=PRODUCT) as read, \
             patch.object(install.time,"sleep"):
            with self.assertRaisesRegex(ValueError,"Unexpected ref"):
                install.wait_ref(self.api,PREFIX,install.BRANCH,INSTALLED)
            self.assertEqual(read.call_count,1)
        with patch.object(install,"read_ref",return_value=None) as read, \
             patch.object(install.time,"sleep"):
            with self.assertRaisesRegex(ValueError,"not confirmed"):
                install.wait_ref(self.api,PREFIX,install.BRANCH,INSTALLED)
            self.assertEqual(read.call_count,6)
        self.assertEqual(self.api.writes,[])


    def test_api_transient_get_retries_and_recovers(self):
        api = install.GitHub("fixture-secret")
        err = HTTPError("https://api.github.com/private",503,"unavailable",{},io.BytesIO(b"secret"))
        with patch.object(api.opener,"open",side_effect=[err,io.BytesIO(b'{"ok":true}')]) as req, \
             patch.object(install.time,"sleep") as delay:
            self.assertEqual(api.request("GET",PREFIX+"/git/ref/heads/Version-Issues-Hub"),{"ok":True})
            self.assertEqual(req.call_count,2)
            delay.assert_called_once_with(0.5)

    def test_api_exhaustion_redacts_path_and_query(self):
        api = install.GitHub("fixture-secret")
        errors=[HTTPError("https://api.github.com/private",500,"secret",{},io.BytesIO(b"secret")) for _ in range(3)]
        with patch.object(api.opener,"open",side_effect=errors) as req, patch.object(install.time,"sleep"):
            with self.assertRaises(install.ApiError) as raised:
                api.request("GET",PREFIX+"/contents/private-file?ref=secret")
            self.assertEqual(req.call_count,3)
            self.assertEqual(str(raised.exception),"GitHub API returned HTTP 500 (GET contents)")

    def test_api_mutating_request_never_retried(self):
        api = install.GitHub("fixture-secret")
        for method in ("POST","PATCH","DELETE"):
            err=HTTPError("https://api.github.com/private",500,"secret",{},io.BytesIO(b"secret"))
            with patch.object(api.opener,"open",side_effect=err) as req, patch.object(install.time,"sleep") as delay:
                with self.assertRaises(install.ApiError) as raised:
                    api.request(method,PREFIX+"/git/refs/heads/private",{"secret":"hidden"})
                self.assertEqual(req.call_count,1)
                self.assertEqual(str(raised.exception),f"GitHub API returned HTTP 500 ({method} git/refs)")
                delay.assert_not_called()

    def test_api_get_timeout_retries_direct_and_wrapped(self):
        for first in (TimeoutError("private detail"), URLError(TimeoutError("private detail"))):
            api = install.GitHub("fixture-secret")
            with patch.object(api.opener,"open",side_effect=[first,io.BytesIO(b'{"ok":true}')]) as req, \
                 patch.object(install.time,"sleep") as delay:
                self.assertEqual(api.request("GET",PREFIX+"/contents/private-file?ref=secret"),{"ok":True})
                self.assertEqual(req.call_count,2)
                delay.assert_called_once_with(0.5)

    def test_api_get_timeout_during_response_read(self):
        api = install.GitHub("fixture-secret")
        class SlowResponse(io.BytesIO):
            def read(self, *args, **kwargs):
                raise TimeoutError("private response detail")
        with patch.object(api.opener,"open",side_effect=[SlowResponse(),io.BytesIO(b'{"ok":true}')]) as req, \
             patch.object(install.time,"sleep"):
            self.assertEqual(api.request("GET",PREFIX+"/contents/private-file"),{"ok":True})
            self.assertEqual(req.call_count,2)

    def test_api_transport_exhaustion_and_no_write_retry(self):
        api = install.GitHub("fixture-secret")
        for method, count in (("GET",3),("POST",1),("PATCH",1),("DELETE",1)):
            errors=[TimeoutError("private request detail") for _ in range(count)]
            with patch.object(api.opener,"open",side_effect=errors) as req, patch.object(install.time,"sleep") as delay:
                with self.assertRaises(install.ApiTransportError) as raised:
                    api.request(method,PREFIX+"/git/refs/heads/private?ref=secret")
                self.assertEqual(req.call_count,count)
                self.assertTrue(raised.exception.timed_out)
                expected=f"GitHub transport timed out ({method} git/refs)"
                if method!="GET":
                    expected+="; inspect before retrying any write"
                    delay.assert_not_called()
                self.assertEqual(str(raised.exception),expected)

    def test_api_other_url_errors_fail_closed(self):
        api = install.GitHub("fixture-secret")
        with patch.object(api.opener,"open",side_effect=URLError("private error")) as req, \
             patch.object(install.time,"sleep") as delay:
            with self.assertRaises(install.ApiTransportError) as raised:
                api.request("GET",PREFIX+"/contents/private-file")
            self.assertEqual(req.call_count,1)
            self.assertFalse(raised.exception.timed_out)
            self.assertEqual(str(raised.exception),"GitHub transport failed (GET contents)")
            delay.assert_not_called()

    def test_api_rejects_duplicate_and_malformed_wire_json(self):
        api = install.GitHub("fixture-secret")
        invalid = (
            b'{"merged":true,"merged":false}',
            b'{"nested":{"private-key":1,"private-key":2}}',
            b'{"merged":true,"m\u0065rged":false}',
            b'{"private-key":',
            b'{"private-key":"\xff"}',
        )
        for method in ("GET", "POST", "PATCH", "DELETE"):
            for raw in invalid:
                with self.subTest(method=method, raw=raw), \
                     patch.object(api.opener, "open", return_value=io.BytesIO(raw)) as req, \
                     patch.object(install.time, "sleep") as delay:
                    with self.assertRaisesRegex(ValueError, "Invalid GitHub JSON response") as raised:
                        api.request(method, PREFIX + "/git/refs/heads/private?ref=secret")
                    self.assertEqual(req.call_count, 1)
                    delay.assert_not_called()
                    self.assertNotIn("private", str(raised.exception))
                    self.assertNotIn("secret", str(raised.exception))
                    self.assertNotIn("merged", str(raised.exception))
                    if method != "GET":
                        self.assertIn("inspect before retrying", str(raised.exception))

    def test_api_valid_json_preserves_nested_values(self):
        api = install.GitHub(None)
        raw = b'{"merged":false,"nested":{"merged":true},"items":[{"id":1},{"id":2}]}'
        with patch.object(api.opener, "open", return_value=io.BytesIO(raw)) as req:
            self.assertEqual(api.request("GET", PREFIX),
                             {"merged": False, "nested": {"merged": True},
                              "items": [{"id": 1}, {"id": 2}]})
            req.assert_called_once()


if __name__ == "__main__":
    unittest.main()
