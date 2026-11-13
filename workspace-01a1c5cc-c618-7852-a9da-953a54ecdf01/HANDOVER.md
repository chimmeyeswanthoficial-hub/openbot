# HANDOVER.md — OpenBot OS v0.2.3

**To:** Reviewing AI (area.ai/agent)
**From:** Build engineer (Antigravity)
**Date:** 2026-11-13
**State:** T1–T9 complete. Suite green. Contract green. Ready for review + extension.

---

## 1. What this project is

OpenBot OS is a **self-hosted, governed autonomous agent company** built on:
- **OpenBot** (CopilotKit) as the substrate — the agent runtime, computers, and UI shell
- **Sentinel** — a FastAPI governance service: policy boundary, audit trail, approvals, ledger
- **Worker** — a scheduler that dispatches routines via AG-UI protocol under Sentinel governance
- **Media API** — the first venture: streaming ffmpeg conversion/split/compress, governed by Sentinel
- **Gateway** — an adapter that intercepts substrate tool calls and routes them through Sentinel policy

The project's invariant: **no outward action without an audit row and a policy decision**.

---

## 2. Current build state

```
python -m pytest          →  214 passed, 2 skipped   (216 collected)
python -m pytest services/sentinel/tests/test_contract.py  →  12/12 passed
ruff check services packages scripts  →  clean
make verify               →  22 pass / 0 fail / 7 warn (blockers, not bugs)
```

**Version:** `0.2.3` (`services/sentinel/app.py`)

### Test breakdown
| Suite | Tests |
|---|---|
| sentinel (policy, app, company, public, contract, pg) | 93 |
| worker (sentinel-client, heartbeat, digest, runner, spec, dispatch-agui) | 63 |
| gateway (mapper, adapter) | 15 |
| ledger (pnl, webhook) | 15 |
| media-api | 5 |
| venture-sdk | 20 |
| scripts/deploy | 5 |
| **Total collected** | **216** |
| **Passed** | **214** |
| **Skipped** | **2** (pg tests — skip without `DATABASE_URL`) |

---

## 3. Key file map

```
workspace-01a1c5cc.../
├── services/
│   ├── sentinel/           FastAPI governance API — policy, audit, approvals, ledger
│   │   ├── app.py          Routes: /v1/decide /v1/approve /v1/audit /v1/overview /v1/pnl
│   │   │                           /webhooks/stripe  GET/POST /v1/approvals
│   │   ├── policy.py       301-line policy engine (the boundary)
│   │   ├── repository.py   SQLite + PostgreSQL store (unified Store interface)
│   │   ├── console.html    Single-file admin UI (no external assets)
│   │   └── tests/
│   │       ├── test_contract.py    Anti-rot suite (12 tests) — MUST stay green
│   │       ├── test_policy.py      46 policy rule tests
│   │       ├── test_app.py         7 app endpoint tests
│   │       ├── test_company.py     18 org-as-data tests
│   │       ├── test_public.py      8 public endpoint / token-gate tests
│   │       └── test_repository_pg.py  2 pg tests (skip without DATABASE_URL)
│   ├── worker/src/
│   │   ├── main.py         Tick daemon (60s, --once, --deadman-url)
│   │   ├── runner.py       Worker.tick() — dispatch routines, apply sentinel decision
│   │   ├── sentinel_client.py  HTTP fail-closed client → POST /v1/decide
│   │   ├── heartbeat.py    Dead-man's switch pinger
│   │   ├── digest.py       Daily approvals digest + escalation
│   │   └── dispatch_agui.py  AG-UI dispatcher (max_runtime_min, budget_usd enforced)
│   ├── gateway/src/
│   │   ├── mapper.py       Maps substrate tool calls → Sentinel canonical actions
│   │   └── adapter.py      GatewayAdapter (fail-closed, AG-UI interrupt cards)
│   ├── ledger/src/
│   │   └── webhook.py      Stripe HMAC-SHA256 webhook → ledger rows
│   └── media-api/src/
│       ├── media_app.py    /v1/convert /v1/split /v1/compress (500MB cap, streaming)
│       └── ffmpeg_runner.py  Subprocess stdin/stdout pipe runner
├── packages/venture-sdk/   VentureSDK — venture + budget + milestone management
├── scripts/
│   ├── deploy.py           Deploy + rollback pipeline (deployments.json state)
│   └── tests/test_deploy.py  5 deploy pipeline tests
├── .openbot/
│   ├── routines/           Markdown routine definitions (scout-daily, deploy-request, etc.)
│   └── state/deployments.json  Deployment history (current_sha, previous_sha, history)
├── company/company.yaml    Org-as-data: bots, ventures, budgets, prohibitions
├── .env.example            All env vars with freellmapi config documented
├── .github/workflows/ci.yml  CI: lint + tests + contract + smoke + fresh-clone job
├── PROJECT_STATE.md        Living state doc (must match test counts — contract enforces)
├── PROJECT_REMAINING.md    Build queue (T1–T9 done; T10 = human calendar work)
├── CHANGELOG.md            [0.2.3] is latest — 216 collected
└── HANDOVER.md             This file
```

---

## 4. The five invariants (never break these)

