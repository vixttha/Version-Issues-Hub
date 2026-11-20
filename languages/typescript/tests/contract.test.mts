import assert from "node:assert/strict";
import { test } from "node:test";

function readCount(value: unknown): number | null {
  return typeof value === "number" && Number.isInteger(value) && value >= 0
    ? value
    : null;
}

test("unknown counts follow the runtime contract", () => {
  assert.equal(readCount(0), 0);
  assert.equal(readCount(3), 3);
  for (const invalid of ["3", -1, 1.5, null]) {
    assert.equal(readCount(invalid), null);
  }
});
