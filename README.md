# Version-Issues-Hub-Branch (VIB)

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/vib-logo.svg">
  <img alt="VIB — angular lettermark joined by a three-checkpoint circuit" src="assets/vib-logo-light.svg" width="300">
</picture>

**Every issue. A checkpoint.**  
Build. Verify. Advance.

Track GitHub issues as development checkpoints. Recover project state, verify the exact revision tested and hand work back to the owner.

**Status: licensed development candidate; v0.0.1 on release hold.** [Source](https://github.com/vixttha/Version-Issues-Hub/tree/d1e8e1a922446d137a793d1fded105f427122ec5) · [Accepted licensing candidate #48](https://github.com/vixttha/Version-Issues-Hub/pull/48) · [Acceptance #37](https://github.com/vixttha/Version-Issues-Hub/issues/37).

## Start here

- **Inspect a project:** [Agent entry point](https://github.com/vixttha/Version-Issues-Hub/blob/d1e8e1a922446d137a793d1fded105f427122ec5/install/branch/AGENTS.md) and [session workflow](https://github.com/vixttha/Version-Issues-Hub/blob/d1e8e1a922446d137a793d1fded105f427122ec5/install/branch/WORKFLOW.md).
- **Install VIB:** [Standalone installation](https://github.com/vixttha/Version-Issues-Hub/blob/d1e8e1a922446d137a793d1fded105f427122ec5/docs/v0.0.0.3.md) and [installed branch guide](https://github.com/vixttha/Version-Issues-Hub/blob/d1e8e1a922446d137a793d1fded105f427122ec5/install/branch/README.md).
- **Review a checkpoint:** [Issue-version ledger](https://github.com/vixttha/Version-Issues-Hub/blob/d1e8e1a922446d137a793d1fded105f427122ec5/ledger/issue-versions.json) and [Standard validation](https://github.com/vixttha/Version-Issues-Hub/blob/d1e8e1a922446d137a793d1fded105f427122ec5/install/branch/STANDARD.md).
- **Maintain an installation:** [Upgrade, archive and recovery](https://github.com/vixttha/Version-Issues-Hub/blob/d1e8e1a922446d137a793d1fded105f427122ec5/install/branch/LIFECYCLE.md).
- **Develop VIB:** [Public verification workflow](https://github.com/vixttha/Version-Issues-Hub/blob/d1e8e1a922446d137a793d1fded105f427122ec5/.github/workflows/verify-checkpoint.yml).

## Quickstart

Requires Git and Python 3.12. Inspect VIB's own public pilot without changing repository state.

```sh
git clone https://github.com/vixttha/Version-Issues-Hub.git
cd Version-Issues-Hub
git checkout --detach d1e8e1a922446d137a793d1fded105f427122ec5
python -m tools.session --target vixttha/Version-Issues-Hub inspect
```

Expected result depends on the live pilot ledger:

- `status`: `resume` for an active valid handoff, or `head_scope_required` if idle; stale or reconciled state may return a blocker.
- `installed_sha`: the exact installed revision
- `owner_merge_required`: `true`
- `evidence_verified`: `false` until actual evidence is checked.

The current self-pilot has an active release checkpoint; do not claim or advance it. An active adopter returns its checkpoint and handoff or a scope/blocker status. Read the installed agent instructions before writing. Never commit credentials.

## How VIB works

**Head → Worker → Validate → Internal Auditor → Head.**

One active Worker at a time. The owner retains control of scope, integration and releases.

Issue versions are numbered from the adopter's baseline. For example, `v0.0.0.1` and subsequent checkpoints build toward `v0.0.1`; after that release, `v0.0.1.1` onward builds toward `v0.0.2`. Package, adopter and README versions are independent.

Standard VIB checks evidence without requiring another ecosystem tool, a database, a GitHub App or branch protection. Optional [hard enforcement](https://github.com/vixttha/Version-Issues-Hub/blob/d1e8e1a922446d137a793d1fded105f427122ec5/install/branch/GATE.md) is owner-enabled and not live-proven. Advisory checks never authorize a merge.

## Install or maintain

For a new, initialized repository, plan installation from the pinned source checkout above. Replace OWNER/REPO and the example baseline with your authorized target and its actual version.

```sh
python tools/install.py \
  --target OWNER/REPO \
  --source-sha d1e8e1a922446d137a793d1fded105f427122ec5 \
  --baseline v0.0.0
```

This is a read-only dry run against the accepted licensing candidate, not an instruction to apply it or bypass owner authorization. Read the license and supplemental permission before any installation. The dedicated `Version-Issues-Hub` branch must not be merged into product source. Existing installations use the lifecycle guide instead of reinstalling. A fresh cross-repository CLI install has not been independently qualified.

## Verification evidence

- **Licensed candidate:** 97 regression tests, 111 graph nodes, 110 edges, 22 checkpoint receipts. [Public CI](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45421603402/attempts/1).
- **Live acceptance:** [Exact read-only public job, attempt 2](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45421603459/attempts/2); attempt 1 disconnected before testing. [Technical acceptance](https://github.com/vixttha/Version-Issues-Hub/pull/48#issuecomment-7135985146).
- **Lifecycle:** [Historical isolated upgrade, archive and recovery evidence](https://github.com/vixttha/Version-Issues-Hub/issues/37); the adopter repository is now private; no live deletion.
- **Adoption:** [AlderVale checkpoint evidence](https://github.com/vixttha/Version-Issues-Hub/issues/37#issuecomment-7128104225); not accepted integration.
- **CLI:** [Fresh remote self-install](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45382958376/attempts/1) on a prior package pin, same repository only.

The results are revision-bound, not a guarantee for every host or future release. Independent LLM host trials and owner acceptance remain [open](https://github.com/vixttha/Version-Issues-Hub/issues/37). Standard VIB has no required paid execution service.

Run the pinned candidate's tests:

```sh
python -B -m unittest discover -s tests -v
```

## Troubleshooting

- `head_scope_required`: no active checkpoint; review issues before claiming one.
- `blocked_other_active_issue`: finish or explicitly defer the active handoff.
- `stale_candidate` or an advanced installed SHA: reload and reverify. Never force-update.
- Merged PR with an outstanding handoff: owner-controlled reconciliation; [candidate recovery fix #41](https://github.com/vixttha/Version-Issues-Hub/issues/41).

## Agent capability discovery — v1

<!-- agent-capability:v1
{"schema_version":1,"id":"vib","branch":"Version-Issues-Hub","entrypoint":"AGENTS.md","scope":"Issue-version checkpoints, handoffs and owner decisions","required_ecosystem_tools":[],"authority":"owner","discovery":"read-only","versioning":"independent"}
-->

A compatible agent may enumerate the target repository's branch refs, resolve this branch to a commit, and read its entry point at that exact commit. Read-only discovery confers no execution, write, integration or release authority. If this branch or marker is absent, the tool is absent or legacy/unverified; continue independently. Check the target's own instructions and owner scope before any action. The marker describes a capability, not a required registry or package version.

Installation convention: human or agent selects a reviewed exact source SHA, checks the dedicated target branch and collisions, follows this product's own installation guide, and records source/target SHA and preserved product state. Never merge a template workspace wholesale into product source. Existing installations require explicit reviewed upgrades; preserve local records and prior receipts. Optional evidence links do not authorize writes. No mandatory coordinator or other ecosystem tool.

## Project terms

The [six engineering laws](ENGINEERING-LAWS.md) preserve independence, composability, portability, persistence, verification and owner authority. Other ecosystem tools are optional. See [architecture decision #9](https://github.com/vixttha/Version-Issues-Hub/issues/9).

The accepted licensing candidate includes [PolyForm Strict 1.0.0](https://github.com/vixttha/Version-Issues-Hub/blob/d1e8e1a922446d137a793d1fded105f427122ec5/LICENSE) and [VIB-NOTICE.md](https://github.com/vixttha/Version-Issues-Hub/blob/d1e8e1a922446d137a793d1fded105f427122ec5/VIB-NOTICE.md) together. The scope is limited to rights actually held, preserves prior MIT grants and third-party rights, and includes supplemental permission for authorized unchanged dedicated-branch installations. Technical acceptance is not legal-title or trademark clearance. Independent host acceptance, commercial clearance, product integration and release remain pending. This draft is not approved for publication.

[Brand identity and asset provenance](https://github.com/vixttha/Version-Issues-Hub/blob/388c6ef968aa15edf3caa34e9de6819dcda24e7f/brand-identity/08-review/BRAND-LOCK.md) — Circuit Industrial v2, unchanged.
