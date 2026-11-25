# #53 research experiment — transaction contract

Owner law: **Don't change the way an agent uses VIB. Change the way VIB handles multiple agents using it.**

Baseline 44573ae95e143116caacd891c842065a6d32743f. Research-only, not a VIB checkpoint allocation, release candidate, live installation, migration or production implementation. Preserve Head → Worker → Validate → Internal Auditor → Head.

## Experiment boundary

Test local Git compare-and-swap with synthetic integer checkpoint identifiers, immutable commits and operation identity. No remote state writes, credentials, actual agent sessions or real issue numbers. 1/2/5/10/25/50/100 simulated clients each prepare from the same snapshot; bounded worker pool; one winner and serialized recovery of losers. This proves only the synthetic invariant under the tested schedules, not remote API atomicity, concurrent retry fairness, production version allocation or agent capacity. The current install.wait_ref helper is separately exercised with a mocked newer revision to expose its fail-closed behavior. Existing product tests run unmodified. Public Ubuntu and Windows runners only. Graphify links the experiment to its source and tests; mapping is not proof of correctness.

## Next design gate

Compare REST single-parent non-force update versus GraphQL expectedHeadOid; model operation replay with matching intent and durable outcome, ownership fencing, issue-scoped evidence, and rollback without renumbering. Test bounded concurrent retries and actual remote semantics only on explicitly isolated state. No live branch upgrade or merge.

Sources: https://git-scm.com/docs/git-update-ref ; https://docs.github.com/en/rest/git/refs ; https://docs.github.com/en/graphql/reference/commits ; https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/

## Baseline Windows finding

Run 45671072469: untouched 107-test baseline passed Ubuntu but failed Windows (3 failures, 6 errors) before research tests; Graphify missing required changed_in relation fixed at bd0a550. Windows fixture GitApi.git uses subprocess text=True, which converts LF to CRLF on Windows before hashing. Research-only fix uses explicit UTF-8 bytes in fixture Git input/output; no production verification relaxed. Compare untouched baseline and corrected fixture runs; report separately. This is not a production repair or release authorization.

## Repeated contention and autonomous recovery

Real local Git CAS, synthetic multi-step records, independent retries with capped full jitter and 100 attempts per operation. Four finite workloads: 1/10/25/100 logical clients with at most 8 simultaneous workers, 3/4/3/2 operations per client respectively. Initial stale snapshot is intentional; first wave barrier is a test fixture, not production coordination. Clients retry in their own execution, with no serial recovery drain. Inject before-write failure and discarded successful responses. Verify every intended operation, stable unique allocation, exact commit count, no missing clients, duplicate replay, intent mismatch, phase conflicts, exhausted retry budget and resumed intent, last-attempt ambiguous success, permanent failure. Logs report retries and completion latency, not a remote throughput SLA. A finite pass is not starvation freedom under arbitrary scheduling; forced competing commits demonstrate bounded exhaustion. GitHub API rate limits, authentication, durable client intent persistence, real host recovery and full five-stage lifecycle remain unqualified. GitHub guidance requires honoring Retry-After/reset and pacing remote writes; local millisecond jitter is not a proposed remote timing policy.

Sources: https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/ ; https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api ; https://git-scm.com/docs/git-update-ref .

## Ordered qualification contract

Owner-approved #53 research batch, options 1–8. Head: preserve live #40 and exact source pin; Worker: contract model only. Validate: existing public Ubuntu/Windows and Graphify workflow. Internal Auditor: verify exact run logs, invariants and limitations; Head: return evidence, no integration before production qualification. Not a canonical VIB claim (current singleton precludes it).

1. Durable intent in Git before effects; separate interpreter discovers same-actor pending intents and replays receipts. 2. Finite competing arrivals; no theoretical starvation guarantee or global scheduler. 3. Cooperative generation fencing with synthetic owner authorization; shared credentials are not an access-control boundary. 4. Pure HTTP classifier honors numeric delay/reset for tested cases; live GitHub transport, malformed/header-date handling and throttle behavior remain unqualified. 5. Scope digest binds simulated receipt to issue, version, criteria, policy, candidate/base, attempt and generation; does not verify actual runs or external current PR state. 6. Validate genuine v1 state with existing production helpers, preserve historical assignments and archive, refuse active/staged migration; no actual installation upgrade or rollback. 7. Full phase model for 1–100 logical clients, deterministic phase interleaving in memory; actual local Git concurrent tests separately. 8. Production integration held until real adapter, scoped evidence verifier, lifecycle and independent host qualification. No production modifications or merge authorization. Synthetic authorization flags are fixtures, not actual owner proof. Pending intent acceptance itself requires a successful CAS; pre-publication crash remains an external caller responsibility. Recovered invalid intents need durable disposition in a later design. Sources: https://git-scm.com/docs/git-update-ref ; https://docs.github.com/en/rest/using-the-rest-api/best-practices-for-using-the-rest-api ; https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/ .

Double-check correction: persisted enqueue order (not lexicographic operation IDs), terminal domain-rejection records separated from success receipts, and conservative handling of malformed throttle headers. Infrastructure errors remain failures, not successful or rejected domain operations. Rejection in this prototype is terminal for that exact operation; it is not a general dependency scheduler. Evidence scope digests are not independent evidence; a caller can construct them, so production must compare trusted observations from GitHub and actual criterion review, never accept the model as a security boundary.
