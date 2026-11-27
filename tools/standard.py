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

def check_pr_run(item, policy, run, attempt, *, api=None, prefix=None):
    """Bind exact run metadata to the preview revision or an identical Git tree."""
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
    if item["head_sha"] != policy["merge_sha"]:
        if api is None or not isinstance(prefix, str) or not prefix:
            raise ValueError("Exact run/preview tree evidence requires repository access")
        # GitHub can report the branch head for pull_request runs. It is not
        # interchangeable with a merge preview unless the full trees match.
        # Exact checkout and required workflow steps still need owner review.
        def tree_at(sha):
            sha = install.require(install.SHA, sha, "run/preview commit")
            commit = install.response_object(api.request("GET", prefix + "/git/commits/" + sha),
                                             "run/preview commit")
            if commit.get("sha") != sha:
                raise ValueError("Run/preview commit identity mismatch")
            tree = install.response_object(commit.get("tree"), "run/preview tree")
            return install.require(install.SHA, tree.get("sha"), "run/preview tree")
        if tree_at(item["head_sha"]) != tree_at(policy["merge_sha"]):
            raise ValueError("Run head tree differs from exact merge preview; head-only metadata cannot qualify a different tree. Require an exact-preview run or an independently reviewed updated head/base with identical trees; rerunning an unchanged head-only PR is insufficient")

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
            check_pr_run(item, policy, run, attempt, api=api, prefix=prefix)
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


ACTIVE_HEAD_RECOVERY = "active_head_recovery"


def verify_active_head_recovery(api, state, active, pr, policy):
    """Verify a fresh preview for an already merged active Head, retaining old pins."""
    if (set(policy) != {"schema_version", "outcome", "head_digest", "premerge", "review"}
            or type(policy["schema_version"]) is not int or policy["schema_version"] != 1
            or state["handoff"]["schema_version"] != 1):
        raise ValueError("Invalid active Head recovery policy")
    original = session.select_active(state["handoff"], active["issue"])
    if (original["phase"] != "Head" or not original["evidence"]
            or session.closure_digest(original) != policy["head_digest"]
            or {k:v for k,v in original.items() if k != "evidence"} !=
               {k:v for k,v in active.items() if k != "evidence"}
            or not set(original["evidence"]).issubset(active["evidence"])):
        raise ValueError("Active Head recovery requires the exact original Head")
    review = policy["review"]
    validate_policy(review)
    old_base = install.require(install.SHA, original.get("integration_base_sha"), "original base")
    old_preview = install.require(install.SHA, original.get("integration_merge_sha"), "original preview")
    if (review["base_sha"] == old_base or review["head_sha"] != original["candidate_sha"]
            or review["pull_request"] != original["pull_request"]):
        raise ValueError("Active Head recovery requires a changed base and unchanged candidate/PR")
    pre = policy["premerge"]
    if not isinstance(pre, dict) or set(pre) != {"merge_sha", "evidence"}:
        raise ValueError("Invalid active Head recovery premerge evidence")
    preview = install.require(install.SHA, pre["merge_sha"], "recovery preview")
    fresh = session.evidence_links(state["ledger"]["repository"], pre["evidence"])
    if not fresh or preview == old_preview:
        raise ValueError("Active Head recovery requires fresh preview evidence")
    prefix = state["prefix"]
    repo_id = state["manifest"]["target_repository_id"]
    old = install.response_object(api.request("GET", prefix + "/git/commits/" + old_preview),
                                  "original integration preview")
    if (old.get("sha") != old_preview or
            [p.get("sha") for p in install.response_rows(old.get("parents"), "original preview parents")]
            != [old_base, original["candidate_sha"]]):
        raise ValueError("Original integration preview differs")
    candidate = {**original, "integration_base_sha": review["base_sha"],
                 "integration_merge_sha": preview, "evidence": fresh}
    invalidated = session.invalidated_archive_runs(state, candidate)
    invalidated.update(session.evidence_run(state["ledger"]["repository"], link)[0]
                       for link in original["evidence"])
    preview_policy = {"repository_id": repo_id, "pull_request": original["pull_request"],
                      "head_sha": original["candidate_sha"], "base_sha": review["base_sha"],
                      "merge_sha": preview}
    def check_fresh():
        for link in fresh:
            run, attempt = session.evidence_run(state["ledger"]["repository"], link)
            if run in invalidated:
                raise ValueError("Active Head recovery cannot reuse stale run evidence")
            root = prefix + "/actions/runs/" + str(run)
            for suffix in ("", "/attempts/" + str(attempt)):
                item = install.response_object(api.request("GET", root + suffix), "recovery preview run")
                check_pr_run(item, preview_policy, run, attempt, api=api, prefix=prefix)
                if not install.response_rows(item.get("pull_requests", []), "recovery PR associations"):
                    raise ValueError("Active Head recovery requires exact PR association")
        for link in fresh:
            run, attempt = session.evidence_run(state["ledger"]["repository"], link)
            item = install.response_object(api.request("GET", prefix + "/actions/runs/" + str(run)),
                                           "latest recovery preview run")
            check_pr_run(item, preview_policy, run, attempt, api=api, prefix=prefix)
            if not install.response_rows(item.get("pull_requests", []), "recovery PR associations"):
                raise ValueError("Active Head recovery requires exact PR association")
    def read_merged():
        item = session.get_pr(api, state, original)
        if (item.get("state") != "closed" or item.get("merged") is not True
                or item.get("merge_commit_sha") != review["merge_sha"]
                or not install.same_id((item["head"].get("repo") or {}).get("id"), repo_id)):
            raise ValueError("Active Head recovery requires exact merged PR identity")
        return item
    if pr != read_merged():
        raise ValueError("Merged PR changed before recovery review")
    check_fresh()
    merged, post = verify_integration(api, state, candidate, pr, review)
    check_fresh()
    read_merged()
    branch = state["manifest"]["product_branch"]
    current = install.require(install.SHA, install.read_ref(api, prefix, branch), "current product revision")
    gate.check_ancestry(api, prefix, merged, current)
    if (install.read_ref(api, prefix, branch) != current
            or install.read_ref(api, prefix, install.BRANCH) != state["ref"]):
        raise ValueError("Product or installed revision changed during active Head recovery")
    return merged, list(dict.fromkeys(fresh + post))


