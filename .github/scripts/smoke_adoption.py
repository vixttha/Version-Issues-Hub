"""Exercise the documented adoption path in a disposable repository."""

import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
from tempfile import TemporaryDirectory
import zlib

SOURCE = Path(__file__).resolve().parents[2] / "brand-identity"
sys.path.insert(0, str(SOURCE))
from test_verify import scored_decision


def png_chunk(kind, data):
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def write_record(path, record):
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def run():
    instructions = b"# Existing project instructions\n"
    readme = b"# Existing project README\n"
    with TemporaryDirectory() as temporary:
        consumer = Path(temporary)
        subprocess.run(["git", "init", "-q"], cwd=consumer, check=True)
        (consumer / "AGENTS.md").write_bytes(instructions)
        (consumer / "README.md").write_bytes(readme)
        kit = consumer / "brand-identity"
        shutil.copytree(SOURCE, kit, ignore=shutil.ignore_patterns("__pycache__"))
        command = [sys.executable, "brand-identity/verify.py"]
        subprocess.run(command, cwd=consumer, check=True)

        assets = kit / "09-assets"
        manifest_path = assets / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["kind"] = "project"
        write_record(manifest_path, manifest)
        subprocess.run(command, cwd=consumer, check=True)
        write_record(kit / "01-strategy" / "creative-decision.json", scored_decision())
        subprocess.run([*command, "--ready-for-artwork"], cwd=consumer, check=True)

        # A transparent 1×1 test fixture exercises registration without production art.
        payload = (
            b"\x89PNG\r\n\x1a\n"
            + png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
            + png_chunk(b"IDAT", zlib.compress(b"\0" * 5))
            + png_chunk(b"IEND", b"")
        )
        for role in ("logo", "wordmark"):
            filename = f"test-{role}.png"
            (assets / filename).write_bytes(payload)
            manifest["assets"].append({
                "file": filename,
                "width": 1,
                "height": 1,
                "alpha": True,
                "sha256": hashlib.sha256(payload).hexdigest(),
                "generated_with": "@Images",
                "role": role,
                "alt": f"Synthetic {role} fixture",
                "source": "Synthetic CI fixture that exercises the @Images inventory field",
                "status": "test",
            })
            write_record(manifest_path, manifest)
            subprocess.run(command, cwd=consumer, check=True)
            if role == "logo":
                early_handoff = subprocess.run(
                    [*command, "--ready-for-handoff"], cwd=consumer, capture_output=True, text=True,
                )
                assert early_handoff.returncode and "needs both logo and wordmark PNGs" in early_handoff.stderr
        test_only_handoff = subprocess.run(
            [*command, "--ready-for-handoff"], cwd=consumer, capture_output=True, text=True,
        )
        assert test_only_handoff.returncode and "status 'approved'" in test_only_handoff.stderr
        for asset in manifest["assets"]:
            asset["status"] = "approved"
        write_record(manifest_path, manifest)
        subprocess.run([*command, "--ready-for-handoff"], cwd=consumer, check=True)
        assert (consumer / "AGENTS.md").read_bytes() == instructions
        assert (consumer / "README.md").read_bytes() == readme
        (kit / "LICENSE").unlink()
        missing_license = subprocess.run(command, cwd=consumer, capture_output=True, text=True)
        assert missing_license.returncode and "Missing regular brand identity LICENSE file" in missing_license.stderr


if __name__ == "__main__":
    run()
