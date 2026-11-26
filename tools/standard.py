"""Read-only advisory GitHub evidence validator; not a merge-enforcement gate."""
import argparse
import os
from pathlib import Path
from tools import checkpoint, gate, install, session

KEYS = gate.POLICY_KEYS - {"publisher_app_id"}
TEST_KEYS = {"run", "attempt", "workflow_id", "job_name", "steps"}

def validate_policy(policy):
    if not isinstance(policy, dict) or set(policy) != KEYS or type(policy["schema_version"]) is not int or policy["schema_version"] != 1:
        raise ValueError("Invalid standard policy")
    install.repo_path(policy["repository"])
    session.text(policy["product_branch"], "product branch")
    for key in ("repository_id", "pull_request"):
        gate.positive(policy[key], key)
    for key in ("source_sha", "installed_sha", "head_sha", "base_sha", "merge_sha"):
        install.require(install.SHA, policy[key], key)
    seen = set()
    for row in gate.nonempty_list(policy["issues"], "owner-approved scope"):
        if not isinstance(row, dict) or set(row) != gate.ISSUE_KEYS:
            raise ValueError("Invalid issue scope")
        n = gate.positive(row["issue"], "issue")
        if n in seen:
            raise ValueError("Duplicate issue")
        seen.add(n)
        install.require(checkpoint.VERSION, row["version"], "issue version")
        install.require(install.SHA, row["fix_sha"], "fix SHA")
        for c in gate.nonempty_list(row["criteria"], "criteria"):
            if not isinstance(c, dict) or set(c) != {"text", "checks"}:
                raise ValueError("Invalid criterion")
            session.text(c["text"], "criterion")
            for t in gate.nonempty_list(c["checks"], "checks"):
                if not isinstance(t, dict) or set(t) != TEST_KEYS:
                    raise ValueError("Invalid standard check")
                for k in ("run", "attempt", "workflow_id"):
                    gate.positive(t[k], k)
                session.text(t["job_name"], "job name")
                steps = gate.nonempty_list(t["steps"], "steps")
                if any(not isinstance(s, str) or not s.strip() for s in steps) or len(steps) != len(set(steps)):
                    raise ValueError("Invalid steps")

def check_pr_run(item, policy, run, attempt):
    """A head-only run without an exact base association is not integration evidence."""
    item = install.response_object(item, "workflow run")
    if (not install.same_id(item.get("id"), run) or not install.same_id(item.get("run_attempt"), attempt)
            or not install.same_id(install.response_object(item.get("repository"), "run repository").get("id"), policy["repository_id"])
            or item.get("event") != "pull_request"
            or item.get("head_sha") not in (policy["head_sha"], policy["merge_sha"])
            or item.get("status") != "completed" or item.get("conclusion") != "success"):
        raise ValueError("Run is stale, unsuccessful or unrelated")
    prs = install.response_rows(item.get("pull_requests", []), "run PR associations")
    if ((prs or item["head_sha"] != policy["merge_sha"])
            and not any(install.same_id(p.get("number"), policy["pull_request"])
                        and install.response_object(p.get("head"), "run PR head").get("sha") == policy["head_sha"]
                        and install.response_object(p.get("base"), "run PR base").get("sha") == policy["base_sha"] for p in prs)):
        raise ValueError("Run PR association does not match current head and base")

