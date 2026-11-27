"""Project-local, read-only VIB self-use preflight (not an adopter dependency)."""
import argparse
import copy
import hashlib
import os
import subprocess
import time
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


def read_projection(pin, issue, *, tested_head=None):
    installed = checkpoint.parse_json(checkpoint.git("show", pin + ":ledger/issue-versions.json"))
    handoff = checkpoint.parse_json(checkpoint.git("show", pin + ":ledger/handoff.json"))
    raw = (Path(checkpoint.LEDGER).read_text(encoding="utf-8") if tested_head is None
           else checkpoint.git("show", tested_head + ":" + Path(checkpoint.LEDGER).as_posix()))
    projection = checkpoint.parse_json(raw)
    return validate_projection(installed, projection, handoff, issue)


SCOPE_KEYS = {"schema_version", "repository", "issue", "version", "base_sha",
              "reviewed_sha", "previous_approval_sha", "criteria", "allowed_paths",
              "qualification", "disposition", "owner_decision"}


def validate_scope(record, ledger, issue, version):
    """Validate an independently published owner-scope record, not a candidate copy."""
    if (not isinstance(record, dict) or set(record) != SCOPE_KEYS
            or type(record["schema_version"]) is not int or record["schema_version"] != 1
            or record["repository"] != ledger["repository"]
            or type(record["issue"]) is not int or record["issue"] != issue
            or record["version"] != version or checkpoint.bindings(ledger).get(issue) != version):
        raise ValueError("Scope approval identity mismatch")
    row = next(r for r in ledger["issues"] if r["issue"] == issue)
    if record["criteria"] != row["acceptance"]:
        raise ValueError("Scope approval criteria differ")
    for key in ("base_sha", "reviewed_sha"):
        checkpoint.require(checkpoint.SHA, record[key], key)
    previous = record["previous_approval_sha"]
    if previous is None:
        if record["reviewed_sha"] != record["base_sha"]:
            raise ValueError("Initial scope approval must bind engineering baseline")
    else:
        checkpoint.require(checkpoint.SHA, previous, "previous approval")
    paths = record["allowed_paths"]
    if (not isinstance(paths, list) or not paths
            or any(not isinstance(p, str) or not p or "\\" in p
                   or any(c in p for c in ("\n", "\r", "\0", "*", "?", "[", "]", ":"))
                   or any(part in ("", ".", "..") for part in p.split("/"))
                   for p in paths) or paths != sorted(set(paths))):
        raise ValueError("Scope paths must be unique sorted literal repository paths")
    if record["qualification"] != "ordinary" or record["disposition"] != "engineering_only":
        raise ValueError("Scope cannot authorize advanced qualification or production integration")
    session.text(record["owner_decision"], "scope owner decision")
    return record


def assert_scope_paths(record, paths):
    outside = set(paths) - set(record["allowed_paths"])
    if outside:
        raise ValueError("Unauthorized scope expansion: " + ", ".join(sorted(outside)))


def changed_paths(base, head, cwd=None):
    """Raw NUL-separated diff includes deletions and both sides of renames."""
    for pin in (base, head):
        checkpoint.require(checkpoint.SHA, pin, "diff revision")
    raw = subprocess.check_output(["git", "--no-replace-objects", "diff", "--name-only", "--no-renames",
                                   "-z", base, head, "--"], cwd=cwd)
    return {p.decode("utf-8") for p in raw.split(b"\0") if p}


def scope_paths(base, head, cwd=None):
    """Include all introduced commits, even a path added and then reverted."""
    shallow = subprocess.check_output(["git", "--no-replace-objects", "rev-parse",
                                       "--is-shallow-repository"], cwd=cwd, text=True).strip()
    if shallow != "false":
        raise ValueError("Scope verification requires complete Git history")
    paths = changed_paths(base, head, cwd)
    revisions = subprocess.check_output(["git", "--no-replace-objects", "rev-list", "--max-count=129",
                                         base + ".." + head], cwd=cwd, text=True).splitlines()
    if len(revisions) > 128:
        raise ValueError("Scope history exceeds bounded checkpoint review; return to Head")
    for revision in revisions:
        checkpoint.require(checkpoint.SHA, revision, "introduced revision")
        raw = subprocess.check_output(["git", "--no-replace-objects", "diff-tree", "--root", "--no-commit-id",
                                       "-r", "-m", "--no-renames", "--name-only", "-z",
                                       revision], cwd=cwd)
        touched = {p.decode("utf-8") for p in raw.split(b"\0") if p}
        parents = subprocess.check_output(["git", "--no-replace-objects", "show", "-s", "--format=%P", revision],
                                          cwd=cwd, text=True).split()
        if len(parents) > 1:
            # A merge of an older side branch can report baseline-only files
            # against that parent. Keep paths whose merged entries differ from
            # the approved baseline; introduced parent commits are separately
            # inspected, including any later reverted change.
            touched.intersection_update(changed_paths(base, revision, cwd))
        paths.update(touched)
    return paths


