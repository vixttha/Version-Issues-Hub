# README HQ Folder Guide

**Current HQ version:** `v0.0.2`

**Branch status:** Approved and archived on `readme-hq`; not merged into `main`.

Use this folder to maintain the README HQ landing page and review how it has changed. The current [HQ landing page](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/README.md) is the canonical entry point for this branch. Use the [HQ version history](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/readme-hq/versions/README.md) to compare archived versions.

## Where to work

| Task | Where to go |
| --- | --- |
| Review an HQ version | [HQ version history](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/readme-hq/versions/README.md) |
| Draft an HQ revision | [HQ workspaces](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/readme-hq/workspace/README.md) |
| Review the public game README | [Game README version history](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/versions/README.md) |
| Draft a game README revision | [Game README workspaces](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/workspace/README.md) |

## Update README HQ

1. Start from the latest archived baseline and put proposed landing-page and guide changes, previews, and notes in `readme-hq/workspace/<version>/`. Keep the experiment's diff inside that folder.
2. After owner approval, update the HQ documents included in the revision. The branch landing page is `/README.md`, and the folder guide is `readme-hq/README.md`.
3. Archive exact approved copies as `README.md` and `GUIDE.md` in `readme-hq/versions/<version>/`. Record the changes in `CHANGELOG.md`, update the version index and workspace record, and preserve all earlier snapshots.
4. Update `tools/readme_hq_baselines.json` with each frozen file's source commit, source path, and Git blob SHA-1 in the same commit as the archive and index changes. The validator verifies the archived snapshot blob SHA-1 values and checks that source commit/path entries are present and well-formed. It does not fetch the recorded historical source commit and path to independently verify the source file.
5. Check the [README HQ validation workflow](https://github.com/vixttha/AlderVale-Pact-of-Ten/actions/workflows/readme-hq.yml?query=branch%3Areadme-hq). It checks archive and workspace indexes, frozen snapshot checksums, current snapshot parity, draft pointers, and branch-local relative Markdown links across drafts and records. It does not verify absolute links to `main` or external URLs.

Public game README updates follow the promotion process on the [current branch HQ landing page](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/README.md#from-draft-to-public-readme).

This v0.0.2 guide is the current approved HQ version on `readme-hq`. It has not been merged into `main` and does not constitute a game release.
