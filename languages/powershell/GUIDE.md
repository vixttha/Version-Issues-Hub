# PowerShell tests

Use PowerShell to exercise Windows launchers, quoting, literal paths, and output handling. Verify observed files and exit codes from an isolated fixture.

The [metadata](metadata.json) maps `POWERSHELL-001` to its runnable example. It declares the runtime, runner, test path, and command arguments. A Windows path with spaces and brackets can be read back literally.

## Add this to a project

1. Choose a project behavior and write one observable expected result. Preserve the case ID when moving the test.
2. Adapt the example assertion to call the real project entry point. Keep a representative input and a rejected or boundary input where applicable.
3. Place the test where the project runner discovers it. Update the case path and command when adopting the metadata alongside your test.
4. Record the actual checkout, runtime, run and job, and result using the [case and receipt form](../../starter/test-vault/case-and-receipt.md).

From the Lydite root, run `python tools/inventory.py --run powershell` in an environment with PowerShell 7 / pwsh. The test command uses the language folder as its working directory.
