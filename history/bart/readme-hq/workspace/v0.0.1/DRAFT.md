# Blender-Agent

**Open, harness-neutral tools for Blender and 3D asset workflows.**

Blender-Agent is an open-source, Python-based foundation for inspecting 3D files and running a small set of controlled Blender operations from a command line or an optional Model Context Protocol (MCP) connection.

**v0.0.1 · Pre-alpha foundation candidate.** The implementation is under review on [`feature/v0.0.1-foundation`](https://github.com/vixttha/Blender-Agent/tree/feature/v0.0.1-foundation). This README is a proposed public homepage; these features are **not yet available on `main`**.

[Capabilities](#capabilities) · [Quick start](#quick-start) · [MCP integration](#optional-mcp-integration) · [Safety](#safety-and-limitations) · [Development](#development-and-validation)

## Capabilities

| Operation | v0.0.1 foundation scope | Limit |
| --- | --- | --- |
| Inspect STL and OBJ | Local, read-only structural inspection | Counts, bounds, size, and SHA-256 are not a quality or printability certificate. |
| Inspect GLB, FBX, and BLEND | File metadata only | Detailed scene inspection requires Blender support. |
| Create a primitive | Blender-backed cube, UV sphere, or cylinder | Small fixed set; not freeform generation. |
| Convert formats | Blender-backed STL, OBJ, GLB, FBX, and BLEND workflows | Real results depend on Blender, input data, and format support. |
| Repair a mesh | Limited merge-by-distance and normal recalculation | Not a guarantee of watertight, printable, or game-ready geometry. |
| CLI | Standard Python command interface | Runs on a machine where the software is installed. |
| MCP | Optional stdio adapter using the MCP Python SDK v1 | Not a hosted service; host integration is not universally verified. |

Autonomous art direction, sculpting, complex rigging, animation, procedural worlds, print certification, game-asset certification, persistent memory, and automatically generated skills are **not shipped** in this foundation.

## Quick start

**Requirements:** Python 3.11 or newer. Blender 4.1 or newer is needed for create, convert, and repair; basic inspection runs without Blender. The CI candidate includes a Blender 4.5 headless workflow.

After checking out a commit that contains the v0.0.1 implementation:

```bash
python -m pip install -e .
blender-agent version
blender-agent skills
```

Create a workspace with `input/` and `output/` folders. Put your own supported mesh in `workspace/input/`, then run:

```bash
blender-agent --workspace ./workspace inspect input/model.stl
blender-agent --workspace ./workspace create cube output/cube.stl --size 1
blender-agent --workspace ./workspace convert input/model.stl output/model.glb
blender-agent --workspace ./workspace repair input/model.stl output/repaired.stl
```

Commands resolve source and output paths inside the workspace; create the directories before running. Replace the example source filename with your actual asset. The create, convert, and repair commands require a Blender executable on the executing machine. You can use `--blender /path/to/blender` to select it. Output files are separate from inputs by default.

## Optional MCP integration

For an MCP-capable host, install the optional adapter:

```bash
python -m pip install -e ".[mcp]"
blender-agent-mcp
```

Configure the host's stdio MCP server command as `blender-agent-mcp` and set `BLENDER_AGENT_WORKSPACE` to an absolute directory. Set `BLENDER_AGENT_BLENDER` if Blender is not on the command path.

The current adapter exposes four bounded tools: `inspect_model`, `create_primitive`, `convert_model`, and `repair_mesh`. It does not give the host an arbitrary Python execution surface. Read [harness integration](docs/HARNESS.md) for configuration details and integration limits.

## Safety and limitations

- Asset operations are confined to a configured workspace, with path and symlink escape checks.
- Inputs are preserved by default. Treat any explicit overwrite option as destructive and back up important work.
- Blender subprocesses run a fixed, reviewed worker; they do not run model-authored scripts.
- Outputs receive basic structural checks, not aesthetic, topology, rigging, collision, or manufacturing certification.
- Connecting a chat model does not itself grant access to local Blender; an authorized runtime and compatible host are necessary.

## Development and validation

The project separates Python unit tests from real Blender and MCP-host acceptance. The v0.0.1 foundation candidate includes Python 3.11/3.12 test jobs on standard public GitHub-hosted Ubuntu and Windows runners, plus an Ubuntu Blender 4.5 headless roundtrip job. **A configured workflow is not evidence that a specific run passed.**

```bash
python -m pip install -e .
python -m compileall -q src
python -m unittest discover -s tests -v
```

Read [architecture](docs/ARCHITECTURE.md), [skill policy](docs/SKILL_POLICY.md), [roadmap](docs/ROADMAP.md), [contributing](CONTRIBUTING.md), [security](SECURITY.md), and [changelog](CHANGELOG.md). These files must be present on the publication target before this README can be published to `main`.

[Report a bug or request a feature](https://github.com/vixttha/Blender-Agent/issues) · [View GitHub Actions](https://github.com/vixttha/Blender-Agent/actions)

## License and affiliation

Planned v0.0.1 code distribution is under MIT; see [LICENSE](LICENSE) in the implementation branch. Blender-Agent is an independent project and is not affiliated with or endorsed by the Blender Foundation.
