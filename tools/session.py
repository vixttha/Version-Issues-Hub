"""Bootstrap VIB from an installed branch; serialize cooperative handoffs on GitHub."""
import argparse
import ast
import copy
import hashlib
import json
import os
import re
import random
import sys
import uuid
from tools import checkpoint, install

PHASES = ("Worker", "Validate", "Internal Auditor", "Head")
ACTIVE_KEYS = {"issue", "version", "phase", "next_action", "fix_sha",
               "candidate_sha", "pull_request", "evidence"}
PIN_KEYS = {"integration_base_sha", "integration_merge_sha"}
PARALLEL_HANDOFF_SCHEMA = 2
# Historical reader capability is not production activation authority.
EXPERIMENTAL_PARALLEL_ENABLED = False
SELF_USE_HELD_ISSUES = (37, 40, 53)
HANDOFF = "ledger/handoff.json"
LEDGER = "ledger/issue-versions.json"

def text(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing {label}")
    return value

def issue_number(value):
    if type(value) is not int or value <= 0:
        raise ValueError("Invalid GitHub issue or PR number")
    return value

def evidence_run(repo, link):
    pattern = re.compile(r"https://github\.com/" + re.escape(repo) +
                         r"/actions/runs/([1-9][0-9]*)/attempts/([1-9][0-9]*)", re.I)
    match = pattern.fullmatch(link) if isinstance(link, str) else None
    if match is None:
        raise ValueError("Use exact repository GitHub Actions run-attempt URLs")
    return tuple(map(int, match.groups()))


def evidence_links(repo, links):
    if not isinstance(links, list):
        raise ValueError("Use exact repository GitHub Actions run-attempt URLs")
    identities = [evidence_run(repo, link) for link in links]
    if len(set(identities)) != len(identities):
        raise ValueError("Duplicate evidence link")
    return links

def validate_active(active, ledger):
    if not isinstance(active, dict) or set(active) not in (ACTIVE_KEYS, ACTIVE_KEYS | PIN_KEYS):
        raise ValueError("Invalid active handoff schema")
    issue_number(active["issue"])
    if checkpoint.bindings(ledger).get(active["issue"]) != active["version"]:
        raise ValueError("Active issue mapping does not match ledger")
    if active["phase"] not in PHASES:
        raise ValueError("Invalid handoff phase")
    text(active["next_action"], "next action")
    fields = [active["fix_sha"], active["candidate_sha"], active["pull_request"]]
    if any(v is not None for v in fields):
        install.require(install.SHA, fields[0], "fix revision")
        install.require(install.SHA, fields[1], "candidate revision")
        issue_number(fields[2])
    if active["phase"] in ("Validate", "Internal Auditor") and any(v is None for v in fields):
        raise ValueError("Verification handoff requires a fix, candidate and PR")
    if PIN_KEYS <= set(active):
        if active["phase"] == "Worker" or any(v is None for v in fields):
            raise ValueError("Integration pins require a candidate")
        for key in PIN_KEYS:
            install.require(install.SHA, active[key], key)
    evidence_links(ledger["repository"], active["evidence"])
    if active["phase"] == "Internal Auditor" and not active["evidence"]:
        raise ValueError("Auditor handoff requires evidence references")
    if active["phase"] == "Worker" and (any(v is not None for v in fields) or active["evidence"]):
        raise ValueError("Worker handoff must not carry stale verification")
    if active["evidence"] and any(v is None for v in fields):
        raise ValueError("Evidence requires a candidate")

def supports_parallel_package(files):
    """Capability declaration in the already verified, owner-pinned reader."""
    try:
        tree = ast.parse(files.get("tools/session.py", ""))
    except (SyntaxError, TypeError, ValueError):
        return False
    declarations = [node for node in tree.body if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == "PARALLEL_HANDOFF_SCHEMA"
                            for target in node.targets)]
    return (len(declarations) == 1 and isinstance(declarations[0].value, ast.Constant)
            and type(declarations[0].value.value) is int
            and declarations[0].value.value == PARALLEL_HANDOFF_SCHEMA)


def require_experimental_parallel():
    if EXPERIMENTAL_PARALLEL_ENABLED is not True:
        raise ValueError("Experimental parallel mode suspended; separate owner-reviewed source authorization required")


def require_unheld_scope(state, numbers):
    if (state["ledger"]["repository"].lower() == install.SOURCE.lower()
            and set(numbers).intersection(SELF_USE_HELD_ISSUES)):
        raise ValueError("Owner-held or experimental self-use issue requires separate reviewed authorization")


def require_parallel_package(state):
    if state.get("parallel_supported") is not True:
        raise ValueError("Installed package lacks parallel handoff support; upgrade the pinned reader first")
    if state["manifest"].get("enforcement") != "disabled":
        raise ValueError("Parallel mode requires disabled optional enforcement")


def active_rows(handoff):
    """Read the legacy singleton or the explicitly enabled parallel collection."""
    if type(handoff.get("schema_version")) is not int:
        raise ValueError("Invalid handoff version")
    if handoff["schema_version"] == 1:
        active = handoff["active"]
        if active is not None and not isinstance(active, dict):
            raise ValueError("Invalid legacy active handoff")
        return [] if active is None else [active]
    if handoff["schema_version"] == 2 and isinstance(handoff["active"], list):
        return handoff["active"]
    raise ValueError("Invalid handoff version or active collection")


def select_active(handoff, number=None):
    rows = active_rows(handoff)
    if number is None:
        if handoff["schema_version"] == 2:
            raise ValueError("Parallel handoff requires explicit --issue")
        if not rows:
            raise ValueError("No active handoff")
        return rows[0]
    number = issue_number(number)
    selected = next((a for a in rows if a["issue"] == number), None)
    if selected is None:
        raise ValueError("Requested issue does not own an active handoff")
    return selected


def put_active(handoff, number, active):
    if handoff["schema_version"] == 1:
        handoff["active"] = active
    else:
        rows = [a for a in active_rows(handoff) if a["issue"] != number]
        if active is not None:
            rows.append(active)
        handoff["active"] = sorted(rows, key=lambda a: a["issue"])


def validate_handoff(handoff, ledger):
    if not isinstance(handoff, dict) or set(handoff) != {"schema_version", "active", "history"}:
        raise ValueError("Invalid handoff schema")
    if not isinstance(handoff["history"], list):
        raise ValueError("Invalid handoff history")
    checkpoint.bindings(ledger)
    in_progress = {row["issue"] for row in ledger["issues"] if row["state"] == "in_progress"}
    rows = active_rows(handoff)
    for active in rows:
        validate_active(active, ledger)
    numbers = [active["issue"] for active in rows]
    if len(set(numbers)) != len(numbers):
        raise ValueError("Duplicate active issue")
    if handoff["schema_version"] == 2 and numbers != sorted(numbers):
        raise ValueError("Parallel active collection must be sorted by issue")
    if in_progress != set(numbers):
        if handoff["schema_version"] == 1 and numbers:
            raise ValueError("Active issue must be the sole in-progress row; owner reconciliation required")
        raise ValueError("Orphan or unmatched in-progress issue without active handoff; owner reconciliation required")
    for record in handoff["history"]:
        if not isinstance(record, dict) or set(record) != {"handoff", "disposition", "decision", "merged_sha"}:
            raise ValueError("Invalid archived handoff")
        validate_active(record["handoff"], ledger)
        if record["disposition"] not in ("blocked", "deferred", "staged", "integrated", "rework") or (record["disposition"] != "rework" and record["handoff"]["phase"] != "Head"):
            raise ValueError("Invalid archived disposition")
        text(record["decision"], "owner decision")
        if record["disposition"] in ("staged", "integrated"):
            archived = record["handoff"]
            if any(archived[key] is None for key in ("fix_sha", "candidate_sha", "pull_request")) or not archived["evidence"]:
                raise ValueError("Archived staged/integrated handoff requires a fix, candidate, PR and evidence")
        if record["disposition"] == "integrated":
            install.require(install.SHA, record["merged_sha"], "merged revision")
        elif record["merged_sha"] is not None:
            raise ValueError("Non-integrated handoff has merged revision")
        engineering_receipt(record, ledger)
    validate_closure_history(handoff, ledger)


ENGINEERING_DECISION = "VIB-ENGINEERING-COMPLETE-1: "


def engineering_policy(policy, ledger, number):
    """Validate an explicit engineering-only envelope around Standard evidence."""
    from tools import standard
    if (not isinstance(policy, dict)
            or set(policy) != {"schema_version", "outcome", "production_branch", "engineering_branch", "review"}
            or type(policy["schema_version"]) is not int or policy["schema_version"] != 1
            or policy["outcome"] != "engineering_complete"):
        raise ValueError("Invalid engineering completion policy")
    production = text(policy["production_branch"], "production branch")
    branch = text(policy["engineering_branch"], "engineering branch")
    if branch in (production, install.BRANCH) or production == install.BRANCH:
        raise ValueError("Engineering destination must differ from production and installed branch")
    review = policy["review"]
    standard.validate_policy(review)
    row = next((r for r in ledger["issues"] if r["issue"] == issue_number(number)), None)
    scope = review["issues"]
    if (row is None or review["repository"] != ledger["repository"]
            or review["product_branch"] != branch or len(scope) != 1
            or scope[0]["issue"] != number or scope[0]["version"] != row["version"]
            or [c["text"] for c in scope[0]["criteria"]] != row["acceptance"]):
        raise ValueError("Engineering policy scope or destination mismatch")
    return review


def engineering_receipt(record, ledger):
    """Recognize only the reserved decision format, preserving legacy archives."""
    decision = record["decision"]
    if not decision.startswith(ENGINEERING_DECISION):
        return None
    receipt = checkpoint.parse_json(decision[len(ENGINEERING_DECISION):])
    if (not isinstance(receipt, dict) or set(receipt) != {"owner_decision", "policy"}
            or record["disposition"] != "deferred" or record["merged_sha"] is not None):
        raise ValueError("Invalid engineering-only archive")
    text(receipt["owner_decision"], "owner decision")
    active = record["handoff"]
    if (active["phase"] != "Head" or any(active[k] is not None for k in
            ("fix_sha", "candidate_sha", "pull_request")) or active["evidence"] or PIN_KEYS & set(active)):
        raise ValueError("Engineering-only archive must not contain production candidate pins")
    engineering_policy(receipt["policy"], ledger, active["issue"])
    return receipt


def finish_engineering(api, state, decision, *, policy, owner_approved=False, issue=None):
    """Plan engineering completion without publishing or asserting production integration."""
    from tools import standard
    if owner_approved is not True:
        raise ValueError("Explicit owner approval is required")
    validate_handoff(state["handoff"], state["ledger"])
    active = select_active(state["handoff"], issue)
    require_unheld_scope(state, [active["issue"]])
    if state["handoff"]["schema_version"] == 2:
        require_experimental_parallel()
    if (active["phase"] != "Head" or any(active[k] is not None for k in
            ("fix_sha", "candidate_sha", "pull_request")) or active["evidence"] or PIN_KEYS & set(active)):
        raise ValueError("Engineering completion requires Head without production candidate pins")
    review = engineering_policy(policy, state["ledger"], active["issue"])
    if policy["production_branch"] != state["manifest"]["product_branch"]:
        raise ValueError("Production branch does not match installed target")
    if get_issue(api, state, active["issue"]).get("state") != "open":
        raise ValueError("Issue is not open; owner reconciliation required")
    scoped = {**active, "fix_sha": review["issues"][0]["fix_sha"],
              "candidate_sha": review["head_sha"], "pull_request": review["pull_request"]}
    def read_pr():
        pr = pr_response(api.request("GET", state["prefix"] + "/pulls/" + str(review["pull_request"])))
        repo_id = state["manifest"]["target_repository_id"]
        if (not install.same_id(pr.get("number"), review["pull_request"])
                or pr["base"].get("ref") != policy["engineering_branch"]
                or not install.same_id(pr["base"]["repo"].get("id"), repo_id)
                or not install.same_id((pr["head"].get("repo") or {}).get("id"), repo_id)
                or pr["head"].get("sha") != review["head_sha"]):
            raise ValueError("Engineering PR candidate or destination changed")
        return pr
    standard.verify_merged_destination(api, state, scoped, read_pr(), review,
                                      policy["engineering_branch"], read_pr)
    if get_issue(api, state, active["issue"]).get("state") != "open":
        raise ValueError("Issue changed during engineering review")
    ledger, handoff = copy.deepcopy(state["ledger"]), copy.deepcopy(state["handoff"])
    archived = copy.deepcopy(active)
    receipt = {"owner_decision": text(decision, "owner decision"), "policy": policy}
    handoff["history"].append({"handoff": archived, "disposition": "deferred",
        "decision": ENGINEERING_DECISION + json.dumps(receipt, sort_keys=True, separators=(",", ":"), allow_nan=False),
        "merged_sha": None})
    next(row for row in ledger["issues"] if row["issue"] == active["issue"])["state"] = "deferred"
    put_active(handoff, active["issue"], None)
    validate_handoff(handoff, ledger)
    return ledger, handoff



CLOSURE_DECISION = "VIB-ISSUE-CLOSURE-1: "
CLOSURE_EXECUTION_V1 = True
CLOSURE_ARCHIVE_OCCURRENCE_V2 = True
CLOSURE_UNRESOLVED = ("pending", "executing")


def closure_digest(record):
    return hashlib.sha256(install.render(record).encode("utf-8")).hexdigest()


