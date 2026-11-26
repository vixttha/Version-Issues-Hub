# Standard VIB — safe lifecycle

## Upgrade and retirement contract

Use the owner-approved source pin and exact current installed branch SHA. Both operations are read-only plans by default. No product branch or protection settings are changed. Only apply after explicit owner approval and a reviewed plan. Do not run while a worker is active, closure is pending, or hard enforcement is enabled. By default, a staged issue awaiting reconciliation blocks upgrade and retirement. The explicit closure-capability upgrade below is an exception for package-only compatibility; it is never a retirement or integration exception.

```sh
python -m tools.lifecycle --target OWNER/REPO --expected-sha STATE_SHA upgrade --source-sha NEW_SOURCE_SHA
python -m tools.lifecycle --target OWNER/REPO --expected-sha STATE_SHA prepare-retirement
```

Add --apply --owner-approved to the selected subcommand only after review. Run from the new reviewed package checkout for upgrades. Upgrade checks that the new source descends from the old source, refuses removed package paths and collisions with adopter files, preserves all existing state and unrelated leaf objects byte-for-byte, and checks the proposed tree before a non-force ref update. Re-read after any ambiguous failure. The expected SHA is a cooperative stale-write guard; serialize owner lifecycle work with other writers and do not force-update refs. The new installation pin is recorded in the manifest, while older pins and states remain in Git history.

Retirement preparation creates a durable archive/vib/STATE_SHA ref at the exact validated installation state and verifies it. It **never deletes** the dedicated branch. If the owner later chooses to remove the installation, freeze all writers, recheck the archive and current SHA, retain evidence and external artifact backups, and delete only the exact dedicated branch via a separately authorized operation. Never delete a product or other template branch. If anything advanced, repeat archival preparation at the new SHA. Archiving Git history does not preserve expiring Actions artifacts automatically.

Phase 4 evidence: unit tests exercise real disposable Git repositories through a simulated GitHub API on public runners. This proves tree/commit/ref preservation under the tested conditions, not live GitHub retirement or an independent agent trial. No live adopter upgrade or deletion is implied.

### Alternative transport after a ref-update failure

If the GitHub REST ref mutation is unavailable, a separately owner-approved `upgrade --source-sha NEW --apply --owner-approved --prepare-only` creates and checks only the new tree and child commit. It does not move a ref. Inspect the returned exact expected old SHA, prepared SHA and tree; recheck repo identity, active work, product and installed refs. An authorized GitHub connector can advance only the dedicated ref with the exact old SHA as its lease and force disabled. Independently verify the prepared commit parent, full tree and unchanged adopter-state blobs after readback. Never automatically retry a failed mutation or fall back to a different transport without checking the actual state. This is a supported alternative path, not a claim that GitHub's REST PATCH outage has been fixed.

### Staged-preserving closure capability upgrade (reviewed opt-in)

For singleton installations whose staged PRs remain open and unmerged, an owner may review a package-only closure-capability upgrade without falsely integrating staged issues. Use the new reviewed source and exact installed SHA:

```sh
python -m tools.lifecycle --target OWNER/REPO --expected-sha STATE_SHA upgrade --source-sha NEW_SOURCE_SHA --preserve-staged
```

The read-only plan binds the source, installed SHA, product SHA, every staged issue/version, latest archive digest, original fix/candidate, PR identity and observed current head. Historical candidates must be ancestors of the current same-repository, same-product-target open PR. Old evidence is not refreshed or promoted. If the owner reviews the plan, pass `--staged-scope-sha256 DIGEST --apply --owner-approved`; prefer `--prepare-only` for independent tree review before any authorized ref movement. A changed scope, unsupported package, active work, pending closure, closed or foreign PR, non-descendant head, or changed product/installed ref refuses. The default guard and retirement refusal remain intact. Package-only upgrade preserves staged ledger and handoff bytes exactly; staged integration still needs new exact evidence and owner approval. Recheck the scope and product/installed refs before publication. This is a cooperative, non-atomic cross-API guard, not a production merge or issue closure authorization.
