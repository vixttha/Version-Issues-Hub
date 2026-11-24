# Licensing review — proposed installation permission (not a grant)

Status: REVIEW_ONLY_NOT_A_GRANT. Owner selected PolyForm Strict 1.0.0 for now. Keep the exact frozen engineering candidate 265e0e4724bc409b16d2605fc4d59d2f3f658eaf, 22 issue-version assignments and existing historical installs. This isolated branch prepares a legal and packaging review, not a stable release or permission to use VIB.

## Proposed permission boundary for counsel and owner review

- For an otherwise permitted purpose, allow copying the unchanged pinned VIB package, license and notice into the user's own dedicated installation branch, including a private repository, and allow normal execution, backups, and owner-controlled upgrades.
- Owner approved hosting the unchanged package in users' own public dedicated branches for otherwise permitted purposes (issue #47 comment 7133948319). Exact supplemental wording in VIB-NOTICE-REVIEW.md is still non-operative. This is separate distribution permission; do not assume Strict authorizes it. No blanket redistribution, modified copies, resale, sublicensing or competing product rights.
- Adopter-local manifest, ledger, handoff, receipts and independently authored product code are not VIB-owned software merely because they are stored alongside it. State editing and normal operation must be allowed without permitting changes to the pinned VIB package.
- Commercial use outside Strict's permitted purposes requires a separate agreement; its specified organization exceptions and fair-use savings are preserved. No customer terms, evaluation period, price, licensing service or retroactive restriction assumed.
- Separate rights in logos, slogans, third-party material and patent rights. Obtain rights-holder review before using a patent grant. Do not alter the official PolyForm text or claim trademark clearance.

## Review candidate packaging

Proposed two namespaced paths VIB-LICENSE.md and VIB-NOTICE.md in the 14-file package, avoiding a root LICENSE collision with adopter content. Reference text is not an operative root license. Review-only installer and lifecycle refuse any apply or prepare-only operation targeting either proposed legal path; plans and historical source verification remain read-only. Old source pins do not require future files; an older installer rejects unknown new paths. Do not bypass the guard. Future approved publication is a distinct reviewed candidate: put the unmodified official license at the VIB source root, map that file into the namespaced installed path, finalize operative notice and exact scope, remove the review-only guard only on owner approval, and verify real fixture install/upgrade, collision refusal, state preservation, historical package hashes and exact public CI. Existing installs must not be modified without adopter authority. Do not add an enforcement server. This review branch does not prove legal enforceability or final distribution.

## Approval gates

1. Rights holder and scope confirmed; third-party and AI-assisted provenance resolved.
2. Public-branch policy owner-approved; counsel/owner review of exact permission, notice and scope still pending.
3. Approved license candidate technically validated; separate explicit distribution and release authorization.
4. Independent agent acceptance #37, commercial clearance #45, publication #46 and release hold #40 remain open.

## Finalization checklist (not authorization)

- Retain the unmodified reference text and its source permission. After rights and exact wording approval, publish the official root LICENSE with a clear scope/exclusions notice. Preserve the existing historical mapping for review and prior pins; any path mapping change must be explicitly tested against earlier literal declarations (do not simply replace an allowlist key that historical pins need).
- Turn the review notice into approved operative terms only after approval. Remove the review-only runtime refusal only on a separately approved final candidate. The fixture-only simulation uses a mocked review guard inside disposable Git objects and is not proof of live authorization or a production bypass.
- Check the complete package hashes, old-pin recovery, new installs, upgrades, collision refusal, unchanged default/product refs and adopter-owned license/state. Validate exact final SHA and matching proposed merge tree. No live adopter upgrade unless separately authorized.

## Ecosystem transition and final scope review

Owner direction: VIB, Veraphify, Provenistem, Lydite Test Vault and Brand Identity Template should adopt the same future PolyForm Strict model for rights-cleared original portions, with narrowly scoped public installation permission where appropriate. Prior MIT grants remain valid; retain applicable original notices and distinguish copied or shared material. Each project needs its own contributor/provenance, nested package, migration, and acceptance review. This is not a blanket grant, relabeling of historical releases, or permission to modify other projects' source. The owner may reuse their own rights-cleared material across projects, including commercially, subject to third-party obligations. No mandatory dependency or centralized license server.

For this candidate, VIB-NOTICE.md embeds the verbatim applicable MIT notices and explicit shared-law exclusion. The official PolyForm reference and 14-file mapping are unchanged; no operative root license until final rights/terms approval. Keep the review-only refusal. If later publishing a root LICENSE, retain historical source mappings and validate new package hashes, upgrade compatibility and notice placement. See issue #47 audit receipt 7134465560.
