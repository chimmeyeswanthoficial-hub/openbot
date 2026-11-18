// OPENBOT-OS: provider-disabled local profile. Do NOT import routes/engine/loop/computer here.
// Reuses Bot HQ's MIT database, store, sessions and event hub; business execution stays in Python.
import crypto from 'node:crypto';
import { execFile } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Hono } from 'hono';
import { bodyLimit } from 'hono/body-limit';
import { streamSSE } from 'hono/streaming';
import { serveStatic } from '@hono/node-server/serve-static';
import { env } from './env.js';
import { db, now } from './db.js';
import './db-config.js';
import { createSession, destroySession, requireUser, userFromCookieHeader, type AuthVars } from './lib/auth.js';
import { hub } from './lib/hub.js';
import { newId } from './lib/ids.js';
import { allLive, appendRow, emitBot, getBot, getBotRow, listBots, listRows, listTasks, toTask } from './store.js';

if (process.env.HQ_LOCAL_ONLY !== '1') throw new Error('Only the explicit HQ_LOCAL_ONLY=1 profile is supported.');
const accessCode = process.env.HQ_ACCESS_CODE ?? '';
if (accessCode.length < 32 || env.sessionSecret.length < 32) throw new Error('Local access code and session secret must each have at least 32 characters.');
const root = path.resolve(process.env.OPENBOT_PROJECT_ROOT ?? fileURLToPath(new URL('../../../../', import.meta.url)));
const kernelState = path.resolve(process.env.HQ_KERNEL_STATE_DIR ?? path.join(root, '.openbot/hq-kernel'));
const webDist = fileURLToPath(new URL('../../web/dist/', import.meta.url));
const ownerId = 'user_local_owner';
let kernelBusy = false;
const streams = new Map<string, number>();

// Local UX jobs, not the accounting ledger. Kernel audit lives in a different SQLite database.
db.exec(`CREATE TABLE IF NOT EXISTS hq_jobs (
  request_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, bot_id TEXT NOT NULL,
  task_id TEXT NOT NULL, status TEXT NOT NULL, receipt TEXT, updated_at INTEGER NOT NULL
)`);

function sameCode(candidate: unknown): boolean {
  if (typeof candidate !== 'string' || candidate.length > 256) return false;
  const a = crypto.createHash('sha256').update(accessCode).digest();
  const b = crypto.createHash('sha256').update(candidate).digest();
  return crypto.timingSafeEqual(a, b);
}
function ownBot(userId: string, id: string) {
  const bot = getBotRow(id);
  return bot && bot.user_id === userId ? bot : null;
}
function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('invalid body');
  return value as Record<string, unknown>;
}
const text = (value: unknown, max: number, fallback = '') => typeof value === 'string' ? value.trim().slice(0, max) : fallback;
const listSkills = (botId: string) => (db.prepare('SELECT * FROM skills WHERE bot_id=? ORDER BY created_at').all(botId) as any[])
  .map(s => ({ id: s.id, botId: s.bot_id, name: s.name, description: s.description, body: s.body, createdAt: s.created_at, updatedAt: s.updated_at }));
const computer = { status: 'stopped', orgoId: null, screens: [], maxScreens: 0, error: 'Computer and all providers are disabled in this local profile.' };

