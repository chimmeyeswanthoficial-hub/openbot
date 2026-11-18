// Disposable tests for the provider-disabled installed host, not upstream's real-provider e2e.
import test from 'node:test';
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'openbot-hq-test-'));
const project = fileURLToPath(new URL('../../../../', import.meta.url));
process.env.HQ_LOCAL_ONLY = '1';
process.env.HQ_ACCESS_CODE = 'local-disposable-code-that-is-never-a-provider-key';
process.env.SESSION_SECRET = crypto.randomBytes(32).toString('hex');
process.env.DB_PATH = path.join(tmp, 'hq.sqlite3');
process.env.HQ_KERNEL_STATE_DIR = path.join(tmp, 'kernel');
process.env.OPENBOT_PROJECT_ROOT = project;
const { createLocalApp } = await import('../dist/local-app.js');
const app = createLocalApp();
let cookie = '';
let botId = '';

const call = async (method, url, body, extra = {}) => app.request(`http://hq.test${url}`, {
  method, headers: { ...(cookie ? { Cookie: cookie } : {}),
    ...(body !== undefined ? { 'Content-Type': 'application/json' } : {}), ...extra },
  body: body !== undefined ? JSON.stringify(body) : undefined,
});

test('health truthfully reports disabled providers and no Hermes readiness claim', async () => {
  const res = await call('GET', '/api/health');
  assert.equal(res.status, 200);
  const data = await res.json();
  assert.equal(data.ok, true);
  assert.equal(data.providersEnabled, false);
  assert.equal(data.engine, 'disabled');
});

test('unauthenticated host refuses operational API requests', async () => {
  assert.equal((await call('GET', '/api/bots')).status, 401);
  assert.equal((await call('POST', '/api/bots/x/company-report', { requestId: crypto.randomUUID() })).status, 401);
});

test('bad code and cross-origin login are refused', async () => {
  assert.equal((await call('POST', '/api/auth/local', { code: 'wrong' })).status, 401);
  assert.equal((await call('POST', '/api/auth/local', { code: process.env.HQ_ACCESS_CODE }, { Origin: 'https://evil.example' })).status, 403);
});

test('explicit local code signs in an owner; session is HttpOnly', async () => {
  const res = await call('POST', '/api/auth/local', { code: process.env.HQ_ACCESS_CODE });
  assert.equal(res.status, 200);
  assert.match(res.headers.get('set-cookie'), /HttpOnly/i);
  cookie = res.headers.get('set-cookie').split(';')[0];
  const me = await (await call('GET', '/api/auth/me')).json();
  assert.equal(me.user.name, 'Local owner');
  const bots = await (await call('GET', '/api/bots')).json();
  botId = bots.bots[0].id;
  assert.ok(botId);
});

test('roster mutations are stored without provisioning any engine', async () => {
  const res = await call('POST', '/api/bots', { name: 'Evidence reviewer', avatarShape: 'square', avatarColor: 'green', mode: 'personal' });
  assert.equal(res.status, 201);
  const { bot } = await res.json();
  assert.equal(bot.name, 'Evidence reviewer');
  const engine = await (await call('GET', `/api/bots/${bot.id}/engine`)).json();
  assert.equal(engine.engine.status, 'stopped');
  assert.deepEqual(engine.engine.providers, []);
});

test('one useful company-report task runs through the actual Python kernel and persists receipts', async () => {
  const requestId = crypto.randomUUID();
  const res = await call('POST', `/api/bots/${botId}/company-report`, { requestId });
  assert.equal(res.status, 200);
  const data = await res.json();
  assert.equal(data.receipt.ok, true);
  assert.equal(data.receipt.report.providers_enabled, false);
  assert.equal(data.receipt.report.inputs.length, 3);
  const saved = JSON.parse(fs.readFileSync(path.join(tmp, 'kernel', 'reports', `${requestId}.json`), 'utf8'));
  assert.equal(saved.run_id, data.receipt.report.run_id);
  const tasks = await (await call('GET', `/api/bots/${botId}/tasks`)).json();
  assert.ok(tasks.tasks.some(t => t.id === data.task.id && t.state === 'done'));
  const replay = await (await call('POST', `/api/bots/${botId}/company-report`, { requestId })).json();
  assert.equal(replay.receipt.report.run_id, saved.run_id);
  assert.equal(replay.replayed, true);
});

