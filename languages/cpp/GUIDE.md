# C++ tests

Use the project's native test framework for numerical and binary contracts. Pin input representation and include known-bad values. This example uses a standalone executable and a nonzero exit on mismatch.

The [metadata](metadata.json) maps `CPP-001` to its runnable example. It declares the runtime, runner, test path, and command arguments. Inclusive bounds accept both edges and reject adjacent out-of-range values.

## Add this to a project

1. Choose a project behavior and write one observable expected result. Preserve the case ID when moving the test.
2. Adapt the example assertion to call the real project entry point. Keep a representative input and a rejected or boundary input where applicable.
3. Place the test where the project runner discovers it. Update the case path and command when adopting the metadata alongside your test.
4. Record the actual checkout, runtime, run and job, and result using the [case and receipt form](../../starter/test-vault/case-and-receipt.md).

From the Lydite root, run `python tools/inventory.py --run cpp` in an environment with C++20 / g++. The test command uses the language folder as its working directory.