function createBot(name: string, userId: string, primary = false, fields: Record<string, unknown> = {}) {
  const count = (db.prepare('SELECT count(*) n FROM bots WHERE user_id=?').get(userId) as any).n;
  if (count >= 8) throw new Error('local roster limit');
  const id = newId('bot');
  db.prepare('INSERT INTO bots(id,user_id,name,label,description,instructions,avatar_shape,avatar_color,mode,is_primary,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)')
    .run(id, userId, name || 'Local bot', primary ? 'Company evidence' : '',
      'Local notes, skills and governed evidence reports. No live agent attached.', '',
      text(fields.avatarShape, 24, 'square'), text(fields.avatarColor, 24, 'blue'), 'personal', primary ? 1 : 0, now(), now());
  // Deliberately NO engine assignment/provisioning, screen allocation or shell startup.
  appendRow(id, 'notice', { type: 'notice', text: 'Local profile: providers are disabled. Chat saves notes; use Run company report for an audited local tool.', tone: 'info' });
  hub.emit(userId, { type: 'roster' });
  return getBot(id)!;
}
function ensureOwner() {
  db.prepare('INSERT OR IGNORE INTO users(id,email,name,created_at) VALUES (?,?,?,?)')
    .run(ownerId, 'local-owner@invalid.local', 'Local owner', now());
  if (!listBots(ownerId).length) createBot('Company desk', ownerId, true);
}
function runKernel(requestId: string): Promise<any> {
  return new Promise((resolve, reject) => {
    // Only startup configuration controls these executable/path arguments, not a web request.
    // Minimal child environment deliberately does not inherit any model, payment, OAuth or SSH keys.
    const child = execFile(process.env.OPENBOT_PYTHON ?? 'python3', [
      path.join(root, 'scripts/hq_readiness.py'), '--root', root, '--state-dir', kernelState,
    ], { cwd: root, timeout: 15_000, killSignal: 'SIGKILL', maxBuffer: 512_000,
      env: { PATH: '/usr/local/bin:/usr/bin:/bin', LANG: 'C.UTF-8', PYTHONNOUSERSITE: '1', PYTHONDONTWRITEBYTECODE: '1' },
    }, (err, stdout) => {
      if (err) return reject(new Error('Kernel unavailable; do not rerun an uncertain job automatically.'));
      try {
        const value = JSON.parse(stdout);
        if (typeof value?.ok !== 'boolean' || typeof value?.executed !== 'boolean') throw new Error('invalid kernel receipt');
        if (value.ok && (!value.report?.run_id || value.report.providers_enabled !== false || value.report.cost_usd !== 0 || !Array.isArray(value.audit_seqs) || value.audit_seqs.length < 6 || !/^[a-f0-9]{64}$/.test(value.report_sha256))) throw new Error('incomplete kernel receipt');
        resolve(value);
      } catch { reject(new Error('Malformed kernel receipt; no completion claimed.')); }
    });
    child.stdin?.end(JSON.stringify({ request_id: requestId, action: 'company.readiness' }));
  });
}

