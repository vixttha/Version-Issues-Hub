# Test Vault v0.0.2

This release candidate packages a [copy-in starter](starter/test-vault/README.md) for GitHub repositories and keeps AlderVale's [152 case ideas](case-catalog.md) and [66-entry language and format guide](language-matrix.md) as worked examples. The [v0.0.1 draft](https://github.com/vixttha/AlderVale-Pact-of-Ten/pull/89) records the earlier AlderVale-first implementation.

## Use in AlderVale

- Start with [gameplay ideas](case-catalog.md#gameplay) or [engineering ideas](case-catalog.md#engineering).
- Use the [case and evidence form](case-and-receipt.md) to record a regression and its exact-build result.
- Run `python3 docs/test-vault/public-template/verify_adoption.py` with Python 3.12, Git, Bash, and Go to check coverage of the existing topic catalogs and rehearse installation into Python CLI, Go API, and docs-only Git fixtures.
- Keep the game matrix and manual owner playthrough receipts tied to the case IDs they actually exercise.

## Copy the starter

The [starter directory](starter/) contains root-relative files including a GitHub Actions workflow. Copy its contents into your target repository root and follow [the installation guide](starter/test-vault/README.md).

The starter works alongside the target project's existing development and delivery workflows. Add cases and runnable tests using that project's own languages, fixtures, and runner policy. See [the starter's workflow for creating tests](starter/test-vault/README.md#build-tests-for-the-target-project).

Standalone redistribution terms are pending an owner license decision. The draft remains available here for review and first-party testing.
