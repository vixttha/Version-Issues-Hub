# Blender-Agent — README HQ

The permanent documentation workspace for Blender-Agent's public README, version history, review evidence, and publication workflow.

**README HQ baseline:** `v0.0.1` · **Public README:** `v0.0.1` draft, not yet published · **Branch:** `readme-hq`

| Area | Purpose |
| --- | --- |
| [Public README draft](https://github.com/vixttha/Blender-Agent/blob/readme-hq/workspace/v0.0.1/DRAFT.md) | Read the proposed v0.0.1 homepage, installation, and capability boundaries. |
| [Draft workspaces](https://github.com/vixttha/Blender-Agent/blob/readme-hq/workspace/README.md) | Maintain each public README candidate independently. |
| [Public README history](https://github.com/vixttha/Blender-Agent/blob/readme-hq/versions/README.md) | Find approved public README snapshots once published. |
| [README HQ versions](https://github.com/vixttha/Blender-Agent/blob/readme-hq/readme-hq/versions/README.md) | Immutable HQ landing page, guide, and change history. |
| [README HQ workspace](https://github.com/vixttha/Blender-Agent/blob/readme-hq/readme-hq/workspace/README.md) | Track the HQ template source and future revisions. |
| [README HQ guide](https://github.com/vixttha/Blender-Agent/blob/readme-hq/readme-hq/README.md) | Validation, archival, publication, and maintenance rules. |
| [Graphify integration](https://github.com/vixttha/Blender-Agent/blob/readme-hq/graphify/README.md) | Coordinate with the separate permanent `graphify-hq` branch. |
| [Public-runner validation](https://github.com/vixttha/Blender-Agent/blob/readme-hq/.github/workflows/readme-hq.yml) | Check structure, links, and frozen HQ documents on free GitHub-hosted runners. |

## Current public README candidate

**[Blender-Agent README v0.0.1](https://github.com/vixttha/Blender-Agent/blob/readme-hq/workspace/v0.0.1/DRAFT.md)** documents the pre-alpha foundation, basic inspection, limited Blender-powered creation/conversion/repair, CLI use, optional MCP integration, security boundaries, and honest testing scope.

The proposed instructions depend on `feature/v0.0.1-foundation`. The current `main` branch does not yet contain those tools. Do not describe this draft as an installed release or publish it ahead of its source implementation.

## Two independent version histories

- **README HQ v0.0.1**: the adapted documentation operating template established on this branch.
- **Public README v0.0.1**: a separate proposed homepage. It becomes approved only after a reviewed publication decision and a verified PR to `main`.

## Working rules

1. Draft every public README revision in `workspace/<version>/`, with its draft and review record.
2. Validate the documentation candidate and the exact application commit independently.
3. After explicit approval, freeze the public README under `versions/<version>/` and publish only the approved homepage and assets through a **dedicated PR to main**.
4. Draft subsequent HQ template changes in `readme-hq/workspace/<version>/` and archive accepted snapshots under `readme-hq/versions/<version>/`.
5. Keep the separate Graphify version branch and its release evidence independent.
6. Never merge this entire documentation branch into the application `main` branch; keep merge and release decisions owner-controlled.

Source inspiration: [AlderVale README HQ v0.0.6](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/007617884c75b9f422fc0feda031042da62962eb/readme-hq/versions/v0.0.6/README.md). This is a Blender-Agent adaptation, not a copy of the game project.
