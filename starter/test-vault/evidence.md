# Verify execution receipts

Use a receipt when a test suite can record a result for a catalog case. The catalog check and the execution verdict can run alongside your existing test commands. This feature uses Python 3.12 and Git. Run from the intended repository root after committing tracked source changes. The bundled producers and verifier require their source files and the selected catalog to be tracked.

1. Keep the case ID in the existing catalog. Declare the checks that must pass before any suites run.
2. Have each suite write one JSON receipt to an empty directory for that case and run attempt. Use the actual checkout from `git rev-parse HEAD` and the run and attempt provided by CI. Keep previous attempts in separate directories.
3. If checks share an observation, pass the same file to each suite and to the verifier. Each suite records the SHA-256 of the exact bytes it read. Use synthetic observations in public examples.
4. Run `python3 test-vault/verify_receipts.py --case case.json --receipts receipts --evidence observation.json` from the project checkout. For a case without a shared observation, omit `--evidence`. GitHub Actions provides run identity automatically. Outside Actions, supply `--run-id` and `--attempt` consistently across all checks.

## Case manifest v2

```json
{"schema_version":2,"case_id":"CLI-001","required_checks":["node-test","python-check"],"shared_evidence":true}
```

## Suite receipt v2

```json
{
  "schema_version": 2,
  "case_id": "CLI-001",
  "check_id": "node-test",
  "checkout_sha": "<actual full 40-character Git SHA>",
  "run_id": "11223344",
  "attempt": "1",
  "environment": {"os": "Linux", "runtime": "Node.js 24"},
  "status": "pass",
  "case_plan_sha256": "<64-character lowercase SHA-256 of the exact case manifest bytes>",
  "evidence_sha256": "<64-character lowercase SHA-256 of the observation file>"
}
```

All fields in the examples are required. Use `null` for `evidence_sha256` when `shared_evidence` is false. Outcomes are `pass`, `fail`, `skip`, or `blocked`. The verifier reads the JSON files in the receipt directory. A missing, duplicate, undeclared, invalid, stale, or nonpassing receipt fails the case. Unknown JSON fields and duplicate JSON keys fail validation. The one combined table is also appended to the GitHub Actions job summary when available.

Each v2 suite hashes the exact manifest bytes it used. Write the plan before running any checks and reuse it unchanged for verification. Changing any manifest bytes, including the required check set, requires new v2 receipts. Observation digests remain separate from plan digests.

Existing v1 manifests and matching v1 receipts remain supported. They omit `case_plan_sha256`. The verdict labels their plan binding as unavailable. Each manifest requires receipts of its own version.

The verifier checks integrity against the inputs and checkout supplied by the workflow. Trust in the reported outcome depends on the suites and runners that produced the receipts. Catalog validity, suite execution, and owner or production acceptance are recorded separately.

See the [Node.js and Python example](examples/shared-evidence/README.md) and the [release follow-ons](UPGRADE.md#future-release-checks).
