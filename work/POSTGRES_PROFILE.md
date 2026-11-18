# Disposable PostgreSQL profile — S01 local engineering checkpoint

This is a bounded successor to the completed AG4 source, not a production migration or activation. It adds an explicit **non-migrating connection mode** and actual local PostgreSQL evidence. The previous six PG skips remain truthful historical results; they are not edited into previous passes.

## Runtime/setup separation

```python
# On a newly created, deliberately disposable fixture, under a schema owner:
setup = Store(disposable_owner_dsn)
EconomicBook(setup, experimental=True)
setup._conn.close()

# After a separate trusted operator provisions the schema and least privileges:
store = Store(disposable_app_dsn, initialize=False)
book = EconomicBook(store, experimental=True, initialize=False)
```

`initialize=False` means **no schema DDL**, not read-only access, API authentication or permission to access a real database. Defaults remain backward-compatible for existing local/demo callers; neither constructor silently falls back if the default schema-initialization path lacks privilege. Both flags reject non-boolean values. A failed Store construction closes its new connection. SQLite's existing-only mode uses `mode=rw`, refuses memory/file-URI ambiguity and does not create a missing file.

Store validates the required existing legacy columns. The canonical book checks the existing version marker and connection-level SQLite foreign-key protections, never repairing an absent/wrong version or committing/rolling back a caller-owned transaction. Schema installation still requires a separately controlled migration identity. No production grant installer or schema rollout is supplied or run by this checkpoint.

## The test profile

A new PostgreSQL 17 cluster is initialized in excluded cache and listens on a **0700 private Unix socket only**, with TCP listening disabled. `fsync`, `synchronous_commit` and `full_page_writes` are on. Local trust authentication is strictly a disposable same-user test convenience, **not deployment guidance**. No production DSN, real data, password, provider or public service is used.

The dedicated test database is named `openbot_fixture*`. A setup identity creates unique synthetic schemas and a separate app role for each case. App roles have LOGIN but are non-owner, NOSUPERUSER, NOCREATEDB, NOCREATEROLE, NOREPLICATION, NOINHERIT, and no schema CREATE or database CREATE/TEMPORARY privilege.

The explicit grants tested in `test_pg_profile.py` are:

- Schema USAGE only; no public schema write inheritance.
- SELECT/INSERT for legacy audit/ledger and canonical postings/links/events; **no UPDATE/DELETE/TRUNCATE** on those evidence tables.
- SELECT/INSERT/UPDATE on approvals/runs/messages for their controlled state transitions. The existing canonical message trigger prevents identity/evidence edits despite status-update privilege.
- SELECT only on canonical schema version; sequence USAGE/SELECT, not sequence UPDATE/reset.
- No PUBLIC execute grants on schema functions. Roles cannot disable triggers or alter/drop/create permanent or temporary tables/functions.

These are fixture grants, not row-level tenant isolation. A trusted DB owner/superuser can alter its database; this is not protection against that administrator, an app-role compromise, SQL injection, local host compromise or hostile cross-tenant access. Agents must never receive these credentials. The independent kernel/authority and later isolation gates still apply.

## Checks and real-world limits

The suite exercises existing-only opening, effective non-superuser role, denied evidence/DDL mutation, trigger-protected message identity, 12 independent approval-resolution processes, 4 independent canonical-ingest processes, missing audit INSERT permission with atomic rollback, actual server-side connection termination before/after commit, five abrupt client exits (79), version mismatch, atomic failed migration, and an actual pg_dump → fresh database pg_restore → row/constraint/grant read-back.

A separate same-host PostgreSQL immediate-stop/restart probe verifies committed synthetic rows and permissions after WAL recovery, and retries a known message without a second economic posting. The download's source/evidence report identifies which commands actually ran and their completed outcomes; this design text alone is not that proof.

Remaining limits:

- PostgreSQL 17 / same-host Unix-socket profile only; no HA, replica/failover, network/TLS, connection pool, managed service, load/performance or cross-machine certification.
- Legacy PG read methods retain their previous transaction semantics. Do not silently rollback a caller's read transaction merely to use the canonical book; use separate owned connections or explicitly end your own transaction. Existing-only construction itself returns its new connection idle.
- Canonical read methods currently acquire a messages-table serialization lock; this is not a certified high-throughput or true SQL read-only-role API. Read-only client pairing needs a separately reviewed read contract.
- Atomic rollback and a conservative `EconomicUnavailable(uncertain=True)` around lost commit acknowledgement are not proof of remote-provider exactly-once or stop. Callers reopen explicitly and retry the **same** message identity; no automatic new-ID retry.
- `Store` initialization defaults are unchanged for compatibility. The deployed app is not reconfigured to this profile; credentials, rollout/migrations and production least privilege need a separate owner-reviewed stage.
- Whole-liability reservation, repeated-routine accounting, durable occurrence scheduling, mandatory remote execution authentication, live provider/cost/stop, encrypted backups, public deployment and the private pilot remain unfinished.

## Reproduce only on a new fixture

Use the hash-locked Python 3.13/Linux profile plus the separately pinned psycopg2 test wheel recorded in the evidence packet. Provision a fresh PostgreSQL instance; never point these mutating/admin tests at a real project database.

Set **both** `OPENBOT_TEST_POSTGRES_DSN` (an explicit `postgresql://` URL) and `OPENBOT_TEST_POSTGRES_ALLOW_WRITES=1`. The added profile cases additionally require an absolute Unix-socket host and an `openbot_fixture*` database. `OPENBOT_PG_TEST_BIN` identifies `pg_dump`/`pg_restore`; optional `OPENBOT_PG_TEST_EVIDENCE` names a new disposable evidence folder. No fallback to `DATABASE_URL`/`SENTINEL_DB` exists.

```sh
python -m pytest services/sentinel/tests/test_repository_pg.py \
  services/sentinel/tests/test_economic_book_pg.py \
  services/sentinel/tests/test_pg_profile.py \
  services/sentinel/tests/test_store_existing.py --junitxml=NEW_PROFILE_XML
```

`NEW_PROFILE_XML` is an operator-chosen new evidence path. The local recovery probe's prepare/verify phases require a successful synthetic restore receipt and the same explicit fixture opt-ins; it does not start a server or invoke a provider. Stop/remove only the disposable cluster after its evidence is retained. Do not delete/reset any existing business state, audit history or old evidence.
