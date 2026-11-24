# VIB Veraphify adoption

Veraphify v0.0.9 preview, current runtime [add4a029312c958a5e126990fc49e802c0112c27](https://github.com/vixttha/Veraphify/tree/add4a029312c958a5e126990fc49e802c0112c27). Previous installation 829fdfae2ac0e8167d740e1a0ad8e8201295c34e. Current VIB candidate 4fc9ac47462101b941ea2f78fc939d42a9de0032. Existing archives, historical receipts, project-specific tools and license preserved. No other upstream project's templates imported. Public Graphify archive, lookup and preservation rerun required; no pass asserted here.

## Standalone path adaptation

Both first public runs failed because upstream main imports its colocated Lydite helper using a repository-specific path. [Archive failure](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45375792742) · [CLI failure](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45375792978). The existing vendored helper equals upstream byte-for-byte except its local profile path; the profile and MIT notice also match. Keep this local runtime dependency with Veraphify rather than requiring an installation of Lydite. One import path adapted; all other runtime bytes match the pinned upstream. Rerun both verification workflows; preserve failed attempts.
