"""Read-only public adopter audit and reproducible defect observations (not acceptance)."""
import copy
import json
import os
from tools import install, session, checkpoint
from unittest.mock import patch

class ReadOnly(install.GitHub):
    def request(self, method, path, body=None):
        if method != "GET" or body is not None:
            raise AssertionError("Audit cannot mutate GitHub")
        return super().request(method, path)

api = ReadOnly(os.environ["GH_TOKEN"])
targets = [
    "vixttha/AlderVale-Pact-of-Ten",
    "vixttha/Blender-Agent-Refinement-Toolkit",
    "vixttha/Version-Issues-Hub",
    "vixttha/clouds",
]
reports = []
states = {}
for target in targets:
    prefix = install.repo_path(target)
    for attempt in range(3):
        before = install.read_ref(api, prefix, install.BRANCH)
        if not before:
            raise ValueError("Expected public installation missing")
        try:
            state = session.load(api, target, before)
            report = session.inspect(api, state)
            rows = []
            for row in state["ledger"]["issues"]:
                item = session.get_issue(api, state, row["issue"])
                rows.append({"issue": row["issue"], "version": row["version"],
                             "ledger_state": row["state"], "github_state": item["state"]})
            active = state["handoff"]["active"]
            pr = session.get_pr(api, state, active) if active and active["pull_request"] and report["status"] != "stale_candidate" else None
        except (ValueError, install.ApiError):
            if install.read_ref(api, prefix, install.BRANCH) != before and attempt < 2:
                continue
            raise
        if install.read_ref(api, prefix, install.BRANCH) != before:
            if attempt < 2:
                continue
            raise ValueError("Moving adopter snapshot; audit incomplete")
        break
    states[target] = state
    reports.append({"repository": target, "installed_sha": before,
        "source_sha": state["manifest"]["source_sha"], "package_files_verified": len(state["manifest"]["package_files_sha256"]),
        "product_sha_observed": state["product_sha"], "baseline": state["manifest"]["baseline_version"],
        "inspection_status": report["status"], "active_issue": active["issue"] if active else None,
        "active_phase": active["phase"] if active else None, "history_count": len(state["handoff"]["history"]),
        "active_pr": {"number": pr["number"], "state": pr["state"], "merged": pr["merged"], "head": pr["head"]["sha"]} if pr else None,
        "ledger": rows})

# Controlled minimal reproduction of #42. No network or writes used for fixture.
repo = "example/product"
ledger = {"schema_version": 1, "repository": repo, "issues": [
    {"issue": 1, "version": "v0.0.0.1", "state": "in_progress", "acceptance": ["test"]},
    {"issue": 2, "version": "v0.0.0.2", "state": "in_progress", "acceptance": ["test"]}]}
handoff = {"schema_version": 1, "active": None, "history": []}
session.validate_handoff(handoff, ledger)
active = {"issue": 1, "version": "v0.0.0.1", "phase": "Worker", "next_action": "fixture",
          "fix_sha": None, "candidate_sha": None, "pull_request": None, "evidence": []}
session.validate_handoff({**handoff, "active": active}, ledger)

# #41: controlled same-head closed or merged PR still yields resume.
sha = "a"*40
head = {**active, "phase": "Head", "fix_sha": sha, "candidate_sha": sha, "pull_request": 3,
        "evidence": ["https://github.com/example/product/actions/runs/1/attempts/1"]}
fixture = {"ref": sha, "product_sha": sha, "ledger": ledger,
           "manifest": {"baseline_version": "v0.0.0", "target_version": "v0.0.1"},
           "handoff": {**handoff, "active": head}}
for merged in (False, True):
    with patch.object(session, "get_issue", return_value={"state":"open", "title":"fixture"}), \
         patch.object(session, "get_pr", return_value={"state":"closed", "merged":merged}):
        assert session.inspect(None, fixture)["status"] == "resume"

# #43: use real observed BART ledger if still available, remove active only in a copy
# to simulate the state after its current handoff completes. Never change actual state.
bart = copy.deepcopy(states[targets[1]])
bart["handoff"]["active"] = None
open_rows = [r for r in reports[1]["ledger"] if r["github_state"] == "open"
             and r["ledger_state"] == "assigned"
             and r["version"].rsplit(".",1)[0] != bart["manifest"]["baseline_version"]]
rollover = []
for row in open_rows:
    try:
        session.claim(api, bart, row["issue"], [], "audit dry run")
    except ValueError as exc:
        if "already belongs to" not in str(exc):
            raise
        rollover.append(row["issue"])
    else:
        raise AssertionError("Historical checkpoint unexpectedly reclaimable")
print(json.dumps({"kind":"read_only_adopter_audit", "audit_checkout":os.environ["GITHUB_SHA"],
    "run":os.environ["GITHUB_RUN_ID"], "attempt":os.environ["GITHUB_RUN_ATTEMPT"],
    "adopters":reports, "observed_defects":{"41_closed_and_merged_same_head_returns_resume":True,
    "42_orphan_and_multiple_in_progress_accepted":True, "43_live_open_old_line_assignments_refused":rollover},
    "limits":["Defect reproduction is not a fix or release pass","No independent LLM trial","No private repository data or writes"]}, indent=2))