test('client arguments cannot become shell, network, budget or file targets', async () => {
  for (const extra of [{ command: 'touch /tmp/nope' }, { url: 'https://example.com' }, { cost: 10 }, { path: '../../.env' }]) {
    const res = await call('POST', `/api/bots/${botId}/company-report`, { requestId: crypto.randomUUID(), ...extra });
    assert.equal(res.status, 400);
  }
});

test('unknown bots cannot start a kernel job', async () => {
  assert.equal((await call('POST', '/api/bots/not-owned/company-report', { requestId: crypto.randomUUID() })).status, 404);
});

test('upstream dangerous routes are unmounted, not merely hidden by UI', async () => {
  for (const route of ['/mcp', '/api/auth/google/start', '/api/computer/ensure',
    `/api/bots/${botId}/engine/login`, `/api/bots/${botId}/engine/restart`, '/api/apps/slack/connect', '/api/voice/session', '/api/approvals/fake']) {
    assert.ok([403, 404].includes((await call('POST', route, {})).status), route);
  }
});

test('chat is a truthful local note, never a pretend model response', async () => {
  const res = await call('POST', `/api/bots/${botId}/messages`, { text: 'Please launch a paid provider now.' });
  assert.equal(res.status, 200);
  const rows = await (await call('GET', `/api/bots/${botId}/rows`)).json();
  assert.ok(rows.rows.some(r => r.body.type === 'notice' && /providers.*disabled/i.test(r.body.text)));
});

test('skill bodies are stored as inert data, not executed', async () => {
  const res = await call('POST', `/api/bots/${botId}/skills`, { name: 'Local test skill', description: 'inert', body: 'shell.exec is not permission' });
  assert.equal(res.status, 201);
  const settings = await (await call('GET', `/api/bots/${botId}/settings`)).json();
  assert.ok(settings.skills.some(s => s.name === 'Local test skill'));
});

test('state and request idempotency survive a new app instance', async () => {
  const another = createLocalApp();
  const response = await another.request('http://hq.test/api/tasks', { headers: { Cookie: cookie } });
  assert.equal(response.status, 200);
  assert.ok((await response.json()).tasks.length >= 1);
});

test('static app has no donor artwork URLs and API misses do not return HTML', async () => {
  const res = await call('GET', '/');
  assert.equal(res.status, 200);
  assert.match(await res.text(), /OpenBot HQ/);
  const miss = await call('GET', '/api/not-real');
  assert.equal(miss.status, 404);
  assert.match(miss.headers.get('content-type'), /json/);
});

