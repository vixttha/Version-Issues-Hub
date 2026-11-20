"""Check inline relative links in the maintained standalone documentation."""

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"\[[^\]\n]+\]\(([^()\s]+)\)")


def links(path):
    text = path.read_text(encoding="utf-8")
    fenced = None
    for line in text.splitlines():
        if match := re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line):
            marker, rest = match.groups()
            if fenced is None:
                fenced = marker
            elif fenced[0] == marker[0] and len(marker) >= len(fenced) and not rest.strip():
                fenced = None
            continue
        if fenced is None:
            yield from LINK.findall(line)


def anchors(path):
    for line in path.read_text(encoding="utf-8").splitlines():
        if heading := re.match(r"^#{1,6} (.+?)\s*#*\s*$", line):
            yield re.sub(r"[^\w\s-]", "", heading[1].lower()).replace(" ", "-")


def main():
    maintained = [ROOT / "README.md", ROOT / "versions/README.md"]
    for directory in ("docs", "starter", "languages", "Graphify HQ"):
        maintained.extend((ROOT / directory).rglob("*.md"))
    issues = []
    for path in sorted(maintained):
        for raw in links(path):
            link = urlsplit(raw)
            if link.scheme or link.netloc:
                continue
            target = (path.parent / unquote(link.path)).resolve() if link.path else path
            if not target.is_relative_to(ROOT) or not target.exists():
                issues.append(f"{path.relative_to(ROOT)}: {raw} has no destination")
            elif link.fragment and target.suffix == ".md" and unquote(link.fragment) not in anchors(target):
                issues.append(f"{path.relative_to(ROOT)}: {raw} has no matching heading")
    if issues:
        raise SystemExit("\n".join(issues))
    print(f"Verified relative links in {len(maintained)} maintained Markdown files.")


if __name__ == "__main__":
    main()
