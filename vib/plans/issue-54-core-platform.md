# Issue #54 — core/platform test design

Status: planning only, 2026-11-25. Owner selected Python, Bash and PowerShell for Agent 4. No test code, fixture repair, workflow edits, product writes or new checkpoint allocation authorized by this document. Issue remains open. 80 proposed test families (66 P0, 14 P1); parameter variants are not separate families. P0 = closure-critical within supported contract; P1 = additional discovery, escalate confirmed defects separately. Existing tests may satisfy families only after exact case-to-evidence mapping; do not duplicate merely to inflate counts. Unsupported platform features require explicit classification, not silent skip or new product promises.

## Verified baseline and hypothesis
- [Issue #54](https://github.com/vixttha/Version-Issues-Hub/issues/54); product pin `7ae6626e44d01d29b11968da28e6debd816f8c06`; prior vault `f03a042e901e4199cdd048c7693ea25d1d671d50`; [run 45672661047](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45672661047/attempts/1): Ubuntu 112/112, Windows 103/112 (six errors/three failures in VIB-006). [Windows log](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45672661047/job/139411806299).
- [Fixture](https://github.com/vixttha/Version-Issues-Hub/blob/7ae6626e44d01d29b11968da28e6debd816f8c06/tests/test_lifecycle.py) sends content through subprocess text mode and reads Git show in text mode. [Lifecycle](https://github.com/vixttha/Version-Issues-Hub/blob/7ae6626e44d01d29b11968da28e6debd816f8c06/tools/lifecycle.py) verifies blob identity and 100644 mode; [installer](https://github.com/vixttha/Version-Issues-Hub/blob/7ae6626e44d01d29b11968da28e6debd816f8c06/tools/install.py) checks raw base64-decoded content against Git blob hash before UTF-8 decoding. Fixture transport is a strong hypothesis, not a proven root cause; don't weaken product checks. Existing simulator discards some mode/type information: use independent real Git objects or explicit mocked responses to exercise actual modes.
- [Vault runner](https://github.com/vixttha/Version-Issues-Hub/blob/6eb82410afc46142d0f1613da1b5d896b279769d/vib/run_cases.py) uses text logs and checks aggregate counts; test exact identities and evidence failure paths separately. No claim of a demonstrated vulnerability from static review.

## Test catalog

### Python (32)

| ID | Priority | Test family | Expected observation / method |
|---|---|---|---|
| 54-PY-01 | P0 | Original lifecycle regression | Run original 13 cases unmodified at pinned SHA; capture all nine failing identities on Windows and Linux control. |
| 54-PY-02 | P0 | LF binary write | Same UTF-8 LF fixture yields same Git blob ID on both OSes; compare raw bytes, not decoded text. |
| 54-PY-03 | P0 | Text-mode differential | Compare text=True and binary stdin in old fixture; show observed bytes, size, first differing offset and hash; no assumed result. |
| 54-PY-04 | P0 | Exact object read | Read via binary git cat-file; LF/CRLF/bare CR remain distinct; no strip or universal newline normalization. |
| 54-PY-05 | P0 | UTF-8 and locale | ASCII, accented, CJK, emoji, combining marks; byte length and hash match independent Git oracle under UTF-8 mode on/off. |
| 54-PY-06 | P0 | Line-ending corpus | LF, CRLF, CR, mixed endings, no terminal LF, repeated final LF and empty content round-trip exactly. |
| 54-PY-07 | P0 | Whitespace and NUL | Trailing spaces/tabs and NUL in synthetic byte oracle preserved; package acceptance follows documented UTF-8/text scope, not invented binary support. |
| 54-PY-08 | P0 | BOM and invalid UTF-8 | Raw UTF-8 BOM is distinguishable; malformed UTF-8 rejected by source decoder without ref writes. |
| 54-PY-09 | P0 | Hash boundary | Compare Git SHA-1 object header+bytes and raw SHA-256; byte lengths at 0, 1, 9, 10, 99, 100 and bounded large input. |
| 54-PY-10 | P0 | Genuine byte tamper | One-byte replacement, newline-only mutation, truncation, appended byte and empty replacement all reject against old pinned source. |
| 54-PY-11 | P0 | Git mode tamper | Change 100644 to 100755, symlink, tree or gitlink in disposable object fixture; reject before publication. |
| 54-PY-12 | P0 | Missing package leaf | Missing/renamed expected package path rejected; ref snapshot unchanged. |
| 54-PY-13 | P0 | Source response integrity | Wrong path/type/encoding/SHA, malformed base64, invalid UTF-8 and wrong commit identity reject. |
| 54-PY-14 | P0 | Tree response integrity | Wrong tree identity, truncated/missing completeness marker, duplicate path and malformed entry reject. |
| 54-PY-15 | P0 | Unchanged source and ancestry | Same source, ancestor, diverged source and wrong merge base reject; true descendant accepted for plan. |
| 54-PY-16 | P0 | Package path removal | Old source leaf absent in new package rejects; no automatic deletion. |
| 54-PY-17 | P0 | Collision types | New leaf collision, existing subtree at new leaf and non-tree parent collision reject; preserve unrelated paths. |
| 54-PY-18 | P0 | Manifest/state file modes | Missing, wrong-type or wrong-mode manifest, ledger and handoff rejected. |
| 54-PY-19 | P0 | Idle/enforcement gates | Active handoff, in_progress/staged issue, enabled enforcement reject; idle disabled state permits planning. |
| 54-PY-20 | P0 | Dry run | No POST/PATCH/DELETE; no state changes; exact deterministic changed paths. |
| 54-PY-21 | P0 | Owner and credential gates | Apply without owner approval or CLI credential rejects; prepare-only without apply rejects. |
| 54-PY-22 | P0 | Legal package boundary | Valid approved fixture succeeds; changed required license/notice or missing legal package fails; adopter license preserved. |
| 54-PY-23 | P0 | Fresh install and upgrade | Known-good source package install then upgrade to descendant; only authorized leaves change, exact parent and manifest hashes. |
| 54-PY-24 | P0 | Preserve unrelated state | Ledger/handoff, history, custom notes, unrelated executable/symlink/gitlink object identities and product ref unchanged. |
| 54-PY-25 | P0 | Proposed tree verification | Simulated API adds/removes/modifies unrelated leaf or mode; reject before ref PATCH. |
| 54-PY-26 | P0 | Stale identity and refs | Repository ID/name/default branch, archived/disabled flags, install ref/product ref drift before apply reject. |
| 54-PY-27 | P0 | Prepared upgrade | Object creation only; no ref move; later confirmation checks observed revision without blind retry. |
| 54-PY-28 | P0 | Concurrent writer | Competing ref update between checks or before PATCH cannot be overwritten; record rejected write and retained competing state. |
| 54-PY-29 | P0 | Failure and uncertain write | Inject failures at tree/commit creation, ref patch, readback; distinguish no-write vs uncertain outcome; no second mutation. |
| 54-PY-30 | P0 | Readback transitions | Expected, known-old, absent, unexpected and never-converging observations; bounded retries; no repeated write. |
| 54-PY-31 | P0 | Retirement and restoration | Plan, archive creation, matching archive reuse, conflicting archive refusal; removal/restoration only in disposable explicit simulation; product history intact. |
| 54-PY-32 | P1 | Generated byte and operation cases | Seeded bounded combinations of bytes, modes and lifecycle sequences; capture failing seed; compare exact state invariants. |

### Bash (16)

| ID | Priority | Test family | Expected observation / method |
|---|---|---|---|
| 54-BA-01 | P0 | Linux byte oracle | Use printf/file bytes, git hash-object --no-filters and git cat-file; cmp and sha256sum agree with Python. |
| 54-BA-02 | P0 | Linux original regression | Run pinned original 13 lifecycle tests in clean Ubuntu; independent exit and counts. |
| 54-BA-03 | P0 | Git newline config | core.autocrlf false/true/input in disposable repos; raw object bytes independent of checkout conversions. |
| 54-BA-04 | P0 | Attributes and filters | text/eol=lf/eol=crlf/-text and a benign synthetic filter; distinguish worktree vs stored object bytes. |
| 54-BA-05 | P0 | Mode and file type | Real Git index 100644/100755/symlink mode and tree/gitlink fixtures; verify exact tree and rejection. |
| 54-BA-06 | P0 | Spaces and metacharacters | Paths with spaces, brackets, quotes, dollar and shell glob characters; literal arguments, no evaluation. |
| 54-BA-07 | P1 | Unicode and case | Non-ASCII and case-distinct names, NFC/NFD, explicit locale; preserve names or report unsupported input. |
| 54-BA-08 | P1 | Leading dash and relative path | Explicit argument boundaries and absolute/relative temp roots; no accidental option interpretation. |
| 54-BA-09 | P0 | Native exit propagation | Success, failing git, failed Python and nonzero pipeline stage; no false-green shell. |
| 54-BA-10 | P0 | Output separation | JSON stdout vs stderr diagnostics; no shell banner or progress corrupts machine-readable output. |
| 54-BA-11 | P0 | Fresh/occupied installation CLI | Run actual CLI through injected disposable API harness where necessary; verify install collision refusal and no live access. |
| 54-BA-12 | P0 | Plan/apply/ref invariants | Independent git rev-parse/ls-tree snapshots before/after dry-run, prepared and approved simulated apply. |
| 54-BA-13 | P1 | Dirty or unrelated workspace | Untracked, modified and unrelated repository paths untouched; no cleanup outside fixture. |
| 54-BA-14 | P1 | Permissions and missing tool | Read-only fixture or unavailable git executable; clear nonzero result; no global config or privilege changes. |
| 54-BA-15 | P1 | Timeout and cleanup | Bounded process timeout, interrupted child, cleanup only fixture-owned files; retain diagnostic artifact. |
| 54-BA-16 | P1 | Shell environment isolation | Different cwd, TMPDIR, HOME, inherited Git index/config (controlled); no shared ref or global config mutation. |

### PowerShell (20)

| ID | Priority | Test family | Expected observation / method |
|---|---|---|---|
| 54-PS-01 | P0 | Windows original regression | Re-run pinned original lifecycle suite without repairs and record nine failed identities and first mismatch. |
| 54-PS-02 | P0 | Independent Windows byte oracle | Use .NET byte APIs and Git native commands without text conversion; compare raw content, hash and length to Python. |
| 54-PS-03 | P0 | Native stdin differential | Compare text pipelines, binary stdin, file input; LF, CRLF, mixed and no terminal LF distinguishable. |
| 54-PS-04 | P0 | Native stdout differential | Compare raw byte-stream output with Get-Content/text parsing; do not use latter as integrity oracle. |
| 54-PS-05 | P0 | PowerShell version and encoding | Record actual pwsh, native argument mode, Python UTF-8 settings; verify UTF-8 no BOM, BOM and UTF-16 negative fixtures. |
| 54-PS-06 | P0 | Git core.autocrlf matrix | false/true/input in disposable config; compare object and worktree independently. |
| 54-PS-07 | P0 | Git attributes and filters | text/eol LF/CRLF/-text, benign filter; no accidental conversion of raw fixture objects. |
| 54-PS-08 | P0 | Windows modes | core.filemode true/false and explicit index mode; do not infer Git mode from NTFS permissions. |
| 54-PS-09 | P0 | Literal path with spaces/brackets | Use literal paths and argument arrays; verify correct temp file and no wildcard expansion. |
| 54-PS-10 | P0 | Unicode path and content | Accented, CJK, emoji and combining marks; correct bytes; record actual supported filesystem behavior. |
| 54-PS-11 | P1 | Case collision | Case-only Git paths in bare object fixture; worktree case-insensitive collisions rejected/handled explicitly, never silent overwrite. |
| 54-PS-12 | P1 | Reserved/path limits | Reserved names, trailing dots/spaces and long path boundary only in disposable safe fixture; report unsupported cases, no OS setting changes. |
| 54-PS-13 | P1 | Drive and separator handling | Absolute/relative paths, drive letter case, backslash/slash and nested working directory; resolve same intended fixture. |
| 54-PS-14 | P0 | Native quoting | Empty args, spaces, apostrophes, backslashes, literal bracket and leading-dash values; compare argv captured by helper. |
| 54-PS-15 | P0 | Exit-code propagation | Capture LASTEXITCODE immediately; intentional git/Python failure, stderr-only success, pipeline failure never become green. |
| 54-PS-16 | P0 | Stdout and stderr separation | JSON parsed separately; binary evidence unaffected by stream merging; diagnostic retained. |
| 54-PS-17 | P0 | Windows lifecycle parity | Fresh install, plan, prepared upgrade, authorized simulated apply, archive and restoration; exact Git trees/refs match expected. |
| 54-PS-18 | P0 | Tamper negative control | Independently change raw bytes/newline or Git index mode; verify rejection and untouched refs. |
| 54-PS-19 | P1 | File lock and cleanup | Exclusive file lock/failed deletion/temporary path in use; bounded failure, no unrelated cleanup; no admin privileges. |
| 54-PS-20 | P1 | Process/environment isolation | NoProfile, controlled TEMP/TMP, inherited Git variables and bounded child timeout; no persistent user or runner setting changes. |

### Shared evidence (12)

| ID | Priority | Test family | Expected observation / method |
|---|---|---|---|
| 54-EV-01 | P0 | Exact pin | Verify vault and product SHAs and clean checkout at start and end; record tree identity; refuse mismatch. |
| 54-EV-02 | P0 | Known-bad control | Original failing revision reproduces on Windows; no reinterpretation as pass; isolate first failure. |
| 54-EV-03 | P0 | Known-good control | Binary-safe fixture and valid pinned package accepted on both OSes; actual repair must be separately approved. |
| 54-EV-04 | P0 | Deliberate false-green controls | No-op, zero tests, skipped, unexpected success, expected failure and nonzero exit cannot satisfy required cases. |
| 54-EV-05 | P0 | Inventory identity | Each planned case has unique ID; expected case identities exactly match executed set, not count alone. |
| 54-EV-06 | P0 | Receipt binding | Wrong SHA, run/attempt, case plan hash, runtime/OS, stale/duplicate/missing receipt rejected. |
| 54-EV-07 | P0 | Artifact verification | Upload logs, plans, verdicts, hashes, binary probes and sanitized diagnostics even on failure; independently verify ZIP digest and payload hash. |
| 54-EV-08 | P0 | Cross-platform parity | Same raw fixture corpus and expected blob identities; compare semantic outputs and intentional platform distinctions, not timestamp-dependent commit SHA. |
| 54-EV-09 | P0 | Graphify traceability | Map #54 to case IDs, source functions, runner jobs and exact evidence; validate no dangling/duplicate mappings; no Graphify claim before fresh run. |
| 54-EV-10 | P0 | Isolation audit | Read-only CI token, no persisted credentials, no live network mutations, before/after fixture refs and product checkout verified. |
| 54-EV-11 | P1 | Repeated runs | Three fresh independent runs after repair on each OS; keep failed attempts and classify flakiness, never erase history. |
| 54-EV-12 | P1 | Bounded generated/mutation audit | Seeded fixture variations, remove each key protection in disposable copies to verify negative controls fail; map killed/surviving mutations, no product edits. |

## Execution order and constraints
1. Capture original evidence and isolate first mismatching path, expected/actual mode, byte length, first differing byte, Git blob ID, raw SHA-256; run same LF fixture on both platforms with text and binary I/O. Compare independently against git hash-object --no-filters / git cat-file, never against normalized Git show strings. Source bytes and worktree bytes are different contracts.
2. Develop minimal red/green reproducer only after owner approval. Decide fixture-only vs product vs both; retain old failing trace and genuine-tampering rejection. No tests may repair product by monkeypatching away integrity checks. Use disposable copies and fake API transport; actual CLI tests that need an API use a test injection seam or local controlled transport, never the live endpoint for writes.
3. Execute all P0 families, map existing tests to identities and add missing coverage; rerun existing 112 baseline tests plus new selected cases on ubuntu-24.04 and windows-latest (Python 3.12, Bash on Ubuntu, pwsh on Windows). Pin exact runner image/tool versions in evidence; standard hosted public runners, contents read, persist-credentials false, fail-fast false, per-platform artifact names, bounded timeouts. Expand P1 via pairwise/seeded combinations, not Cartesian explosion. Windows older shell/UNC/admin-only features outside supported scope unless separately authorized.
4. Run independent negative controls for bytes/modes and false-green receipts. Record exact product/vault SHAs, case IDs, run/attempt, OS/runtime/Git configuration, logs, raw synthetic probe bytes/digests, tree snapshots, artifact SHA-256, and read back evidence. Graphify map case-to-code-to-proof as a separate check; historical map rebuild is not proof of #54.
5. Internal audit distinguishes test-fixture defect, product defect and evidence defect. A P0 failure blocks #54 acceptance; unrelated confirmed bugs get separate scope. P1 cases that cannot run documented with rationale, no false pass. Head/owner controls integration and closure. Other three agents' refs/claims/releases remain untouched.

## Primary references
- [Python 3.12 subprocess](https://docs.python.org/3.12/library/subprocess.html) and [I/O](https://docs.python.org/3.12/library/io.html): text vs binary conversion.
- [Git hash-object](https://git-scm.com/docs/git-hash-object), [cat-file](https://git-scm.com/docs/git-cat-file), [attributes](https://git-scm.com/docs/gitattributes), [config](https://git-scm.com/docs/git-config): object bytes and checkout policy.
- [PowerShell redirection](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_redirection), [native parsing](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_parsing), [Windows paths](https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file): byte streams, argument passing, path constraints.
- [GitHub runner choice](https://docs.github.com/en/actions/how-tos/write-workflows/choose-where-workflows-run/choose-the-runner-for-a-job), [workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax), [artifact verification](https://docs.github.com/en/actions/tutorials/store-and-share-data): CI isolation and evidence.
