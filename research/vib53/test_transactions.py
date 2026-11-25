"""Research-only synthetic Git transaction experiment; never contacts GitHub."""
import concurrent.futures
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import install

REF = "refs/heads/synthetic-state"


class Store:
    def __init__(self, directory):
        self.directory = directory
        self.git("init", "--bare", "--quiet")
        self.git("config", "user.name", "VIB research")
        self.git("config", "user.email", "research@example.invalid")
        self.initial = self.commit(None, {})
        self.git("update-ref", REF, self.initial)

    def git(self, *args, data=None, check=True):
        result = subprocess.run(
            ["git", "-C", str(self.directory), *args], input=data,
            text=True, capture_output=True, check=check, timeout=30,
        )
        return result.stdout.strip() if check else result

    def head(self):
        return self.git("rev-parse", REF)

    def read(self, head):
        return json.loads(self.git("show", head + ":state.json"))

    def commit(self, parent, records):
        blob = self.git("hash-object", "-w", "--stdin", data=json.dumps(records, sort_keys=True))
        tree = self.git("mktree", data=f"100644 blob {blob}\tstate.json\n")
        parents = ["-p", parent] if parent else []
        return self.git("commit-tree", tree, *parents, "-m", "synthetic transaction")

    def propose(self, parent, issue, operation):
        records = self.read(parent)
        for key, row in records.items():
            if row["operation"] == operation:
                if key != str(issue):
                    raise ValueError("operation identity reused with different intent")
                return None, row
        if str(issue) in records:
            raise ValueError("issue already claimed")
        version = max((r["version"] for r in records.values()), default=0) + 1
        row = {"operation": operation, "version": version}
        records[str(issue)] = row
        return self.commit(parent, records), row

    def cas(self, parent, candidate):
        return self.git("update-ref", REF, candidate, parent, check=False).returncode == 0

    def replay(self, issue, operation):
        parent = self.head()
        candidate, row = self.propose(parent, issue, operation)
        if candidate is not None and not self.cas(parent, candidate):
            raise AssertionError("unexpected contention in serialized recovery phase")
        return row


class TransactionResearch(unittest.TestCase):
    def test_same_issue_race(self):
        with tempfile.TemporaryDirectory() as temp:
            store = Store(Path(temp))
            parent = store.head()
            a, _ = store.propose(parent, 1, "a")
            b, _ = store.propose(parent, 1, "b")
            with concurrent.futures.ThreadPoolExecutor(2) as pool:
                results = list(pool.map(lambda sha: store.cas(parent, sha), [a, b]))
            self.assertEqual(sum(results), 1)
            winner = store.read(store.head())["1"]["operation"]
            loser = "b" if winner == "a" else "a"
            with self.assertRaisesRegex(ValueError, "already claimed"):
                store.replay(1, loser)
            self.assertEqual(len(store.read(store.head())), 1)

    def test_distinct_issues_contention_and_recovery(self):
        for count in (1, 2, 5, 10, 25, 50, 100):
            with self.subTest(clients=count), tempfile.TemporaryDirectory() as temp:
                store = Store(Path(temp))
                parent = store.head()
                # Every client deliberately starts from the same stale snapshot.
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                    proposals = list(pool.map(lambda i: store.propose(parent, i, f"op-{i}")[0], range(1, count + 1)))
                    results = list(pool.map(lambda sha: store.cas(parent, sha), proposals))
                self.assertEqual(sum(results), 1)
                # Controlled recovery, NOT a throughput benchmark or concurrent retry test.
                for issue, success in enumerate(results, 1):
                    if not success:
                        store.replay(issue, f"op-{issue}")
                final = store.read(store.head())
                self.assertEqual(set(final), {str(i) for i in range(1, count + 1)})
                self.assertEqual(sorted(r["version"] for r in final.values()), list(range(1, count + 1)))
                self.assertEqual(len({r["operation"] for r in final.values()}), count)
                self.assertEqual(int(store.git("rev-list", "--count", REF)), count + 1)
                print(f"clients={count} first_wave_commits=1 stale_rejections={count-1} recovered={count-1}", flush=True)

    def test_ambiguous_success_and_intent(self):
        with tempfile.TemporaryDirectory() as temp:
            store = Store(Path(temp))
            parent = store.head()
            candidate, expected = store.propose(parent, 1, "a")
            self.assertTrue(store.cas(parent, candidate))
            # Simulate a lost response, then unrelated successful work.
            store.replay(2, "b")
            self.assertNotEqual(store.head(), candidate)
            self.assertEqual(store.git("merge-base", "--is-ancestor", candidate, store.head(), check=False).returncode, 0)
            final = store.head()
            self.assertEqual(store.replay(1, "a"), expected)
            self.assertEqual(store.head(), final)
            with self.assertRaisesRegex(ValueError, "different intent"):
                store.replay(3, "a")
            self.assertEqual(store.head(), final)

    def test_current_readback_limitation(self):
        # Real production helper, mocked read transport; expected rejection,
        # not a repair or proof of a bug under the supported Solo contract.
        with patch.object(install, "read_ref", return_value="c" * 40):
            with self.assertRaisesRegex(ValueError, "Unexpected ref revision"):
                install.wait_ref(None, "/repos/example/synthetic", "synthetic", "b" * 40, "a" * 40)


if __name__ == "__main__":
    unittest.main(verbosity=2)
