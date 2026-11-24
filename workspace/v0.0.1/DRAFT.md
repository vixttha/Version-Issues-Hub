# Version-Issues-Hub (VIB)

Issue-linked checkpoints, reproducible verification, and durable agent handoffs for GitHub projects. VIB helps humans and compatible coding agents recover what is being developed, what was tested, and what the owner still needs to decide.

**Development candidate v0.0.0.19 · First product release v0.0.1 not yet published.** [Pinned source](https://github.com/vixttha/Version-Issues-Hub/tree/4fc9ac47462101b941ea2f78fc939d42a9de0032) · [Draft PR #2](https://github.com/vixttha/Version-Issues-Hub/pull/2) · [Remaining acceptance #37](https://github.com/vixttha/Version-Issues-Hub/issues/37).

## Start here

| I want to… | Start with |
| --- | --- |
| Inspect a project using VIB | [Agent entry point](https://github.com/vixttha/Version-Issues-Hub/blob/4fc9ac47462101b941ea2f78fc939d42a9de0032/install/branch/AGENTS.md) and [session workflow](https://github.com/vixttha/Version-Issues-Hub/blob/4fc9ac47462101b941ea2f78fc939d42a9de0032/install/branch/WORKFLOW.md) |
| Install VIB on my repository | [Standalone installation](https://github.com/vixttha/Version-Issues-Hub/blob/4fc9ac47462101b941ea2f78fc939d42a9de0032/docs/v0.0.0.3.md) and [installed branch guide](https://github.com/vixttha/Version-Issues-Hub/blob/4fc9ac47462101b941ea2f78fc939d42a9de0032/install/branch/README.md) |
| Review a checkpoint | [Issue-version ledger](https://github.com/vixttha/Version-Issues-Hub/blob/4fc9ac47462101b941ea2f78fc939d42a9de0032/ledger/issue-versions.json) and [Standard validation](https://github.com/vixttha/Version-Issues-Hub/blob/4fc9ac47462101b941ea2f78fc939d42a9de0032/install/branch/STANDARD.md) |
| Upgrade or prepare an archive | [Safe lifecycle guide](https://github.com/vixttha/Version-Issues-Hub/blob/4fc9ac47462101b941ea2f78fc939d42a9de0032/install/branch/LIFECYCLE.md) |
| Develop VIB itself | [Public verification workflow](https://github.com/vixttha/Version-Issues-Hub/blob/4fc9ac47462101b941ea2f78fc939d42a9de0032/.github/workflows/verify-checkpoint.yml) and [engineering laws](https://github.com/vixttha/Version-Issues-Hub/blob/4fc9ac47462101b941ea2f78fc939d42a9de0032/ENGINEERING-LAWS.md) |

## First useful action

From a Git checkout with Python 3.12, inspect an installed project's state. Replace OWNER/REPO with the authorized adopter repository.

```sh
git clone https://github.com/vixttha/Version-Issues-Hub.git
cd Version-Issues-Hub
git checkout --detach 4fc9ac47462101b941ea2f78fc939d42a9de0032
python -m tools.session --target OWNER/REPO inspect
```

This is read-only. An installed project returns its current checkpoint and handoff or an explicit scope/blocker status. Read the installed [AGENTS.md](https://github.com/vixttha/Version-Issues-Hub/blob/4fc9ac47462101b941ea2f78fc939d42a9de0032/install/branch/AGENTS.md) before writing anything. Supply authorized GitHub credentials only where necessary; never place them in committed files.

To plan installation into an initialized repository (without writing):

```sh
python -m tools.install --target OWNER/REPO --source-sha 4fc9ac47462101b941ea2f78fc939d42a9de0032 --baseline v0.0.0
```

Use the adopter's actual baseline version, not the example blindly. The owner must review the plan before apply. VIB uses a dedicated `Version-Issues-Hub` branch; never merge this branch into product source. Existing installs use the lifecycle guide instead of reinstalling. A corrected fresh remote CLI apply still awaits acceptance.

## How VIB works

Head → Worker → Validate → Internal Auditor → Head. One active Worker; the owner retains scope, integration and release authority.

Issue versions begin with the project's baseline version: v0.0.0.1, v0.0.0.2 and subsequent checkpoints build toward v0.0.1. After that release, v0.0.1.1 onward builds toward v0.0.2. VIB's package version, the adopter's checkpoint versions and its README workspace version remain independent.

Standard VIB reviews revision-bound evidence without requiring branch protection, a GitHub App, a database or another ecosystem tool. Optional [hard enforcement](https://github.com/vixttha/Version-Issues-Hub/blob/4fc9ac47462101b941ea2f78fc939d42a9de0032/install/branch/GATE.md) is separate, owner-enabled and not live-proven. A passing advisory check is not permission to merge.

## What has been verified

| Capability | Observed evidence |
| --- | --- |
| Candidate regression and evidence graph | 77 tests, 96 nodes/95 edges, 19 checkpoint receipts; [PR run](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45357923198/attempts/1) |
| Live adopter state recovery | [Public-runner recovery](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45357923129/attempts/1) |
| Remote upgrade, archive and recovery ref | [Isolated clouds lifecycle pilot](https://github.com/vixttha/clouds/actions/runs/45357811869/attempts/1); connector ref update, no live deletion |
| Real project use | [AlderVale adoption evidence](https://github.com/vixttha/Version-Issues-Hub/issues/37#issuecomment-7128104225); game checkpoint in development, not accepted integration |
| Independent LLM hosts and corrected fresh remote install | Pending [acceptance #37](https://github.com/vixttha/Version-Issues-Hub/issues/37) |

These results apply to the named revisions and test paths, not all hosts or future releases. Use standard GitHub-hosted public runners for the verified public profile; no paid execution required.

To verify the pinned product candidate from the checkout above:

```sh
python -B -m unittest discover -s tests -v
```

The command is used by the candidate's public workflow. The complete README onboarding walkthrough has not yet been replayed independently.

## Project boundaries

The [six architectural laws](https://github.com/vixttha/Version-Issues-Hub/blob/4fc9ac47462101b941ea2f78fc939d42a9de0032/ENGINEERING-LAWS.md) preserve independence, composability, portability, persistence, verification and owner authority. Provenistem, README HQ and Brand Identity are optional complementary tools; none is a required dependency. No template branch is merged wholesale into the product. See [owner-locked architecture](https://github.com/vixttha/Version-Issues-Hub/issues/9).

Reuse terms: the pinned VIB product tree has no LICENSE file; do not infer an open-source license from public visibility. Release, reuse terms and publication remain owner decisions.
