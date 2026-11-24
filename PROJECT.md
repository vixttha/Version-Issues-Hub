# Version-Issues-Hub Ideas and Features

Permanent project-local Provenistem workspace, package v0.0.2. This is an adopter library, not the VIB implementation, issue-version ledger, or package authority.

## Existing catalog

- [Ideas](ideas/INDEX.md): six existing historical records.
- [Features](features/INDEX.md): six existing historical records.
- [Agent guide](LIBRARY-AGENT-GUIDE.md) and [adoption instructions](docs/ADOPTION.md).
- Portable package source: [pinned upstream v0.0.2](https://github.com/vixttha/Provenistem/tree/e36fcd6d12633395e9b573228c0797ade9e775b0/packages/provenistem).
- [Prior public catalog validation](https://github.com/vixttha/Version-Issues-Hub/actions/runs/44696174996).

## Current project navigation

The existing records retain their recorded lifecycle states. They are historical planning context, not a live release or implementation verdict. Do not infer VIB completion from them.

| VIB authority | Source |
| --- | --- |
| Owner-locked independent install boundary | [Issue #9](https://github.com/vixttha/Version-Issues-Hub/issues/9) |
| Current development candidate | [Exact source](https://github.com/vixttha/Version-Issues-Hub/tree/ee64cdd7019c3cd279213c490226eb3f89f5fb49) |
| Issue/version assignments and acceptance | [Canonical ledger](https://github.com/vixttha/Version-Issues-Hub/blob/ee64cdd7019c3cd279213c490226eb3f89f5fb49/ledger/issue-versions.json) |
| Agent workflow | [VIB workflow](https://github.com/vixttha/Version-Issues-Hub/blob/ee64cdd7019c3cd279213c490226eb3f89f5fb49/install/branch/WORKFLOW.md) |
| Exact candidate validation | [Public push run](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45330061978) |
| Product integration status | [Draft PR #2](https://github.com/vixttha/Version-Issues-Hub/pull/2) |

## Operating boundaries

Read and maintain this library when the owner explicitly requests Provenistem work. Do not implement VIB or route VIB issue registration, feature requests, handoff state, or release decisions into this catalog. VIB owns those decisions in its own package and GitHub issues. Do not create another permanent Provenistem branch, merge this workspace into main, or republish the upstream template. Keep the six existing records and their evidence intact. Do not copy private records into this public repository.

Run `python tools/library.py check` for this populated installation. The existing public Ubuntu/Windows catalog checks and pinned Graphify catalog build are independent of VIB's product acceptance. The upstream blank starter alone uses `--expect-empty`.
