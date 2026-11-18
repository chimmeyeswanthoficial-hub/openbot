// Actual headless browser test; ephemeral state and no real providers/upstream e2e.
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { chromium } from '../apps/bot-hq/node_modules/playwright/index.mjs';

const root = fileURLToPath(new URL('../', import.meta.url));
const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'openbot-hq-browser-'));
const code = crypto.randomBytes(32).toString('hex');
const child = spawn(process.execPath, [path.join(root, 'apps/bot-hq/server/dist/local-entry.js')], {
  cwd: root, env: { PATH: '/usr/local/bin:/usr/bin:/bin', HQ_LOCAL_ONLY: '1',
    HQ_ACCESS_CODE: code, SESSION_SECRET: crypto.randomBytes(32).toString('hex'), PORT: '0',
    DB_PATH: path.join(temp, 'hq.sqlite3'), HQ_KERNEL_STATE_DIR: path.join(temp, 'kernel'),
    OPENBOT_PROJECT_ROOT: root, OPENBOT_PYTHON: process.env.OPENBOT_PYTHON ?? path.join(root, '.venv/bin/python') },
  stdio: ['ignore', 'pipe', 'pipe'],
});
let logs = '';
child.stdout.on('data', chunk => { logs += chunk; });
child.stderr.on('data', chunk => { logs += chunk; });
const port = await new Promise((resolve, reject) => {
  const timeout = setTimeout(() => reject(new Error(`Local server did not start: ${logs}`)), 15_000);
  child.stdout.on('data', () => { const match = logs.match(/interface on port (\d+)/); if (match) { clearTimeout(timeout); resolve(Number(match[1])); } });
  child.once('exit', status => { clearTimeout(timeout); reject(new Error(`server exited ${status}: ${logs}`)); });
});
const origin = `http://127.0.0.1:${port}`;
let browser;
const failures = [], external = [];
try {
  browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
  page.on('pageerror', err => failures.push(err.message));
  await page.route('**/*', route => {
    if (!route.request().url().startsWith(origin)) { external.push(route.request().url()); return route.abort(); }
    return route.continue();
  });
  await page.goto(origin, { waitUntil: 'domcontentloaded' });
  await page.getByRole('heading', { name: 'OpenBot HQ', exact: true }).waitFor();
  await page.getByLabel('Local access code').fill(code);
  await page.getByRole('button', { name: 'Open local workspace', exact: true }).click();
  await page.getByRole('button', { name: 'Run company report', exact: true }).waitFor();
  await page.getByRole('button', { name: 'Run company report', exact: true }).click();
  await page.getByRole('status').filter({ hasText: 'Report saved' }).waitFor({ timeout: 15_000 });
  const reports = fs.readdirSync(path.join(temp, 'kernel/reports'));
  assert.equal(reports.length, 1);
  const receipt = JSON.parse(fs.readFileSync(path.join(temp, 'kernel/reports', reports[0]), 'utf8'));
  assert.equal(receipt.providers_enabled, false);
  assert.equal(receipt.inputs.length, 3);
  await page.getByLabel('Local note').fill('Browser-verified local note; not an outbound message.');
  await page.getByRole('button', { name: 'Save note', exact: true }).click();
  await page.getByText('Browser-verified local note; not an outbound message.', { exact: true }).waitFor();
  await page.reload({ waitUntil: 'domcontentloaded' });
  await page.getByText('Browser-verified local note; not an outbound message.', { exact: true }).waitFor();
  await page.screenshot({ path: path.join(root, 'audit/bot-hq-browser.png'), fullPage: true });
  assert.deepEqual(failures, [], 'no browser JavaScript exceptions');
  assert.deepEqual(external, [], 'no browser external network attempts');
  const result = { passed: true, profile: 'local-only', actualBrowser: 'Playwright Chromium',
    checks: ['sign-in', 'built UI', 'real kernel report and task', 'note save', 'reload persistence', 'no external browser requests', 'no JS exceptions'],
    kernelRun: receipt.run_id, providersEnabled: false,
    scope: 'Disposable local HTTP browser flow; no remote provider or hostile OS isolation proof.' };
  fs.writeFileSync(path.join(root, 'audit/bot-hq-browser.json'), JSON.stringify(result, null, 2) + '\n');
  console.log(JSON.stringify(result, null, 2));
} finally {
  await browser?.close();
  child.kill('SIGTERM');
  await new Promise(resolve => { if (child.exitCode !== null) resolve(); else child.once('exit', resolve); });
  fs.rmSync(temp, { recursive: true, force: true }); // only this test's disposable fixture
}