def ancestor(old, new):
    if subprocess.run(["git", "--no-replace-objects", "merge-base", "--is-ancestor", old, new],
                      check=False).returncode != 0:
        raise ValueError("Scope approval or reviewed revision is not an ancestor")


def approval_change(revision, path):
    """The actual last first-parent change, not merely an equal file value."""
    return checkpoint.git("log", "--first-parent", "-1", "--format=%H", revision, "--", path) or None


def approval_parent(revision, path):
    parents = checkpoint.git("show", "-s", "--format=%P", revision).split()
    if len(parents) != 1 or changed_paths(parents[0], revision) != {path}:
        raise ValueError("Canonical scope publication must be a separate single-parent policy commit")
    return approval_change(parents[0], path)


# Incident-specific, forward-only recovery for the malformed #96 claim.
# The original combined commit is never accepted as a current approval.
# Only an independent policy-only successor may invoke this validation.
MALFORMED_043_SCOPE = "08f9b79cbbf9be50a396c1a54cf92dd308c0b268"
MALFORMED_043_PARENT = "5a7dff464e2dd763c3a72717abc0d3a2dc12dd78"


def verify_043_scope_genesis(revision, path, approval, successor, successor_revision):
    if (revision != MALFORMED_043_SCOPE
            or path != "ledger/scope-approvals/v0.0.0.43.json"
            or approval["issue"] != 96 or approval["version"] != "v0.0.0.43"
            or approval["repository"] != "vixttha/Version-Issues-Hub"
            or approval["previous_approval_sha"] is not None
            or successor["previous_approval_sha"] != revision):
        raise ValueError("Malformed scope genesis is not eligible for incident recovery")
    if (checkpoint.git("show", "-s", "--format=%P", revision).split()
            != [MALFORMED_043_PARENT]
            or changed_paths(MALFORMED_043_PARENT, revision) != {
                path, "ledger/issue-versions.json", "ledger/handoff.json"}
            or approval_change(MALFORMED_043_PARENT, path) is not None):
        raise ValueError("Malformed scope genesis ancestry or paths differ")
    if approval_parent(successor_revision, path) != revision:
        raise ValueError("Recovery must be an independent scope-policy successor")
    immutable = SCOPE_KEYS - {"reviewed_sha", "previous_approval_sha", "owner_decision"}
    if any(successor[k] != approval[k] for k in immutable):
        raise ValueError("Recovery must retain exact original scope")
    def read(rev, file):
        return checkpoint.parse_json(checkpoint.git("show", rev + ":" + file))
    old = read(MALFORMED_043_PARENT, "ledger/issue-versions.json")
    new = read(revision, "ledger/issue-versions.json")
    before = read(MALFORMED_043_PARENT, "ledger/handoff.json")
    after = read(revision, "ledger/handoff.json")
    session.validate_handoff(before, old)
    session.validate_handoff(after, new)
    checkpoint.check_history(new, old)
    if (before["schema_version"] != 1 or after["schema_version"] != 1
            or before["active"] is not None or before["history"] != after["history"]
            or new["issues"][:-1] != old["issues"]
            or new["issues"][-1] != {"issue": 96, "version": "v0.0.0.43",
                "state": "in_progress", "acceptance": approval["criteria"]}
            or after["active"]["issue"] != 96 or after["active"]["phase"] != "Worker"):
        raise ValueError("Malformed claim changed historical state or Worker identity")


