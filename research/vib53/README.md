# #53 research experiment — transaction contract

Owner law: **Don't change the way an agent uses VIB. Change the way VIB handles multiple agents using it.**

Baseline 44573ae95e143116caacd891c842065a6d32743f. Research-only, not a VIB checkpoint allocation, release candidate, live installation, migration or production implementation. Preserve Head → Worker → Validate → Internal Auditor → Head.

## Experiment boundary

Test local Git compare-and-swap with synthetic integer checkpoint identifiers, immutable commits and operation identity. No remote state writes, credentials, actual agent sessions or real issue numbers. 1/2/5/10/25/50/100 simulated clients each prepare from the same snapshot; bounded worker pool; one winner and serialized recovery of losers. This proves only the synthetic invariant under the tested schedules, not remote API atomicity, concurrent retry fairness, production version allocation or agent capacity. The current install.wait_ref helper is separately exercised with a mocked newer revision to expose its fail-closed behavior. Existing product tests run unmodified. Public Ubuntu and Windows runners only. Graphify links the experiment to its source and tests; mapping is not proof of correctness.

## Next design gate

Compare REST single-parent non-force update versus GraphQL expectedHeadOid; model operation replay with matching intent and durable outcome, ownership fencing, issue-scoped evidence, and rollback without renumbering. Test bounded concurrent retries and actual remote semantics only on explicitly isolated state. No live branch upgrade or merge.

Sources: https://git-scm.com/docs/git-update-ref ; https://docs.github.com/en/rest/git/refs ; https://docs.github.com/en/graphql/reference/commits ; https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/
