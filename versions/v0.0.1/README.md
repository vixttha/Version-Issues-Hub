# Public Test Vault template

Use this template to build a public, reviewable record of what your game tests cover. Start with the change or reported bug, attach a stable case ID, run the smallest suite that exercises the affected behavior, then link the exact revision and runner result.

## Start here

- [Test ideas](case-catalog.md) lists gameplay and engineering cases, with proposed languages and expected outcomes.
- [Language and tool guide](language-matrix.md) shows where another runtime provides independent evidence.
- [Case and evidence template](case-and-receipt.md) gives fields for a regression case, a CI receipt, and manual acceptance.
- [Catalog validator](validate_catalog.py) uses Python’s standard library to check case IDs and catalog coverage.

Copy this folder into your repository, replace the example case catalog with your own, and run `python3 docs/test-vault/public-template/validate_catalog.py` from your checkout. AlderVale’s workflow also checks this template against its [gameplay](../game-catalog.md) and [engineering](../engineering-catalog.md) topic catalogs. When adapting its [GitHub Actions workflow](../../../.github/workflows/test-vault-template.yml), update the path filters and point the validator to your topic catalogs, or omit the optional source catalogs.

## How AlderVale uses public GitHub runners

| Check | Where it runs | Evidence to keep |
|---|---|---|
| Game logic, data contracts, production build, and server checks | Existing Linux, Windows, and macOS core jobs | Actual checkout SHA, job URL, relevant case IDs, and skips |
| Guest enrollment, duel, offline HUD, and save/reload | Existing Chromium, Firefox, and WebKit jobs | Scenario result per browser and per attempt |
| Firestore rules and persistence | Existing Java-backed demo emulator | Emulator version, synthetic fixtures, and asserted rules or transaction outcomes |
| Template consistency | Public Ubuntu template job on relevant pull requests | Case and topic counts, checked-out SHA, and job URL |
| Owner desktop playthrough and real-device behavior | Documented owner-run build | Build SHA, environment, steps, and observed results |

Use standard GitHub-hosted runners with minimum token permissions, finite job timeouts, and synthetic data. Keep API and storage use within the project’s approved budget. Keep private planning, real account data, secrets, and production service state out of public evidence.

## Closing a regression

1. Link the existing GitHub issue and identify the expected behavior.
2. Add or link a test at the layer where the failure is visible. If the bug crosses a real save, browser, or service boundary, add the corresponding integration check when it provides coverage a unit test cannot provide.
3. Record the known-bad result when it is safe and reproducible, the fixed result, and any nearby behavior also tested.
4. Check the exact PR merge checkout, including its base and head. Keep failed attempts and skips visible. A rerun passing is a separate observation.
5. Record owner playtesting separately. Use the linked merged fix, exact-CI receipt, and regression result when closing a bug.

A passing suite establishes that the listed assertions passed on the recorded build, fixtures, and environments. Use “verified for these cases” in a handoff. Unknown defects, untested environments, and human acceptance stay open in the evidence record.
