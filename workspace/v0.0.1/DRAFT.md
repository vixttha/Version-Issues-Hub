# Version-Issues-Hub

**Track every accepted issue as a versioned development checkpoint. Preserve the evidence. Keep the owner in control.**

VIB is a GitHub-first workflow for humans and coding agents who need durable issue-to-version mapping, repeatable validation and a handoff that can be recovered from the repository.

**Status:** development candidate for v0.0.1; not released. [Source candidate](https://github.com/vixttha/Version-Issues-Hub/tree/83deccb89f048e6aa11726837fff123bdb793e89) · [Draft PR #2](https://github.com/vixttha/Version-Issues-Hub/pull/2) · [Owner review packet](https://github.com/vixttha/Version-Issues-Hub/blob/83deccb89f048e6aa11726837fff123bdb793e89/docs/release-v0.0.1-review.md)

## Start here

| For | First step |
| --- | --- |
| Repository owners | [Standalone installation contract](https://github.com/vixttha/Version-Issues-Hub/blob/83deccb89f048e6aa11726837fff123bdb793e89/docs/v0.0.0.3.md) |
| Coding agents | [Agent entry point](https://github.com/vixttha/Version-Issues-Hub/blob/83deccb89f048e6aa11726837fff123bdb793e89/install/branch/AGENTS.md) and [workflow](https://github.com/vixttha/Version-Issues-Hub/blob/83deccb89f048e6aa11726837fff123bdb793e89/install/branch/WORKFLOW.md) |
| Contributors | [GitHub issues](https://github.com/vixttha/Version-Issues-Hub/issues) and [issue-version ledger](https://github.com/vixttha/Version-Issues-Hub/blob/83deccb89f048e6aa11726837fff123bdb793e89/ledger/issue-versions.json) |
| Reviewers | [Public checks](https://github.com/vixttha/Version-Issues-Hub/actions) and [preserved archive evidence](https://github.com/vixttha/Version-Issues-Hub/tree/829fdfae2ac0e8167d740e1a0ad8e8201295c34e/archives/candidates) |

## How it works

Head → Worker → Validate → Internal Auditor → Head. One active Worker; the owner approves scope, integration and releases.

A baseline project version of v0.0.0 yields issue checkpoints v0.0.0.1, v0.0.0.2 and so on toward project version v0.0.1. A checkpoint records its issue, stable fix revision, candidate revision, acceptance criteria and evidence. Passing tests do not alone imply integration.

## Installation preview

With an authorized GitHub-capable Python 3 host, inspect the exact candidate first. Substitute your own authorized repository and reviewed baseline.

```sh
git clone https://github.com/vixttha/Version-Issues-Hub.git
cd Version-Issues-Hub
git checkout --detach 83deccb89f048e6aa11726837fff123bdb793e89
python tools/install.py --target OWNER/REPO --source-sha 83deccb89f048e6aa11726837fff123bdb793e89 --baseline v0.0.0
```

This command is a dry run. The separately authorized apply creates only the dedicated `Version-Issues-Hub` branch. It refuses existing installations. Do not merge the installed branch into product source. Upgrade and removal require a separate reviewed procedure.

## Verify

```sh
python -B -m unittest discover -s tests -v
```

GitHub public runners produce revision-bound receipts and Graphify evidence. [Previous eight-checkpoint archive validation](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45331511873) applies to its pinned source, not every later commit. Independent agent trials and optional live merge enforcement are separate acceptance questions. Branch protection is intentionally disabled for this project.

## Independent tools, complementary roles

| Tool | Responsibility |
| --- | --- |
| VIB | Issue versions, workflow, acceptance and integration records |
| [Provenistem](https://github.com/vixttha/Version-Issues-Hub/tree/Provenistem) | Ideas and features |
| [Veraphify](https://github.com/vixttha/Version-Issues-Hub/tree/Veraphify) | Revision-bound archive lookup |
| [README HQ](https://github.com/vixttha/Version-Issues-Hub/tree/readme-hq) | Documentation workflow |
| [Lydite Test Vault](https://github.com/vixttha/Version-Issues-Hub/tree/Lydite-Test-Vault) | Test catalog and receipts |

VIB remains independent of Provenistem. They are complementary parts of the same puzzle. Optional references do not transfer authority, install another tool, or establish mandatory dependencies. [Architecture lock](https://github.com/vixttha/Version-Issues-Hub/issues/9).

## Release and license

The current candidate is not a released package or license grant. Do not redistribute it without resolving the project's reuse and licensing terms. Owner approval of the exact release revision is required.
