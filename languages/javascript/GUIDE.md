# JavaScript tests

Use node:test for JavaScript modules and command-line tools. Use a local service or browser when the assertion depends on HTTP, browser behavior, or persistent state.

The [metadata](metadata.json) maps `JAVASCRIPT-001` to its runnable example. It declares the runtime, runner, test path, and command arguments. Serialized JSON preserves Unicode and numeric types.

## Add this to a project

1. Choose a project behavior and write one observable expected result. Preserve the case ID when moving the test.
2. Adapt the example assertion to call the real project entry point. Keep a representative input and a rejected or boundary input where applicable.
3. Place the test where the project runner discovers it. Update the case path and command when adopting the metadata alongside your test.
4. Record the actual checkout, runtime, run and job, and result using the [case and receipt form](../../starter/test-vault/case-and-receipt.md).

From the Lydite root, run `python tools/inventory.py --run javascript` in an environment with Node.js 24 / node:test. The test command uses the language folder as its working directory.
