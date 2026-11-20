# README HQ Folder Guide

**Current HQ version:** `v0.0.3` · Owner-approved archive for the `readme-hq` branch.

This guide documents the [README HQ validator](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/tools/check_readme_hq.py) and how to prepare, validate, and archive a new HQ version.

## Where to work

| Task | Where to go |
| --- | --- |
| Review approved HQ versions | [HQ version history](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/readme-hq/versions/README.md) |
| Review HQ workspaces | [HQ workspace index](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/readme-hq/workspace/README.md) |
| Review the public game README history | [Public README version history](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/versions/README.md) |
| Draft a public game README | [Public README workspaces](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/workspace/README.md) |
| Review the current approved folder guide | [v0.0.3 guide archive](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/readme-hq/versions/v0.0.3/GUIDE.md) |
| Review the validator workflow | [README HQ workflow](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/.github/workflows/readme-hq.yml) |
| Review the frozen-source manifest | [Baseline manifest](https://github.com/vixttha/AlderVale-Pact-of-Ten/blob/readme-hq/tools/readme_hq_baselines.json) |

## What the validator checks

The README HQ workflow runs `python3 tools/check_readme_hq.py` on a standard public GitHub-hosted `ubuntu-latest` runner. It runs on pushes to `readme-hq`, pull requests targeting `readme-hq`, and manual workflow dispatch. The job has a finite timeout, read-only repository contents permission, and concurrency cancellation. It skips execution when the repository is private.

The validator checks the following areas.

### 1. Archive structure and frozen provenance

- Each version index must list every archive folder exactly once, and each archive must contain its required files.
- The baseline manifest records the source commit, source path, and Git blob SHA-1 for every frozen README or GUIDE snapshot.
- The validator fetches the exact recorded source commits when needed, reads the recorded source path from that commit, and compares its Git blob SHA-1 with the archived snapshot.
- The live HQ landing page and folder guide must match the latest approved archive byte for byte.
- Existing manifest entries and archived changelogs are checked against the trusted prior checkout so older history cannot be silently rewritten.
- The public README and HQ workspace indexes must match their folders. Draft pointers and the direct pointer from the latest HQ draft to the latest public README draft are checked.

### 2. Branch-local and current-main navigation

- Relative Markdown links and absolute links into the `readme-hq` branch are resolved against the exact validation checkout. Paths that escape the repository or point to missing files/directories fail.
- Heading fragments are checked against generated Markdown heading slugs.
- At the start of every hosted run, the validator fetches `origin/main` to check links against the current revision. The log records the exact main SHA used for that run.
- GitHub links to `main` are checked against that fetched main SHA. The validator verifies whether the target is a file or directory and checks heading fragments against the target file at that same main SHA.

### 3. External URL discovery

The validator extracts external destinations from:

- Inline Markdown links and reference links.
- Markdown autolinks and bare URLs.
- Protocol-relative URLs.
- HTML `href`, `src`, `poster`, and `action` attributes.

It deduplicates destinations, checks a bounded number of links, and skips local loopback examples such as `localhost` rather than treating them as public links.

### 4. External request safety

- Only HTTP and HTTPS are accepted, using standard ports 80 and 443.
- DNS destinations must resolve to public IP addresses. Private, loopback, reserved-local, and otherwise non-public destinations are rejected.
- The connection is pinned to a validated public IP address while preserving the original hostname for the Host header and TLS certificate verification.
- TLS certificate verification remains enabled.
- The checker follows bounded redirects (up to five hops); every redirect target is revalidated before another request is made. A redirect to a private or loopback destination is blocked.
- The checker starts with HEAD. When a server rejects HEAD with 403, 405, or 501, it uses a bounded GET fallback with a one-byte range request.
- Network concurrency and per-request timeouts are bounded.

### 5. Result classification and diagnostics

- Successful 2xx responses and 304 are reported as `PASS`.
- Missing pages (404 or 410), unsafe destinations, DNS failures, TLS certificate failures, redirect loops, and other definitive client errors are reported as failures.
- Access blocks and inconclusive responses, including a remaining HTTP 403 after the bounded GET fallback, 401, 408, 425, 429, server errors, timeouts, and network/protocol errors, are reported as `UNVERIFIED`. The run output lists these destinations for follow-up.
- Credentials in URLs are rejected. Diagnostics redact credentials, query strings, and fragments so tokens or private query values are not printed.
- The run output counts skipped local loopback examples separately.

## Regression coverage

The validator includes negative fixtures for archive drift, altered source records, frozen changelogs, missing workspace entries, broken draft links, stale draft pointers, and understated guide coverage. It also exercises valid workspace transitions and external-link cases such as redirects, broken destinations, blocked responses, loopback targets, malformed URLs, encoded paths, and diagnostic redaction.

The guide-coverage guard checks the latest active HQ workspace guide while a version is in Draft. Once the owner approves and archives that version, the guard checks the latest archived GUIDE snapshot instead. A draft cannot pass validation if its guide omits any required category of implemented validator behavior.

## Creating and approving an HQ version

1. Create a version folder under `readme-hq/workspace/<version>/`. Keep the proposed landing page in `DRAFT.md`, the proposed folder guide in `GUIDE.md`, the proposed changelog in `CHANGELOG.md`, and the workspace record in `README.md`.
2. Keep the workspace index row at `Draft` while the owner reviews it. Add the version to the archive index and frozen-source manifest after owner acceptance.
3. After explicit owner acceptance, copy the approved landing page and guide byte for byte into `readme-hq/versions/<version>/`. Add the changelog, update the approved version index, update the live root README and folder guide, and add source commit/path/blob entries to the manifest in the same archive commit.
4. Change the workspace row to an archived status, retain the source record, and preserve all earlier archives and changelogs.
5. Run the README HQ workflow on the exact proposed archive commit. Review the checkout SHA, prior archive baseline, main SHA, test summary, and any UNVERIFIED external destinations.
6. Keep merges, public README publication, and game releases under separate owner authorization.

## Scope boundaries

README HQ manages its own approved history and the separate public game README workspaces. GitHub Issues tracks engineering work. Notion holds private planning and handoffs.

Keep the `readme-hq` branch separate from the full game `main` branch. It is a sparse documentation branch; do not merge it wholesale into `main`. Refresh and revalidate the [separate public README proposal](https://github.com/vixttha/AlderVale-Pact-of-Ten/pull/62) against current `main` before promotion.
