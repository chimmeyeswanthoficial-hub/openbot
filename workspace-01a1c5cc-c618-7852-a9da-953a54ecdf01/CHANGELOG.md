# Changelog

The format is [Keep a Changelog](https://keepachangelog.com/) and this project adheres to
[Semantic Versioning](https://semver.org/). Every release note ends with the verify output that
signed it off (see `.claude/skills/project-owner/SKILL.md`).

## [0.2.3] — 2026-11-13

Deploy pipeline tests (T7 complete), suite hardening, and contract anti-rot update.

### Added
- **Deploy pipeline tests (`scripts/tests/test_deploy.py`, 5 tests).** T7 is now fully tested:
  `test_deploy_records_history_entry`, `test_deploy_updates_current_and_previous_sha`,
  `test_rollback_reverts_current_sha`, `test_rollback_fails_without_previous_sha`,
  `test_deploy_rollback_roundtrip_records_rollback_row`.
- `scripts/tests/` added to `pyproject.toml` testpaths and `test_contract.py` suite list so the
  anti-rot collector tracks deploy tests automatically.
- Suite expanded to 216 passed tests (214 passed, 2 skipped).

### Changed
- Contract `_collected()` now scans `scripts/tests` in addition to the six service suites.



Governance engine hardening, PostgreSQL persistence backend, Worker Sentinel wiring, and dead-man's switch.

### Fixed
- **`Worker.tick()` double-dispatch within the same clock minute.** Guarded by `_last_fired` minute key so two rapid ticks in the same minute cannot burn budget twice.
- **Lost-race approval resolution under concurrency.** Conditional UPDATE guarantees exactly one caller wins approval races under concurrent worker/operator requests.

### Added
- **`SentinelClient` HTTP fail-closed client (`services/worker/src/sentinel_client.py`).** Connects Worker to Sentinel `/v1/decide` with a 5s timeout and fail-closed security boundary.
- **Worker Daemon Entrypoint (`services/worker/src/main.py`).** Supports continuous 60s ticking, `--once` execution mode, and automated dead-man's switch pings.
- **PostgreSQL Persistence Backend (`services/sentinel/repository.py`).** Supports SQLite and PostgreSQL via `DATABASE_URL` / `SENTINEL_DB` with identical `Store` interface and `test_repository_pg.py`.
- **Dead-man's Switch Heartbeat (`services/worker/src/heartbeat.py`).** Heartbeat pings to `DEADMAN_PING_URL` monitor control-plane health.
- **Gate-Starvation Alarm & Approvals Digest (`services/worker/src/digest.py`).** Added `approvals_pending_max_age_hours` metric to `/v1/overview`, console amber warning banner on approvals older than 24h, and daily digest generator.
- **Stripe Payment Webhooks (`services/ledger/src/webhook.py` & `POST /webhooks/stripe`).** Verifies HMAC-SHA256 signatures, maps `invoice.paid` / `charge.refunded` to ledger rows, and guarantees idempotency on the event id.
- **OpenBot Gateway Adapter (`services/gateway/src/adapter.py` & `mapper.py`).** Intercepts substrate agent tool execution, maps tool calls to Sentinel canonical actions, and produces AG-UI interrupt cards on gate.
- **AG-UI Routine Dispatcher (`services/worker/src/dispatch_agui.py`).** Executes scheduled routines over AG-UI protocol to bot runtimes, enforcing hard runtime limits (`max_runtime_min`) and budget caps (`budget_usd`), delivering channel outputs.
- **Media API First Venture Service (`services/media-api/src/app.py`).** Pure streaming conversion, splitting, and compression without buffering to disk, governed by Sentinel policy and 500 MB upload cap.
- Suite expanded to 211 passed tests.

## [0.2.1] — 2026-11-10

A pass over the release itself: the things that were true on my machine were not yet true for a
stranger, and the console proved it.

### Fixed
- **The org chart could name a runtime that does not exist, on any machine without `repos/`.** The
  `agent_impl` check only ran when the substrate was on disk; absent it, an invented `agent-nope`
  loaded clean. Found by copying the repository without `repos/` and running the suite — the exact
  machine a stranger has. The validator now falls back to a committed `company/agent_impls.yaml`
  (generated from the pinned tree, and drift-checked against it when both are present) and **refuses
  to load a company it cannot verify** rather than skipping the check.
- **A failing audit store no longer lets a decision escape.** Every persistence call is now guarded:
  if the row cannot be written the caller gets `503` and the action is refused, instead of a `500`
  after the decision was made. `healthz` reports `store: ok|unavailable`. Found by deleting the
  SQLite file under a running server — exactly the kind of failure that only shows up in production.
- **The approval queue is signal again.** `read billing portal` — a routine *reading* invoices — was
  gated as `money.payment`. Rules now follow OpenBot's own convention: the action is its first verb,
  so reads (`read|get|list|view|search|check|draft|…`) are browsing, while `refund`, `charge`,
  `pay invoice` still stop. A read never skips credentials or deletes (`list api keys` still gates).
  The seeded demo went from 4 pending (2 of them noise) to 3 real decisions.
- Credential rules match plurals (`api keys`, `passwords`, `tokens`), which is how tool names are
  actually written.

### Added
- `test_public.py`: token-gated writes, reads stay open, ledger replay refused, store failure
  refuses everything.
- `scripts/sync-docs.sh` + a contract test that fails when `docs/` drifts from the root documents.
- `make release-check` (verify + test + smoke) and a console **token** button that stores the token
  in the tab only.
- A contract suite that fails when a capability bullet has no evidence tag, when the changelog
  version does not match `app.py`, or when the console calls an endpoint that does not exist.

### Security
- `SENTINEL_UI_TOKEN` gates approvals and ledger writes; the console prompts for it and keeps it in
  `sessionStorage`. Loopback stays open for `make demo`; a public address must not.
- The console escapes every rendered value and keeps boot settings in an `application/json` block.

Verified by `make release-check`. Counts are **not** written here on purpose: a number typed into
prose goes stale the next time a test is added (it already did), so this file records *what was
verified*, and the commands record *how much*. `make verify` is the authority; `PROJECT_STATE.md`
carries the last measured totals with the date they were taken.

## [0.2.0] — 2026-11-10

The control plane release: the governance layer became a running product instead of a design.

### Added
- **Control room** at `/`: roles, duties, prohibitions, money, approval queue, routines, audit
  trail, runs and incidents on one page, computed from stored rows. Single file, no external assets.
- **Persistence** (`repository.py`): SQLite or in-memory; append-only audit (no update/delete
  methods exist), approvals resolved exactly once by conditional update, idempotent ledger rows.
- **Ledger** (`services/ledger`): net revenue, margin, contribution, agent share, MRR and
  reconciliation from rows only. `make smoke` asserts the arithmetic end to end.
- **Worker** (`services/worker`): strict markdown routine parser (unknown key = error), cron
  matching, and a dispatch decision that refuses paused ventures, unknown ventures, un-budgeted
  runs and over-cap spend — each refusal written as an audit row.
- **Company as data** (`company/company.yaml` + `company.py`): 6 roles, 6 duties, 10 prohibitions;
  the loader refuses an agent at the root, a role with no prohibitions, an unbudgeted duty, a
  routine below the 15-minute floor, or ceilings above the company cap.
- `make demo` seeds a demo dataset **through the validated paths**, including a replayed payment
  event that is correctly ignored.
- `scripts/smoke.sh`: 10 end-to-end checks on a throwaway database.
- `aboutme.md`, `advantages.md`, `disadvantages.md`, `FEATURES.md`, `BLOCKERS.md`.

### Changed
- Sentinel API is versioned at 0.2.0 and grew `/v1/overview`, `/v1/pnl`, `/v1/ledger`.
- Test count is reported honestly from now on, and it is now printed by `make test` rather than
  typed into a document (that is how it went wrong before: **107 tests** — 52 sentinel including the
  15 company tests, 45 worker, 10 ledger).

### Fixed
- Documented test count was wrong (52 vs 37 was itself an undercount of the real suite).
- Routine outputs accept both `["#chan", "page:X"]` and `- channel: "#chan"` — the parser
  previously rejected the shape we actually wrote in every routine file.

### Security
- `SENTINEL_UI_TOKEN` gates approvals and ledger writes; the console prompts for it and keeps it in
  the tab only. Loopback stays open for `make demo`, a public address must not.
- The console escapes every value it renders and puts its boot settings in an
  `application/json` block, so a literal `</script>` in config cannot break out. Both are enforced by
  `tests/test_contract.py`.

### Known gaps
- The substrate (OpenBot Bots over AG-UI) is not wired to the worker yet — M1.
- No model key, no Intelligence project, no payment provider: see `BLOCKERS.md`.
- Docker absent in the build sandbox, so per-bot computers were never started here.

```
Verified by: make release-check
  make test        → 119 passed
  make smoke       → 10/10 checks
  make verify      → see plan.md §8b
```

## [0.1.0] — 2026-11-10

First cut: repositories installed and verified, Sentinel policy engine with 37 tests, skills layer,
post-mortem ledger, master plan.
