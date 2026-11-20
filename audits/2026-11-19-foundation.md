# Foundation portfolio audit

**Recorded November 19, 2026.** Reviewed the 60 repositories returned for the owner before creation of the standalone project. Four had no commits. In the 56 others, inspection included the pinned default-branch tree, the root README if present, root agent instructions if present, and matching README branch names. All 56 recursive tree listings returned complete results. Of 55 root READMEs, 15 consisted of one non-empty line after trimming. Nineteen repositories had root agent instructions. This portfolio pass assessed documentation surfaces. The source migrations and public exemplars received the detailed inspection below.

## Public exemplars

| Repository and revision | What the source shows | What README HQ adopted or should verify |
| --- | --- | --- |
| [AlderVale at a6c2060](https://github.com/vixttha/AlderVale-Pact-of-Ten/tree/a6c2060b8175f505cc6327ccb5658cc00a458b24) | Windows launcher and source setup, guest first playthrough, signed-in Bazaar route, bug reporting and project rules have distinct entry points. Its HQ archives the guide separately from the homepage and keeps six Graphify maps. | Adopt role-based routes, first-success milestones, separate draft/archive/publication states, and version-map provenance. The published v0.0.4 README and archived v0.0.4 match by Git blob. |
| [BART at 3e7f9e0](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/tree/3e7f9e02e61739825b56bcafecebbd0221cc9657) | CLI and MCP first steps, a triangle fixture, platform-specific commands, separate release and development evidence, and a visual review. The v0.0.3 workspace survived on a topic branch outside the current HQ tree. | Import the topic-branch draft and published assets. The v0.0.4 HQ draft matches the README on main at the rebrand checkpoint. Treat archive approval and publication history as independent evidence. |
| [Brand Identity Template at 87d0f9a](https://github.com/vixttha/Brand-Identity-Template/tree/87d0f9aedbe69ca4b16815d6b3329efcf5889da9) | Copy-in installation, a direct ZIP link, an explicit template-to-project state change, and a standard-library verifier. CI describes the combined base and head and the tested SHA. | Adopt the clean consumer smoke check and use exact combined-commit evidence when a candidate is reviewed for merge. |
| [Lydite at fe7b00a](https://github.com/vixttha/Lydite-Test-Vault-Template/tree/fe7b00aa17862d7a01dfd15481594be837bc6d9f) | Human-readable guides sit alongside inventory metadata and executable fixtures. The readme distinguishes a declared case from a run result. | Adopt a searchable structured inventory with evidence status. Keep observations and actual execution results visible. |

## Findings

| Priority | Finding | Change in the candidate |
| --- | --- | --- |
| High | A project can use the same version number for its homepage, its HQ guide, and its software. BART's development checkpoint shows the ambiguity. | The index names the project and collection for every version and records both draft and published forms. |
| High | Looking only at the two HEADs loses BART's v0.0.3 visual workspace and canonical publication snapshot. | Pinned both public topic and publication commits. Preserved the two complete HQ trees with per-file blob hashes. |
| High | Header-only and missing READMEs give people and agents no route to first success or authoritative instructions. | Added a first-action and agent navigation contract plus a detailed audit procedure. |
| Medium | A README archive with media can render differently after moving between its workspace, archive, and homepage. | Preserved original media, added a portable navigation index, and recorded source-vs-destination path checks in the guide. |
| Medium | Flat prose alone makes repeated techniques difficult to detect across audits. | Added stable IDs, search aliases, outcome keys, and an exact-collision validator. The review step addresses equivalent ideas with different wording. |

The cross-repository pass was static. Git blob comparison verified the two publication equivalences above. Running each project's first-use path, retesting historical CI, and a rendered cross-platform review were outside this pass. Historical source docs with application-specific relative paths can be read in their original pinned GitHub tree.
