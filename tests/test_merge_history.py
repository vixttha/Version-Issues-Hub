"""Real disposable Git scenarios for #53; not production integration qualification."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from tools import checkpoint


class MergeHistoryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.git("init", "-b", "target")
        self.git("config", "user.name", "VIB Test")
        self.git("config", "user.email", "vib@example.invalid")
        self.git("config", "commit.gpgsign", "false")
        self.git("config", "core.autocrlf", "false")
        self.base = self.commit_file("base.txt", "baseline\n", "base")

    def git(self, *args, check=True, input_text=None):
        result = subprocess.run(["git", "-C", str(self.root), *args],
                                input=None if input_text is None else input_text.encode("utf-8"),
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=check)
        return result.stdout.decode("utf-8").strip() if check else result

    def commit_file(self, path, value, message):
        (self.root / path).write_bytes(value.encode("utf-8"))
        self.git("add", path)
        self.git("commit", "-m", message)
        return self.git("rev-parse", "HEAD")

    def branches(self):
        self.git("checkout", "-b", "feature")
        fix = self.commit_file("fix.txt", "fix\n", "original fix")
        self.git("checkout", "target")
        target = self.commit_file("other.txt", "other\n", "unrelated base advance")
        return fix, target

    def assert_ancestry(self, fix, candidate, present):
        old = os.getcwd()
        try:
            os.chdir(self.root)
            if present:
                checkpoint.verify_fix_ancestry("v0.0.0.1", fix, candidate)
            else:
                with self.assertRaisesRegex(ValueError, "not in candidate history"):
                    checkpoint.verify_fix_ancestry("v0.0.0.1", fix, candidate)
        finally:
            os.chdir(old)

    def test_merge_commit_preserves_original_fix_and_tree(self):
        fix, target = self.branches()
        self.git("merge", "--no-ff", "-m", "proposed", fix)
        proposed = self.git("rev-parse", "HEAD")
        tree = self.git("rev-parse", proposed + "^{tree}")
        actual = self.git("commit-tree", tree, "-p", target, "-p", fix, input_text="actual\n")
        self.assertNotEqual(proposed, actual)
        self.assertEqual(self.git("rev-parse", actual + "^{tree}"), tree)
        self.assertEqual(self.git("show", "-s", "--format=%P", actual).split(), [target, fix])
        self.assert_ancestry(fix, actual, True)

    def test_squash_and_rebase_preserve_content_not_fix_identity(self):
        fix, target = self.branches()
        self.git("merge", "--no-ff", "-m", "ordinary merge", fix)
        tree = self.git("rev-parse", "HEAD^{tree}")
        self.git("checkout", "-b", "squash-case", target)
        self.git("merge", "--squash", fix)
        self.git("commit", "-m", "squashed")
        squash = self.git("rev-parse", "HEAD")
        self.git("checkout", "-b", "rebase-case", fix)
        self.git("rebase", target)
        rebase = self.git("rev-parse", "HEAD")
        for candidate in (squash, rebase):
            self.assertEqual(self.git("rev-parse", candidate+"^{tree}"), tree)
            self.assertNotEqual(candidate, fix)
            self.assert_ancestry(fix, candidate, False)

    def test_stale_base_can_create_clean_semantic_conflict(self):
        self.commit_file("minimum.txt", "1\n", "minimum")
        base = self.commit_file("maximum.txt", "10\n", "maximum")
        self.git("checkout", "-b", "raise-min")
        a = self.commit_file("minimum.txt", "8\n", "raise minimum")
        self.git("checkout", "-b", "lower-max", base)
        b = self.commit_file("maximum.txt", "4\n", "lower maximum")
        def valid(sha):
            return int(self.git("show", sha+":minimum.txt")) <= int(self.git("show", sha+":maximum.txt"))
        self.assertTrue(valid(a))
        self.assertTrue(valid(b))
        self.git("checkout", "target")
        self.git("merge", "--no-ff", "-m", "first", a)
        first = self.git("rev-parse", "HEAD")
        self.assertNotEqual(first, base)
        self.git("merge", "--no-ff", "-m", "second", b)
        combined = self.git("rev-parse", "HEAD")
        self.assertFalse(valid(combined))
        self.assertEqual(self.git("show", "-s", "--format=%P", combined).split(), [first,b])

    def test_textual_conflict_is_not_a_merge_candidate(self):
        self.git("checkout", "-b", "change-one")
        a = self.commit_file("base.txt", "first\n", "first")
        self.git("checkout", "target")
        b = self.commit_file("base.txt", "second\n", "second")
        result = self.git("merge", "--no-ff", "-m", "conflict", a, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.git("rev-parse", "HEAD"), b)
        self.git("merge", "--abort")

    def test_conditional_ref_rejects_stale_base(self):
        fix, target = self.branches()
        self.git("update-ref", "refs/heads/synthetic", self.base)
        self.git("update-ref", "refs/heads/synthetic", target, self.base)
        result = self.git("update-ref", "refs/heads/synthetic", fix, self.base, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.git("rev-parse", "refs/heads/synthetic"), target)
        self.assertEqual(self.git("rev-parse", "refs/heads/target"), target)
