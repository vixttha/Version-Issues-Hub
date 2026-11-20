# Blender-Agent

Blender-Agent is a pre-alpha Python toolkit for inspecting 3D assets and running a small set of headless Blender operations. Use it from the command line or connect a compatible host through the optional Model Context Protocol (MCP) adapter.

**v0.0.2 pre-alpha foundation.** The quick start uses a pinned, tested source revision. [Foundation PR](https://github.com/vixttha/Blender-Agent/pull/1)

[Quick start](#quick-start) · [Capabilities](#capabilities) · [MCP setup](#mcp-setup) · [Testing and contributing](#testing-and-contributing)

## Quick start

Install Git and Python 3.11 or newer. The first example runs without Blender.

```sh
git clone https://github.com/vixttha/Blender-Agent.git
cd Blender-Agent
git checkout --detach 2f621fbd5ad0e3e6a96bc9037a9d7cd28edda65b
python -m venv .venv
```

Activate the virtual environment with `source .venv/bin/activate` on macOS or Linux, or `.\.venv\Scripts\Activate.ps1` in PowerShell. Then install the package and inspect a sample triangle:

```sh
python -m pip install .
blender-agent version
python -c "from pathlib import Path; p = Path('readme-demo'); p.mkdir(); (p / 'triangle.obj').write_text('v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n', encoding='utf-8')"
blender-agent --workspace readme-demo inspect triangle.obj
```

The inspection reports three vertices, one face, bounds from `[0, 0, 0]` to `[1, 1, 0]`, and a SHA-256 digest. The sample command expects a fresh `readme-demo` directory. To try your own asset, put it inside that workspace and pass its filename to `inspect`.

### Create, convert, and repair with Blender

The worker requires Blender 4.1 or newer. The headless smoke test uses Blender 4.5.0 on Ubuntu. Put `blender` on your command path or pass `--blender` with the executable path before the operation name.

```sh
blender-agent --workspace readme-demo create cube cube.stl --size 1
blender-agent --workspace readme-demo convert cube.stl cube.glb
blender-agent --workspace readme-demo repair cube.stl cube-repaired.stl
```

If a destination already exists, choose a new output name. Convert and repair can replace a separate output only when the CLI is given `--overwrite`. Use a dedicated workspace with trusted inputs and keep backups of important assets.

## Capabilities

| Operation | v0.0.2 scope |
| --- | --- |
| Inspect STL and OBJ | Python reports file size, SHA-256, bounds, and basic geometry counts. |
| Inspect GLB, FBX, and BLEND | Python reports file metadata only. |
| Create | Headless Blender creates a cube, UV sphere, or cylinder. |
| Convert | The Blender worker has readers and writers for STL, OBJ, GLB, FBX, and BLEND. Public CI checks STL roundtrips through OBJ, GLB, FBX, and BLEND. |
| Repair | Blender merges nearby vertices and recalculates face normals, then writes a separate output. |

The worker uses a fixed operation set and starts Blender with automatic script execution disabled. Blender runs with your account’s permissions. Use a workspace whose contents and concurrent access you control. The worker caps captured logs at 256 KiB and published output at 512 MiB. Detailed STL and OBJ inspection is limited to 128 MiB per input. Geometry counts and cleanup give you diagnostics. Printability, game-engine imports, and material or animation fidelity require checks in the destination tool. [Architecture](https://github.com/vixttha/Blender-Agent/blob/2f621fbd5ad0e3e6a96bc9037a9d7cd28edda65b/docs/ARCHITECTURE.md) · [Roadmap](https://github.com/vixttha/Blender-Agent/blob/2f621fbd5ad0e3e6a96bc9037a9d7cd28edda65b/docs/ROADMAP.md)

## MCP setup

Install the optional adapter in the repository’s activated environment:

```sh
python -m pip install ".[mcp]"
```

Configure your host to launch `blender-agent-mcp` over stdio. Use the executable from the virtual environment if your host has a separate command path. Set `BLENDER_AGENT_WORKSPACE` to the absolute path of an existing workspace and optionally set `BLENDER_AGENT_BLENDER` to your Blender executable.

The adapter exposes `inspect_model`, `create_primitive`, `convert_model`, and `repair_mesh`. Public CI starts the installed launcher from a separate working directory, checks all four input schemas, and verifies workspace-bounded inspection on Linux and Windows. Compatibility depends on the host. [Harness configuration](https://github.com/vixttha/Blender-Agent/blob/2f621fbd5ad0e3e6a96bc9037a9d7cd28edda65b/docs/HARNESS.md)

## Testing and contributing

Run the Python suite from the source checkout:

```sh
python -m unittest discover -s tests -v
```

The pinned foundation passed Python 3.11 and 3.12 checks on Linux and Windows. On Ubuntu with Blender 4.5.0, CI created an STL cube, roundtripped it through OBJ, GLB, FBX, and BLEND, and wrote a separate repaired STL. It checked triangle counts and bounds for each resulting STL. Individual MCP hosts and other Blender format combinations still need their own verification. [Foundation CI run](https://github.com/vixttha/Blender-Agent/actions/runs/44436263213)

If you find a bug, include the source revision, OS, Python and Blender versions, file format, command, and expected and actual results. A small synthetic asset helps reproduce file-specific behavior. [GitHub Issues](https://github.com/vixttha/Blender-Agent/issues) · [Contributing](https://github.com/vixttha/Blender-Agent/blob/2f621fbd5ad0e3e6a96bc9037a9d7cd28edda65b/CONTRIBUTING.md) · [Security](https://github.com/vixttha/Blender-Agent/blob/2f621fbd5ad0e3e6a96bc9037a9d7cd28edda65b/SECURITY.md) · [Changelog](https://github.com/vixttha/Blender-Agent/blob/2f621fbd5ad0e3e6a96bc9037a9d7cd28edda65b/CHANGELOG.md)

## License

Blender-Agent is an independent project distributed under the [MIT License](https://github.com/vixttha/Blender-Agent/blob/2f621fbd5ad0e3e6a96bc9037a9d7cd28edda65b/LICENSE).