def closure_receipt(record):
    if not record["decision"].startswith(CLOSURE_DECISION):
        return None
    value = checkpoint.parse_json(record["decision"][len(CLOSURE_DECISION):])
    if (not isinstance(value, dict) or value.get("status") not in ("pending", "executing", "confirmed", "cancelled")
            or not isinstance(value.get("policy"), dict)):
        raise ValueError("Invalid issue closure receipt")
    if value["status"] == "executing":
        if set(value) != {"status", "policy", "execution_id"}:
            raise ValueError("Invalid closure execution receipt")
        validate_execution_id(value["execution_id"])
    elif value["status"] == "cancelled":
        if set(value) not in ({"status", "policy", "cancellation"},
                              {"status", "policy", "cancellation", "execution_id"}):
            raise ValueError("Invalid closure cancellation receipt")
        cancel = value["cancellation"]
        if (not isinstance(cancel, dict) or set(cancel) != {"owner_decision", "state", "state_reason"}
                or cancel["state"] not in ("open", "closed")
                or (cancel["state_reason"] is not None and not isinstance(cancel["state_reason"], str))):
            raise ValueError("Invalid cancellation observation")
        text(cancel["owner_decision"], "closure cancellation owner decision")
        if "execution_id" in value:
            validate_execution_id(value["execution_id"])
    elif value["status"] == "confirmed" and "execution_id" in value:
        if set(value) != {"status", "policy", "execution_id"}:
            raise ValueError("Invalid closure confirmation receipt")
        validate_execution_id(value["execution_id"])
    elif set(value) != {"status", "policy"}:
        raise ValueError("Invalid issue closure receipt")
    return value


def validate_execution_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{32}", value):
        raise ValueError("Invalid closure execution identity")
    return value


def supports_closure_execution(files):
    # Pin a reviewed capability marker; this is a compatibility check, not
    # an independent authorization or code-trust guarantee.
    code = files.get("tools/session.py", "")
    try:
        module = ast.parse(code)
    except (SyntaxError, TypeError, ValueError):
        return False
    return any(isinstance(node, ast.Assign)
               and any(isinstance(target, ast.Name) and target.id == "CLOSURE_ARCHIVE_OCCURRENCE_V2"
                       for target in node.targets)
               and isinstance(node.value, ast.Constant) and node.value.value is True
               for node in module.body) and CLOSURE_DECISION in code


def require_closure_compatible_history(handoff, supported):
    # This guard runs before the full handoff validator during load.
    if not isinstance(handoff, dict) or not isinstance(handoff.get("history"), list):
        raise ValueError("Invalid handoff history")
    for record in handoff["history"]:
        if not isinstance(record, dict):
            raise ValueError("Invalid archived handoff")
        text(record.get("decision"), "owner decision")
    if not supported and any(record["decision"].startswith(CLOSURE_DECISION)
                             for record in handoff["history"]):
        raise ValueError("Reserved closure receipt prefix requires explicit history compatibility review")


def closure_records(handoff, number):
    return [closure_receipt(r) for r in handoff["history"]
            if r["handoff"]["issue"] == number and closure_receipt(r) is not None]


def closure_archive_index(handoff, number):
    """Zero-based absolute occurrence in the immutable append-only history."""
    return next((i for i in range(len(handoff["history"]) - 1, -1, -1)
                 if handoff["history"][i]["handoff"]["issue"] == number
                 and closure_receipt(handoff["history"][i]) is None), None)


def closure_archive(handoff, number):
    index = closure_archive_index(handoff, number)
    return handoff["history"][index] if index is not None else None


def matches_closure_archive(handoff, number, policy):
    index = closure_archive_index(handoff, number)
    return (index is not None and index == policy["archive_index"]
            and closure_digest(handoff["history"][index]) == policy["archive_digest"])


def legacy_approval_statement(review):
    # Whole-string grammar, not keyword searching or natural-language inference.
    return (f"Owner-approved engineering completion: PR #{review['pull_request']}; "
            f"fix {review['issues'][0]['fix_sha']}; candidate {review['head_sha']}; "
            f"merge {review['merge_sha']}.")


def legacy_engineering_approval(archive):
    """Recognize the exact positive legacy grammar, not arbitrary prose."""
    return re.fullmatch(
        r"Owner-approved engineering completion: PR #([1-9][0-9]*); "
        r"fix ([0-9a-f]{40}); candidate ([0-9a-f]{40}); merge ([0-9a-f]{40})\.",
        archive["decision"])


def archive_has_engineering_approval(archive, ledger):
    return (engineering_receipt(archive, ledger) is not None
            or legacy_engineering_approval(archive) is not None)


def closure_policy(policy, ledger, number):
    binding = checkpoint.bindings(ledger).get(issue_number(number))
    if (binding is None or not isinstance(policy, dict) or set(policy) != {
            "schema_version", "repository", "issue", "version", "archive_ref",
            "archive_digest", "archive_index", "reason", "owner_decision", "engineering"}
            or type(policy["schema_version"]) is not int or policy["schema_version"] != 2
            or policy["repository"] != ledger["repository"]
            or issue_number(policy["issue"]) != number
            or binding != policy["version"]):
        raise ValueError("Issue closure policy identity mismatch")
    install.require(install.SHA, policy["archive_ref"], "historical archive revision")
    if type(policy["archive_index"]) is not int or policy["archive_index"] < 0:
        raise ValueError("Invalid closure archive occurrence")
    if not isinstance(policy["archive_digest"], str) or not re.fullmatch(r"[0-9a-f]{64}", policy["archive_digest"]):
        raise ValueError("Invalid closure archive digest")
    text(policy["owner_decision"], "issue-specific owner decision")
    if policy["reason"] == "completed":
        engineering_policy(policy["engineering"], ledger, number)
    elif policy["reason"] != "not_planned" or policy["engineering"] is not None:
        raise ValueError("Unsupported closure reason or engineering evidence")
    return policy


def validate_closure_approval(archive, ledger, number, policy):
    """Check immutable local approval for both loading and publication."""
    stored = engineering_receipt(archive, ledger)
    if policy["reason"] == "not_planned":
        if archive_has_engineering_approval(archive, ledger):
            raise ValueError("Engineering-complete work cannot be recorded as not planned")
        return None
    envelope = policy["engineering"]
    review = engineering_policy(envelope, ledger, number)
    if archive["disposition"] != "deferred" or (stored is not None and stored["policy"] != envelope):
        raise ValueError("Engineering closure evidence conflicts with the archive")
    expected_pins = {"fix_sha": review["issues"][0]["fix_sha"],
                     "candidate_sha": review["head_sha"], "pull_request": review["pull_request"]}
    for key, expected in expected_pins.items():
        recorded = archive["handoff"][key]
        if recorded is not None and recorded != expected:
            raise ValueError("Closure evidence conflicts with archived handoff pin: " + key)
    if stored is None and archive["decision"] != legacy_approval_statement(review):
        raise ValueError("Legacy closure requires an unambiguous approved archived PR/fix/candidate/merge tuple; owner reconciliation required")
    return review


def validate_closure_history(handoff, ledger):
    # The original archived record stays byte-for-byte intact; closure never
    # supersedes its engineering or production disposition.
    prior = {}
    pending = {}
    used = set()
    executions = set()
    confirmed_occurrences = set()
    for index, record in enumerate(handoff["history"]):
        number = record["handoff"]["issue"]
        receipt = closure_receipt(record)
        if receipt is None:
            if pending:
                raise ValueError("Issue history changed during pending closure")
            prior[number] = index
            continue
        policy = closure_policy(receipt["policy"], ledger, number)
        basis_index = prior.get(number)
        basis = handoff["history"][basis_index] if basis_index is not None else None
        if (basis is None or basis_index != policy["archive_index"]
                or closure_digest(basis) != policy["archive_digest"]
                or record["handoff"] != basis["handoff"]
                or record["disposition"] != basis["disposition"]
                or record["merged_sha"] != basis["merged_sha"]
                or basis["disposition"] not in ("deferred", "blocked")
                or (policy["reason"] == "completed" and basis["disposition"] != "deferred")):
            raise ValueError("Closure receipt changed its historical disposition")
        validate_closure_approval(basis, ledger, number, policy)
        if receipt["status"] == "pending":
            identity = closure_digest(policy)
            if pending:
                raise ValueError("Overlapping pending issue closure")
            if identity in used or basis_index in confirmed_occurrences:
                raise ValueError("Duplicate pending issue closure for confirmed archive occurrence")
            used.add(identity)
            pending[number] = receipt
        elif receipt["status"] == "executing":
            earlier = pending.get(number)
            execution = receipt["execution_id"]
            if (earlier is None or earlier["status"] != "pending" or earlier["policy"] != policy
                    or execution in executions):
                raise ValueError("Unmatched or duplicate closure execution")
            executions.add(execution)
            pending[number] = receipt
        else:
            earlier = pending.pop(number, None)
            if (earlier is None or earlier["policy"] != policy
                    or earlier.get("execution_id") != receipt.get("execution_id")
                    or (receipt["status"] == "confirmed" and earlier["status"] != "executing")):
                raise ValueError("Unmatched closure terminal receipt")
            if receipt["status"] == "confirmed":
                confirmed_occurrences.add(basis_index)
    if len(pending) > 1:
        raise ValueError("Only one pending issue closure is permitted")
    if pending and active_rows(handoff):
        raise ValueError("Pending closure must be reconciled before claiming work")
    for number in pending:
        row = next(r for r in ledger["issues"] if r["issue"] == number)
        if row["state"] != handoff["history"][prior[number]]["disposition"]:
            raise ValueError("Pending closure disposition changed")


def pending_closure(handoff):
    """Discover the single unresolved intent without needing an issue number."""
    for record in reversed(handoff["history"]):
        receipt = closure_receipt(record)
        if receipt is not None:
            number = record["handoff"]["issue"]
            records = closure_records(handoff, number)
            if records[-1]["status"] in CLOSURE_UNRESOLVED:
                last = records[-1]
                return {"issue": number, "version": last["policy"]["version"],
                        "status": last["status"],
                        "execution_id": last.get("execution_id"),
                        "policy_digest": closure_digest(last["policy"]),
                        "archive_digest": last["policy"]["archive_digest"],
                        "archive_index": last["policy"]["archive_index"]}
    return None


def closure_status(state, item):
    number = issue_number(item["number"])
    row = next((r for r in state["ledger"]["issues"] if r["issue"] == number), None)
    archive = closure_archive(state["handoff"], number)
    archive_index = closure_archive_index(state["handoff"], number)
    all_records = closure_records(state["handoff"], number)
    records = [r for r in all_records if r["policy"]["archive_index"] == archive_index]
    last = records[-1] if records else None
    reason = item.get("state_reason")
    github_state = item.get("state")
    if github_state not in ("open", "closed"):
        raise ValueError("Unverified GitHub issue state")
    matching = last and github_state == "closed" and reason == last["policy"]["reason"]
    current_basis = last and matches_closure_archive(state["handoff"], number, last["policy"])
    active = any(a["issue"] == number for a in active_rows(state["handoff"]))
    consistent = bool(row and archive and not active and row["state"] == archive["disposition"]
                      and row["state"] in ("deferred", "blocked"))
    confirmed = bool(matching and current_basis and consistent and last["status"] == "confirmed")
    engineering = "unverified"
    approved = bool(archive and archive_has_engineering_approval(archive, state["ledger"]))
    legacy = legacy_engineering_approval(archive) if archive else None
    legacy_pins_match = bool(legacy and all(
        archive["handoff"][key] is None or str(archive["handoff"][key]) == value
        for key, value in zip(("pull_request", "fix_sha", "candidate_sha"), legacy.groups()[:3])))
    if consistent and row["state"] == "deferred" and (
            engineering_receipt(archive, state["ledger"]) or legacy_pins_match):
        engineering = "recorded"
    disposition_conflict = bool(consistent and approved
                                and github_state == "closed" and reason == "not_planned")
    if confirmed and last["policy"]["reason"] == "completed" and row and row["state"] == "deferred":
        engineering = "recorded"
    if last and last["status"] == "executing":
        synchronization = "execution_reconciliation_required"
    elif last and last["status"] == "pending":
        synchronization = ("pending_confirmation" if matching else
                           ("pending_issue_close" if github_state == "open" else "conflict"))
        if not consistent or not current_basis:
            synchronization = "conflict"
    elif last and last["status"] == "cancelled":
        synchronization = "cancelled" if consistent and current_basis else "conflict"
    elif last:
        synchronization = "state_matches_historical_receipt" if confirmed else "conflict"
    else:
        synchronization = ("conflict" if github_state == "closed" and active else
                           ("historical_unverified" if github_state == "closed" else "not_recorded"))
    # Preserve an observed cancellation or the durable execution-recovery
    # warning; disposition conflict is a separate dimension.
    if disposition_conflict and synchronization not in ("cancelled", "execution_reconciliation_required"):
        synchronization = "conflict"
    return {"issue": number, "version": row["version"] if row else None,
            "engineering_completion": engineering, "github_state": github_state,
            "disposition_conflict": disposition_conflict,
            "github_state_reason": reason, "production_integrated": bool(row and row["state"] == "integrated"),
            "ledger_state": row["state"] if row else None, "closure_synchronization": synchronization,
            "archive_digest": closure_digest(archive) if archive else None,
            "archive_index": archive_index,
            "closure_receipt": last, "closure_event_verified": False,
            "historical_confirmation_recorded": bool(last and last["status"] == "confirmed"),
            "prior_archive_confirmation_recorded": any(r["status"] == "confirmed"
                and r["policy"]["archive_index"] != archive_index for r in all_records),
            "live_evidence_verified": False}


