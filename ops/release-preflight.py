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
        if "job_names" in spec:
            check(f"{group} run {run_id} exact job names",
                  sorted(job["name"] for job in jobs["jobs"]) == sorted(spec["job_names"][str(run_id)]))
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
        record_review(group, spec["head"])

def record_review(group, head):
    # Only the installed CodeRabbit GitHub App may supply review evidence.
    # Fail closed if the inventory is incomplete or exact reviews are ambiguous.
    checks = api("/commits/" + head + "/check-runs?filter=all&per_page=100")
    rows = checks["check_runs"]
    complete = checks["total_count"] == len(rows)
    bot = [x for x in rows if x.get("name") == "CodeRabbit"
           and x.get("head_sha") == head
           and (x.get("app") or {}).get("slug") == "coderabbitai"
           and (x.get("app") or {}).get("id") == 347564]
    review = {"group": group, "head": head, "inventory_complete": complete,
              "matching_checks": len(bot), "status": "missing", "conclusion": None}
    if not complete:
        review["status"] = "incomplete"
    elif len(bot) > 1:
        review["status"] = "ambiguous"
    elif len(bot) == 1:
        review.update(status=bot[0]["status"], conclusion=bot[0]["conclusion"],
                      check_id=bot[0]["id"], app_id=347564)
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

def main():
    check("public repository identity", api("")["visibility"] == "public" and os.environ["GITHUB_REPOSITORY"] == REPO)
    check("main frozen", branch("main") == M["main"])
    check("brand frozen", branch("Brand-Identity") == M["brand"])
    check("accepted README frozen", branch("readme-hq") == M["readme"])
    check("homepage branch pinned", branch("review/vib-homepage-preflight") == M["homepage"]["head"])
    check("homepage root rehearsal pinned", branch("review/vib-homepage-root-rehearsal") == M["homepage_root"]["head"])
    check("self state pinned", branch("Version-Issues-Hub") == M["installed_state"])
    for key in ("engineering", "licensing_review", "homepage", "homepage_root", "archive", "live_isolation"):
        receipt(key, M[key])
    original = leaves(M["readme"])
    derivative = leaves(M["homepage"]["head"])
    frozen = {k:v for k,v in original.items() if k.startswith("workspace/v0.0.1/accepted/")}
    check("five accepted README blobs unchanged", len(frozen) == 5 and all(derivative.get(k) == v for k,v in frozen.items()))
    legal = leaves(M["licensing_review"]["head"])
    root = leaves(M["homepage_root"]["head"])
    delta = {k for k in legal.keys() | root.keys() if legal.get(k) != root.get(k)}
    check("root rehearsal exact scope", delta == {"README.md", "assets/vib-logo.svg",
          "assets/vib-logo-light.svg", "tools/check_vib_homepage_root.cjs",
          ".github/workflows/vib-homepage-root-rehearsal.yml"})
    for name in ("vib-logo.svg", "vib-logo-light.svg"):
        check("root locked asset " + name,
              root["assets/" + name] == original["workspace/v0.0.1/accepted/assets/" + name])
    check("root rehearsal parent", [p["sha"] for p in api("/git/commits/" + M["homepage_root"]["head"])["parents"]] == [M["licensing_review"]["head"]])
    issue_list = api("/issues?state=open&per_page=100")
    check("issue listing within page", len(issue_list) < 100)
    actual = {x["number"] for x in issue_list if "pull_request" not in x}
    check("all open issues classified", actual == {x["issue"] for x in M["queue"]})
    report["issue_queue"] = M["queue"]
    # Use the frozen repaired VIB implementation against its exact installed snapshot.
    def inspect(issue):
        return json.loads(subprocess.check_output(
            [sys.executable, "-m", "tools.session", "--target", REPO,
             "--expected-sha", M["installed_state"], "inspect", "--issue", str(issue)],
            cwd="frozen-engineering", text=True))
    active = inspect(40)
    other = inspect(47)
    check("VIB sole active release checkpoint", active["status"] == "resume" and active["active"]["issue"] == 40 and active["active"]["version"] == "v0.0.0.23" and active["active"]["phase"] == M["installed_phase"])
    check("competing issue refused", other["status"] == "blocked_other_active_issue")
    check_inspected_revisions(active, other)
    report["vib_inspect"] = active
    # GitHub content read is immutable, and imported historical versions are not integrations.
    import base64
    def contents(path, ref):
        return json.loads(base64.b64decode(api("/contents/" + path + "?ref=" + ref)["content"]))
    ledger = contents("ledger/issue-versions.json", M["installed_state"])
    original = contents("ledger/issue-versions.json", M["engineering"]["head"])
    check("22 historical mappings and criteria intact", len(ledger["issues"]) == 23 and len(original["issues"]) == 22 and all({k: row[k] for k in ("issue","version","acceptance")} == {k: old[k] for k in ("issue","version","acceptance")} and row["state"] == "assigned" for row,old in zip(ledger["issues"], original["issues"])))
    check("no second active ledger row", [x["issue"] for x in ledger["issues"] if x["state"] == "in_progress"] == [40])
    check("root still frozen at final read", branch("review/vib-homepage-root-rehearsal") == M["homepage_root"]["head"])
    check_final_refs()
    report["mechanical"] = "passed"

if __name__ == "__main__":
    try:
        main()
    finally:
        out.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
