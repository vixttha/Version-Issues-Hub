"""Project-local, read-only VIB self-use preflight (not an adopter dependency)."""
import argparse
import subprocess
from pathlib import Path

from tools import checkpoint, session


def validate_projection(installed, projection, handoff, issue):
    """Refuse missing/extra assignments, criteria drift, and wrong active scope."""
    left = checkpoint.bindings(installed)
    right = checkpoint.bindings(projection)
    if installed["repository"] != projection["repository"] or left != right:
        raise ValueError("Canonical and engineering assignments differ")
    criteria = lambda ledger: {r["issue"]: r["acceptance"] for r in ledger["issues"]}
    if criteria(installed) != criteria(projection):
        raise ValueError("Canonical and engineering acceptance criteria differ")
    states = lambda ledger: {r["issue"]: r["state"] for r in ledger["issues"]}
    if states(installed) != states(projection):
        raise ValueError("Canonical and engineering checkpoint states differ")
    if installed["repository"] != "vixttha/Version-Issues-Hub":
        raise ValueError("Self-use preflight requires the VIB product repository")
    session.validate_handoff(handoff, installed)
    active = handoff["active"]
    if type(issue) is not int or active is None or active["issue"] != issue:
        raise ValueError("Requested issue does not own canonical handoff")
    if active["phase"] != "Worker":
        raise ValueError("Product edits require the canonical Worker phase")
    return active["version"]


WORKER_RECORD = Path("ledger/self-use-worker.json")


def worker_record(record, branch):
    """Bind a new engineering branch to exactly one historical Worker snapshot."""
    if (not isinstance(record, dict)
            or set(record) != {"schema_version", "issue", "version", "installed_sha"}
            or type(record["schema_version"]) is not int or record["schema_version"] != 1):
        raise ValueError("Invalid canonical Worker record")
    issue = session.issue_number(record["issue"])
    version = checkpoint.require(checkpoint.VERSION, record["version"], "checkpoint version")
    pin = checkpoint.require(checkpoint.SHA, record["installed_sha"], "installed revision")
    if branch != "plan/checkpoint-" + version:
        raise ValueError("Worker record version does not match checkpoint branch")
    return pin, issue, version


def read_projection(pin, issue):
    installed = checkpoint.parse_json(checkpoint.git("show", pin + ":ledger/issue-versions.json"))
    handoff = checkpoint.parse_json(checkpoint.git("show", pin + ":ledger/handoff.json"))
    projection = checkpoint.parse_json(Path(checkpoint.LEDGER).read_text(encoding="utf-8"))
    return validate_projection(installed, projection, handoff, issue)


def verify_checkpoint_branch(branch):
    record = checkpoint.parse_json(WORKER_RECORD.read_text(encoding="utf-8"))
    pin, issue, version = worker_record(record, branch)
    # Read the public installed ref; a historical pin must be in its ancestry.
    # This is revision-bound evidence, not a claim that the Worker is still active.
    subprocess.run(["git", "fetch", "--no-tags", "origin", "refs/heads/Version-Issues-Hub"],
                   check=True)
    if subprocess.run(["git", "merge-base", "--is-ancestor", pin, "FETCH_HEAD"],
                      check=False).returncode != 0:
        raise ValueError("Worker pin is not in canonical installed branch history")
    if read_projection(pin, issue) != version:
        raise ValueError("Worker record version differs from canonical assignment")
    return pin, issue, version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed-ref")
    parser.add_argument("--issue", type=int)
    parser.add_argument("--worker-branch")
    args = parser.parse_args()
    try:
        if args.worker_branch is not None:
            if args.installed_ref is not None or args.issue is not None:
                raise ValueError("Choose a Worker branch or an explicit installed ref and issue")
            pin, issue, version = verify_checkpoint_branch(args.worker_branch)
        else:
            pin = checkpoint.require(checkpoint.SHA, args.installed_ref, "installed revision")
            issue = session.issue_number(args.issue)
            version = read_projection(pin, issue)
        print(f"VIB self-use preflight passed: #{issue} {version} at {pin}")
    except (ValueError, KeyError, OSError, TypeError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"VIB self-use preflight refused: {exc}\n")


if __name__ == "__main__":
    main()