def check_test(api, prefix, policy, evidence, test, *, post_merge=False):
    run, attempt = test["run"], test["attempt"]
    url = f"https://github.com/{policy['repository']}/actions/runs/{run}/attempts/{attempt}"
    if url.lower() not in {link.lower() for link in evidence}:
        raise ValueError("Run is not in staged evidence")
    root = prefix + "/actions/runs/" + str(run)
    for item in (api.request("GET", root), api.request("GET", root + "/attempts/" + str(attempt))):
        item = install.response_object(item, "workflow run")
        if (not install.same_id(item.get("id"), run) or not install.same_id(item.get("run_attempt"), attempt)
                or not install.same_id(install.response_object(item.get("repository"), "run repository").get("id"), policy["repository_id"])
                or not install.same_id(item.get("workflow_id"), test["workflow_id"])
                or (not post_merge and (item.get("event") != "pull_request"
                    or item.get("head_sha") not in (policy["head_sha"], policy["merge_sha"])))
                or (post_merge and (item.get("event") not in ("push", "workflow_dispatch")
                    or item.get("head_sha") != policy["merge_sha"]
                    or item.get("head_branch") != policy["product_branch"]
                    or not install.same_id(install.response_object(item.get("head_repository"), "run head repository").get("id"), policy["repository_id"])))
                or item.get("status") != "completed" or item.get("conclusion") != "success"):
            raise ValueError("Run is stale, unsuccessful or unrelated")
        if not post_merge:
            check_pr_run(item, policy, run, attempt)
    jobs = gate.exact_collection(api, root + "/attempts/" + str(attempt) + "/jobs?per_page=100", "jobs")
    matches = [j for j in jobs if j.get("name") == test["job_name"]]
    if len(matches) != 1 or matches[0].get("status") != "completed" or matches[0].get("conclusion") != "success":
        raise ValueError("Required job missing or unsuccessful")
    job = matches[0]
    if post_merge and (not install.same_id(job.get("run_id"), run) or not install.same_id(job.get("run_attempt"), attempt)
            or job.get("head_sha") != policy["merge_sha"]):
        raise ValueError("Post-merge job identity mismatch")
    for step in test["steps"]:
        matches = [s for s in install.response_rows(job.get("steps", []), "job steps") if s.get("name") == step]
        if len(matches) != 1 or matches[0].get("status") != "completed" or matches[0].get("conclusion") != "success":
            raise ValueError("Required step missing or unsuccessful")
    if post_merge:
        latest = install.response_object(api.request("GET", root), "latest run")
        if not install.same_id(latest.get("id"), run) or not install.same_id(latest.get("run_attempt"), attempt) or latest.get("status") != "completed" or latest.get("conclusion") != "success":
            raise ValueError("Post-merge run changed during review")
    return {"run": run, "attempt": attempt, "job_id": gate.positive(job["id"], "job ID"),
            "url": url, "checkout_review_required": True}


def verify_integration(api, state, active, pr, policy):
    """Reuse Standard mappings for one issue's actual merged revision; read-only."""
    session.require_unheld_scope(state, [active["issue"]])
    if state["handoff"]["schema_version"] == 2:
        session.require_experimental_parallel()
    return verify_merged_destination(api, state, active, pr, policy,
                                     state["manifest"]["product_branch"],
                                     lambda: session.get_pr(api, state, active))


