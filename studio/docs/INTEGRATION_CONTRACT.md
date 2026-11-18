# Shared companion UI → existing authenticated kernel

## Two hosts, deliberately not one privileged preview proxy

| Host/mode | Actual functionality | Authority boundary |
|---|---|---|
| `studio/src/studio.py serve` | Fixed light HTML, public status, optional fixed source download, pure companion/social planners | Stateless development preview, no `/api/v1` proxy, private CLI store, secret, executor or publisher route |
| Owner-approved HTTPS gateway, exact `/control/` | Same generated light HTML + API v1 / wire client 0.2.0 adapter | Explicit one-use host-console pairing, server-derived scopes, memory-only P-256 request proofs, separate exact approval and execution |
| Bundled native/offline/file preview | Same interface; local human briefs, requests and exact CSV calculation | No server identity, pairing, execution or account connection; missing planning validation remains unavailable |

`studio/web/gateway-session.js` is the implemented adapter, not a second engine.
`studio/scripts/build-web.py` writes byte-identical Studio/gateway/iOS payloads.
Windows and Android builds embed the actual gateway HTML; package checks compare
its exact bytes. Gateway configuration must pin the newly reviewed client hash.
Never replace a running profile's pin or disable checks just to accept changed UI.

## Implemented exact wire contract

- Identity: API `1`, client `0.2.0`, TLS required, fixed-owned-fixture mode and explicit
  non-production status. Envelope server identity/version/source must match.
- Pairing: one-use 43-character code from the trusted console; proof of a generated
  P-256 key. Private key is **non-exportable, renderer-memory only**, not hardware
  storage. The public key is exportable for pairing. Nothing is saved in browser storage.
- Server, not selected companion: actor/venture/role/grants/scopes/budget/catalog are
  derived by the existing trusted server. No UI-supplied actor, role, arbitrary tool,
  customer program, provider, shell, foreign destination or venture is accepted.
- Requests: exact allowlisted relative method/path/body SHA-256, one-use server
  challenge and signature. No cookie credential, redirect-following or automatic
  mutation retry. Challenge message/ID/expiry and late-response epoch are checked.
- Freshness: monotonic ≤15-second read-back and server session-expiry bound. No write
  authority while busy, offline, stale, backgrounded or after invalidation. Reads
  are serialized with mutations; a successful write still requires new read-back.
- Pair cancellation before dispatch sends no pairing request. A cancelled/lost
  response after dispatch is not proof that the server did nothing. Inspect/revoke
  from the trusted console as appropriate; never blindly repeat the effect.

| User action | Route | Separate requirement |
|---|---|---|
| Refresh | Signed `GET /api/v1/snapshot` | Scoped read; displays tasks/audit/canonical exact book, not imported finance data |
| Propose | Signed `POST /api/v1/tasks` | First-party rights/method confirmation, exact fixed sample and local-review destination; not approval |
| Review | Signed task `/approve` | Fresh server-owner scope, current exact digest and distinct owner console reauthentication bound to device/task/digest |
| Execute | Signed task `/execute` | Queued current exact digest and **separate user confirmation**; kernel rechecks effect boundary |
| Stop | Signed task `/cancel` | Scoped explicit request; not a remote-kill, settlement or stopped-provider-cost claim |
| Artifact | Signed task `/artifact` | Scoped read; actual returned content is canonical-hash checked in the client as well as server attestation |
| Revoke | Signed `/session/revoke` or trusted console | Acknowledged self-revocation forgets local key; local forget alone is not server revocation |

Only `invoice-good-v1`, `invoice-discount-defect-v1`, `invoice-docs-defect-v1` are
accepted. Maximum provider exposure is USD 0.00. The source's namespace-owned QA
executes on the selected Linux fixture host, **not on the phone/Windows client**.
Completion/receipt/hash is not qualified human usefulness acceptance or permission
to deliver externally. Imported CSV totals are not the canonical ledger or spend authority.

## Browser behavior/data boundaries

Local chats are human briefs plus deterministic intake, never invented model calls.
Optional v2 persistence holds only non-secret briefs/custom/routine requests. No
financial CSV, codes, device key or authoritative server receipt is persisted.
Legacy v1 browser data is left untouched. Restored blueprints are unvalidated.

The UI handles proposal/approval/execute/read-back separately. A proposal whose
reply is lost remains uncertain and requires explicit inspection before any new
proposal. A later read or native resume never automatically replays a mutation.
Code fields clear on close/pause. Text is escaped; delayed file/planner results
cannot silently overwrite edits. Native capability hints affect UI affordances
only, not server role, authentication, scopes or request allowlists.

The preview's pure JSON routes remain bounded (64 KiB HTTP), exact-field/integer
canonical planners. They reject duplicate keys, cross-origin planning requests,
ambiguous bodies, arbitrary file paths and execution/publishing writes. Their hash
and browser acknowledgement are integrity/local review, **not authenticated approval**.
Private CLI stores remain explicit local operations and are never read by HTTP.

## Observed proof and its limits

- 26 gateway protocol unit tests use **real WebCrypto with fake transport**. They
  cover exact challenge binding, scope/expiry, no implicit retry, artifact hash,
  late/cancelled pair/read/write and no persisted keys. They are not TLS proof.
- 44 actual shared-renderer HTTPS checks per Chromium and Linux WebKit use NEW
  disposable fixture profiles and the real kernel. Three fixed QA artifacts are
  read back, with invalid reauth, proof replay/forgery/path move, viewer/cross-venture,
  offline/pause/resume, explicit cancel, revocation and response loss **after a real
  server proposal**. Test-only instrumentation is not shipped in the UI.
- Each fixture separately checks real CA trust/default refusal/wrong hostname/
  cleartext refusal and stops its HTTPS listener. Chromium permits just the fixture
  SPKI and has `ignoreHTTPSErrors=false`. WebKit's localhost test explicitly uses
  `ignoreHTTPSErrors=true`; that is application behavior proof, **not TLS/OS trust**.
  Native code never overrides certificate errors.
- 35 local UI + 21 finance checks per browser, 78 opaque offline-viewer checks, 48
  Studio Python and the configured 1251-pass/173-PG-skip kernel profile are separate,
  overlapping evidence sets. They are not a completion percentage or independent review.

Read top-level `VERIFICATION.md` for exact receipts and retained initial failures.
The initial missing pinned tool correctly failed closed; installing a compatible
binary name or weakening the check is not an acceptable repair.

## What is still missing

This closes the **bounded local R03 wiring increment**, not R03 or the product in
full. Owner staging TLS/deployment/identity, generalized companion/provider streaming,
real capped providers, real per-bot VM/IDE lifecycle, official social OAuth/actions,
customer data/workloads, production operations and multi-tenant use are not implemented
or accepted by this adapter. No real account or external provider collaborated here.

Existing `work/` authority/catalog/approval/work/isolation/operations code is preserved.
Independent hostile-host/provider review, native devices/Mac/signing, witnessed
operations/privacy, protected independent evaluation, the real pilot and human
release remain the gates in `PUBLIC_RELEASE_ROADMAP.md` and `ANTIGRAVITY_NEXT.md`.
