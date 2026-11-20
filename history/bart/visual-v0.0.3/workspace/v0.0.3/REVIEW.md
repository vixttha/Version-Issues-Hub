# README visual and source audit

## Baselines

- [Published v0.0.2 README](https://github.com/vixttha/Blender-Agent/blob/v0.0.2/README.md), release commit `cb945bd8531ee425615c1968612ab6503849369d`.
- [Application main](https://github.com/vixttha/Blender-Agent/commit/42c1ce618543374ed4dd5c8bcac5d437835c4e57) adds full Blender-through-MCP coverage without changing application source or README text.
- [README HQ archive](https://github.com/vixttha/Blender-Agent/blob/df9b4c387b86aa423216311334247eac0b155420/versions/v0.0.2/README.md) matches the tagged README bytes.
- [Graphify release receipt](https://github.com/vixttha/Blender-Agent/blob/5526238af9b510092db336d01b26a42c1ef82548/versions/v0.0.2/receipt.json) covers 10 Markdown sources. The archive has 37 nodes, 36 edges, and a verified graph checksum. [Graphify public runner](https://github.com/vixttha/Blender-Agent/actions/runs/44439503554)

The original [issue #16](https://github.com/vixttha/Blender-Agent/issues/16) check was Ubuntu-only. The revised [README HQ workflow](../../.github/workflows/readme-hq.yml) extracts the published Markdown commands and runs them in fresh clones on Ubuntu and Windows. It verifies the release SHA and archived README bytes, the documented CLI output and file digest, and the documented MCP request over real stdio from outside the workspace. It also verifies that an out-of-workspace input is rejected.

## Findings and draft repairs

| Finding | Draft change |
| --- | --- |
| GitHub Preview renders the document with sensible headings and copy buttons. The setup block scrolls horizontally even in a 1,363 px desktop viewport. | Platform blocks and a short OBJ fixture replace the single long Python command. |
| The introduction links to the foundation PR. Readers need a direct pre-release path and a plain explanation of CLI versus MCP. | Link the pre-release, then show which operations need Blender. |
| A support table and testing prose exist. The full Blender-through-MCP test is discoverable in current harness docs and CI but missing from the homepage. | Put release and main evidence in separate compatibility rows. |
| The README lacks any visual example, a ready-to-adapt MCP host configuration, and troubleshooting for path and dependency errors. | Add two labeled concepts, the generic configuration, and common recovery steps. |
| The application is pre-alpha. Host compatibility and material fidelity depend on the exercised workflow. | Keep explicit test limits and link security and roadmap. |
| The live HQ front page still refers to the original v0.0.1 draft. Its frozen template and workflow changes belong to separate HQ maintenance. | Update the live HQ landing page and keep the archived v0.0.1 template pinned. |

The draft shows the inspected triangle JSON ahead of the concept artwork. The v0.0.3 development evidence comes from PR #30’s exact checkpoint checkout. The [published examples](DRAFT.md#quick-start) use v0.0.2. The [workspace publication paths](README.md#publication-paths) preserve the relative image links when the homepage is promoted.

## Inspiration

- [scrcpy](https://github.com/Genymobile/scrcpy#readme) puts OS-specific entry points and practical tips near usage.
- [Ruff](https://github.com/astral-sh/ruff#readme) separates installation, usage and configuration so readers can use short action-first blocks.
- [yt-dlp](https://github.com/yt-dlp/yt-dlp#readme) distinguishes official release files from dependent install routes.
- [FreeCAD](https://github.com/FreeCAD/FreeCAD#readme) gives users and contributors distinct paths and links release channels in installation.
