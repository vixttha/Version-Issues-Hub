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

This fresh version-specific workspace starts from the installed clean README HQ template. [First project README v0.0.1](workspace/v0.0.1/README.md) is a candidate, not published. The existing permanent [README HQ branch](https://github.com/vixttha/Version-Issues-Hub/tree/readme-hq) is unchanged.

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
