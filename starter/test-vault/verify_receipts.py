"""Verify one case's versioned execution receipts and write its combined verdict."""

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

from source_commit import source_commit
from validate_catalog import read_cases


CHECK_ID = re.compile(r"[a-z][a-z0-9-]{0,63}")
SHA = re.compile(r"[0-9a-f]{40}")
RUN_ID = re.compile(r"[1-9][0-9]*")
STATUSES = {"pass", "fail", "skip", "blocked"}
DEFAULT_CATALOG = Path(__file__).with_name("cases.md")


def unique_object(items):
    result = {}
    for key, value in items:
        if key in result:
            raise ValueError("duplicate JSON field")
        result[key] = value
    return result


def read_object(path, raw=None):
    data = json.loads(path.read_bytes() if raw is None else raw, object_pairs_hook=unique_object)
    if not isinstance(data, dict):
        raise ValueError("expected a JSON object")
    return data


def expect_fields(data, fields, versions):
    if data.keys() != set(fields):
        raise ValueError("missing or unknown fields")
    if type(data["schema_version"]) is not int or data["schema_version"] not in versions:
        raise ValueError("unsupported schema version")


def read_case(path, catalog):
    raw = path.read_bytes()
    case = read_object(path, raw)
    expect_fields(case, ("schema_version", "case_id", "required_checks", "shared_evidence"), {1, 2})
    case_id, checks = case["case_id"], case["required_checks"]
    if not isinstance(case_id, str) or case_id not in read_cases(catalog)[0]:
        raise ValueError("case ID must be registered in the selected catalog")
    if (not isinstance(checks, list) or not checks
            or any(not isinstance(check, str) or not CHECK_ID.fullmatch(check) for check in checks)
            or len(set(checks)) != len(checks)):
        raise ValueError("required checks must be a nonempty list of unique check IDs")
    if type(case["shared_evidence"]) is not bool:
        raise ValueError("shared_evidence must be a boolean")
    return case, hashlib.sha256(raw).hexdigest()


def verify_receipt(receipt, expected):
    expect_fields(receipt, (*expected, "check_id", "environment", "status"), {expected["schema_version"]})
    for field, value in expected.items():
        if receipt[field] != value:
            raise ValueError(f"{field} does not match this verification")
    environment = receipt["environment"]
    if (not isinstance(environment, dict) or environment.keys() != {"os", "runtime"}
            or any(not isinstance(value, str) or not value.strip() for value in environment.values())):
        raise ValueError("environment must contain nonempty os and runtime strings")
    status = receipt["status"]
    if not isinstance(status, str) or status not in STATUSES:
        raise ValueError("unrecognized outcome")
    return status


def verdict(directory, checks, expected):
    results = {check: [] for check in checks}
    issues = []
    if directory.is_symlink() or not directory.is_dir():
        issues.append("Receipt directory is missing or invalid.")
    else:
        entries = sorted(directory.glob("*.json"))
        for path in entries:
            if path.is_symlink() or not path.is_file():
                issues.append("Found an unreadable or invalid receipt.")
                continue
            try:
                receipt = read_object(path)
            except (OSError, ValueError, RecursionError):
                issues.append("Found an unreadable or invalid receipt.")
                continue
            check = receipt.get("check_id")
            if not isinstance(check, str) or check not in results:
                issues.append("Found an undeclared check receipt.")
                continue
            try:
                outcome = verify_receipt(receipt, expected)
                results[check].append((outcome.upper(), "Valid receipt"))
            except ValueError as error:
                results[check].append(("INVALID", str(error)))

    rows = []
    for check, receipts in results.items():
        if len(receipts) == 1:
            status, detail = receipts[0]
        elif receipts:
            status, detail = "DUPLICATE", "More than one receipt for this check"
        else:
            status, detail = "MISSING", "No receipt for this check"
        rows.append((check, status, detail))
    return rows, list(dict.fromkeys(issues))


def render(case_id, expected, rows, issues):
    passed = not issues and all(status == "PASS" for _, status, _ in rows)
    lines = [
        f"### Test Vault execution evidence · {case_id}",
        "",
        f"Checkout: {expected['checkout_sha']} · Run: {expected['run_id']} · Attempt: {expected['attempt']}",
        *([f"Case plan SHA-256: {expected['case_plan_sha256']}"] if "case_plan_sha256" in expected
          else ["Legacy receipt v1 · case plan binding unavailable"]),
        "",
        "| Required check | Result | Evidence |",
        "|---|---|---|",
        *(f"| {check} | {status} | {detail} |" for check, status, detail in rows),
        "",
        *(f"- {issue}" for issue in issues),
        "",
        f"**Overall: {'PASS' if passed else 'FAIL'}**",
        "",
    ]
    return passed, "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True, help="Case manifest JSON")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--receipts", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, help="Shared observation file, if required by the case")
    parser.add_argument("--run-id", default=os.environ.get("GITHUB_RUN_ID"))
    parser.add_argument("--attempt", default=os.environ.get("GITHUB_RUN_ATTEMPT"))
    args = parser.parse_args()

    try:
        case, plan_sha = read_case(args.case, args.catalog)
        if not RUN_ID.fullmatch(args.run_id or "") or not RUN_ID.fullmatch(args.attempt or ""):
            raise ValueError("run ID and attempt must be positive decimal strings")
        checkout = source_commit(Path.cwd(), (Path(__file__), args.catalog))
        if not SHA.fullmatch(checkout):
            raise ValueError("checkout must be a full Git SHA")
        if case["shared_evidence"] != (args.evidence is not None):
            raise ValueError("evidence argument must match the case's shared_evidence setting")
        expected = {
            "schema_version": case["schema_version"],
            "case_id": case["case_id"], "checkout_sha": checkout, "run_id": args.run_id,
            "attempt": args.attempt, "evidence_sha256": None,
        }
        if case["schema_version"] == 2:
            expected["case_plan_sha256"] = plan_sha
        if args.evidence is not None:
            with args.evidence.open("rb") as stream:
                expected["evidence_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
        rows, issues = verdict(args.receipts, case["required_checks"], expected)
        passed, summary = render(case["case_id"], expected, rows, issues)
    except (OSError, ValueError, RecursionError, subprocess.CalledProcessError) as error:
        print(f"Test Vault execution evidence failed: {error}")
        passed = False
        summary = "### Test Vault execution evidence\n\n**Overall: FAIL**\n\nCould not verify the case inputs.\n"

    print(summary)
    if summary_path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(summary_path).open("a", encoding="utf-8") as output:
            output.write(summary + "\n")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
