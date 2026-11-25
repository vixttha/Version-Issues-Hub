"""Project-local, read-only VIB self-use preflight (not an adopter dependency)."""
import argparse
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
    session.validate_handoff(handoff, installed)
    active = handoff["active"]
    if type(issue) is not int or active is None or active["issue"] != issue:
        raise ValueError("Requested issue does not own canonical handoff")
    if active["phase"] != "Worker":
        raise ValueError("Product edits require the canonical Worker phase")
    return active["version"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed-ref", required=True)
    parser.add_argument("--issue", type=int, required=True)
    args = parser.parse_args()
    try:
        pin = checkpoint.require(checkpoint.SHA, args.installed_ref, "installed revision")
        installed = checkpoint.parse_json(checkpoint.git("show", pin + ":ledger/issue-versions.json"))
        handoff = checkpoint.parse_json(checkpoint.git("show", pin + ":ledger/handoff.json"))
        projection = checkpoint.parse_json(Path(checkpoint.LEDGER).read_text(encoding="utf-8"))
        version = validate_projection(installed, projection, handoff, args.issue)
        print(f"VIB self-use preflight passed: #{args.issue} {version} at {pin}")
    except (ValueError, KeyError, OSError, TypeError) as exc:
        parser.exit(1, f"VIB self-use preflight refused: {exc}\n")


if __name__ == "__main__":
    main()
