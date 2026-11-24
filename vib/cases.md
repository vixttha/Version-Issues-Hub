# VIB project cases

| Case | Area | Priority | Suggested implementation | Expected outcome |
|---|---|---|---|---|
| VIB-001 | Issue ledger and receipts | P0 | Python unittest (test_checkpoint.py) | Stable issue versions and exact evidence receipts. |
| VIB-002 | Standalone install | P0 | Python unittest (test_install.py) | Isolated install and collision rejection. |
| VIB-003 | Agent handoff | P0 | Python unittest (test_session.py) | Single-worker handoff and stale-state rejection. |
| VIB-004 | Standard validation | P0 | Python unittest (test_standard.py) | Advisory evidence checks fail closed without merge authority. |
| VIB-005 | Optional gate | P1 | Python unittest (test_gate.py) | Mocked trusted gate protocol; no live enforcement claim. |
| VIB-006 | Lifecycle | P0 | Python unittest (test_lifecycle.py) | Safe upgrade, archive and preservation regression. |
| VIB-007 | Snapshot recovery | P0 | Python unittest (test_acceptance_snapshot.py) | Concurrent snapshot recovery regression; not an LLM trial. |
