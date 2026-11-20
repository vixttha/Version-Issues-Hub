"""Exercise the shipped starter in three clean Git working trees."""

import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from textwrap import dedent


ROOT = Path(__file__).resolve().parent
STARTER = ROOT / "starter"
VALIDATOR = Path("test-vault/validate_catalog.py")
ACTION = Path(".github/workflows/test-vault.yml")
HEADER = "| Case | Area | Priority | Suggested implementation | Expected outcome |\n"
DIVIDER = "|---|---|---|---|---|\n"
SAMPLES = ("python-cli", "go-api", "docs-only")


def run(args, cwd, *, result=0, includes=None, env=None):
    completed = subprocess.run(
        args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        check=False, timeout=75, env=env,
    )
    if completed.returncode != result or (includes and includes not in completed.stdout):
        raise RuntimeError(
            f"{args} returned {completed.returncode}, expected {result}"
            f" and {includes!r}\n{completed.stdout}"
        )
    return completed.stdout.strip()


def check_project(sample, target):
    if sample == "python-cli":
        path = target / "cli.py"
        path.write_text(
            "import argparse\n"
            "parser = argparse.ArgumentParser()\n"
            "parser.add_argument('name')\n"
            "args = parser.parse_args()\n"
            "print(f'Hello, {args.name}')\n", encoding="utf-8",
        )
        run([sys.executable, path.name, "Vault"], target, includes="Hello, Vault")
        run([sys.executable, path.name], target, result=2, includes="required")
        return "| CLI-001 | Arguments | P0 | Python | Print a greeting or reject a missing name. |\n"
    if sample == "go-api":
        (target / "go.mod").write_text("module example.test/vault-api\n\ngo 1.20\n", encoding="utf-8")
        (target / "health.go").write_text(
            'package api\nimport "net/http"\n'
            'func health(w http.ResponseWriter, r *http.Request) {\n'
            '  w.WriteHeader(http.StatusOK)\n'
            '  w.Write([]byte("ok"))\n}\n', encoding="utf-8",
        )
        (target / "health_test.go").write_text(
            'package api\nimport ("net/http/httptest"; "testing")\n'
            'func TestHealth(t *testing.T) {\n'
            '  response := httptest.NewRecorder()\n'
            '  health(response, httptest.NewRequest("GET", "/health", nil))\n'
            '  if response.Code != 200 || response.Body.String() != "ok" {\n'
            '    t.Fatal("unexpected health response")\n  }\n}\n', encoding="utf-8",
        )
        run(["go", "test", "./..."], target, env={**os.environ, "GOPROXY": "off", "GOTOOLCHAIN": "local"})
        return "| HTTP-GET-001 | Health | P0 | Go | A health request returns 200. |\n"

    (target / "index.md").write_text("# Start here\n\n[Setup](setup.md)\n", encoding="utf-8")
    (target / "setup.md").write_text("# Setup\n", encoding="utf-8")
    if not (target / "setup.md").is_file() or "[Setup](setup.md)" not in (target / "index.md").read_text(encoding="utf-8"):
        raise RuntimeError("Documentation sample does not link to its setup page")
    return r"| DOCS-001 | Navigation | P0 | Python | Page titles may contain A \| B. |" + "\n"


