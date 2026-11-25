# VIB — permanent language responsibility charter

Decision date: 2026-11-25. Owner requested that each language be reviewed and assigned a permanent testing responsibility. This is the operating allocation for Agent 4; the individual roles are engineering decisions under that instruction, not separately owner-ratified implementation or release approvals. The first work package remains an engineering recommendation until selected. No new tests are claimed implemented by this charter.

## Scope

VIB remains Python-based. The 14 existing Lydite language folders and template metadata remain unchanged. No obligation to build all 14 suites or introduce product dependencies. Core = routine VIB verification; Advanced = scoped research/negative testing on demand; Supporting = independent consumer checks when justified; Optional = dormant until a concrete consumer/interface justifies work. All roles use synthetic/disposable fixtures and standard free GitHub-hosted runners. No production state writes. Cross-language testing may corroborate but does not replace native VIB regression tests or independent agent acceptance.

| Language | Class | Permanent responsibility | First candidate test | Acceptance boundary |
|---|---|---|---|---|
| Python | Core | Production behavior and regression oracle | Actual Python CLI, ledger, install, lifecycle, handoff, receipt and validation suites; reproduce #54 | Positive and negative cases on Ubuntu and Windows; no skipped/zero-test false pass |
| Bash | Core | Linux CLI and Git integration | Disposable repository; paths with spaces, shell quoting, executable modes, exit status | Actual CLI exit and Git object/ref state agree with expected; no live mutation |
| PowerShell | Core | Windows CLI and filesystem portability | Literal paths, brackets, Unicode, CRLF, subprocess/exit semantics; reproduce #54 alongside Python | Binary Git blob and mode checks, positive and negative cases on Windows; distinguish fixture vs product |
| Go | Advanced | Concurrent clients and contention | Disposable 1–100 simulated clients; collisions, duplicate claims, starvation, retry/latency, operation reconciliation under #53 contract | Distinct claims progress, same claim unique, no lost operations; record schedule/seed and latency; no production capacity claim |
| Rust | Advanced | Defensive input and evidence integrity | Independent strict parser, truncation, duplicate keys, numeric bounds, malformed and oversized evidence; SHA-256 cross-check | Known valid evidence accepted, corrupted inputs rejected with bounded resource use |
| F# | Advanced | Event replay and temporal recovery | Operation-ID event sequences, interrupted transitions, duplicate/reordered events | Repeated operations converge without double application; replay matches expected history |
| Haskell | Advanced | Reference state invariants | Pure reference model for legal transitions, version uniqueness, history preservation; generated sequences | Counterexamples reproducible by seed/trace; reference model independent of implementation; not a formal proof |
| JavaScript | Supporting | Cross-runtime JSON and receipt reading | Node parser and digest checks, Unicode, JSON number/string distinctions, exact run identity | Independent consumer agrees with specified valid/invalid fixture corpus; guard JS safe integer limits |
| TypeScript | Supporting | Typed client boundary | Discriminated state/receipt types and unknown-payload runtime validation; explicit type-check separate from Node type stripping | Compile-time negative fixtures and runtime malformed inputs both fail; no mandatory TypeScript toolchain in product |
| C# | Optional | Versioned .NET consumer compatibility | System.Text.Json parsing of public receipt/manifest schemas, unknown/missing fields and schema versions | Accept documented versions; reject invalid types/unsupported versions; only on demonstrated consumer need |
| Java | Optional | Byte encoding and portable file interchange | UTF-8, BOM policy, line endings and byte-based digests using JDK standard APIs | Round-trip and exact SHA-256 fixtures match published byte contract; only on demonstrated JVM need |
| C++ | Optional | Native numerical and binary interface compatibility | Boundary lengths, integer width/overflow and native file consumers if a real interface exists | Documented native interface fixture passes both valid and invalid bounds; no native extension required |
| Lua | Optional | Lightweight scripting integration | CLI wrapper exit status, stdout/stderr separation, small synthetic integration scripts | Wrapper propagates failures and does not mutate active refs; only if actual Lua consumer exists |
| Ruby | Optional | Text automation and documentation consumer | Independent catalog/link/text processing, Unicode and stable IDs for consumer scripts | Detect missing/duplicate IDs and invalid links in deterministic fixtures; only on actual Ruby consumer need |

C is not a current installed language. Keep out of scope until a real C interface exists and the owner approves adding it upstream or locally. Do not invent a native interface just to exercise another language.

## Recommended activation order

1. Python + PowerShell: investigate Windows lifecycle failure [#54](https://github.com/vixttha/Version-Issues-Hub/issues/54); Python owns product/fixture logic, PowerShell owns platform-specific black-box checks. Do not repair or claim product work without owner/Head scope.
2. Bash: Linux parity and install/ref safety.
3. Go: independent contention simulator only against the separately qualified #53 research contract; do not change other agents' work or treat current singleton rejection as a defect.
4. JavaScript and TypeScript: independent receipt/data contracts and typed boundary; pin any added dev tooling and test type checking separately.
5. Rust, F#, Haskell: negative evidence corpus and distinct replay/state-model work, based on real risks.
6. C#, Java, C++, Lua, Ruby: dormant, activate only for a real interface and separate owner scope.

## Evidence and governance

Each new case needs a unique Lydite case identity, target source and vault SHAs, runner/OS/runtime, observed command and outcome, run/attempt, artifact digest where available and both passing and failing controls. Reject skipped, stale, zero-test and mismatched evidence. Graphify maps evidence; they do not prove runtime correctness. No new release gate, language runtime, checkpoint, merge or live claim is authorized by this document. No duplicated tests simply to increase counts. Retain historical evidence and report limits.

## Existing execution baseline (not this document's future implementation)

[Vault refresh f03a042](https://github.com/vixttha/Version-Issues-Hub/commit/f03a042e901e4199cdd048c7693ea25d1d671d50), product `7ae6626e44d01d29b11968da28e6debd816f8c06`. [Project run 45672661047](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45672661047): Ubuntu 112/112 tests passed; Windows 103/112 passed, nine lifecycle failures/errors, nine other suites green. [Template run 45672661225](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45672661225): four applicable jobs passed, upstream-only release recording skipped by design, three archived Graphify maps verified. Template language examples are not product tests. Windows failure is recorded in #54; root cause remains unproven. No new test case or fix was implemented by this charter.
