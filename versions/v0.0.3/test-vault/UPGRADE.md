# Upgrade from v0.0.2

Review file conflicts before copying from the v0.0.3 starter. To opt in while keeping your current catalog and workflow, copy `test-vault/verify_receipts.py` and `test-vault/evidence.md`. Copy `test-vault/examples/` if you want the example, and copy this guide alongside the evidence documentation. The verifier reuses your existing v0.0.2 catalog validator. Keep using the same catalog table, optional topics registry, and project test commands.

Pick one registered case, define its required checks, and run the new verdict after the suites. Review the test receipt for the actual checkout and attempt. A failed or missing required check should fail the combined verdict even when the catalog passes.

## Future release checks

For projects with shipped builds, tie release receipts to the tested tag, full checkout, and digest of the actual artifact. Preserve synthetic fixtures from supported older data formats and validate their migration with the new build. Use a separately identified smoke test against the intended deployed version when checking a deployment. Record the target, version, result, and limitations with that check.
