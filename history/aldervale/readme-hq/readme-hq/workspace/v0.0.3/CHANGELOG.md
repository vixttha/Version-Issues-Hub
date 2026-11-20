# README HQ v0.0.3 changelog

Owner-approved on 2026-11-16. Changes since README HQ v0.0.2.

## Folder guide

- Replaces the stale v0.0.2 validator limitations with the behavior implemented by the current validator.
- Documents frozen-source provenance checks using the recorded source commit, source path, and Git blob SHA-1.
- Documents fresh `origin/main` resolution, exact main SHA receipts, target type checks, and heading-fragment validation.
- Documents external URL discovery across Markdown, bare URLs, protocol-relative URLs, and HTML attributes.
- Explains bounded redirects, public DNS validation, pinned public IP connections, TLS verification, loopback/private-target rejection, and bounded HEAD/GET probing.
- Defines `PASS`, failure, and `UNVERIFIED` outcomes, including diagnostic redaction.
- Explains the public GitHub-hosted README HQ workflow and the owner-controlled archive boundary.

## Landing page and archive

- Adds direct navigation to both version indexes, both workspace indexes, and the live HQ guide.
- Records v0.0.3 in the approved version index and archives the landing page and guide byte for byte.
- Pins both snapshots to their approved workspace source commit, paths, and Git blob IDs in the provenance manifest.
- Marks the v0.0.3 workspace archived and keeps its approved source files.
- Preserves the public README promotion heading linked from earlier HQ archives.

## Validator regression guard

- Adds a required coverage matrix for source provenance, current-main links, external URL discovery, redirect/destination safety, result classification, and diagnostic redaction.
- Checks the latest active workspace GUIDE while a candidate is in Draft; after approval and archival, checks the latest archived GUIDE.
- Adds six negative fixtures that remove one required coverage claim at a time.
- Updates draft-dependent fixtures to create a draft when the latest workspace is archived. Retains the existing archive, source, changelog, workspace, Markdown-link, external-link, and valid-transition tests.

## Preserved

- README HQ v0.0.2 landing page, folder guide, changelog, and frozen manifest entries remain byte-for-byte unchanged.
- README HQ v0.0.1 archives remain unchanged.
- The public game README and its separate v0.0.2 draft remain unchanged.
