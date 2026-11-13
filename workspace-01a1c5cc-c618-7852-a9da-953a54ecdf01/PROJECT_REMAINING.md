# PROJECT_REMAINING.md — the build brief

> **Build status as of 2026-11-13:** T1–T9 ✅ COMPLETE. T10 = human calendar work.
> See `HANDOVER.md` for the full handover to the reviewing AI.

**You are the new engineer (or AI) taking this repository.** This document is the transfer of my
judgement, not just my notes. Read `PROJECT_STATE.md` first for what exists; this file is what to do,
in what order, and how you will know it is done.

**Working rule for this project:** a task is finished when a stranger can watch it work and a command
can fail on it. Not when the file exists.

---

## 0. Start here (10 minutes, do not skip)

```sh
make install && make test && make smoke && make verify
bash scripts/session-start.sh
python3 -m pytest services/sentinel/tests/test_contract.py -v      # the anti-rot suite
```

Then read, in this order: `README.md` → **`PROJECT_BRAIN.md`** (how to think about this) →
`PROJECT_STATE.md` §3 (the request path) → `company/company.yaml`
→ `services/sentinel/policy.py` (301 lines, the whole boundary) → `.openbot/routines/scout-daily.md`
(what a routine actually is).

**If `make test` is red, fix that first and ship nothing else.** The repository's promise is that its
checks are honest; a red suite invalidates every other claim in these documents.

### The five rules you inherit

1. **No audit row, no action.** Every outward call goes through `decide()` and persists before it acts.
2. **Policy is code, not prose.** If you cannot write a failing test for the rule, it is not a rule.
3. **Money comes from rows.** Never a stored total, never an agent's report.
4. **Never weaken a test to make a change pass.** Read the diff of `**/tests/**` before anything else.
5. **Never edit `repos/`.** Seams live in `services/`, `packages/`, plugin points; markers must be
   listed in `patches/OPENBOT-OS.md` (`scripts/os-markers.sh --check`).

---

## 1. The blockers only the owner can clear (do these in parallel, they are calendar work)

| # | Blocker | Who | Why nothing else works without it | Reference |
|---|---|---|---|---|
| B1 | A Linux box with Docker | owner | the substrate cannot start | `BLOCKERS.md` B1 |
| B4 | CopilotKit Intelligence project (`npx copilotkit login / project select`) | owner | no threads, no memory, no Bot | `BLOCKERS.md` B4 |
| B5 | One model key (OpenAI is shortest; `BOT_PROVIDER=anthropic` also works) | owner | no agent turn is possible | `BLOCKERS.md` B5 |
| B6 | Generated secrets (`KEY_ENCRYPTION_KEY` **back it up**) | owner | server refuses placeholder secrets | `BLOCKERS.md` B6 |
| B9 | Stripe account (test mode needs no entity) | owner | no revenue can settle | `BLOCKERS.md` B9 |
| B10 | Dead-man's switch (Healthchecks.io or a $5 cron elsewhere) | you can set up | you cannot leave without it | `BLOCKERS.md` B10 |
| — | Legal entity + bank (live payments only) | owner | a human must sign; weeks of calendar time | `disadvantages.md` §2 |

Ask the owner for B1–B9 on day one. While waiting, do task **T1** below — it needs nothing.

---

## 2. The build queue

Each task states: **goal → files → acceptance (a command that fails today) → traps → est.**.
Estimates are the effort of a competent agent with a precise brief, not a human sprint.

### T1. Wire the worker to the Sentinel for real  ·  1 day  ·  *no dependencies*

**Goal:** the scheduler's dispatch decision is judged by the same boundary as everything else, in
production, not only in tests.

- **Files:** `services/worker/src/runner.py` — `Worker.__init__(..., sentinel=None)` already accepts
  an injected callable and `dispatch()` already applies its answer at line ~218 (a `deny` writes a
  `routine.dispatch` audit row and ends the run `denied`). So the *shape* exists and is tested; what
  is missing is a real client and a process that constructs it. Add
  `services/worker/src/sentinel_client.py`, `services/worker/src/main.py`, and
  `services/worker/tests/test_worker_sentinel.py`.