def verify_forward_recovery_authority(source, specification, gate_a_evidence, *,
                                      pin, head, current, approval, successor_revision):
    """Check exact receipt binding supplied by an independently operated Head.

    Source trust is established outside the Worker and outside this candidate.
    This is cooperative evidence validation, not authentication of arbitrary
    Python callers. No CLI flag, policy file or Worker-generated record can
    configure a trusted source. A trusted Head must independently resolve the
    actual decision, including revocation/ambiguity, and Gate A evidence.
    """
    resolve = getattr(source, "resolve_verified_forward_decision", None)
    if (not callable(resolve) or not isinstance(specification, bytes) or not specification
            or not isinstance(gate_a_evidence, bytes) or not gate_a_evidence):
        raise ValueError("Explicit owner authorization for malformed #96 recovery is not established")
    binding = {
        "repository": approval["repository"], "issue": approval["issue"],
        "version": approval["version"], "incident_parent_sha": MALFORMED_043_PARENT,
        "incident_sha": MALFORMED_043_SCOPE, "recovery_successor_sha": successor_revision,
        "scope_approval_sha": pin, "canonical_revision": current, "tested_head_sha": head,
        "engineering_base_sha": approval["base_sha"],
        "scope_sha256": session.closure_digest(approval),
        "specification_sha256": hashlib.sha256(specification).hexdigest(),
        "gate_a_sha256": hashlib.sha256(gate_a_evidence).hexdigest(),
        "operations": ["qualify_forward_recovery"],
    }
    # The resolver cannot mutate our comparison basis. A true/false answer
    # or a bare policy document is never enough for this exact validation.
    receipt = copy.deepcopy(resolve(copy.deepcopy(binding)))
    if (not isinstance(receipt, dict)
            or set(receipt) != {"schema_version", "status", "decision_id", "binding",
                               "approved_at", "expires_at"}
            or type(receipt["schema_version"]) is not int or receipt["schema_version"] != 1
            or receipt["status"] != "approved"
            or not isinstance(receipt["decision_id"], str) or not receipt["decision_id"].strip()
            or not isinstance(receipt["binding"], dict)
            or session.closure_digest(receipt["binding"]) != session.closure_digest(binding)
            or type(receipt["approved_at"]) is not int or type(receipt["expires_at"]) is not int
            or not receipt["approved_at"] <= time.time() < receipt["expires_at"]):
        raise ValueError("Independent forward recovery authorization is missing, stale or invalid")
    return receipt


def verify_scope(pin, issue, version, head, current, pr_base=None, *,
                 require_recovery_authorization=False, recovery_authority_source=None,
                 reviewed_specification=None, gate_a_evidence=None, confirm_snapshot=None):
    path = "ledger/scope-approvals/" + version + ".json"
    def read(revision):
        return checkpoint.parse_json(checkpoint.git("show", revision + ":" + path))
    ledger = checkpoint.parse_json(checkpoint.git("show", pin + ":ledger/issue-versions.json"))
    approval = validate_scope(read(pin), ledger, issue, version)
    if approval_change(current, path) != pin or read(current) != approval:
        raise ValueError("Stale scope approval; reload the current canonical approval")
    if pr_base is not None and pr_base != approval["base_sha"]:
        parents = checkpoint.git("show", "-s", "--format=%P", head).split()
        if pr_base != head or len(parents) != 2 or parents[0] != approval["base_sha"]:
            raise ValueError("PR base differs from owner-approved engineering baseline")
    ancestor(approval["base_sha"], head)
    ancestor(approval["reviewed_sha"], head)
    cursor, child = pin, approval
    successor = None
    recovered = False
    for _ in range(32):
        prior = child["previous_approval_sha"]
        if cursor == MALFORMED_043_SCOPE:
            if successor is None or pin == cursor:
                raise ValueError("Malformed canonical scope requires independent recovery approval")
            verify_043_scope_genesis(cursor, path, child, successor[1], successor[0])
            recovered = True
            break
        if approval_parent(cursor, path) != prior:
            raise ValueError("Scope approval predecessor does not match actual canonical history")
        if prior is None:
            break
        if prior == cursor:
            raise ValueError("Scope approval references itself")
        ancestor(prior, cursor)
        parent = validate_scope(read(prior), ledger, issue, version)
        if (parent["base_sha"] != child["base_sha"] or parent == child
                or parent["reviewed_sha"] == child["reviewed_sha"]):
            raise ValueError("Amendment must bind a new reviewed revision and unchanged baseline")
        ancestor(parent["reviewed_sha"], child["reviewed_sha"])
        assert_scope_paths(parent, scope_paths(parent["base_sha"], child["reviewed_sha"]))
        successor = (cursor, child)
        cursor, child = prior, parent
    else:
        raise ValueError("Scope amendment chain exceeds bound")
    assert_scope_paths(approval, scope_paths(approval["base_sha"], head))
    if recovered:
        # Structural proof and a Worker-generated policy cannot confer authority.
        if require_recovery_authorization:
            receipt = verify_forward_recovery_authority(recovery_authority_source, reviewed_specification,
                gate_a_evidence, pin=pin, head=head, current=current, approval=approval,
                successor_revision=successor[0])
            if confirm_snapshot is not None:
                confirm_snapshot()
            if not receipt["approved_at"] <= time.time() < receipt["expires_at"]:
                raise ValueError("Independent forward recovery authorization expired during final review")
            if confirm_snapshot is not None:
                print(f"VIB independently supplied forward recovery disposition matched: #{issue} {version} at {pin}; read-only qualification only")
            else:
                print(f"VIB authority receipt matches supplied pins: #{issue} {version} at {pin}; LIVE SNAPSHOT UNCONFIRMED")
        else:
            if any(x is not None for x in (recovery_authority_source, reviewed_specification, gate_a_evidence)):
                raise ValueError("Recovery authority inputs require strict recovery qualification")
            print(f"VIB structural scope verified: #{issue} {version} at {pin}; OWNER AUTHORIZATION UNVERIFIED; engineering tests only")
    else:
        if any(x is not None for x in (recovery_authority_source, reviewed_specification, gate_a_evidence)):
            raise ValueError("Forward recovery authority applies only to the exact known incident")
        print(f"VIB scope record verified: #{issue} {version} at {pin}; engineering-only ordinary qualification")
    return approval


