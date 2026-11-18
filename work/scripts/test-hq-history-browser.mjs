// Disposable real-browser history flow; no providers, primary state or upstream e2e suite.
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { chromium } from '../apps/bot-hq/node_modules/playwright/index.mjs';

const root = fileURLToPath(new URL('../', import.meta.url));
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'hq-history-browser-'));
const code = crypto.randomBytes(32).toString('hex');
const child = spawn(process.execPath, [path.join(root, 'apps/bot-hq/server/dist/local-entry.js')], {
  cwd: root, env: { PATH: '/usr/local/bin:/usr/bin:/bin', HQ_LOCAL_ONLY: '1',
    HQ_ACCESS_CODE: code, SESSION_SECRET: crypto.randomBytes(32).toString('hex'), PORT: '0',
    DB_PATH: path.join(temp, 'hq.sqlite3'), HQ_KERNEL_STATE_DIR: path.join(temp, 'kernel'),
    OPENBOT_PROJECT_ROOT: root, OPENBOT_PYTHON: process.env.OPENBOT_PYTHON ?? path.join(root, '.venv/bin/python') },
  stdio: ['ignore', 'pipe', 'pipe'],
});
let logs = '', browser;
child.stdout.on('data', chunk => { logs += chunk; });
child.stderr.on('data', chunk => { logs += chunk; });
try {
  const port = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`server startup timed out: ${logs}`)), 15_000);
    child.stdout.on('data', () => {
      const match = logs.match(/interface on port (\d+)/);
      if (match) { clearTimeout(timer); resolve(Number(match[1])); }
    });
    child.once('exit', status => { clearTimeout(timer); reject(new Error(`server exited ${status}: ${logs}`)); });
  });
  const origin = `http://127.0.0.1:${port}`;
  browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  const errors = [], external = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.route('**/*', route => {
    if (!route.request().url().startsWith(`${origin}/`)) {
      external.push(route.request().url()); return route.abort();
    }
    return route.continue();
  });
  await page.goto(origin, { waitUntil: 'domcontentloaded' });
  await page.getByLabel('Local access code').fill(code);
  await page.getByRole('button', { name: 'Open local workspace', exact: true }).click();
  await page.getByRole('button', { name: 'Run company report', exact: true }).waitFor();
  const { bots } = await (await page.request.get(`${origin}/api/bots`)).json();
  const id = bots[0].id;
  for (let i = 0; i < 225; i++) {
    const res = await page.request.post(`${origin}/api/bots/${id}/messages`, { data: { text: `history-note-${String(i).padStart(3, '0')}` } });
    assert.equal(res.status(), 200);
  }
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.getByText('history-note-224', { exact: true }).waitFor();
  assert.equal(await page.getByText('history-note-000', { exact: true }).count(), 0);
  const button = page.getByRole('button', { name: 'Load earlier entries', exact: true });
  await button.waitFor();
  const pattern = '**/api/bots/*/rows?beforeSeq=*';
  const refuse = route => route.fulfill({ status: 503, contentType: 'application/json', body: '{"error":"disposable test refusal"}' });
  await page.route(pattern, refuse);
  await button.click();
  await page.getByRole('alert').filter({ hasText: 'Could not load earlier entries' }).waitFor();
  assert.equal(await button.isEnabled(), true);
  assert.equal(await page.getByText('history-note-224', { exact: true }).count(), 1);
  await page.unroute(pattern, refuse);
  await button.click();
  await page.getByText('history-note-025', { exact: true }).waitFor();
  assert.equal(await page.getByText('history-note-000', { exact: true }).count(), 0);
  await button.click();
  await page.getByText('history-note-000', { exact: true }).waitFor();
  await button.waitFor({ state: 'detached' });
  assert.equal(await page.locator('.bubble__plain').count(), 225);
  assert.equal(await page.getByRole('alert').count(), 0);
  assert.deepEqual(errors, []);
  assert.deepEqual(external, []);
  const health = await (await page.request.get(`${origin}/api/health`)).json();
  assert.equal(health.providersEnabled, false);
  assert.equal((await (await page.request.get(`${origin}/api/tasks`)).json()).tasks.length, 0);
  const result = { task_date: '2026-11-10', observed_runner_utc: new Date().toISOString(),
    passed: true, browser: 'Playwright Chromium headless shell', retainedRows: 451, recoveredNotes: 225,
    checks: ['real authenticated built UI', 'newest 200 rows on reload', '503 shows retry without losing latest notes',
      'two earlier-page clicks recover all 451 rows / 225 notes without duplicates', 'button ends at oldest entry',
      'no JS exceptions', 'no external browser requests', 'providers still disabled; no tasks or kernel jobs created'],
    limits: ['disposable local HTTP only, not HTTPS/proxy-cookie/hostile-tenant proof', 'browser --no-sandbox is a test environment flag, not workload isolation'] };
  fs.writeFileSync(path.join(root, 'audit/hq-history-browser.json'), JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify(result, null, 2));
} finally {
  await browser?.close();
  child.kill('SIGTERM');
  await new Promise(resolve => { if (child.exitCode !== null || child.signalCode !== null) resolve(); else child.once('exit', resolve); });
  fs.rmSync(temp, { recursive: true, force: true }); // This script's temporary fixture only.
}
