# Historical dogfooding audit — six independent products

**Decision:** Practical engineering utility is demonstrated by real development history. This is distinct from universal interoperability or measured causal performance improvement. Audit snapshot: 2026-11-24. No new product, release, installer change, or mandatory coordinator.

## Method and scope

Three layers: (1) inspect actual issue/PR narratives and distinguish open findings, merged output, branch-local usage, and planned features; (2) read exact Git files and object identities, historical run metadata, selected job outcomes and logs; (3) independently recheck the pinned evidence on a read-only GitHub public runner, including the Git blob hash and run attempt identity. The machine-readable evidence register contains 21 distinct case records (18 internal development cases, two external BART corroborations, one installed-only control). Cases share evidence and are not independent experiments. The public issue/PR census is metadata-only; full historical causal attribution for every commit, private agent action, or unpublished record is unavailable.

## Case register

| ID | Tool | Host | Evidence classification | Observed contribution |
| --- | --- | --- | --- | --- |
| D01 | Provenistem | Provenistem | operational self-use | 11 ideas and 16 features in current pinned self-catalog; first public check validated 10 ideas and 15 features. |
| D02 | VIB | VIB | operational self-use, candidate | 17 actual issue/version assignments and pinned acceptance receipts; one active workflow, not stable release. |
| D03 | Lydite | Lydite | release qualification | Five public jobs verified language examples, inventory/starter adoption, graph maps and candidate receipt at v0.0.4 source. This is native self-validation, not independent efficacy evidence. |
| D04 | Provenistem | Lydite | verified draft use | 6 ideas and 7 features at historical pinned catalog; actual release references and cross-platform validation; draft not merged. |
| D05 | Provenistem | VIB | operational branch use | 6 ideas and 6 features, historical source kept distinct from live issue ledger; navigation deficiency tracked in #18. |
| D06 | Provenistem | Brand Identity | operational project records | 8 ideas and 7 features in project-owned catalog; 6 marked verified, one implemented; status is record claim, not new independent certification. |
| D07 | Provenistem | README HQ | corrected adopter records | Corrected 12 ideas/12 features catalog ownership and selection boundaries in #149; preserved original trial. |
| D08 | Veraphify | Provenistem | real archive and defect investigation | Two version archives and three code citations; audit probes reproduced blocked parent, partial index build and duplicate JSON fields on v0.0.2. Defects remain open; audit success means reproduction succeeded. |
| D09 | Veraphify | Lydite | integrated adopter verification | Pinned v0.0.9 archive CLI validated inventory implementation at tools/inventory.py:212; real Lydite source and digest. |
| D10 | Veraphify | README HQ | integrated adopter verification | Pinned archive CLI verified technique registry implementation tools/check_readme_hq.py:31 at exact source. |
| D11 | Veraphify | VIB | retained candidate archive | Verified eight implementation citations and persisted archive; candidate only, not all 17 checkpoints. |
| D12 | Lydite | Veraphify | integrated product qualification | 211 named Vault cases across six topics, 19 brand tests, Linux/Windows archive replay; five repair issues #57–61, including dot-prefixed repo regression. Original detection of #61 credited to CodeRabbit, not Vault. |
| D13 | Lydite | Brand Identity | integrated repair verification | Five mechanical jobs and 53 native Vault tests; draft vs approved role handling and safe evidence links; five expected failures converted to normal tests. |
| D14 | README HQ | Veraphify | real documentation and execution trial | Pinned README and two-version walkthrough, rendered navigation and exact citations; CodeRabbit guidance corrected. README/product and workflow revisions kept distinct. |
| D15 | README HQ | README HQ | self-improvement from adopter trial | Veraphify pilot led to missing technique definition and searchable five-step reusable combination; catalog validated on both platforms. Fresh independent handoff remains pending in historical pilot. |
| D16 | README HQ | VIB | verified documentation draft | Draft v0.0.1 README authored at older pinned candidate, two public jobs verified navigation/maps. Not published and not current release guide. |
| D17 | Brand Identity | Veraphify | creative planning and name confirmation | Three scored concepts, recorded selected Filed Edge direction and name confirmation; project asset manifest empty. Later visual directions not inferred; no approved logo claim. |
| D18 | Brand Identity | Brand Identity | real template self-development | Own verifier exercised by Lydite, actual release-candidate approval and evidence link tests; 53 native tests in #16. Shared evidence with D13, not extra test count. |
| D19 | VIB | BART (external) | operational handoff and integration | 24 historical mappings at adopter pin; #55 v0.0.3.2 and #69 v0.0.3.3 integrated; exact main CI 10/10. Later #45 handoff pinned to active owner decision. No package release inferred. |
| D20 | Brand Identity | BART (external) | actual draft assets | Two recorded draft logo/wordmark PNG exports; not final artwork approval. |
| D21 | Brand Identity | VIB | installed only | Blank creative decision: no proof of VIB branding completion. Excluded from practical-use tally. |

### Source anchors

