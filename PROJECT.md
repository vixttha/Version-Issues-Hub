# Version-Issues-Hub — Veraphify workspace

Permanent independent Veraphify v0.0.9 preview installation. [Runtime instructions](README.md).

- [Live VIB development branch](https://github.com/vixttha/Version-Issues-Hub/tree/plan/v0.0.0.1) (moving; verify exact head).
- [Pinned eight-checkpoint candidate](https://github.com/vixttha/Version-Issues-Hub/tree/3b6951be81d2fc9468b5379aead57c7afc444754) (v0.0.0.8 candidate, not a release).
- [Pinned manifest](https://github.com/vixttha/Version-Issues-Hub/blob/3b6951be81d2fc9468b5379aead57c7afc444754/docs/receipt-evidence.json) and [ledger](https://github.com/vixttha/Version-Issues-Hub/blob/3b6951be81d2fc9468b5379aead57c7afc444754/ledger/issue-versions.json).
- [Original five-checkpoint run](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45330366047) (historical candidate).
- [Current archive workflow](https://github.com/vixttha/Version-Issues-Hub/actions/workflows/vib-veraphify.yml).

The workflow compares the manifest against the pinned issue-version ledger, checks each implementation citation, and verifies the archive digest. Public push runs also preserve exact verified candidate bytes and receipt under `archives/candidates/<source>/<run>-<attempt>/` on this branch. The original artifact is recovered using its recorded ZIP SHA-256. PR runs are read-only. Preservation is not an owner acceptance or release decision. Existing bytes must never be replaced; any non-fast-forward push fails. Durable storage is verified only after the Git commit exists. Issue #15 tracks live ref protection.

VIB remains independent of Provenistem. Both are complementary parts of the same puzzle. [Owner lock](https://github.com/vixttha/Version-Issues-Hub/issues/9). Optional read-only references only; neither product requires the other or transfers write authority. No private source, credentials, or product branch mutations.