def verify_closure_basis(api, state, number, policy):
    from tools import gate, standard
    ledger, handoff = state["ledger"], state["handoff"]
    validate_handoff(handoff, ledger)
    closure_policy(policy, ledger, number)
    if state.get("closure_supported") is not True:
        raise ValueError("Installed package does not support issue closure; reviewed upgrade required")
    if active_rows(handoff):
        raise ValueError("Closure requires an empty active lane")
    # Self-use roadmap explicitly retains these unresolved gates.
    if ledger["repository"] == "vixttha/Version-Issues-Hub" and number in (37, 40, 53):
        raise ValueError("Owner-held or experimental self-use issue is not eligible")
    archive = closure_archive(handoff, number)
    row = next(r for r in ledger["issues"] if r["issue"] == number)
    if (archive is None or row["state"] != archive["disposition"]
            or row["state"] not in ("blocked", "deferred")
            or not matches_closure_archive(handoff, number, policy)):
        raise ValueError("Closure requires the current exact inactive archived disposition occurrence")
    prefix, historical = state["prefix"], policy["archive_ref"]
    if install.read_ref(api, prefix, install.BRANCH) != state["ref"]:
        raise ValueError("Installed state advanced; reload")
    gate.check_ancestry(api, prefix, historical, state["ref"])
    old_handoff = checkpoint.parse_json(install.read_text(api, prefix, HANDOFF, historical))
    old_ledger = checkpoint.parse_json(install.read_text(api, prefix, LEDGER, historical))
    old_manifest = checkpoint.parse_json(install.read_text(api, prefix, "vib-install.json", historical))
    validate_handoff(old_handoff, old_ledger)
    checkpoint.check_history(ledger, old_ledger)
    if (not matches_closure_archive(old_handoff, number, policy)
            or closure_archive(old_handoff, number) != archive
            or old_ledger["repository"] != ledger["repository"]
            or old_manifest["target_repository"] != ledger["repository"]
            or old_manifest["target_repository_id"] != state["manifest"]["target_repository_id"]
            or old_manifest["product_branch"] != state["manifest"]["product_branch"]
            or old_handoff["history"] != handoff["history"][:len(old_handoff["history"])]):
        raise ValueError("Historical closure archive or repository identity mismatch")
    review = validate_closure_approval(archive, ledger, number, policy)
    if policy["reason"] == "not_planned":
        # Reconciliation only; never create a new not-planned closure.
        item = get_issue(api, state, number)
        if item.get("state") != "closed" or item.get("state_reason") != "not_planned":
            raise ValueError("Not-planned closure requires an existing matching GitHub disposition")
        return archive
    envelope = policy["engineering"]
    if (row["state"] != "deferred" or envelope["production_branch"] != state["manifest"]["product_branch"]
            or review["source_sha"] != old_manifest["source_sha"]):
        raise ValueError("Engineering closure evidence conflicts with the archive")
    gate.check_ancestry(api, prefix, review["installed_sha"], historical)
    # Keep the reviewed historical policy immutable. Only the transient proof
    # view binds Standard's freshness check to the current mutation lease.
    proof = {**review, "installed_sha": state["ref"]}
    proof_state = {**state, "manifest": {**state["manifest"], "source_sha": old_manifest["source_sha"]}}
    active = {**archive["handoff"], "fix_sha": review["issues"][0]["fix_sha"],
              "candidate_sha": review["head_sha"], "pull_request": review["pull_request"]}
    def read_pr():
        pr = pr_response(api.request("GET", prefix + "/pulls/" + str(review["pull_request"])))
        repo_id = state["manifest"]["target_repository_id"]
        if (not install.same_id(pr.get("number"), review["pull_request"])
                or pr["base"].get("ref") != envelope["engineering_branch"]
                or not install.same_id(pr["base"]["repo"].get("id"), repo_id)
                or not install.same_id((pr["head"].get("repo") or {}).get("id"), repo_id)
                or pr["head"].get("sha") != review["head_sha"]):
            raise ValueError("Closure PR identity changed")
        return pr
    standard.verify_merged_destination(api, proof_state, active, read_pr(), proof,
                                      envelope["engineering_branch"], read_pr)
    return archive


def closure_plan(api, state, number, policy, stage, *, owner_approved=False, execution_id=None):
    if owner_approved is not True:
        raise ValueError("Explicit owner-approved issue closure required")
    if stage not in ("pending", "executing", "confirmed"):
        raise ValueError("Invalid closure stage")
    if stage == "pending":
        if execution_id is not None:
            raise ValueError("Pending intent cannot contain an execution identity")
    else:
        validate_execution_id(execution_id)
    archive = verify_closure_basis(api, state, number, policy)
    item = get_issue(api, state, number)
    status = item.get("state")
    if status not in ("open", "closed") or (status == "closed" and item.get("state_reason") != policy["reason"]):
        raise ValueError("GitHub issue state conflicts with reviewed closure")
    if stage == "confirmed" and status != "closed":
        raise ValueError("Cannot confirm closure before matching GitHub readback")
    records = closure_records(state["handoff"], number)
    last = records[-1] if records else None
    if stage == "pending" and last and last["policy"] == policy and last["status"] == "pending":
        return state["ledger"], state["handoff"]
    if (stage == "executing" and (last is None or last["status"] != "pending" or last["policy"] != policy)
            or stage == "confirmed" and (last is None or last["status"] != "executing"
                or last["policy"] != policy or last.get("execution_id") != execution_id)
            or (stage == "pending" and last and
                (last["status"] in CLOSURE_UNRESOLVED or any(
                    record["policy"] == policy or
                    (record["status"] == "confirmed" and
                     record["policy"]["archive_index"] == policy["archive_index"])
                    for record in records)))):
        raise ValueError("Conflicting or missing durable closure intent or execution")
    ledger, handoff = copy.deepcopy(state["ledger"]), copy.deepcopy(state["handoff"])
    receipt = {"status": stage, "policy": policy}
    if execution_id is not None:
        receipt["execution_id"] = execution_id
    handoff["history"].append({**archive, "decision": CLOSURE_DECISION + json.dumps(
        receipt, sort_keys=True, separators=(",", ":"), allow_nan=False)})
    validate_handoff(handoff, ledger)
    return ledger, handoff


def cancel_closure_plan(api, state, number, policy, decision, *, owner_approved=False, recovery_execution=None):
    """Retire the exact pending intent without asserting closure or replaying an issue write."""
    if owner_approved is not True:
        raise ValueError("Explicit owner-approved closure cancellation required")
    text(decision, "closure cancellation owner decision")
    ledger, handoff = state["ledger"], state["handoff"]
    validate_handoff(handoff, ledger)
    closure_policy(policy, ledger, number)
    if state.get("closure_supported") is not True or active_rows(handoff):
        raise ValueError("Cancellation requires a compatible installed package and empty lane")
    if install.read_ref(api, state["prefix"], install.BRANCH) != state["ref"]:
        raise ValueError("Installed state advanced before cancellation")
    records = closure_records(handoff, number)
    last = records[-1] if records else None
    if last is None or last["policy"] != policy:
        raise ValueError("Cancellation requires the exact durable pending intent")
    if last["status"] == "cancelled":
        if (last["cancellation"]["owner_decision"] != decision
                or last.get("execution_id") != recovery_execution):
            raise ValueError("Cancellation was already recorded with different recovery evidence")
        return ledger, handoff
    if last["status"] == "executing":
        if recovery_execution is None or validate_execution_id(recovery_execution) != last["execution_id"]:
            raise ValueError("Executing closure requires exact owner recovery identity and stopped executor")
    elif last["status"] != "pending" or recovery_execution is not None:
        raise ValueError("Only a pending closure or explicitly recovered execution may be cancelled")
    archive = closure_archive(handoff, number)
    row = next(r for r in ledger["issues"] if r["issue"] == number)
    if (archive is None or row["state"] != archive["disposition"]
            or not matches_closure_archive(handoff, number, policy)):
        raise ValueError("Pending closure archive occurrence changed")
    # A failed or superseded workflow proof is precisely why cancellation is
    # needed. Do not reverify that proof or make any GitHub issue mutation.
    item = get_issue(api, state, number)
    observed = {"owner_decision": decision, "state": item.get("state"),
                "state_reason": item.get("state_reason")}
    if (observed["state"] not in ("open", "closed")
            or (observed["state_reason"] is not None and not isinstance(observed["state_reason"], str))):
        raise ValueError("Unverified issue state for cancellation")
    if install.read_ref(api, state["prefix"], install.BRANCH) != state["ref"]:
        raise ValueError("Installed state advanced during cancellation")
    ledger, handoff = copy.deepcopy(ledger), copy.deepcopy(handoff)
    receipt = {"status": "cancelled", "policy": policy, "cancellation": observed}
    if recovery_execution is not None:
        receipt["execution_id"] = recovery_execution
    handoff["history"].append({**archive, "decision": CLOSURE_DECISION + json.dumps(
        receipt, sort_keys=True, separators=(",", ":"), allow_nan=False)})
    validate_handoff(handoff, ledger)
    return ledger, handoff


def save_closure(api, state, ledger, handoff, number, *, apply=False, owner_approved=False):
    """Publish via the existing issue-local lease and verify serialized state."""
    result = save(api, state, ledger, handoff, apply, issue=number, closure_approved=owner_approved)
    if apply:
        pin = install.require(install.SHA, result["installed_sha"], "closure publication revision")
        for path, expected in ((LEDGER, ledger), (HANDOFF, handoff)):
            actual = checkpoint.parse_json(install.read_text(api, state["prefix"], path, pin))
            if actual != expected:
                raise ValueError("Closure ledger publication readback mismatch; reload before replay")
    return result


def complete_closure(api, state, number, policy, *, owner_approved=False, apply=False):
    if owner_approved is not True:
        raise ValueError("Explicit owner-approved issue closure required")
    verify_closure_basis(api, state, number, policy)
    records = closure_records(state["handoff"], number)
    last = records[-1] if records else None
    if last is None or last["policy"] != policy or last["status"] == "cancelled":
        raise ValueError("Publish a new exact closure intent; cancelled intent cannot be replayed")
    if last["status"] == "executing":
        raise ValueError("Closure execution already acquired; owner reconciliation required; never replay PATCH")
    item = get_issue(api, state, number)
    if last["status"] == "confirmed":
        if item.get("state") != "closed" or item.get("state_reason") != policy["reason"]:
            raise ValueError("Historical closure receipt conflicts with live issue state")
        if install.read_ref(api, state["prefix"], install.BRANCH) != state["ref"]:
            raise ValueError("Installed state advanced during closure observation")
        return {"status": "historical_receipt_matches_state", "installed_sha": state["ref"],
                "closure_event_verified": False}
    if item.get("state") not in ("open", "closed") or (item["state"] == "closed" and item.get("state_reason") != policy["reason"]):
        raise ValueError("GitHub issue state conflicts with closure intent")
    if not apply:
        return {"status": "planned", "issue": number, "issue_patch_required": item["state"] == "open",
                "installed_sha": state["ref"], "production_integrated": False}
    # Each invocation acquires a unique durable claim via fast-forward CAS.
    # Competing completions/cancellation from the old parent cannot both win.
    # No issue mutation is permitted on ambiguous acquisition or stale lease.
    execution_id = uuid.uuid4().hex
    ledger, handoff = closure_plan(api, state, number, policy, "executing",
                                   owner_approved=True, execution_id=execution_id)
    try:
        acquired = save_closure(api, state, ledger, handoff, number, apply=True, owner_approved=True)
        pin = install.require(install.SHA, acquired["installed_sha"], "closure execution revision")
        if (acquired.get("status") != "saved" or acquired.get("recovered_response") is True
                or install.read_ref(api, state["prefix"], install.BRANCH) != pin):
            raise ValueError("Closure execution acquisition ambiguous or not current")
        state = {**state, "ref": pin, "ledger": ledger, "handoff": handoff}
        verify_closure_basis(api, state, number, policy)
        item = get_issue(api, state, number)
        if install.read_ref(api, state["prefix"], install.BRANCH) != pin:
            raise ValueError("Closure execution lease changed")
        if item.get("state") == "open" and policy["reason"] == "completed":
            api.request("PATCH", state["prefix"] + "/issues/" + str(number),
                        {"state": "closed", "state_reason": "completed"})
        elif item.get("state") != "closed" or item.get("state_reason") != policy["reason"]:
            raise ValueError("Issue changed before closure")
        ledger, handoff = closure_plan(api, state, number, policy, "confirmed",
                                       owner_approved=True, execution_id=execution_id)
        return save_closure(api, state, ledger, handoff, number, apply=True, owner_approved=True)
    except (ValueError, KeyError, TypeError, OSError, install.ApiError) as exc:
        raise ValueError("Closure outcome may be partial; reload durable intent/execution and live issue. "
                         "Do not replay PATCH. Stop executor before owner recovery. " + str(exc)) from exc


