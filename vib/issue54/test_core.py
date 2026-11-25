"""Issue 54: independent byte oracle and product integrity tests (no remote API)."""
import base64
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

PRODUCT = Path(os.environ["VIB_CHECKOUT"]).resolve()
PIN = "7ae6626e44d01d29b11968da28e6debd816f8c06"
if subprocess.check_output(["git", "-C", str(PRODUCT), "rev-parse", "HEAD"]).decode().strip() != PIN:
    raise RuntimeError("Wrong product pin")
sys.path.insert(0, str(PRODUCT))
from tools import lifecycle, install, session

spec = importlib.util.spec_from_file_location("original_lifecycle", PRODUCT / "tests/test_lifecycle.py")
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)

def git(root, *args, data=None):
    env = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    return subprocess.check_output(["git", "-C", str(root), *args], input=data, env=env, timeout=20)

def oracle(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()

CORPUS = {
    "empty": "", "lf": "a\nb\n", "crlf": "a\r\nb\r\n", "cr": "a\rb\r",
    "mixed": "a\r\nb\nc\r", "no_final": "abc", "final_twice": "abc\n\n",
    "spaces": " \t a \t\n ", "nul": "a\0b", "bom": "\ufeffabc\n",
    "accent": "caf\u00e9\n", "cjk": "\u6c34\n", "emoji": "\U0001f642\n",
    "nfd": "e\u0301\n", "nfc": "\u00e9\n",
}
for n in (1, 9, 10, 99, 100, 4096, 65536):
    CORPUS[f"length_{n}"] = "x" * n
rng = random.Random(54)
for n in range(12):
    CORPUS[f"seed54_{n:02d}"] = "".join(rng.choice("a \n\r\t\u00e9\u6c34") for _ in range(31+n))

class Bytes(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory(prefix="vib 54 [bytes] ")
        self.addCleanup(t.cleanup)
        self.root = Path(t.name)
        git(self.root, "init", "--bare", "--object-format=sha1", "-q")

    def probe(self, value):
        raw = value.encode("utf-8")
        oid = git(self.root, "hash-object", "-w", "--no-filters", "--stdin", data=raw).decode().strip()
        self.assertEqual(oid, oracle(raw))
        self.assertEqual(lifecycle.blob_id(value), oid)
        self.assertEqual(git(self.root, "cat-file", "blob", oid), raw)
        self.assertEqual(lifecycle.digest_files({"x": value})["x"], hashlib.sha256(raw).hexdigest())

    def test_text_transport_differential(self):
        value = "old guide\n"
        raw = value.encode("utf-8")
        old_oid = subprocess.check_output(["git", "-C", str(self.root), "hash-object", "-w", "--stdin"],
                                          input=value, text=True, encoding="utf-8", timeout=20).strip()
        actual = git(self.root, "cat-file", "blob", old_oid)
        predicted = value.replace("\n", os.linesep).encode("utf-8")
        self.assertEqual(actual, predicted)
        self.assertEqual(old_oid, oracle(predicted))
        self.assertEqual(actual == raw, os.linesep == "\n")
        observation = {"platform": sys.platform, "expected_hex": raw.hex(),
              "observed_hex": actual.hex(), "expected_oid": oracle(raw), "observed_oid": old_oid,
              "expected_length": len(raw), "observed_length": len(actual)}
        if "RUNNER_TEMP" in os.environ:
            out = Path(os.environ["RUNNER_TEMP"]) / "issue54"
            out.mkdir(exist_ok=True)
            (out / "transport.json").write_text(json.dumps(observation, indent=2)+"\n", encoding="utf-8")

    def test_text_read_hides_crlf(self):
        raw = b"a\r\nb\r\n"
        oid = git(self.root, "hash-object", "-w", "--stdin", data=raw).decode().strip()
        normalized = subprocess.check_output(["git", "-C", str(self.root), "cat-file", "blob", oid],
                                             text=True, encoding="utf-8", timeout=20)
        self.assertEqual(normalized, "a\nb\n")
        self.assertNotEqual(normalized.encode(), raw)
        self.assertEqual(git(self.root, "cat-file", "blob", oid), raw)

def byte_case(value):
    def check(self):
        self.probe(value)
    return check

for name, value in CORPUS.items():
    setattr(Bytes, "test_bytes_" + name, byte_case(value))

class SourceResponse(unittest.TestCase):
    def setUp(self):
        self.raw = b"a\r\nb\n"
        self.item = {"type":"file", "encoding":"base64", "path":"x",
                     "sha":oracle(self.raw), "content":base64.b64encode(self.raw).decode()}

    def read(self, item):
        api = unittest.mock.Mock()
        api.request.return_value = item
        result = install.read_text(api, "/repos/example/test", "x", "a"*40)
        api.request.assert_called_once()
        return result

    def test_valid(self):
        self.assertEqual(self.read(self.item).encode(), self.raw)

    def test_invalid_utf8(self):
        raw = b"\xff"
        with self.assertRaises(UnicodeDecodeError):
            self.read(dict(self.item, sha=oracle(raw), content=base64.b64encode(raw).decode()))

def source_case(change):
    def check(self):
        with self.assertRaises(ValueError):
            self.read(dict(self.item, **change))
    return check
for name, change in {"path":{"path":"y"}, "type":{"type":"symlink"}, "encoding":{"encoding":"utf-8"},
                     "sha":{"sha":"0"*40}, "base64":{"content":"!!!!"},
                     "changed_bytes":{"content":"YQ=="}}.items():
    setattr(SourceResponse, "test_reject_" + name, source_case(change))

class TreeResponse(unittest.TestCase):
    def check_tree(self, change, commit_change=None):
        api = unittest.mock.Mock()
        commit = {"sha":"a"*40, "tree":{"sha":"b"*40}}
        row = {"path":"x","type":"blob","mode":"100644","sha":"c"*40}
        tree = {"sha":"b"*40,"truncated":False,"tree":[row]}
        api.request.side_effect = [dict(commit, **(commit_change or {})), dict(tree, **change)]
        return lifecycle.tree_entries(api, "/repos/example/test", "a"*40)

    def test_valid(self):
        self.assertEqual(self.check_tree({})[1], {"x":("blob","100644","c"*40)})

    def test_duplicate(self):
        row = {"path":"x","type":"blob","mode":"100644","sha":"c"*40}
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.check_tree({"tree":[row,copy.copy(row)]})

    def test_truncated(self):
        with self.assertRaisesRegex(ValueError, "incomplete"):
            self.check_tree({"truncated":True})

    def test_missing_completeness(self):
        with self.assertRaisesRegex(ValueError, "incomplete"):
            self.check_tree({"truncated":None})

    def test_wrong_tree(self):
        with self.assertRaisesRegex(ValueError, "incomplete"):
            self.check_tree({"sha":"d"*40})

    def test_wrong_commit(self):
        with self.assertRaisesRegex(ValueError, "identity"):
            self.check_tree({}, {"sha":"d"*40})

def safe_git(self, *args, data=None):
    env = dict(os.environ, GIT_AUTHOR_NAME="VIB test", GIT_AUTHOR_EMAIL="vib@example.invalid",
               GIT_COMMITTER_NAME="VIB test", GIT_COMMITTER_EMAIL="vib@example.invalid",
               GIT_INDEX_FILE=str(Path(self.path)/"fixture-index"),
               GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
    return subprocess.check_output(["git","-C",self.path,*args],
        input=None if data is None else data.encode("utf-8"), env=env, timeout=20).decode("utf-8").strip()

def safe_read(self, sha, path):
    return git(self.path, "show", sha+":"+path).decode("utf-8")

class LifecycleNegative(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for name, replacement in (("git",safe_git),("read",safe_read)):
            p=patch.object(original.GitApi,name,replacement)
            p.start()
            self.addCleanup(p.stop)
        self.api=original.GitApi(tmp.name)
        p=patch.object(install,"source_files",side_effect=lambda api,sha: dict({original.OLD:original.OLD_FILES,original.NEW:original.NEW_FILES}[sha]))
        p.start()
        self.addCleanup(p.stop)
        p=patch.object(install,"read_text",side_effect=lambda api,prefix,path,ref:api.read(ref,path))
        p.start()
        self.addCleanup(p.stop)

    def reject(self, value=None, mode=None, remove=False):
        a=self.api
        path="README.md"
        a.git("read-tree",a.old)
        if remove:
            a.git("update-index","--force-remove","--",path)
        else:
            oid=a.git("hash-object","-w","--stdin",data=value)
            a.git("update-index","--add","--cacheinfo",mode or "100644",oid,path)
        changed=a.commit(a.git("write-tree"),[a.old])
        a.ref(install.BRANCH,changed)
        with self.assertRaisesRegex(ValueError,"pinned bytes or mode"):
            lifecycle.upgrade(a,original.REPO,changed,original.NEW,apply=True,owner_approved=True)
        self.assertEqual(a.writes,[])
        self.assertEqual(a.ref(install.BRANCH),changed)
        self.assertEqual(a.ref("main"),a.product)

    def test_valid_plan(self):
        a=self.api
        plan=lifecycle.upgrade(a,original.REPO,a.old,original.NEW)
        self.assertEqual(plan["status"],"planned")
        self.assertEqual(a.writes,[])
        self.assertEqual(a.ref(install.BRANCH),a.old)

    def test_removed(self):
        self.reject(remove=True)

    def test_executable_mode(self):
        self.reject(original.OLD_FILES["README.md"],"100755")

    def test_symlink_mode(self):
        self.reject("elsewhere","120000")

def tamper_case(value):
    def check(self):
        self.reject(value)
    return check
for name, value in {"crlf":"old guide\r\n","truncated":"old guid","replaced":"Old guide\n",
                     "empty":"","appended":"old guide\nx","no_final":"old guide",
                     "space":"old guide \n","bom":"\ufeffold guide\n"}.items():
    setattr(LifecycleNegative,"test_tamper_"+name,tamper_case(value))

class Readback(unittest.TestCase):
    def verify(self, values, expected_error=None):
        api=unittest.mock.Mock()
        with patch.object(install,"read_ref",side_effect=values), patch.object(install.time,"sleep"):
            if expected_error:
                with self.assertRaisesRegex(ValueError,expected_error):
                    install.wait_ref(api,"/repos/example/test","vib","a"*40,"b"*40)
            else:
                self.assertEqual(install.wait_ref(api,"/repos/example/test","vib","a"*40,"b"*40),"a"*40)
        api.request.assert_not_called()

    def test_immediate(self):
        self.verify(["a"*40])
    def test_delayed(self):
        self.verify(["b"*40,"b"*40,"a"*40])
    def test_unexpected(self):
        self.verify(["c"*40],"Unexpected ref")
    def test_absent(self):
        self.verify([None],"Unexpected ref")
    def test_exhausted(self):
        self.verify(["b"*40]*6,"not confirmed")

if __name__ == "__main__":
    unittest.main(verbosity=2)
