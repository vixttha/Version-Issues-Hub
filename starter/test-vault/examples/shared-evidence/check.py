"""Independently check the Node.js sample's recorded quote."""

import hashlib
import json
import os
import platform
import subprocess
import sys
from pathlib import Path


def unique_fields(pairs):
    fields = {}
    for key, value in pairs:
        if key in fields:
            raise ValueError(f"duplicate JSON key: {key}")
        fields[key] = value
    return fields


def main():
    data = Path(os.environ["VAULT_EXAMPLE_EVIDENCE"]).read_bytes()
    unit_cents, quantity = 125, 3
    expected = {
        "unit_cents": unit_cents, "quantity": quantity,
        "total_cents": sum(unit_cents for _ in range(quantity)),
    }
    try:
        passed = json.loads(data, object_pairs_hook=unique_fields) == expected
    except ValueError as error:
        print(f"Invalid shared evidence: {error}", file=sys.stderr)
        passed = False
    script = Path(__file__).resolve()
    manifest = script.with_name("case.json")
    plan = manifest.read_bytes()
    case = json.loads(plan)
    checkout = subprocess.check_output(
        [sys.executable, script.parents[2] / "source_commit.py", script, manifest], text=True,
    ).strip()
    receipt = {
        "schema_version": 2, "case_id": case["case_id"], "check_id": "python-check",
        "case_plan_sha256": hashlib.sha256(plan).hexdigest(),
        "checkout_sha": checkout,
        "run_id": os.environ["GITHUB_RUN_ID"], "attempt": os.environ["GITHUB_RUN_ATTEMPT"],
        "environment": {"os": platform.system(), "runtime": platform.python_version()},
        "status": "pass" if passed else "fail",
        "evidence_sha256": hashlib.sha256(data).hexdigest(),
    }
    output = Path(os.environ["VAULT_EXAMPLE_RECEIPTS"]) / "python.json"
    output.write_text(json.dumps(receipt) + "\n", encoding="utf-8")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
