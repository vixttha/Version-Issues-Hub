# Lua tests

Use Lua for script behavior, mod hooks, or independent geometry checks. A fixture with unequal dimensions makes axis mix-ups visible.

The [metadata](metadata.json) maps `LUA-001` to its runnable example. It declares the runtime, runner, test path, and command arguments. Clamping movement respects separate horizontal and vertical bounds.

## Add this to a project

1. Choose a project behavior and write one observable expected result. Preserve the case ID when moving the test.
2. Adapt the example assertion to call the real project entry point. Keep a representative input and a rejected or boundary input where applicable.
3. Place the test where the project runner discovers it. Update the case path and command when adopting the metadata alongside your test.
4. Record the actual checkout, runtime, run and job, and result using the [case and receipt form](../../starter/test-vault/case-and-receipt.md).

From the Lydite root, run `python tools/inventory.py --run lua` in an environment with Lua 5.4. The test command uses the language folder as its working directory.
