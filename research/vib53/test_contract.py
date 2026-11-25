"""Qualification for options 1–7; tests are not live agent trials."""
import concurrent.futures
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from tools import checkpoint, session
from contract import ContractStore, apply, enqueue, migrate, pending, retry_policy, scope

def initial():
    return migrate({"schema_version": 1, "repository": "example/synthetic", "issues": []},
                   {"schema_version": 1, "active": None, "history": []}, "v0.0.0", "policy-a")

def intent(issue, actor, action, generation=1, **fields):
    return dict(issue=issue, actor=actor, action=action, generation=generation, **fields)

def perform(s, op, i):
    enqueue(s, op, i)
    apply(s, op)

def evidence(s, issue, generation=1):
    e = dict(candidate="a"*40, base="b"*40, run=issue, attempt=1, result="success")
    e["scope"] = scope(s, issue, e["candidate"], e["base"], e["run"], e["attempt"], generation)
    return e

class ContractTests(unittest.TestCase):
    def test_durable_process_resume(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ContractStore(Path(temp))
            store.transaction(lambda s: (s.update(initial()) or True))
            store.transaction(lambda s: enqueue(s, "claim-1", intent(1, "a", "claim", authorized=True, criteria=["test"])))
            before = store.head()
            # Separate interpreter, no original operation argument or memory.
            script = "from pathlib import Path; from contract import ContractStore; import sys; ContractStore.__new__(ContractStore).open(Path(sys.argv[1])).recover_pending('a',1)"
            for _ in range(2):
                subprocess.run([sys.executable, "-c", script, temp], cwd=Path(__file__).resolve().parent,
                               env={**__import__("os").environ, "PYTHONPATH": str(Path(__file__).resolve().parents[2])},
                               check=True, timeout=60)
            s = store.read(store.head())
            self.assertNotEqual(before, store.head())
            self.assertEqual(pending(s, "a", 1), [])
            self.assertEqual(s["receipts"]["claim-1"]["version"], "v0.0.0.1")
            self.assertEqual(int(store.git("rev-list", "--count", "refs/heads/synthetic-state")), 4)
            with self.assertRaisesRegex(ValueError, "intent mismatch"):
                enqueue(s, "claim-1", intent(2, "a", "claim", authorized=True, criteria=["test"]))

    def test_finite_competing_arrivals(self):
        with tempfile.TemporaryDirectory() as temp:
            store = ContractStore(Path(temp))
            store.transaction(lambda s: (s.update(initial()) or True))
            def client(n):
                actor = str(n)
                op = "claim-"+actor
                store.transaction(lambda s: enqueue(s, op, intent(n, actor, "claim", authorized=True, criteria=["test"])), seed=n)
                store.recover_pending(actor, 1)
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
                list(pool.map(client, range(1, 21)))
            s = store.read(store.head())
            self.assertEqual(len(s["receipts"]), 20)
            self.assertEqual(len(set(checkpoint.bindings(s["ledger"]).values())), 20)
            self.assertEqual(set(s["receipts"]), set(s["intents"]))

    def test_ownership_fence(self):
        s = initial()
        perform(s, "a", intent(1, "a", "claim", authorized=True, criteria=["test"]))
        with self.assertRaisesRegex(ValueError, "unauthorized recovery"):
            perform(s, "bad", intent(1, "b", "recover", 2))
        perform(s, "new", intent(1, "b", "recover", 2, authorized=True))
        with self.assertRaisesRegex(ValueError, "stale ownership"):
            perform(s, "old", intent(1, "a", "advance"))
        self.assertEqual(s["lanes"]["1"]["version"], "v0.0.0.1")
        perform(s, "next", intent(1, "b", "advance", 2))
        self.assertEqual(s["lanes"]["1"]["phase"], "Validate")

    def test_retry_classification(self):
        self.assertEqual(retry_policy(403, {}, 100, 0), ("stop", 0))
        self.assertEqual(retry_policy(409, {}, 100, 0), ("stop", 0))
        self.assertEqual(retry_policy(429, {"Retry-After":"120"}, 100, 0), ("defer",120))
        self.assertEqual(retry_policy(403, {"X-RateLimit-Remaining":"0","X-RateLimit-Reset":"500"},100,0), ("defer",400))
        self.assertEqual(retry_policy(503, {}, 100, 0), ("reconcile",1))

    def test_scope_isolation(self):
        s = initial()
        perform(s, "a", intent(1, "a", "claim", authorized=True, criteria=["test"]))
        e = evidence(s, 1)
        perform(s, "b", intent(2, "b", "claim", authorized=True, criteria=["other"]))
        self.assertEqual(e, evidence(s, 1))
        for field, value in [("candidate","c"*40),("base","d"*40),("run",2),("attempt",2)]:
            other = {**e,field:value}
            self.assertNotEqual(e["scope"], scope(s,1,other["candidate"],other["base"],other["run"],other["attempt"],1))
        s["policy"] = "policy-b"
        self.assertNotEqual(e, evidence(s, 1))

    def test_legacy_migration_preserves_history(self):
        s = initial()
        ledger = s["ledger"]
        checkpoint.register(ledger, 9, "v0.0.0", ["original"])
        ledger["issues"][0]["state"] = "integrated"
        active = dict(issue=9,version="v0.0.0.1",phase="Head",next_action="archived",
                      fix_sha=None,candidate_sha=None,pull_request=None,evidence=[])
        history = [{"handoff":active,"disposition":"integrated","decision":"owner","merged_sha":"a"*40}]
        handoff = {"schema_version":1,"active":None,"history":history}
        migrated = migrate(ledger,handoff,"v0.0.0","policy-a")
        self.assertEqual(migrated["ledger"],ledger)
        self.assertEqual(migrated["legacy_history"],history)
        perform(migrated,"new",intent(10,"a","claim",authorized=True,criteria=["test"]))
        checkpoint.check_history(migrated["ledger"],ledger)
        self.assertEqual(migrated["lanes"]["10"]["version"],"v0.0.0.2")
        busy = copy.deepcopy(ledger)
        busy["issues"][0]["state"]="in_progress"
        with self.assertRaisesRegex(ValueError,"migration requires idle"):
            migrate(busy,{**handoff,"active":active},"v0.0.0","policy-a")

    def test_full_phase_model(self):
        for count in (1,2,5,10,25,50,100):
            s = initial()
            for n in range(1,count+1):
                perform(s,f"{n}-claim",intent(n,str(n),"claim",authorized=True,criteria=["test"]))
            for n in range(1,count+1):
                perform(s,f"{n}-worker",intent(n,str(n),"advance"))
            for n in range(1,count+1):
                perform(s,f"{n}-validate",intent(n,str(n),"advance",evidence=evidence(s,n)))
            for n in range(1,count+1):
                perform(s,f"{n}-audit",intent(n,str(n),"advance",evidence=evidence(s,n)))
            for n in range(1,count+1):
                perform(s,f"{n}-finish",intent(n,str(n),"finish",authorized=True,evidence=evidence(s,n)))
            self.assertEqual(len(s["receipts"]),count*5)
            self.assertTrue(all(x["phase"]=="Done" for x in s["lanes"].values()))
            self.assertEqual(len(set(checkpoint.bindings(s["ledger"]).values())),count)
            self.assertTrue(all(x["state"]=="verified" for x in s["ledger"]["issues"]))
            print(f"PHASE_MODEL clients={count} transitions={count*5}",flush=True)

    def test_scope_rejects_failed_and_stale(self):
        s=initial()
        perform(s,"claim",intent(1,"a","claim",authorized=True,criteria=["test"]))
        perform(s,"work",intent(1,"a","advance"))
        e=evidence(s,1)
        with self.assertRaisesRegex(ValueError,"unverified evidence"):
            perform(s,"fail",intent(1,"a","advance",evidence={**e,"result":"skipped"}))
        perform(s,"validate",intent(1,"a","advance",evidence=e))
        s["policy"]="changed"
        with self.assertRaisesRegex(ValueError,"scope changed"):
            perform(s,"audit",intent(1,"a","advance",evidence=e))
