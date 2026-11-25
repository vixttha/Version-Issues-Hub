"""Research contract only. Not an installed VIB package or production API."""
import copy
import hashlib
import json
import random
import time
from tools import checkpoint, session
from test_retry import RetryStore, Deferred
from test_transactions import REF

PHASES = ("Worker", "Validate", "Internal Auditor", "Head")

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def migrate(ledger, handoff, baseline, policy):
    """Validate genuine v1 state; do not migrate active or staged work."""
    session.validate_handoff(handoff, ledger)
    if handoff["active"] is not None or any(x["state"] == "staged" for x in ledger["issues"]):
        raise ValueError("migration requires idle, unstaged state")
    checkpoint.require(checkpoint.LINE, baseline, "baseline")
    return {"schema": 2, "ledger": copy.deepcopy(ledger),
            "legacy_history": copy.deepcopy(handoff["history"]), "baseline": baseline,
            "policy": policy, "lanes": {}, "intents": {}, "receipts": {}}

def scope(state, issue, candidate, base, run, attempt, generation):
    row = next(x for x in state["ledger"]["issues"] if x["issue"] == issue)
    return digest({"repository": state["ledger"]["repository"], "issue": issue,
                   "version": row["version"], "criteria": row["acceptance"],
                   "policy": state["policy"], "candidate": candidate, "base": base,
                   "run": run, "attempt": attempt, "generation": generation})

def enqueue(state, op, intent):
    old = state["intents"].get(op)
    if old is not None:
        if old != intent:
            raise ValueError("intent mismatch")
        return False
    if not isinstance(op, str) or not op or not isinstance(intent, dict):
        raise ValueError("invalid intent")
    state["intents"][op] = copy.deepcopy(intent)
    return True

def apply(state, op):
    """Only synthetic authorized intents; no external side effects."""
    intent = state["intents"][op]
    if op in state["receipts"]:
        return False
    issue, actor, generation, action = (intent[k] for k in ("issue", "actor", "generation", "action"))
    if type(issue) is not int or issue <= 0 or not isinstance(actor, str) or not actor or type(generation) is not int:
        raise ValueError("invalid assignment identity")
    key = str(issue)
    lane = state["lanes"].get(key)
    if action == "claim":
        if lane is not None or generation != 1 or intent.get("authorized") is not True:
            raise ValueError("claim conflict or unauthorized")
        if issue in checkpoint.bindings(state["ledger"]):
            raise ValueError("historical claim requires separate recovery")
        version, _ = checkpoint.register(state["ledger"], issue, state["baseline"], intent["criteria"])
        row = next(x for x in state["ledger"]["issues"] if x["issue"] == issue)
        row["state"] = "in_progress"
        lane = {"actor": actor, "generation": generation, "phase": "Worker",
                "version": version, "evidence": None}
        state["lanes"][key] = lane
    else:
        if lane is None:
            raise ValueError("missing lane")
        if action == "recover":
            if intent.get("authorized") is not True or generation != lane["generation"] + 1 or lane["phase"] == "Done":
                raise ValueError("unauthorized recovery")
            lane.update(actor=actor, generation=generation, phase="Worker", evidence=None)
        else:
            if actor != lane["actor"] or generation != lane["generation"]:
                raise ValueError("stale ownership")
            if action == "advance" and lane["phase"] == "Worker":
                lane["phase"] = "Validate"
            elif action == "advance" and lane["phase"] == "Validate":
                evidence = intent["evidence"]
                expected = scope(state, issue, evidence["candidate"], evidence["base"],
                                 evidence["run"], evidence["attempt"], generation)
                if evidence["scope"] != expected or evidence["result"] != "success":
                    raise ValueError("unverified evidence")
                lane.update(phase="Internal Auditor", evidence=copy.deepcopy(evidence))
            elif action == "advance" and lane["phase"] == "Internal Auditor":
                if intent["evidence"] != lane["evidence"]:
                    raise ValueError("stale evidence")
                e = lane["evidence"]
                if e["scope"] != scope(state, issue, e["candidate"], e["base"], e["run"], e["attempt"], generation):
                    raise ValueError("scope changed")
                lane["phase"] = "Head"
            elif action == "finish" and lane["phase"] == "Head" and intent.get("authorized") is True:
                if intent["evidence"] != lane["evidence"]:
                    raise ValueError("stale evidence")
                e = lane["evidence"]
                if e["scope"] != scope(state, issue, e["candidate"], e["base"], e["run"], e["attempt"], generation):
                    raise ValueError("scope changed")
                lane["phase"] = "Done"
                next(x for x in state["ledger"]["issues"] if x["issue"] == issue)["state"] = "verified"
            else:
                raise ValueError("invalid phase or authorization")
    state["receipts"][op] = {"intent_digest": digest(intent), "version": lane["version"],
                              "generation": lane["generation"], "phase": lane["phase"]}
    return True

def pending(state, actor, generation):
    return sorted(op for op, intent in state["intents"].items()
                  if op not in state["receipts"] and intent["actor"] == actor
                  and intent["generation"] == generation)

def retry_policy(status, headers, now, attempt):
    """Pure classification, not a live HTTP transport. Delay is seconds."""
    headers = {k.lower(): v for k, v in headers.items()}
    limited = status == 429 or (status == 403 and
        ("retry-after" in headers or headers.get("x-ratelimit-remaining") == "0"))
    if limited:
        delay = max(60, 2 ** min(attempt, 8))
        if "retry-after" in headers:
            delay = max(delay, int(headers["retry-after"]))
        if headers.get("x-ratelimit-remaining") == "0":
            delay = max(delay, int(headers["x-ratelimit-reset"]) - now)
        return "defer", delay
    if status in (408, 500, 502, 503, 504):
        return "reconcile", max(1, 2 ** min(attempt, 8))
    # A 409 alone is not proof of a stale write.
    return "stop", 0

class ContractStore(RetryStore):
    def open(self, directory):
        self.directory = directory
        return self

    def transaction(self, fn, budget=100, seed=0):
        rng = random.Random(seed)
        for attempt in range(budget):
            parent = self.head()
            state = self.read(parent)
            if not fn(state):
                return state
            if self.conditional_write(parent, self.commit(parent, state)):
                return state
            time.sleep(rng.uniform(0, min(.08, .002 * 2 ** min(attempt, 6))))
        raise Deferred("transaction deferred; persisted intents remain discoverable")

    def recover_pending(self, actor, generation):
        for op in pending(self.read(self.head()), actor, generation):
            self.transaction(lambda s: apply(s, op))
