# #53 implementation candidate — transaction foundation

Owner law: **Don't change the way an agent uses VIB. Change the way VIB handles multiple agents using it.**

Based on 7ae6626e44d01d29b11968da28e6debd816f8c06, separate from active release. Existing session CLI and singleton contract retained. Real production transport now recognizes later descendant commits and ambiguous PATCH outcomes, without repeating writes; throttle timing retained safely. No release checkpoint allocated. Windows fixture preserves exact input bytes as qualified in research. Tests use real production functions with mocked GitHub outcomes; live remote contention, durable prepublication intent, multi-active handoffs, ownership, evidence scope, actual migration, independent host trials remain outstanding. No production installation or release authorized.

## PR integration safety — qualification before runtime change

[Issue #53 scope addition](https://github.com/vixttha/Version-Issues-Hub/issues/53#issuecomment-7170943599). Recommend A+B: extend existing finish/reconcile, receipt and scope checks; no parallel merge service. A merge observation is not accepted integration; require actual commit identity, membership in target history, exact-SHA successful trusted run/attempt/checkout and criteria review, then owner closure. Preserve stable original fix and historical receipts. Compare base/head/proposed merge before approval, retain issue-local evidence and invalidate stale integration evidence. For initial parallel qualification, ordinary merge commits only; squash/rebase safely held, not globally disabled. GitHub expected-head merge guard does not pin base; even a successful precheck cannot prevent an external writer, and Standard is advisory. Optional GitHub merge queue and conditional product-ref research separate; no direct product writes. Batched issue scope and PR ownership remain required. No automatic closing/reopening, force-push, merge, or release.

Five real disposable Git tests characterize ancestry, equal tree/different SHA, squash/rebase, clean semantic conflict, textual conflict and conditional local ref rejection. These are Git behavior tests, not a repair of finish/reconcile or proof of actual remote API CAS. Existing session tests still accept merged metadata without post-merge verification. Production negative-path tests must reject missing/failed/skipped/cancelled/wrong-repo/wrong-SHA/wrong-attempt evidence, stale head/base, early closure, duplicate ownership, and incomplete batch scope. Preserve legacy mappings and single-agent CLI; no migration or new checkpoint now. No runtime change in this slice. See https://docs.github.com/en/rest/pulls/pulls and https://git-scm.com/docs/git-update-ref .

## Post-merge acceptance repair

Existing `finish` and `reconcile` now require the existing Standard policy shape scoped to one issue for new integrated dispositions. Verify live public repo, actual ordinary merge parents, target membership, fix ancestry, exact product-branch push/dispatch run/attempt, workflow, job and required steps. Preserve prior evidence and append post-merge URLs plus canonical policy in the existing owner decision field. No new schema or runtime dependency. Owner-reviewed checkout and criterion judgment remain mandatory; metadata alone cannot establish actual test semantics. Unsupported history/events stop safely. No claim of atomic external merge prevention or global parallel state. Tests exercise both real session entry points with simulated API responses.

CodeRabbit follow-up: parse independent throttle bounds even if Retry-After is malformed; normalize truncated response bodies into a redacted transport failure without repeating writes. The existing handoff confirmation path retains candidate identity. Three targeted tests exercise these cases.

## Stale integration evidence recovery

Extend existing session handoffs with optional paired base and proposed-merge pins. Compare live target ref, PR head/base, test merge parents and exact run attempt on normal transitions and staging. Read-only inspect detects stale active/staged evidence. Refresh preserves original fix ancestry and checkpoint and archives prior proof; staged reclaim preserves history and resumes Validate. Standard policies reject stale/unpinned staged records. No global parallel assignments, scheduler or external merge enforcement; checks occur on use, not continuously. New tests exercise existing production paths with simulated GitHub responses.

Refresh refuses archived run IDs from earlier candidate pins even if the run is rerun or its PR association changes. Staging is checked again before object creation and immediately before the installed ref update. A disposable real Git test exercises the production session against two independent feature branches, simulated API reads and actual merge parents; no real target writes. Separate GitHub refs remain non-atomic; subsequent use rechecks freshness.

CodeRabbit review confirmed the multi-mapping attempt race. Re-read earlier pre-merge runs and all mapped post-merge attempts after the complete evidence check, retaining identity validation. Added regressions for a rerun during a later run in both integration paths and in session evidence submission. Staged prior-release-line work retains its existing owner reconciliation restriction. These checks narrow the external race window; no atomic GitHub-wide snapshot is asserted.

## Issue-scoped evidence isolation

Add a single-issue delta guard at the existing session save boundary, including dry-run output. All unrelated ledger rows and their relative order, active handoffs and historical records must remain equal; new history must belong to the intended issue, existing criteria remain immutable and integrated/retired rows cannot change. Existing command shapes are retained; optional explicit issue assertions for advance/finish and explicit scope from CLI to save. Staged reconciliation can complete without clearing another active issue. Reuse of qualifying shared PR evidence remains possible, and another issue's stale-run archive is not a global blacklist. No new schema or dependency. Simulated GitHub tests cover transitions, tampered plans, wrong owner scope, serialized tree bytes and stale ref rejection. Standard advisory still requires current installed policy pin and complete staged PR scope; this is not general multi-active qualification.

Additional tests prove distinct-PR refresh makes no reads of the other PR or its run; an integrated row cannot be reopened through save; legacy save inference handles an unchanged unrelated active slot; explicit CLI issue assertions refuse mismatches before transition; Standard owner-policy repinning after unrelated ledger state changes reuses unchanged qualifying run evidence. Installed revision pin remains mandatory, including when no tests need rerunning.

## Review closure repairs

Candidate-bearing legacy handoffs report stale integration pins even without evidence. Standard advisory rechecks exact run attempts and workflow identity after all job mappings, then rechecks installed ref and proposed PR merge. Previously repaired transport and post-merge races remain covered. No enforcement change.

## Parallel active handoff candidate

Explicit owner-approved claim --parallel promotes the legacy singleton envelope to schema v2 sorted list without changing existing handoffs, acceptance, assignments or archives. Per-issue selection is required for v2 mutations, no implicit retargeting. Save compares active maps by issue and rejects unrelated edits and downgrade. Standard advisory permits unrelated active v2 PRs; optional gate fails closed, lifecycle remains idle-only. Solo v1 remains default, unchanged commands. Same-issue claim remains idempotent cooperative recovery, not an actor lease; stale ref transactions still require reload, not fairness certification. No production installation change.

Compatibility guard: inspect the literal parallel schema capability in the byte-verified installed package before promotion. A newer client cannot upgrade an old installed reader's state by itself. Idle lifecycle upgrades refuse a target pin lacking the declaration if v2 state exists. A disposable bare Git test injects an actual competing non-force ref update between object creation and publication, verifies rejection, reloads and replans the loser, and checks both assignments, history and product bytes. This is a simulated GitHub transport over real Git objects, not a live agent trial.

## Bounded automatic contention recovery (isolated candidate)

Separate experiment branch while live acceptance is rate-limited. Existing CLI commands keep original arguments. Parallel apply rebuilds only after typed pre-publication drift or definitive unthrottled 409/422 ref rejection and a bounded single-parent history read proving the issue's ledger, active record and archive unchanged at every intermediate commit. Replan must preserve issue intent (uncommitted version allocation may change). No blind write replay, no retry of ambiguous outcomes or rate-limit/permanent errors; exact integration policies unchanged. Four attempts and jitter reduce collisions, not a fairness guarantee. No production mutation.

Qualification fixes: same-issue rejection test now competes with genuinely different intent, rather than potentially producing the same Git object. Added three consecutive real Git conflicts, single completion archive, product movement tests; intermediate ledger continuity and schema non-regression verified at each commit.

## Qualification review repairs

Preserve ambiguous 408/5xx candidate identity with Retry-After; wait for delays up to eight seconds before confirmation, otherwise defer with exact candidate and delay. Propagate numeric child CLI cooldown receipts without replay or text guessing. Verify immutable criteria and integrated rows for every intervening revision, plus unchanged pinned package blob IDs and modes, including intermediate changes that are later restored. Qualification only; no new feature or deployment.

## Bounded continuation qualification

Isolated candidate atop the exact compatibility revision 3610e00263b7fcce21de4c678d4d4ba61475e1b9. Existing CLI eligible parallel writes may continue the same immutable issue intent for two bounded rounds of four attempts. Each definitive conflict is verified, including the final attempt; an unchanged ref does not become a contention result. A stable digest of original installation, product, issue, planned transition and CLI request parameters is recorded in the same publication commit; raw intent is not written to metadata. Exhaustion returns an identity and initial/observed revisions but does not persist pending intent or automatically resume after process loss. This is a publication receipt, not exactly-once crash recovery or starvation freedom. Reuse only verified immutable tree metadata and identical blob identities during adjacent history reads; changed bytes must match the claimed blob SHA. No policy repin or ambiguous PATCH replay; no coordinator, deployment or version allocation.

## Repeated workload qualification

Repeat the previous qualification matrix against the compatibility-plus-continuation source. Four concurrent workers maximum, 1/2/5/10/25/50/100 logical clients and three transactions each, two bounded rounds; record all simulated API requests and separately identify harness resubmission. Eight consecutive wins establish the remaining starvation counterexample. Restart replay and real Git migration tests remain required. Accelerated sleeps and simulated transport are not a live service or independent agent acceptance. Failed progress gates remain failures even if regression assertions pass.
