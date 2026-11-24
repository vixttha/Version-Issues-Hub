# Veraphify

**Code memory for each project version.** Archive a project’s evidence graph and look up the exact Git commit, file, and line that implemented a feature in a selected version.

**v0.0.9 preview** · [Try the two-version walkthrough](https://github.com/vixttha/Veraphify/blob/66e822b56528c5f3e7b7730709d4b472ae2d5f1e/docs/adopter-walkthrough.md) · [Verification evidence](docs/verification.md) · [Release tracker](https://github.com/vixttha/Veraphify/issues/21)

## Version-Issues-Hub installation

See the [project evidence workspace](PROJECT.md) for the pinned VIB candidate and archive workflow. The upstream preview walkthrough remains separate.

## Quickstart

From a checkout of the `Veraphify` branch, use Git, Bash, and Node.js 24.

```bash
node veraphifiy.mjs --help
```

The help output lists `import`, `verify`, and `lookup`. The CLI filename retains its original spelling.

To see an archive in use, follow the [two-version walkthrough](docs/adopter-walkthrough.md) from this checkout. The walkthrough uses Linux x86-64 and CPython 3.12 with `venv`, in addition to the tools above. It builds disposable fixture evidence with the pinned Graphify producer and looks up the same feature twice.

| Fixture version | Implementation citation for `feature:export` |
| --- | --- |
| `v1.0.0` | `src/feature.py:3` |
| `v1.1.0` | `src/feature.py:4` |

Each result identifies a different source commit. Importing `v1.1.0` leaves the earlier archive entry byte-for-byte identical.

## Archive your own project

Before building the evidence, keep the combined size of inventoried and cited Git files within the [8 MiB source budget](docs/adopter-walkthrough.md).

1. **Import** a `graph.json` and `receipt.json` pair from the [pinned Graphify producer](https://github.com/vixttha/Blender-Agent-Refinement-Toolkit/tree/6af3c2025be3f51e02dca4e4502088c526aae6d1/versions/v0.0.8), using the project identity and source commit declared by the receipt.
2. **Verify** the entry for that project and version. Store the source commit and archive SHA-256 from a trusted import separately. Pass them as `--source` and `--archive-sha256` to verify the exact entry.
3. **Look up** a feature in that version. Pass the same trusted `--source` and `--archive-sha256` pins to `lookup`. Citations give one-based physical line numbers in the pinned Git source.

Archive entries preserve the graph, receipt, and verified source bytes. Keep archives built from private repositories in private storage.

## Verification

The public Test Vault ran the documented walkthrough on Ubuntu. Separate Ubuntu and Windows jobs independently replayed both versions from the retained archive handoff. [Exact push run, attempt 1](https://github.com/vixttha/Veraphify/actions/runs/44644119066/attempts/1) · [Evidence and rerun instructions](docs/verification.md) · [Test Vault](https://github.com/vixttha/Veraphify/blob/66e822b56528c5f3e7b7730709d4b472ae2d5f1e/test-vault/README.md)

## License and attribution

Veraphify-authored code and tests are available under the [MIT license](https://github.com/vixttha/Veraphify/blob/66e822b56528c5f3e7b7730709d4b472ae2d5f1e/LICENSE). Read the [reuse and attribution guide](docs/reuse.md) for the Lydite notice that accompanies this branch's runtime.

## Project links

[Report an issue](https://github.com/vixttha/Veraphify/issues/new/choose) · [Release tracker](https://github.com/vixttha/Veraphify/issues/21)

We use and support the open-source [Graphify project](https://github.com/Graphify-Labs/graphify). Veraphify is developed and maintained independently of Graphify Labs.

## Engineering ecosystem

[Owner-approved six architectural laws](ENGINEERING-LAWS.md) apply to this product. Standalone operation and owner authority remain unchanged. The product has no mandatory coordination-tool dependency.


## Owner-approved engineering ecosystem laws

Decision ENGINEERING-ECOSYSTEM-LAWS-001 (2026-11-24). Mission: Build a toolkit that gives compatible LLM agents a structured engineering environment, rather than building another AI model.

<!-- engineering-laws:start -->
1. **Independence:** Every tool must remain independently installable, usable, versioned and maintained.
2. **Composability:** Installing additional tools expands the agent's capabilities without creating mandatory dependencies.
3. **Portability:** No mandatory AI provider, model, agent harness or paid execution service.
4. **Persistence:** Project knowledge, decisions, progress and evidence survive the termination of an AI session.
5. **Verification:** Development claims must be supported by reproducible, revision-bound evidence.
6. **Owner authority:** The human retains control over scope, architectural decisions, integration and releases.
<!-- engineering-laws:end -->

Remain standalone. Other tools are optional; their absence must not block normal operation. Preserve project-local authority and evidence; never automatically install, merge, synchronize or write to another tool's branch. No mandatory seventh coordinator, paid service or AI provider. Existing product scope remains authoritative. Change these laws only by explicit owner approval.

## Agent capability discovery — v1

<!-- agent-capability:v1
{"schema_version":1,"id":"veraphify","branch":"Veraphify","entrypoint":"README.md","scope":"Version archive and exact-source citations","required_ecosystem_tools":[],"authority":"owner","discovery":"read-only","versioning":"independent"}
-->

A compatible agent may enumerate the target repository's branch refs, resolve this branch to a commit, and read its entry point at that exact commit. Read-only discovery confers no execution, write, integration or release authority. If this branch or marker is absent, the tool is absent or legacy/unverified; continue independently. Check the target's own instructions and owner scope before any action. The marker describes a capability, not a required registry or package version.

Installation convention: human or agent selects a reviewed exact source SHA, checks the dedicated target branch and collisions, follows this product's own installation guide, and records source/target SHA and preserved product state. Never merge a template workspace wholesale into product source. Existing installations require explicit reviewed upgrades; preserve local records and prior receipts. Optional evidence links do not authorize writes. No mandatory coordinator or other ecosystem tool.
