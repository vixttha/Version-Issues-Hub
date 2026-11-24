# VIB front-door audit — 2026-11-24

Target: vixttha/Version-Issues-Hub; public main 1b11865f79464ae7db9a648467e8c2c1cb898a02; candidate 4fc9ac47462101b941ea2f78fc939d42a9de0032; README HQ installed branch 18c99e2e3a9d93ff7cfa37203ae18e88160062dc. Technique library pinned at [88feb6971d2f49c530535f09d0defb1e9e1808bf](https://github.com/vixttha/README-HQ/tree/88feb6971d2f49c530535f09d0defb1e9e1808bf). README workspace v0.0.1 is an unapproved draft; product v0.0.0.19 is an unreleased development candidate. No publication or product writes.

| Priority | Observation | Reader impact | Draft response |
| --- | --- | --- | --- |
| High | [Public main README](https://github.com/vixttha/Version-Issues-Hub/blob/1b11865f79464ae7db9a648467e8c2c1cb898a02/README.md) contains only a title | No first action, status or navigation | Candidate-aware entry points; actual homepage promotion remains owner-gated |
| High | [Previous workspace draft](https://github.com/vixttha/Version-Issues-Hub/blob/18c99e2e3a9d93ff7cfa37203ae18e88160062dc/workspace/v0.0.1/DRAFT.md) pins v0.0.0.5 | Readers miss Standard VIB, current installer and lifecycle | Update pin and scope claims; keep old draft in Git history |
| High | Previous draft conflates optional enforcement with acceptance | Readers may infer mandatory App or rulesets | Clearly distinguish advisory default and unproven optional enforcement |
| Medium | Historical receipts are not independent host trials | Risk of overclaiming compatibility | Explicit pending #37, distinguish actual adopter use from independent LLM trials |
| Medium | No product LICENSE in pinned tree | Public visibility could be mistaken for reuse permission | Flag owner decision; no license assigned |
| Medium | Brand kit contains no approved identity or assets | Homepage cannot yet carry a stable brand | Separate strategy draft in Brand-Identity branch; no artwork or brand publication |

## Applied techniques

Library commit above. Active records reviewed: [role-based-entry-points](https://github.com/vixttha/README-HQ/blob/88feb6971d2f49c530535f09d0defb1e9e1808bf/techniques/role-based-entry-points.md), [exact-revision-walkthrough](https://github.com/vixttha/README-HQ/blob/88feb6971d2f49c530535f09d0defb1e9e1808bf/techniques/exact-revision-walkthrough.md), [agent-instruction-pointer](https://github.com/vixttha/README-HQ/blob/88feb6971d2f49c530535f09d0defb1e9e1808bf/techniques/agent-instruction-pointer.md), [claim-scope-labels](https://github.com/vixttha/README-HQ/blob/88feb6971d2f49c530535f09d0defb1e9e1808bf/techniques/claim-scope-labels.md), [independent-version-lines](https://github.com/vixttha/README-HQ/blob/88feb6971d2f49c530535f09d0defb1e9e1808bf/techniques/independent-version-lines.md), [declared-versus-observed-evidence](https://github.com/vixttha/README-HQ/blob/88feb6971d2f49c530535f09d0defb1e9e1808bf/techniques/declared-versus-observed-evidence.md), [permanent-proof-links](https://github.com/vixttha/README-HQ/blob/88feb6971d2f49c530535f09d0defb1e9e1808bf/techniques/permanent-proof-links.md). Existing mechanisms reused; no new library record proposed. The local draft uses revision links and status labels; the underlying candidate runs are observed. Full clean-reader walkthrough, desktop/narrow rendering, owner reuse terms and publication-path review remain pending.

## Scope and evidence

Source routes statically checked against pinned GitHub tree; candidate PR verify and graphify jobs read back as successful. [Final closure audit](https://github.com/vixttha/Version-Issues-Hub/pull/2) retains exact receipt hashes and historical results. This audit is not a fresh host trial. README HQ validation runs on the workspace branch; product CI is separate.

[Current draft](../workspace/v0.0.1/DRAFT.md).