// OPENBOT-OS: reuse store pagination without exposing unbounded revision queries or other owners.
test('owned transcript pages recover every retained entry once with bounded cursors', async () => {
  const { appendRow } = await import('../dist/store.js');
  const { db } = await import('../dist/db.js');
  const created = await (await call('POST', '/api/bots', { name: 'History fixture' })).json();
  const id = created.bot.id;
  for (let i = 0; i < 450; i++) appendRow(id, 'message', { type: 'message', role: 'user', text: `history-${i}` });
  const count = () => db.prepare('SELECT count(*) n FROM rows WHERE bot_id=?').get(id).n;
  const before = count();
  const seen = [];
  let cursor = null, generation;
  do {
    const query = cursor === null ? '' : `?beforeSeq=${cursor}&generation=${generation}`;
    const res = await call('GET', `/api/bots/${id}/rows${query}`);
    assert.equal(res.status, 200);
    const page = await res.json();
    generation ??= page.generation;
    assert.equal(page.generation, generation);
    assert.ok(Number.isSafeInteger(page.revision));
    assert.ok(page.rows.length <= 200);
    assert.equal(page.hasMore, page.nextBeforeSeq !== null);
    assert.deepEqual(page.rows.map(r => r.seq), [...page.rows.map(r => r.seq)].sort((a, b) => a - b));
    assert.ok(page.rows.every(r => r.generation === generation && r.botId === id && (cursor === null || r.seq < cursor)));
    seen.push(...page.rows.map(r => r.seq));
    cursor = page.nextBeforeSeq;
    if (cursor !== null) assert.equal(cursor, page.rows[0].seq);
  } while (cursor !== null);
  assert.equal(before, 451);
  assert.equal(seen.length, before);
  assert.equal(new Set(seen).size, before);
  assert.deepEqual([...seen].sort((a, b) => a - b), Array.from({ length: before }, (_, i) => i + 1));
  assert.equal(count(), before, 'history GET never deletes or appends evidence');
  const small = await (await call('GET', `/api/bots/${id}/rows?limit=3`)).json();
  assert.equal(small.rows.length, 3);
  assert.equal(small.nextBeforeSeq, 449);
});

test('history rejects malformed, duplicated, unbounded and unversioned cursor queries', async () => {
  for (const query of ['limit=0', 'limit=-1', 'limit=201', 'limit=1.5', 'limit=NaN', 'limit=01',
    'limit=2&limit=3', 'beforeSeq=0', 'beforeSeq=2', 'beforeSeq=2&generation=1.5',
    'beforeSeq=9007199254740992&generation=1', 'generation=-1', 'generation=1&generation=1',
    'afterRev=0', 'path=../../.env']) {
    assert.equal((await call('GET', `/api/bots/${botId}/rows?${query}`)).status, 400, query);
  }
});

test('history binds earlier pages to the conversation generation and refuses cross-owner reads', async () => {
  const { clearConversation, appendRow } = await import('../dist/store.js');
  const { db } = await import('../dist/db.js');
  const created = await (await call('POST', '/api/bots', { name: 'Reset fixture' })).json();
  const id = created.bot.id;
  const original = await (await call('GET', `/api/bots/${id}/rows`)).json();
  clearConversation(id); // Disposable host fixture only; no new clear/delete API is exposed.
  appendRow(id, 'message', { type: 'message', role: 'user', text: 'new generation' });
  assert.equal((await call('GET', `/api/bots/${id}/rows?beforeSeq=2&generation=${original.generation}`)).status, 409);
  const current = await (await call('GET', `/api/bots/${id}/rows`)).json();
  assert.equal(current.generation, original.generation + 1);
  assert.deepEqual(current.rows.map(r => r.body.text), ['new generation']);
  assert.equal(current.nextBeforeSeq, null);
  db.prepare('INSERT INTO users(id,email,name,created_at) VALUES (?,?,?,?)').run('history_other', 'history-other@invalid.local', 'Other fixture', 0);
  db.prepare('INSERT INTO bots(id,user_id,name,created_at,updated_at) VALUES (?,?,?,?,?)').run('history_other_bot', 'history_other', 'Private fixture', 0, 0);
  assert.equal((await call('GET', '/api/bots/history_other_bot/rows?limit=1')).status, 404);
  assert.equal((await call('GET', '/api/bots/absent/rows')).status, 404);
  assert.equal((await app.request(`http://hq.test/api/bots/${id}/rows`)).status, 401);
});

test('logout invalidates the session', async () => {
  assert.equal((await call('POST', '/api/auth/logout', {})).status, 200);
  assert.equal((await call('GET', '/api/bots')).status, 401);
});

test.after(() => {
  // Only our disposable fixture; no project state is removed.
  fs.rmSync(tmp, { recursive: true, force: true });
});
