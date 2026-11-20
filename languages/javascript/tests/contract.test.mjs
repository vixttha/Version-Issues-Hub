import assert from "node:assert/strict";
import { test } from "node:test";

test("JSON round trip preserves a Unicode label and numeric count", () => {
  const original = { label: "café", count: 2 };
  const restored = JSON.parse(JSON.stringify(original));
  assert.deepEqual(restored, original);
  assert.equal(typeof restored.count, "number");
});
