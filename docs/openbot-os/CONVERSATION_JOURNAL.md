# Application-owned conversation journal — implemented component contract

**Successor integration note:** the storage component remains inert, but an optional
signed-device HTTP adapter now exists. See [AUTHENTICATED_HISTORY.md](AUTHENTICATED_HISTORY.md)
for its exact human-history contract, real tests and limits. No live chat, Studio
history UI, complete AG-UI runner or provider is implied.

Source: `work/services/sentinel/conversation_journal.py`.
Tests: `work/services/sentinel/tests/test_conversation_journal.py`.
License: first-party MIT. Runtime dependencies: Python standard library/SQLite.
**Status: tested inert storage library with a successor opt-in signed-device HTTP
adapter. No live AG-UI, Studio conversation UI, providers or production data.**

## Why it exists

The existing `work_store.py` persists task/work execution events. This component
stores a different resource: a person's ordered conversation history, independent
of a particular task runner or licensed platform. It deliberately does not migrate
that older store or duplicate its approval, audit, budget and execution authority.

CopilotKit's MIT TypeScript runtime already supports local runners and an OSS
SQLite-runner package exists at the reviewed pin. Before integration, compare its
contract with ours. Reuse the SDK runner where it fits; do not maintain redundant
agent-execution machinery just to claim independence. This journal is not an
AG-UI AgentRunner drop-in and does not replace Intelligence's entire product.

## Trust and authorization

A dedicated `sqlite3.Connection` must use `isolation_level=None`. The caller owns
its lifecycle, directory, private permissions/Windows ACLs, timeout, encryption,
backup and retention. Do not give the database connection/file to an agent.
Initialization is explicit on an empty dedicated database; existing unrelated,
incomplete or unknown-version schemas are refused, never silently migrated.

`Scope(tenant, principal)` is a typed **query scope**, not an authentication token.
Trusted server middleware must derive both fields from an already authenticated,
authorized identity. A request-body `user_id`, bot claim, UI selection or supplied
Scope is not evidence of permission. Sharing and org membership are not implemented.
Scope tests establish SQL-predicate separation only, not hostile-host isolation or
end-to-end multi-tenant acceptance.

## API

```python
import sqlite3
from conversation_journal import ConversationJournal, Scope

# Example is disposable memory only. For durability, the operator explicitly
# opens a private dedicated file with appropriate ACLs and tested backup policy.
connection = sqlite3.connect(':memory:', isolation_level=None)
journal = ConversationJournal(connection, initialize=True)
owner = Scope('example-org', 'authenticated-human')
journal.create_thread(owner, 'thread-1', title='Example')
seq = journal.append(
    owner, 'thread-1', event_id='event-1', expected_sequence=0,
    event={'type': 'TEXT_MESSAGE_CONTENT', 'delta': 'A stored example'},
)
page = journal.read_events(owner, 'thread-1', after=0, limit=50)
connection.close()
```

- `create_thread`: same scope/id/title is an idempotent retry; changed title with
  that identity is a conflict. No hidden rename or creation on a read/append.
- `list_threads`: owner-scoped keyset pagination by thread ID, at most 100 rows.
- `append`: one `BEGIN IMMEDIATE` transaction checks current sequence, event ID,
  canonical payload and quotas, then writes the event and counters together.
  Exactly the same event ID/payload/prior sequence returns its original sequence,
  even after later events. Changed content/precondition or a stale new append fails.
- `read_events`: ordered events after a committed sequence, with a payload-byte
  limit as well as a row limit. The digest detects accidental payload changes; it
  is **not** a signature/MAC or protection from a malicious database owner.
- `delete_thread`: exact owner scope and foreign-key cascade, logical deletion
  only. It does not erase filesystem free pages, WAL/journal data, backups or audit.

## Enforced resource/data limits

| Limit | Value |
|---|---:|
| Event JSON UTF-8 bytes | 32,768 |
| JSON depth / visited values | 12 / 2,048 |
| Entries per JSON array/object | 256 |
| IDs | 1–128 restricted ASCII characters |
| Replay page | ≤100 events and ≤131,072 **payload** bytes |
| Events / logical payload per thread | 4,096 / 4 MiB |
| Threads per scope / per database | 1,000 / 10,000 |
| Database logical event payload | 64 MiB |

Envelope/JSON escaping overhead is not included in `payload_bytes`; it is not an
HTTP response-size bound. SQLite files/journals/backups, titles, indexes and churn
are outside the logical payload quota: monitor actual disk and configure retention.
Identifiers are bound SQL parameters, never paths. Non-finite/unsafe large numbers,
non-JSON types, duplicate/coerced numeric keys, invalid Unicode and conflicting
payload `threadId` are refused. Caller Python dictionaries cannot represent duplicate
JSON keys; raw-JSON HTTP adapters must reject duplicates **before** this API
(the successor signed-device adapter now does so).

An uppercase `type` and optional thread correlation are checked, but AG-UI event
schemas, run/message/tool lifecycle and resume semantics are **not** validated.
The existing narrow SSE profile is also not the full AG-UI protocol. A future
adapter needs protocol fixtures and correlation checks before committing events.
A stored `TOOL_CALL_START` is inert JSON and never calls a tool.

## Tests actually exercised

31 tests use real disposable SQLite files/connections, not a mocked database:
initialization/schema refusal, scope-predicate separation, stable ID retries,
conflicts, JSON/bounds, keyset and byte-bounded replay, quotas, forced transaction
rollback, foreign-transaction preservation, competing writers with one sequence
winner, reopen, abrupt child-process exit **after commit**, owned cascade deletion
and accidental payload corruption. Abrupt post-commit exit is not every possible
power-loss/fsync/OS/storage failure. No hardware-durability or performance benchmark
claim, production migration, PostgreSQL backend, auth/HTTP integration or provider
run follows from these tests.
