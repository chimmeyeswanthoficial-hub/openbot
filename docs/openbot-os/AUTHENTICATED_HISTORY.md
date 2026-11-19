# Authenticated history — first real gateway integration

Parent: `cf2acb10530ab3c33c567bb9831c5d6dbe515349` (the standalone journal foundation).
This successor connects that journal to the **existing signed-device gateway**.
It is an actual storage/authentication implementation, not a mock history engine.
It remains **off by default**, is not connected to Studio chat, and runs no agent,
provider, tool, computer, IDE, official social API or customer workload.

## What changed

`work/services/gateway/src/conversation_api.py` implements strict bounded human
history operations. `control_api.py` authorizes them through existing P-256 proofs,
single-use path/method/body-bound nonces, TLS/host/origin checks and rate limits.
Trusted server sessions, not request JSON or browser companion labels, select the
venture and principal. No new unauthenticated server or HTTP provisioning route.
The old legacy Sentinel demo-console token mode is **not** this authentication path.

A trusted host must explicitly initialize a **dedicated private file-backed SQLite
journal** using `ConversationJournal`, then supply `ConversationAPI(journal)` to
`ControlBridge(..., history=...)`. `None` is the default. Runtime HTTP performs no
DDL, migration, setup/grant issuance, file creation or automatic pairing. The host
owns connection lifecycle (`check_same_thread=False` when used by worker threads),
private directories/ACLs, backups, encryption and physical-capacity monitoring.
Nothing in this change modifies an owner runtime or silently enables this API.

The currently supported history authentication/storage profile is **SQLite only**.
A PostgreSQL WorkStore explicitly refuses this history extension with 503. Existing
non-history PostgreSQL routes are not intentionally changed. PG history needs its
own locking, migration and actual test profile, not a copied SQLite pass.

## Additive wire contract

Existing API v1/client 0.2.0 remains; these new capabilities require explicit new
grants. Old generic `read`/`propose` grants do **not** acquire history rights.
Capabilities: `history-read`, `history-write`, `history-delete`. Only a trusted host
can grant them; viewers may receive read, never write/delete. Writes also require
an authenticated human-owner session. Default grants remain unchanged.

All history routes are **POST**, including reads, because the existing gateway
forbids query strings and signs the exact body. Pagination cursors must be bound to
the proof, not put in unsigned query parameters. Every request uses a new nonce.

`c…` is `c` + 32 lowercase hexadecimal characters; `m…` is `m` + 32 lowercase hex.
Choose fresh random IDs, not titles/names or sequential customer identifiers.

| Path under `/api/v1/conversations` | Exact JSON | Required capability |
|---|---|---|
| `/create` | `{"thread_id":"c…","title":"…"}` | `history-write` + human owner |
| `/list` | `{"after":"","limit":50}`; later `after` is a thread ID | `history-read` |
| `/c…/read` | `{"after":0,"limit":50}`; later `after` is last committed sequence | `history-read` |
| `/c…/messages` | `{"message_id":"m…","text":"…","expected_sequence":0}` | `history-write` + human owner |
| `/c…/delete` | `{}` | `history-delete` + human owner |

No extra actor/venture/tenant/principal/role/event/tool/approval fields are accepted.
Known credential-like patterns in titles/text are refused without echo; that is
**not comprehensive DLP**, secret classification or safe HTML rendering. Text is
plain data and must never be interpreted as trusted markup, code or permission.

Bodies remain capped at **16 KiB** by the gateway; human text at **8 KiB UTF-8**;
titles at 200 characters/800 bytes. The journal's bounded rows/payload bytes,
logical quotas, ordered compare-and-swap and integrity checks remain in force.
Read pages contain at most 100 events/128 KiB payload; an additional 192 KiB
history-result serialization bound protects envelope overhead. These logical
limits do not bound total physical SQLite/WAL/audit/backup storage.

Duplicate JSON keys, NaN/Infinity, excessive parser nesting and invalid encoding
are refused. Strict JSON parsing also applies to pairing/challenge/legacy POST
bodies. No TLS/origin/client-hash/pairing/CSP guard was weakened.

## Identity, revocation, audit and uncertain completion

The journal scope uses the authenticated actor and a hash of **gateway identity +
venture**. An owner role is not permission to read another actor's private chat.
A second device explicitly paired as the same actor can read that actor's history;
a different actor, venture or gateway identity cannot. This is the existing local
host-issued session model, **not a general organization/multi-tenant auth product**.

