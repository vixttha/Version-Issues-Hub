# VIB v0.0.1 — owner review packet

**Candidate only; not released or approved for stable distribution.** Target v0.0.1, development checkpoints through v0.0.0.17. [PR #2](https://github.com/vixttha/Version-Issues-Hub/pull/2) remains draft.

## Standard mode

Standalone pinned installation; adopter-local issue and handoff state; revision-bound verification; one active Worker; owner decisions. Optional hard enforcement is separate, not required or enabled here (#15, #22). Six architectural laws and read-only capability discovery are integrated into this development branch (#28, #32); no other ecosystem tool is a mandatory dependency.

## Evidence and open gates

- Exact predecessor 3f426e4940ef37544520851980418c71c31e0b93: 68 regression tests, Graphify, law check and read-only public adoption passed in runs 45340536708, 45340536956, 45340536697, 45340529495 and 45340529504.
- Actual BART and AlderVale installs and live recovery; disposable existing-repository manual upgrade and lease removal passed in run 45337083418; preserved state in test/vib-install-lifecycle at 2d19c4c00d78fb20b5bb98bef6a39453a1c0d1ea.
- Safe CLI lifecycle tests with real local Git objects and simulated API. Real clouds CLI install created its ref; upgrade apply failed at GitHub PATCH git/refs HTTP 500 in run 45339505842. Do not replay; inspect current target and use a separately reviewed transport if authorized. Fresh empty repository and generalized live upgrade acceptance not complete.
- Independent Notion harness recovery trial is partial (#10), not a fresh ChatGPT trial. Controlled comparison on BART #69 found no accuracy gain, and the intervention used more observed tool calls. Full development benchmarking remains open. Mechanical tests cannot substitute for LLM acceptance.
- v0.0.0.17 handles GET transport timeouts; verify its own exact CI and receipts before acceptance. Failed attempts retained.
- Licensing: no LICENSE or COPYING at the current VIB source tree; owner must choose a license and verify reuse before redistribution. README HQ also lacks a product-root license at its current source pin; archive licenses are not a grant for README HQ.
- No release tag, main merge, ruleset activation, paid execution or commercial launch authorized by candidate testing. Explicit owner decision tied to exact accepted source and evidence remains required.

## Owner review

Review exact candidate, independent agent evidence, live lifecycle limitations and licensing. Do not conflate a passed schema or discovery check with product acceptance or hard merge enforcement.
