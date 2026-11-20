"""Independently check the Node.js sample's recorded quote."""

import hashlib
import json
import os
import platform
import subprocess
from pathlib import Path


def main():
    data = Path(os.environ["VAULT_EXAMPLE_EVIDENCE"]).read_bytes()
    actual = json.loads(data)
    unit_cents, quantity = 125, 3
    expected = {
        "unit_cents": unit_cents, "quantity": quantity,
        "total_cents": sum(unit_cents for _ in range(quantity)),
    }
    passed = actual == expected
    case = json.loads(Path(__file__).with_name("case.json").read_text(encoding="utf-8"))
    receipt = {
        "schema_version": 1, "case_id": case["case_id"], "check_id": "python-check",
        "checkout_sha": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
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
