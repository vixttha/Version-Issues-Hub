# Ecosystem verification receipt

- Foundation: six merged policy PRs VIB #28, Provenistem #6, Lydite #123, Veraphify #78, README HQ #154, Brand Identity #30.
- Discovery/distribution: VIB #32, Provenistem #7, Lydite #124, Veraphify #79, README HQ #155, Brand Identity #31. All merged; VIB into development candidate, not main.
- Identical six-law Git blob in all six: 8f1956821ee179334c20e3f4a3d49dae2f5cbaf2.
- Three verification layers: exact pre-merge diff and CI; 64 independent branch configurations with actual product native smoke commands; post-merge exact tree readback, matching tested trees in 6/6 repositories. Veraphify has no push workflow on merged main; exact PR tested tree and PR CI passed.
- Public run 45340494369 attempt 1 at 74bf6cca5f0719da0eb013c60663fd301486d3b3: 64/64 configurations; 63 nonempty + baseline; 192 native smoke executions, 2/2 negative controls. Previous run 45340210357 failed because root documents can reference separate law file; corrected and preserved.
- Artifact ID 14895956924, SHA-256 db49bf5f2d2e946688897f2c73e749f912d30d834c4e5bfa3550dfb97adefe1d. [Run](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45340494369/attempts/1) · [Artifact](https://github.com/vixttha/Version-Issues-Hub/actions/runs/45340494369/artifacts/14895956924).
- Integrated source snapshots: VIB 3f426e4940ef37544520851980418c71c31e0b93, Provenistem d64d0c73538e79af0292642c1f23bafe2e979ec0, Lydite eae4c9d9d56ed132b400d7c0f56a9babfe5cba07, Veraphify add4a029312c958a5e126990fc49e802c0112c27, README HQ b1bbc9a72a5193afcaeaf823f097753070bfa43f, Brand Identity 74a4666404fb4aa427881d0907cacbc8c65e2cfc. Each integrated merge tree equals its tested discovery head; exact candidate pins in pins.json.
- This is fixture coexistence and native smoke validation, not every runtime integration scenario or actual installation to 63 remote repos. No existing adopter upgrades, release, commercial launch or mandatory dependencies.
