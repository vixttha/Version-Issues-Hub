# Python tests

Use standard-library unittest or the project's existing runner for pure functions, CLI behavior, and filesystem invariants. Use temporary directories for write and recovery cases.

The [metadata](metadata.json) maps `PYTHON-001` to its runnable example. It declares the runtime, runner, test path, and command arguments. A rejected debit preserves the balance.

## Add this to a project

1. Choose a project behavior and write one observable expected result. Preserve the case ID when moving the test.
2. Adapt the example assertion to call the real project entry point. Keep a representative input and a rejected or boundary input where applicable.
3. Place the test where the project runner discovers it. Update the case path and command when adopting the metadata alongside your test.
4. Record the actual checkout, runtime, run and job, and result using the [case and receipt form](../../starter/test-vault/case-and-receipt.md).

From the Lydite root, run `python tools/inventory.py --run python` in an environment with Python 3.12 / unittest. The test command uses the language folder as its working directory.
