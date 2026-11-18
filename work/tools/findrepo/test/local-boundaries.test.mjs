import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, writeFileSync, readFileSync, existsSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const cli = fileURLToPath(new URL('../skills/findrepo/scripts/findrepo.mjs', import.meta.url));
function withSandbox(fn) {
  const dir = mkdtempSync(join(tmpdir(), 'findrepo-local-test-'));
  try { return fn(dir); } finally { rmSync(dir, { recursive: true, force: true }); }
}
function research(dir, moreEnv = {}, cache = false) {
  const log = join(dir, 'gh-was-called');
  writeFileSync(join(dir, 'gh'), `#!/bin/sh\necho called > '${log}'\necho fake-gh-token\n`, { mode: 0o755 });
  const code = `
    import { findRepos } from ${JSON.stringify(new URL('file://' + cli).href)};
    const seen = [];
    globalThis.fetch = async (url, opts) => {
      seen.push(opts.headers.Authorization ?? null);
      return { status: 200, json: async () => ({ items: [] }), headers: new Headers() };
    };
    await findRepos('queue');
    console.log(JSON.stringify(seen));
  `;
  const res = spawnSync(process.execPath, ['--input-type=module', '-e', code], {
    env: { PATH: dir, HOME: dir, TMPDIR: dir, FINDREPO_NO_CACHE: cache ? '' : '1',
      GITHUB_TOKEN: 'fake-env-token', ...moreEnv }, encoding: 'utf8', timeout: 15000,
  });
  assert.equal(res.status, 0, res.stderr);
  return { seen: JSON.parse(res.stdout.trim()), ghCalled: existsSync(log), dir };
}

test('default research does not read gh auth or send inherited tokens', () => withSandbox(dir => {
  const r = research(dir);
  assert.equal(r.ghCalled, false);
  assert.ok(r.seen.length > 0);
  assert.ok(r.seen.every(v => v === null));
}));

test('environment auth requires explicit opt-in and still does not invoke gh', () => withSandbox(dir => {
  const r = research(dir, { FINDREPO_ALLOW_AUTH: '1' });
  assert.equal(r.ghCalled, false);
  assert.ok(r.seen.every(v => v === 'Bearer fake-env-token'));
}));

test('authenticated responses are not written to shared public cache', () => withSandbox(dir => {
  research(dir, { FINDREPO_ALLOW_AUTH: '1' }, true);
  assert.equal(existsSync(join(dir, 'openbot-findrepo-public-cache')), false);
}));

test('init cannot mutate project instructions by default', () => withSandbox(dir => {
  const target = join(dir, 'AGENTS.md');
  writeFileSync(target, 'retain this\n');
  const r = spawnSync(process.execPath, [cli, 'init', '--file', target], {
    env: { PATH: dir, HOME: dir }, encoding: 'utf8', timeout: 5000,
  });
  assert.notEqual(r.status, 0);
  assert.match(r.stderr, /writes are disabled/);
  assert.equal(readFileSync(target, 'utf8'), 'retain this\n');
}));
