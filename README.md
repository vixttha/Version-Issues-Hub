# Version-Issues-Hub

Version-Issues-Hub tracks accepted GitHub issues as numbered development checkpoints. VIB follows the issue, the exact tested revision, and the evidence back to the owner's integration decision.

Each issue version starts with its baseline project version. Issue versions `v0.0.0.1` onward build toward `v0.0.1`. Once `v0.0.1` is complete, issue versions `v0.0.1.1` onward build toward `v0.0.2`.

Start with [the issue-version ledger](ledger/issue-versions.json), [the checkpoint guide](docs/v0.0.0.1.md), and [issue #1](https://github.com/vixttha/Version-Issues-Hub/issues/1) for the first verification record.


Standalone branch installation candidate: [v0.0.0.3](docs/v0.0.0.3.md). VIB owns its package and workflow independently of other templates.

Agent package: [v0.0.0.4](docs/v0.0.0.4.md), including batched handoffs in [WORKFLOW.md](install/branch/WORKFLOW.md). Owner-enabled [merge gate candidate](install/branch/GATE.md) is not live enforcement; Standard VIB is the default; the disposable GitHub pilot gates only optional hard enforcement. See [standard validation](install/branch/STANDARD.md).

## Engineering ecosystem

[Owner-approved six architectural laws](ENGINEERING-LAWS.md) apply to this product. Standalone operation and owner authority remain unchanged. The product has no mandatory coordination-tool dependency.

## Agent capability discovery — v1

<!-- agent-capability:v1
{"schema_version":1,"id":"vib","branch":"Version-Issues-Hub","entrypoint":"AGENTS.md","scope":"Issue-version checkpoints, handoffs and owner decisions","required_ecosystem_tools":[],"authority":"owner","discovery":"read-only","versioning":"independent"}
-->

A compatible agent may enumerate the target repository's branch refs, resolve this branch to a commit, and read its entry point at that exact commit. Read-only discovery confers no execution, write, integration or release authority. If this branch or marker is absent, the tool is absent or legacy/unverified; continue independently. Check the target's own instructions and owner scope before any action. The marker describes a capability, not a required registry or package version.

Installation convention: human or agent selects a reviewed exact source SHA, checks the dedicated target branch and collisions, follows this product's own installation guide, and records source/target SHA and preserved product state. Never merge a template workspace wholesale into product source. Existing installations require explicit reviewed upgrades; preserve local records and prior receipts. Optional evidence links do not authorize writes. No mandatory coordinator or other ecosystem tool.
