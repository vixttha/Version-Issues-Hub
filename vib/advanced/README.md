# Batches 7–16 — advanced qualification

Pinned product 7ae6626e44d01d29b11968da28e6debd816f8c06. Baseline 621 named checks; 1066/1084 prior executions passed. No product or live branch changes. Separate public-runner workflow. Frozen exact test identities; fail on real failures, preserve reports. Python 103 named cases; Bash 8 and PowerShell 8 platform cases. No count inflation for generated inner operations.

| Batch | Scope | Python cases |
|---|---|---:|
| 10 | ZIP controls and repeatable bytes | 8 |
| 11 | HTTP retry/permission and loopback transport | 23 |
| 12 | Filesystem links and errors | 3 |
| 13 | Selected mutations | 4 |
| 14 | Actual historical package blob/ancestry checks | 3 |
| 15 | Cumulative growth and process kill/restart | 4 |
| 16 | Frozen independent byte vectors | 1 |
| 07 | Coverage instrument and false-green probes | 4 |
| 08 | Full five-factor Boolean matrix and six event permutations | 38 |
| 09 | Seeded properties and strict JSON probes | 15 |

Limitations: measured coverage is baseline and advanced in-process Python, excludes uninstrumented subprocesses and prior vault suites; not full product coverage. Sequence matrix is bounded. Historical checks validate actual package identities, not complete migration matrix. Process termination is at explicit before/after publication barriers, not mid-system-call durability. Prior ZIP job verifies two exact artifacts and their embedded logs/receipts; old auditor does not establish independent historical IDs. No live agent or service qualification. Benchmark budgets exploratory. Sources: https://coverage.readthedocs.io/en/latest/branch.html ; https://csrc.nist.gov/pubs/sp/800/142/final ; https://docs.python.org/3/library/json.html ; https://docs.github.com/en/rest/actions/artifacts ; https://git-scm.com/docs/git-worktree .

Second revision: repaired two incorrectly captured mutation functions; explicit non-assert baseline guards, frozen baseline and core case-ID catalogs from exact prior logs (both OS agree on Python IDs), log hashes and shell receipts; prior ZIP connector readback receipt. Five product strict JSON/HTTP failure probes remain red. Prior ZIP automated job manual only after rate limit; independent readback already verified both archives. Inventory unchanged.