def verify_checkpoint_branch(branch, *, require_recovery_authorization=False,
                             recovery_authority_source=None, reviewed_specification=None,
                             gate_a_evidence=None):
    tested_head = None
    if require_recovery_authorization:
        tested_head = checkpoint.require(checkpoint.SHA, checkpoint.git("rev-parse", "HEAD"), "tested revision")
    raw = (WORKER_RECORD.read_text(encoding="utf-8") if tested_head is None
           else checkpoint.git("show", tested_head + ":" + WORKER_RECORD.as_posix()))
    pin, issue, version = worker_record(checkpoint.parse_json(raw), branch)
    supplied_authority = any(x is not None for x in (
        recovery_authority_source, reviewed_specification, gate_a_evidence))
    if supplied_authority and (not require_recovery_authorization
                               or (issue, version) != (96, "v0.0.0.43")):
        raise ValueError("Forward authority inputs require strict qualification of the known incident")
    # Read the public installed ref; a historical pin must be in its ancestry.
    # This is revision-bound evidence, not a claim that the Worker is still active.
    ref = "refs/heads/Version-Issues-Hub"
    rows = [line.split() for line in checkpoint.git("ls-remote", "--exit-code", "origin", ref).splitlines()]
    observed = [row for row in rows if len(row) == 2 and row[1] == ref]
    if len(observed) != 1:
        raise ValueError("Canonical installed ref is missing or ambiguous")
    current = checkpoint.require(checkpoint.SHA, observed[0][0], "observed canonical revision")
    subprocess.run(["git", "fetch", "--no-tags", "--no-write-fetch-head", "origin", current],
                   check=True)
    if subprocess.run(["git", "--no-replace-objects", "merge-base", "--is-ancestor", pin, current],
                      check=False).returncode != 0:
        raise ValueError("Worker pin is not in canonical installed branch history")
    projection_options = {"tested_head": tested_head} if tested_head is not None else {}
    if read_projection(pin, issue, **projection_options) != version:
        raise ValueError("Worker record version differs from canonical assignment")
    if checkpoint.version_number(version) >= (0, 0, 0, 41):
        head = tested_head or checkpoint.git("rev-parse", "HEAD")
        options = {"require_recovery_authorization": True} if require_recovery_authorization else {}
        if supplied_authority:
            def confirm_snapshot():
                again = [line.split() for line in checkpoint.git(
                    "ls-remote", "--exit-code", "origin", ref).splitlines()]
                if ([row for row in again if len(row) == 2 and row[1] == ref] != [[current, ref]]
                        or checkpoint.git("rev-parse", "HEAD") != head):
                    raise ValueError("Canonical or tested revision changed during recovery authority review")

            options.update(recovery_authority_source=recovery_authority_source,
                           reviewed_specification=reviewed_specification,
                           gate_a_evidence=gate_a_evidence, confirm_snapshot=confirm_snapshot)
        verify_scope(pin, issue, version, head, current, os.environ.get("VIB_PR_BASE_SHA") or None, **options)
    print(f"VIB observed canonical revision: {current}; Worker pin: {pin}")
    return pin, issue, version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installed-ref")
    parser.add_argument("--issue", type=int)
    parser.add_argument("--worker-branch")
    parser.add_argument("--require-recovery-authorization", action="store_true",
                        help="Refuse the known #96 structurally recovered scope until authorization is established")
    args = parser.parse_args()
    try:
        if args.worker_branch is not None:
            if args.installed_ref is not None or args.issue is not None:
                raise ValueError("Choose a Worker branch or an explicit installed ref and issue")
            options = {"require_recovery_authorization": True} if args.require_recovery_authorization else {}
            pin, issue, version = verify_checkpoint_branch(args.worker_branch, **options)
        else:
            if args.require_recovery_authorization:
                raise ValueError("Recovery authorization check requires --worker-branch")
            pin = checkpoint.require(checkpoint.SHA, args.installed_ref, "installed revision")
            issue = session.issue_number(args.issue)
            version = read_projection(pin, issue)
            if checkpoint.version_number(version) >= (0, 0, 0, 41):
                raise ValueError("Scope-controlled checkpoints require --worker-branch")
        print(f"VIB technical self-use preflight passed: #{issue} {version} at {pin}")
    except (ValueError, KeyError, OSError, TypeError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"VIB self-use preflight refused: {exc}\n")


if __name__ == "__main__":
    main()
