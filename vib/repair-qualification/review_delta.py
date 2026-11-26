"""Separate, read-only-to-GitHub qualification for full-review behavior defects."""
import json, subprocess, sys, tempfile
from pathlib import Path
from unittest.mock import patch

source = Path(sys.argv[1]).resolve()
mode = sys.argv[2]
output = Path(sys.argv[3])
sha = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
assert sha == {"before": "ab03646daf4fee23e9857bd2ccbb4fd759891611", "after": "041e187dc1d383082c1a4805e6d4743eec97e535"}[mode]
sys.path[:0] = [str(source), str(source / "tests")]
from tools import session
from test_session import SessionTests, FIX, CANDIDATE, RUN, HEAD, NEXT
from test_contention_recovery import RecoveryTests, B, REPO

results = []
def record(name, observed, expected):
    results.append({"case": name, "outcome": observed, "expected": expected,
                    "pass": observed == expected})

def rework_case(replacement):
    fixture = SessionTests()
    fixture.setUp()
    try:
        fixture.claim()
        fixture.advance(fix=FIX, candidate=CANDIDATE, pr=8)
        fixture.advance(evidence=[RUN])
        fixture.advance()
        s, api = fixture.state, fixture.api
        s["ledger"], s["handoff"] = session.finish(api, s, "staged", "stage")
        api.pr.update(state="closed", merged=False)
        ledger, handoff = session.claim(api, s, 247, [], "rework", rework_staged=True)
        original = api.request
        def request(method, path, body=None):
            result = original(method, path, body)
            if replacement and method == "POST" and path.endswith("/git/commits"):
                api.pr.update(state=replacement[0], merged=replacement[1])
            return result
        with patch.object(api, "request", side_effect=request):
            try:
                result = session.save(api, s, ledger, handoff, True, issue=247)
            except ValueError:
                result = None
        patches = [w for w in api.writes if w[0] == "PATCH"]
        if result is None:
            assert not patches and api.ref == HEAD
            return "refused_no_patch"
        assert len(patches) == 1 and api.ref == NEXT and result["installed_sha"] == NEXT
        return "published"
    finally:
        fixture.doCleanups()

record("reopened_after_plan", rework_case(("open", False)), "refused_no_patch")
record("merged_after_plan", rework_case(("closed", True)), "refused_no_patch")
record("closed_unmerged_control", rework_case(None), "published")

fixture = RecoveryTests()
try:
    fixture.setUp()
    api = fixture.api
    with tempfile.TemporaryDirectory() as directory:
        pending = []
        result = fixture.recover(lambda state: fixture.claim(state, B), B,
            on_pending_intent=lambda intent: pending.append(session.persist_pending_intent(directory, intent)),
            on_recovery_ticket=lambda ticket: session.persist_recovery_ticket(directory, ticket))
        fresh = session.load(api, REPO)
        partial = Path(directory) / (result["operation_id"] + "-" + "0" * 40 + ".json")
        before_writes = list(api.writes)
        for raw in (b'{"schema_version":', b'\xff'):
            partial.write_bytes(raw)
            try:
                receipt = session.inspect_pending(api, fresh, pending[0])
            except ValueError:
                observed = "inventory_aborted"
            else:
                observed = "isolated_and_confirmed" if (
                    [c["status"] for c in receipt["candidates"]] == ["unreadable", "published"]
                    and receipt["candidates"][1]["installed_sha"] == result["installed_sha"]
                    and receipt["automatic_replay"] is False) else "unexpected"
            assert partial.read_bytes() == raw and api.writes == before_writes
            record("partial_json" if raw.startswith(b"{") else "invalid_utf8", observed, "isolated_and_confirmed")
        partial.write_text("{}", encoding="utf-8")
        try:
            session.inspect_pending(api, fresh, pending[0])
        except ValueError:
            observed = "identity_refused"
        else:
            observed = "identity_accepted"
        assert api.writes == before_writes
        record("decoded_wrong_identity_control", observed, "identity_refused")
finally:
    fixture.doCleanups()

output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(json.dumps({"source": sha, "mode": mode, "cases": results}, indent=2) + "\n", encoding="utf-8")
print(json.dumps(results), flush=True)
if mode == "before":
    assert [r["pass"] for r in results] == [False, False, True, False, False, True]
else:
    assert all(r["pass"] for r in results)
