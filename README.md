# Brand Identity Template

Use the [brand identity kit](brand-identity/README.md) to develop your product's name, slogan, logo, wordmark, visual system and PNG assets. Start with your audience, the product's purpose and the first place the brand will appear.

## Add the kit to an existing project

1. Download the [Brand Identity Template ZIP](https://github.com/vixttha/Brand-Identity-Template/archive/refs/heads/main.zip) and extract it. Copy the entire `brand-identity/` directory, including its license, into your repository. If that directory already exists, review the files before copying them.
2. Link `brand-identity/README.md` from your project's existing `AGENTS.md` or equivalent instructions, or point the agent directly to the [kit README](brand-identity/README.md).
3. In the copied `brand-identity/09-assets/manifest.json`, change `"kind": "template"` to `"kind": "project"`. Leave `assets` empty until you register your exports.
4. Start the [creative brief](brand-identity/01-strategy/brief.md). Follow the [creative direction workflow](brand-identity/01-strategy/creative-direction.md) before generating artwork with @Images.
5. From your repository root, run `python3 brand-identity/verify.py`. On Windows, use `py -3 brand-identity/verify.py`. The verifier uses Python 3.10+ and its standard library.

## Review a template change

The pull request check runs on GitHub's combined base and head commit. The Actions job summary records both parents and the tested commit. Before merging, compare the recorded base and head with the current PR. If either changed, update the PR branch with the latest base and require a passing run for the new combination. Branch push checks cover the source checkout.

## VIB project workspace

[Creative brief](brand-identity/01-strategy/brief.md) · [Decision record](brand-identity/01-strategy/creative-decision.json). Foundation approved under VIB-BRAND-FOUNDATION-001: Version-Issues-Hub-Branch / VIB, Cobalt Precision, hybrid monogram + path, dual slogans. Five mockups authorized; final artwork not approved. Repository and install refs unchanged.

## Engineering ecosystem

[Owner-approved six architectural laws](ENGINEERING-LAWS.md) apply to this product. Standalone operation and owner authority remain unchanged. The product has no mandatory coordination-tool dependency.

## Agent capability discovery — v1

<!-- agent-capability:v1
{"schema_version":1,"id":"brand-identity","branch":"Brand-Identity","entrypoint":"README.md","scope":"Brand identity and owner-approved visual assets","required_ecosystem_tools":[],"authority":"owner","discovery":"read-only","versioning":"independent"}
-->

A compatible agent may enumerate the target repository's branch refs, resolve this branch to a commit, and read its entry point at that exact commit. Read-only discovery confers no execution, write, integration or release authority. If this branch or marker is absent, the tool is absent or legacy/unverified; continue independently. Check the target's own instructions and owner scope before any action. The marker describes a capability, not a required registry or package version.

Installation convention: human or agent selects a reviewed exact source SHA, checks the dedicated target branch and collisions, follows this product's own installation guide, and records source/target SHA and preserved product state. Never merge a template workspace wholesale into product source. Existing installations require explicit reviewed upgrades; preserve local records and prior receipts. Optional evidence links do not authorize writes. No mandatory coordinator or other ecosystem tool.