def load(api, target, expected_sha=None, *, _source_cache=None):
    prefix = install.repo_path(target)
    meta = api.request("GET", prefix)
    if meta.get("full_name", "").lower() != target.lower() or type(meta.get("id")) is not int:
        raise ValueError("Target repository identity mismatch")
    ref = install.read_ref(api, prefix, install.BRANCH)
    if ref is None:
        raise ValueError("VIB is not installed")
    if expected_sha is not None and ref != install.require(install.SHA, expected_sha, "expected installed SHA"):
        raise ValueError("Installed branch has advanced; reload before acting")
    def read(path):
        return install.read_text(api, prefix, path, ref)
    manifest = checkpoint.parse_json(read("vib-install.json"))
    if (manifest.get("schema_version") != 1 or manifest.get("package") != install.BRANCH
            or manifest.get("source_repository") != install.SOURCE
            or manifest.get("target_repository") != meta["full_name"]
            or manifest.get("target_repository_id") != meta["id"]
            or manifest.get("install_branch") != install.BRANCH
            or manifest.get("product_branch") != meta["default_branch"]
            or meta["default_branch"] == install.BRANCH):
        raise ValueError("Installed manifest does not match target identity or product branch")
    baseline = install.require(install.BASELINE, manifest["baseline_version"], "baseline")
    major, minor, patch = checkpoint.version_number(baseline)
    if manifest["target_version"] != f"v{major}.{minor}.{patch + 1}":
        raise ValueError("Manifest target version does not match baseline")
    install.require(install.SHA, manifest["product_baseline_sha"], "starting product revision")
    source = install.require(install.SHA, manifest["source_sha"], "source revision")
    # Reuse only immutable source content within one recovery invocation.
    # Manifest, installed bytes, live refs and ledger are still read on every load.
    if _source_cache is not None and source in _source_cache:
        expected_files = _source_cache[source]
    else:
        expected_files = install.source_files(api, source)
        if _source_cache is not None:
            _source_cache[source] = dict(expected_files)
    digests = {p: hashlib.sha256(s.encode()).hexdigest() for p, s in expected_files.items()}
    if manifest["package_files_sha256"] != digests or any(read(p) != s for p, s in expected_files.items()):
        raise ValueError("Installed package does not match pinned source")
    ledger = checkpoint.parse_json(read(LEDGER))
    checkpoint.bindings(ledger)
    if ledger["repository"] != meta["full_name"]:
        raise ValueError("Ledger belongs to another repository")
    handoff = checkpoint.parse_json(read(HANDOFF))
    closure_supported = supports_closure_execution(expected_files)
    require_closure_compatible_history(handoff, closure_supported)
    validate_handoff(handoff, ledger)
    parallel_supported = supports_parallel_package(expected_files)
    if handoff["schema_version"] == 2 and not parallel_supported:
        raise ValueError("Installed package lacks parallel handoff support")
    product = install.read_ref(api, prefix, meta["default_branch"])
    if product is None:
        raise ValueError("Product branch is missing")
    return {"prefix": prefix, "ref": ref, "manifest": manifest,
            "ledger": ledger, "handoff": handoff, "product_sha": product,
            "parallel_supported": parallel_supported,
            "closure_supported": closure_supported}

def get_issue(api, state, number):
    value = api.request("GET", state["prefix"] + "/issues/" + str(issue_number(number)))
    value = install.response_object(value, "issue")
    if not install.same_id(value.get("number"), number) or "pull_request" in value:
        raise ValueError("Expected an actual GitHub issue, not a PR")
    return value

def pr_response(pr):
    pr = install.response_object(pr, "PR")
    base = install.response_object(pr.get("base"), "PR base")
    install.response_object(base.get("repo"), "PR base repository")
    head = install.response_object(pr.get("head"), "PR head")
    if head.get("repo") is not None:
        install.response_object(head["repo"], "PR head repository")
    return pr


def get_pr(api, state, active):
    pr = pr_response(api.request("GET", state["prefix"] + "/pulls/" + str(issue_number(active["pull_request"]))))
    if (not install.same_id(pr.get("number"), active["pull_request"])
            or pr["base"].get("ref") != state["manifest"]["product_branch"]
            or not install.same_id(pr["base"]["repo"].get("id"), state["manifest"]["target_repository_id"])
            or pr["head"].get("sha") != active["candidate_sha"]):
        raise ValueError("PR candidate or target changed; return to Worker and reverify")
    return pr

def require_open_pr(api, state, active):
    pr = get_pr(api, state, active)
    if pr.get("merged") is True:
        raise ValueError("PR is merged; return to Head for owner reconciliation")
    if pr.get("state") != "open" or pr.get("merged") is not False:
        raise ValueError("PR is not open and unmerged; return to Head or rework")
    return pr


def integration_snapshot(api, state, active):
    """Read the current ordinary PR test merge, including its actual parents."""
    pr = require_open_pr(api, state, active)
    prefix = state["prefix"]
    if not install.same_id((pr.get("head", {}).get("repo") or {}).get("id"), state["manifest"]["target_repository_id"]):
        raise ValueError("PR head repository changed or unsupported")
    base = install.require(install.SHA, pr["base"].get("sha"), "PR base")
    merged = install.require(install.SHA, pr.get("merge_commit_sha"), "proposed merge")
    if install.read_ref(api, prefix, state["manifest"]["product_branch"]) != base:
        raise ValueError("Product base changed; refresh integration evidence")
    commit = install.response_object(api.request("GET", prefix + "/git/commits/" + merged), "merge commit")
    if (commit.get("sha") != merged or [p.get("sha") for p in install.response_rows(commit.get("parents"), "commit parents")] !=
            [base, active["candidate_sha"]] or base == active["candidate_sha"]):
        raise ValueError("Proposed merge parents changed or unsupported")
    observed = require_open_pr(api, state, active)
    if (observed["base"].get("sha") != base or observed.get("merge_commit_sha") != merged
            or not install.same_id((observed.get("head", {}).get("repo") or {}).get("id"), state["manifest"]["target_repository_id"])
            or install.read_ref(api, prefix, state["manifest"]["product_branch"]) != base):
        raise ValueError("Product base or proposed merge changed during inspection")
    return {"integration_base_sha": base, "integration_merge_sha": merged}

def require_fresh_snapshot(api, state, active):
    current = integration_snapshot(api, state, active)
    if any(active.get(key) != value for key, value in current.items()):
        raise ValueError("Stale or unpinned integration evidence; refresh and revalidate")
    return current

def refresh_candidate(api, state, active, note):
    """Keep the original fix only when the current PR still contains it."""
    from tools import gate
    if get_issue(api, state, active["issue"]).get("state") != "open":
        raise ValueError("Issue is not open; owner reconciliation required")
    pr = pr_response(api.request("GET", state["prefix"] + "/pulls/" + str(issue_number(active["pull_request"]))))
    candidate = install.require(install.SHA, pr["head"].get("sha"), "current PR head")
    refreshed = {**active, "candidate_sha": candidate, "phase": "Validate",
                 "next_action": text(note, "next action"), "evidence": []}
    refreshed.update(integration_snapshot(api, state, refreshed))
    gate.check_ancestry(api, state["prefix"], active["fix_sha"], candidate)
    require_fresh_snapshot(api, state, refreshed)
    return refreshed

def verify_candidate_runs(api, state, active, links):
    from tools import standard
    require_fresh_snapshot(api, state, active)
    policy = {"repository_id": state["manifest"]["target_repository_id"],
              "pull_request": active["pull_request"], "head_sha": active["candidate_sha"],
              "base_sha": active["integration_base_sha"], "merge_sha": active["integration_merge_sha"]}
    # An old run must not be re-labelled as fresh by a rerun or mutable PR
    # association. Keep its original record; require a new run for changed pins.
    invalidated = set()
    for record in state["handoff"]["history"]:
        old = record["handoff"]
        if (old["issue"] == active["issue"] and
                any(old.get(k) != active.get(k) for k in PIN_KEYS | {"candidate_sha", "pull_request"})):
            invalidated.update(evidence_run(state["ledger"]["repository"], link)[0]
                               for link in old["evidence"])
    for link in links:
        run, attempt = evidence_run(state["ledger"]["repository"], link)
        if run in invalidated:
            raise ValueError("Archived run belongs to stale integration evidence; use a new run")
        root = state["prefix"] + "/actions/runs/" + str(run)
        for item in (api.request("GET", root), api.request("GET", root + "/attempts/" + str(attempt))):
            standard.check_pr_run(item, policy, run, attempt)
    # Re-read every earlier run after all links were inspected.
    for link in links:
        run, attempt = evidence_run(state["ledger"]["repository"], link)
        standard.check_pr_run(api.request("GET", state["prefix"] + "/actions/runs/" + str(run)),
                              policy, run, attempt)
    require_fresh_snapshot(api, state, active)

def inspect(api, state, requested=None):
    handoff = state["handoff"]
    validate_handoff(handoff, state["ledger"])
    rows = active_rows(handoff)
    issue = requested if requested is not None else (rows[0]["issue"] if len(rows) == 1 else None)
    active = next((a for a in rows if a["issue"] == issue), None)
    if handoff["schema_version"] == 1 and rows:
        active = rows[0]
    info = None
    if issue is not None:
        item = get_issue(api, state, issue)
        info = {"number": issue, "title": item.get("title"), "state": item.get("state"),
                "version": checkpoint.bindings(state["ledger"]).get(issue)}
    staged = None
    if issue is not None and any(r["issue"] == issue and r["state"] == "staged" for r in state["ledger"]["issues"]):
        prior = next((r for r in reversed(state["handoff"]["history"]) if r["handoff"]["issue"] == issue), None)
        if prior is None or prior["disposition"] != "staged":
            raise ValueError("Missing latest staged handoff")
        staged = prior["handoff"]
    inspected = staged if staged is not None else active
    status = "staged" if staged is not None else ("head_scope_required" if active is None else "resume")
    if active and issue != active["issue"] and staged is None:
        status = "blocked_other_active_issue"
    if issue is None and len(rows) > 1:
        status = "issue_selection_required"
    if inspected and status in ("resume", "staged"):
        if inspected["pull_request"] is not None:
            try:
                pr = get_pr(api, state, inspected)
            except ValueError:
                status = "stale_candidate"
            else:
                if pr.get("merged") is True and pr.get("state") == "closed":
                    status = "merged_reconciliation_required"
                elif pr.get("state") == "closed" and pr.get("merged") is False:
                    status = "closed_pr_rework_required"
                elif pr.get("state") != "open" or pr.get("merged") is not False:
                    status = "pr_state_unverified"
                else:
                    try:
                        require_fresh_snapshot(api, state, inspected)
                    except (ValueError, KeyError, TypeError):
                        status = "stale_integration_evidence"
        if status in ("resume", "staged") and info["state"] != "open":
            status = "issue_reconciliation_required"
    engineering = None
    if issue is not None and any(r["issue"] == issue and r["state"] == "deferred" for r in state["ledger"]["issues"]):
        prior = closure_archive(handoff, issue)
        if prior is not None:
            engineering = engineering_receipt(prior, state["ledger"])
        if engineering is not None:
            status = "engineering_complete"
    pending = pending_closure(handoff)
    if pending is not None and requested is None:
        status = "closure_reconciliation_required"
    return {"status": status, "installed_sha": state["ref"], "product_sha": state["product_sha"],
            **({"pending_closure": pending} if pending is not None else {}),
            "repository": state["ledger"]["repository"], "baseline": state["manifest"]["baseline_version"],
            "target": state["manifest"]["target_version"], "issue": info, "active": active,
            "owner_merge_required": True, "evidence_verified": False,
            "staged": staged, **({"lifecycle": closure_status(state, item)} if info is not None else {}),
            **({"engineering_completion": engineering, "production_integrated": False}
                                  if engineering is not None else {}),
            **({"active_issues": [a["issue"] for a in rows]}
                                  if handoff["schema_version"] == 2 else {})}

def recovery_plan(api, state, requested=None):
    """Read-only, lease-bound next step and same-issue evidence reuse advisory."""
    from tools import gate
    def require_lease():
        if install.read_ref(api, state["prefix"], install.BRANCH) != state["ref"]:
            raise ValueError("Installed state advanced; reload recovery plan")
    require_lease()
    observed = inspect(api, state, requested)
    info = observed["issue"]
    number = info["number"] if info is not None else None
    status = observed["status"]
    active = observed["staged"] or observed["active"]
    lifecycle = observed.get("lifecycle") or {}
    pending = pending_closure(state["handoff"])
    if pending is not None:
        status = "closure_reconciliation_required"
    elif state["handoff"]["schema_version"] == PARALLEL_HANDOFF_SCHEMA:
        status = "experimental_history_only"
    elif (state["ledger"]["repository"] == "vixttha/Version-Issues-Hub"
          and number in SELF_USE_HELD_ISSUES):
        status = "owner_hold"
    elif lifecycle.get("closure_synchronization") == "state_matches_historical_receipt":
        status = "closure_recorded"
    elif lifecycle.get("engineering_completion") == "recorded" and status == "head_scope_required":
        status = "engineering_complete"
    actions = {
        "closure_reconciliation_required": "Reconcile durable closure with owner; never replay issue mutation.",
        "experimental_history_only": "Inspect historical state only; experimental activation remains suspended.",
        "owner_hold": "Retain owner hold; do not claim or promote this issue.",
        "closure_recorded": "Retain historical closure receipt; no new closure or integration.",
        "engineering_complete": "Retain engineering receipt; production and issue closure remain separate decisions.",
        "head_scope_required": "Head must select and authorize scope before claim.",
        "blocked_other_active_issue": "Resume the existing active issue or obtain a Head disposition.",
        "issue_selection_required": "Select the exact issue for read-only inspection.",
        "stale_candidate": "Review changed PR; refresh or return to Head without reusing stale evidence.",
        "stale_integration_evidence": "Refresh integration pins and revalidate at the current merge.",
        "merged_reconciliation_required": "Return to Head; verify actual merge and owner disposition.",
        "closed_pr_rework_required": "Return to Head for rework decision; preserve prior evidence.",
        "pr_state_unverified": "Stop and verify the actual PR state.",
        "issue_reconciliation_required": "Return to Head; reconcile the live issue and archived state.",
        "staged": "Review staged evidence; owner decides whether to revalidate or reconcile.",
    }
    phases = {
        "Worker": "Implement only approved scope; record fix and exact candidate before Validate.",
        "Validate": "Validate exact candidate and run attempts before Internal Auditor.",
        "Internal Auditor": "Audit exact scope, pins and evidence before returning to Head.",
        "Head": "Owner decides disposition; no automatic merge, closure or release.",
    }
    action = (phases[active["phase"]] if status == "resume" and active is not None
              else actions.get(status, "Stop and reconcile unknown state with Head."))
    reuse = {"status": "not_available", "links": []}
    if status in ("resume", "staged") and active is not None and active["issue"] == number:
        links = evidence_links(state["ledger"]["repository"], active["evidence"])
        if links:
            reuse["status"] = "revalidation_required"
            try:
                if (not active["fix_sha"] or not active["candidate_sha"]
                        or not active["pull_request"] or any(not active.get(k) for k in PIN_KEYS)):
                    raise ValueError("Missing exact evidence pins")
                # Only links recorded on this exact issue handoff are considered.
                # A run once recorded against another fix on this issue is stale.
                for record in state["handoff"]["history"]:
                    previous = record["handoff"]
                    if previous["issue"] == number and previous["fix_sha"] != active["fix_sha"]:
                        old_runs = {evidence_run(state["ledger"]["repository"], link)[0]
                                    for link in previous["evidence"]}
                        if any(evidence_run(state["ledger"]["repository"], link)[0] in old_runs
                               for link in links):
                            raise ValueError("Archived run belongs to another fix")
                gate.check_ancestry(api, state["prefix"], active["fix_sha"], active["candidate_sha"])
                verify_candidate_runs(api, state, active, links)
            except (ValueError, KeyError, TypeError, install.ApiError, OSError):
                reuse["status"] = "refused"
            else:
                reuse = {"status": "exact_run_revalidated", "links": links,
                         "issue": number, "fix_sha": active["fix_sha"],
                         "candidate_sha": active["candidate_sha"], "pull_request": active["pull_request"],
                         **{key: active[key] for key in sorted(PIN_KEYS)}}
            # Evidence checks may observe a PR or issue change after the initial
            # inspection. Never return the earlier phase action on that basis.
            try:
                latest = inspect(api, state, requested)
            except (ValueError, KeyError, TypeError, install.ApiError, OSError):
                status = "pr_state_unverified"
                action = actions[status]
                reuse = {"status": "refused", "links": []}
            else:
                observed = latest
                status = latest["status"]
                if status not in ("resume", "staged"):
                    action = actions.get(status, "Stop and reconcile unknown state with Head.")
                    reuse = {"status": "refused", "links": []}
                elif reuse["status"] == "refused":
                    status = "evidence_revalidation_required"
                    action = "Revalidate exact recorded evidence or return to Head; do not advance."
    require_lease()
    return {**observed, "recovery_status": status, "recommended_next_action": action,
            "evidence_reuse": reuse, "read_only": True,
            "owner_decision_required": True, "evidence_verified": False}


