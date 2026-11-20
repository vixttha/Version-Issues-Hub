# Using Lydite

## Install the complete Vault

From a Lydite Git checkout, use the [starter install](../starter/test-vault/README.md#install-in-an-existing-repository) to add the catalog and workflow. Also copy `tools/inventory.py`, `tools/native_outcomes.py`, and each desired `languages/<language-folder>/` directory to the same paths in the target repository. Review collisions in an existing project. Use the runtimes listed in the selected manifests. The inventory reads the language folders beside its parent `tools/` directory.

From the target repository root, run `python tools/inventory.py` to check the declarations. Run `python tools/inventory.py --run python` for the Python example if installed. Replace the sample with a test of the real project entry point and register that test in the manifest. Add the same command to the target's CI once the runtime is set up. The copied catalog workflow checks the catalog; the language execution command runs the selected tests.

## Pick one behavior

Choose the language or runtime that controls the behavior. A second language can provide independent evidence when it reads the same observation through a different implementation or checks a real client boundary.

1. Write a stable case ID, the project risk or contract, the fixture, and an observable expected result.
2. Start in the matching [language folder](../languages). The guide explains what that runtime is suited to test. The metadata maps the example to its command, runner, and test file.
3. Adapt the runnable example to the actual project entry point. Include a known-bad or boundary input where it supplies distinct evidence. Keep fixtures synthetic and their outputs deterministic.
4. Record the command and result in the [case and run receipt](../starter/test-vault/case-and-receipt.md). When suites share an observation, use the [receipt verifier](../starter/test-vault/evidence.md) to bind results to the same checkout, run, attempt, and observation bytes.

## Get the inventory

Run `python tools/inventory.py` from the repository root. Counts come from declared cases and unique primary test paths. Support files, such as a .NET project file, are tracked separately. The inventory checks that a test directory contains the declared files and case IDs are unique. A suite's individual assertion count belongs to the native runner report.

Keep primary and support fixtures inside the language's real `tests/` directory. File symlinks and redirected test roots are rejected.

Keep planned cases in a project test plan. Once an assertion exists, record its code location. Treat a case as verified only after it runs for the intended checkout and environment. Store skipped runs and known failures as their actual outcomes, even when the surrounding job is green.

## Run the examples

Add `--evidence path/to/report.json` to write one record per selected case. Choose a generated report path that leaves tracked files, existing language and tool inputs, and Git metadata untouched. Each record lists the declared command arguments, declared and observed runtime, and PASS, FAIL, SKIP, or BLOCKED outcome. The ordered `command_results` list maps to the declared command indexes and records process outcomes and exit codes when available. Stages skipped after an earlier failure are recorded as NOT_RUN. A clean Git checkout receives its commit SHA. Modified and extracted checkouts can run locally and report MODIFIED or UNVERSIONED without claiming an exact commit. If the verified checkout changes at a probe or command boundary, the report is marked DRIFTED and loses its claimed checkout SHA. Later cases are blocked. Hosted CI requires a clean checkout and uploads those reports on passing and failing runs, with the checkout, run and attempt, job, and runner image information.

Every manifest case binds its outcome to its primary `test` file. Native runners require `native_test` with the expected native name. Python `unittest` uses a qualified class and method name and verifies the reported method's source file. Node and Go run the declared file explicitly. Rust verifies the compiler input and the resulting case-local binary. A suite-wide pass cannot replace a missing named result.

For a standalone assertion, point a supported interpreter directly at the primary file, or build the declared C++ or C# source and immediately run the resulting case-local artifact. C# projects explicitly include the primary source. Set the optional zero-based `assertion_command_index` to identify an assertion stage before post-processing. See the language manifests for supported invocation shapes.

For a case with a `native_runner`, the final command supplies the native verdict by default. Set the optional zero-based `native_command_index` when build, test and post-processing commands appear in the same case and the test command is earlier. Every command must still complete successfully.

Run `python tools/inventory.py --run <language-folder>` with the runtime listed in that folder's metadata. The arguments run from the language folder. A `{tmp}` argument is replaced with a fresh temporary directory. Lydite's CI executes the examples on standard public GitHub-hosted Ubuntu and Windows runners and records the exact checkout and result for each case.

The copied [v0.0.3 starter](../starter/test-vault/README.md) remains available for adopters who only need a catalog and optional receipts. The legacy Graphify maps under [Graphify HQ](../Graphify%20HQ/README.md) describe the archived template versions. The [archive manifest](../versions/manifest.json) pins the source. On Ubuntu with Python 3.12, install `tools/graphify/requirements.txt` and run `PYTHONHASHSEED=0 python tools/graphify/version_maps.py "$(mktemp -d)" --fetch-upstream --check` to fetch the three public source commits and compare freshly rebuilt maps with the committed snapshots.
