# Agent 4 — Lydite Test Vault

Owner direction: Agent 4 owns the VIB testing workspace, not product implementation. This is an assignment record, not proof of a running separate agent.

## Scope and isolation
- Write only on `Lydite-Test-Vault` and separately authorized vault topic branches. Never change product main, release PRs, the live VIB installation, other agents' refs, active claims, checkpoints or review threads.
- Read pinned public VIB source into a separate checkout with no persisted credentials. Use synthetic/disposable fixtures; no live mutations or private data in public logs.
- Standard GitHub-hosted public Ubuntu and Windows runners only; no paid runners or external service requirement. CodeRabbit, CircleCI, Sentry and Plugin Eval are optional evidence sources, not prerequisites.
- Keep the owner-controlled Head → Worker → Validate → Internal Auditor → Head workflow. Report findings with exact reproduction, expected and observed behavior, source and vault SHAs, run/attempt, receipts and logs. File confirmed nonduplicate defects only with clear scope; do not claim or repair product issues without owner scope.
- Preserve independent versioning, existing stable install and receipts. No automatic integration, upgrade, release or additional language runtime in the product.

## Baselines (2026-11-25)
- Published Lydite [v0.0.4](https://github.com/vixttha/Lydite-Test-Vault-Template/releases/tag/v0.0.4), SHA `87d25d80d3154d295052412b64b29a0f0f152c27`; embedded starter separately versioned v0.0.3.
- Latest upstream main `eae4c9d9d56ed132b400d7c0f56a9babfe5cba07`. The existing copied source files match this tree except for host-specific README/workflow and two upstream-only workflows intentionally omitted. Preserve MIT license and historical maps.
- Latest development checkpoint v0.0.4.75, [draft PR #40](https://github.com/vixttha/Lydite-Test-Vault-Template/pull/40), SHA `a19c58a5b005bfab3e60b0b16aae13bf01023118`; owner withheld v0.0.5 merge readiness. Record only; do not install draft as approved.
- VIB product snapshot [`7ae6626e44d01d29b11968da28e6debd816f8c06`](https://github.com/vixttha/Version-Issues-Hub/tree/7ae6626e44d01d29b11968da28e6debd816f8c06) from PR #2 at observation. It is a candidate, not a released version. Existing seven case identities retained; three new suite bindings recorded.
- Previous vault [`610f4f52ded26ee8c3a8d958bd01358efa2f472a`](https://github.com/vixttha/Version-Issues-Hub/tree/610f4f52ded26ee8c3a8d958bd01358efa2f472a) and its public [project run](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45375914604), [template/Graphify run](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45375914266) remain historical evidence, not proof of this revision.

## Work sequence
1. Inventory current product coverage and run all ten pinned Python suites using the existing Lydite per-suite receipt runner.
2. Review the language-role matrix with the owner. Proposed roles are not approved; no selection or new language implementation now.
3. After owner selection, develop one scoped negative/positive case at a time with reproducible evidence. Prioritize actual VIB defects rather than duplicate tests written in every language.
4. Future contention research (#53) remains separate; offline model and simulated clients must not be described as actual independent agent trials (#37).

## Evidence boundary
Lydite records mechanical outcomes only. Existing template language examples are not VIB integration tests. Graphify archive checks are not agent acceptance. Standard VIB remains advisory, and merge/release authority remains with the owner. Current status is setup, pending exact new-run evidence and owner language decisions.