def verify_closed_staged_pr(api, state, previous):
    """Require the same archived PR to remain closed and unmerged."""
    pr = pr_response(api.request("GET", state["prefix"] + "/pulls/" +
                                 str(issue_number(previous["pull_request"]))))
    if (not install.same_id(pr.get("number"), previous["pull_request"])
            or pr.get("state") != "closed" or pr.get("merged") is not False
            or pr["base"].get("ref") != state["manifest"]["product_branch"]
            or not install.same_id(pr["base"]["repo"].get("id"), state["manifest"]["target_repository_id"])):
        raise ValueError("Staged rework requires a verified closed unmerged PR")


def claim(api, state, number, criteria, note, *, resume_prior_line=False, parallel=False,
          rework_staged=False):
    validate_handoff(state["handoff"], state["ledger"])
    if pending_closure(state["handoff"]) is not None:
        raise ValueError("Reconcile pending closure before claiming work")
    require_unheld_scope(state, [number])
    if parallel or state["handoff"]["schema_version"] == 2:
        require_parallel_package(state)
        require_experimental_parallel()
    item = get_issue(api, state, number)
    if item.get("state") != "open":
        raise ValueError("Only an open GitHub issue can be claimed")
    ledger = copy.deepcopy(state["ledger"])
    handoff = copy.deepcopy(state["handoff"])
    rows = active_rows(handoff)
    active = next((a for a in rows if a["issue"] == number), None)
    if active is not None:
        if rework_staged:
            raise ValueError("Staged rework requires a staged issue")
        record = next(x for x in ledger["issues"] if x["issue"] == number)
        if criteria and criteria != record["acceptance"]:
            raise ValueError("Existing acceptance criteria differ")
        return ledger, handoff
    if parallel and handoff["schema_version"] == 1:
        require_parallel_package(state)
        handoff["schema_version"] = 2
        handoff["active"] = rows
    if handoff["schema_version"] == 1 and rows:
        raise ValueError("Another issue owns the active handoff")
    if handoff["schema_version"] == 2:
        require_parallel_package(state)
    baseline = state["manifest"]["baseline_version"]
    row = next((x for x in ledger["issues"] if x["issue"] == number), None)
    if row is not None and row["state"] in ("integrated", "retired"):
        raise ValueError("Historical issue cannot be reclaimed")
    if rework_staged and (row is None or row["state"] != "staged"):
        raise ValueError("Staged rework requires a staged issue")
    if row is not None and row["state"] == "staged":
        if resume_prior_line or row["version"].rsplit(".", 1)[0] != baseline:
            raise ValueError("Staged prior-line issue requires owner reconciliation")
        if criteria and criteria != row["acceptance"]:
            raise ValueError("Existing acceptance criteria differ")
        prior = next((r for r in reversed(handoff["history"]) if r["handoff"]["issue"] == number), None)
        if prior is None or prior["disposition"] != "staged":
            raise ValueError("Missing latest staged handoff")
        if rework_staged:
            verify_closed_staged_pr(api, state, prior["handoff"])
            worker = {"issue": number, "version": row["version"], "phase": "Worker",
                      "next_action": text(note, "next action"), "fix_sha": None,
                      "candidate_sha": None, "pull_request": None, "evidence": []}
            put_active(handoff, number, worker)
        else:
            put_active(handoff, number, refresh_candidate(api, state, prior["handoff"], note))
        row["state"] = "in_progress"
        validate_handoff(handoff, ledger)
        return ledger, handoff
    if row is not None and row["version"].rsplit(".", 1)[0] != baseline:
        prior_line = row["version"].rsplit(".", 1)[0]
        if (checkpoint.version_number(prior_line) >= checkpoint.version_number(baseline)
                or row["state"] not in ("assigned", "blocked", "deferred")):
            raise ValueError("Issue is not eligible for prior-line recovery; owner reconciliation required")
        if not resume_prior_line:
            raise ValueError("Prior-line issue requires explicit owner-approved --resume-prior-line")
        version = row["version"]
    else:
        if resume_prior_line:
            raise ValueError("Prior-line recovery requires an existing eligible historical issue")
        version, _ = checkpoint.register(ledger, number, baseline, criteria)
        row = next(x for x in ledger["issues"] if x["issue"] == number)
    if criteria and criteria != row["acceptance"]:
        raise ValueError("Existing acceptance criteria differ")
    row["state"] = "in_progress"
    put_active(handoff, number, {"issue": number, "version": version, "phase": "Worker",
                         "next_action": text(note, "next action"), "fix_sha": None,
                         "candidate_sha": None, "pull_request": None, "evidence": []})
    validate_handoff(handoff, ledger)
    return ledger, handoff

def advance(api, state, note, *, fix=None, candidate=None, pr=None, evidence=None,
            rework=False, return_to_head=False, refresh=False, issue=None):
    validate_handoff(state["handoff"], state["ledger"])
    ledger = copy.deepcopy(state["ledger"])
    handoff = copy.deepcopy(state["handoff"])
    active = select_active(handoff, issue)
    active["next_action"] = text(note, "next action")
    phase = active["phase"]
    if sum((rework, return_to_head, refresh)) > 1:
        raise ValueError("Choose one transition")
    if refresh:
        if phase == "Worker" or active["pull_request"] is None:
            raise ValueError("Refresh requires an existing PR candidate")
        if any(v is not None for v in (fix, candidate, pr)) or evidence:
            raise ValueError("Refresh preserves the original fix; do not supply replacement evidence")
        previous = copy.deepcopy(select_active(state["handoff"], active["issue"]))
        put_active(handoff, active["issue"], refresh_candidate(api, state, previous, note))
        handoff["history"].append({"handoff": previous, "disposition": "rework",
                                   "decision": "Refresh integration evidence: " + note, "merged_sha": None})
    elif rework:
        if phase == "Worker":
            raise ValueError("Already in Worker phase")
        if get_issue(api, state, active["issue"]).get("state") != "open":
            raise ValueError("Issue is not open; return to Head for owner reconciliation")
        if active["pull_request"] is not None:
            # Rework is allowed for stale or closed-unmerged PRs, never for a
            # merged PR (including a changed head) or an unverified PR state.
            existing = api.request("GET", state["prefix"] + "/pulls/" +
                                   str(issue_number(active["pull_request"])))
            if (existing.get("number") != active["pull_request"]
                    or existing.get("merged") is not False
                    or existing.get("state") not in ("open", "closed")):
                raise ValueError("PR is merged or state is unverified; return to Head for owner reconciliation")
        previous = copy.deepcopy(select_active(state["handoff"], active["issue"]))
        handoff["history"].append({"handoff": previous, "disposition": "rework",
                                   "decision": note, "merged_sha": None})
        active.update(phase="Worker", fix_sha=None, candidate_sha=None, pull_request=None, evidence=[])
        for key in PIN_KEYS:
            active.pop(key, None)
    elif return_to_head:
        if phase == "Head":
            raise ValueError("Already at Head")
        active["phase"] = "Head"
    elif get_issue(api, state, active["issue"]).get("state") != "open":
        raise ValueError("Issue is not open; return to Head for owner reconciliation")
    elif phase == "Worker":
        active.update(phase="Validate", fix_sha=fix, candidate_sha=candidate, pull_request=pr, evidence=[])
        validate_active(active, ledger)
        active.update(integration_snapshot(api, state, active))
    elif phase == "Validate":
        links = evidence_links(ledger["repository"], evidence or [])
        verify_candidate_runs(api, state, active, links)
        active.update(phase="Internal Auditor", evidence=links)
    elif phase == "Internal Auditor":
        verify_candidate_runs(api, state, active, active["evidence"])
        active["phase"] = "Head"
    else:
        raise ValueError("Head must decide or return to Worker")
    validate_handoff(handoff, ledger)
    return ledger, handoff

def finish(api, state, disposition, decision, *, policy=None, issue=None):
    validate_handoff(state["handoff"], state["ledger"])
    ledger = copy.deepcopy(state["ledger"])
    handoff = copy.deepcopy(state["handoff"])
    active = select_active(handoff, issue)
    if active["phase"] != "Head":
        raise ValueError("Return to Head before deciding")
    if disposition not in ("blocked", "deferred", "staged", "integrated"):
        raise ValueError("Invalid disposition")
    if text(decision, "owner decision").startswith(ENGINEERING_DECISION):
        raise ValueError("Use the dedicated engineering completion command")
    merged = None
    if policy is not None and disposition != "integrated":
        raise ValueError("Post-merge policy applies only to integration")
    if disposition in ("staged", "integrated"):
        if not active["evidence"]:
            raise ValueError("Integration requires recorded verification evidence")
        pr = get_pr(api, state, active)
        if disposition == "staged":
            if pr.get("state") != "open" or pr.get("merged") is not False:
                raise ValueError("Staging requires an open unmerged PR")
            verify_candidate_runs(api, state, active, active["evidence"])
        else:
            if pr.get("state") != "closed" or pr.get("merged") is not True:
                raise ValueError("GitHub does not report a closed, merged PR")
            from tools import standard
            merged, links = standard.verify_integration(api, state, active, pr, policy)
            active["evidence"] = list(dict.fromkeys(active["evidence"] + links))
            decision = integration_decision(decision, policy)
    handoff["history"].append({"handoff": active, "disposition": disposition,
                               "decision": text(decision, "owner decision"), "merged_sha": merged})
    next(x for x in ledger["issues"] if x["issue"] == active["issue"])["state"] = disposition
    put_active(handoff, active["issue"], None)
    validate_handoff(handoff, ledger)
    return ledger, handoff

def integration_decision(decision, policy):
    # Preserve the exact reviewed mapping in the existing decision field, without
    # changing the v1 archive schema or rewriting earlier receipts.
    return text(decision, "owner decision") + "\nPost-merge policy: " + json.dumps(
        policy, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)

def reconcile(api, state, number, decision, *, policy=None):
    validate_handoff(state["handoff"], state["ledger"])
    if pending_closure(state["handoff"]) is not None:
        raise ValueError("Reconcile unresolved closure before integration reconciliation")
    ledger = copy.deepcopy(state["ledger"])
    handoff = copy.deepcopy(state["handoff"])
    # Reconciliation operates on one staged issue, not the active slot.
    # Its exact post-merge policy and final save scope protect other records.
    row = next((x for x in ledger["issues"] if x["issue"] == issue_number(number)), None)
    if row is None or row["state"] != "staged":
        raise ValueError("Integration reconciliation requires a staged issue")
    prior = next((x for x in reversed(handoff["history"]) if x["handoff"]["issue"] == number), None)
    if prior is None or prior["disposition"] != "staged":
        raise ValueError("Missing latest staged handoff")
    active = copy.deepcopy(prior["handoff"])
    pr = get_pr(api, state, active)
    if pr.get("state") != "closed" or pr.get("merged") is not True:
        raise ValueError("GitHub does not report a closed, merged PR")
    if not active["evidence"]:
        raise ValueError("Integration requires recorded verification evidence")
    from tools import standard
    merged, links = standard.verify_integration(api, state, active, pr, policy)
    active["evidence"] = list(dict.fromkeys(active["evidence"] + links))
    handoff["history"].append({"handoff": active, "disposition": "integrated",
        "decision": integration_decision(decision, policy), "merged_sha": merged})
    row["state"] = "integrated"
    return ledger, handoff


def verify_operation_commit(commit, operation_id):
    if (not isinstance(operation_id, str) or not re.fullmatch(r"[0-9a-f]{64}", operation_id)
            or not isinstance(commit.get("message"), str)
            or commit["message"].strip().splitlines()[-1:] != ["VIB-Operation: " + operation_id]):
        raise ValueError("Candidate operation receipt does not match")


