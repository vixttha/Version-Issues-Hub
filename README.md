# Lydite Test Vault Template

**A mechanical touchstone for software. Put your code against the stone and prove it works.**

## Why Lydite?

Historically, *lydite* was a dense black stone used as a touchstone. Drag metal across it, and the physical mark left behind proved whether it was pure or counterfeit—no assumptions, no trusting claims.

This template is the stone; your code is the metal. Instead of relying on "it works on my machine" or vague checklists, a Lydite test vault turns project claims into repeatable, mechanically verified proof.

## Start here

- [Browse the language folders](languages). Each folder has `metadata.json`, `GUIDE.md`, and `tests/`.
- [Install the original copy-in starter](starter/test-vault/README.md) to adopt the catalog and receipt verifier in an existing project.
- [Read the migration audit](docs/migration-audit.md) for what came from AlderVale and Blender-Agent.
- [Browse the historical versions](versions/README.md) for the original template snapshots.
- [Review the standalone release candidate](docs/release-candidate.md) for the draft changelog and validation record.

Run `python tools/inventory.py` from the repository root to see each language, runtime, runner, declared case count, and test-file count. The inventory validates the metadata against files on disk. Each case holds its purpose, test path, and command arguments. Language folders include a small runnable example that you can adapt to your own project's entry point.

A **declared case** is one named behavior in the metadata. Several assertions can belong to one case. A **runner result** records the case outcome for the checkout and environment that actually ran it. See the [test guide](docs/testing.md) for the workflow.

## License

Lydite is available under the [MIT License](LICENSE). Include a copy of the license when you copy the starter or examples into another project. Third-party dependencies and linked projects have their own license terms.
