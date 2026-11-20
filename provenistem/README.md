# Provenistem — v0.0.2

**Product:** Provenistem · **Versioning:** independent · **Mode:** portable, standalone and optionally host-integrated. Governance-Branch can offer a separately authorized optional adapter without becoming dependent on Provenistem; Provenistem does not require Governance. This branch documents a future neutral package contract and does not republish the historical v0.0.2 release.

The earlier v0.0.1 design remains a historical baseline; the v0.0.2 private tag is immutable. See the [product-neutral provenance boundary](docs/PROVENANCE.md) and [owner-locked optional integration rules](docs/PORTABILITY-AND-MODULE-CONTRACT.md). Internal development audit reports and CI machinery are excluded from portable packages.

**Provenistem is a portable Ideas & Features tracker for any project.** Record ideas and features, connect related items, and follow their status and development progress. Decision, origin, testing and evidence-reference fields are supporting tracking details—not a broader governance or verification product. [This simple scope is owner-locked.](docs/PRODUCT-SCOPE-LOCK.md)

Provenistem contains exactly two portable record libraries:

- [Ideas](ideas/README.md): possibilities, pros/cons, reasons, exploration, and human decisions.
- [Features](features/README.md): stable capability identities, implementation status, scoped evidence, and references to ideas.

A human can use the files directly in GitHub. An LLM can read and suggest edits by following [the agent guide](LIBRARY-AGENT-GUIDE.md). No plugin, Governance installation, cloud service, runner, Python, or local environment is required to *use the records*.

**Starts empty.** `ideas/records/` and `features/records/` intentionally contain no real adopter records. Documents in `templates/` are synthetic examples only, never canonical project data.

## Quick use (GitHub website only)

1. Copy `ideas/`, `features/`, **and `templates/` if following the examples below** into an isolated, collision-free location in your repository. The agent guide is optional. Never overwrite existing paths. See [adoption instructions](docs/ADOPTION.md).
2. For a new idea, copy [the example](templates/idea.example.json) into `ideas/records/IDEA-000001.json`, edit its ID, title, and facts. For a new feature, use [the feature example](templates/feature.example.json) at `features/records/FEAT-000001.json`. Use the next unused ID, never recycle an ID.
3. Link features to existing ideas by `idea_ids`; keep decisions, implementation, tests, and release claims separate.
4. Edit or regenerate `INDEX.md` as a **read-only view** of records; records always prevail if an index becomes stale. An optional standard-library-only Python helper can validate and generate indexes, but is *not required*.

Run optional checks when Python happens to be available: `python tools/library.py check`, `python tools/library.py build`, `python -m unittest discover -s tests -v`. Copy `tools/` and `tests/` if those helpers are wanted. **v0.0.2 adds count-neutral populated-adopter tests, a bounded validator, local `maxLength` schema support and read-only `python tools/adopter.py <host-library-root>` no-clobber planning.** Starter publishers can also use `python tools/library.py check --expect-empty`; do **not** apply that flag to populated adopters.

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
