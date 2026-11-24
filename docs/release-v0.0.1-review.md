# VIB v0.0.1 — owner review packet

Status: **candidate, NOT APPROVED / NOT RELEASED**. Target project version v0.0.1; issue checkpoints v0.0.0.1–v0.0.0.8. [Draft integration PR #2](https://github.com/vixttha/Version-Issues-Hub/pull/2). GitHub issues and ledger are canonical; template versions remain independent.

## Candidate scope
- Stable issue/version mappings and revision-bound per-issue receipts.
- Pinned standalone installer (create-only, existing branches refused), adopter-local ledger, and cooperative agent handoff.
- Staging/reconciliation for multiple issues, owner decisions and exact evidence.
- Optional gate implementation: simulated controls only; disabled for VIB itself per [owner decision #15](https://github.com/vixttha/Version-Issues-Hub/issues/15). No claims of enforced merge blocking.
- Independent Provenistem, Veraphify, README HQ, and Lydite; optional references only. No mandatory dependencies or cross-template writes.

## Evidence and remaining acceptance
- [Prior exact candidate validation](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45331436864).
- [Durable archive and eight checkpoint citations](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45331511873).
- [Live read-only acceptance workflow](https://github.com/vixttha/Version-Issues-Hub/actions/workflows/live-acceptance.yml) must be checked at the proposed source revision.
- [Install and adoption issue #9](https://github.com/vixttha/Version-Issues-Hub/issues/9): actual BART adoption is separate from a fresh disposable repository creation and lifecycle trial. Upgrade/removal are not implemented as installer commands; do not represent occupied-branch refusal as upgrade support.
- [Fresh harness issue #10](https://github.com/vixttha/Version-Issues-Hub/issues/10): independent ChatGPT and second harness trials, using only installed branch URL and owner-authorized scope, are still required; separate process recovery is not independent LLM evaluation.
- Optional gate live pilot is not performed because branch protection is declined here. Exclude live enforcement claims from any cooperative-only release; separate explicit scope approval needed if deferring this feature.
- Verify reuse/license terms and package license before distribution; no license grant implied.
- Reconcile CodeRabbit reviews and exact final source/public CI, retain evidence, and record explicit owner acceptance. Do not merge, tag, publish, or close acceptance issues merely because a test suite is green.

## Owner decision
Approve only a named source SHA and evidence set after reviewing gaps. Product release and README publication are separate decisions. Do not change branch protection, pay for runners, or install into another project without owner authorization.
