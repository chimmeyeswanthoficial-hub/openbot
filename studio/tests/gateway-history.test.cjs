// Dedicated protocol unit tests for Authenticated History in gateway-session.js.
// Real WebCrypto ECDSA P-256 proofs with a mock transport.
// No network, live model, external agent or production key involved.
'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const {webcrypto, createHash, randomBytes} = require('node:crypto');
const {Session, liveLocation, allowed, historyScopes, THREAD_ID, MESSAGE_ID} = require('../web/gateway-session.js');

const hash = s => createHash('sha256').update(s).digest('hex');
const canonical = v => v === null || typeof v !== 'object' ? JSON.stringify(v) : Array.isArray(v) ? '[' + v.map(canonical).join(',') + ']' : '{' + Object.keys(v).sort().map(k => JSON.stringify(k) + ':' + canonical(v[k])).join(',') + '}';
const origin = {protocol: 'https:', origin: 'https://history.invalid', pathname: '/control/', search: ''};
const code = 'h'.repeat(43);
const threadId = 'c' + '1'.repeat(32);
const messageId = 'm' + '2'.repeat(32);

function fixture(options = {}) {
  let mono = 100, online = true, pub;
  const requests = [], challenges = new Map();
  const defaultScopes = ['read', 'revoke-self', 'history-read', 'history-write', 'history-delete'];
  const data = {
    role: 'owner',
    device: 'd'.repeat(32),
    venture: 'alpha',
    scopes: options.scopes || defaultScopes,
    expires: 1700000900,
    ...options.pairing
  };

  const threads = [{id: threadId, title: 'Test Conversation'}];
  const events = [{
    sequence: 0,
    type: 'CUSTOM',
    name: 'openbot.user_message.v1',
    value: {
      thread_id: threadId,
      message_id: messageId,
      role: 'user',
      author: 'human:alice',
      text: 'Hello authenticated world.',
      source: 'authenticated_human_input'
    }
  }];

  function envelope(value) {
    return {
      api_version: '1',
      server_id: 'a'.repeat(64),
      observed_at: 1700000000,
      fresh_for_seconds: 15,
      source: 'local_authenticated_server',
      data: value
    };
  }

  const subtle = new Proxy(webcrypto.subtle, {
    get(target, k) {
      const v = target[k];
      return typeof v === 'function' ? v.bind(target) : v;
    }
  });

  const transport = async (path, request) => {
    requests.push({path, ...request});
    const body = request.body ? JSON.parse(request.body) : null;
    let value;

    if (path === '/api/v1/identity') {
      value = {client_version: '0.2.0', client_sha256: 'e'.repeat(64), tls_required: true, mode: 'local_owned_fixture', public_or_production_release: false};
    } else if (path === '/api/v1/pair') {
      pub = await webcrypto.subtle.importKey('spki', Buffer.from(body.public_key, 'base64url'), {name: 'ECDSA', namedCurve: 'P-256'}, true, ['verify']);
      assert(await webcrypto.subtle.verify({name: 'ECDSA', hash: 'SHA-256'}, pub, Buffer.from(body.signature, 'base64url'), Buffer.from('openbot.pair/1\n' + 'a'.repeat(64) + '\n' + code)));
      value = data;
    } else if (path === '/api/v1/challenge') {
      const nonce = randomBytes(24).toString('base64url'), expires = 1700000030;
      value = {id: nonce, expires, message: ['openbot.control-request/1', 'a'.repeat(64), data.device, nonce, body.method, body.path, body.body_sha256, String(expires)].join('\n')};
      challenges.set(nonce, {...body, ...value});
    } else {
      const c = challenges.get(request.headers['X-OpenBot-Challenge']);
      assert(c, 'one-use challenge required');
      challenges.delete(c.id);
      assert.equal(c.method, request.method);
      assert.equal(c.path, path);
      assert.equal(c.body_sha256, hash(request.body || ''));
      assert(await webcrypto.subtle.verify({name: 'ECDSA', hash: 'SHA-256'}, pub, Buffer.from(request.headers['X-OpenBot-Signature'], 'base64url'), Buffer.from(c.message)));

      if (options.failAfterChallenge) throw Error('synthetic timeout or 503 after possible commit');

      if (path === '/api/v1/snapshot') {
        value = {status: {execution_mode: 'fixed_owned_qa_only', paid_provider_enabled: false, customer_execution_enabled: false}, tasks: [], audit: [], exact_book: {summary: {}, postings: []}};
      } else if (path === '/api/v1/conversations/list') {
        value = {history_api_version: '1', history_only: true, agent_executed: false, source: 'application_sqlite_journal', threads, has_more: false, next_after: null};
      } else if (path === '/api/v1/conversations/create') {
        value = {history_api_version: '1', history_only: true, agent_executed: false, source: 'application_sqlite_journal', thread_id: body.thread_id};
      } else if (path === '/api/v1/conversations/' + threadId + '/read') {
        value = {history_api_version: '1', history_only: true, agent_executed: false, source: 'application_sqlite_journal', events, has_more: false, next_after: null};
      } else if (path === '/api/v1/conversations/' + threadId + '/messages') {
        value = {history_api_version: '1', history_only: true, agent_executed: false, source: 'application_sqlite_journal', thread_id: threadId, message_id: body.message_id, sequence: body.expected_sequence + 1};
      } else if (path === '/api/v1/conversations/' + threadId + '/delete') {
        value = {history_api_version: '1', history_only: true, agent_executed: false, source: 'application_sqlite_journal', thread_id: threadId, deleted: true, secure_erasure: false};
      } else {
        throw Error('unexpected history test route: ' + path);
      }
    }
    return {ok: true, json: async () => JSON.parse(JSON.stringify(envelope(value)))};
  };

  const session = new Session({location: origin, transport, crypto: {subtle}, now: () => mono, online: () => online});
  return {
    session,
    requests,
    options,
    setTime: v => { mono = v; },
    setOnline: v => { online = v; },
    async pair() {
      await session.identify();
      return session.pair(code, 'Test Device');
    }
  };
}

