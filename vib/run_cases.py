"""Run project suites in a separate pinned checkout; use Lydite v2 receipt verdicts."""
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "starter/test-vault"))
from source_commit import source_commit
from validate_catalog import read_cases
from verify_receipts import verdict, render

plan_file = root / "vib/plan.json"
catalog = root / "vib/cases.md"
vault_sha = source_commit(root, (plan_file, catalog, Path(__file__)))
plan = json.loads(plan_file.read_bytes())
product = Path(os.environ["VIB_CHECKOUT"]).resolve()
product_sha = source_commit(product)
assert product_sha == plan["product_sha"], "Product checkout mismatch"
assert set(read_cases(catalog)[0]) == {x["case_id"] for x in plan["cases"]}
assert {x["suite"] for x in plan["cases"]} == {p.name for p in (product / "tests").glob("test_*.py")}
output = Path(os.environ["RUNNER_TEMP"]) / "vib-vault"
output.mkdir()
report = {"vault_sha": vault_sha, "product_sha": product_sha, "run_id": os.environ["GITHUB_RUN_ID"], "attempt": os.environ["GITHUB_RUN_ATTEMPT"], "cases": []}
all_pass = True
for item in plan["cases"]:
    case = item["plan"]
    directory = output / item["case_id"]
    directory.mkdir()
    plan_bytes = (json.dumps(case, indent=2) + "\n").encode()
    (directory / "plan.json").write_bytes(plan_bytes)
    receipts = directory / "receipts"
    receipts.mkdir()
    command = [sys.executable, "-B", "-m", "unittest", "discover", "-s", "tests", "-p", item["suite"], "-v"]
    result = subprocess.run(command, cwd=product, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    (directory / "unittest.log").write_text(result.stdout, encoding="utf-8")
    print(result.stdout, flush=True)
    count = re.search(r"Ran (\d+) tests? in ", result.stdout)
    passed = result.returncode == 0 and bool(count and int(count.group(1)) > 0) and not re.search(r"\bskipped=\d+|\bexpected failures=\d+", result.stdout)
    expected = {"schema_version":2, "case_id":case["case_id"], "checkout_sha":product_sha, "run_id":report["run_id"], "attempt":report["attempt"], "case_plan_sha256":hashlib.sha256(plan_bytes).hexdigest(), "evidence_sha256":None}
    receipt = {**expected, "check_id":"python-unittest", "environment":{"os":platform.system(),"runtime":platform.python_version()}, "status":"pass" if passed else "fail"}
    (receipts / "python-unittest.json").write_text(json.dumps(receipt, indent=2)+"\n", encoding="utf-8")
    rows, issues = verdict(receipts, case["required_checks"], expected)
    ok, summary = render(case["case_id"], expected, rows, issues)
    print(summary)
    (directory / "verdict.md").write_text(summary, encoding="utf-8")
    report["cases"].append({"id":case["case_id"],"command":command[1:],"tests":int(count.group(1)) if count else 0,"outcome":"pass" if ok else "fail"})
    all_pass = all_pass and ok
assert source_commit(product) == product_sha, "Product checkout drift"
(output / "report.json").write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
print(json.dumps(report, indent=2))
raise SystemExit(0 if all_pass else 1)