def confirm_handoff(api, prefix, old, new, tree, *, operation_id=None):
    """Confirm the exact proposed commit, even if a later transaction advanced the ref."""
    for value, label in ((old, "previous"), (new, "candidate"), (tree, "tree")):
        install.require(install.SHA, value, label + " revision")
    for delay in (0, 0.25, 0.5, 1, 2, 4):
        if delay:
            install.time.sleep(delay)
        observed = install.read_ref(api, prefix, install.BRANCH)
        if observed == new:
            if operation_id is not None:
                commit = install.response_object(api.request("GET", prefix + "/git/commits/" + new), "candidate commit")
                if (commit.get("sha") != new or install.response_object(commit.get("tree"), "commit tree").get("sha") != tree
                        or [p.get("sha") for p in install.response_rows(commit.get("parents"), "commit parents")] != [old]):
                    raise ValueError("Candidate commit does not match the proposed transaction")
                verify_operation_commit(commit, operation_id)
            return observed
        if observed == old:
            continue
        if observed is None:
            raise ValueError("Installed branch disappeared")
        comparison = install.response_object(api.request("GET", prefix + "/compare/" + new + "..." + observed), "candidate comparison")
        if (comparison.get("status") != "ahead" or type(comparison.get("behind_by")) is not int
                or comparison.get("behind_by") != 0
                or type(comparison.get("ahead_by")) is not int or comparison["ahead_by"] <= 0
                or install.response_object(comparison.get("base_commit"), "base commit").get("sha") != new
                or install.response_object(comparison.get("merge_base_commit"), "merge base").get("sha") != new):
            raise ValueError("Observed revision does not establish candidate ancestry")
        commit = install.response_object(api.request("GET", prefix + "/git/commits/" + new), "candidate commit")
        if (commit.get("sha") != new or install.response_object(commit.get("tree"), "commit tree").get("sha") != tree
                or [p.get("sha") for p in install.response_rows(commit.get("parents"), "commit parents")] != [old]):
            raise ValueError("Candidate commit does not match the proposed transaction")
        if operation_id is not None:
            verify_operation_commit(commit, operation_id)
        return observed
    raise ValueError("Handoff commit not confirmed")

def persist_recovery_ticket(directory, ticket):
    """Opt-in host journal: immutable per-candidate file, flushed before PATCH."""
    from pathlib import Path
    root = Path(directory)
    if not root.is_dir():
        raise ValueError("Recovery directory must already exist")
    op = ticket.get("operation_id")
    candidate = ticket.get("candidate_sha")
    if not isinstance(op, str) or not re.fullmatch(r"[0-9a-f]{64}", op):
        raise ValueError("Invalid recovery operation identity")
    install.require(install.SHA, candidate, "recovery candidate")
    return persist_journal_record(root, op + "-" + candidate + ".json", ticket)


