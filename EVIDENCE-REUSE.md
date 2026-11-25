# Evidence reuse — approved principle

**Reuse verified evidence. Preserve its origin. Confirm its applicability. Revalidate affected or uncertain scope. Keep acceptance issue-specific and owner-controlled.**

The earlier wording "refresh only what changed" was too narrow: transitive dependencies and integration state may affect unchanged files. "Never inherit approval blindly" was too permissive: evidence is reusable, approval does not transfer to another scope.

## Safe reuse rules
- Reuse a qualifying execution for the same exact revision and applicable criterion after independent review; one execution may support several issues without duplicating work.
- Preserve original repository, issue/version where applicable, tested SHA, original fix, candidate, base, proposed or actual merge, workflow, run, attempt, job, test commands, outcome and environment. Never relabel historical execution as a new run.
- An unrelated installed-ledger update can require a refreshed current owner policy pin without requiring another identical execution, if all actual evidence remains eligible.
- Changed candidate/base/merge, uncertain checkout, changed relevant test/dependency/environment, or superseded attempt require scope-appropriate fresh verification. Actual merged-revision checks remain distinct.
- Failed, missing, skipped, tampered, contradictory or unverifiable evidence cannot prove acceptance. Retain historical failures; distinguish stale, rejected and unverified. A green status alone is not proof of test semantics.
- Reuse test definitions and defect history against newer candidates, not the old verdict as proof of the new code. Independent host trials cannot be replaced by existing CI.
- Record independent applicability and owner decision; no cross-issue authority transfer.

## Research boundaries
Exact-revision reuse and issue-local policy refresh are the immediate direction. Cross-revision fingerprints, selective regression testing and automatic test skipping remain deferred research, not required components. Graphify supports navigation and impact analysis, not completeness proof or authority to skip tests. If future work is authorized, shadow-run full suites and compare conservative predictions; qualify identity, freshness, dependencies, integrity and concurrency negatives on public Ubuntu and Windows. No unmeasured savings or universal zero-false-green guarantee.

Source: [owner-approved decision](https://github.com/vixttha/Version-Issues-Hub/issues/9#issuecomment-7172184112); [parallel candidate workflow](https://github.com/vixttha/Version-Issues-Hub/blob/2ca71c5f29c93550db57bae534ad51b1fd8d63a7/install/branch/WORKFLOW.md).