History admission reads current device scopes and checks role/actor/venture against
the current underlying session after request proof validation. Lock order is:

`devices transaction → work/session transaction → dedicated journal transaction`.

In the tested SQLite profile, protocol-respecting device/session revocation is
serialized with the history operation. A revoke already completed before admission
is denied; an already-admitted operation can commit before revoke returns. This does
not retract bytes already sent or protect against a hostile host/DB administrator.
Arbitrary direct SQL/alternate store protocols are outside that guarantee.

A content-free **attempt audit is committed before history access/mutation**. A
separate completion marker is written afterward. Audits contain operation/actor/
venture/attempt identity, never conversation title/text/event contents. No history
DELETE can erase immutable work/audit tables. Access metadata is still personal
information; the real deployment must define its privacy/retention policy.

This is not a distributed transaction across three DBs. If history commits but
completion audit/response fails, the durable attempt remains and the API fails
closed. Reconcile using the stable thread/message ID and a **new signed nonce**;
identical create/message retries return the committed result without a duplicate.
Changed-content/sequence retries conflict. Never infer "nothing happened" from a
503/lost connection or blindly retry an external effect. No external effect exists
in this feature.

## AG-UI: exact code/contract reuse, not an inflated engine claim

Server-generated human history is stored as a namespaced **AG-UI CUSTOM event**:

```json
{"type":"CUSTOM","name":"openbot.user_message.v1","value":{"thread_id":"c…","message_id":"m…","role":"user","author":"human:…","text":"…","source":"authenticated_human_input"}}
```

The exact MIT schema at AG-UI commit
`3416b86da4b3288e87f827c7f2759a7fa18b5231`, `spec/1.0/schema.json`, is now actually
retained at `work/third_party/ag-ui-contract/`, with original license and immutable
provenance. The raw Git-blob identity was checked against the pinned contents API.
Tests validate emitted CUSTOM envelopes and negative cases against that real schema,
with no remote schema resolution. No hand-written lookalike is relabeled upstream.

This is **schema reuse and a custom-event boundary**, not a full AG-UI lifecycle,
SSE transport, CopilotKit AgentRunner or provider integration. CUSTOM semantics are
application-owned. Do not put it on a live stream until the chosen compatible
runtime/version and run/message/tool/cancel/resume contracts are tested. Existing
fixture SSE is not silently upgraded or relabeled AG-UI 1.0.

## Deletion and privacy limits

Deletion is scoped logical history deletion with foreign-key cascade. It is not
secure erase, backup purge, immutable-audit deletion or provider-record deletion.
Idempotency applies within an existing thread lifecycle. **Do not reuse deleted
thread IDs**; retained tombstones/old-cursor semantics need a reviewed schema/migration
before a stronger no-resurrection contract can be promised. No HTTP file import,
attachments, assistant/system events or arbitrary client tool payloads are accepted.

## Measured tests and known exclusions

The new test module has **58 passing cases** after correcting two test-harness
assumptions: restart must not recreate a trusted setup authority without DDL, and
a write-capable TLS fixture must explicitly request owner role (viewer is default).
The permissions/production code were not weakened to make these tests green.
A first lint command also used the wrong cwd; preserved logs distinguish that from
an application failure.

Coverage: real file-backed SQLite, real P-256 proofs; scopes/roles/actor/venture/
gateway denial; duplicate/non-JSON input and byte bounds; retry/conflict/pagination;
concurrent signed devices; actual DB-trigger rollback; pre-effect audit failure;
commit-before-notification uncertainty; device/session revoke races; all three
stores reopened without DDL; logical delete preserving audit. One bounded real
TLS-socket case uses normal certificate verification and proves an untrusted CA
fails. Other HTTP cases use ASGI TestClient, **not OS/native TLS trust acceptance**.

Optional test dependencies are hash-locked in `work/requirements.agui-test.lock.txt`,
used alongside the existing handoff/control locks in an excluded disposable cache.
No SDK/runtime service or system package is installed by product startup.

No production DB migration, PG history, live model, Studio history UI, agent execution,
real tenant/user, device acceptance, hostile-host audit or genuine pilot ran.
See `evidence/openbot-os-history/VERIFICATION.md` for the final exact source/test
packet. Real-world rollout remains blocked on the explicit external gates.
