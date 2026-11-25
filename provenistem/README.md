# Provenistem — v0.0.2

**Product:** Provenistem · **Versioning:** independent · **Mode:** portable, standalone and optionally host-integrated. Governance-Branch can offer a separately authorized optional adapter without becoming dependent on Provenistem; Provenistem does not require Governance. This branch documents a future neutral package contract and does not republish the historical v0.0.2 release.

The earlier v0.0.1 design remains a historical baseline; the v0.0.2 private tag is immutable. See the [product-neutral provenance boundary](docs/PROVENANCE.md) and [owner-locked optional integration rules](docs/PORTABILITY-AND-MODULE-CONTRACT.md). Internal development audit reports and CI machinery are excluded from portable packages.

**Provenistem is a portable Ideas & Features tracker for any project.** Record ideas and features, connect related items, and follow their status and development progress. Decision, origin, testing and evidence-reference fields are supporting tracking details—not a broader governance or verification product. [This simple scope is owner-locked.](docs/PRODUCT-SCOPE-LOCK.md)

Provenistem contains exactly two portable record libraries:

- [Ideas](ideas/README.md): possibilities, pros/cons, reasons, exploration, and human decisions.
- [Features](features/README.md): stable capability identities, implementation status, scoped evidence, and references to ideas.

A human can use the files directly in GitHub. An LLM can read and suggest edits by following [the agent guide](LIBRARY-AGENT-GUIDE.md). No plugin, Governance installation, cloud service, runner, Python, or local environment is required to *use the records*.

**The upstream starter starts empty.** `ideas/records/` and `features/records/` intentionally contain no real adopter records. Documents in `templates/` are synthetic examples only, never canonical project data.

## Quick use (GitHub website only)

1. Copy `README.md`, `LICENSE`, `LIBRARY-AGENT-GUIDE.md`, `ideas/`, `features/`, `docs/`, and `templates/` into one isolated, collision-free library root. Select the reviewed clean portable starter as the copy source, not a populated host catalog. The agent guide and examples are optional to use; retain the files for working relative links. Preserve the [MIT license](LICENSE) and its copyright and permission notices. Never overwrite existing paths. See [adoption instructions](docs/ADOPTION.md).
2. For a new idea, copy [the example](templates/idea.example.json) into `ideas/records/IDEA-000001.json`, edit its ID, title, and facts. For a new feature, use [the feature example](templates/feature.example.json) at `features/records/FEAT-000001.json`. Use the next unused ID, never recycle an ID.
3. Link features to existing ideas by `idea_ids`; keep decisions, implementation, tests, and release claims separate.
4. Edit or regenerate `INDEX.md` as a **read-only view** of records; records always prevail if an index becomes stale. An optional standard-library-only Python helper can validate and generate indexes, but is *not required*.

For optional validation add `tools/`; for optional tests also add `tests/` to the complete basic copy. From the library root (for this nested layout, `cd provenistem` from the host repository root), use `python tools/library.py check` for record/index validation and `python tools/library.py build` only when authorized to regenerate derived indexes. Run `python -m unittest discover -s tests -v` only in a clean, isolated starter or synthetic test copy with empty canonical record directories. Do not run the full source-distribution regression suite against a populated host or remove its records to satisfy a test. Only a clean starter uses `python tools/library.py check --expect-empty`. Python is optional for manual record use. The read-only `python tools/adopter.py <host-library-root>` planner does not authorize copying or overwriting; reconcile host differences first.

### Exact numeric identity (forward repair)

The optional validator preserves exact decimal literals when parsing JSON for value identity, including `uniqueItems`. Numerically equal values (such as `1` and `1.0`) remain equal; booleans remain distinct. Nonfinite and excessive decimal exponents are rejected. The existing v1 schema types remain object, array, string and integer; this repair does not enable a new `number` schema type or loosen integer validation.

No GitHub Actions workflow, runner configuration, release authorization, or development test-arm file is included in this portable package. Any CI is optional and host-owned. Prior source/host test receipts do not imply independent external security certification.

## One-way Governance isolation

[The interoperability boundary](docs/ONE-WAY-BOUNDARY.md) allows Governance-Branch to *offer* Provenistem as an opt-in, host-owned module, but forbids mandatory dependencies, upstream mutations, silent installation, schema conversion and overwriting canonical `ideas/` or `features/` paths. The adapter is a future design, not a shipped integration.

## Authority and trust

An idea is not approval to implement. A feature record is not permission to run a tool, proof of test success, or evidence of release. This library never supersedes project owner decisions, `AGENTS.md`, code owners, protected branches, official release records or external acceptance gates.

Only an actual project's release authority can assert shipped versions. The template's `release_membership` field must stay `NOT_ASSERTED`. Evidence references and SHAs are *claims to independently check*, not authenticated receipts.

## Read next

- [Library agent guide](LIBRARY-AGENT-GUIDE.md)
- [Lifecycle and state meanings](docs/LIFECYCLE.md)
- [Zero-install adoption](docs/ADOPTION.md)
- [Isolation / threat boundaries](docs/ISOLATION.md)
- [Provenance and source separation](docs/PROVENANCE.md)

Provenistem version: `0.0.2`; frozen experimental library baseline: `0.0.1`. Neither is the adopting project's product version. A private GitHub release must refer to the exact 24-file package commit, not the larger development branch.

## Owner-approved engineering ecosystem laws

Decision ENGINEERING-ECOSYSTEM-LAWS-001 (2026-11-24). Mission: Build a toolkit that gives compatible LLM agents a structured engineering environment, rather than building another AI model.

<!-- engineering-laws:start -->
1. **Independence:** Every tool must remain independently installable, usable, versioned and maintained.
2. **Composability:** Installing additional tools expands the agent's capabilities without creating mandatory dependencies.
3. **Portability:** No mandatory AI provider, model, agent harness or paid execution service.
4. **Persistence:** Project knowledge, decisions, progress and evidence survive the termination of an AI session.
5. **Verification:** Development claims must be supported by reproducible, revision-bound evidence.
6. **Owner authority:** The human retains control over scope, architectural decisions, integration and releases.
<!-- engineering-laws:end -->

Remain standalone. Other tools are optional; their absence must not block normal operation. Preserve project-local authority and evidence; never automatically install, merge, synchronize or write to another tool's branch. No mandatory seventh coordinator, paid service or AI provider. Existing product scope remains authoritative. Change these laws only by explicit owner approval.

## Branch-local library boundary

Read the local catalog at the library root in the adopting workspace. Resolve its actual repository, branch and revision before citing records. This nested copy is an optional library, not a standalone branch discovery marker. Read-only discovery does not authorize writes. Preserve local records and prior receipts; no automatic cross-branch installation, synchronization, integration or release.
