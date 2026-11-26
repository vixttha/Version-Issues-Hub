# Batch 6 — qualification design (before execution)

Product pin 7ae6626e44d01d29b11968da28e6debd816f8c06. Vault-only; no real repository mutations by tests. Baseline 534 checks, 908/926 passed, nine known failed probes on both OS. 

| ID | Proof | Oracle and stop condition |
|---|---|---|
| Q01 | Install interruption | Fault before/after tree, commit, ref, and readback; no repeated write, preserve product ref |
| Q02 | Stale verification | Reject changed base/head/merge/ref/attempt; state unchanged |
| Q03 | Cross-checkpoint contamination | Explicit per-issue evidence association; shared run allowed only when explicitly linked; unrelated scope unchanged |
| Q04 | Archive restoration | Exact archived Git object and bytes; manual restore in disposable repo; no automatic deletion |
| Q05 | Mutation | Positive baseline, one isolated source edit, assertion failure, restored baseline |
| Q06 | Concurrent filesystem writers | Real Git compare-and-swap and atomic file replacement; no claim of multi-agent support or lossless shared-file writes |
| Q07 | Large ledger | 1k/10k/50k records, binding and allocation correctness, measured wall time/peak Python allocations |
| Q08 | Resource bounds | Bounded input sizes, subprocess timeouts and cleanup; no destructive machine exhaustion |
| Q09 | CLI | Real invalid command invocations with exact exit codes; no file changes or remote access |
| Q10 | Adopter | Fresh synthetic installation, ledger allocation, archive and manual restore; real Git objects and synthetic API |

All tests have positive and negative controls where applicable. Existing red probes remain red. Report suite identity, exact SHA, OS, attempt, logs, digest; no green claim until results observed. Benchmark sizes and budgets are exploratory, not owner-approved SLAs. Sources: https://git-scm.com/docs/git-update-ref.html ; https://docs.python.org/3/library/unittest.mock.html ; https://docs.python.org/3/library/subprocess.html ; https://docs.github.com/en/actions/concepts/billing-and-usage .
