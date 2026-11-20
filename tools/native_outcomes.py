"""Read the supported native runners' positive test results."""

import inspect
import json
import os
import re
import sys
import unittest


UNITTEST_RESULT = "LYDITE_UNITTEST_RESULTS "


NATIVE_RUNNERS = {"go-json", "node-tap", "rust-libtest", "unittest"}


def go_events(output):
    return (json.loads(line) for line in output.splitlines() if line.startswith("{"))


TAP_RESULT = re.compile(r"^( *)(ok|not ok) [0-9]+(?: - (.*))?$")
TAP_DIRECTIVE = re.compile(r"(?<!\\)\s+#\s*(skip|todo)(?:\s|$)", re.I)


def node_leaf_results(output):
    """Node TAP prints child results before the parent result at a lower indentation."""
    groups = set()
    for line in output.splitlines():
        if not (result := TAP_RESULT.fullmatch(line)):
            continue
        indent, status, title = result.groups()
        depth = len(indent)
        parent = depth in groups
        groups.discard(depth)
        if depth >= 4:
            groups.add(depth - 4)
        if parent:
            continue
        directive = TAP_DIRECTIVE.search(title or "")
        name = (title or "").strip()
        if directive:
            name = (title or "")[:directive.start()].strip()
        yield name, directive[1].lower() if directive else status


def node_leaf_outcomes(output):
    return (status for _, status in node_leaf_results(output))


def unittest_command(command):
    """Preserve the standard unittest module CLI while recording native events."""
    for index, arg in enumerate(command[1:], 1):
        if arg in ("-c", "--") or not arg.startswith("-"):
            break
        if arg == "-m":
            if command[index + 1:index + 2] == ["unittest"]:
                return [*command[:index], os.path.abspath(__file__), *command[index + 2:]]
            break
    return command


def unittest_outcomes(output):
    rows = output.splitlines()
    if rows and rows[-1].startswith(UNITTEST_RESULT):
        record = json.loads(rows[-1].removeprefix(UNITTEST_RESULT))
        return record["passed"], record["skipped"]

    # Direct test binaries can still supply standard unittest text output.
    summaries = re.findall(r"^OK(?: \(([^\n]*)\))?\s*$", output, re.M)
    counts = re.findall(r"^Ran (\d+) tests? in ", output, re.M)
    if not summaries or not counts:
        return 0, 0
    skipped = re.search(r"skipped=(\d+)", summaries[-1])
    skip_count = int(skipped[1]) if skipped else 0
    if not skip_count:
        expected = re.search(r"expected failures=(\d+)", summaries[-1])
        return max(0, int(counts[-1]) - (int(expected[1]) if expected else 0)), 0
    verbose = sum(bool(re.fullmatch(r".+ \.\.\. ok", line)) for line in rows)
    compact = sum(line.count(".") for line in rows if re.fullmatch(r"[.sx]+", line))
    return max(verbose, compact), skip_count


def skipped_tests(runner, output):
    if runner == "go-json":
        return sum(bool(event.get("Test") and event.get("Action") == "skip") for event in go_events(output))
    if runner == "node-tap":
        return sum(outcome == "skip" for outcome in node_leaf_outcomes(output))
    if runner == "unittest":
        return unittest_outcomes(output)[1]
    return sum(map(int, re.findall(r"^test result: ok\. .*? (\d+) ignored;", output, re.M)))


def passed_tests(runner, output):
    if runner == "go-json":
        return sum(
            bool(event.get("Test") and event.get("Action") == "pass")
            for event in go_events(output) if isinstance(event, dict)
        )
    if runner == "node-tap":
        return sum(outcome == "ok" for outcome in node_leaf_outcomes(output))
    if runner == "rust-libtest":
        return int(matches[-1]) if (matches := re.findall(
            r"^test result: ok\. (\d+) passed;", output, re.M,
        )) else 0
    if runner == "unittest":
        return unittest_outcomes(output)[0]
    return 0


def selected_outcome(runner, output, name, source):
    if runner == "go-json":
        events = list(go_events(output))
        if any(event.get("Test", "").startswith(name + "/") for event in events):
            return None
        outcomes = [event["Action"] for event in events
                    if event.get("Test") == name and event.get("Action") in ("pass", "skip", "fail")]
    elif runner == "node-tap":
        outcomes = [{"ok": "pass", "skip": "skip"}.get(status, "fail")
                    for title, status in node_leaf_results(output) if title == name]
    elif runner == "rust-libtest":
        outcomes = [{"ok": "pass", "ignored": "skip", "FAILED": "fail"}[status]
                    for status in re.findall(rf"^test {re.escape(name)} \.\.\. (ok|ignored|FAILED)(?:$|,)", output, re.M)]
    else:
        lines = output.splitlines()
        if not lines or not lines[-1].startswith(UNITTEST_RESULT):
            return None
        record = json.loads(lines[-1].removeprefix(UNITTEST_RESULT))
        outcomes = [
            outcome for key, outcome in (("passing", "pass"), ("skipping", "skip"))
            for item in record[key]
            if (item["id"] == name or item["id"].endswith("." + name))
            and os.path.normcase(os.path.realpath(item["source"])) == os.path.normcase(str(source.resolve()))
        ]
    return outcomes[0] if len(outcomes) == 1 else None


def unittest_identity(test):
    method = getattr(test, getattr(test, "_testMethodName", ""), None)
    source = inspect.getsourcefile(inspect.unwrap(method)) if method is not None else None
    return {"id": test.id(), "source": os.path.realpath(source)} if source else None


class EvidenceResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.passed = set()

    def addSuccess(self, test):
        super().addSuccess(test)
        self.passed.add(test)

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is None:
            self.passed.add(test)


if __name__ == "__main__":
    sys.path[0] = os.getcwd()
    program = unittest.main(
        module=None, testRunner=unittest.TextTestRunner(resultclass=EvidenceResult), exit=False,
    )
    result = program.result
    passed = [entry for test in result.passed if (entry := unittest_identity(test))]
    skipped = {getattr(test, "test_case", test) for test, _ in result.skipped} - result.passed
    skipped = [entry for test in skipped if (entry := unittest_identity(test))]
    print(UNITTEST_RESULT + json.dumps({
        "passed": len(result.passed), "skipped": len(result.skipped),
        "passing": sorted(passed, key=lambda entry: (entry["source"], entry["id"])),
        "skipping": sorted(skipped, key=lambda entry: (entry["source"], entry["id"])),
    }))
    raise SystemExit(0 if result.wasSuccessful() else 1)