def persist_journal_record(root, filename, record):
    path = root / filename
    data = install.render(record).encode("utf-8")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    # Never overwrite a prior receipt (including a partial or corrupt receipt).
    # A failed write leaves a visible file and stops publication.
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    if os.name == "posix":
        dfd = os.open(root, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    return path


def validate_pending_intent(intent, prefix=None):
    keys = {"schema_version", "repository", "issue", "initial_sha", "operation_id"}
    if (not isinstance(intent, dict) or set(intent) != keys
            or type(intent["schema_version"]) is not int or intent["schema_version"] != 1
            or not isinstance(intent["repository"], str)
            or not intent["repository"].startswith("/repos/")
            or (prefix is not None and intent["repository"] != prefix)):
        raise ValueError("Invalid pending intent or repository mismatch")
    issue_number(intent["issue"])
    install.require(install.SHA, intent["initial_sha"], "initial installed SHA")
    op = intent["operation_id"]
    if not isinstance(op, str) or not re.fullmatch(r"[0-9a-f]{64}", op):
        raise ValueError("Invalid pending operation identity")
    return op


def persist_pending_intent(directory, intent):
    from pathlib import Path
    root = Path(directory)
    if not root.is_dir():
        raise ValueError("Recovery directory must already exist")
    op = validate_pending_intent(intent)
    return persist_journal_record(root, op + ".pending.json", intent)


def inspect_pending(api, state, path):
    """Read-only inventory; missing/unconfirmed evidence never authorizes replay."""
    from pathlib import Path
    path = Path(path)
    intent = checkpoint.parse_json(path.read_text(encoding="utf-8"))
    op = validate_pending_intent(intent, state["prefix"])
    if path.name != op + ".pending.json":
        raise ValueError("Pending journal filename does not match operation identity")
    outcomes = []
    for candidate in sorted(path.parent.glob(op + "-*.json")):
        candidate_sha = install.require(install.SHA, candidate.name[len(op)+1:-5],
                                        "recovery candidate filename")
        try:
            ticket = checkpoint.parse_json(candidate.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            # A damaged file cannot establish publication or nonpublication.
            # Preserve it untouched and keep inspecting the other tickets.
            outcomes.append({"status": "unreadable", "candidate_sha": candidate_sha,
                             "origin_ancestry_verified": False})
            continue
        if (not isinstance(ticket, dict) or ticket.get("operation_id") != op
                or ticket.get("issue") != intent["issue"]
                or ticket.get("repository") != intent["repository"]
                or candidate.name != op + "-" + str(ticket.get("candidate_sha")) + ".json"):
            raise ValueError("Pending candidate does not match journal identity")
        install.require(install.SHA, ticket.get("candidate_sha"), "recovery candidate")
        try:
            origin = intent["initial_sha"]
            parent = install.require(install.SHA, ticket.get("parent_sha"), "recovery parent")
            if origin != parent:
                try:
                    comparison = api.request("GET", state["prefix"] + "/compare/" + origin + "..." + parent)
                except install.ApiError as exc:
                    if exc.status != 404 or exc.retry_after is not None:
                        raise
                    raise ValueError("Pending journal origin or parent not found") from exc
                comparison = install.response_object(comparison, "journal ancestry")
                base = install.response_object(comparison.get("merge_base_commit"), "merge base")
                if (comparison.get("status") != "ahead"
                        or type(comparison.get("behind_by")) is not int or comparison["behind_by"] != 0
                        or type(comparison.get("ahead_by")) is not int or comparison["ahead_by"] <= 0
                        or base.get("sha") != origin
                        or install.response_object(comparison.get("base_commit"), "base commit").get("sha") != origin):
                    raise ValueError("Pending origin is not an ancestor of candidate parent")
            try:
                result = inspect_operation(api, state, ticket)
            except install.ApiError as exc:
                if exc.status != 404 or exc.retry_after is not None:
                    raise
                raise ValueError("Pending candidate evidence not found") from exc
            result["origin_ancestry_verified"] = True
        except ValueError:
            # Unconfirmed evidence is not proof of nonpublication. API errors
            # (including throttling) propagate immediately; do not keep polling.
            result = {"status": "unconfirmed", "candidate_sha": ticket["candidate_sha"],
                      "origin_ancestry_verified": False}
        outcomes.append(result)
    return {"status": "inspection_only", "operation_id": op, "issue": intent["issue"],
            "initial_sha": intent["initial_sha"], "candidates": outcomes,
            "origin_intent_authenticated": False,
            "read_only": True, "automatic_replay": False}


def non_state_entries(entries):
    """Exclude only the two state files and their tree ancestors."""
    return {p: entry for p, entry in entries.items()
            if p not in (LEDGER, HANDOFF)
            and not (entry[0] == "tree"
                     and any(f.startswith(p + "/") for f in (LEDGER, HANDOFF)))}


def inspect_operation(api, state, ticket):
    """Read-only proof of one published candidate; never resume or replay a write."""
    keys = {"schema_version", "repository", "issue", "parent_sha", "candidate_sha",
            "tree_sha", "operation_id"}
    if (not isinstance(ticket, dict) or set(ticket) != keys
            or type(ticket["schema_version"]) is not int or ticket["schema_version"] != 1
            or ticket["repository"] != state["prefix"]):
        raise ValueError("Invalid recovery ticket or repository mismatch")
    number = issue_number(ticket["issue"])
    old, new, tree = (install.require(install.SHA, ticket[k], k)
                      for k in ("parent_sha", "candidate_sha", "tree_sha"))
    operation_id = ticket["operation_id"]
    if not isinstance(operation_id, str) or not re.fullmatch(r"[0-9a-f]{64}", operation_id):
        raise ValueError("Invalid recovery operation identity")
    if old == new:
        raise ValueError("Invalid recovery candidate parent")
    try:
        observed = confirm_handoff(api, state["prefix"], old, new, tree,
                                   operation_id=operation_id)
        # Bind the issue label to the actual candidate delta, not only the ticket.
        # A matching trailer alone must not certify an unrelated tree mutation.
        from tools import lifecycle
        _, prior_entries = lifecycle.tree_entries(api, state["prefix"], old)
        observed_tree, next_entries = lifecycle.tree_entries(api, state["prefix"], new)
        # Recursive Git tree listings also contain ancestor directory entries,
        # whose object IDs change when either allowed state file changes.
        if observed_tree != tree or non_state_entries(prior_entries) != non_state_entries(next_entries):
            raise ValueError("Recovery candidate changed unrelated tree entries")
        def read_state(path, ref, entries):
            entry = entries.get(path)
            raw = install.read_text(api, state["prefix"], path, ref)
            if entry != ("blob", "100644", lifecycle.blob_id(raw)):
                raise ValueError("Recovery state blob identity mismatch")
            return checkpoint.parse_json(raw)
        before = read_state(LEDGER, old, prior_entries)
        after = read_state(LEDGER, new, next_entries)
        h0 = read_state(HANDOFF, old, prior_entries)
        h1 = read_state(HANDOFF, new, next_entries)
        if (before["repository"] != state["ledger"]["repository"]
                or after["repository"] != before["repository"]):
            raise ValueError("Recovery ledger repository mismatch")
        check_issue_delta({**state, "ledger": before, "handoff": h0}, after, h1, number,
                          historical=True)
        if issue_view(before, h0, number) == issue_view(after, h1, number):
            raise ValueError("Recovery candidate has no issue-local change")
    except (AttributeError, KeyError, TypeError) as exc:
        raise ValueError("Malformed recovery evidence; publication not confirmed") from exc
    return {"status": "published", "installed_sha": new, "observed_sha": observed,
            "issue": number, "operation_id": operation_id, "read_only": True}


class HandoffUnconfirmed(ValueError):
    """An exact candidate is available for inspection, not blind resubmission."""
    def __init__(self, candidate, retry_after=None):
        self.candidate_sha = candidate
        self.retry_after = retry_after
        delay = f"; wait at least {retry_after} seconds before inspecting" if retry_after is not None else ""
        super().__init__("Handoff outcome unconfirmed; inspect candidate " + candidate + " before retrying" + delay)

def check_issue_delta(state, ledger, handoff, number=None, *, historical=False):
    """Only one explicitly scoped issue may change in a session transaction.

    Preserve unrelated rows and active work, immutable existing criteria, and
    the exact historical archive prefix. Legacy callers may omit the issue
    only when the current/new active slot or a single append identifies it.
    This is a cooperative data-integrity guard, not an authorization boundary.
    Only read-only historical inspection may bypass current activation/hold rules;
    all save and recovery publication paths use the default mutation guard.
    """
    before_ledger, before_handoff = state["ledger"], state["handoff"]
    validate_handoff(before_handoff, before_ledger)
    checkpoint.check_history(ledger, before_ledger)
    validate_handoff(handoff, ledger)
    if ledger["repository"] != before_ledger["repository"]:
        raise ValueError("Ledger repository changed")
    history = before_handoff["history"]
    if handoff["history"][:len(history)] != history:
        raise ValueError("Historical handoff changed")
    appended = handoff["history"][len(history):]
    previous = {a["issue"]: a for a in active_rows(before_handoff)}
    proposed = {a["issue"]: a for a in active_rows(handoff)}
    changed = {n for n in previous.keys() | proposed.keys() if previous.get(n) != proposed.get(n)}
    migration = before_handoff["schema_version"] != handoff["schema_version"]
    if migration and (before_handoff["schema_version"], handoff["schema_version"]) != (1, 2):
        raise ValueError("Handoff schema downgrade is not supported")
    if number is None:
        if len(changed) == 1:
            number = next(iter(changed))
        elif not changed and appended:
            number = appended[0]["handoff"]["issue"]
        elif ledger == before_ledger and handoff == before_handoff:
            return
        else:
            raise ValueError("Issue scope required for state mutation")
    number = issue_number(number)
    if not historical:
        require_unheld_scope(state, [number])
    old_rows = {r["issue"]: r for r in before_ledger["issues"]}
    new_rows = {r["issue"]: r for r in ledger["issues"]}
    if {n:r for n,r in old_rows.items() if n != number} != {
            n:r for n,r in new_rows.items() if n != number}:
        raise ValueError("Issue scope violation: unrelated ledger row changed")
    if [r for r in before_ledger["issues"] if r["issue"] != number] != [
            r for r in ledger["issues"] if r["issue"] != number]:
        raise ValueError("Issue scope violation: unrelated ledger order changed")
    if number in old_rows:
        if new_rows[number]["acceptance"] != old_rows[number]["acceptance"]:
            raise ValueError("Issue scope violation: existing acceptance criteria changed")
        if old_rows[number]["state"] in ("integrated", "retired") and new_rows[number] != old_rows[number]:
            raise ValueError("Issue scope violation: terminal issue changed")
    if changed - {number}:
        raise ValueError("Issue scope violation: unrelated active handoff changed")
    if migration and (number in previous or number not in proposed or appended
                      or state["manifest"].get("enforcement", "disabled") != "disabled"):
        raise ValueError("Parallel migration requires a new owner-approved active claim")
    if handoff["schema_version"] == 2:
        require_parallel_package(state)
        if not historical:
            require_experimental_parallel()
    if any(r["handoff"]["issue"] != number for r in appended):
        raise ValueError("Issue scope violation: unrelated history appended")
    if number not in new_rows:
        raise ValueError("Issue scope does not identify a ledger record")
    if number in old_rows and old_rows[number]["state"] in ("integrated", "retired") and appended:
        raise ValueError("Issue scope violation: terminal issue history appended")


class HandoffStale(ValueError):
    """A known pre-publication conflict: no ref PATCH was sent."""


class HandoffRejected(install.ApiError):
    """A definitive ref rejection, not an ambiguous transport outcome."""
    def __init__(self, error, candidate, tree, operation_id=None):
        super().__init__(error.status, "PATCH", "git/refs", error.retry_after)
        self.candidate_sha, self.tree_sha = candidate, tree
        self.operation_id = operation_id


def save(api, state, ledger, handoff, apply=False, *, issue=None, operation_id=None,
         on_recovery_ticket=None, policy=None, engineering_approved=False, closure_approved=False):
    if operation_id is not None and (not isinstance(operation_id, str)
            or not re.fullmatch(r"[0-9a-f]{64}", operation_id)):
        raise ValueError("Invalid operation identity")
    check_issue_delta(state, ledger, handoff, issue)
    if ledger == state["ledger"] and handoff == state["handoff"]:
        return {"status": "unchanged", "installed_sha": state["ref"]}
    unresolved = pending_closure(state["handoff"])
    if unresolved is not None:
        appended_closure = handoff["history"][len(state["handoff"]["history"]):]
        if (ledger != state["ledger"] or len(appended_closure) != 1
                or appended_closure[0]["handoff"]["issue"] != unresolved["issue"]
                or closure_receipt(appended_closure[0]) is None):
            raise ValueError("Reconcile unresolved closure before unrelated state publication")
    if not apply:
        return {"status": "planned", "ledger": ledger, "handoff": handoff}
    # Recheck proof for newly staged rows before persisting. A stale stage
    # must not be published merely because its earlier plan was successful.
    appended = handoff["history"][len(state["handoff"]["history"]):]
    # A staged-to-Worker rework has no new archive entry. Recover the exact
    # archived PR from the verified prior state rather than trusting a caller pin.
    staged_issues = {row["issue"] for row in state["ledger"]["issues"] if row["state"] == "staged"}
    rework_prs = []
    for active in active_rows(handoff):
        if active["phase"] == "Worker" and active["issue"] in staged_issues:
            prior = next((record for record in reversed(state["handoff"]["history"])
                          if record["handoff"]["issue"] == active["issue"]), None)
            if prior is None or prior["disposition"] != "staged":
                raise ValueError("Missing latest staged handoff")
            rework_prs.append(prior["handoff"])
    def revalidate_publication():
        from tools import standard
        for previous in rework_prs:
            verify_closed_staged_pr(api, state, previous)
        for record in appended:
            active = record["handoff"]
            closure = closure_receipt(record)
            engineering = engineering_receipt(record, ledger)
            if closure is not None:
                if closure["status"] == "cancelled":
                    expected = cancel_closure_plan(api, state, active["issue"], closure["policy"],
                        closure["cancellation"]["owner_decision"], owner_approved=closure_approved,
                        recovery_execution=closure.get("execution_id"))
                else:
                    expected = closure_plan(api, state, active["issue"], closure["policy"], closure["status"],
                                            owner_approved=closure_approved,
                                            execution_id=closure.get("execution_id"))
                if expected != (ledger, handoff):
                    raise ValueError("Closure publication proof does not match reviewed intent")
            elif engineering is not None:
                expected = finish_engineering(api, state, engineering["owner_decision"],
                    policy=engineering["policy"], owner_approved=engineering_approved, issue=active["issue"])
                if expected != (ledger, handoff):
                    raise ValueError("Engineering publication proof does not match reviewed record")
            elif record["disposition"] == "staged":
                verify_candidate_runs(api, state, active, active["evidence"])
            elif record["disposition"] == "integrated":
                merged, links = standard.verify_integration(api, state, active,
                                                             get_pr(api, state, active), policy)
                if (merged != record["merged_sha"] or not set(links).issubset(active["evidence"])
                        or not record["decision"].endswith("\nPost-merge policy: " + json.dumps(
                            policy, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False))):
                    raise ValueError("Integrated publication proof does not match reviewed record")
    revalidate_publication()
    prefix, old = state["prefix"], state["ref"]
    if install.read_ref(api, prefix, install.BRANCH) != old:
        raise HandoffStale("Installed branch advanced; reload")
    commit = api.request("GET", prefix + "/git/commits/" + old)
    if commit.get("sha") != old:
        raise ValueError("Wrong installed commit")
    tree = api.request("POST", prefix + "/git/trees", {
        "base_tree": install.require(install.SHA, commit["tree"]["sha"], "installed tree"),
        "tree": [{"path": p, "type": "blob", "mode": "100644", "content": install.render(v)}
                 for p, v in ((LEDGER, ledger), (HANDOFF, handoff))],
    })["sha"]
    message = "VIB cooperative handoff"
    if operation_id is not None:
        message += "\n\nVIB-Operation: " + operation_id
    new = api.request("POST", prefix + "/git/commits", {"message": message,
        "tree": install.require(install.SHA, tree, "handoff tree"), "parents": [old]})["sha"]
    install.require(install.SHA, new, "handoff commit")
    if new == old:
        raise ValueError("Proposed handoff commit equals its parent")
    # Emit the exact recovery ticket before publication. If its sink fails,
    # do not attempt the ref update. It contains no raw intent or credential.
    if operation_id is not None and on_recovery_ticket is not None:
        on_recovery_ticket({"schema_version": 1, "repository": prefix, "issue": issue_number(issue),
                            "parent_sha": old, "candidate_sha": new, "tree_sha": tree,
                            "operation_id": operation_id})
    # A journal sink can take time. Check proof after it completes, as close
    # to the actual ref update as possible (the API is not a shared transaction).
    revalidate_publication()
    # Fast-forward-only CAS: a divergent writer cannot overwrite a competing handoff.
    ambiguous = False
    try:
        api.request("PATCH", prefix + "/git/refs/heads/" + install.BRANCH, {"sha": new, "force": False})
    except (install.ApiTransportError, install.ResponseDecodeError, json.JSONDecodeError):
        ambiguous = True
    except install.ApiError as error:
        # Rate limits and permanent errors must not trigger polling or resubmission.
        if error.retry_after is None and error.status in (409, 422):
            raise HandoffRejected(error, new, tree, operation_id) from None
        # A 5xx/408 can be returned after publication. Preserve the candidate
        # even if a Retry-After prevents immediate readback. Never repeat PATCH.
        if error.status not in (408, 500, 502, 503, 504):
            raise
        if error.retry_after is not None:
            if error.retry_after > 8:
                raise HandoffUnconfirmed(new, error.retry_after) from None
            install.time.sleep(error.retry_after)
        ambiguous = True
    try:
        observed = confirm_handoff(api, prefix, old, new, tree, operation_id=operation_id)
    except install.ApiError as error:
        raise HandoffUnconfirmed(new, error.retry_after) from None
    except (ValueError, KeyError, TypeError, OSError, AttributeError):
        # Valid JSON can still have the wrong shape (for example a list or
        # null instead of a ref/compare/commit object). Preserve the candidate
        # after publication; never treat malformed readback as a retry signal.
        raise HandoffUnconfirmed(new) from None
    result = {"status": "saved", "installed_sha": new}
    if operation_id is not None:
        result["operation_id"] = operation_id
    if observed != new or ambiguous:
        result.update(observed_sha=observed, recovered_response=ambiguous)
    return result

def issue_view(ledger, handoff, number):
    """Snapshot every issue-local record, including all archived transitions."""
    return (next((r for r in ledger["issues"] if r["issue"] == number), None),
            next((a for a in active_rows(handoff) if a["issue"] == number), None),
            [r for r in handoff["history"] if r["handoff"]["issue"] == number])


def retry_scope(api, previous, fresh, number, rejection, *, _history_cache=None):
    """Prove intervening single-parent commits did not touch this issue.

    Reading only the two endpoint snapshots would miss a change-and-revert.
    Bound ancestry work, reject rewrites/merges, and never trust an API error
    alone as evidence of contention.
    """
    if (fresh["prefix"] != previous["prefix"] or fresh["manifest"] != previous["manifest"]
            or fresh["product_sha"] != previous["product_sha"]):
        raise ValueError("Package, repository or product changed; review before retrying")
    old, cursor = previous["ref"], fresh["ref"]
    if cursor == old:
        raise rejection
    prefix = fresh["prefix"]
    path = []
    for _ in range(32):
        if cursor == old:
            break
        commit = install.response_object(api.request("GET", prefix + "/git/commits/" + cursor), "intervening commit")
        parents = install.response_rows(commit.get("parents"), "commit parents")
        if commit.get("sha") != cursor or len(parents) != 1:
            raise ValueError("Intervening history is not a verified linear handoff chain")
        parent = install.require(install.SHA, parents[0].get("sha"), "intervening parent")
        if parent == cursor:
            raise ValueError("Invalid intervening parent")
        path.append((cursor, commit, parent))
        cursor = parent
    if cursor != old:
        raise ValueError("Contention ancestry bound exceeded; inspect before retrying")
    confirmed = None
    if isinstance(rejection, HandoffRejected):
        for sha, commit, parent in path:
            if sha == rejection.candidate_sha:
                if parent != old or install.response_object(commit.get("tree"), "commit tree").get("sha") != rejection.tree_sha:
                    raise HandoffUnconfirmed(sha)
                if rejection.operation_id is not None:
                    try:
                        verify_operation_commit(commit, rejection.operation_id)
                    except ValueError:
                        raise HandoffUnconfirmed(sha) from None
                confirmed = sha
                break
    try:
        validate_retry_history(api, previous, fresh, number, path, confirmed, _history_cache=_history_cache)
    except ValueError as exc:
        if confirmed is not None:
            # The candidate exists, but the later chain has not qualified.
            # Retain its identity for read-only inspection, never replay.
            raise HandoffUnconfirmed(confirmed) from exc
        raise
    return confirmed


def validate_retry_history(api, previous, fresh, number, path, confirmed=None, *, _history_cache=None):
    """Check each adjacent transaction even when the candidate is already published."""
    prefix, old = fresh["prefix"], previous["ref"]
    expected = issue_view(previous["ledger"], previous["handoff"], number)
    history = previous["handoff"]["history"]
    prior_ledger = previous["ledger"]
    prior_handoff = previous["handoff"]
    prior_schema = prior_handoff["schema_version"]
    from tools import lifecycle
    key = (prefix, old)
    if _history_cache is not None and key in _history_cache:
        old_entries = _history_cache[key]
    else:
        _, old_entries = lifecycle.tree_entries(api, prefix, old)
    package_paths = previous["manifest"]["package_files_sha256"]
    protected = {p: old_entries.get(p) for p in package_paths}
    if any(entry is None or entry[:2] != ("blob", "100644") for entry in protected.values()):
        raise ValueError("Original package tree invalid during contention")
    prior_entries = old_entries
    for sha, commit, _ in reversed(path):
        _, entries = lifecycle.tree_entries(api, prefix, sha, commit=commit)
        if any(entries.get(p) != entry for p, entry in protected.items()):
            raise ValueError("Installed package changed during contention")
        if sha == confirmed and non_state_entries(prior_entries) != non_state_entries(entries):
            raise ValueError("Confirmed candidate changed unrelated tree entries")
        def read(file, prior_value):
            entry = entries.get(file)
            if (entry is None or entry[:2] != ("blob", "100644")
                    or not isinstance(entry[2], str) or not install.SHA.fullmatch(entry[2])):
                raise ValueError("Invalid state blob during contention")
            if entry == prior_entries.get(file):
                return prior_value
            raw = install.read_text(api, prefix, file, sha)
            if lifecycle.blob_id(raw) != entry[2]:
                raise ValueError("State blob identity mismatch during contention")
            return checkpoint.parse_json(raw)
        if read("vib-install.json", previous["manifest"]) != previous["manifest"]:
            raise ValueError("Installed manifest changed during contention")
        ledger, handoff = read(LEDGER, prior_ledger), read(HANDOFF, prior_handoff)
        validate_handoff(handoff, ledger)
        checkpoint.check_history(ledger, prior_ledger)
        current_rows = {row["issue"]: row for row in ledger["issues"]}
        for row in prior_ledger["issues"]:
            if current_rows[row["issue"]]["acceptance"] != row["acceptance"]:
                raise ValueError("Historical acceptance changed during contention")
            if row["state"] in ("integrated", "retired") and current_rows[row["issue"]] != row:
                raise ValueError("Terminal record changed during contention")
        if handoff["schema_version"] < prior_schema:
            raise ValueError("Handoff schema regressed during contention")
        if (handoff["history"][:len(history)] != history
                or (confirmed is None and issue_view(ledger, handoff, number) != expected)):
            raise ValueError("Issue or archive changed during contention; inspect before retrying")
        # Validate every adjacent transaction under its own inferred issue scope,
        # not the issue being retried. This also protects terminal archive appends.
        previous_rows = {row["issue"]: row for row in prior_ledger["issues"]}
        before_active = {row["issue"]: row for row in active_rows(prior_handoff)}
        after_active = {row["issue"]: row for row in active_rows(handoff)}
        changed = {n for n in previous_rows.keys() | current_rows.keys()
                   if previous_rows.get(n) != current_rows.get(n)}
        changed.update(n for n in before_active.keys() | after_active.keys()
                       if before_active.get(n) != after_active.get(n))
        changed.update(record["handoff"]["issue"] for record in handoff["history"][len(history):])
        if len(changed) > 1:
            raise ValueError("Multiple issue scopes changed during contention")
        if sha == confirmed and changed != {number}:
            raise ValueError("Confirmed candidate does not change exactly its issue scope")
        historical = {**previous, "ledger": prior_ledger, "handoff": prior_handoff}
        check_issue_delta(historical, ledger, handoff, next(iter(changed), None))
        history = handoff["history"]
        prior_ledger = ledger
        prior_handoff = handoff
        prior_entries = entries
        prior_schema = handoff["schema_version"]
    if prior_ledger != fresh["ledger"] or prior_handoff != fresh["handoff"]:
        raise ValueError("Reconstructed history does not match fresh endpoint")
    # Retain only the last fully qualified immutable tree in this invocation.
    # No live reference, installed bytes or failed history is cached.
    if _history_cache is not None:
        _history_cache.clear()
        _history_cache[(prefix, fresh["ref"])] = dict(prior_entries)


def planned_issue_view(ledger, handoff, number, new_issue):
    view = copy.deepcopy(issue_view(ledger, handoff, number))
    if new_issue:
        # An uncommitted allocation may change to the next available checkpoint.
        for row in view[:2]:
            if row is not None:
                row["version"] = None
    return view


def operation_identity(state, issue, intended, request=None):
    """A receipt fingerprint, not a durable pending-operation journal.

    Bind the initial immutable ref, installation/product and normalized
    transition; CLI request parameters distinguish otherwise equivalent plans.
    No raw command parameters are written into Git metadata.
    """
    value = {"domain": "vib-operation-v1", "repository": state["prefix"],
             "initial_sha": state["ref"], "manifest": state["manifest"],
             "product_sha": state["product_sha"], "issue": issue,
             "intent": intended, "request": request}
    return hashlib.sha256(install.render(value).encode("utf-8")).hexdigest()


class HandoffDeferred(ValueError):
    """Definitive, scoped conflict after bounded execution; no success claim."""
    def __init__(self, operation_id, initial_sha, observed_sha):
        self.operation_id = operation_id
        self.initial_sha = initial_sha
        self.observed_sha = observed_sha
        super().__init__("Contention retry budget exhausted; no unconfirmed write replayed"
                         f"; operation {operation_id}; initial {initial_sha}; observed {observed_sha}")


def recover_save(api, target, state, plan, issue, *, attempts=4, rounds=1, request=None,
                 on_recovery_ticket=None, on_pending_intent=None, _source_cache=None):
    """Replan only a proved unrelated, definitive conflict; never replay a PATCH."""
    if type(attempts) is not int or not 1 <= attempts <= 4:
        raise ValueError("Contention attempts must be between 1 and 4")
    if type(rounds) is not int or not 1 <= rounds <= 2:
        raise ValueError("Contention rounds must be between 1 and 2")
    issue = issue_number(issue)
    ledger, handoff = plan(state)
    check_issue_delta(state, ledger, handoff, issue)
    if handoff["schema_version"] != 2 or (ledger == state["ledger"] and handoff == state["handoff"]):
        # An idempotent inspection/claim is not a new pending mutation.
        return save(api, state, ledger, handoff, True, issue=issue)
    new_issue = issue_view(state["ledger"], state["handoff"], issue)[0] is None
    intended = planned_issue_view(ledger, handoff, issue, new_issue)
    initial_sha = state["ref"]
    operation_id = operation_identity(state, issue, intended, request)
    if on_pending_intent is not None:
        on_pending_intent({"schema_version": 1, "repository": state["prefix"],
                           "issue": issue, "initial_sha": initial_sha,
                           "operation_id": operation_id})
    budget = attempts * rounds
    source_cache = {} if _source_cache is None else _source_cache
    history_cache = {}
    for attempt in range(budget):
        try:
            result = save(api, state, ledger, handoff, True, issue=issue, operation_id=operation_id,
                          on_recovery_ticket=on_recovery_ticket)
            if attempt:
                result["contention_retries"] = attempt
            return result
        except (HandoffStale, HandoffRejected) as error:
            # GitHub 422 may also mean validation failure or spam. Require
            # observed ref movement, a linear chain and unchanged issue scope.
            # Even the final rejection must be classified against exact history.
            # Never call an unclassified 422 "contention"; an identical candidate
            # might have been published by a competing invocation.
            install.time.sleep(random.uniform(1, min(8, 2 ** (attempt + 1))))
            try:
                fresh = load(api, target, _source_cache=source_cache)
                confirmed = retry_scope(api, state, fresh, issue, error, _history_cache=history_cache)
            except install.ApiError as read_error:
                if isinstance(error, HandoffRejected) and read_error is not error:
                    raise HandoffUnconfirmed(error.candidate_sha, read_error.retry_after) from None
                raise
            except (install.MalformedResponse, AttributeError, KeyError, TypeError, OSError):
                # After an attempted ref write, malformed or interrupted
                # recovery reads must retain the exact candidate identity.
                if isinstance(error, HandoffRejected):
                    raise HandoffUnconfirmed(error.candidate_sha) from None
                raise

            if confirmed is not None:
                if not isinstance(error, HandoffRejected) or error.operation_id != operation_id:
                    raise HandoffUnconfirmed(confirmed)
                return {"status":"saved", "installed_sha":confirmed,
                        "observed_sha":fresh["ref"], "recovered_response":True,
                        "contention_retries":attempt, "operation_id":operation_id}
            if attempt + 1 == budget:
                raise HandoffDeferred(operation_id, initial_sha, fresh["ref"]) from error
            ledger, handoff = plan(fresh)
            check_issue_delta(fresh, ledger, handoff, issue)
            if (handoff["schema_version"] != 2 or
                    planned_issue_view(ledger, handoff, issue, new_issue) != intended):
                raise ValueError("Replanned issue intent changed; inspect before retrying")
            state = fresh


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--target", required=True)
    p.add_argument("--expected-sha")
    p.add_argument("--recovery-dir", help="Optional existing durable host directory for parallel publication tickets")
    sub = p.add_subparsers(dest="command", required=True)
    status = sub.add_parser("inspect")
    status.add_argument("--issue", type=int)
    status.add_argument("--recovery-plan", action="store_true", help="Read-only next step and exact evidence reuse advisory")
    recovery = sub.add_parser("inspect-operation", help="Read-only confirmation from a retained recovery ticket")
    ticket_input = recovery.add_mutually_exclusive_group(required=True)
    ticket_input.add_argument("--ticket-json")
    ticket_input.add_argument("--ticket-file")
    pending = sub.add_parser("inspect-pending", help="Read-only inventory of retained operation tickets")
    pending.add_argument("--intent-file", required=True)
    c = sub.add_parser("claim")
    c.add_argument("issue", type=int)
    c.add_argument("--acceptance", action="append", default=[])
    c.add_argument("--note", required=True)
    c.add_argument("--owner-approved", action="store_true")
    c.add_argument("--parallel", action="store_true", help="Owner-approved opt-in to parallel handoffs when claiming a new active issue")
    c.add_argument("--rework-staged", action="store_true", help="Owner-approved rework of a staged issue with a closed unmerged PR")
    c.add_argument("--resume-prior-line", action="store_true", help="Resume an eligible unresolved historical checkpoint without renumbering")
    a = sub.add_parser("advance")
    a.add_argument("--note", required=True)
    a.add_argument("--issue", type=int, help="Assert the intended active issue before advancing")
    a.add_argument("--fix")
    a.add_argument("--candidate")
    a.add_argument("--pr", type=int)
    a.add_argument("--evidence", action="append", default=[])
    a.add_argument("--rework", action="store_true")
    a.add_argument("--refresh", action="store_true", help="Keep original fix and checkpoint; archive stale evidence and revalidate current PR")
    a.add_argument("--return-to-head", action="store_true")
    f = sub.add_parser("finish")
    f.add_argument("disposition", choices=["blocked", "deferred", "staged", "integrated"])
    f.add_argument("--decision", required=True)
    f.add_argument("--issue", type=int, help="Assert the intended active issue before finishing")
    f.add_argument("--owner-approved", action="store_true")
    e = sub.add_parser("finish-engineering", help="Record engineering completion without production integration")
    e.add_argument("--issue", type=int)
    e.add_argument("--decision", required=True)
    e.add_argument("--policy", required=True, help="Owner-reviewed engineering completion policy JSON")
    e.add_argument("--owner-approved", action="store_true")
    i = sub.add_parser("reconcile")
    i.add_argument("issue", type=int)
    i.add_argument("--decision", required=True)
    i.add_argument("--owner-approved", action="store_true")
    for command in (f, i):
        command.add_argument("--policy", help="Owner-reviewed Standard post-merge policy JSON (required for integration)")
    cl = sub.add_parser("issue-closure", help="Prepare or complete one owner-reviewed issue closure")
    cl.add_argument("issue", type=int)
    cl.add_argument("--stage", choices=("prepare", "complete", "cancel"), required=True)
    cl.add_argument("--policy", required=True)
    cl.add_argument("--decision", help="Required owner cancellation decision; attest no concurrent closure execution")
    cl.add_argument("--recover-execution", help="Exact execution ID; owner must first stop and reconcile the executor")
    cl.add_argument("--owner-approved", action="store_true")
    for command in (c, a, f, i, e, cl):
        command.add_argument("--apply", action="store_true")
    args = p.parse_args()
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    api = install.GitHub(token)
    try:
        source_cache = {}
        state = load(api, args.target, args.expected_sha, _source_cache=source_cache)
        if args.command == "inspect":
            result = (recovery_plan(api, state, args.issue) if args.recovery_plan
                      else inspect(api, state, args.issue))
        elif args.command == "issue-closure":
            from pathlib import Path
            if not args.owner_approved or (args.apply and (not token or not args.expected_sha)):
                raise ValueError("Closure requires owner approval; apply also requires credential and exact lease")
            policy = checkpoint.parse_json(Path(args.policy).read_text(encoding="utf-8"))
            if args.stage != "cancel" and args.recover_execution is not None:
                raise ValueError("Execution recovery is only valid with --stage cancel")
            if args.stage == "cancel":
                ledger, handoff = cancel_closure_plan(api, state, args.issue, policy, args.decision,
                    owner_approved=True, recovery_execution=args.recover_execution)
                result = save_closure(api, state, ledger, handoff, args.issue, apply=args.apply, owner_approved=True)
            elif args.stage == "prepare":
                if args.decision is not None:
                    raise ValueError("Cancellation decision is only valid with --stage cancel")
                ledger, handoff = closure_plan(api, state, args.issue, policy, "pending", owner_approved=True)
                result = save_closure(api, state, ledger, handoff, args.issue, apply=args.apply, owner_approved=True)
            else:
                if args.decision is not None:
                    raise ValueError("Cancellation decision is only valid with --stage cancel")
                result = complete_closure(api, state, args.issue, policy, owner_approved=True, apply=args.apply)
        elif args.command == "inspect-operation":
            from pathlib import Path
            raw = (Path(args.ticket_file).read_text(encoding="utf-8")
                   if args.ticket_file is not None else args.ticket_json)
            result = inspect_operation(api, state, checkpoint.parse_json(raw))
        elif args.command == "inspect-pending":
            result = inspect_pending(api, state, args.intent_file)
        else:
            if args.apply and (not token or not args.expected_sha):
                raise ValueError("Apply requires a credential and exact expected installed SHA")
            if args.command in ("claim", "finish", "reconcile", "finish-engineering") and not args.owner_approved:
                raise ValueError("Explicit owner approval is required")
            if args.command in ("advance", "finish", "finish-engineering"):
                scope = select_active(state["handoff"], args.issue)["issue"]
            else:
                scope = args.issue
            from pathlib import Path
            policy = (checkpoint.parse_json(Path(args.policy).read_text(encoding="utf-8"))
                      if args.command in ("finish", "reconcile", "finish-engineering") and args.policy else None)
            def plan(current):
                if args.command == "claim":
                    return claim(api, current, args.issue, args.acceptance, args.note,
                        resume_prior_line=args.resume_prior_line, parallel=args.parallel,
                        rework_staged=args.rework_staged)
                if args.command == "advance":
                    return advance(api, current, args.note, fix=args.fix, candidate=args.candidate,
                        pr=args.pr, evidence=args.evidence, rework=args.rework,
                        return_to_head=args.return_to_head, refresh=args.refresh, issue=scope)
                if args.command == "finish":
                    return finish(api, current, args.disposition, args.decision, policy=policy, issue=scope)
                if args.command == "finish-engineering":
                    return finish_engineering(api, current, args.decision, policy=policy,
                                              owner_approved=args.owner_approved, issue=scope)
                return reconcile(api, current, args.issue, args.decision, policy=policy)
            # Exact owner post-merge policy pins must not be silently rewritten.
            if args.apply and policy is None and args.command != "reconcile" and not (
                    args.command == "finish" and args.disposition == "integrated"):
                # Preserve the CLI interface. A second bounded round continues
                # only the same verified intent in this execution.
                request = {k: v for k, v in vars(args).items()
                           if k not in ("target", "expected_sha", "apply", "recovery_dir")}
                def emit_ticket(ticket):
                    if args.recovery_dir is not None:
                        persist_recovery_ticket(args.recovery_dir, ticket)
                    print("VIB-RECOVERY " + json.dumps(ticket, sort_keys=True), file=sys.stderr, flush=True)
                def emit_pending(intent):
                    persist_pending_intent(args.recovery_dir, intent)
                result = recover_save(api, args.target, state, plan, scope, rounds=2, request=request,
                                      on_recovery_ticket=emit_ticket,
                                      on_pending_intent=emit_pending if args.recovery_dir is not None else None,
                                      _source_cache=source_cache)
            else:
                ledger, handoff = plan(state)
                if args.command == "finish-engineering":
                    result = save(api, state, ledger, handoff, args.apply, issue=scope,
                                  engineering_approved=args.owner_approved)
                else:
                    result = save(api, state, ledger, handoff, args.apply, issue=scope, policy=policy)
        print(install.render(result), end="")
    except (ValueError, KeyError, TypeError, OSError, install.ApiError) as exc:
        install.cli_error(p, "VIB session stopped", exc)

if __name__ == "__main__":
    main()
