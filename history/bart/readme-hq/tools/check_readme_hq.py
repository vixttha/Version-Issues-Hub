"""Read-only validation for the Blender-Agent Refinement Toolkit README HQ documentation branch."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

REQUIRED = (
    "README.md",
    "readme-hq/README.md",
    "readme-hq/versions/README.md",
    "readme-hq/versions/v0.0.1/README.md",
    "readme-hq/versions/v0.0.1/GUIDE.md",
    "readme-hq/versions/v0.0.1/CHANGELOG.md",
    "readme-hq/workspace/README.md",
    "readme-hq/workspace/v0.0.1/README.md",
    "versions/README.md",
    "workspace/README.md",
    "workspace/v0.0.1/README.md",
    "workspace/v0.0.1/DRAFT.md",
    "workspace/v0.0.1/CHANGELOG.md",
    "workspace/v0.0.1/REVIEW.md",
    "workspace/v0.0.4/README.md",
    "workspace/v0.0.4/DRAFT.md",
    "workspace/v0.0.4/CHANGELOG.md",
    "workspace/v0.0.4/REVIEW.md",
    "graphify/README.md",
    ".github/workflows/readme-hq.yml",
)
LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
SECRET = re.compile(r"(?i)\b(?:api[_-]?key|secret[_-]?key|access[_-]?token|password)\s*[:=]\s*['\"]?[A-Za-z0-9_-]{10,}")
PRIVATE_PATH = re.compile(r"(?i)(?:C:\\Users\\|/Users/[^/\s]+/|/home/[^/\s]+/)")
PINNED = "45726472fbe7f32de32f87426dc0b21b8fc1e8f7"
FROZEN_HQ_BLOBS = {
    "readme-hq/versions/v0.0.1/CHANGELOG.md": "b1445c773659f80dfb8668fb7b33f9741c3c5e4c",
    "readme-hq/versions/v0.0.1/GUIDE.md": "cc84d5c41d62de91ee82fb08b8ebdc5ce32421e6",
    "readme-hq/versions/v0.0.1/README.md": "326d609adcfcab36b00f1e04c7e2d39b6b587307",
}


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    for rel in REQUIRED:
        if not (root / rel).is_file():
            errors.append(f"missing required file: {rel}")
    if errors:
        return errors

    for path, expected in FROZEN_HQ_BLOBS.items():
        data = (root / path).read_bytes()
        header = f"blob {len(data)}".encode("ascii") + b"\0"
        if hashlib.sha1(header + data, usedforsecurity=False).hexdigest() != expected:
            errors.append(f"archived HQ baseline drift: {path}")

    draft = (root / "workspace/v0.0.1/DRAFT.md").read_text(encoding="utf-8")
    if PINNED not in (root / "workspace/v0.0.1/README.md").read_text(encoding="utf-8"):
        errors.append("workspace source commit pin missing")
    if "not yet available" not in draft.lower() or "not shipped" not in draft.lower():
        errors.append("public draft must distinguish unreleased and planned features")
    if "Draft" not in (root / "versions/README.md").read_text(encoding="utf-8"):
        errors.append("public version index must say the current homepage is a draft")

    # Validate navigation on HQ source pages. The candidate homepage is intentionally
    # excluded: its relative links target the implementation branch's future main tree.
    for rel in REQUIRED:
        if not rel.endswith(".md") or rel.startswith("workspace/v0.0.1/DRAFT.md"):
            continue
        path = root / rel
        content = path.read_text(encoding="utf-8")
        if EMAIL.search(content):
            errors.append(f"public email address in {rel}")
        if SECRET.search(content):
            errors.append(f"credential-like assignment in {rel}")
        if PRIVATE_PATH.search(content):
            errors.append(f"personal home-directory path in {rel}")
        if rel == "workspace/v0.0.4/DRAFT.md":
            continue
        for raw in LINK.findall(content):
            dest = raw.strip().split(" ", 1)[0].strip("<>")
            parsed = urlsplit(dest)
            if parsed.scheme or parsed.netloc or dest.startswith("#") or dest.startswith("//"):
                continue
            candidate = (path.parent / unquote(parsed.path)).resolve()
            try:
                candidate.relative_to(root.resolve())
            except ValueError:
                errors.append(f"link escapes repository: {rel} -> {dest}")
                continue
            if not candidate.exists():
                errors.append(f"broken local link: {rel} -> {dest}")
    return errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = validate(root)
    for problem in errors:
        print("FAIL:", problem)
    if errors:
        return 1
    print("PASS: README HQ v0.0.1 snapshots, required files, draft status, and branch navigation")
    print("NOTE: GitHub-hosted CI, external HTTP links, and application tests require separate evidence.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
