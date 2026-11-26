# Lydite Test Vault Template

**A mechanical touchstone for software. Put your code against the stone and prove it works.**

## Why Lydite?

Historically, *lydite* was a dense black stone used as a touchstone. Drag metal across it, and the physical mark left behind proved whether it was pure or counterfeit—no assumptions, no trusting claims.

This template is the stone; your code is the metal. Instead of relying on "it works on my machine" or vague checklists, a Lydite test vault turns project claims into repeatable, mechanically verified proof.

## Start here

- [Browse the language folders](languages). Each folder has `metadata.json`, `GUIDE.md`, and `tests/`.
- [Install the original copy-in starter](starter/test-vault/README.md) to adopt the catalog and receipt verifier in an existing project.
- [Read the migration audit](docs/migration-audit.md) for what came from AlderVale and Blender-Agent.
- [Browse the historical versions](versions/README.md) for the original template snapshots.
- [Review the standalone release candidate](docs/release-candidate.md) for the draft changelog and validation record.

Run `python tools/inventory.py` from the repository root to see each language, runtime, runner, declared case count, and test-file count. The inventory validates the metadata against files on disk. Each case holds its purpose, test path, and command arguments. Language folders include a small runnable example that you can adapt to your own project's entry point.

A **declared case** is one named behavior in the metadata. Several assertions can belong to one case. A **runner result** records the case outcome for the checkout and environment that actually ran it. See the [test guide](docs/testing.md) for the workflow.

## License

Lydite is available under the [MIT License](LICENSE). Include a copy of the license when you copy the starter or examples into another project. Third-party dependencies and linked projects have their own license terms.

## VIB project Test Vault

[Agent 4 operating scope](vib/AGENT-4.md) · [Permanent language responsibilities](vib/language-roles.md) · [Adoption and baseline history](VIB-ADOPTION.md).

[Project cases](vib/cases.md) · [Pinned plan](vib/plan.json) · [Runner](vib/run_cases.py). This workspace tests a separately pinned product checkout; the original template language tests remain separate.

## Engineering ecosystem

[Owner-approved six architectural laws](ENGINEERING-LAWS.md) apply to this product. Standalone operation and owner authority remain unchanged. The product has no mandatory coordination-tool dependency.

## Agent capability discovery — v1

<!-- agent-capability:v1
{"schema_version":1,"id":"lydite","branch":"Lydite-Test-Vault","entrypoint":"README.md","scope":"Test catalog and execution receipts","required_ecosystem_tools":[],"authority":"owner","discovery":"read-only","versioning":"independent"}
-->

A compatible agent may enumerate the target repository's branch refs, resolve this branch to a commit, and read its entry point at that exact commit. Read-only discovery confers no execution, write, integration or release authority. If this branch or marker is absent, the tool is absent or legacy/unverified; continue independently. Check the target's own instructions and owner scope before any action. The marker describes a capability, not a required registry or package version.

Installation convention: human or agent selects a reviewed exact source SHA, checks the dedicated target branch and collisions, follows this product's own installation guide, and records source/target SHA and preserved product state. Never merge a template workspace wholesale into product source. Existing installations require explicit reviewed upgrades; preserve local records and prior receipts. Optional evidence links do not authorize writes. No mandatory coordinator or other ecosystem tool.
