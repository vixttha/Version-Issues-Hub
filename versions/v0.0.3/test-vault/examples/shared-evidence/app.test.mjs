import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

test('quote CLI returns the expected total and records its output', () => {
  const app = fileURLToPath(new URL('./app.mjs', import.meta.url));
  const evidence = execFileSync(process.execPath, [app, '125', '3']);
  writeFileSync(process.env.VAULT_EXAMPLE_EVIDENCE, evidence);
  const { case_id } = JSON.parse(readFileSync(new URL('./case.json', import.meta.url), 'utf8'));
  const receipt = {
    schema_version: 1,
    case_id,
    check_id: 'node-test',
    checkout_sha: execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim(),
    run_id: process.env.GITHUB_RUN_ID,
    attempt: process.env.GITHUB_RUN_ATTEMPT,
    environment: { os: process.platform, runtime: process.version },
    status: 'fail',
    evidence_sha256: createHash('sha256').update(evidence).digest('hex'),
  };
  try {
    assert.deepEqual(JSON.parse(evidence), { unit_cents: 125, quantity: 3, total_cents: 375 });
    receipt.status = 'pass';
  } finally {
    writeFileSync(join(process.env.VAULT_EXAMPLE_RECEIPTS, 'node.json'), JSON.stringify(receipt) + '\n');
  }
});
