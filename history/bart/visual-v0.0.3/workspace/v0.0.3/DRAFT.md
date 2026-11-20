# Blender-Agent

Blender-Agent is a pre-alpha Python toolkit for inspecting, creating, converting, and repairing 3D assets locally. Use the CLI or connect an MCP host. Inspection runs on Python alone. Creation, conversion, and repair run Blender in the background.

**README v0.0.3 preview.** Try the examples with the published [v0.0.2 pre-release](https://github.com/vixttha/Blender-Agent/releases/tag/v0.0.2). Follow [the v0.0.3 application candidate](https://github.com/vixttha/Blender-Agent/pull/30) for upcoming changes.

[Quick start](#quick-start) · [Capabilities](#capabilities) · [MCP setup](#mcp-setup) · [Compatibility](#compatibility) · [Troubleshooting](#troubleshooting)

## Quick start

Use Git and Python 3.11 or newer. Clone into a directory that does not already contain a `Blender-Agent` folder.

```sh
git clone -b v0.0.2 --single-branch https://github.com/vixttha/Blender-Agent.git
cd Blender-Agent
python -m venv .venv
```

### macOS or Linux

The examples use `python`. If your system exposes Python 3 as `python3`, use that in the clone block.

```sh
.venv/bin/python -m pip install .
.venv/bin/blender-agent version
mkdir -p readme-demo
cat > readme-demo/triangle.obj <<'OBJ'
v 0 0 0
v 1 0 0
v 0 1 0
f 1 2 3
OBJ
.venv/bin/blender-agent --workspace readme-demo inspect triangle.obj
```

### Windows PowerShell

Run this block after the clone block. It uses the virtual environment’s executables directly.

```powershell
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\blender-agent.exe version
New-Item -ItemType Directory -Path readme-demo -Force | Out-Null
@'
v 0 0 0
v 1 0 0
v 0 1 0
f 1 2 3
'@ | Set-Content -Encoding ascii readme-demo\triangle.obj
.\.venv\Scripts\blender-agent.exe --workspace readme-demo inspect triangle.obj
```

### Check your result

The version command reports `0.0.2`. The inspection JSON includes these fields:

```json
{
  "format": "obj",
  "vertices": 3,
  "faces": 1,
  "bounds": {
    "min": [0, 0, 0],
    "max": [1, 1, 0]
  }
}
```

The full result includes the file’s size and SHA-256 digest. The digest depends on the exact file bytes, including line endings. [Public Linux and Windows walkthrough checks](https://github.com/vixttha/Blender-Agent/pull/39/checks)

![A solid triangle beside a wireframe triangle with three marked vertices](assets/triangle-inspection.webp)

*Concept illustration of the triangle from the walkthrough. The JSON above shows its inspected geometry.*

### Run a headless Blender job

Install Blender 4.1 or newer. Put the Blender executable on your command path or pass `--blender` with its path before the operation. Use `./.venv/bin/blender-agent` on macOS or Linux. In PowerShell, use `.\.venv\Scripts\blender-agent.exe` in place of the launcher below.

```sh
./.venv/bin/blender-agent --workspace readme-demo create cube cube.stl
./.venv/bin/blender-agent --workspace readme-demo convert cube.stl cube.glb
./.venv/bin/blender-agent --workspace readme-demo repair cube.stl repaired.stl
```

The input stays in place. Choose fresh output names when repeating the commands. The CLI accepts `--overwrite` for a separate convert or repair destination. MCP keeps overwrite disabled.

![Wireframe cube beside a solid orange cube on a neutral background](assets/wireframe-cube.webp)

*Concept illustration of cube geometry. The commands above produce files in `readme-demo`.*

## Capabilities

| Operation | Result in v0.0.2 | Needs Blender |
| --- | --- | --- |
| Inspect STL or OBJ | Size, digest, bounds, and basic mesh counts | No |
| Inspect GLB, FBX, or BLEND | File metadata and digest | No |
| Create | Cube, UV sphere, or cylinder | Yes |
| Convert | Read and write STL, OBJ, GLB, FBX, and BLEND | Yes |
| Repair | Weld nearby vertices and recalculate face normals in a separate output | Yes |

Geometry checks establish counts and bounds for the tested samples. Material and animation fidelity, printability, and game-engine readiness require validation in the destination tool. [Architecture](https://github.com/vixttha/Blender-Agent/blob/cb945bd8531ee425615c1968612ab6503849369d/docs/ARCHITECTURE.md) · [Roadmap](https://github.com/vixttha/Blender-Agent/blob/cb945bd8531ee425615c1968612ab6503849369d/docs/ROADMAP.md)

## MCP setup

Complete the quick start, then install the optional MCP adapter in the same environment.

```sh
.venv/bin/python -m pip install ".[mcp]"
```

```powershell
.\.venv\Scripts\python.exe -m pip install ".[mcp]"
```

Use your host’s stdio configuration format. Set `command` to the absolute launcher path inside your clone and set `BLENDER_AGENT_WORKSPACE` to the absolute path to its existing `readme-demo` directory.

```json
{
  "command": "/path/to/Blender-Agent/.venv/bin/blender-agent-mcp",
  "env": {
    "BLENDER_AGENT_WORKSPACE": "/path/to/Blender-Agent/readme-demo",
    "BLENDER_AGENT_BLENDER": "blender"
  }
}
```

On Windows the launcher ends in `.venv\Scripts\blender-agent-mcp.exe`. Use doubled backslashes in JSON or forward slashes. Set `BLENDER_AGENT_BLENDER` to the full executable path if your host needs it for Blender-powered operations. The inspection example runs without Blender.

### First tool call

After connecting, invoke `inspect_model` with the arguments below. The path is relative to the workspace you configured.

```json
{
  "name": "inspect_model",
  "arguments": {
    "path": "triangle.obj"
  }
}
```

Look for the same **3 vertices, 1 face, and bounds** as in the CLI result. The SHA-256 matches the CLI when both inspect the same file. The launcher also exposes `create_primitive`, `convert_model`, and `repair_mesh`. [v0.0.2 harness guide](https://github.com/vixttha/Blender-Agent/blob/cb945bd8531ee425615c1968612ab6503849369d/docs/HARNESS.md)

## Compatibility

| Area | Evidence |
| --- | --- |
| Python CLI | Python 3.11 and 3.12 on Linux and Windows |
| Headless Blender | Blender 4.5.0 on Ubuntu. Cube creation, STL roundtrips through OBJ, GLB, FBX and BLEND, and mesh repair |
| MCP stdio in v0.0.2 | Launcher, schemas, and workspace-bounded inspection on Linux and Windows. [Tagged source CI](https://github.com/vixttha/Blender-Agent/actions/runs/44438741759) · [Release quick-start check](https://github.com/vixttha/Blender-Agent/actions/runs/44438934108/job/135274667346) |
| MCP on main at `42c1ce6` | All four tool calls with Blender 4.5.0 on Ubuntu, including repair and source preservation. Windows exercises launcher startup, schemas, and workspace-bounded inspection. [Main CI](https://github.com/vixttha/Blender-Agent/actions/runs/44441784614) · [Ubuntu Blender job](https://github.com/vixttha/Blender-Agent/actions/runs/44441784614/job/135284120753) · [Windows stdio job](https://github.com/vixttha/Blender-Agent/actions/runs/44441784614/job/135284121183) |

Named host integrations, macOS runner coverage, and universal format fidelity require their own checks.

### v0.0.3 development candidate

At [checkpoint v0.0.2.19](https://github.com/vixttha/Blender-Agent/commit/c263d53e97f593fbb65ecd4cfb9bc42d6dc7b944), public CI exercised the installed MCP wheel with Blender 4.1.0 and 4.5.0 on Ubuntu and Blender 4.5.0 on Windows. The candidate requires an explicit MCP workspace and declares MCP SDK `>=1.30.0,<2`. [Candidate CI](https://github.com/vixttha/Blender-Agent/actions/runs/44451569549)

- **OBJ export.** Keep the OBJ and the returned `material_library` file together. Keep referenced texture images accessible as separate files.
- **BLEND saves.** Keep referenced images and libraries accessible at their original resolved paths.
- **Workspace boundary.** Use trusted assets and dependencies. Blender can resolve secondary files using its process’s filesystem permissions. Use OS-level isolation for untrusted workloads.

[Candidate harness guide](https://github.com/vixttha/Blender-Agent/blob/c263d53e97f593fbb65ecd4cfb9bc42d6dc7b944/docs/HARNESS.md) · [Candidate security guide](https://github.com/vixttha/Blender-Agent/blob/c263d53e97f593fbb65ecd4cfb9bc42d6dc7b944/SECURITY.md)

## Troubleshooting

- **Blender cannot be found.** Confirm the executable path and pass `--blender` for the CLI or `BLENDER_AGENT_BLENDER` in your host environment.
- **MCP starts in the wrong directory.** Set `BLENDER_AGENT_WORKSPACE` explicitly to an existing absolute path.
- **The destination already exists or its parent is missing.** Use a fresh output inside the workspace and create its parent directory before running the job.
- **Inspect rejects a large STL or OBJ.** Detailed inspection is capped at 128 MiB per input. Blender jobs cap the source and published output at 512 MiB each, with a default timeout of 180 seconds.
- **The format opens but the result looks different.** Check materials, textures, rigging, and animation in the target tool. The roundtrip checks use a geometric cube fixture.

Use a trusted workspace whose files and concurrent writers you control. The worker disables Blender auto-execution. Blender still runs with your account permissions. [Security and reporting](https://github.com/vixttha/Blender-Agent/blob/cb945bd8531ee425615c1968612ab6503849369d/SECURITY.md)

## Project links

[Changelog](https://github.com/vixttha/Blender-Agent/blob/cb945bd8531ee425615c1968612ab6503849369d/CHANGELOG.md) · [Contributing](https://github.com/vixttha/Blender-Agent/blob/cb945bd8531ee425615c1968612ab6503849369d/CONTRIBUTING.md) · [Issues](https://github.com/vixttha/Blender-Agent/issues) · [Specialist skill guides](https://github.com/vixttha/Blender-Agent/tree/cb945bd8531ee425615c1968612ab6503849369d/skills) · [v0.0.2 documentation graph](https://github.com/vixttha/Blender-Agent/blob/5526238af9b510092db336d01b26a42c1ef82548/versions/v0.0.2/README.md) · [MIT License](https://github.com/vixttha/Blender-Agent/blob/cb945bd8531ee425615c1968612ab6503849369d/LICENSE)