export function createLocalApp() {
  const app = new Hono<AuthVars>();
  app.onError((_err, c) => c.json({ error: 'Local request failed; no external action was attempted.' }, 400));
  app.use('*', async (c, next) => {
    c.header('X-Content-Type-Options', 'nosniff');
    c.header('Referrer-Policy', 'no-referrer');
    // Allow embedding in the workspace preview, while restricting this app's own resource egress.
    c.header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'");
    if (c.req.path.startsWith('/api/')) c.header('Cache-Control', 'no-store');
    await next();
  });
  app.use('/api/*', bodyLimit({ maxSize: 65_536, onError: c => c.json({ error: 'body too large' }, 413) }));
  app.use('/api/*', async (c, next) => {
    if (!['GET', 'HEAD', 'OPTIONS'].includes(c.req.method)) {
      const origin = c.req.header('origin');
      if (origin) {
        try { if (new URL(origin).host !== c.req.header('host') && new URL(origin).host !== new URL(c.req.url).host) return c.json({ error: 'cross-origin write refused' }, 403); }
        catch { return c.json({ error: 'invalid origin' }, 403); }
      }
      if (!/^application\/json(?:;|$)/i.test(c.req.header('content-type') ?? '')) return c.json({ error: 'JSON required' }, 415);
    }
    await next();
  });
  app.get('/api/health', c => c.json({ ok: !!db.prepare('SELECT 1 ready').get(), profile: 'local-only', providersEnabled: false, engine: 'disabled' }));
  app.get('/api/auth/me', c => c.json({ user: userFromCookieHeader(c.req.header('cookie')), devLogin: false, localOnly: true }));
  // One global bounded throttle avoids an unbounded per-IP map or trusting spoofed forwarded IPs.
  let loginAttempts = 0, loginWindow = now();
  app.post('/api/auth/local', async c => {
    if (now() - loginWindow > 60_000) { loginAttempts = 0; loginWindow = now(); }
    if (++loginAttempts > 20) return c.json({ error: 'Try again in one minute.' }, 429);
    const body = object(await c.req.json());
    if (Object.keys(body).length !== 1 || !sameCode(body.code)) return c.json({ error: 'Invalid local access code' }, 401);
    ensureOwner();
    createSession(c, ownerId);
    return c.json({ ok: true });
  });
  app.post('/api/auth/logout', c => { destroySession(c); return c.json({ ok: true }); });
  app.use('/api/*', requireUser);

  app.get('/api/bots', c => c.json({ bots: listBots(c.get('user').id), live: allLive(c.get('user').id) }));
  app.post('/api/bots', async c => {
    const fields = object(await c.req.json());
    if (Object.keys(fields).some(k => !['name', 'avatarShape', 'avatarColor', 'mode'].includes(k))) return c.json({ error: 'unsupported bot fields' }, 400);
    const name = text(fields.name, 60);
    if (!name) return c.json({ error: 'name required' }, 400);
    return c.json({ bot: createBot(name, c.get('user').id, false, fields) }, 201);
  });
  // OPENBOT-OS: bounded read-only history reuses store.ts; never mount upstream routes.ts.
  app.get('/api/bots/:id/rows', c => {
    const b = ownBot(c.get('user').id, c.req.param('id'));
    if (!b) return c.json({ error: 'not found' }, 404);
    const query = c.req.queries();
    if (Object.entries(query).some(([key, values]) => !['beforeSeq', 'generation', 'limit'].includes(key) || values.length !== 1)) return c.json({ error: 'Invalid history query. Reload the conversation.' }, 400);
    const integer = (key: string, fallback?: number) => {
      const value = query[key]?.[0];
      if (value === undefined) return fallback;
      if (!/^[1-9]\d*$/.test(value) || !Number.isSafeInteger(Number(value))) throw new Error('invalid history cursor');
      return Number(value);
    };
    const limit = integer('limit', 200)!;
    const beforeSeq = integer('beforeSeq'), generation = integer('generation');
    if (limit > 200 || (beforeSeq !== undefined && generation === undefined)) return c.json({ error: 'Invalid history query. Reload the conversation.' }, 400);
    if (generation !== undefined && generation !== b.generation) return c.json({ error: 'This conversation changed. Reload its latest entries.' }, 409);
    const found = listRows(b.id, { beforeSeq, limit: limit + 1 });
    const hasMore = found.length > limit;
    const rows = hasMore ? found.slice(1) : found;
    return c.json({ generation: b.generation, revision: b.rev, rows, hasMore, nextBeforeSeq: hasMore ? rows[0].seq : null });
  });
  app.post('/api/bots/:id/read', c => {
    const b = ownBot(c.get('user').id, c.req.param('id'));
    if (!b) return c.json({ error: 'not found' }, 404);
    db.prepare('UPDATE bots SET unread=0 WHERE id=?').run(b.id);
    return c.json({ ok: true });
  });
  app.post('/api/bots/:id/messages', async c => {
    const b = ownBot(c.get('user').id, c.req.param('id'));
    if (!b) return c.json({ error: 'not found' }, 404);
    const body = object(await c.req.json());
    const note = text(body.text, 16_000);
    if (!note || Object.keys(body).some(k => k !== 'text')) return c.json({ error: 'text only' }, 400);
    const row = appendRow(b.id, 'message', { type: 'message', role: 'user', text: note });
    appendRow(b.id, 'notice', { type: 'notice', text: 'Note saved. Providers are disabled; no model or tool ran.', tone: 'info' });
    emitBot(b.id);
    return c.json({ row });
  });
  app.patch('/api/bots/:id', async c => {
    const b = ownBot(c.get('user').id, c.req.param('id'));
    if (!b) return c.json({ error: 'not found' }, 404);
    const fields = object(await c.req.json());
    const columns: Record<string, [string, number]> = { name: ['name', 60], label: ['label', 100], description: ['description', 2000], instructions: ['instructions', 20_000], avatarShape: ['avatar_shape', 24], avatarColor: ['avatar_color', 24] };
    if (Object.keys(fields).some(k => !columns[k])) return c.json({ error: 'Only inert local bot fields may change.' }, 400);
    db.transaction(() => { for (const [key, value] of Object.entries(fields)) {
      const [column, limit] = columns[key];
      db.prepare(`UPDATE bots SET ${column}=?, updated_at=? WHERE id=?`).run(text(value, limit), now(), b.id);
    } })();
    emitBot(b.id);
    return c.json({ bot: getBot(b.id) });
  });
  app.get('/api/tasks', c => c.json({ tasks: (db.prepare('SELECT t.* FROM tasks t JOIN bots b ON b.id=t.bot_id WHERE b.user_id=? ORDER BY t.updated_at DESC').all(c.get('user').id) as any[]).map(toTask) }));
  app.get('/api/bots/:id/tasks', c => ownBot(c.get('user').id, c.req.param('id')) ? c.json({ tasks: listTasks(c.req.param('id')) }) : c.json({ error: 'not found' }, 404));
  app.get('/api/bots/:id/routines', c => ownBot(c.get('user').id, c.req.param('id')) ? c.json({ routines: [] }) : c.json({ error: 'not found' }, 404));
  app.get('/api/bots/:id/engine', c => ownBot(c.get('user').id, c.req.param('id')) ? c.json({ engine: { botId: c.req.param('id'), profile: 'local-only', status: 'stopped', error: 'Providers disabled', model: null, provider: null, version: null, providers: [], ownScreen: false } }) : c.json({ error: 'not found' }, 404));
  app.get('/api/bots/:id/settings', c => {
    const id = c.req.param('id');
    if (!ownBot(c.get('user').id, id)) return c.json({ error: 'not found' }, 404);
    return c.json({ skills: listSkills(id), memories: [], routines: [], tasks: listTasks(id), memory: { lastConsolidatedAt: null, historyChars: 0, compactAtChars: 0, lastCompaction: null } });
  });
  app.post('/api/bots/:id/skills', async c => {
    const b = ownBot(c.get('user').id, c.req.param('id'));
    if (!b) return c.json({ error: 'not found' }, 404);
    const fields = object(await c.req.json());
    if (Object.keys(fields).some(k => !['name', 'body', 'description'].includes(k))) return c.json({ error: 'unsupported skill fields' }, 400);
    const name = text(fields.name, 80), body = text(fields.body, 20_000);
    if (!name || !body) return c.json({ error: 'name and body required' }, 400);
    const id = newId('skl');
    db.prepare('INSERT INTO skills(id,bot_id,name,body,description,created_at,updated_at) VALUES (?,?,?,?,?,?,?)')
      .run(id, b.id, name, body, text(fields.description, 300), now(), now());
    return c.json({ skill: listSkills(b.id).find(s => s.id === id) }, 201);
  });
  app.get('/api/computer', c => c.json({ computer }));
  app.get('/api/computer/details', c => c.json({ computer, screens: [], hibernation: { idleMinutes: 0, viewers: 0, dryRun: true } }));
  app.get('/api/apps', c => c.json({ apps: [], connected: [], connectedApps: [], categories: [], total: 0 }));
  app.get('/api/policies', c => c.json({ policies: [] }));
  app.get('/api/bots/:id/files', c => ownBot(c.get('user').id, c.req.param('id')) ? c.json({ status: 'asleep', path: '', files: [], error: 'General filesystem access is disabled. Reports are in the transcript.' }) : c.json({ error: 'not found' }, 404));

  app.post('/api/bots/:id/company-report', async c => {
    const user = c.get('user'), b = ownBot(user.id, c.req.param('id'));
    if (!b) return c.json({ error: 'not found' }, 404);
    const body = object(await c.req.json());
    if (Object.keys(body).length !== 1 || typeof body.requestId !== 'string' || !/^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/.test(body.requestId)) return c.json({ error: 'Only a canonical requestId is accepted.' }, 400);
    const requestId = body.requestId;
    const existing = db.prepare('SELECT * FROM hq_jobs WHERE request_id=?').get(requestId) as any;
    if (existing) {
      if (existing.user_id !== user.id || existing.bot_id !== b.id) return c.json({ error: 'request identity conflict' }, 409);
      if (!existing.receipt) return c.json({ error: 'Interrupted/active job requires reconciliation; it was not rerun.', requestId }, 409);
      return c.json({ receipt: JSON.parse(existing.receipt), task: listTasks(b.id).find(t => t.id === existing.task_id), replayed: true });
    }
    if (kernelBusy) return c.json({ error: 'One bounded kernel report is already running.' }, 409);
    const taskId = newId('task');
    db.transaction(() => {
      db.prepare('INSERT INTO hq_jobs(request_id,user_id,bot_id,task_id,status,updated_at) VALUES (?,?,?,?,?,?)').run(requestId, user.id, b.id, taskId, 'running', now());
      db.prepare('INSERT INTO tasks(id,bot_id,title,state,note,created_at,updated_at) VALUES (?,?,?,?,?,?,?)').run(taskId, b.id, 'Company readiness evidence', 'working', 'Waiting for independent Sentinel audit and a fixed local report.', now(), now());
    })();
    kernelBusy = true;
    hub.emit(user.id, { type: 'tasks', botId: b.id });
    try {
      const receipt = await runKernel(requestId);
      const note = receipt.ok ? `Kernel ${receipt.report.run_id}; ${receipt.audit_seqs.length} audit rows; zero provider cost. Recorded evidence, not a new verification run.` : `Refused: ${String(receipt.code ?? 'unknown')}. No external action attempted.`;
      db.transaction(() => {
        db.prepare('UPDATE hq_jobs SET status=?,receipt=?,updated_at=? WHERE request_id=?').run(receipt.ok ? 'done' : 'refused', JSON.stringify(receipt), now(), requestId);
        db.prepare('UPDATE tasks SET state=?,note=?,updated_at=? WHERE id=?').run(receipt.ok ? 'done' : 'needs_input', note, now(), taskId);
        appendRow(b.id, 'notice', { type: 'notice', text: note, tone: receipt.ok ? 'info' : 'warn' });
        if (receipt.ok) appendRow(b.id, 'message', { type: 'message', role: 'assistant', text: `Deterministic local kernel report, not an AI answer.\n\n\`\`\`json\n${JSON.stringify(receipt.report, null, 2)}\n\`\`\`` });
      })();
      emitBot(b.id);
      return c.json({ receipt, task: listTasks(b.id).find(t => t.id === taskId), replayed: false });
    } catch {
      // Keep receipt NULL: a crash/timeout is NOT proof that the kernel did nothing.
      db.prepare('UPDATE hq_jobs SET status=?,updated_at=? WHERE request_id=?').run('uncertain', now(), requestId);
      db.prepare('UPDATE tasks SET state=?,note=?,updated_at=? WHERE id=?').run('needs_input', 'Kernel outcome uncertain. Inspect audit/marker/report before retrying; no automatic rerun.', now(), taskId);
      return c.json({ error: 'Kernel unavailable or receipt invalid; manual reconciliation required.', requestId }, 503);
    } finally { kernelBusy = false; hub.emit(user.id, { type: 'tasks', botId: b.id }); }
  });

  app.get('/api/events', c => {
    const user = c.get('user');
    if ((streams.get(user.id) ?? 0) >= 4) return c.json({ error: 'stream limit' }, 429);
    streams.set(user.id, (streams.get(user.id) ?? 0) + 1);
    return streamSSE(c, async stream => {
      const queue: string[] = [];
      let wake: (() => void) | undefined;
      let timer: ReturnType<typeof setTimeout> | undefined;
      const unsub = hub.subscribe(user.id, event => { if (queue.length < 128) queue.push(JSON.stringify(event)); else void stream.close(); wake?.(); });
      stream.onAbort(() => wake?.());
      try {
        await stream.writeSSE({ data: JSON.stringify({ type: 'hello', serverTime: now() }) });
        while (!stream.aborted && !stream.closed) {
          if (!queue.length) await new Promise<void>(resolve => { wake = resolve; timer = setTimeout(resolve, 20_000); });
          clearTimeout(timer);
          wake = undefined;
          if (!stream.aborted && !stream.closed) await stream.writeSSE({ data: queue.shift() ?? JSON.stringify({ type: 'ping' }) });
        }
      } finally { clearTimeout(timer); unsub(); streams.set(user.id, Math.max(0, (streams.get(user.id) ?? 1) - 1)); }
    });
  });

  app.all('/api/*', c => c.json({ error: 'Not supported in local-only profile; providers, permissions and execution cannot be enabled by this API.' }, 404));
  app.all('/mcp/*', c => c.json({ error: 'MCP is disabled' }, 404));
  if (fs.existsSync(path.join(webDist, 'index.html'))) {
    app.use('/*', serveStatic({ root: path.relative(process.cwd(), webDist) }));
    app.get('*', c => c.html(fs.readFileSync(path.join(webDist, 'index.html'), 'utf8')));
  }
  return app;
}
