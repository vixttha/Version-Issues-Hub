"""Read-only release preflight. Mechanical success is never release approval."""
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.request import Request, urlopen

M = json.loads(Path("ops/release-pipeline.json").read_text())
REPO = M["repository"]
ROOT = "https://api.github.com/repos/" + REPO
report = {"schema": 1, "pipeline_sha": os.environ["GITHUB_SHA"],
          "run_id": os.environ["GITHUB_RUN_ID"], "attempt": os.environ["GITHUB_RUN_ATTEMPT"],
          "mechanical": "failed", "release": "BLOCKED", "blockers": M["release_blockers"],
          "checks": []}
out = Path(os.environ["RUNNER_TEMP"]) / "vib-release-report.json"

def api(path):
    req = Request(ROOT + path, headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"],
                  "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"})
    with urlopen(req, timeout=25) as response:
        return json.load(response)

def check(label, condition):
    report["checks"].append({"name": label, "pass": bool(condition)})
    if not condition:
        raise ValueError(label)

def branch(name):
    return api("/branches/" + name)["commit"]["sha"]

def leaves(sha):
    tree = api("/git/trees/" + sha + "?recursive=1")
    check("tree complete " + sha[:7], not tree["truncated"])
    return {x["path"]: x["sha"] for x in tree["tree"] if x["type"] == "blob"}

def check_pr_revision(group, spec, p):
    check(group + " exact PR head", p["head"]["sha"] == spec["head"])
    if spec.get("merged"):
        check(group + " integrated PR", p["state"] == "closed" and p["merged"]
              and p["merge_commit_sha"] == spec["integrated_sha"])
    elif "historical_base" in spec:
        check(group + " historical licensing PR remains open draft",
              p["draft"] and p["state"] == "open" and not p["merged"])
        if p["merge_commit_sha"] != spec["merge"] or p["base"]["sha"] != spec["historical_base"]:
            report["blockers"].append(group + " requires fresh integration review")
    else:
        check(group + " frozen draft PR", p["merge_commit_sha"] == spec["merge"]
              and p["draft"] and p["state"] == "open" and not p["merged"])


def check_ledger_mappings(ledger, original):
    keys = ("issue", "version", "acceptance")
    check("22 historical mappings and criteria intact",
          len(ledger["issues"]) == 23 and len(original["issues"]) == 24
          and all({k: row[k] for k in keys} == {k: old[k] for k in keys}
                  and row["state"] == "assigned"
                  for row, old in zip(ledger["issues"][:22], original["issues"][:22])))
    check("two new engineering checkpoint mappings",
          [(r["issue"], r["version"]) for r in original["issues"][22:]] ==
          [(39, "v0.0.0.24"), (51, "v0.0.0.25")])
    by_issue = {r["issue"]: r["version"] for r in original["issues"]}
    check("closed checkpoint versions intact",
          all(by_issue.get(r["issue"]) == r["version"] for r in M["closed_checkpoints"]))
    check("unique engineering versions", len(set(by_issue.values())) == len(original["issues"]))


