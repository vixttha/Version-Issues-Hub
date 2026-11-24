# VIB v0.0.1 — owner review packet

**Candidate only; not released or approved for stable distribution.** Target v0.0.1, development checkpoints through v0.0.0.19. [PR #2](https://github.com/vixttha/Version-Issues-Hub/pull/2) remains draft. The verified installed-package candidate is [4fc9ac47462101b941ea2f78fc939d42a9de0032](https://github.com/vixttha/Version-Issues-Hub/tree/4fc9ac47462101b941ea2f78fc939d42a9de0032). The subsequent #39 acceptance-harness and review-document correction does not change the installed package or historical checkpoint pins; verify its own exact candidate and CI via PR #2 before accepting.

## Current evidence and open gates

- [Public PR verification](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45357923198) and [push verification](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45357911909): 77 tests per checkout, 19 checkpoint receipts, Graphify 96 nodes/95 edges. [Live read-only PR acceptance](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45357923129) and [law contract](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45357923126) passed on that candidate. These are historical exact-revision results, not automatic acceptance of a later commit.
- [Clouds non-destructive lifecycle](https://github.com/vixttha/clouds/actions/runs/45357811869) passed after the separately authorized prepared-tree connector upgrade to f06084dab6d3339d10c3c3793a365bedc5ac1362. Preserve the original HTTP 500 and other failed attempts; the original direct PATCH failure is not claimed fixed. No live deletion.
- [Fresh remote CLI self-install](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45382958376) passed, source 4fc9ac47462101b941ea2f78fc939d42a9de0032, installed branch 62c6c51802c3806909ccc191696b8dbb9b91fcad. Dry-run and apply exited 0; duplicate refused. Same-repository qualification only, not a fresh cross-repository install or model trial. Preserve the existing branch.
- [Phase 4 issue #37](https://github.com/vixttha/Version-Issues-Hub/issues/37) is the current acceptance register. Independent fresh ChatGPT and alternative-harness trials under the approved model configuration and owner acceptance remain outstanding. No mechanical or historical test substitutes for these trials.
- #34 optional hard-enforcement publication race remains separately open; Standard adoption does not require hard enforcement. #39 tracks acceptance-harness recovery and self-install handling. No live pilot writes or automatic retry authorized.
- Licensing remains unresolved: no verified product-level grant at the reviewed VIB source. No release, distribution approval, paid runners or commercial launch.

## Standard mode

Standalone pinned installation; adopter-local issue and handoff state; revision-bound verification; one active Worker; owner decisions. Optional hard enforcement is separate, not required or enabled here (#15, #22). Six architectural laws and read-only capability discovery are integrated into this development branch (#28, #32); no other ecosystem tool is a mandatory dependency.

## Historical evidence (superseded status wording)

The following earlier observations are preserved as historical context, not the current acceptance gates.

### Earlier evidence and open gates

- Exact predecessor 3f426e4940ef37544520851980418c71c31e0b93: 68 regression tests, Graphify, law check and read-only public adoption passed in runs 45340536708, 45340536956, 45340536697, 45340529495 and 45340529504.
- Actual BART and AlderVale installs and live recovery; disposable existing-repository manual upgrade and lease removal passed in run 45337083418; preserved state in test/vib-install-lifecycle at 2d19c4c00d78fb20b5bb98bef6a39453a1c0d1ea.
- Safe CLI lifecycle tests with real local Git objects and simulated API. Real clouds CLI install created its ref; upgrade apply failed at GitHub PATCH git/refs HTTP 500 in run 45339505842. Do not replay; inspect current target and use a separately reviewed transport if authorized. Fresh empty repository and generalized live upgrade acceptance not complete.
- Independent Notion harness recovery trial is partial (#10), not a fresh ChatGPT trial. Controlled comparison on BART #69 found no accuracy gain, and the intervention used more observed tool calls. Full development benchmarking remains open. Mechanical tests cannot substitute for LLM acceptance.
- v0.0.0.17 handles GET transport timeouts; verify its own exact CI and receipts before acceptance. Failed attempts retained.
- Licensing: no LICENSE or COPYING at the current VIB source tree; owner must choose a license and verify reuse before redistribution. README HQ also lacks a product-root license at its current source pin; archive licenses are not a grant for README HQ.
- No release tag, main merge, ruleset activation, paid execution or commercial launch authorized by candidate testing. Explicit owner decision tied to exact accepted source and evidence remains required.

### Earlier owner review

Review exact candidate, independent agent evidence, live lifecycle limitations and licensing. Do not conflate a passed schema or discovery check with product acceptance or hard merge enforcement.
