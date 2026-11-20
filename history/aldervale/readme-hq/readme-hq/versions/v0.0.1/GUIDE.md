# README HQ Folder Guide

**Current HQ version:** `v0.0.1`

Use this folder to maintain the README HQ landing page and review how it has changed. Start with the [current landing page](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/README.md) or open the [version history](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/readme-hq/versions/README.md) to compare snapshots.

## Where to work

| Task | Where to go |
| --- | --- |
| Review an HQ version | [HQ version history](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/readme-hq/versions/README.md) |
| Draft an HQ revision | [HQ workspaces](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/readme-hq/workspace/README.md) |
| Review the public game README | [Game README version history](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/versions/README.md) |
| Draft a game README revision | [Game README workspaces](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/workspace/README.md) |

## Update README HQ

1. Start from the latest snapshot and put drafts, assets, previews, and notes in `readme-hq/workspace/<version>/`. Check that the experiment’s diff stays inside that folder.
2. After approval, update the HQ documents included in the revision. The branch landing page is `/README.md`, and this guide is `readme-hq/README.md`.
3. Archive exact copies as `README.md` and `GUIDE.md` in `readme-hq/versions/<version>/`. Record changes since the previous HQ version in `CHANGELOG.md`, then update the version index and workspace record in the same commit.
4. Check the [README HQ validation run](https://github.com/vixttha/AlderVale-Pact-of-Ten/actions/workflows/readme-hq.yml?query=branch%3Areadme-hq) for that commit. It checks the version records, snapshot copies, and internal links.

Public game README updates follow the process on the [HQ landing page](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/README.md#from-draft-to-public-readme).
