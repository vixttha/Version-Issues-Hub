# README HQ

AlderVale’s home for the public README’s approved versions, changelogs, and drafts.

**Current HQ version:** `v0.0.3` · Owner-approved archive for the `readme-hq` branch.

| Start here | Use it for |
| --- | --- |
| [Public README version history](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/versions/README.md) | Compare approved game README versions and their changelogs. |
| [Public README workspaces](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/workspace/README.md) | Find the folder assigned to a game README version and review its draft. |
| [README HQ version history](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/readme-hq/versions/README.md) | Compare approved README HQ landing pages, guides, and changelogs. |
| [README HQ workspaces](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/readme-hq/workspace/README.md) | Find the source files and workspace record for each HQ version. |
| [README HQ folder guide](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/readme-hq/README.md) | Review the updated validator documentation and its coverage guard. |

**Current archived public README baseline:** [v0.0.1](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/versions/v0.0.1/README.md). The separate [public README integration proposal](https://github.com/vixttha/AlderVale-Pact-of-Ten/pull/62) is in Draft. Refresh and revalidate it against current `main` before promotion.

**Current public README draft:** [v0.0.2 draft](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/workspace/v0.0.2/DRAFT.md) · [Public README workspace record](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/workspace/v0.0.2/README.md).

**HQ v0.0.3 archive:** [Landing page](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/readme-hq/versions/v0.0.3/README.md) · [Folder guide](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/readme-hq/versions/v0.0.3/GUIDE.md) · [Changelog](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/readme-hq/versions/v0.0.3/CHANGELOG.md).

## From draft to approved HQ version

1. Draft the landing page, folder guide, and changelog in `readme-hq/workspace/<version>/`. Keep the workspace record and review notes beside them.
2. Validate the candidate with the README HQ workflow. The latest active workspace guide is checked against the validator's implemented coverage requirements.
3. Wait for explicit owner acceptance before archiving. A Draft workspace is not an approved version.
4. After acceptance, copy the approved landing page and guide byte for byte into `readme-hq/versions/<version>/`, add the changelog, update the approved version index and live documents, and pin each frozen file's source commit, source path, and Git blob SHA-1 in the baseline manifest.
5. Publish the public game README through its own PR to `main` after owner authorization.

The `readme-hq` branch is a sparse documentation branch. Do not merge it wholesale into the full game `main` branch. All merges, public README promotion, and releases remain owner-controlled.

## From draft to public README

1. Keep game README experiments in the assigned `workspace/<version>/` folder.
2. After owner approval, copy the approved README into `versions/<version>/README.md` and record its changelog and version index entry.
3. Use a dedicated PR to `main` for the approved public README and its assets. Verify the links from the repository root before the owner authorizes publication.