- [Provenistem self-use record](https://github.com/vixttha/Provenistem/blob/8c9647d1cd168642ba4dd3b2b5ec3045634d1bcb/catalog/features/records/FEAT-000016.json) and [adopter audit](https://github.com/vixttha/Provenistem/blob/8c9647d1cd168642ba4dd3b2b5ec3045634d1bcb/catalog/ADOPTER-BUG-AUDIT.md).
- [VIB 17-checkpoint ledger](https://github.com/vixttha/Version-Issues-Hub/blob/dad94766a7462a67098be7408f49d0eeeadc3af0/ledger/issue-versions.json), [PR #2](https://github.com/vixttha/Version-Issues-Hub/pull/2), [BART adopter ledger](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/blob/beab675bc7c8c228a77e858c3c3a50c40fe7ec2b/ledger/issue-versions.json).
- [Lydite Provenistem catalog PR #34](https://github.com/vixttha/Lydite-Test-Vault-Template/pull/34), [Lydite Veraphify adoption #115](https://github.com/vixttha/Lydite-Test-Vault-Template/pull/115), [Lydite upstream defect report #121](https://github.com/vixttha/Lydite-Test-Vault-Template/issues/121).
- [Provenistem issues #2](https://github.com/vixttha/Provenistem/issues/2), [#3](https://github.com/vixttha/Provenistem/issues/3), [#4](https://github.com/vixttha/Provenistem/issues/4), [audit run](https://github.com/vixttha/Provenistem/actions/runs/44995999617), [archive lookups](https://github.com/vixttha/Provenistem/actions/runs/44995999617/job/137127048871). Ubuntu job log explicitly confirmed duplicate_member, partial_index_build, blocked_parent. These are reproduced defects, not upstream repairs.
- [Veraphify integration #56](https://github.com/vixttha/Veraphify/pull/56), [dot-prefixed repo issue #61](https://github.com/vixttha/Veraphify/issues/61), [Vault documentation](https://github.com/vixttha/Veraphify/blob/add4a029312c958a5e126990fc49e802c0112c27/test-vault/README.md), [exact public run](https://github.com/vixttha/Veraphify/actions/runs/44653386073), [Brand Identity decision](https://github.com/vixttha/Veraphify/blob/63c10e8797a1803f3198387d74c59ddc10056ae1/brand-identity/01-strategy/creative-decision.json).
- [README HQ applied to Veraphify #55](https://github.com/vixttha/Veraphify/pull/55), [README HQ adoption #143](https://github.com/vixttha/README-HQ/pull/143), [feedback #148](https://github.com/vixttha/README-HQ/issues/148), [corrected Provenistem records #149](https://github.com/vixttha/README-HQ/issues/149).
- [Brand Identity mechanical repair #16](https://github.com/vixttha/Brand-Identity-Template/pull/16), [53-test job](https://github.com/vixttha/Brand-Identity-Template/actions/runs/44513584643/job/135523733650), [BART draft asset manifest](https://github.com/vixttha/Brand-Identity-Template/blob/2d199fc4c206df3032803fea9eb7c5327a31aae9/brand-identity/09-assets/manifest.json).
- [VIB archive and preservation](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45331511873), [VIB README draft](https://github.com/vixttha/Version-Issues-Hub/blob/990ffad5c1ede38bc7edac3a145499f0dbbc0788/workspace/v0.0.1/DRAFT.md), [BART exact-main CI](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/actions/runs/45337193197).

## Closed feedback loops

1. **Provenistem ↔ Veraphify:** Provenistem tracked its own development; Veraphify retrieved exact historical code and supported audit probes; findings returned to Provenistem's issue and idea library. Three reproducible defects, open upstream.
2. **Lydite ↔ Veraphify:** Lydite's adapted Vault qualified Veraphify's preview and regressions; Veraphify in turn archived and checked Lydite implementation evidence. 211 named cases and 19 brand tests belong to the same qualification run, not additive across case studies.
3. **README HQ ↔ Veraphify:** Actual product documentation was drafted and exercised, then the trial was distilled into a reusable five-step technique combination. Veraphify also independently archived README HQ source.
4. **Lydite → Brand Identity:** Native public-runner regressions verified real handoff and link repairs. Brand Identity contributed creative-direction records and tests to Veraphify. The Veraphify name and concepts are real historical records, not final logo delivery.
5. **Provenistem + Veraphify + README HQ → VIB:** Project records, versioned archive retrieval, and versioned documentation provided separate engineering context. VIB dogfoods its issue/version ledger and has real external BART issue integration/handoffs. No evidence that VIB has already been operationally used inside each of the other five upstream products.

## Honest commercial claims

Supported: six independently developed tools with real self-use and cross-product engineering contributions; public reproducible evidence; demonstrated actual bug reproduction, regression verification, documentation reuse, and durable handoffs. The earlier 64-configuration/192-smoke matrix supplements this evidence but is not the basis for practical utility. Not supported: every tool used on every other tool, all defects fixed, 99% reliability, universal harness support, stable release of every product, or measured token/time/cost savings. Prior paired recovery pilot was a tie (7/8 each; 9 vs 15 observed tool calls) and remains part of the evidence. Historical utility is not invalidated by an inconclusive performance benchmark.

## Preservation and follow-up

Retain source pins and failures. Do not close existing issues, modify releases, alter adopter branches or infer owner approval. Finish unresolved VIB live upgrade, optional hard gate review and fresh-harness acceptance separately. Document verified dogfooding as existing product evidence, not a new product feature.

## Completed independent replay

[Triple-check receipt](VERIFIED-RECEIPT.md) — public runner PASS. 18 exact Git files, 17 historical attempts, 431 issue/PR metadata records and retained archive digest verified.
