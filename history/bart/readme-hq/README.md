# Blender-Agent Refinement Toolkit — README HQ

The permanent documentation workspace for Blender-Agent Refinement Toolkit's public README, version history, review evidence, and publication workflow.

**README HQ baseline:** `v0.0.1` · **Public README candidate:** `v0.0.4` draft · **Branch:** `readme-hq`

| Area | Purpose |
| --- | --- |
| [Public README draft](workspace/v0.0.4/DRAFT.md) | Review the BART rebrand, installation, and capability boundaries. |
| [Draft workspaces](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/blob/readme-hq/workspace/README.md) | Maintain each public README candidate independently. |
| [Public README history](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/blob/readme-hq/versions/README.md) | Find approved public README snapshots once published. |
| [README HQ versions](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/blob/readme-hq/readme-hq/versions/README.md) | Immutable HQ landing page, guide, and change history. |
| [README HQ workspace](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/blob/readme-hq/readme-hq/workspace/README.md) | Track the HQ template source and future revisions. |
| [README HQ guide](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/blob/readme-hq/readme-hq/README.md) | Validation, archival, publication, and maintenance rules. |
| [Graphify integration](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/blob/readme-hq/graphify/README.md) | Coordinate with the separate permanent `graphify-hq` branch. |
| [Public-runner validation](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/blob/readme-hq/.github/workflows/readme-hq.yml) | Check structure, links, and frozen HQ documents on free GitHub-hosted runners. |

## Current public README candidate

[README v0.0.4](workspace/v0.0.4/DRAFT.md) introduces **BART**, the agent for Blender-Agent Refinement Toolkit. See the [review record](workspace/v0.0.4/REVIEW.md) and [application candidate](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/pull/67).

## Two independent version histories

- [README HQ versions](readme-hq/versions/README.md) record the accepted documentation operating template.
- [Public README versions](versions/README.md) record the history of the application homepage.

## Working rules

1. Draft every public README revision in `workspace/<version>/`, with its draft and review record.
2. Validate the documentation candidate and the exact application commit independently.
3. After explicit approval, freeze the public README under `versions/<version>/` and publish only the approved homepage and assets through a **dedicated PR to main**.
4. Draft subsequent HQ template changes in `readme-hq/workspace/<version>/` and archive accepted snapshots under `readme-hq/versions/<version>/`.
5. Keep the separate Graphify version branch and its release evidence independent.
6. Never merge this entire documentation branch into the application `main` branch; keep merge and release decisions owner-controlled.

Source inspiration: [AlderVale README HQ v0.0.6](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/007617884c75b9f422fc0feda031042da62962eb/readme-hq/versions/v0.0.6/README.md).
