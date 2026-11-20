"""Execute the README shell examples and verify the actual installed CLI and MCP."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DRAFT = ROOT / "workspace/v0.0.3/DRAFT.md"
RELEASE_VERSION = "0.0.2"
RELEASE_SHA = "cb945bd8531ee425615c1968612ab6503849369d"
WINDOWS = os.name == "nt"


def section(text: str, heading: str) -> str:
    start = f"{heading}\n"
    body = text.split(start, 1)[1]
    return re.split(r"^#{1,2} ", body, maxsplit=1, flags=re.M)[0]


def blocks(text: str, heading: str, language: str) -> list[str]:
    return re.findall(rf"^```{language}\n(.*?)^```$", section(text, heading), re.M | re.S)


def executable(clone: Path, name: str) -> Path:
    return clone / ".venv" / ("Scripts" if WINDOWS else "bin") / (name + (".exe" if WINDOWS else ""))


def run_walkthrough(text: str, temp: Path) -> None:
    windows_shell = "powershell" if WINDOWS else "sh"
    heading = "### Windows PowerShell" if WINDOWS else "### macOS or Linux"
    clone, posix, _ = blocks(text, "## Quick start", "sh")
    platform = blocks(text, heading, windows_shell)[0] if WINDOWS else posix
    install, = blocks(text, "## MCP setup", windows_shell)
    if WINDOWS:
        script = temp / "walkthrough.ps1"
        script.write_text(
            "$ErrorActionPreference = 'Stop'\n$PSNativeCommandUseErrorActionPreference = $true\n"
            + clone + platform + install,
            encoding="utf-8",
        )
        command = ["pwsh", "-NoProfile", "-File", str(script)]
    else:
        script = temp / "walkthrough.sh"
        script.write_text(clone + platform + install, encoding="utf-8")
        command = ["bash", "-eu", str(script)]

    checkout = temp / "Blender-Agent"
    result = subprocess.run(command, cwd=temp, text=True, capture_output=True, timeout=300)
    if result.returncode:
        sys.stderr.write(result.stderr.replace(str(temp), "<workdir>"))
        sys.stderr.write(result.stdout.replace(str(temp), "<workdir>"))
        result.check_returncode()

    actual_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=checkout, text=True).strip()
    assert actual_sha == RELEASE_SHA, actual_sha
    archived = subprocess.check_output(["git", "show", "HEAD:README.md"], cwd=checkout)
    snapshot = subprocess.check_output(["git", "show", "HEAD:versions/v0.0.2/README.md"], cwd=ROOT)
    assert archived == snapshot, "The archived README differs from the tagged release"

    decoder = json.JSONDecoder()
    version, inspection = [decoder.raw_decode(match.group())[0]
                           for match in re.finditer(r"^\{\n.*?^\}", result.stdout, re.M | re.S)]
    assert version == {"version": RELEASE_VERSION}, version
    example, = blocks(text, "### Check your result", "json")
    for key, value in json.loads(example).items():
        assert inspection[key] == value, (key, value, inspection)
    fixture = checkout / "readme-demo" / "triangle.obj"
    assert fixture.read_text(encoding="ascii").splitlines() == [
        "v 0 0 0", "v 1 0 0", "v 0 1 0", "f 1 2 3",
    ]
    data = fixture.read_bytes()
    assert inspection["size_bytes"] == len(data), inspection
    assert inspection["sha256"] == hashlib.sha256(data).hexdigest(), inspection
    print(f"CLI {RELEASE_VERSION} at {actual_sha}: documented triangle geometry, byte size and digest verified.", flush=True)

    expected = temp / "triangle-result.json"
    expected.write_text(json.dumps(inspection), encoding="utf-8")
    (temp / "outside.obj").write_bytes(data)
    subprocess.run(
        [str(executable(checkout, "python")), str(Path(__file__).resolve()), "--mcp", str(temp)],
        check=True,
        timeout=90,
    )
    assert fixture.read_bytes() == data, "The inspection modified the fixture"


async def verify_mcp(text: str, temp: Path) -> None:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    checkout = temp / "Blender-Agent"
    config, request = map(json.loads, blocks(text, "## MCP setup", "json"))
    launcher = executable(checkout, "blender-agent-mcp")
    assert config["command"].endswith("/.venv/bin/blender-agent-mcp"), config
    location = config["env"]["BLENDER_AGENT_WORKSPACE"]
    assert location.endswith("/Blender-Agent/readme-demo"), config
    config["command"] = str(launcher)
    config["env"]["BLENDER_AGENT_WORKSPACE"] = str(checkout / "readme-demo")
    params = StdioServerParameters(**config, cwd=temp)
    expected = json.loads((temp / "triangle-result.json").read_text(encoding="utf-8"))

    async with asyncio.timeout(60), stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            initialized = await session.initialize()
            assert initialized.serverInfo.name == "blender-agent", initialized
            tools = await session.list_tools()
            assert {tool.name for tool in tools.tools} == {
                "inspect_model", "create_primitive", "convert_model", "repair_mesh",
            }
            result = await session.call_tool(**request)
            assert not result.isError, result
            payload = result.structuredContent
            if payload is None:
                payload = json.loads(result.content[0].text)
            assert payload == expected, (payload, expected)
            failure = await session.call_tool("inspect_model", {"path": "../outside.obj"})
            assert failure.isError, failure
            assert any(
                content.type == "text" and "Path must remain inside the configured workspace." in content.text
                for content in failure.content
            ), failure
    print("MCP stdio: documented request matches the full CLI JSON, including digest; outside-workspace call rejected.")


if __name__ == "__main__":
    text = DRAFT.read_text(encoding="utf-8")
    if len(sys.argv) == 3 and sys.argv[1] == "--mcp":
        asyncio.run(verify_mcp(text, Path(sys.argv[2])))
    else:
        with tempfile.TemporaryDirectory(prefix="blender agent readme ") as directory:
            run_walkthrough(text, Path(directory))
