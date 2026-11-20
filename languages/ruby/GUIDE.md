# Ruby tests

Use Ruby for content validation, text processing, or a project-native test suite. Use committed samples with explicit required fields and known-bad inputs.

The [metadata](metadata.json) maps `RUBY-001` to its runnable example. It declares the runtime, runner, test path, and command arguments. Content records require a nonempty title.

## Add this to a project

1. Choose a project behavior and write one observable expected result. Preserve the case ID when moving the test.
2. Adapt the example assertion to call the real project entry point. Keep a representative input and a rejected or boundary input where applicable.
3. Place the test where the project runner discovers it. Update the case path and command when adopting the metadata alongside your test.
4. Record the actual checkout, runtime, run and job, and result using the [case and receipt form](../../starter/test-vault/case-and-receipt.md).

From the Lydite root, run `python tools/inventory.py --run ruby` in an environment with Ruby / standalone script. The test command uses the language folder as its working directory.
