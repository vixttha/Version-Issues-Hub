# VIB Veraphify adoption

## Current audit snapshot (2026-11-27)

Audit base: `4addbcbd1a4b577c9cb2a3bdc91d0038b2409e45`. Runtime derives from upstream Veraphify v0.0.9 preview `add4a029312c958a5e126990fc49e802c0112c27`, with VIB-specific local additions. This is not a claim that the entire CLI equals upstream or that the upstream preview is the latest release.

- The vendored `lib/inspect-evidence.mjs` differs from that pinned upstream `test-vault/javascript/inspect-evidence.mjs` only by the profile URL (`../handoff-profile.json` → `./handoff-profile.json`). The profile and Lydite MIT notice match upstream Git blobs `d5bf5921531cf4e4558adeb9dead1626ce8f77dc` and `30e65839065c0ea88ca00a2de47d65de4313e154`. Preserve the notice with the runtime.
- The CLI also imports VIB-local `lib/code-graph.mjs` and adds the fix, cumulative, candidate, engineering and development retrieval scopes. Standalone runtime packaging requires the CLI and both modules, the profile, and applicable notices; it does not require a Lydite installation, a test-vault directory, or an npm install.
- The historical feature-evidence workflow currently pins `041e187dc1d383082c1a4805e6d4743eec97e535` (v0.0.0.37, candidate-only). [Retained exact run 45994489992/1](https://github.com/vixttha/Version-Issues-Hub/tree/4addbcbd1a4b577c9cb2a3bdc91d0038b2409e45/archives/candidates/041e187dc1d383082c1a4805e6d4743eec97e535/45994489992-1) covers 38 feature lookups across two shards. It is not the live VIB head or a .42/.43 feature-evidence claim.
- Historical code graphs .1–.36 (#77), engineering graphs .37–.40 (PR #90), corrected .40 through .42 (PR #98), and separate development snapshot .43 (PR #100, source `0147d51eb7965034848ea623be55676149a74895`) have distinct scopes and dispositions. .42 is production-deferred; .43 development evidence is not accepted or integrated evidence. [Development workflow](docs/development-graphs.md).
- [Post-merge public run 45994489992/1](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45994489992/attempts/1) and [development replay](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45994489954/attempts/1) passed for their respective pins. These do not qualify new packaging tests.
- Issue [#80](https://github.com/vixttha/Version-Issues-Hub/issues/80) adds isolated Ubuntu/Windows packaging checks, including exact pinned import, verify and lookup, missing runtime files, wrong pins, corrupted archives and unavailable versions. Existing archive bytes stay unchanged. Do not regenerate already covered historical graphs or reopen [#16](https://github.com/vixttha/Version-Issues-Hub/issues/16), [#17](https://github.com/vixttha/Version-Issues-Hub/issues/17), or [#77](https://github.com/vixttha/Version-Issues-Hub/issues/77).

## Original adoption record (historical; retained verbatim)

The following note describes the original adoption only. Its wording “current” refers to that original event, not the live branch or current candidate.

Veraphify v0.0.9 preview, current runtime [add4a029312c958a5e126990fc49e802c0112c27](https://github.com/vixttha/Veraphify/tree/add4a029312c958a5e126990fc49e802c0112c27). Previous installation 829fdfae2ac0e8167d740e1a0ad8e8201295c34e. Current VIB candidate 4fc9ac47462101b941ea2f78fc939d42a9de0032. Existing archives, historical receipts, project-specific tools and license preserved. No other upstream project's templates imported. Public Graphify archive, lookup and preservation rerun required; no pass asserted here.

## Standalone path adaptation

Both first public runs failed because upstream main imports its colocated Lydite helper using a repository-specific path. [Archive failure](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45375792742) · [CLI failure](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45375792978). The existing vendored helper equals upstream byte-for-byte except its local profile path; the profile and MIT notice also match. Keep this local runtime dependency with Veraphify rather than requiring an installation of Lydite. One import path adapted; all other runtime bytes match the pinned upstream. Rerun both verification workflows; preserve failed attempts.