def copy_and_check(sample, target):
    shutil.copytree(STARTER, target)
    run(["git", "init", "-q", "-b", "trunk"], target)
    run(["git", "add", "."], target)
    run(["git", "-c", "user.name=Test Vault Fixture", "-c", "user.email=fixture@example.invalid",
         "-c", "commit.gpgsign=false", "commit", "-qm", "Install Test Vault"], target)
    action = (target / ACTION).read_text(encoding="utf-8")
    skipped, marker, script = action.partition("        run: |\n")
    if not marker or not skipped.strip():
        raise RuntimeError("Expected the catalog workflow's run block")
    workflow_step = ["bash", "-e", "-c", dedent(script)]
    summary = target / "summary.txt"
    env = {
        **os.environ, "GITHUB_STEP_SUMMARY": str(summary), "GITHUB_EVENT_NAME": "pull_request",
        "GITHUB_RUN_ID": "0", "GITHUB_RUN_ATTEMPT": "1",
        "PR_BASE_SHA": "fixture-base", "PR_HEAD_SHA": "fixture-head",
    }
    checkout = run(["git", "rev-parse", "HEAD"], target)
    run(workflow_step, target, env=env, includes="Catalog result: PASS")
    if f"Checkout: {checkout}" not in summary.read_text(encoding="utf-8"):
        raise RuntimeError("Workflow summary omitted the tested checkout")
    for name in ("README.md", "case-and-receipt.md"):
        path = target / "test-vault" / name
        for link in re.findall(r"\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            if not (link.startswith(("https://", "#")) or (path.parent / link).is_file()):
                raise RuntimeError(f"{path}: unresolved link {link}")

    command = [sys.executable, str(VALIDATOR)]
    run(command, target, includes="1 unique cases across 1 topics")
    case_path = target / "test-vault/cases.md"
    topics_path = target / "test-vault/topics.json"
    row = check_project(sample, target)
    catalog = HEADER + DIVIDER + "   " + row
    topic = row.split("|")[1].strip().rsplit("-", 1)[0]
    topics_path.write_text(f'["{topic}"]\n', encoding="utf-8")
    case_path.write_text(HEADER + row, encoding="utf-8")
    run(command, target, result=1, includes="expected a Markdown table divider")
    for fence in ("```", "~~~"):
        example = f"{fence}markdown\n{HEADER}{DIVIDER}{row}{fence}\n\n"
        case_path.write_text(example + catalog, encoding="utf-8")
        run(command, target, includes="1 unique cases across 1 topics")
    case_path.write_text(catalog, encoding="utf-8")
    run(workflow_step, target, env=env, includes="Catalog result: PASS")
    case_path.write_text(catalog + "  " + row.replace("| P0 |", "| P9 |"), encoding="utf-8")
    run(command, target, result=1, includes="invalid case row")
    run(workflow_step, target, env=env, result=1, includes="Catalog result: FAIL")
    if "Catalog result: FAIL" not in summary.read_text(encoding="utf-8"):
        raise RuntimeError("Workflow summary omitted the failed result")
    case_path.write_text(catalog + row, encoding="utf-8")
    run(command, target, result=1, includes="duplicate case")
    case_path.write_text(catalog, encoding="utf-8")
    topics_path.write_text('["OTHER"]\n', encoding="utf-8")
    run(workflow_step, target, env=env, result=1, includes=f"unknown topics: {topic}")
    print(f"PASS: {sample} checked workflow topic drift, fenced examples, dividers, invalid priorities, and duplicate IDs.")


def check_aldervale():
    from json import dumps

    topics = sorted({
        match.group(1)
        for file in ("game-catalog.md", "engineering-catalog.md")
        for line in (ROOT.parent / file).read_text(encoding="utf-8").splitlines()
        if (match := re.match(r"^\|\s*([A-Z]+[0-9]+)\s*·", line))
    })
    with TemporaryDirectory() as directory:
        topics_file = Path(directory) / "topics.json"
        topics_file.write_text(dumps(topics), encoding="utf-8")
        print(run(
            [sys.executable, str(STARTER / VALIDATOR), "--catalog", str(ROOT / "case-catalog.md"),
             "--topics", str(topics_file)],
            ROOT, includes="unique cases across",
        ))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--fixture", choices=SAMPLES)
    mode.add_argument("--aldervale-only", action="store_true")
    options = parser.parse_args()
    if options.fixture is None:
        check_aldervale()
    if options.aldervale_only:
        return
    with TemporaryDirectory() as directory:
        for sample in (options.fixture,) if options.fixture else SAMPLES:
            copy_and_check(sample, Path(directory) / sample)


if __name__ == "__main__":
    main()
