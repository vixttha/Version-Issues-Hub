"""Validate the public Test Vault's case IDs and optional topic coverage."""

import argparse
from pathlib import Path
import re


CASE_ID = re.compile(r"([A-Z]+\d{2,})-(\d{3,})")
TOPIC_ROW = re.compile(r"^\|\s*([A-Z]+\d{2,})\s*·")
PRIORITIES = {"P0", "P1", "P2"}


def read_cases(path):
    case_ids = set()
    topics = set()
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.startswith("|") or line.startswith(("| Case |", "|---")):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        match = CASE_ID.fullmatch(cells[0]) if cells else None
        if len(cells) != 5 or not all(cells) or not match or cells[2] not in PRIORITIES:
            raise ValueError(f"{path}:{line_number}: invalid case row")
        case_id = match.group()
        if case_id in case_ids:
            raise ValueError(f"{path}:{line_number}: duplicate case {case_id}")
        case_ids.add(case_id)
        topics.add(match.group(1))
    if not case_ids:
        raise ValueError(f"{path}: no cases found")
    return case_ids, topics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=Path(__file__).with_name("case-catalog.md"))
    parser.add_argument("source_catalogs", nargs="*", type=Path)
    args = parser.parse_args()
    try:
        cases, topics = read_cases(args.catalog)
        expected = set()
        for path in args.source_catalogs:
            matches = {
                match.group(1)
                for line in path.read_text(encoding="utf-8").splitlines()
                if (match := TOPIC_ROW.match(line))
            }
            if not matches:
                raise ValueError(f"{path}: no source topics found")
            expected.update(matches)
        if args.source_catalogs and topics != expected:
            missing = ", ".join(sorted(expected - topics)) or "none"
            unknown = ", ".join(sorted(topics - expected)) or "none"
            raise ValueError(f"missing topics: {missing}; unknown topics: {unknown}")
    except (OSError, ValueError) as error:
        parser.exit(1, f"Test Vault validation failed: {error}\n")
    print(f"Test Vault: {len(cases)} unique cases across {len(topics)} topics.")


if __name__ == "__main__":
    main()
