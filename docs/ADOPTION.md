# Provenistem — Standalone adoption guide (v0.0.2)

**Purpose:** track project Ideas & Features and their status/progress, nothing broader. See [the owner-locked product scope](PRODUCT-SCOPE-LOCK.md).

## Zero-install copy
**This is a draft procedure; it is not a receipt for a completed fresh-adopter test.** Before copying, inspect the host's governing instructions, existing `ideas/`, `features/`, `templates/`, `tools/`, and target paths. Select a new isolated destination or stop for human-owned reconciliation; do not merge independent canonical registries automatically.

Use GitHub's web UI, Git, or whatever file tooling is already available. Copy `ideas/` and `features/` from this branch as a single isolated library root into an explicitly authorized separate host project. Keep the blank `records/` folders (represented by `.gitkeep`). Copy `templates/` **when using the example-file steps**; otherwise create records manually according to the schemas. Optionally copy the guide, `tools/`, `tests/` and docs into that same root so relative paths remain valid.

**Never overwrite** an existing host file or `AGENTS.md`. Stop and reconcile if a directory already exists or an ID conflicts. No account credentials, cloud API, plugin, hosted service, local runner, Python package or new execution environment is necessary for record storage or browsing.

## Host-local records
Each adopter starts at `IDEA-000001` / `FEAT-000001` in its own repository, with its own evidence, metadata and approvals. IDs are scoped **to the host repository**, not globally. Host paths are relative; do not link to another project's private data or inherit its record status.

Examples are stored in `templates/`, never in `*/records/`. Remove example-only placeholders before declaring a record meaningful. Update the two indexes manually or with the optional tool.

## Optional validation
If Python 3 is already available, the dependency-free `tools/library.py` helper offers `check` and `build` actions; `tests/` provides offline regressions. For a populated host use `python tools/library.py check` (never `--expect-empty`). In v0.0.2, `python tools/adopter.py <host-library-root>` produces a **read-only, non-mutating** per-file upgrade plan. `SAME` files are unchanged; `KEEP_HOST` protects canonical records/indexes; `REVIEW_LOCAL_DIFFERENCE` requires host-controlled field-by-field reconciliation; `ADD` means absent but is not permission to copy. Nothing is installed or modified by the planner. Local schema additions must be retained, not overwritten. **Do not run this helper on untrusted or concurrently writable filesystems with elevated permissions.** Symlink checks are preflights, not atomic anti-race guarantees. Each new adopting repository must run its own host-specific checks; the source's accepted test receipts and two prior adopter checks do not certify every future installation. The optional helpers are not installed by default, are not a runtime dependency, and do not grant authority.

## Scope of this package
Provenistem is an isolated, optional Ideas + Features product. Installing it does **not** install, configure, update, or authorize any other framework or project. A separate control plane may offer it through an optional host-owned adapter, but no automatic install, merge, CI provisioning, host README replacement or policy mutation is part of adoption.
