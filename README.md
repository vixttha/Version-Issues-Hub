# README HQ

README HQ helps people understand a GitHub project and take their first useful step. It gives coding agents the same starting point, with links to repository instructions, test commands, and the evidence behind version and compatibility claims.

**Current version** · [README HQ v0.0.6](versions/v0.0.6/README.md)

| If you want to | Start here |
| --- | --- |
| Find a current or historical README | [Version index](versions/README.md) |
| Explore changes and evidence by version | [Graphify HQ](graphify-hq/README.md) |
| Improve a README in your own repository | [README guide](README-GUIDE.md) |
| Request a detailed repository review | [Repository audit](audits/README.md) |
| Browse techniques learned from reviews | [README Technique Library](https://github.com/vixttha/README-HQ/tree/README-Technique-Library) |
| Invoke README HQ from an agent | [Agent entry point](AGENTS.md) |

## Version-Issues-Hub workspace

This permanent installation keeps the project's [README workspace](workspace/README.md) separate from the upstream template's own version history. The [v0.0.1 draft](workspace/v0.0.1/DRAFT.md) is not published to the product homepage.

## Use README HQ

Ask your coding agent to use `vixttha/README-HQ`, branch `readme-hq`, and name the target repository. For example, **Use README HQ to audit owner/repository.** The agent loads the branch at its current commit and uses the target repository's own instructions for work there.

To check a README HQ checkout, use Python 3.10 or newer.

```sh
git clone --branch readme-hq https://github.com/vixttha/README-HQ.git
cd README-HQ
python3 tools/check_readme_hq.py
```

On Windows, use `py -3 tools/check_readme_hq.py`. A passing check prints counts for the version index, archived technique records, local navigation, and archived source files.

The branch keeps versions and audit findings available between sessions. An authorized human or agent starts each audit, records each new finding, and reviews any resulting project changes.

## Engineering ecosystem

[Owner-approved six architectural laws](ENGINEERING-LAWS.md) apply to this product. Standalone operation and owner authority remain unchanged. The product has no mandatory coordination-tool dependency.

## Agent capability discovery — v1

<!-- agent-capability:v1
{"schema_version":1,"id":"readme-hq","branch":"readme-hq","entrypoint":"AGENTS.md","scope":"Documentation authoring and version history","required_ecosystem_tools":[],"authority":"owner","discovery":"read-only","versioning":"independent"}
-->

A compatible agent may enumerate the target repository's branch refs, resolve this branch to a commit, and read its entry point at that exact commit. Read-only discovery confers no execution, write, integration or release authority. If this branch or marker is absent, the tool is absent or legacy/unverified; continue independently. Check the target's own instructions and owner scope before any action. The marker describes a capability, not a required registry or package version.

Installation convention: human or agent selects a reviewed exact source SHA, checks the dedicated target branch and collisions, follows this product's own installation guide, and records source/target SHA and preserved product state. Never merge a template workspace wholesale into product source. Existing installations require explicit reviewed upgrades; preserve local records and prior receipts. Optional evidence links do not authorize writes. No mandatory coordinator or other ecosystem tool.
