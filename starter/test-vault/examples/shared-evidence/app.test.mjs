import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

function readObservation(data) {
  const text = data.toString('utf8');
  const observation = JSON.parse(text);
  const tokens = /"(?:\\.|[^"\\])*"|[{}\[\]]/gs;
  const stack = [];
  for (const match of text.matchAll(tokens)) {
    const token = match[0];
    if (token === '{' || token === '[') {
      stack.push(token === '{' ? new Set() : null);
    } else if (token === '}' || token === ']') {
      stack.pop();
    } else if (/^\s*:/.test(text.slice(match.index + token.length))) {
      const key = JSON.parse(token);
      const keys = stack.at(-1);
      assert.ok(!keys.has(key), 'duplicate JSON key: ' + key);
      keys.add(key);
    }
  }
  return observation;
}

test('shared JSON observation rejects repeated object keys', () => {
  const duplicate = Buffer.from('{"unit_cents":120,"\\u0075nit_cents":125,"quantity":3,"total_cents":375}');
  assert.throws(() => readObservation(duplicate), /duplicate JSON key: unit_cents/);
  assert.throws(() => readObservation(Buffer.from('{"data":[{"k":1,"k":2}]}')), /duplicate JSON key: k/);
  assert.deepEqual(readObservation(Buffer.from('[{"k":1},{"k":2}]')), [{ k: 1 }, { k: 2 }]);
});

test('quote CLI returns the expected total and records its output', () => {
  const app = fileURLToPath(new URL('./app.mjs', import.meta.url));
  const evidence = execFileSync(process.execPath, [app, '125', '3']);
  writeFileSync(process.env.VAULT_EXAMPLE_EVIDENCE, evidence);
  const plan = readFileSync(new URL('./case.json', import.meta.url));
  const { case_id } = JSON.parse(plan);
  const receipt = {
    schema_version: 2,
    case_plan_sha256: createHash('sha256').update(plan).digest('hex'),
    case_id,
    check_id: 'node-test',
    checkout_sha: execFileSync(process.env.VAULT_EXAMPLE_PYTHON || 'python3', [
      fileURLToPath(new URL('../../source_commit.py', import.meta.url)),
      app, fileURLToPath(import.meta.url), fileURLToPath(new URL('./case.json', import.meta.url)),
    ], { encoding: 'utf8' }).trim(),
    run_id: process.env.GITHUB_RUN_ID,
    attempt: process.env.GITHUB_RUN_ATTEMPT,
    environment: { os: process.platform, runtime: process.version },
    status: 'fail',
    evidence_sha256: createHash('sha256').update(evidence).digest('hex'),
  };
  try {
    assert.deepEqual(readObservation(evidence), { unit_cents: 125, quantity: 3, total_cents: 375 });
    for (const args of [
      [], ['125'], ['125', '3', 'extra'], ['', '3'], ['125', ' '],
      ['-1', '3'], ['1.5', '3'], ['9007199254740992', '1'], ['9007199254740991', '2'],
    ]) {
      const result = spawnSync(process.execPath, [app, ...args], { encoding: 'utf8' });
      assert.ifError(result.error);
      assert.equal(result.status, 1, `expected quote rejection for ${JSON.stringify(args)}`);
      assert.equal(result.stdout, '');
      assert.match(result.stderr, /Expected/);
    }
    receipt.status = 'pass';
  } finally {
    writeFileSync(join(process.env.VAULT_EXAMPLE_RECEIPTS, 'node.json'), JSON.stringify(receipt) + '\n');
  }
});
