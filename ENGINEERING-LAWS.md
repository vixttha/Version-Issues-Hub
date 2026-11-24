# Six architectural laws

**Decision ID: ENGINEERING-ECOSYSTEM-LAWS-001 — owner approved 2026-11-24.**

Mission: Build a toolkit that gives compatible LLM agents a structured engineering environment, rather than building another AI model.

<!-- engineering-laws:start -->
1. **Independence:** Every tool must remain independently installable, usable, versioned and maintained.
2. **Composability:** Installing additional tools expands the agent's capabilities without creating mandatory dependencies.
3. **Portability:** No mandatory AI provider, model, agent harness or paid execution service.
4. **Persistence:** Project knowledge, decisions, progress and evidence survive the termination of an AI session.
5. **Verification:** Development claims must be supported by reproducible, revision-bound evidence.
6. **Owner authority:** The human retains control over scope, architectural decisions, integration and releases.
<!-- engineering-laws:end -->

Each product keeps its existing responsibility, canonical records, release history and standalone installation. Optional references may cross product boundaries; references confer no write or release authority. No seventh mandatory coordination tool, shared backend, registration service or runtime dependency is permitted. A compatible agent may discover installed tools through repository navigation or an owner-supplied branch reference; missing tools must not prevent standalone operation. No automatic installation, synchronization or merge of template branches. Existing adopter data and immutable evidence must be preserved. No paid execution is required; use standard GitHub public runners for this project's hosted validation. This contract does not enable branch protection or hard enforcement.

For each candidate, check standalone usage with other ecosystem tools absent, optional coexistence without authority transfer, provider-neutral instructions, exact-revision recovery, reproducible evidence and explicit owner decisions. A documentation check establishes wording parity only; product behavior requires its own tests. Report unsupported capabilities and unverified claims. Change these laws only by explicit owner approval. No release or cross-repository installation is authorized by this decision alone.
