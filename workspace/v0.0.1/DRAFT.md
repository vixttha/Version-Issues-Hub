# Version-Issues-Hub

Track each accepted GitHub issue as a stable development checkpoint, connect it to exact source revisions and public verification evidence, and retain the owner's integration decision.

**Development candidate — not a released package.** The default branch is currently a placeholder. The working source is on [the development branch](https://github.com/vixttha/Version-Issues-Hub/tree/plan/v0.0.0.1); this draft describes [the pinned candidate](https://github.com/vixttha/Version-Issues-Hub/tree/ee64cdd7019c3cd279213c490226eb3f89f5fb49).

## How VIB works

Head → Worker → Validate → Internal Auditor → Head. One active Worker; the repository owner controls scope, merges, and releases. Issue versions such as v0.0.0.1 build toward project version v0.0.1. Checkpoint evidence is not proof of integration.

| Task | Start here |
| --- | --- |
| Read the issue/version ledger | [Canonical ledger](https://github.com/vixttha/Version-Issues-Hub/blob/ee64cdd7019c3cd279213c490226eb3f89f5fb49/ledger/issue-versions.json) |
| Review standalone installation | [Installer candidate](https://github.com/vixttha/Version-Issues-Hub/blob/ee64cdd7019c3cd279213c490226eb3f89f5fb49/docs/v0.0.0.3.md) |
| Resume an agent session | [Workflow contract](https://github.com/vixttha/Version-Issues-Hub/blob/ee64cdd7019c3cd279213c490226eb3f89f5fb49/install/branch/WORKFLOW.md) |
| Check development progress | [Draft integration PR](https://github.com/vixttha/Version-Issues-Hub/pull/2) and [issues](https://github.com/vixttha/Version-Issues-Hub/issues) |
| Inspect candidate evidence | [Public Actions run](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45330061978) |

## Verify the candidate

A Git checkout and Python 3.12 are used by the public verification workflow. From the pinned checkout:

```sh
git clone https://github.com/vixttha/Version-Issues-Hub.git
cd Version-Issues-Hub
git checkout --detach ee64cdd7019c3cd279213c490226eb3f89f5fb49
python -B -m unittest discover -s tests -v
```

The public workflow runs the test suite and produces issue-specific receipts and a Graphify evidence map. [Inspect the workflow](https://github.com/vixttha/Version-Issues-Hub/blob/ee64cdd7019c3cd279213c490226eb3f89f5fb49/.github/workflows/verify-checkpoint.yml). No paid or self-hosted runner is required for this public verification path.

## Adoption boundaries

VIB installs on a dedicated `Version-Issues-Hub` branch in an adopter's repository, separately from product source and other templates. The owner selects the package pin and explicitly authorizes installation. The installer and cooperative agent handoff are candidates; fresh harness trials and owner-enabled merge enforcement remain separate acceptance gates. Do not treat this draft as installation approval or a public release.

See [the locked install architecture](https://github.com/vixttha/Version-Issues-Hub/issues/9) and [the staged handoff checkpoint](https://github.com/vixttha/Version-Issues-Hub/issues/11).
