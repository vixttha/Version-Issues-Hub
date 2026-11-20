"""List and run the checks declared in Lydite language manifests."""

import argparse
import json
import os
import platform
import re
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path, PurePosixPath
from tempfile import NamedTemporaryFile, TemporaryDirectory

from native_outcomes import NATIVE_RUNNERS, passed_tests, selected_outcome, skipped_tests, unittest_command


ROOT = Path(__file__).resolve().parents[1]
CASE_ID = re.compile(r"[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*-[0-9]{3,}")
RUNNERS = {"ubuntu-24.04", "windows-latest"}


def test_path(folder, name):
    path = PurePosixPath(name)
    if len(path.parts) < 2 or path.parts[0] != "tests" or ".." in path.parts or "\\" in name:
        raise ValueError(f"{folder.name}: expected a path within tests/: {name}")
    return path.as_posix()


def check_files(folder, cases):
    declared = set()
    for case in cases:
        case["test"] = test_path(folder, case["test"])
        case["support"] = [test_path(folder, name) for name in case["support"]]
        declared.update([case["test"], *case["support"]])

    tests = folder / "tests"
    boundary = folder.resolve() / "tests"
    if tests.is_symlink() or tests.resolve() != boundary:
        raise ValueError(f"{folder.name}: tests/ must be a real directory inside the language folder")
    for name in sorted(declared):
        path = folder / name
        try:
            inside = path.resolve().is_relative_to(boundary)
        except RuntimeError:
            inside = False
        if not inside or path.is_symlink():
            raise ValueError(f"{folder.name}: declared fixture must stay inside tests/ without a file symlink: {name}")

    actual = {
        path.relative_to(folder).as_posix()
        for path in (folder / "tests").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    if actual != declared:
        raise ValueError(f"{folder.name}: missing {sorted(declared - actual)}, unlisted {sorted(actual - declared)}")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON field {key!r}")
        result[key] = value
    return result


def required_fields(value, required, optional, label):
    if not isinstance(value, dict):
        raise ValueError(f"{label}: expected an object")
    missing = required - value.keys()
    unknown = value.keys() - required - optional
    if missing or unknown:
        raise ValueError(f"{label}: missing fields {sorted(missing)}; unknown fields {sorted(unknown)}")


def nonblank(value):
    return isinstance(value, str) and bool(value.strip()) and "\x00" not in value


def argument_list(value):
    return (
        isinstance(value, list) and bool(value) and nonblank(value[0])
        and all(isinstance(arg, str) and "\x00" not in arg for arg in value[1:])
    )


DIRECT_ASSERTIONS = {
    "bash": ("bash",), "fsi": ("dotnet", "fsi", "--exec"),
    "haskell": ("runghc",), "java": ("java",),
    "lua": ("lua5.4",), "powershell": ("pwsh", "-NoProfile", "-File"),
    "python": ("python",), "ruby": ("ruby",),
}


def executable(value):
    return PurePosixPath(value.replace("\\", "/")).name.lower().removesuffix(".exe")


def test_invocation(folder, case):
    """Bind a native stage or standalone assertion to the declared primary file."""
    commands = case["commands"]
    test = case["test"]
    runner = case.get("native_runner")
    stage = case.get("native_command_index", case.get("assertion_command_index", len(commands) - 1))
    command = commands[stage]
    program = executable(command[0])
    if runner == "unittest":
        return re.fullmatch(r"python(?:[0-9.]*)?", program) and unittest_command(command) != command
    if runner in {"node-tap", "go-json"}:
        secondary, required, allowed = ("--test", "--test-reporter=tap",
            r"--test-reporter=tap|--test-name-pattern=.+") if runner == "node-tap" else (
                "test", "-json", r"-json|-count=[0-9]+|-run=.+|-v")
        return bool(
            program == ("node" if runner == "node-tap" else "go")
            and command[1:2] == [secondary]
            and required in command[2:-1]
            and PurePosixPath(command[-1]).as_posix() == test
            and all(re.fullmatch(allowed, arg) for arg in command[2:-1])
        )
    if not runner:
        for prefix in DIRECT_ASSERTIONS.values():
            if ([program, *command[1:len(prefix)]] == list(prefix)
                    and len(command) > len(prefix) and PurePosixPath(command[len(prefix)]).as_posix() == test):
                return True
    if runner not in (None, "rust-libtest"):
        return False
    for build in commands[max(0, stage - 1):stage]:
        compiler = executable(build[0])
        if compiler == ("rustc" if runner else "g++") and len(build) >= 4:
            flags, source, option, artifact = build[1:-3], *build[-3:]
            valid_flags = flags == ["--test"] if runner else all(
                re.fullmatch(r"(?:-std=c\+\+[0-9]+|-W[a-zA-Z]+)", value) for value in flags
            )
            if (valid_flags and PurePosixPath(source).as_posix() == test and option == "-o"
                    and re.fullmatch(r"\{tmp\}/[a-zA-Z0-9._-]+", artifact) and command[0] == artifact):
                return True
        if not runner and compiler == "dotnet" and build[1:2] == ["build"] and len(build) == 6:
            _, _, project, flag, artifacts, intermediate = build
            project_path = PurePosixPath(project)
            if (project not in case["support"] or project_path.suffix != ".csproj" or flag != "--output"
                    or not re.fullmatch(r"\{tmp\}/[a-zA-Z0-9._-]+", artifacts)
                    or intermediate != "-p:BaseIntermediateOutputPath={tmp}/obj/"
                    or command[:2] != ["dotnet", f"{artifacts}/{project_path.stem}.dll"]):
                continue
            expected_source = str(PurePosixPath(test).relative_to(project_path.parent)) if (
                PurePosixPath(test).is_relative_to(project_path.parent)) else None
            try:
                spec = ET.parse(folder / project).getroot()
            except ET.ParseError as error:
                raise ValueError(f"{case['id']}: invalid test project") from error
            if (spec.attrib == {"Sdk": "Microsoft.NET.Sdk"} and expected_source
                    and spec.findtext("PropertyGroup/EnableDefaultCompileItems") == "false"
                    and [item.attrib for item in spec.findall("ItemGroup/Compile")] == [{"Include": expected_source}]):
                return True
    return False


def read_manifest(folder, seen):
    manifest = json.loads((folder / "metadata.json").read_text(encoding="utf-8"), object_pairs_hook=unique_object)
    required_fields(manifest, {"schema_version", "language", "runtime", "runner", "cases"}, {"runtime_probe"}, "manifest")
    if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1:
        raise ValueError("schema_version: expected integer 1")
    if not nonblank(manifest["runner"]) or manifest["runner"] not in RUNNERS:
        raise ValueError(f"runner: expected one of {sorted(RUNNERS)}")
    for key in ("language", "runtime"):
        if not nonblank(manifest[key]):
            raise ValueError(f"{key}: expected a nonblank string")
    if "runtime_probe" in manifest and not argument_list(manifest["runtime_probe"]):
        raise ValueError("runtime_probe: expected a nonempty argument list")
    if not (folder / "GUIDE.md").is_file():
        raise ValueError("GUIDE.md is missing")

    cases = manifest["cases"]
    if not isinstance(cases, list) or not cases:
        raise ValueError("cases: expected at least one declared case")
    for index, case in enumerate(cases, 1):
        label = f"case {index}"
        required_fields(case, {"id", "purpose", "test", "support", "commands"}, {"native_runner", "native_command_index", "native_test", "assertion_command_index"}, label)
        case_id = case["id"]
        if not nonblank(case_id) or not CASE_ID.fullmatch(case_id) or case_id in seen:
            raise ValueError(f"{label}: invalid or duplicate case {case_id}")
        if not nonblank(case["purpose"]):
            raise ValueError(f"{case_id}: purpose must be a nonblank string")
        if not nonblank(case["test"]):
            raise ValueError(f"{case_id}: test must be a nonblank path")
        support = case["support"]
        if not isinstance(support, list) or not all(nonblank(path) for path in support):
            raise ValueError(f"{case_id}: support must be a list of nonblank paths")
        commands = case["commands"]
        if not isinstance(commands, list) or not commands or not all(argument_list(argv) for argv in commands):
            raise ValueError(f"{case_id}: commands must contain one or more nonempty argument lists")
        if "native_runner" in case:
            native = case["native_runner"]
            if not nonblank(native) or native not in NATIVE_RUNNERS:
                raise ValueError(f"{case_id}: unknown native_runner {native!r}")
        if "native_runner" in case and not nonblank(case.get("native_test")):
            raise ValueError(f"{case_id}: native_runner requires a named native_test")
        if "native_test" in case and "native_runner" not in case:
            raise ValueError(f"{case_id}: native_test requires a native_runner")
        for field, requires_native in (("native_command_index", True), ("assertion_command_index", False)):
            if field in case:
                stage = case[field]
                if ("native_runner" in case) != requires_native or type(stage) is not int or not 0 <= stage < len(commands):
                    raise ValueError(f"{case_id}: invalid {field} for this runner or command list")
        seen.add(case_id)
    check_files(folder, cases)
    for case in cases:
        if not test_invocation(folder, case):
            raise ValueError(f"{case['id']}: command stages do not bind to declared test {case['test']}")
    return manifest


def read_inventory(directory):
    inventory = {}
    seen = set()
    for folder in sorted(directory.iterdir()):
        if not folder.is_dir():
            continue
        try:
            inventory[folder.name] = read_manifest(folder, seen)
        except (OSError, ValueError, RecursionError) as error:
            raise ValueError(f"{folder / 'metadata.json'}: {error}") from error
    if not inventory:
        raise ValueError("No languages found")
    return inventory


def print_inventory(inventory):
    print("| Language | Runtime | Declared cases | Test files | Runner |")
    print("| --- | --- | ---: | ---: | --- |")
    for manifest in inventory.values():
        cases = manifest["cases"]
        test_files = len({case["test"] for case in cases})
        print(f'| {manifest["language"]} | {manifest["runtime"]} | {len(cases)} | {test_files} | {manifest["runner"]} |')
    print(f'\n{sum(len(m["cases"]) for m in inventory.values())} declared cases in {len(inventory)} language folders.')


class CheckoutDrift(RuntimeError):
    """A verified checkout changed during execution."""


def command_status(command, folder, env, timeout):
    try:
        result = subprocess.run(
            command, cwd=folder, env=env, check=False, timeout=timeout,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors="replace",
        )
    except subprocess.TimeoutExpired as error:
        if error.stdout:
            print(error.stdout.decode(errors="replace"), end="", flush=True)
        return "FAIL", f"{command[0]} timed out after {timeout:g}s", None, ""
    except FileNotFoundError:
        return "BLOCKED", f"required executable unavailable: {command[0]}", None, ""
    except OSError as error:
        return "BLOCKED", f"cannot start {command[0]}: {error}", None, ""
    print(result.stdout, end="", flush=True)
    if result.returncode:
        return "FAIL", f"{command[0]} exited with code {result.returncode}", result.returncode, result.stdout
    return "PASS", "command completed", result.returncode, result.stdout


def execute_case(case, folder, env, *, timeout=180, guard=None, command_results=None):
    native_output = ""
    commands = case["commands"]
    native_index = case.get("native_command_index", len(commands) - 1)
    with TemporaryDirectory(prefix="lydite-") as temp:
        for index, argv in enumerate(commands):
            if guard:
                guard()
            command = [arg.replace("{tmp}", temp) for arg in argv]
            if case.get("native_runner") == "unittest" and index == native_index:
                command = unittest_command(command)
            status, reason, exit_code, output = command_status(command, folder, env, timeout)
            if command_results is not None:
                command_results[index].update(outcome=status, detail=reason, exit_code=exit_code)
            if guard:
                guard()
            if status != "PASS":
                return status, reason
            if index == native_index:
                native_output = output
    if native := case.get("native_runner"):
        try:
            if name := case.get("native_test"):
                outcome = selected_outcome(native, native_output, name, Path(folder) / case["test"])
                if outcome == "pass":
                    return "PASS", f"declared native test passed: {name}"
                if outcome == "skip":
                    return "SKIP", f"declared native test skipped: {name}"
                return "FAIL", f"declared native test did not report a unique pass: {name}"
            if not passed_tests(native, native_output):
                if skipped_tests(native, native_output):
                    return "SKIP", f"{native} reported skipped tests and no passes"
                return "FAIL", f"{native} reported no passing tests"
        except (ValueError, AttributeError, KeyError, TypeError):
            return "FAIL", f"{native} reported an invalid result"
    return "PASS", "case passed"


def runtime_version(probe, folder, env):
    if not probe:
        return None
    try:
        result = subprocess.run(
            probe, cwd=folder, env=env, timeout=20, capture_output=True,
            text=True, errors="replace", check=True,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return next(
        (line.strip() for output in (result.stdout, result.stderr) for line in output.splitlines() if line.strip()),
        None,
    )


def checkout_identity(root):
    def git(*args):
        return subprocess.check_output(
            ["git", "-C", str(root), *args], text=True, stderr=subprocess.DEVNULL,
        ).strip()

    try:
        if Path(git("rev-parse", "--show-toplevel")).resolve() != root.resolve():
            return {"state": "UNVERSIONED", "commit": None, "base_commit": None}
        base = git("rev-parse", "HEAD")
        dirty = git("status", "--porcelain=v1", "--untracked-files=all", "--", ".")
    except (OSError, subprocess.CalledProcessError):
        return {"state": "UNVERSIONED", "commit": None, "base_commit": None}
    return {"state": "MODIFIED" if dirty else "CLEAN", "commit": None if dirty else base, "base_commit": base}


def report_destination(path):
    destination = path.resolve()
    inputs = ((ROOT / name).resolve() for name in ("languages", "tools"))
    if destination.is_relative_to((ROOT / ".git").resolve()) or (
        destination.exists() and any(destination.is_relative_to(prefix) for prefix in inputs)
    ):
        raise ValueError("evidence destination points inside project inputs")
    try:
        tracked = subprocess.check_output(
            ["git", "-C", str(ROOT), "ls-files", "-z"], stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        tracked = b""
    except subprocess.CalledProcessError:
        tracked = b""
    if any(destination == (ROOT / os.fsdecode(name)).resolve() for name in tracked.split(b"\0") if name):
        raise ValueError("evidence destination points to a tracked project file")
    return destination


def write_report(path, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as stream:
            pending = Path(stream.name)
            json.dump(report, stream, indent=2)
            stream.write("\n")
        pending.replace(path)
    finally:
        if pending is not None:
            pending.unlink(missing_ok=True)


def run_cases(inventory, languages, evidence=None):
    if evidence is not None:
        evidence = report_destination(evidence)
    source = checkout_identity(ROOT)
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "DOTNET_CLI_TELEMETRY_OPTOUT": "1"}
    report = {
        "schema_version": 1,
        "checkout_sha": source["commit"],
        "source": source,
        "run_id": env.get("GITHUB_RUN_ID"),
        "attempt": env.get("GITHUB_RUN_ATTEMPT"),
        "job": env.get("GITHUB_JOB"),
        "runner": env.get("LYDITE_RUNNER"),
        "environment": {
            "os": platform.system(), "release": platform.release(), "architecture": platform.machine(),
            "image_os": env.get("ImageOS"), "image_version": env.get("ImageVersion"),
        },
        "cases": [],
    }
    def guard():
        if source["state"] == "CLEAN" and checkout_identity(ROOT) != source:
            raise CheckoutDrift("the verified checkout changed during execution")

    hosted_blocked = env.get("GITHUB_ACTIONS") == "true" and source["state"] != "CLEAN"
    drifted = False
    print(f"Checkout {source['commit'] or source['state']} | run {report['run_id'] or 'local'}"
          f" | attempt {report['attempt'] or 'n/a'}", flush=True)
    for slug in languages:
        manifest = inventory[slug]
        folder = ROOT / "languages" / slug
        runtime = None
        if manifest.get("runtime_probe") and not (hosted_blocked or drifted):
            try:
                guard()
                runtime = runtime_version(manifest["runtime_probe"], folder, env)
                guard()
            except CheckoutDrift:
                drifted = True
        for case in manifest["cases"]:
            command_results = [
                {"index": index, "outcome": "NOT_RUN", "detail": "stage not reached", "exit_code": None}
                for index in range(len(case["commands"]))
            ]
            print(f'{case["id"]} | {case["purpose"]}', flush=True)
            if drifted:
                status, reason = "BLOCKED", "tracked checkout changed during this run"
            elif hosted_blocked:
                status, reason = "BLOCKED", "hosted evidence requires a clean Git checkout at the Vault root"
            elif manifest.get("runtime_probe") and runtime is None:
                status, reason = "BLOCKED", "declared runtime version probe failed"
            else:
                try:
                    status, reason = execute_case(case, folder, env, guard=guard, command_results=command_results)
                except CheckoutDrift as error:
                    drifted = True
                    status, reason = "FAIL", str(error)
            print(f'{case["id"]} | {status} | {reason}', flush=True)
            report["cases"].append({
                "case_id": case["id"], "language": slug, "test": case["test"],
                "declared_runner": manifest["runner"], "declared_runtime": manifest["runtime"],
                "observed_runtime": runtime, "commands": case["commands"], "command_results": command_results,
                "native_test": case.get("native_test"),
                "outcome": status, "detail": reason,
            })
    if drifted:
        report["source"] = {"state": "DRIFTED", "commit": None, "base_commit": source["base_commit"]}
        report["checkout_sha"] = None
    if evidence is not None:
        write_report(report_destination(evidence), report)
    return 0 if all(case["outcome"] == "PASS" for case in report["cases"]) else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--run", metavar="LANGUAGE", help="execute one language folder")
    group.add_argument("--runner", choices=sorted(RUNNERS), help="execute every case assigned to the specified runner")
    parser.add_argument("--evidence", type=Path, help="write a JSON report for a case run")
    args = parser.parse_args()
    if args.evidence and not (args.run or args.runner):
        parser.error("--evidence requires --run or --runner")
    try:
        inventory = read_inventory(ROOT / "languages")
        if args.run:
            if args.run not in inventory:
                raise ValueError(f"Unknown language folder: {args.run}")
            return run_cases(inventory, [args.run], args.evidence)
        elif args.runner:
            languages = [slug for slug, manifest in inventory.items() if manifest["runner"] == args.runner]
            if not languages:
                raise ValueError(f"No language folders were assigned to {args.runner}")
            return run_cases(inventory, languages, args.evidence)
        else:
            print_inventory(inventory)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        parser.exit(1, f"Lydite inventory: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