def receipt(group, spec):
    count = 0
    for run_id in spec["runs"]:
        attempt = spec.get("attempts", {}).get(str(run_id), spec.get("attempt", 1))
        run = api("/actions/runs/" + str(run_id))
        check(f"{group} run {run_id} exact head", run["head_sha"] == spec["head"])
        check(f"{group} run {run_id} attempt {attempt} success",
              run["run_attempt"] == attempt and run["status"] == "completed" and run["conclusion"] == "success")
        jobs = api(f"/actions/runs/{run_id}/attempts/{attempt}/jobs?per_page=100")
        check(f"{group} run {run_id} full job list", jobs["total_count"] == len(jobs["jobs"]))
        for job in jobs["jobs"]:
            check(f"{group} {job['name']} success", job["status"] == "completed" and job["conclusion"] == "success")
            check(f"{group} {job['name']} hosted", job["runner_group_name"] == "GitHub Actions" and any(x in ("ubuntu-latest", "ubuntu-24.04", "windows-latest", "macos-latest") for x in job["labels"]) and "self-hosted" not in job["labels"])
        count += len(jobs["jobs"])
    check(group + " exact job count", count == spec["jobs"])
    if "pr" in spec:
        p = api("/pulls/" + str(spec["pr"]))
        check_pr_revision(group, spec, p)
        c = api("/git/commits/" + spec["head"])
        merge = api("/git/commits/" + spec["merge"])
        base = spec.get("base", spec.get("historical_base", p["base"]["sha"]))
        check(group + " merge tree and parents", c["tree"]["sha"] == merge["tree"]["sha"] and [x["sha"] for x in merge["parents"]] == [base, spec["head"]])
        if spec.get("merged"):
            actual = api("/git/commits/" + spec["integrated_sha"])
            check(group + " actual merge equals tested tree and parents",
                  actual["tree"]["sha"] == merge["tree"]["sha"] and actual["parents"] == merge["parents"])
        checks = api("/commits/" + spec["head"] + "/check-runs?per_page=100")
        bot = [x for x in checks["check_runs"] if x["name"] == "CodeRabbit"]
        # Review is a separate release gate, not a deterministic job result.
        # Missing, pending or unsuccessful review never authorizes release.
        review = {"group": group, "head": spec["head"],
                  "status": bot[0]["status"] if bot else "missing",
                  "conclusion": bot[0]["conclusion"] if bot else None}
        report.setdefault("reviews", []).append(review)
        if review["status"] != "completed" or review["conclusion"] != "success":
            report["blockers"].append(group + " CodeRabbit review not successful")

def check_live_acceptance_matrix(spec):
    """Require both scoped live jobs and both corresponding evidence artifacts."""
    expected = {"live (core)", "live (external)"}
    for run_id in spec["live_runs"]:
        attempt = spec.get("attempts", {}).get(str(run_id), spec.get("attempt", 1))
        jobs = api(f"/actions/runs/{run_id}/attempts/{attempt}/jobs?per_page=100")
        check(f"acceptance live {run_id} complete job list", jobs["total_count"] == len(jobs["jobs"]))
        check(f"acceptance live {run_id} core and external jobs",
              {j["name"] for j in jobs["jobs"]} == expected
              and len(jobs["jobs"]) == 2
              and all(j["status"] == "completed" and j["conclusion"] == "success" for j in jobs["jobs"]))
        artifacts = api(f"/actions/runs/{run_id}/artifacts?per_page=100")
        check(f"acceptance live {run_id} complete artifacts list",
              artifacts["total_count"] == len(artifacts["artifacts"]))
        names = {f"live-acceptance-{scope}-{run_id}-{attempt}" for scope in ("core", "external")}
        matching = [a for a in artifacts["artifacts"] if a["name"] in names]
        check(f"acceptance live {run_id} exact scoped artifacts",
              len(matching) == 2 and {a["name"] for a in matching} == names
              and all(not a["expired"] and a["size_in_bytes"] > 0 for a in matching))


def check_acceptance_receipt_archives(spec):
    """Require both push and proposed-merge issue receipts and graph artifacts."""
    for record in spec["receipt_runs"]:
        run_id = record["run"]
        attempt = spec.get("attempts", {}).get(str(run_id), spec.get("attempt", 1))
        if record["event"] not in ("push", "pull_request"):
            raise ValueError("Unsupported acceptance receipt event")
        artifacts = api(f"/actions/runs/{run_id}/artifacts?per_page=100")
        check(f"acceptance receipt {run_id} complete artifact list",
              artifacts["total_count"] == len(artifacts["artifacts"]))
        expected = {f"{kind}-{record['event']}-{run_id}-{attempt}" for kind in
                    ("issue-receipts", "vib-evidence")}
        matching = [a for a in artifacts["artifacts"] if a["name"] in expected]
        check(f"acceptance receipt {run_id} exact two archives",
              len(matching) == 2 and {a["name"] for a in matching} == expected
              and all(not a["expired"] and a["size_in_bytes"] > 0 for a in matching))


def check_inspected_revisions(active, other):
    check("product revision frozen after inspection",
          active["product_sha"] == M["main"] and other["product_sha"] == M["main"])
    check("installed revision frozen after inspection",
          active["installed_sha"] == M["installed_state"] and other["installed_sha"] == M["installed_state"])

def check_final_refs():
    check("main still frozen at final read", branch("main") == M["main"])
    check("installed state still frozen at final read", branch("Version-Issues-Hub") == M["installed_state"])

