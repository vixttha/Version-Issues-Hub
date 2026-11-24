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
        check(group + " frozen draft PR", p["head"]["sha"] == spec["head"] and p["merge_commit_sha"] == spec["merge"] and p["draft"] and p["state"] == "open" and not p["merged"])
        c = api("/git/commits/" + spec["head"])
        merge = api("/git/commits/" + spec["merge"])
        check(group + " merge tree and parents", c["tree"]["sha"] == merge["tree"]["sha"] and [x["sha"] for x in merge["parents"]] == [p["base"]["sha"], spec["head"]])
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
          active["status"] == "resume" and handoff["issue"] == 40
          and handoff["version"] == "v0.0.0.23"
          and handoff["phase"] == M["installed_phase"])
    check("competing issue refused", other["status"] == "blocked_other_active_issue")


def main():
    check("public repository identity", api("")["visibility"] == "public" and os.environ["GITHUB_REPOSITORY"] == REPO)
    check("main frozen", branch("main") == M["main"])
    check("brand frozen", branch("Brand-Identity") == M["brand"])
    check("accepted README frozen", branch("readme-hq") == M["readme"])
    check("homepage branch pinned", branch("review/vib-homepage-preflight") == M["homepage"]["head"])
    check("self state pinned", branch("Version-Issues-Hub") == M["installed_state"])
    for key in ("engineering", "licensing_review", "homepage", "archive"):
        receipt(key, M[key])
    original = leaves(M["readme"])
    derivative = leaves(M["homepage"]["head"])
    frozen = {k:v for k,v in original.items() if k.startswith("workspace/v0.0.1/accepted/")}
    check("five accepted README blobs unchanged", len(frozen) == 5 and all(derivative.get(k) == v for k,v in frozen.items()))
    issue_list = api("/issues?state=open&per_page=100")
    check("issue listing within page", len(issue_list) < 100)
    actual = {x["number"] for x in issue_list if "pull_request" not in x}
    check("all open issues classified", actual == {x["issue"] for x in M["queue"]})
    report["issue_queue"] = M["queue"]
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
    check("22 historical mappings and criteria intact", len(ledger["issues"]) == 23 and len(original["issues"]) == 22 and all({k: row[k] for k in ("issue","version","acceptance")} == {k: old[k] for k in ("issue","version","acceptance")} and row["state"] == "assigned" for row,old in zip(ledger["issues"], original["issues"])))
    check("no second active ledger row", [x["issue"] for x in ledger["issues"] if x["state"] == "in_progress"] == [40])
    check_final_refs()
    report["mechanical"] = "passed"

if __name__ == "__main__":
    try:
        main()
    finally:
        out.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