def verify_merged_destination(api, state, active, pr, policy, destination, read_pr):
    """Shared exact merged-revision evidence checks; destination is selected by the caller."""
    if policy is None:
        raise ValueError("Integration requires an owner-reviewed post-merge policy")
    validate_policy(policy)
    prefix, manifest, ledger = state["prefix"], state["manifest"], state["ledger"]
    merged = install.require(install.SHA, pr.get("merge_commit_sha"), "merged revision")
    if (policy["repository"] != ledger["repository"]
            or policy["repository_id"] != manifest["target_repository_id"]
            or policy["product_branch"] != destination
            or policy["source_sha"] != manifest["source_sha"]
            or policy["installed_sha"] != state["ref"]
            or policy["pull_request"] != active["pull_request"]
            or policy["head_sha"] != active["candidate_sha"]
            or policy["merge_sha"] != merged):
        raise ValueError("Post-merge policy identity or revision mismatch")
    meta = api.request("GET", prefix)
    if (meta.get("id") != policy["repository_id"] or meta.get("private") is not False
            or meta.get("full_name") != policy["repository"]
            or meta.get("default_branch") != manifest["product_branch"]):
        raise ValueError("Post-merge verification requires the matching public repository")
    row = next(r for r in ledger["issues"] if r["issue"] == active["issue"])
    scope = policy["issues"]
    if (len(scope) != 1 or scope[0]["issue"] != active["issue"]
            or scope[0]["version"] != active["version"]
            or scope[0]["fix_sha"] != active["fix_sha"]
            or [c["text"] for c in scope[0]["criteria"]] != row["acceptance"]):
        raise ValueError("Post-merge policy must map every criterion of this issue exactly")
    def assert_merged(value):
        if (value.get("merged") is not True or value.get("state") != "closed"
                or value.get("merge_commit_sha") != merged):
            raise ValueError("Actual merged PR identity changed or is unverified")
        commit = install.response_object(api.request("GET", prefix + "/git/commits/" + merged), "merged commit")
        if (commit.get("sha") != merged or
                [p.get("sha") for p in install.response_rows(commit.get("parents"), "merge parents")] != [policy["base_sha"], policy["head_sha"]]
                or policy["base_sha"] == policy["head_sha"] or merged in (policy["base_sha"], policy["head_sha"])):
            raise ValueError("Unsupported merge history or incorrect actual merge parents")
        target = install.require(install.SHA, install.read_ref(api, prefix, policy["product_branch"]), "current product revision")
        gate.check_ancestry(api, prefix, merged, target)
    assert_merged(pr)
    gate.check_ancestry(api, prefix, active["fix_sha"], policy["head_sha"])
    links = list(dict.fromkeys(
        f"https://github.com/{policy['repository']}/actions/runs/{test['run']}/attempts/{test['attempt']}"
        for criterion in scope[0]["criteria"] for test in criterion["checks"]))
    for criterion in scope[0]["criteria"]:
        for test in criterion["checks"]:
            check_test(api, prefix, policy, links, test, post_merge=True)
    # A run checked earlier may have been rerun while a later mapping was
    # inspected. Recheck every unique run/attempt before returning a verdict.
    mappings = {(test["run"], test["attempt"], test["workflow_id"])
                for criterion in scope[0]["criteria"] for test in criterion["checks"]}
    for run, attempt, workflow in sorted(mappings):
        latest = install.response_object(api.request("GET", prefix + "/actions/runs/" + str(run)), "latest run")
        if (not install.same_id(latest.get("id"), run) or not install.same_id(latest.get("run_attempt"), attempt)
                or not install.same_id(install.response_object(latest.get("repository"), "run repository").get("id"), policy["repository_id"])
                or not install.same_id(install.response_object(latest.get("head_repository"), "run head repository").get("id"), policy["repository_id"])
                or not install.same_id(latest.get("workflow_id"), workflow)
                or latest.get("event") not in ("push", "workflow_dispatch")
                or latest.get("head_sha") != merged or latest.get("head_branch") != policy["product_branch"]
                or latest.get("status") != "completed" or latest.get("conclusion") != "success"):
            raise ValueError("Post-merge run changed during review")
    assert_merged(read_pr())
    if install.read_ref(api, prefix, install.BRANCH) != state["ref"]:
        raise ValueError("Installed state advanced during post-merge review")
    return merged, links

def evaluate(api, target, policy):
    validate_policy(policy)
    meta = api.request("GET", install.repo_path(target))
    if meta.get("private") is not False or meta.get("id") != policy["repository_id"]:
        raise ValueError("Standard public-runner profile requires a public target")
    result = gate.evaluate_scope(api, target, policy, validate_policy, check_test)
    # Recheck all mappings after job/step inspection, including earlier runs.
    prefix = install.repo_path(target)
    mappings = {(t["run"], t["attempt"], t["workflow_id"])
                for row in policy["issues"] for c in row["criteria"] for t in c["checks"]}
    for run, attempt, workflow in sorted(mappings):
        root = prefix + "/actions/runs/" + str(run)
        for path in (root + "/attempts/" + str(attempt), root):
            item = api.request("GET", path)
            check_pr_run(item, policy, run, attempt)
            if not install.same_id(item.get("workflow_id"), workflow):
                raise ValueError("Run workflow changed during review")
    if install.read_ref(api, prefix, install.BRANCH) != policy["installed_sha"]:
        raise ValueError("Installed state advanced during Standard review")
    gate.assert_current_pr(api, prefix, policy)
    # Metadata cannot establish what arbitrary product workflows executed.
    return {**result, "status": "review_required", "check": "VIB / standard advisory",
            "mode": "standard", "published": False, "merge_enforced": False,
            "owner_review_required": True, "checkout_review_required": True}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target", required=True)
    p.add_argument("--policy", required=True, type=Path)
    args = p.parse_args()
    try:
        policy = checkpoint.parse_json(args.policy.read_text(encoding="utf-8"))
        api = install.GitHub(os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN"))
        print(install.render(evaluate(api, args.target, policy)), end="")
    except (ValueError, KeyError, TypeError, OSError, install.ApiError) as exc:
        p.exit(1, f"VIB standard validation refused: {exc}\n")

if __name__ == "__main__":
    main()
