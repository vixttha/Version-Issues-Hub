"""Record release candidate identity after the public validation matrix completes."""

import argparse
import json
import os
import subprocess
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


SUPPORTING_JOBS = (
    ("Inventory and starter adoption", "lydite-adoption"),
    ("Language examples (ubuntu-24.04)", "lydite-cases-ubuntu-24.04"),
    ("Language examples (windows-latest)", "lydite-cases-windows-latest"),
    ("Rebuild and verify archived Graphify maps", None),
)


def supporting_evidence(jobs, artifacts, run_id, attempt, run_url):
    entries = []
    for job_name, artifact_prefix in SUPPORTING_JOBS:
        matches = [job for job in jobs if job["name"] == job_name]
        if len(matches) != 1 or any(
            job.get("run_attempt") != attempt or str(job.get("run_id")) != str(run_id)
            or job.get("conclusion") != "success" for job in matches
        ):
            raise ValueError(f"{job_name} has no unique successful job in attempt {attempt}. Re-run all jobs.")
        job = matches[0]
        entry = {"job": job_name, "job_id": job["id"], "attempt": attempt,
                 "job_url": f"{run_url}/job/{job['id']}"}
        if artifact_prefix is not None:
            name = f"{artifact_prefix}-attempt-{attempt}"
            found = [item for item in artifacts if item["name"] == name and not item["expired"]]
            if len(found) != 1 or not found[0].get("expires_at") or not found[0].get("digest"):
                raise ValueError(f"{name} is unavailable or incomplete. Re-run all jobs.")
            item = found[0]
            entry["artifact"] = {
                "name": name, "id": item["id"], "digest": item["digest"], "expires_at": item["expires_at"],
                "url": f"{run_url}/artifacts/{item['id']}",
            }
        entries.append(entry)
    return entries


def github_items(endpoint, key):
    data = subprocess.check_output(["gh", "api", endpoint], text=True)
    return json.loads(data)[key]


def fetch_support(repository, run_id, attempt, run_url):
    prefix = f"repos/{repository}/actions/runs/{run_id}"
    for retry in range(3):
        jobs = github_items(f"{prefix}/attempts/{attempt}/jobs?per_page=100", "jobs")
        artifacts = github_items(f"{prefix}/artifacts?per_page=100", "artifacts")
        try:
            return supporting_evidence(jobs, artifacts, run_id, attempt, run_url)
        except ValueError:
            if retry == 2:
                raise
            time.sleep(2)


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args], text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    checkout = git("rev-parse", "HEAD")
    if checkout != os.environ["GITHUB_SHA"]:
        raise SystemExit("release candidate checkout differs from the workflow revision")
    manifest = json.loads((ROOT / "versions/manifest.json").read_text(encoding="utf-8"))
    repository, run_id = os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_RUN_ID"]
    run_url = f"{os.environ['GITHUB_SERVER_URL']}/{repository}/actions/runs/{run_id}"
    attempt = int(os.environ["GITHUB_RUN_ATTEMPT"])
    try:
        evidence = fetch_support(repository, run_id, attempt, run_url)
    except (ValueError, subprocess.CalledProcessError) as error:
        raise SystemExit(f"Release-candidate evidence unavailable: {error}") from error
    record = {
        "schema_version": 1,
        "target": "v0.0.4",
        "publication_state": "awaiting-owner-approval",
        "checkout_sha": checkout,
        "tree_sha": git("rev-parse", "HEAD^{tree}"),
        "pull_request_head": os.environ.get("CANDIDATE_PR_HEAD") or None,
        "archive_current": manifest["current"],
        "archive_sources": manifest["versions"],
        "run_id": run_id,
        "attempt": str(attempt),
        "run_url": run_url,
        "completed_jobs": ["inventory-and-adoption", "examples (Ubuntu and Windows)", "graphify"],
        "supporting_evidence": evidence,
        "supporting_artifacts_expire_at": min(
            item["artifact"]["expires_at"] for item in evidence if "artifact" in item
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(f"Draft v0.0.4 release record written for {checkout}.")


if __name__ == "__main__":
    main()