test('history scopes and regex patterns are exported correctly', () => {
  assert(historyScopes.has('history-read'));
  assert(historyScopes.has('history-write'));
  assert(historyScopes.has('history-delete'));
  assert.equal(historyScopes.size, 3);
  assert(THREAD_ID.test('c' + '0'.repeat(32)));
  assert(!THREAD_ID.test('m' + '0'.repeat(32)));
  assert(MESSAGE_ID.test('m' + 'f'.repeat(32)));
  assert(!MESSAGE_ID.test('c' + 'f'.repeat(32)));
});

test('allowed routes permit all valid history POST endpoints and reject invalid methods or paths', () => {
  assert(allowed('POST', '/api/v1/conversations/list'));
  assert(allowed('POST', '/api/v1/conversations/create'));
  assert(allowed('POST', '/api/v1/conversations/' + threadId + '/read'));
  assert(allowed('POST', '/api/v1/conversations/' + threadId + '/messages'));
  assert(allowed('POST', '/api/v1/conversations/' + threadId + '/delete'));

  // Disallowed: GET, invalid paths, directory traversals, query strings
  assert(!allowed('GET', '/api/v1/conversations/list'));
  assert(!allowed('GET', '/api/v1/conversations/' + threadId + '/read'));
  assert(!allowed('POST', '/api/v1/conversations/c123/read')); // wrong length ID
  assert(!allowed('POST', '/api/v1/conversations/../admin'));
  assert(!allowed('POST', '/api/v1/conversations/' + threadId + '/read?query=1'));
  assert(!allowed('DELETE', '/api/v1/conversations/' + threadId + '/delete'));
});

test('viewer role can pair with history-read but not history-write or history-delete', async () => {
  // Valid viewer with history-read
  const f1 = fixture({pairing: {role: 'viewer', scopes: ['read', 'revoke-self', 'history-read']}});
  assert(await f1.pair());
  assert(f1.session.can('history-read'));
  assert(!f1.session.can('history-write'));
  assert(!f1.session.can('history-delete'));

  // Invalid viewer attempting history-write
  const f2 = fixture({pairing: {role: 'viewer', scopes: ['read', 'revoke-self', 'history-read', 'history-write']}});
  await assert.rejects(f2.pair(), /server-derived/);

  // Invalid viewer attempting history-delete
  const f3 = fixture({pairing: {role: 'viewer', scopes: ['read', 'revoke-self', 'history-delete']}});
  await assert.rejects(f3.pair(), /server-derived/);
});

test('historyList requires fresh history-read scope and valid bounds', async () => {
  const f = fixture();
  await f.pair();
  assert(f.session.can('history-read'));

  // Successful call
  const list = await f.session.historyList('', 50);
  assert.equal(list.history_api_version, '1');
  assert.equal(list.threads.length, 1);
  assert.equal(list.threads[0].id, threadId);

  // Pagination parameters validation
  await assert.rejects(f.session.historyList('bad-id', 50), /Invalid history list parameters/);
  await assert.rejects(f.session.historyList('', 0), /Invalid history list parameters/);
  await assert.rejects(f.session.historyList('', 101), /Invalid history list parameters/);
  await assert.rejects(f.session.historyList('', '50'), /Invalid history list parameters/);

  // Fails when offline or stale
  f.setOnline(false);
  await assert.rejects(f.session.historyList(), /Fresh/);
});