- **Do:** implement `SentinelClient.decide(action) -> dict` against `POST /v1/decide`
  (timeout 5 s, **on timeout or 5xx return `{"decision":"deny","rule":"sentinel.unreachable"}`** —
  fail closed, always). Construct `Worker(store=..., sentinel=client, ...)` in a small
  `services/worker/src/main.py` tick loop that runs `Worker.tick()` every 60 s and logs
  `{fired, refused}`.
- **Acceptance:**
  - a test where the Sentinel returns `deny` leaves the run `denied` **and** writes an audit row;
  - a test where the client times out leaves the run refused with `sentinel.unreachable`;
  - a manual run of `main.py` against the live Sentinel produces one `routine.dispatch` audit row per
    due routine.
- **Traps:** do not retry a *decision* (a timeout is a no, not an unknown); do not cache allows.
  **`Worker.tick()` is not yet idempotent** — its docstring says "fire everything due exactly once for
  this clock minute", but there is no `last_fired_minute` guard, so two ticks in the same minute
  dispatch twice. Write the failing test first (`services/worker/tests/test_runner.py`), then fix it;
  budget accounting counts dispatched spend, so a double dispatch also burns the daily cap twice.

### T2. The OpenBot gateway adapter  ·  2–3 days  ·  *needs a running substrate*

**Goal:** actions taken *inside* OpenBot (its browser/computer/MCP tool calls) are judged by our
Sentinel, and our approvals appear where a Bot can wait on them.

- **Files:** new `services/gateway/` (a small HTTP service, Python or TS — your choice, be consistent
  with the substrate if you write TS), plus a thin patch or plugin hook in
  `repos/OpenBot/server/` documented in `patches/OPENBOT-OS.md`.
- **How:** OpenBot's server already resolves a target, evaluates policy, writes an audit row and then
  calls the computer (`repos/OpenBot/docs/architecture.md` §"Browser action governance"). Put the
  Sentinel **in front of the final call**: map OpenBot's action to our `Action` (`kind`, `name`,
  `url/path`, `actor`, `initiator`), call `POST /v1/decide`, and on `gate` return the AG-UI interrupt
  and block — the same shape as `repos/OpenBot/docs/approvals.md`.
- **Acceptance:**
  - a Bot asking to `gmail.send_message` inside OpenBot appears in `GET /v1/approvals` and the chat
    shows a waiting card;
  - approving it in the OpenBot UI resolves **our** approval row (`approval_id` matches in both
    audit trails) and the run continues once;
  - denying it stops the run, and the transcript says why;
  - a Bot writing outside its venture's write root is denied and the run is killed.
