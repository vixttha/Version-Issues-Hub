# Version-Issues-Hub-Branch (VIB)

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/vib-logo.svg">
  <img alt="VIB — angular lettermark joined by a three-checkpoint circuit" src="assets/vib-logo-light.svg" width="300">
</picture>

**Every issue. A checkpoint.**  
Build. Verify. Advance.

Track GitHub issues as development checkpoints. Recover project state, verify the exact revision tested and hand work back to the owner.

**Status: development candidate v0.0.0.19; v0.0.1 not released.** [Source](https://github.com/vixttha/Version-Issues-Hub/tree/114a22196eab578b3053002f8eb7af935b26fe89) · [Draft PR #2](https://github.com/vixttha/Version-Issues-Hub/pull/2) · [Acceptance #37](https://github.com/vixttha/Version-Issues-Hub/issues/37).

## Start here

- **Inspect a project:** [Agent entry point](https://github.com/vixttha/Version-Issues-Hub/blob/114a22196eab578b3053002f8eb7af935b26fe89/install/branch/AGENTS.md) and [session workflow](https://github.com/vixttha/Version-Issues-Hub/blob/114a22196eab578b3053002f8eb7af935b26fe89/install/branch/WORKFLOW.md).
- **Install VIB:** [Standalone installation](https://github.com/vixttha/Version-Issues-Hub/blob/114a22196eab578b3053002f8eb7af935b26fe89/docs/v0.0.0.3.md) and [installed branch guide](https://github.com/vixttha/Version-Issues-Hub/blob/114a22196eab578b3053002f8eb7af935b26fe89/install/branch/README.md).
- **Review a checkpoint:** [Issue-version ledger](https://github.com/vixttha/Version-Issues-Hub/blob/114a22196eab578b3053002f8eb7af935b26fe89/ledger/issue-versions.json) and [Standard validation](https://github.com/vixttha/Version-Issues-Hub/blob/114a22196eab578b3053002f8eb7af935b26fe89/install/branch/STANDARD.md).
- **Maintain an installation:** [Upgrade, archive and recovery](https://github.com/vixttha/Version-Issues-Hub/blob/114a22196eab578b3053002f8eb7af935b26fe89/install/branch/LIFECYCLE.md).
- **Develop VIB:** [Public verification workflow](https://github.com/vixttha/Version-Issues-Hub/blob/114a22196eab578b3053002f8eb7af935b26fe89/.github/workflows/verify-checkpoint.yml).

## Quickstart

Requires Git and Python 3.12. Inspect VIB's own public pilot without changing repository state.

```sh
git clone https://github.com/vixttha/Version-Issues-Hub.git
cd Version-Issues-Hub
git checkout --detach 114a22196eab578b3053002f8eb7af935b26fe89
python -m tools.session --target vixttha/Version-Issues-Hub inspect
```

Expected result for the empty pilot ledger:

- `status`: `head_scope_required`
- `installed_sha`: the exact installed revision
- `owner_merge_required`: `true`

An active adopter returns its checkpoint and handoff or a scope/blocker status. Read the installed agent instructions before writing. Never commit credentials.

## How VIB works

**Head → Worker → Validate → Internal Auditor → Head.**

One active Worker at a time. The owner retains control of scope, integration and releases.

Issue versions are numbered from the adopter's baseline. For example, `v0.0.0.1` and subsequent checkpoints build toward `v0.0.1`; after that release, `v0.0.1.1` onward builds toward `v0.0.2`. Package, adopter and README versions are independent.

Standard VIB checks evidence without requiring another ecosystem tool, a database, a GitHub App or branch protection. Optional [hard enforcement](https://github.com/vixttha/Version-Issues-Hub/blob/114a22196eab578b3053002f8eb7af935b26fe89/install/branch/GATE.md) is owner-enabled and not live-proven. Advisory checks never authorize a merge.

## Install or maintain

For a new, initialized repository, plan installation from the pinned source checkout above. Replace OWNER/REPO and the example baseline with your authorized target and its actual version.

```sh
python tools/install.py \
  --target OWNER/REPO \
  --source-sha 114a22196eab578b3053002f8eb7af935b26fe89 \
  --baseline v0.0.0
```

This is a dry run. Owner approval is required before applying the plan. The dedicated `Version-Issues-Hub` branch must not be merged into product source. Existing installations use the lifecycle guide instead of reinstalling. A fresh cross-repository CLI install has not been independently qualified.

## Verification evidence

- **Candidate:** 84 regression tests, 96 graph nodes, 95 edges, 19 checkpoint receipts. [Public CI](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45395079231/attempts/1).
- **Live recovery:** [Public adopter state test](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45395079253/attempts/1).
- **Lifecycle:** [Isolated upgrade, archive and recovery](https://github.com/vixttha/clouds/actions/runs/45357811869/attempts/1); connector ref update, no live deletion.
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
- Merged PR with an outstanding handoff: owner-controlled reconciliation; [known recovery issue #41](https://github.com/vixttha/Version-Issues-Hub/issues/41).

## Project terms

The [six engineering laws](https://github.com/vixttha/Version-Issues-Hub/blob/114a22196eab578b3053002f8eb7af935b26fe89/ENGINEERING-LAWS.md) preserve independence, composability, portability, persistence, verification and owner authority. Other ecosystem tools are optional. See [architecture decision #9](https://github.com/vixttha/Version-Issues-Hub/issues/9).

The pinned product tree has no LICENSE file; public visibility is not an open-source license. Reuse terms, commercial clearance and release remain separate owner decisions.

[Brand identity and asset provenance](https://github.com/vixttha/Version-Issues-Hub/blob/388c6ef968aa15edf3caa34e9de6819dcda24e7f/brand-identity/08-review/BRAND-LOCK.md) — Circuit Industrial v2, unchanged.
