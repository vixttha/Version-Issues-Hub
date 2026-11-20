# One shared observation in Node.js and Python

The Node.js test invokes a CLI that quotes three units at 125 cents and saves its JSON output. The CLI requires two unsigned decimal integers and a total within the safe integer range. The Python check derives the expected total independently. Both readers reject repeated JSON object keys and hash the original observed bytes. Both suites write their own v2 receipt for the same observation and exact case plan.

From an existing Git checkout with the starter installed, add `CLI-001` to its catalog. Register the `CLI` topic too if your catalog uses a topic registry. Commit these changes and the installed files before running the receipt example. Run from the checkout root using Node.js 24 and Python 3.12. For a local example, set positive sample run and attempt IDs before running the following steps, or use the IDs provided by GitHub Actions.

```bash
export GITHUB_RUN_ID=${GITHUB_RUN_ID:-1}
export GITHUB_RUN_ATTEMPT=${GITHUB_RUN_ATTEMPT:-1}
export VAULT_EXAMPLE_RECEIPTS="$(mktemp -d)"
export VAULT_EXAMPLE_EVIDENCE="$(mktemp)"
example=test-vault/examples/shared-evidence
node --test "$example/app.test.mjs"
python3 "$example/check.py"
python3 test-vault/verify_receipts.py --case "$example/case.json" \
  --receipts "$VAULT_EXAMPLE_RECEIPTS" --evidence "$VAULT_EXAMPLE_EVIDENCE"
```

In CI, run the verifier even if a suite fails, so the summary shows the missing or failing check. The repository's upgrade rehearsal runs this scenario on a v0.0.2 installation. See the [receipt contract](../../evidence.md).
