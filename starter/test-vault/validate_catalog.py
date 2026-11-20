"""Check a Test Vault Markdown catalog and its optional JSON topic registry."""

import argparse
import json
import re
from pathlib import Path


CASE_ID = re.compile(r"([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*)-([0-9]{3,})")
TOPIC_ID = re.compile(r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*")
HEADER = ["Case", "Area", "Priority", "Suggested implementation", "Expected outcome"]
SEPARATOR = re.compile(r":?-{3,}:?")
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
PRIORITIES = {"P0", "P1", "P2"}


def table_cells(line):
    fields = re.split(r"(?<!\\)((?:\\\\)*)\|", line)
    cells = [fields[i] + (fields[i + 1] if i + 1 < len(fields) else "")
             for i in range(0, len(fields), 2)]
    if cells[0] == "":
        cells.pop(0)
    if cells and cells[-1] == "":
        cells.pop()
    return [cell.strip() for cell in cells]


def read_cases(path):
    cases = set()
    topics = set()
    in_table = False
    pending_divider = None
    fence = None
    comment = False
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if comment:
            comment = "-->" not in raw
            continue
        marker = FENCE.match(raw)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = None
            continue

        indented_code = raw.expandtabs(4).startswith("    ")
        line = raw.strip()
        starts_comment = not indented_code and line.startswith("<!--")
        cells = table_cells(line) if not (marker or indented_code or starts_comment) and "|" in line else []
        if pending_divider is not None:
            if len(cells) != len(HEADER) or not all(SEPARATOR.fullmatch(cell) for cell in cells):
                raise ValueError(f"{path}:{pending_divider}: expected a Markdown table divider after the header")
            pending_divider = None
            in_table = True
            continue

        if marker:
            fence = marker[1]
        if starts_comment:
            comment = "-->" not in line
        if not cells:
            in_table = False
            continue
        if cells == HEADER:
            pending_divider = number
            continue
        if not in_table:
            continue
        match = CASE_ID.fullmatch(cells[0]) if cells else None
        if len(cells) != len(HEADER) or not all(cells) or not match or cells[2] not in PRIORITIES:
            raise ValueError(f"{path}:{number}: invalid case row")
        case_id = match.group()
        if case_id in cases:
            raise ValueError(f"{path}:{number}: duplicate case {case_id}")
        cases.add(case_id)
        topics.add(match.group(1))
    if pending_divider is not None:
        raise ValueError(f"{path}:{pending_divider}: expected a Markdown table divider after the header")
    if not cases:
        raise ValueError(f"{path}: no cases found")
    return cases, topics


def read_topics(path):
    values = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(values, list) or not values:
        raise ValueError(f"{path}: expected a nonempty JSON array of topic IDs")
    if any(not isinstance(value, str) or not TOPIC_ID.fullmatch(value) for value in values):
        raise ValueError(f"{path}: invalid topic ID")
    if len(set(values)) != len(values):
        raise ValueError(f"{path}: duplicate topic ID")
    return set(values)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path(__file__).with_name("cases.md"))
    parser.add_argument("--topics", type=Path, help="Optional JSON array of expected topic IDs")
    args = parser.parse_args()
    try:
        cases, topics = read_cases(args.catalog)
        if args.topics:
            expected = read_topics(args.topics)
            if topics != expected:
                missing = ", ".join(sorted(expected - topics)) or "none"
                unknown = ", ".join(sorted(topics - expected)) or "none"
                raise ValueError(f"missing topics: {missing}; unknown topics: {unknown}")
    except (OSError, ValueError) as error:
        parser.exit(1, f"Test Vault validation failed: {error}\n")
    print(f"Test Vault: {len(cases)} unique cases across {len(topics)} topics.")


if __name__ == "__main__":
    main()
