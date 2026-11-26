# ITQS 400-case planning catalogue

400 unique IDs and exact normalized scenario titles, not 400 new tests. Each row names a fixture class, expected behavior, existing native-suite search location and required evidence. Cross-category overlap (e.g. replay and crash recovery) must reuse actual case IDs before implementation; do not credit redundant executions as distinct proofs. Some rows are limitation/disclosure checks rather than runtime assertions. Existing 85 strict subcases are independently executed and not added to this count. No release or checkpoint allocation.

| Batch | Planned rows | Native reuse candidates |
|---|---:|---|
| 01 Origin | 24 | test_contention_recovery.py;test_transaction_confirmation.py |
| 02 API | 48 | test_api_boundaries.py;test_install.py;test_gate.py;test_standard.py |
| 03 Isolation | 24 | test_issue_isolation.py;test_parallel_handoff.py;test_session.py |
| 04 Allocation | 32 | test_checkpoint.py;test_parallel_handoff.py;test_vib53_qualification.py |
| 05 Atomicity | 24 | test_transaction_confirmation.py;test_contention_recovery.py;test_session.py |
| 06 Restart | 32 | test_contention_recovery.py;test_transaction_confirmation.py;test_vib53_qualification.py |
| 07 Replay | 24 | test_transaction_confirmation.py;test_contention_recovery.py;test_session.py |
| 08 Contention | 24 | test_contention_recovery.py;test_vib53_qualification.py |
| 09 History | 20 | test_merge_history.py;test_release_checkpoint_mapping.py;test_checkpoint.py |
| 10 Evidence | 28 | test_gate.py;test_standard.py;test_graphify_evidence.py;test_acceptance_snapshot.py |
| 11 Authority | 20 | test_session.py;test_standard.py;test_gate.py;test_install.py |
| 12 Legacy | 20 | test_lifecycle.py;test_install.py;test_session.py;test_vib53_qualification.py |
| 13 Portability | 16 | test_install.py;test_lifecycle.py;test_vib53_qualification.py |
| 14 Efficiency | 16 | test_vib53_qualification.py;test_contention_recovery.py |
| 15 Adversarial | 32 | test_contention_recovery.py;test_transaction_confirmation.py;test_graphify_evidence.py |
| 16 Lifecycle | 16 | test_vib53_qualification.py;test_post_merge.py;test_live_acceptance.py |

See `catalog.json` for the complete individual case map. This planning-only branch is not a runnable qualification result.
