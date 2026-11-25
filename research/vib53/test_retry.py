"""Isolated retry research. Real local Git CAS, synthetic operations, no network."""
import concurrent.futures
import json
import random
import tempfile
import threading
import time
import unittest
from pathlib import Path

from test_transactions import Store, REF


class Deferred(RuntimeError):
    """Retry budget exhausted; intent remains resumable, not completed."""


class RetryStore(Store):
    def propose_step(self, parent, issue, step, operation, payload):
        records = self.read(parent)
        intent = {"issue": issue, "step": step, "payload": payload}
        for row in records.values():
            if operation in row["operations"]:
                receipt = row["operations"][operation]
                if receipt["intent"] != intent:
                    raise ValueError("operation ID reused with different intent")
                return None, receipt
        key = str(issue)
        if key not in records:
            if step != 0:
                raise ValueError("missing claim")
            version = max((r["version"] for r in records.values()), default=0) + 1
            records[key] = {"version": version, "next": 0, "operations": {}}
        row = records[key]
        if row["next"] != step:
            raise ValueError("stale or competing phase")
        receipt = {"intent": intent, "version": row["version"]}
        row["operations"][operation] = receipt
        row["next"] += 1
        return self.commit(parent, records), receipt

    def conditional_write(self, parent, candidate):
        result = self.git("update-ref", REF, candidate, parent, check=False)
        if result.returncode == 0:
            return True
        error = result.stderr.decode("utf-8", errors="replace")
        # Do not turn arbitrary Git errors into retryable conflicts.
        if "cannot lock ref" in error and ("expected" in error or "File exists" in error):
            return False
        raise RuntimeError(error)

    def execute(self, issue, step, operation, payload, *, budget=100,
                seed=0, fault=None, first_snapshot=None, before_write=None):
        rng = random.Random(seed)
        metrics = dict(attempts=0, conflicts=0, before=0, lost=0, replays=0)
        for attempt in range(budget):
            metrics["attempts"] += 1
            parent = first_snapshot if attempt == 0 and first_snapshot else self.head()
            candidate, receipt = self.propose_step(parent, issue, step, operation, payload)
            if candidate is None:
                metrics["replays"] += 1
                return receipt, metrics
            if before_write:
                before_write(attempt)
            if fault == "before" and attempt == 0:
                metrics["before"] += 1
            elif self.conditional_write(parent, candidate):
                if fault == "after":
                    # Deliberately discard success response; the next iteration
                    # must recover a durable matching receipt, not write again.
                    metrics["lost"] += 1
                    fault = None
                else:
                    return receipt, metrics
            else:
                metrics["conflicts"] += 1
            if attempt + 1 < budget:
                time.sleep(rng.uniform(0, min(0.08, 0.002 * 2 ** min(attempt, 6))))
        # Final read even when the last allowed write had an ambiguous result.
        snapshot = self.read(self.head())
        for row in snapshot.values():
            if operation in row["operations"]:
                receipt = row["operations"][operation]
                if receipt["intent"] != {"issue": issue, "step": step, "payload": payload}:
                    raise ValueError("operation ID reused with different intent")
                metrics["replays"] += 1
                return receipt, metrics
        raise Deferred(f"retry budget exhausted for {operation}")