def verify_integration(api, state, active, pr, policy):
    """Reuse Standard mappings for one issue's actual merged revision; read-only."""
    session.require_unheld_scope(state, [active["issue"]])
    if state["handoff"]["schema_version"] == 2:
        session.require_experimental_parallel()
    if policy is None:
        raise ValueError("Integration requires an owner-reviewed post-merge policy")
    if isinstance(policy, dict) and policy.get("outcome") == ACTIVE_HEAD_RECOVERY:
        return verify_active_head_recovery(api, state, active, pr, policy)
    validate_policy(policy)
    if active.get("integration_base_sha") != policy["base_sha"]:
        raise ValueError("Stale or unpinned integration base; historical reconciliation required")
    preview_sha = install.require(install.SHA, active.get("integration_merge_sha"), "pinned integration preview")
    prefix = state["prefix"]
    def preview_tree():
        preview = install.response_object(api.request("GET", prefix + "/git/commits/" + preview_sha),
                                          "pinned integration preview")
        if (preview.get("sha") != preview_sha
                or [p.get("sha") for p in install.response_rows(preview.get("parents"), "preview parents")]
                != [policy["base_sha"], policy["head_sha"]]):
            raise ValueError("Pinned integration preview identity or parents differ")
        return install.require(install.SHA, install.response_object(preview.get("tree"),
                               "integration preview tree").get("sha"), "integration preview tree")
    before = preview_tree()
    branch = state["manifest"]["product_branch"]
    merged, links = verify_merged_destination(api, state, active, pr, policy, branch,
                                             lambda: session.get_pr(api, state, active))
    actual = install.response_object(api.request("GET", prefix + "/git/commits/" + merged),
                                     "actual product merge")
    if (actual.get("sha") != merged
            or [p.get("sha") for p in install.response_rows(actual.get("parents"), "actual merge parents")]
            != [policy["base_sha"], policy["head_sha"]]):
        raise ValueError("Actual merge identity or parents differ")
    actual_tree = install.require(install.SHA, install.response_object(actual.get("tree"),
                                 "actual integration tree").get("sha"), "actual integration tree")
    if preview_tree() != before or actual_tree != before:
        raise ValueError("Actual merge tree differs from tested preview")
    current = install.require(install.SHA, install.read_ref(api, prefix, branch), "current product revision")
    gate.check_ancestry(api, prefix, merged, current)
    if (install.read_ref(api, prefix, branch) != current
            or install.read_ref(api, prefix, install.BRANCH) != state["ref"]):
        raise ValueError("Product integration target or installed state changed")
    return merged, links


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
            or install.product_target(meta, manifest) != manifest["product_branch"]):
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
            check_pr_run(item, policy, run, attempt, api=api, prefix=prefix)
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