1. **No audit row, no action.** Every outward call goes through `decide()` and persists before it acts.
2. **Policy is code, not prose.** Every rule has a failing test before its fix.
3. **Money comes from rows.** `GET /v1/pnl` sums audit rows — never a stored total, never an agent report.
4. **Never weaken a test to make a change pass.** The diff of `**/tests/**` is the first thing to review.
5. **Contract anti-rot test must always pass.** `PROJECT_STATE.md`, `README.md`, and the latest CHANGELOG entry must claim exactly `pytest --collect-only` count. Run `python -m pytest services/sentinel/tests/test_contract.py` after every change.

---

## 5. What's complete (T1–T9)

| Task | What was built | Tests |
|---|---|---|
| T1 | Worker ↔ Sentinel wiring (`sentinel_client.py`, `main.py`, fail-closed, 5s timeout) | 5 |
| T2 | Gateway adapter (`mapper.py`, `adapter.py`, AG-UI interrupt cards) | 15 |
| T3 | AG-UI dispatcher (`dispatch_agui.py`, hard runtime + budget limits) | 4 |
| T4 | PostgreSQL backend (`repository.py` SQLite+PG, `DATABASE_URL`) | 2 |
| T5 | Stripe webhooks (`webhook.py`, HMAC-SHA256, idempotency) | 5 |
| T6 | Media API first venture (`media_app.py`, streaming ffmpeg, 500MB cap) | 5 |
| T7 | Deploy pipeline (`deploy.py`, `deploy.sh`, rollback, `deployments.json`) | 5 |
| T8 | Dead-man's switch (`heartbeat.py`, urllib fail-safe) | 3 |
| T9 | Gate-starvation alarm + digest (`digest.py`, amber console banner, overview metric) | 3 |

---

## 6. What the reviewing AI should do / can extend

### High-value additions
1. **More GitHub integrations** — PR-to-routine: when a PR opens, fire a `code-review` routine through the Worker. Tie into `webhook.py` pattern.
2. **Slack / Discord notifications** — hook into `digest.py`'s output and post to a channel (the structure is there, just needs a sender).
3. **Vector memory / RAG** — add a `services/memory/` service: ChromaDB or pgvector, store routine outputs, let the dispatcher query context. CopilotKit Intelligence project (`B4`) must be set up first.
4. **Dashboard charts** — the console is intentionally a single HTML file. Add `Chart.js` from CDN to render `GET /v1/pnl` and `GET /v1/overview` as sparklines.
5. **CLI tool** — `python -m openbot <subcommand>` wrapping `scripts/` tools so the AI agents in the org can invoke deploy, smoke, verify without shell knowledge.
6. **Multi-venture support** — `company/company.yaml` already has a `ventures:` list. The sentinel policy is venture-aware. Add a venture selector to the console.
7. **Webhook for GitHub releases** — trigger auto-deploy when a release is published (uses `deploy.py` already).

### Repos worth pulling in (from hi.md / grokbot-clone pattern)
- `elie222/inbox-zero` — the approval resolution loop in `loop.ts` was already used for Gateway design; the email-to-task routing could become a `mail-intake` routine
- `nickvasilescu/grokbot-clone` — approval/resume loop already incorporated into `adapter.py`
- OpenDots routine definitions — can be mapped to `.openbot/routines/` templates

### How to add a new service
1. Create `services/<name>/src/<name>_app.py` (name the file `<name>_app.py` — not `app.py` — to prevent pytest module collisions)
2. Create `services/<name>/tests/test_<name>.py` + `conftest.py`
3. Add to `pyproject.toml` testpaths and pythonpath
4. Add to `services/sentinel/tests/test_contract.py` suites list in `_collected()`
5. Update `PROJECT_STATE.md` test counts + sync `docs/`
6. Add a `[0.x.y]` CHANGELOG entry

---

## 7. Owner blockers (still need human action)

| # | Blocker | Action needed |
|---|---|---|
| B1 | Linux box + Docker | Provision a VPS; `docker compose up` in `repos/OpenBot` |
| B4 | CopilotKit Intelligence | `npx copilotkit login && npx copilotkit project select` |
| B5 | Model key OR freellmapi | Set `OPENAI_API_KEY=freellmapi-c0e640e2...` + `OPENAI_API_BASE=http://127.0.0.1:31415/v1` |
| B6 | Secrets | `openssl rand -hex 24` → `KEY_ENCRYPTION_KEY`, `BOT_TOKEN_SECRET` |
| B9 | Stripe | Test-mode account + webhook endpoint → `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET` |
| B10 | Dead-man's switch | Healthchecks.io free tier → `DEADMAN_PING_URL` |

**freellmapi quick-start** (already in `.env.example`):
```bash
npx freellmapi setup-claude --url http://127.0.0.1:31415
# In .env:
OPENAI_API_BASE=http://127.0.0.1:31415/v1
OPENAI_API_KEY=freellmapi-c0e640e2ad229ee8bef49e4d0798c673c5b479bf2108cd03
BOT_PROVIDER=openai
```

---

## 8. How to verify the handover in 60 seconds

```bash
cd workspace-01a1c5cc-c618-7852-a9da-953a54ecdf01

# Suite + contract
python -m pytest -q                                       # 214 passed, 2 skipped
python -m pytest services/sentinel/tests/test_contract.py # 12 passed

# Boot the control plane
python -m uvicorn app:app --app-dir services/sentinel --port 8090 &
curl http://127.0.0.1:8090/healthz   # {"status":"ok","store":"ok"}

# Smoke (10 end-to-end checks)
bash scripts/smoke.sh                # 10/10

# Lint
ruff check services packages scripts  # clean
```

---

*Signed off: 2026-11-13 · 214 passed · 12 contract · ruff clean*