class RetryResearch(unittest.TestCase):
    def exercise(self, count, steps, seed):
        with tempfile.TemporaryDirectory() as temp:
            store = RetryStore(Path(temp))
            initial = store.head()
            start = time.monotonic()
            workers = min(8, count)
            barrier = threading.Barrier(workers, timeout=60)
            def client(issue):
                # Only first worker wave synchronizes initial attempts. All
                # subsequent writes/retries are autonomous, no recovery drain.
                if issue <= workers:
                    barrier.wait()
                reports = []
                for step in range(steps):
                    operation = f"{issue}:{step}"
                    fault = "before" if (issue + step) % 11 == 0 else (
                        "after" if (issue + step) % 7 == 0 else None)
                    receipt, metric = store.execute(
                        issue, step, operation, "synthetic", seed=seed + issue * 31 + step,
                        fault=fault, first_snapshot=initial if step == 0 else None)
                    reports.append((receipt, metric))
                return issue, reports, time.monotonic() - start
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
                results = list(pool.map(client, range(1, count + 1)))
            final = store.read(store.head())
            self.assertEqual(set(final), {str(i) for i in range(1, count + 1)})
            self.assertEqual(sorted(r["version"] for r in final.values()), list(range(1, count+1)))
            seen = set()
            metrics = []
            for issue, reports, _ in results:
                row = final[str(issue)]
                self.assertEqual(row["next"], steps)
                self.assertEqual(set(row["operations"]), {f"{issue}:{i}" for i in range(steps)})
                for step, (receipt, metric) in enumerate(reports):
                    op = f"{issue}:{step}"
                    self.assertNotIn(op, seen)
                    seen.add(op)
                    self.assertEqual(receipt, {"intent": {"issue": issue, "step": step,
                        "payload": "synthetic"}, "version": row["version"]})
                    self.assertEqual(row["operations"][op], receipt)
                    metrics.append(metric)
            self.assertEqual(len(seen), count * steps)
            self.assertEqual(int(store.git("rev-list", "--count", REF)), count * steps + 1)
            self.assertTrue(all(m["attempts"] <= 100 for m in metrics))
            if count > 1:
                self.assertGreater(sum(m["conflicts"] for m in metrics), 0)
            if count >= 10:
                self.assertGreater(sum(m["before"] for m in metrics), 0)
                self.assertGreater(sum(m["lost"] for m in metrics), 0)
            attempts = sorted(m["attempts"] for m in metrics)
            print("RETRY_METRICS " + json.dumps(dict(
                clients=count, workers=workers, seed=seed, operations=len(seen),
                completed_clients=len(results), conflicts=sum(m["conflicts"] for m in metrics),
                attempts=sum(attempts), max_attempts=max(attempts),
                p95_attempts=attempts[(95*len(attempts)+99)//100-1],
                prewrite_faults=sum(m["before"] for m in metrics),
                lost_responses=sum(m["lost"] for m in metrics),
                replayed_receipts=sum(m["replays"] for m in metrics),
                duplicate_commits=0, missing_operations=0, deferred_clients=0,
                elapsed_seconds=round(time.monotonic()-start, 3),
                last_client_seconds=round(max(r[2] for r in results), 3)), sort_keys=True), flush=True)

    def test_repeated_contention(self):
        for count, steps, seed in ((1, 3, 1), (10, 4, 17), (25, 3, 31), (100, 2, 53)):
            with self.subTest(count=count, steps=steps, seed=seed):
                self.exercise(count, steps, seed)

    def test_duplicate_operation_race_and_mismatched_intent(self):
        with tempfile.TemporaryDirectory() as temp:
            store = RetryStore(Path(temp))
            parent = store.head()
            with concurrent.futures.ThreadPoolExecutor(2) as pool:
                results = list(pool.map(lambda _: store.execute(1, 0, "same", "a",
                    first_snapshot=parent), range(2)))
            self.assertEqual(results[0][0], results[1][0])
            self.assertEqual(int(store.git("rev-list", "--count", REF)), 2)
            before = store.head()
            with self.assertRaisesRegex(ValueError, "different intent"):
                store.execute(1, 0, "same", "b")
            with self.assertRaisesRegex(ValueError, "different intent"):
                store.execute(2, 0, "same", "a")
            with self.assertRaisesRegex(ValueError, "competing phase"):
                store.execute(1, 0, "other", "a")
            self.assertEqual(store.head(), before)

    def test_exhaustion_and_independent_resume(self):
        with tempfile.TemporaryDirectory() as temp:
            store = RetryStore(Path(temp))
            def competitor(attempt):
                store.execute(100 + attempt, 0, f"competitor-{attempt}", "x")
            with self.assertRaises(Deferred):
                store.execute(1, 0, "pending", "x", budget=3, before_write=competitor)
            self.assertNotIn("1", store.read(store.head()))
            self.assertEqual(len(store.read(store.head())), 3)
            # Simulate restart with no in-memory retry state and same intent.
            receipt, _ = store.execute(1, 0, "pending", "x")
            self.assertEqual(receipt["version"], 4)
            before = store.head()
            self.assertEqual(store.execute(1, 0, "pending", "x")[0], receipt)
            self.assertEqual(store.head(), before)

    def test_last_attempt_lost_response(self):
        with tempfile.TemporaryDirectory() as temp:
            store = RetryStore(Path(temp))
            receipt, metric = store.execute(1, 0, "last", "x", budget=1, fault="after")
            self.assertEqual(receipt["version"], 1)
            self.assertEqual(metric["lost"], 1)
            self.assertEqual(metric["replays"], 1)
            self.assertEqual(int(store.git("rev-list", "--count", REF)), 2)

    def test_permanent_error_is_not_retried(self):
        with tempfile.TemporaryDirectory() as temp:
            store = RetryStore(Path(temp))
            before = store.head()
            calls = []
            def denied(parent, candidate):
                calls.append(candidate)
                raise PermissionError("permanent denied")
            store.conditional_write = denied
            with self.assertRaises(PermissionError):
                store.execute(1, 0, "denied", "x")
            self.assertEqual(len(calls), 1)
            self.assertEqual(store.head(), before)