- **Traps:** do not duplicate approval UIs — pick one as the surface of record (recommendation:
  OpenBot's, because the person is already in the conversation; our console becomes the admin view);
  write the mapping table (OpenBot tool name → our `kind`/`name`) in one file with a test per row;
  keep the OpenBot audit row **and** ours, they answer different questions (`initiator_kind` is ours).

### T3. Routine dispatch → a real Bot over AG-UI  ·  2 days  ·  *after T2*

**Goal:** "a routine fires and something actually happens".

- **Files:** `services/worker/src/dispatch_agui.py`, one agent implementation choice (see
  `company.yaml`: `ceo`/`growth` → `agent-bot`, `cto` → `agent-langgraph`, `ops` → `agent-mastra`,
  `auditor` → `agent-computer`), tests with a fake AG-UI endpoint.
- **Acceptance:** at its cron minute, `scout-daily` runs the real Bot, its output lands in the channel
  named in the routine's `outputs`, and the run row moves `queued → running → succeeded` with a cost.
- **Traps:** a run that exceeds `max_runtime_min` must be killed and recorded (`health-sweep` relies on
  this); the routine's `budget_usd` must be passed down as a hard stop, not a suggestion.

### T4. Postgres instead of SQLite  ·  1 day  ·  *independent*

**Goal:** survive restarts and multiple workers; this is the only file that changes.

- **Files:** `services/sentinel/repository.py` only (`Store` interface stays identical),
  `services/sentinel/tests/test_repository_pg.py` (skipped when `DATABASE_URL` is absent).
- **Acceptance:** the entire suite passes with `SENTINEL_DB=postgres://…`; `audit` has a REVOKE
  UPDATE/DELETE grant for the app role; `resolve_approval` still returns `False` on a lost race under
  10 concurrent calls (write that test — it is the one that proves the conditional UPDATE).
- **Traps:** do not add an ORM; keep `sqlite3` working for `make demo` (two backends, one interface).
  A single `idempotency_key` UNIQUE constraint must exist in Postgres too, or revenue can double.

### T5. Payment webhooks → the ledger  ·  2 days  ·  *needs B9*

**Goal:** revenue appears only when the provider says so.

- **Files:** new `services/ledger/src/webhook.py` + a route on the Sentinel
  (`POST /webhooks/stripe`), tests with recorded fixtures.
- **Acceptance:**
  - verify the provider signature (reject on mismatch — test it with a tampered body);
  - `invoice.paid` → `kind: revenue` with `idempotency_key = <event id>`; the same event replayed
    yields `200 {created:false}` and no second row;
  - `charge.refunded` → `kind: refund`; `balance_transaction` fees → `kind: fee`;
  - a nightly job writes `cogs` from the infra bill (idempotent by date+venture);
  - `pnl.reconcile(rows, provider_gross)` returns `drift_usd == 0.00`, and when you deliberately break
    one row it returns non-zero **and raises an alert** rather than adjusting.
- **Traps:** never trust a webhook without a signature check; never fetch "amount" from the model —
  it is in the event; store the raw event id, not a hash of it.

### T6. Media API — the first venture's product  ·  4–6 days  ·  *needs T2/T5 for end-to-end*

**Goal:** one endpoint, one price, one invoice. This is the thing a stranger pays for.

- **Files:** new `services/media-api/` (FastAPI, `ffmpeg` subprocess, `/healthz`, `/v1/split`,
  `/v1/convert`, `/v1/compress`), `services/media-api/tests/`, the venture's policy file
  `services/sentinel/policy/media-api.yaml` (already exists — extend it).
- **Acceptance:**
  - a 250 MB synthetic file splits without touching `/tmp` (the post-mortem rule `pm_…_01`: stream,
    do not buffer) — this test exists as a requirement, write it first;
  - p95 < 20 s for a 100 MB convert on the VPS, measured and written into `unit_economics`;
  - `/healthz` returns `{ok, ffmpeg}` and `503` when the binary is missing;
  - the endpoint is metered: units are counted per call and reported to the ledger as `revenue` only
    after the provider settles.
- **Traps:** do not build a dashboard before the endpoint works; do not accept uploads into memory
  unbounded; cap file size and return `413` with a message a person can read (`openbot-copy` skill).

### T7. Deploy pipeline  ·  2 days  ·  *independent*

**Goal:** an agent can *request* a deploy; a human or a gate can approve it; a rollback is tested.

- **Files:** `scripts/deploy.sh`, `.github/workflows/*` or a `routines/deploy-request.md`, and a
  `deployments.json` state file.
- **Acceptance:** build once by sha → migrate (expand/backfill/contract) → canary one instance →
  smoke (health, one read, one gated write in staging) → roll out → record
  `{image_sha, migration_id, previous_sha}`. Then **execute a deliberate rollback** and show the
  service healthy on the previous sha.
- **Traps:** a non-reversible migration blocks the deploy; agents never write to prod — they write a
  deploy request.

### T8. The dead-man's switch + alerts  ·  0.5 day  ·  *do this before anything unattended runs*

**Goal:** a company that cannot tell you it is dead is not running itself.

- **Acceptance:** two independent signals (control-plane heartbeat; "no routine completed in 6 h") go
  to an external monitor; killing the box produces an alert within the hour. Test it by killing it.

### T9. Approvals daily digest + gate-starvation alarm  ·  1 day

**Goal:** the #1 real-world failure of human-in-the-loop is a queue nobody clears.

- **Acceptance:** one message per day listing pending approvals with counts and ages; if the oldest is
  > 24 h, the message escalates and the console banner turns amber; a metric
  `approvals_pending_max_age_hours` exists in `/v1/overview`.
- **Traps:** do not auto-approve anything to "unblock" the company. Ever. That is the one change that
  would make this project dangerous.

### T10. The 30-day dress rehearsal  ·  calendar, not effort

**Goal:** you learn what is missing while it is cheap.

- **Acceptance:** the owner leaves for 30 days at ~$1k MRR with a read-only dashboard; on return the
  company (a) made money, (b) filed and fixed its own incidents, (c) did nothing the owner would not
  have approved. Write the findings into `post_mortems` and fix the top three before scaling.

---

## 3. Dependency order

```
T1 ──┐
T4 ──┼──► T2 ──► T3 ──► T6 (end to end) ──► T10
T5 ──┘             ▲
T7 ── T8 ── T9 ────┘
```

Do **T1, T4, T8** first: they need nothing from the owner and they make everything after them
testable. T2/T3 are the real product gap — say so in every status update until they are done.

---

## 3a. Where this brief may be wrong (read before trusting it)

I wrote it from a measured inventory, but not every claim in it was re-verified against the code.
These are the ones I would check first, and the correction I would expect to find:

| Claim in T2 | Check it before you start | If contradicted |
|---|---|---|
| OpenBot "evaluates policy, writes audit, then calls the computer" | grep `repos/OpenBot/server` for the policy call site and read the surrounding 50 lines | The hook is still the right seam; the *file* moves. Find the single chokepoint that every tool call passes through and put the Sentinel there — if there is no chokepoint, **build it** (that is the real work, budget a week) |
| OpenBot approvals are AG-UI interrupts | read `repos/OpenBot/docs/approvals.md` end to end | Adapt our `approval_id` to whatever the waiting primitive is; do not build a second queue |
| The gateway should be a separate HTTP service | you may be able to patch the server directly | Prefer the **in-process hook** if the substrate exposes one — one fewer process to keep alive is one fewer thing to monitor |

| Claim in T3 | Check | If contradicted |
|---|---|---|
| Each role maps to a named `agent-*` package | they live at the repo root, not in a subfolder: `ls repos/OpenBot/agent-*` — I confirmed **`agent-bot`, `agent-langgraph`, `agent-computer`, `agent-mastra` are all present** in the pinned tree | If a pin bump removes one, pick from what is installed; `company.yaml` is data, so edit it and `test_company.py` together |
| A routine's `outputs` (channel/page) are writable by the Bot | check the Bot's Slack/notion skills | Until a channel is connected, land output in the run row + `#ops-daily` fallback file; do not block M1 on Slack |

| Claim in T4/T5 | Check | If contradicted |
|---|---|---|
| `repository.py` is the only storage file | `grep -rn "sqlite3\|connect(" services packages` | Any direct connection outside `repository.py` is a bug — fix it in the same PR |
| Stripe is the right provider | `company.yaml` + `disadvantages.md` §2 | The webhook contract (signature, event id, replay) is the requirement; the vendor is not. Keep `webhook.py` vendor-thin |

**The honest summary:** T1, T6, T7, T8, T9 are specified against code I have read. T2, T3 and T5 are
specified against upstream documentation and *labels* — read the upstream source before you trust the
file paths in them. Nothing in this brief requires you to trust me; every acceptance check is a
command that either passes or fails.

---

## 4. How to prove your work (the definition of done, inherited)

For every task:

- [ ] A test fails on `main` before your change and passes after.
- [ ] Every new outward action returns a policy decision and writes an audit row.
- [ ] `make release-check` is green (verify + test + smoke).
- [ ] Docs updated in the same commit, and `scripts/sync-docs.sh` run if you touched a root document.
- [ ] `aboutme.md` still tags the capability honestly (`[shipped]` / `[M1–M3]` / `[human]` / `[never]`).
- [ ] If you fixed a bug: a `postmortem` ledger entry with an **enforced** `rule_kind` and a real
      `rule_ref`.
- [ ] Your PR body states, in one sentence, what could now go wrong.

## 5. What NOT to build (I thought about these; do not)

| Tempting | Why not |
|---|---|
| Autonomous entity formation / filings / tax positions | legally a human act; a jail sentence dressed as a feature (`disadvantages.md` §2) |
| Autonomous price changes | highest blast radius decision in a company; one bad night destroys the margin |
| Agents sending mail or publishing without a gate | the single change that turns this from a tool into a liability |
| A marketplace of third-party skills | shipping someone else's instructions into a company with a bank account |
| A second venture before the first pays | `D7`; scope sprawl is the #1 killer in `plan.md` §13 |
| Porting Rakazo's mobile/desktop clients | OpenBot already ships desktop builds; wrapping is a maintenance tax |
| Rewriting the substrate in Python | the substrate is TS for good reasons (AG-UI, computers, components); our logic is Python on purpose |

## 6. Traps that will bite you specifically

1. **`repos/` has no `.git` history** (tarballs). `git init` + remote + tag the pin before you touch
   anything, or you cannot rebase upstream ever (`BLOCKERS.md` B3).
2. **`muse` refuses to run without Bubblewrap** and warns if it is installed under a writable root.
   `apt install bubblewrap`, install it to `/opt/muse`, and check `muse skills list` shows our skills.
3. **The workspace snapshot is capped at ~128 MB / 10k files.** Node's and Bun's binaries are not
   recoverable from it (`tools/README.md`); large upstream media was moved out
   (`scripts/restore-media.sh`). Watch `make verify` §4 when you `npm install` anything.
4. **SQLite file deletion under a running server** produced the only 500 I shipped; the guard exists
   now (`_must_persist`). Do not "clean up" state files while the service runs.
5. **The console is served by the Sentinel itself**, not by Vite. It must stay a single file with no
   external assets or it breaks in the sandboxed preview and behind a strict CSP.
6. **Contract tests will fail you for stale docs** — that is the feature, not an obstacle. Run
   `scripts/sync-docs.sh`.
7. **Never let an "allow" be cached.** A policy decision is per-action, per-initiator. The moment you
   memoise it, an unattended run inherits a person's approval.

## 7. Milestone gates (do not start the next until the previous is green)

| Gate | Green when |
|---|---|
| **M1** | a routine fires at 06:00, is audited as `initiator=routine`, asks permission for anything dangerous, and lands in its channel — for **7 consecutive days** with no manual step |
| **M2** | a stranger can pay for Media API; the row comes from the webhook; a refund was exercised in test mode; a rollback was executed once on purpose; the 250 MB test is green |
| **M3** | 30 days with no sev1/sev2; monthly review auto-generated; restore drill green; a prompt change promoted only through evals |
| **M4** | ≥ $5k MRR, or a written evidence-based pivot; agent cost per venture known to the dollar |
| **M5** | the 30-day dress rehearsal passed |

## 8. If you disagree with me

Good. Argue it in `STACK_DECISIONS.md` as a new dated entry (the file is append-only) and change the
code in the same PR with a test. What you may not do is quietly relax a safety rule, remove a gate, or
make a document claim something the code does not prove. Those three are the project.

---

**Handover signature**

```
State verified : 2026-11-10   make test → 165 passed · make smoke → 10/10 · make verify → 0 fail
                 22 pass / 7 warn as shipped · 23 pass / 6 warn with the Sentinel running
Built          : governance boundary, ledger, worker, venture SDK, org-as-data, console, skills, 12 documents
Not built      : T1–T10 above (substrate wiring, webhooks, the first product, deploy, alerts, rehearsal)
Blocked on     : B1, B4, B5, B6, B9 (owner); B3, B10 (you, 1 day)
The one thing  : the Bot ↔ worker connection (T2/T3) is the difference between "the boundary works"
                 and "the company works". Do not let feature work jump that queue.
```