def check_active_checkpoint(active, other):
    handoff = active["active"]
    check("VIB sole active release checkpoint",
          handoff["issue"] == 40
          and handoff["version"] == "v0.0.0.23"
          and handoff["phase"] == M["installed_phase"])
    # The PR under review is this pipeline itself. A new pipeline commit
    # invalidates the historical Head candidate; do not claim it is resumable.
    if handoff["phase"] == "Head" and handoff["pull_request"] == 49:
        current = api("/pulls/49")
        check("current pipeline is the exact open draft under review",
              current["head"]["sha"] == report["pipeline_sha"]
              and current["state"] == "open" and current["draft"] and not current["merged"])
        expected = "resume" if handoff["candidate_sha"] == current["head"]["sha"] else "stale_candidate"
        check("Head recovery status matches actual PR revision", active["status"] == expected)
        if expected == "stale_candidate":
            report["blockers"].append("Head handoff references historical PR49 revision; reconcile before integration")
    else:
        check("active checkpoint resumable", active["status"] == "resume")
    check("competing issue refused", other["status"] == "blocked_other_active_issue")


def main():
    check("public repository identity", api("")["visibility"] == "public" and os.environ["GITHUB_REPOSITORY"] == REPO)
    check("main frozen", branch("main") == M["main"])
    check("brand frozen", branch("Brand-Identity") == M["brand"])
    check("accepted README frozen", branch("readme-hq") == M["readme"])
    check("homepage branch pinned", branch("review/vib-homepage-preflight") == M["homepage"]["head"])
    check("self state pinned", branch("Version-Issues-Hub") == M["installed_state"])
    for key in ("engineering", "licensing_review", "homepage", "archive", "acceptance_review"):
        receipt(key, M[key])
    check_live_acceptance_matrix(M["acceptance_review"])
    check_acceptance_receipt_archives(M["acceptance_review"])
    check_live_acceptance_matrix(M["engineering"])
    check_acceptance_receipt_archives(M["engineering"])
    original = leaves(M["readme"])
    derivative = leaves(M["homepage"]["head"])
    frozen = {k:v for k,v in original.items() if k.startswith("workspace/v0.0.1/accepted/")}
    check("five accepted README blobs unchanged", len(frozen) == 5 and all(derivative.get(k) == v for k,v in frozen.items()))
    issue_list = api("/issues?state=open&per_page=100")
    check("issue listing within page", len(issue_list) < 100)
    actual = {x["number"] for x in issue_list if "pull_request" not in x}
    check("all open issues classified", actual == {x["issue"] for x in M["queue"]})
    report["issue_queue"] = M["queue"]
    for record in M["closed_checkpoints"]:
        issue = api("/issues/" + str(record["issue"]))
        check(f"issue {record['issue']} closed completed", issue["state"] == "closed" and issue["state_reason"] == "completed")
    # Use the frozen repaired VIB implementation against its own historical installation.
    def inspect(issue):
        return json.loads(subprocess.check_output(
            [sys.executable, "-m", "tools.session", "--target", REPO,
             "--expected-sha", M["installed_state"], "inspect", "--issue", str(issue)],
            cwd="frozen-engineering", text=True))
    active = inspect(40)
    other = inspect(47)
    check_active_checkpoint(active, other)
    check_inspected_revisions(active, other)
    report["vib_inspect"] = active
    # GitHub content read is immutable, and imported historical versions are not integrations.
    import base64
    def contents(path, ref):
        return json.loads(base64.b64decode(api("/contents/" + path + "?ref=" + ref)["content"]))
    handoff = contents("ledger/handoff.json", M["installed_state"])
    check("inspected handoff matches pinned ledger", active["active"] == handoff["active"])
    ledger = contents("ledger/issue-versions.json", M["installed_state"])
    original = contents("ledger/issue-versions.json", M["engineering"]["head"])
    check_ledger_mappings(ledger, original)
    check("no second active ledger row", [x["issue"] for x in ledger["issues"] if x["state"] == "in_progress"] == [40])
    check_final_refs()
    report["mechanical"] = "passed"

if __name__ == "__main__":
    try:
        main()
    finally:
        out.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
