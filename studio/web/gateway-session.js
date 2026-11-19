/* OpenBot first-party adapter to API v1 / wire client v0.2.0.
 * Fixed-owned QA only. No provider keys, persistent device key or proxy authority.
 * A displayed companion NEVER selects a server actor, venture, role or budget.
 */
(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else Object.defineProperty(root, 'OpenBotGateway', {value: api, writable: false});
})(typeof globalThis === 'object' ? globalThis : this, function () {
  'use strict';
  const HEX = /^[a-f0-9]{64}$/, DEVICE = /^[A-Za-z0-9_-]{32}$/, TASK = /^w[a-f0-9]{32}$/;
  const UUID = /^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/;
  const THREAD_ID = /^c[a-f0-9]{32}$/, MESSAGE_ID = /^m[a-f0-9]{32}$/;
  const historyScopes = Object.freeze(new Set(['history-read', 'history-write', 'history-delete']));
  const scopes = new Set(['read', 'propose', 'approve', 'execute', 'cancel', 'revoke-self', ...historyScopes]);
  const fixtures = Object.freeze(['invoice-good-v1', 'invoice-discount-defect-v1', 'invoice-docs-defect-v1']);
  const empty = () => ({status: {}, tasks: [], audit: [], exact_book: {summary: {}, postings: []}});
  const bytes = text => new TextEncoder().encode(text);
  const b64 = value => btoa(String.fromCharCode(...new Uint8Array(value)))
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  const canonical = value => value === null || typeof value !== 'object' ? JSON.stringify(value)
    : Array.isArray(value) ? '[' + value.map(canonical).join(',') + ']'
    : '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + canonical(value[k])).join(',') + '}';
  async function digest(text, crypto) {
    return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', bytes(text))), v => v.toString(16).padStart(2, '0')).join('');
  }
  function liveLocation(location) {
    return location?.protocol === 'https:' && location.pathname === '/control/' && !location.search
      && typeof location.origin === 'string' && location.origin.startsWith('https://');
  }
  function allowed(method, path) {
    return method === 'GET' && /^\/api\/v1\/(snapshot|status|tasks|audit|exact-book|session|tasks\/w[a-f0-9]{32}(?:\/artifact)?)$/.test(path)
      || method === 'POST' && /^\/api\/v1\/(tasks|session\/revoke|tasks\/w[a-f0-9]{32}\/(?:approve|execute|cancel)|conversations\/(?:create|list|c[a-f0-9]{32}\/(?:read|messages|delete)))$/.test(path);
  }
  class Session {
    #keys = null; #transport; #crypto; #now; #online; #notify;
    #epoch = 0; #seen = null; #observed = 0;
    constructor({location = globalThis.location, transport = globalThis.fetch?.bind(globalThis),
      crypto = globalThis.crypto, now = () => performance.now(),
      online = () => globalThis.navigator?.onLine !== false, changed = () => {}} = {}) {
      this.enabled = liveLocation(location); this.origin = this.enabled ? location.origin : null;
      this.server = null; this.pairing = null; this.snapshot = empty();
      this.busy = false; this.error = ''; this.ttl = 15;
      this.#transport = transport; this.#crypto = crypto; this.#now = now;
      this.#online = online; this.#notify = changed;
    }
    fresh() {
      const age = this.#seen === null ? -1 : this.#now() - this.#seen;
      return Boolean(this.enabled && this.server && this.pairing && this.#keys && this.#online()
        && age >= 0 && age < this.ttl * 1000 && this.#observed + age / 1000 < this.pairing.expires);
    }
    can(scope) { return this.fresh() && !this.busy && this.pairing.scopes.includes(scope); }
    info() {
      return Object.freeze({enabled: this.enabled, origin: this.origin, server: this.server,
        pairing: this.pairing ? {...this.pairing, scopes: [...this.pairing.scopes]} : null,
        fresh: this.fresh(), busy: this.busy, error: this.error,
        key_storage: 'non-exportable private key in renderer memory only', production_connection: false});
    }
    invalidate(reason = 'Session read-back is stale.') {
      this.#epoch++; this.#seen = null; this.error = reason; this.#notify();
    }
    forget() {
      this.invalidate('Session forgotten locally. Revoke on the trusted server if needed.');
      this.pairing = null; this.#keys = null; this.snapshot = empty(); this.#notify();
    }
    #check(value) {
      if (!value || value.api_version !== '1' || !HEX.test(value.server_id)
        || this.server && value.server_id !== this.server || !Number.isInteger(value.observed_at)
        || value.fresh_for_seconds !== 15 || value.source !== 'local_authenticated_server')
        throw Error('Server identity or version mismatch; no authority assumed.');
      return value;
    }
    async #request(method, path, body, headers = {}, timeout = 15000) {
      if (!this.enabled) throw Error('Use the owner-approved HTTPS gateway /control/ page. This preview has no execution route.');
      const controller = new AbortController(), timer = setTimeout(() => controller.abort(), timeout);
      try {
        const response = await this.#transport(path, {method,
          headers: {Accept: 'application/json', ...(body !== undefined ? {'Content-Type': 'application/json'} : {}), ...headers},
          body, credentials: 'omit', cache: 'no-store', redirect: 'error', referrerPolicy: 'no-referrer', signal: controller.signal});
        let value;
        try { value = await response.json(); }
        catch (_) { throw Error('Versioned JSON response required. Outcome may need read-back.'); }
        if (!response.ok) throw Error(typeof value.detail === 'string' ? value.detail : 'Request refused; no automatic retry.');
        return this.#check(value);
      } finally { clearTimeout(timer); }
    }
    async identify() {
      if (!this.enabled || this.busy) return false;
      const epoch = this.#epoch;
      try {
        const r = await this.#request('GET', '/api/v1/identity');
        if (epoch !== this.#epoch) return false;
        if (r.data?.client_version !== '0.2.0' || r.data.tls_required !== true
          || r.data.public_or_production_release !== false || r.data.mode !== 'local_owned_fixture'
          || !HEX.test(r.data.client_sha256)) throw Error('Unsupported identity contract.');
        this.server = r.server_id; this.error = ''; this.#notify(); return true;
      } catch (error) { if (epoch === this.#epoch) this.invalidate(error.message); throw error; }
    }
    async pair(code, label) {
      if (!this.server || this.busy || typeof code !== 'string' || !/^[A-Za-z0-9_-]{43}$/.test(code)
        || typeof label !== 'string' || !label.trim() || label.length > 64 || /[\x00-\x1f\x7f]/.test(label))
        throw Error('A valid one-use host-console pairing code and device label are required.');
      if (!this.#crypto?.subtle) throw Error('Secure WebCrypto context required.');
      this.#epoch++; const epoch = this.#epoch;
      this.busy = true; this.#seen = null; this.pairing = null; this.#keys = null; this.#notify();
      try {
        const keys = await this.#crypto.subtle.generateKey({name: 'ECDSA', namedCurve: 'P-256'}, false, ['sign', 'verify']);
        const public_key = b64(await this.#crypto.subtle.exportKey('spki', keys.publicKey));
        const signature = b64(await this.#crypto.subtle.sign({name: 'ECDSA', hash: 'SHA-256'}, keys.privateKey,
          bytes('openbot.pair/1\n' + this.server + '\n' + code)));
        if (epoch !== this.#epoch) throw Error('Pairing cancelled before dispatch. No pairing request sent.');
        const r = await this.#request('POST', '/api/v1/pair', JSON.stringify({code, public_key, signature, label: label.trim(), client_version: '0.2.0'}));
        if (epoch !== this.#epoch) throw Error('Pairing response became stale; inspect/revoke the server session before retrying.');
        const p = r.data;
        if (!p || !DEVICE.test(p.device) || !['owner', 'viewer'].includes(p.role) || typeof p.venture !== 'string'
          || !p.venture || !Array.isArray(p.scopes) || !p.scopes.includes('read') || new Set(p.scopes).size !== p.scopes.length
          || p.scopes.some(s => !scopes.has(s)) || p.role === 'viewer' && p.scopes.some(s => !['read', 'revoke-self', 'history-read'].includes(s))
          || !Number.isInteger(p.expires) || p.expires <= r.observed_at) throw Error('Invalid server-derived device scope.');
        this.#keys = keys; this.pairing = {device: p.device, role: p.role, venture: p.venture, scopes: [...p.scopes], expires: p.expires};
        this.error = '';
      } catch (error) { this.pairing = null; this.#keys = null; this.error = error.message; throw error; }
      finally { this.busy = false; this.#notify(); }
      return this.refresh();
    }
    async #signed(method, path, body) {
      if (!allowed(method, path) || !this.pairing || !this.#keys) throw Error('Pair this device and use a fixed versioned route.');
      const epoch = this.#epoch, keys = this.#keys, device = this.pairing.device;
      const raw = body === undefined ? '' : JSON.stringify(body), bodyHash = await digest(raw, this.#crypto);
      if (epoch !== this.#epoch) throw Error('Session changed before challenge; request not sent.');
      const challenge = await this.#request('POST', '/api/v1/challenge', JSON.stringify({device, method, path, body_sha256: bodyHash, api_version: '1'}));
      const c = challenge.data, expected = ['openbot.control-request/1', this.server, device, c?.id, method, path, bodyHash, String(c?.expires)].join('\n');
      if (!c || !DEVICE.test(c.id) || c.message !== expected || !Number.isInteger(c.expires)
        || c.expires <= challenge.observed_at || c.expires > challenge.observed_at + 60) throw Error('Exact request/challenge binding refused.');
      if (epoch !== this.#epoch || this.pairing?.device !== device) throw Error('Session changed before signing; request not sent.');
      const signature = await this.#crypto.subtle.sign({name: 'ECDSA', hash: 'SHA-256'}, keys.privateKey, bytes(c.message));
      if (signature.byteLength !== 64) throw Error('This WebView lacks the required P-256 signature format.');
      if (epoch !== this.#epoch) throw Error('Session changed before dispatch; request not sent.');
      const reply = await this.#request(method, path, method === 'GET' ? undefined : raw,
        {'Content-Type': 'application/json', 'X-OpenBot-Device': device, 'X-OpenBot-Challenge': c.id, 'X-OpenBot-Signature': b64(signature)}, 30000);
      if (epoch !== this.#epoch || this.pairing?.device !== device)
        throw Error('Late response discarded. Read back the server outcome; never resend implicitly.');
      return reply;
    }
    async refresh() {
      if (!this.pairing || this.busy) return false;
      const epoch = this.#epoch; this.busy = true; this.#notify();
      try {
        const r = await this.#signed('GET', '/api/v1/snapshot'), s = r.data;
        if (epoch !== this.#epoch) return false;
        if (!s || s.status?.execution_mode !== 'fixed_owned_qa_only' || s.status.paid_provider_enabled !== false
          || s.status.customer_execution_enabled !== false || !Array.isArray(s.tasks) || s.tasks.length > 100
          || s.tasks.some(t => !TASK.test(t?.id)) || !Array.isArray(s.audit) || !s.exact_book)
          throw Error('Incomplete or unsupported authoritative snapshot.');
        this.snapshot = s; this.ttl = r.fresh_for_seconds; this.#observed = r.observed_at;
        this.#seen = this.#now(); this.error = ''; return true;
      } catch (error) { if (epoch === this.#epoch) { this.#seen = null; this.error = error.message; } return false; }
      finally { this.busy = false; this.#notify(); }
    }
    async #mutate(scope, path, body) {
      if (!this.can(scope)) throw Error('Fresh authenticated scope required. No action sent.');
      this.busy = true; this.#notify();
      try { const r = await this.#signed('POST', path, body); this.error = ''; return r.data; }
      catch (error) { this.error = 'Unknown/refused outcome; no automatic retry. ' + error.message; throw error; }
      finally { this.#seen = null; this.busy = false; this.#notify(); }
    }
    async propose(value) {
      const fields = ['acceptance', 'ai_use_approved', 'destination', 'fixture', 'goal', 'request_id', 'rights_ref'];
      if (!value || Object.keys(value).sort().join(',') !== fields.join(',') || !fixtures.includes(value.fixture)
        || value.destination !== 'local-review' || value.rights_ref !== 'owned:first-party-seed' || value.ai_use_approved !== true
        || !UUID.test(value.request_id) || [value.goal, value.acceptance].some(s => typeof s !== 'string' || !s.trim() || s.length > 512 || /[\x00-\x1f\x7f]/.test(s)))
        throw Error('Exact owned-sample intake and rights/method confirmation required. No actor, role, account or venture is accepted from the UI.');
      return this.#mutate('propose', '/api/v1/tasks', value);
    }
    async taskAction(action, id, expected, code) {
      if (!TASK.test(id) || !['approve', 'execute', 'cancel'].includes(action) || action !== 'cancel' && !HEX.test(expected))
        throw Error('Exact task/digest required.');
      const current = this.snapshot.tasks.find(t => t.id === id);
      if (!current || action !== 'cancel' && current.spec_digest !== expected
        || action === 'approve' && current.status !== 'review' || action === 'execute' && current.status !== 'queued'
        || action === 'cancel' && !['review', 'queued', 'running'].includes(current.status)) throw Error('Current exact server task required.');
      if (action === 'approve' && (this.pairing?.role !== 'owner' || typeof code !== 'string' || !/^[A-Za-z0-9_-]{43}$/.test(code)))
        throw Error('Separate owner host-console reauthentication required.');
      const body = action === 'cancel' ? {} : action === 'approve' ? {digest: expected, reauth_code: code} : {digest: expected};
      return this.#mutate(action, '/api/v1/tasks/' + id + '/' + action, body);
    }
    async artifact(id) {
      if (!this.can('read') || !TASK.test(id)) throw Error('Fresh scoped read required.');
      const epoch = this.#epoch; this.busy = true; this.#notify();
      try {
        const r = await this.#signed('GET', '/api/v1/tasks/' + id + '/artifact'), a = r.data;
        if (!a || !HEX.test(a.sha256) || a.external_delivery !== false || !a.content
          || await digest(canonical(a.content), this.#crypto) !== a.sha256) throw Error('Verified local artifact content required.');
        if (epoch !== this.#epoch) throw Error('Late artifact discarded.');
        return a;
      } catch (error) { this.#seen = null; this.error = error.message; throw error; }
      finally { this.busy = false; this.#notify(); }
    }
    #randomHex(n) {
      const arr = new Uint8Array(n);
      const c = (this.#crypto?.getRandomValues && this.#crypto)
        || (globalThis.crypto?.getRandomValues && globalThis.crypto)
        || (typeof require === 'function' ? require('node:crypto') : null);
      if (!c?.getRandomValues) throw Error('Cryptographic random generation unavailable.');
      c.getRandomValues(arr);
      return Array.from(arr, b => b.toString(16).padStart(2, '0')).join('');
    }
    #validateHistoryResponse(d) {
      if (!d || d.history_api_version !== '1' || d.history_only !== true
        || d.agent_executed !== false || d.source !== 'application_sqlite_journal')
        throw Error('Server history contract mismatch; no authority assumed.');
      return d;
    }
    async historyList(after = '', limit = 50) {
      if (!this.can('history-read')) throw Error('Fresh history-read scope required.');
      if (typeof after !== 'string' || (after !== '' && !THREAD_ID.test(after)) || !Number.isInteger(limit) || limit < 1 || limit > 100)
        throw Error('Invalid history list parameters.');
      const epoch = this.#epoch; this.busy = true; this.#notify();
      try {
        const r = await this.#signed('POST', '/api/v1/conversations/list', {after, limit});
        if (epoch !== this.#epoch) throw Error('Session changed during history read; response discarded.');
        const d = r.data;
        this.#validateHistoryResponse(d);
        if (!Array.isArray(d.threads)) throw Error('Invalid threads list in history response.');
        this.#seen = this.#now();
        return d;
      } catch (error) { this.#seen = null; this.error = error.message; throw error; }
      finally { this.busy = false; this.#notify(); }
    }
    async historyCreate(title, threadId = undefined) {
      if (!this.can('history-write') || this.pairing?.role !== 'owner')
        throw Error('Fresh owner history-write scope required.');
      const tid = threadId || ('c' + this.#randomHex(16));
      if (!THREAD_ID.test(tid) || typeof title !== 'string' || !title.trim() || title.length > 200 || /[\x00-\x1f\x7f]/.test(title))
        throw Error('Invalid thread title or identifier.');
      this.busy = true; this.#notify();
      try {
        const r = await this.#signed('POST', '/api/v1/conversations/create', {thread_id: tid, title: title.trim()});
        const d = r.data;
        this.#validateHistoryResponse(d);
        if (d.thread_id !== tid) throw Error('Thread identity mismatch in response.');
        this.#seen = this.#now();
        return d;
      } catch (error) {
        this.#seen = null;
        this.error = 'Unknown/refused outcome; no automatic retry. ' + error.message;
        throw error;
      } finally { this.busy = false; this.#notify(); }
    }
    async historyRead(threadId, after = 0, limit = 50) {
      if (!this.can('history-read')) throw Error('Fresh history-read scope required.');
      if (!THREAD_ID.test(threadId) || !Number.isInteger(after) || after < 0 || !Number.isInteger(limit) || limit < 1 || limit > 100)
        throw Error('Invalid history read parameters.');
      const epoch = this.#epoch; this.busy = true; this.#notify();
      try {
        const r = await this.#signed('POST', '/api/v1/conversations/' + threadId + '/read', {after, limit});
        if (epoch !== this.#epoch) throw Error('Session changed during history read; response discarded.');
        const d = r.data;
        this.#validateHistoryResponse(d);
        if (!Array.isArray(d.events)) throw Error('Invalid events in history response.');
        this.#seen = this.#now();
        return d;
      } catch (error) { this.#seen = null; this.error = error.message; throw error; }
      finally { this.busy = false; this.#notify(); }
    }
    async historyMessage(threadId, text, expectedSequence, messageId = undefined) {
      if (!this.can('history-write') || this.pairing?.role !== 'owner')
        throw Error('Fresh owner history-write scope required.');
      if (!THREAD_ID.test(threadId) || typeof text !== 'string' || !text.trim() || !Number.isInteger(expectedSequence) || expectedSequence < 0)
        throw Error('Invalid message parameters.');
      if (bytes(text).length > 8192 || /[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]/.test(text))
        throw Error('Message text exceeds 8192 UTF-8 bytes or contains control characters.');
      const mid = messageId || ('m' + this.#randomHex(16));
      if (!MESSAGE_ID.test(mid)) throw Error('Invalid message identifier.');
      this.busy = true; this.#notify();
      try {
        const r = await this.#signed('POST', '/api/v1/conversations/' + threadId + '/messages', {
          message_id: mid,
          text: text.trim(),
          expected_sequence: expectedSequence
        });
        const d = r.data;
        this.#validateHistoryResponse(d);
        if (d.thread_id !== threadId || d.message_id !== mid || !Number.isInteger(d.sequence))
          throw Error('Invalid message response structure.');
        this.#seen = this.#now();
        return d;
      } catch (error) {
        this.#seen = null;
        this.error = 'Unknown/refused outcome; no automatic retry. ' + error.message;
        throw error;
      } finally { this.busy = false; this.#notify(); }
    }
    async historyDelete(threadId) {
      if (!this.can('history-delete') || this.pairing?.role !== 'owner')
        throw Error('Fresh owner history-delete scope required.');
      if (!THREAD_ID.test(threadId)) throw Error('Invalid thread identifier.');
      this.busy = true; this.#notify();
      try {
        const r = await this.#signed('POST', '/api/v1/conversations/' + threadId + '/delete', {});
        const d = r.data;
        this.#validateHistoryResponse(d);
        if (d.thread_id !== threadId || d.deleted !== true || d.secure_erasure !== false)
          throw Error('Invalid deletion response contract.');
        this.#seen = this.#now();
        return d;
      } catch (error) {
        this.#seen = null;
        this.error = 'Unknown/refused outcome; no automatic retry. ' + error.message;
        throw error;
      } finally { this.busy = false; this.#notify(); }
    }
    async revoke() { const r = await this.#mutate('revoke-self', '/api/v1/session/revoke', {}); this.forget(); return r; }
  }
  return Object.freeze({Session, liveLocation, allowed, fixtures, historyScopes, THREAD_ID, MESSAGE_ID});
});
