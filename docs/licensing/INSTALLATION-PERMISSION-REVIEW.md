# Licensing review — proposed installation permission (not a grant)

Status: REVIEW_ONLY_NOT_A_GRANT. Owner selected PolyForm Strict 1.0.0 for now. Keep the exact frozen engineering candidate 265e0e4724bc409b16d2605fc4d59d2f3f658eaf, 22 issue-version assignments and existing historical installs. This isolated branch prepares a legal and packaging review, not a stable release or permission to use VIB.

## Proposed permission boundary for counsel and owner review

- For an otherwise permitted purpose, allow copying the unchanged pinned VIB package, license and notice into the user's own dedicated installation branch, including a private repository, and allow normal execution, backups, and owner-controlled upgrades.
- For a public repository, expressly decide whether to allow hosting the unchanged package only in the dedicated branch, including unavoidable GitHub view/fork rights. This is a separate distribution permission; do not assume Strict authorizes it. If not approved, restrict adopters to permitted private installations or redesign distribution later. No blanket redistribution, modified copies, resale, sublicensing or competing product rights.
- Adopter-local manifest, ledger, handoff, receipts and independently authored product code are not VIB-owned software merely because they are stored alongside it. State editing and normal operation must be allowed without permitting changes to the pinned VIB package.
- Commercial use outside Strict's permitted purposes requires a separate agreement; its specified organization exceptions and fair-use savings are preserved. No customer terms, evaluation period, price, licensing service or retroactive restriction assumed.
- Separate rights in logos, slogans, third-party material and patent rights. Obtain rights-holder review before using a patent grant. Do not alter the official PolyForm text or claim trademark clearance.

## Review candidate packaging

Proposed two namespaced paths VIB-LICENSE.md and VIB-NOTICE.md in the 14-file package, avoiding a root LICENSE collision with adopter content. Reference text is not an operative root license. Review-only installer and lifecycle refuse any apply or prepare-only operation targeting either proposed legal path; plans and historical source verification remain read-only. Old source pins do not require future files; an older installer rejects unknown new paths. Do not bypass the guard. Future approved publication is a distinct reviewed candidate: put the unmodified official license at the VIB source root, map that file into the namespaced installed path, finalize operative notice and exact scope, remove the review-only guard only on owner approval, and verify real fixture install/upgrade, collision refusal, state preservation, historical package hashes and exact public CI. Existing installs must not be modified without adopter authority. Do not add an enforcement server. This review branch does not prove legal enforceability or final distribution.

## Approval gates

1. Rights holder and scope confirmed; third-party and AI-assisted provenance resolved.
2. Counsel/owner approves exact permission and notice, including public-branch distribution decision.
3. Approved license candidate technically validated; separate explicit distribution and release authorization.
4. Independent agent acceptance #37, commercial clearance #45, publication #46 and release hold #40 remain open.
