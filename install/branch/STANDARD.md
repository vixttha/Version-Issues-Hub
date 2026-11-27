# Standard VIB — default validation mode

## Standard validation contract

Install the dedicated Version-Issues-Hub branch into an initialized repository. No GitHub App, branch protection, separate test repository, database or extra service is required. For this public-runner profile use only authorized public repositories and standard GitHub-hosted runners. Private repository installs are supported by the installer but private execution is outside this profile.

Follow Head → Worker → Validate → Internal Auditor → Head. Before proposing integration, stage the complete issue scope, pin the installed state, PR head/base/proposed merge and each fix SHA, and map every acceptance criterion to its actual GitHub run attempt, workflow, job and steps. Use the same policy shape as GATE.md except omit publisher_app_id; replace each checks entry with {"run":123,"attempt":1,"workflow_id":52,"job_name":"product-test","steps":["Run acceptance"]}. No App fields are used.

Run `python -m tools.standard --target OWNER/REPO --policy /approved/standard-policy.json` in an authorized cloud host. It is read-only. It checks live repository and state identity, current PR and merge parents, complete staged scope, fix ancestry, run attempt, workflow and successful jobs/steps. A successful metadata check returns **review_required**, not a merge authorization. Missing, stale, mismatched or skipped evidence is rejected.

The Internal Auditor must independently review the actual checkout SHA in logs or receipts, actual test commands and outputs, runner type (standard hosted public), and criterion-specific results. Metadata alone cannot prove the workflow tested the intended code. If anything is absent or invalid, stop, return to Worker, and rerun verification. Record the reviewed exact revision, run attempt and result in the owner handoff. The owner alone approves integration. No standard verdict is published as a trusted check or claimed to block GitHub merges.

## Phase 3 completion and Phase 4

Standard Phase 3: read-only metadata validation, positive/negative tests on public runners, clear owner-review and no-enforcement behavior. Phase 4: live isolated installation, repository-specific mapping, real public-runner evidence, fresh independent agent resume, and upgrade/removal preservation. Optional hard enforcement remains a separate unproven capability until its own live pilot succeeds; it is not a standard release or adoption prerequisite. Do not change existing protection settings or install another template.

## Post-merge use of Standard mappings

`session finish integrated` and `session reconcile` reuse this policy format with one issue and the actual two-parent merge SHA/base, not the PR's synthetic merge. See WORKFLOW.md. The run must be a successful push or workflow_dispatch on the product branch at that exact SHA, with matching current attempt, job identity and successful mapped steps. The owner-reviewed decision must still establish actual checkout, commands, public hosted runner and criterion outcomes. Other merge methods/events are not yet qualified. Existing pre-merge Standard evaluation is unchanged.

Standard evaluation also requires the staged handoff's proposed-merge/base pins to match the live policy. Legacy unpinned staged rows must be refreshed through the existing claim workflow. Head-only Actions metadata without the exact PR base/head association cannot establish integration freshness. Previous run receipts remain historical; review the actual checkout on the new candidate.

In owner-enabled parallel schema v2, unrelated active issues do not block Standard advisory evaluation of the complete staged scope for a different PR. Active work associated with that PR must first be staged or reconciled. Optional hard enforcement remains unqualified for v2; do not enable it.

Integration integrity (corrective candidate): separate engineering completion, production integration, and issue closure; do not report integration from issue closure, staging or an engineering-branch merge. Reconcile exact target evidence and outstanding bounded deferrals before unrelated claims. Existing installations require a separately reviewed upgrade; this text is not a production-integration or release authorization.

Ordinary pre-merge Standard accepts head-only run metadata for advisory review only when the exact commit objects establish identical head and preview trees and the PR association matches. Divergent or missing trees are refused; actual checkout and mapped steps still require independent review.

For multiple distinct historical fixes of one staged/deferred issue, use one owner-reviewed reconciliation policy with `schema_version: 1`, `outcome: historical_product_integration_batch`, and an ordered `proofs` array of separate `historical_product_integration` policies (each with exact archive index/digest, premerge evidence and full post-merge review). The proofs must cover every outstanding distinct fix and include the latest occurrence. No unrelated issue or partial integrated state is published; missing, conflicting, held or ambiguous authority fails closed. Do not infer proof from later ancestry alone. This is not permission to apply a live migration or integrate without separate owner approval.

A bounded same-fix deferral renewal does not destroy an eligible original staged proof basis. Use its exact archive occurrence and digest, fresh preview and post-merge evidence; distinct obligations remain until independently proved. Do not retire an issue with outstanding integration debt. Closed deferred issues require owner disposition reconciliation before a claim. Batch run attempts are checked again after all proofs; remote reads and publication are not an atomic cross-ref transaction.
