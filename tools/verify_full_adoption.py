"""Rehearse the documented complete Vault install in a disposable project."""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from verify_adoption import ROOT, STARTER, run


def commit(project, message):
    run(["git", "add", "."], project)
    run(["git", "-c", "user.name=Test Vault Fixture", "-c", "user.email=fixture@example.invalid",
         "-c", "commit.gpgsign=false", "commit", "-qm", message], project)
    return run(["git", "rev-parse", "HEAD"], project)


def verify(output, work):
    project = work / "project"
    shutil.copytree(STARTER, project, ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "languages/python", project / "languages/python",
                    ignore=shutil.ignore_patterns("__pycache__"))
    (project / "tools").mkdir()
    for name in ("inventory.py", "native_outcomes.py"):
        shutil.copy2(ROOT / "tools" / name, project / "tools" / name)
    (project / "README.md").write_text("# Synthetic consumer project\n", encoding="utf-8")
    run(["git", "init", "-qb", "trunk"], project)
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    inventory = [sys.executable, "tools/inventory.py"]
    report_dir = output.resolve()
    run([*inventory, "--run", "missing-language"], project, result=1,
        includes="Unknown language folder", env=env)
    run(inventory, project, includes="1 declared cases in 1 language folders", env=env)
    commit(project, "Install the complete Vault")

    language = project / "languages/python"
    test = language / "tests/test_contract.py"
    native = test.read_text(encoding="utf-8")
    app = language / "app.py"
    app.write_text("def debit(balance, amount):\n    return balance if amount < 0 or amount > balance else balance - amount\n",
                   encoding="utf-8")
    start, end = native.index("def debit("), native.index("class DebitContract")
    test.write_text(native[:start] + "from app import debit\n\n\n" + native[end:], encoding="utf-8")

    def check(name, sha, expected, exit_code):
        path = report_dir / f"adoption-{name}.json"
        run([*inventory, "--run", "python", "--evidence", str(path)], project, result=exit_code, env=env)
        report = json.loads(path.read_text(encoding="utf-8"))
        outcomes = {case["case_id"]: case["outcome"] for case in report["cases"]}
        if report["checkout_sha"] != sha or outcomes != expected:
            raise AssertionError(f"{name}: wrong source or case outcomes {report}")
        if any(not case["observed_runtime"] for case in report["cases"]):
            raise AssertionError(f"{name}: runtime reporting is missing")

    check("pass", commit(project, "Exercise the consumer implementation"), {"PYTHON-001": "PASS"}, 0)

    original_app = app.read_text(encoding="utf-8")
    run(inventory, project, includes="1 declared cases", env=env)
    if run(["git", "status", "--porcelain"], project):
        raise AssertionError("Verification left generated files in the consumer checkout")
    app.write_text("def debit(balance, amount):\n    return balance - amount\n", encoding="utf-8")
    metadata = language / "metadata.json"
    manifest = json.loads(metadata.read_text(encoding="utf-8"))
    fixture = manifest["cases"][0]["test"]
    independent = language / "tests/independent.py"
    independent.write_text("assert 6 * 7 == 42\n", encoding="utf-8")
    missing_python = work / "unavailable-runtime" / "python"
    manifest["cases"].extend([
        {"id": "PYTHON-002", "purpose": "Report a missing executable", "test": fixture,
         "support": [], "commands": [[str(missing_python), fixture]]},
        {"id": "PYTHON-003", "purpose": "Continue after an independent case fails", "test": "tests/independent.py",
         "support": [], "commands": [["python", "tests/independent.py"]]},
    ])
    metadata.write_text(json.dumps(manifest), encoding="utf-8")
    check("fail", commit(project, "Exercise a controlled regression and missing prerequisite"),
          {"PYTHON-001": "FAIL", "PYTHON-002": "BLOCKED", "PYTHON-003": "PASS"}, 1)

    independent.unlink()
    manifest["cases"] = manifest["cases"][:1]
    metadata.write_text(json.dumps(manifest), encoding="utf-8")
    app.write_text(original_app, encoding="utf-8")
    test.write_text(
        test.read_text(encoding="utf-8").replace(
            "    def test_rejected", '    @unittest.skip("synthetic skipped case")\n    def test_rejected',
        ),
        encoding="utf-8",
    )
    check("skip", commit(project, "Exercise a native all-skipped suite"), {"PYTHON-001": "SKIP"}, 1)

    test.write_text("import unittest\n", encoding="utf-8")
    check("empty", commit(project, "Exercise zero native tests"), {"PYTHON-001": "FAIL"}, 1)
    print("Complete install verified across passing, failing, blocked, all-skipped, and zero-test outcomes.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-dir", required=True, type=Path)
    args = parser.parse_args()
    with TemporaryDirectory() as directory:
        verify(args.evidence_dir, Path(directory))
