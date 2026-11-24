# Version-Issues-Hub

Standalone VIB branch. Do not merge into the product. Start with [AGENTS.md](AGENTS.md) and [WORKFLOW.md](WORKFLOW.md). The installed package pin and target identity are in [vib-install.json](vib-install.json). The [ledger](ledger/issue-versions.json) and [handoff](ledger/handoff.json) belong to the adopter.

Run `python -m tools.session --target OWNER/REPO inspect` in an authorized cloud host to recover the current state. Merge enforcement is disabled unless separately configured and proven by the owner.

Optional owner-enabled gate: [GATE.md](GATE.md). The candidate is not live enforcement until the disposable ruleset pilot passes.

**Default: Standard VIB.** No GitHub App, rulesets, branch protection, database or external service required. Use [STANDARD.md](STANDARD.md) to review product evidence. Optional hard enforcement is separate and does not block ordinary adoption.

Owner-controlled [upgrade and retirement preparation](LIFECYCLE.md) is dry-run-first; never automatically delete a branch.

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
