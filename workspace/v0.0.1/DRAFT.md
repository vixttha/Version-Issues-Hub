# Version-Issues-Hub-Branch (VIB)

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/vib-logo.svg">
  <img alt="VIB — angular lettermark joined by a three-checkpoint circuit" src="assets/vib-logo-light.svg" width="380">
</picture>

**Every issue. A checkpoint.**  
Build. Verify. Advance.

Issue-linked checkpoints, reproducible verification, and durable agent handoffs for GitHub projects. VIB helps humans and compatible coding agents recover what is being developed, what was tested, and what the owner still needs to decide.

**Development candidate v0.0.0.19 · v0.0.1 not released.** [Pinned source](https://github.com/vixttha/Version-Issues-Hub/tree/114a22196eab578b3053002f8eb7af935b26fe89) · [Draft PR #2](https://github.com/vixttha/Version-Issues-Hub/pull/2) · [Remaining acceptance #37](https://github.com/vixttha/Version-Issues-Hub/issues/37).

## Start here

| I want to… | Start with |
| --- | --- |
| Inspect a project using VIB | [Agent entry point](https://github.com/vixttha/Version-Issues-Hub/blob/114a22196eab578b3053002f8eb7af935b26fe89/install/branch/AGENTS.md) and [session workflow](https://github.com/vixttha/Version-Issues-Hub/blob/114a22196eab578b3053002f8eb7af935b26fe89/install/branch/WORKFLOW.md) |
| Install VIB on my repository | [Standalone installation](https://github.com/vixttha/Version-Issues-Hub/blob/114a22196eab578b3053002f8eb7af935b26fe89/docs/v0.0.0.3.md) and [installed branch guide](https://github.com/vixttha/Version-Issues-Hub/blob/114a22196eab578b3053002f8eb7af935b26fe89/install/branch/README.md) |
| Review a checkpoint | [Issue-version ledger](https://github.com/vixttha/Version-Issues-Hub/blob/114a22196eab578b3053002f8eb7af935b26fe89/ledger/issue-versions.json) and [Standard validation](https://github.com/vixttha/Version-Issues-Hub/blob/114a22196eab578b3053002f8eb7af935b26fe89/install/branch/STANDARD.md) |
| Upgrade or prepare an archive | [Safe lifecycle guide](https://github.com/vixttha/Version-Issues-Hub/blob/114a22196eab578b3053002f8eb7af935b26fe89/install/branch/LIFECYCLE.md) |
| Develop VIB itself | [Public verification workflow](https://github.com/vixttha/Version-Issues-Hub/blob/114a22196eab578b3053002f8eb7af935b26fe89/.github/workflows/verify-checkpoint.yml) and [engineering laws](https://github.com/vixttha/Version-Issues-Hub/blob/114a22196eab578b3053002f8eb7af935b26fe89/ENGINEERING-LAWS.md) |

## First useful action

From a Git checkout with Python 3.12, inspect an installed project's state. The copyable read-only example inspects VIB's own public pilot; for another project replace the target with the authorized repository.

```sh
git clone https://github.com/vixttha/Version-Issues-Hub.git
cd Version-Issues-Hub
git checkout --detach 114a22196eab578b3053002f8eb7af935b26fe89
python -m tools.session --target vixttha/Version-Issues-Hub inspect
```

This is read-only. The pilot has an empty ledger: expect JSON containing `status: head_scope_required`, the exact installed SHA and `owner_merge_required: true`. An active adopter returns its checkpoint and handoff or a scope/blocker status. Read the installed [AGENTS.md](https://github.com/vixttha/Version-Issues-Hub/blob/114a22196eab578b3053002f8eb7af935b26fe89/install/branch/AGENTS.md) before writing anything. Supply authorized GitHub credentials only where necessary; never place them in committed files.

To plan installation into an initialized repository (without writing):

```sh
python tools/install.py --target OWNER/REPO --source-sha 114a22196eab578b3053002f8eb7af935b26fe89 --baseline v0.0.0
```

Use the adopter's actual baseline version, not the example blindly. The owner must review the plan before apply. VIB uses a dedicated `Version-Issues-Hub` branch; never merge this branch into product source. Existing installs use the lifecycle guide instead of reinstalling. A fresh remote self-install passed on the prior pinned package; a fresh cross-repository install is not independently qualified.

## How VIB works

Head → Worker → Validate → Internal Auditor → Head. One active Worker; the owner retains scope, integration and release authority.

Issue versions begin with the project's baseline version: v0.0.0.1, v0.0.0.2 and subsequent checkpoints build toward v0.0.1. After that release, v0.0.1.1 onward builds toward v0.0.2. VIB's package version, the adopter's checkpoint versions and its README workspace version remain independent.

Standard VIB reviews revision-bound evidence without requiring branch protection, a GitHub App, a database or another ecosystem tool. Optional [hard enforcement](https://github.com/vixttha/Version-Issues-Hub/blob/114a22196eab578b3053002f8eb7af935b26fe89/install/branch/GATE.md) is separate, owner-enabled and not live-proven. A passing advisory check is not permission to merge.

## What has been verified

| Capability | Observed evidence |
| --- | --- |
| Candidate regression and evidence graph | 84 tests, 96 nodes/95 edges, 19 checkpoint receipts; [PR run](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45395079231/attempts/1) |
| Live adopter state recovery | [Public-runner recovery](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45395079253/attempts/1) |
| Remote upgrade, archive and recovery ref | [Isolated clouds lifecycle pilot](https://github.com/vixttha/clouds/actions/runs/45357811869/attempts/1); connector ref update, no live deletion |
| Real project use | [AlderVale adoption evidence](https://github.com/vixttha/Version-Issues-Hub/issues/37#issuecomment-7128104225); game checkpoint in development, not accepted integration |
| Fresh remote CLI self-install | [Passed on prior package pin](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45382958376/attempts/1); same-repository only |
| Independent LLM hosts, owner acceptance | Pending [acceptance #37](https://github.com/vixttha/Version-Issues-Hub/issues/37) |

These results apply to the named revisions and test paths, not all hosts or future releases. The public profile was tested on standard GitHub-hosted public runners; no paid execution service is required by Standard VIB.

To verify the pinned product candidate from the checkout above:

```sh
python -B -m unittest discover -s tests -v
```

The command is used by the candidate's public workflow. The linked CI evidence is revision-bound; the separate README review records the clean quickstart replay status.

## Troubleshooting

- `head_scope_required`: no active checkpoint; inspect existing issues before claiming one.
- `blocked_other_active_issue`: finish or explicitly defer the current handoff before another claim.
- `stale_candidate` or an advanced installed SHA: reload the exact branch and reverify. Do not force-update.
- A merged PR with an outstanding handoff needs owner-controlled reconciliation; see [known recovery issue #41](https://github.com/vixttha/Version-Issues-Hub/issues/41).

## Project boundaries

The [six architectural laws](https://github.com/vixttha/Version-Issues-Hub/blob/114a22196eab578b3053002f8eb7af935b26fe89/ENGINEERING-LAWS.md) preserve independence, composability, portability, persistence, verification and owner authority. Provenistem, README HQ and Brand Identity are optional complementary tools; none is a required dependency. No template branch is merged wholesale into the product. See [owner-locked architecture](https://github.com/vixttha/Version-Issues-Hub/issues/9).

Reuse terms: the pinned VIB product tree has no LICENSE file; public visibility does not establish an open-source license. Product reuse terms, brand commercial clearance and release remain separate owner decisions.

[Brand identity and asset provenance](https://github.com/vixttha/Version-Issues-Hub/blob/388c6ef968aa15edf3caa34e9de6819dcda24e7f/brand-identity/08-review/BRAND-LOCK.md). The approved visual master is Circuit Industrial v2; no artwork has been modified for this draft.
