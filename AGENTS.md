# README HQ agent entry point

Use the `readme-hq` branch as the durable workspace when asked to use README HQ. Resolve its commit and the target repository's ref independently. Read the target's applicable instructions, version metadata, and repository rules at the selected ref.

| Request | Work |
| --- | --- |
| Show the versions | Read [the version index](versions/README.md). Return the requested project's HQ and homepage versions with status and pinned links. |
| Inspect a repository | Follow [the audit workflow](audits/README.md). Give ranked findings with source and validation status, then record any reusable discovery with its source evidence. |
| Draft or update a README | Use [the README guide](README-GUIDE.md). Use the external library to help the owner select or adapt suitable techniques, then draft on a working branch and verify the target entry points. |
| Archive or publish a README | Use the guide's version workflow and the target repository's acceptance rules. Return the approved archive and homepage publication evidence independently. |

Use [README-Technique-Library](https://github.com/vixttha/README-HQ/tree/README-Technique-Library) for reusable technique and combination definitions. Compare a new observation with active and retired library records before suggesting an addition. Record the library commit, selected IDs, applicability, and evidence with the target project.

Use the public branch for public-safe evidence and general techniques. Keep private repository identities, original files, and private evidence with the owner. Verify changes with `python3 tools/check_readme_hq.py` and report what was actually tested. The owner decides homepage publication and releases.

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

## Agent capability discovery — v1

<!-- agent-capability:v1
{"schema_version":1,"id":"readme-hq","branch":"readme-hq","entrypoint":"AGENTS.md","scope":"Documentation authoring and version history","required_ecosystem_tools":[],"authority":"owner","discovery":"read-only","versioning":"independent"}
-->

A compatible agent may enumerate the target repository's branch refs, resolve this branch to a commit, and read its entry point at that exact commit. Read-only discovery confers no execution, write, integration or release authority. If this branch or marker is absent, the tool is absent or legacy/unverified; continue independently. Check the target's own instructions and owner scope before any action. The marker describes a capability, not a required registry or package version.

Installation convention: human or agent selects a reviewed exact source SHA, checks the dedicated target branch and collisions, follows this product's own installation guide, and records source/target SHA and preserved product state. Never merge a template workspace wholesale into product source. Existing installations require explicit reviewed upgrades; preserve local records and prior receipts. Optional evidence links do not authorize writes. No mandatory coordinator or other ecosystem tool.
