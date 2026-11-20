# README HQ operating guide

**HQ baseline:** `v0.0.1`, adapted for the Blender-Agent public repository.

## Branches and ownership

- `main` is the public application branch.
- `feature/v0.0.1-foundation` contains the pre-alpha implementation candidate that the first public README describes.
- `readme-hq` is the permanent documentation workspace. It is intentionally separate from `main`.
- `graphify-hq` is the independent release/version mapping branch. Documentation snapshots never substitute for release validation.

## Two version sequences

**HQ templates:** `readme-hq/workspace/vX.Y.Z/` is the development folder; `readme-hq/versions/vX.Y.Z/` is the accepted snapshot. Freeze landing page, guide, and changelog together.

**Public homepage:** `workspace/vX.Y.Z/` holds proposed text, scope, and review evidence. After approval, retain `versions/vX.Y.Z/README.md` and `CHANGELOG.md`, then publish from a *separate branch and PR* to `main`. A draft has no release authority.

## Required candidate review

1. Confirm the implementation branch at a full commit SHA; verify commands, requirements, and link targets against that exact source.
2. Validate relative Markdown links, HQ snapshots, indexes, and absent private identifying data.
3. Check that the README clearly distinguishes available features, limitations, planned features, and unverified integration tests.
4. Run [README HQ validation](https://github.com/vixttha/Blender-Agent/blob/readme-hq/.github/workflows/readme-hq.yml) on the exact documentation commit using standard free GitHub-hosted public runners.
5. Review the publication PR against current `main` for conflicting changes and ensure any linked application files exist there before merging.
6. Obtain explicit publication approval. Never merge the HQ branch wholesale.

## Baseline and immutability

The initial HQ `v0.0.1` landing and guide are frozen under [versions](https://github.com/vixttha/Blender-Agent/blob/readme-hq/readme-hq/versions/README.md). The live root `README.md` and this guide must match their latest HQ archive snapshots byte for byte. Keep previous versions unchanged; amendments belong to a newer version with a changelog.

The first public README is currently **Draft**. Do not add it to the approved `versions/` archive or claim it is public on `main` until the implementation and publication are accepted.

## Validator scope

`tools/check_readme_hq.py` enforces:
- HQ landing and guide equal archived v0.0.1 files.
- Expected indexes, source record, changelogs, draft, and workflow exist.
- HQ documentation's repository-relative links resolve locally, including percent-encoded paths.
- The public README candidate is explicitly marked as draft, and its source commit is pinned.
- No obvious personal-email, credential assignment, or home-directory path is introduced into the HQ Markdown.

The draft README targets the future application root, so its relative links are reviewed against the pinned implementation branch, **not** resolved against this documentation branch. External destinations and GitHub Actions execution are separate verification steps; a local validator pass is not a claim that all remote links or the app work.

## Graphify

Reuse the existing [Blender-Agent Graphify HQ](https://github.com/vixttha/Blender-Agent/tree/graphify-hq) rather than copying AlderVale's game map. The Graphify archive has its own version source and receipts. A future HQ template map must have independently generated and verified evidence before any Graphify certification claim.

## Privacy and cost boundaries

Do not include creator biographies, private directories, private repository references, account secrets, or personal contact information. Use standard GitHub-hosted runners on this **public** repository. No required local agent runner, paid CI, or automatic release.