test('historyCreate requires owner history-write and enforces title boundaries', async () => {
  const f = fixture();
  await f.pair();

  // Successful creation with generated ID
  const res1 = await f.session.historyCreate('A clean title');
  assert.equal(res1.history_api_version, '1');
  assert(THREAD_ID.test(res1.thread_id));

  // Successful creation with explicit ID
  const explicitId = 'c' + '3'.repeat(32);
  const res2 = await f.session.historyCreate('Explicit ID title', explicitId);
  assert.equal(res2.thread_id, explicitId);

  // Validation failures: empty title, control chars, too long, wrong ID format
  await assert.rejects(f.session.historyCreate('   '), /Invalid thread title/);
  await assert.rejects(f.session.historyCreate('Title with \x00 control'), /Invalid thread title/);
  await assert.rejects(f.session.historyCreate('A'.repeat(201)), /Invalid thread title/);
  await assert.rejects(f.session.historyCreate('Title', 'bad_id'), /Invalid thread title/);

  // Viewer role cannot create
  const fViewer = fixture({pairing: {role: 'viewer', scopes: ['read', 'revoke-self', 'history-read']}});
  await fViewer.pair();
  await assert.rejects(fViewer.session.historyCreate('Viewer title'), /Fresh owner history-write/);
});

test('historyRead requires history-read and validates bounds', async () => {
  const f = fixture();
  await f.pair();

  const res = await f.session.historyRead(threadId, 0, 50);
  assert.equal(res.history_api_version, '1');
  assert.equal(res.events.length, 1);
  assert.equal(res.events[0].value.text, 'Hello authenticated world.');

  // Bounds validation
  await assert.rejects(f.session.historyRead('bad_id'), /Invalid history read parameters/);
  await assert.rejects(f.session.historyRead(threadId, -1), /Invalid history read parameters/);
  await assert.rejects(f.session.historyRead(threadId, 0, 0), /Invalid history read parameters/);
  await assert.rejects(f.session.historyRead(threadId, 0, 101), /Invalid history read parameters/);
});

test('historyMessage requires owner history-write and enforces 8 KiB bound and control-char checks', async () => {
  const f = fixture();
  await f.pair();

  // Successful message append
  const res = await f.session.historyMessage(threadId, 'Human message text', 0);
  assert.equal(res.thread_id, threadId);
  assert(MESSAGE_ID.test(res.message_id));
  assert.equal(res.sequence, 1);

  // Bounds and UTF-8 size validation
  await assert.rejects(f.session.historyMessage(threadId, '   ', 0), /Invalid message parameters/);
  await assert.rejects(f.session.historyMessage(threadId, 'Valid text', -1), /Invalid message parameters/);
  await assert.rejects(f.session.historyMessage('bad_thread', 'Valid text', 0), /Invalid message parameters/);
  await assert.rejects(f.session.historyMessage(threadId, 'Text with \x00 null', 0), /Message text exceeds/);
  await assert.rejects(f.session.historyMessage(threadId, 'x'.repeat(8193), 0), /Message text exceeds/);

  // Viewer role cannot post message
  const fViewer = fixture({pairing: {role: 'viewer', scopes: ['read', 'revoke-self', 'history-read']}});
  await fViewer.pair();
  await assert.rejects(fViewer.session.historyMessage(threadId, 'Viewer text', 0), /Fresh owner history-write/);
});

test('historyDelete requires owner history-delete and validates thread ID', async () => {
  const f = fixture();
  await f.pair();

  const res = await f.session.historyDelete(threadId);
  assert.equal(res.thread_id, threadId);
  assert.equal(res.deleted, true);
  assert.equal(res.secure_erasure, false);

  await assert.rejects(f.session.historyDelete('bad_id'), /Invalid thread identifier/);

  // Viewer cannot delete
  const fViewer = fixture({pairing: {role: 'viewer', scopes: ['read', 'revoke-self', 'history-read']}});
  await fViewer.pair();
  await assert.rejects(fViewer.session.historyDelete(threadId), /Fresh owner history-delete/);
});

test('uncertain failure retains operation and prevents silent retry', async () => {
  const f = fixture();
  await f.pair();
  assert(f.session.can('history-write'));

  // Trigger failure after pairing is active
  f.options.failAfterChallenge = true;

  // Operation fails after challenge / possible commit
  await assert.rejects(
    f.session.historyMessage(threadId, 'Message that might have committed', 0, messageId),
    /synthetic timeout/
  );
  assert(!f.session.fresh());
  assert.match(f.session.error, /no automatic retry/);
});
