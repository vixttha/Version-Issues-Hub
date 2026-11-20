"""Verify GitHub pull-request provenance independently of a local branch."""

import json
import os
import re
from urllib.request import Request, urlopen

REPOSITORY = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}/[A-Za-z0-9_.-]{1,100}")
COMMIT = re.compile(r"[0-9a-f]{40}")


def github_json(repository, route):
    if not REPOSITORY.fullmatch(repository):
        raise ValueError("Expected a GitHub owner/repository")
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "Graphify-HQ"}
    if token := os.environ.get("GH_TOKEN"):
        headers["Authorization"] = "Bearer " + token
    request = Request(f"https://api.github.com/repos/{repository}/{route}", headers=headers)
    with urlopen(request, timeout=15) as response:
        return json.load(response)


def pages(fetch, route):
    for page in range(1, 11):
        data = fetch(f"{route}?per_page=100&page={page}")
        if not isinstance(data, list):
            raise ValueError("Expected a GitHub API list: " + route)
        yield from data
        if len(data) < 100:
            return
    raise ValueError("GitHub API pagination limit reached: " + route)


def verify_pull_request(repository, source, expected, fetch=None):
    """Return a live observation with source membership and exact-SHA reviews."""
    num = expected["number"]
    route = f"pulls/{num}"
    if fetch is None:
        def fetch(path):
            return github_json(repository, path)

    pr = fetch(route)
    head = pr["head"]
    if (
        pr["number"] != num
        or pr["base"]["repo"]["full_name"].lower() != repository.lower()
        or (head["repo"] or {}).get("full_name", "").lower() != repository.lower()
        or head["ref"] != expected["source_branch"]
        or not COMMIT.fullmatch(head["sha"])
    ):
        raise ValueError(f"GitHub PR #{num} does not match the expected source repository and branch")

    is_head = source == head["sha"]
    if not is_head and not any(item["sha"] == source for item in pages(fetch, route + "/commits")):
        raise ValueError(f"{source} is absent from the GitHub commit list for PR #{num}")

    decisions = {}
    for review in pages(fetch, route + "/reviews"):
        if review["state"] in {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"} and review["user"]:
            decisions[review["user"]["id"]] = review
    approvals = sum(
        review["state"] == "APPROVED" and review["commit_id"] == source
        for review in decisions.values()
    )
    state = pr["state"]
    if pr["merged"]:
        state = "merged"
    elif state == "open" and pr["draft"]:
        state = "draft"
    return {
        "pull_request": f"https://github.com/{repository}/pull/{num}",
        "source_commit": source,
        "source_relation": "current head" if is_head else "historical PR commit",
        "head_commit": head["sha"],
        "pr_state": state,
        "merge_commit": pr["merge_commit_sha"] if pr["merged"] else None,
        "exact_commit_approvals": approvals,
    }
