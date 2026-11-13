# OpenBot OS — Master Plan

**Status:** M0 complete (environment installed, governance layer running) · **Version:** 1.0
**Owner:** you · **Written:** 2026-11-10 · **Next review:** 2026-11-17
**Source material:** `uploads/Untitled document.docx.pdf` (8 pages), plus the four repos below.
**Owner decisions (2026-11-10):** OpenBot is the host · first venture is Media API · own VPS + Docker ·
no model/payment accounts yet (see `STACK_DECISIONS.md` C1–C4 and `BLOCKERS.md`).

---

## 0. One paragraph

You are building one thing, not five: **a governed runtime that lets agents start, run and scale
small businesses without supervision, and that cannot repeat a mistake it has already paid for.**
OpenBot is the substrate (it already has the policy gateway, the per-bot computers, the scheduler
and the human-approval engine). Rakazo, OpenDots, Grok Bot and Meta Muse Code are feature donors
and labour, not products to merge. The novelty we build is the **venture layer** (manifest → P&L
ledger → kill criteria) and the **self-evolution loop** (incident → enforced prevention rule).
Everything else in the PDF already exists in the four upstreams and should be *ported, not
rewritten*.

---

## 1. What is installed and verified (M0 — done today)

| Piece | Where | State | Proof |
|---|---|---|---|
| OpenBot (substrate) | `repos/OpenBot` | source + deps (`bun install --frozen-lockfile`, 1282 pkgs) | repo tree, `bun.lock` honoured |
| Rakazo (feature donor) | `repos/rakazo` | source + deps (`pnpm install --frozen-lockfile`, 2200 pkgs) | pnpm v12.18.0, Node 24.22.2 |
| OpenDots (review-gate donor) | `repos/OpenDots` | source + deps (`npm ci`, 1046 pkgs) + **`npm run typecheck` green** | typecheck exit 0 |
| Meta **Muse Code** (`muse`) | `~/.local/bin/muse` | **installed, v1.4.14 (R7309.1)** | `muse --version` |
| Sentinel policy engine | `services/sentinel` | **52 tests green** (policy + endpoints + company), service **running on :8090** | `curl :8090/healthz` → `{"ok":true,...}` |
| Skills layer | `.claude/skills/` | 8 skills + inherited upstream skills | `scripts/session-start.sh` |
| Ledger + state | `.openbot/` | post-mortem ledger with 1 real entry + checker | `check.sh` → `0 problem(s)` |

**Three honest caveats about the install:**

1. **`git clone` crashes the sandbox shell**, so all three repos came from GitHub tarballs
   (`codeload.github.com/.../tar.gz`). There is no `.git` history in them yet. Fix when you run
   this on your own machine, or run `git init` + `git remote add` (see `INSTALL_LOG.md`).
2. **The `irm .../install.ps1` command is Windows-only PowerShell** and installs **Meta Muse Code
   (the `muse` CLI)**, not "Meta Muse" the consumer app. On this Linux box the equivalent
   `curl -fsSL https://dev.meta.ai/install.sh | bash` was used, with `MUSE_INSTALL_DIR=~/.local/bin`.
   Muse also needs a Meta Model API account before it can run a turn — that is a key you must add.
3. **Docker is not available in this environment**, so OpenBot's and Rakazo's computers/sandboxes
   (their core value) could not be started here — only installed and type-checked. Production must
   run on a Docker host (see §11).

Full reproduction steps: **`INSTALL_LOG.md`**. Decisions taken and why: **`STACK_DECISIONS.md`**.

---

## 2. The PDF, translated into things that can actually be built

The PDF is good raw thinking with three categories of content. Separating them is the most useful
thing I can do for you.

### 2.1 Already solved by the repos (port, don't build)

| PDF ask | Reality |
|---|---|
| Markdown routines from an Obsidian folder | OpenBot has governed **routines** + a worker; Rakazo has markdown-first routines. We need a *parser contract* only. |
| Human-in-the-loop approval queue | OpenBot's `docs/approvals.md` is a complete, tested ladder (safety → rules → auto-review → default). OpenDots has the approve-before-save card. Copy the vocabulary, wire the queue. |
| Sentinel proxy masking keys | OpenBot's gateway already resolves/policies/audits browser+MCP actions and has an egress proxy per computer. Our Sentinel adds **raw HTTP** + **money** + **cross-venture isolation**. |
| Multiple agent personas with separate memories | OpenBot Bots + Rakazo group chats/delegation + OpenDots specialist Dots. |
| Media pipelines (ffmpeg/Pillow) | Trivially available; it is a **venture**, not a platform feature (see Venture 01). |
| Expo mobile / Electron desktop | Rakazo ships web+desktop(iOS/Android); OpenBot ships desktop builds. Don't wrap anything. |
| Voice client engine | Rakazo has voice/calls; OpenDots has realtime speech + compute bridge. |
| Playwright teach-by-demonstration | Grok Bot's idea; Rakazo has computer use + recordings. Implement as a **session recorder → routine** (see §6, L3). |

### 2.2 Fix the technical inaccuracies (so you don't build on sand)

| PDF says | Correction | What we do instead |
|---|---|---|
| "FastAPI backend + React frontend, inject features as custom FastAPI endpoints" | OpenBot is **TypeScript** (Bun + Hono + React + Postgres/pgvector). Rakazo is TS. OpenDots is TS. | Keep the substrate TS. Put **Python where the PDF wants it**: the Sentinel, the routines parser, media pipelines, and every venture service. One HTTP contract between them. |
| "Model: claude-3-5-sonnet / claude-3-opus" | Those model names are two generations stale; hard-coding models is how a system rots. | Route by **capability tier** (`fast | balanced | deep`) in one config; `muse` and Claude Code both sit behind the same order format. |
| "Dynamic LLC provisioning via Stripe Atlas" | Entity formation is legally gated: KYC, identity documents, real money, human signature. It cannot be autonomous, and pretending otherwise is a legal risk. | Human does formation **once**. Agents do everything after: repo, domain, deploy, Stripe product/price, invoices, docs. Automated **venture provisioning** (`§7.2`). |
| "Auto-allocate budgets, spin up AWS/GCP containers" | Real, but spend is the fastest way to lose money unattended. | Spend is **deny-by-default, gate above $0** until a venture has revenue (`§8`). |
| "Rewrite its own system prompts / swap LLM backends" | Self-editing prompts with no eval harness produces confident drift. | Prompt/model changes are **experiments** gated by an eval suite and a canary (`§6`, L4). |

### 2.3 Genuinely new — this is what we build

1. **Venture SDK + P&L ledger** — a venture is a validated manifest, an isolated sandbox, a budget
   line, a policy file, kill criteria, and a double-entry-ish ledger fed by payment webhooks.
2. **Post-mortem → prevention loop** — every incident must land a rule of kind `test | policy | type
   | lint | prompt`, and the ledger checker fails CI when the rule is missing or its test is absent.
   (Shipped today; `§6`, L1.)
3. **Market → venture → launch pipeline** that runs on a schedule, unattended, with a human gate on
   price and on anything that leaves the building.
4. **Skill acquisition loop**: learn a tool in `deny_all`, verify in a throwaway sandbox, promote by
   PR — never learn directly into production.
5. **The unattended-operation contract**: dead-man's switch, auto-pause on sev1, monthly
   auto-generated review, one-command stop. This is the difference between "runs 24/7" and "ran
   until it silently died in week 6".

---

## 3. The decisions this plan is built on (and their alternatives)

| # | Decision | Why | If you disagree |
|---|---|---|---|
| D1 | **OpenBot is the substrate.** Rakazo and OpenDots are donors. | OpenBot is the only one with policy+audit+approvals+computers+supervisor already wired. It's MIT and threadbare enough to own. | Rakazo as host is also viable and more feature-complete out of the box, but you'd be re-implementing governance on top of a product that optimises for personal use. |
| D2 | **Our code lives in `services/`, `packages/` and plugin seams.** Upstream edits are marked `OPENBOT-OS:` and upstreamed as PRs. | Three fast-moving upstreams + a year unattended = you must be able to re-pull. | A hard fork freezes you on today's version and inherits every future CVE. |
| D3 | **Policy in code, not in prompts.** | Prompts are suggestions; a regex in `policy.py` is a boundary. | — |
| D4 | **Money is human-gated until revenue exists.** `auto_spend_usd: 0`. | The single most expensive unattended failure mode. | You can raise it per venture, in a PR, with a reason. |
| D5 | **Revenue is read from webhook rows only.** | Agents that "report" revenue invent it. | — |
| D6 | **Python for the Sentinel/ventures, TS for the product.** | Matches the PDF's instinct and the repos' reality. | — |
| D7 | **One venture at a time until the first one pays.** | The PDF's "multiple companies" is the reward for focus, not a substitute for it. | — |

---

## 4. Architecture

```text
                     ┌──────────────────────────── Obsidian / .md routines ───────────────────────────┐
                     │  .openbot/routines/*.md   (+ venture.yaml, AGENTS.md, post_mortems)            │
                     └───────────────────────────────────┬────────────────────────────────────────────┘
                                                         │ vault watcher → RoutineSpec (pydantic)
┌────────────────────────────────────────────────────────▼───────────────────────────────────────────┐
│  RUN ORCHESTRATOR  (Python worker, services/worker)                                                │
│  cron floor 15m · budget per run · initiator=routine · retry once · sev1 auto-pause                │
└───────┬──────────────────────────────┬──────────────────────────────┬──────────────────────────────┘
        │                              │                              │
┌───────▼────────────┐      ┌──────────▼───────────┐      ┌───────────▼────────────────────────────┐
│ OPENBOT SUBSTRATE  │      │ SENTINEL (FastAPI)   │      │ VENTURE RUNTIME                        │
│ app :3010          │      │ :8090                │      │ services/<venture> (FastAPI)           │
│ server :3001       │◄────►│ decide() → audit row │◄────►│ sandboxed, egress allowlist            │
│ computers :4100    │      │ HITL approvals queue │      │ deploy via deploy-request → canary     │
│ supervisor :4500   │      │ secret scrub+inject  │      │ P&L rows on payment webhook            │
│ postgres/pgvector  │      └──────────┬───────────┘      └───────────┬────────────────────────────┘
│ routines worker    │                 │                              │
└───────┬────────────┘                 │                    ┌─────────▼─────────┐
        │                              │                    │ PAYMENT PROVIDER  │
┌───────▼────────────┐        ┌────────▼─────────┐          │ (webhook only)    │
│ COPILOTKIT         │        │ MINI-ANTHROPIC/  │          └───────────────────┘
│ INTELLIGENCE       │        │ MODEL GATEWAY    │
│ threads + memory   │        │ (capability tier)│
└────────────────────┘        └──────────────────┘
        ▲                              ▲
        │                              │  coding labour: Claude Code · muse (event log → trace.jsonl)
        └──────────── AG-UI events to the UI ──────────────┘
```

**Ports / processes to run:** OpenBot `app 3010`, `server 3001`, `agent-computer 4100`,
`supervisor 4500`, Postgres 5432; Sentinel 8090; worker (no port); venture services 8100+.
Everything except the Sentinel needs Docker; the Sentinel and the worker do not.

**Two boundaries, never crossed:** (a) an agent never holds a real credential — Sentinel injects a
per-run, TTL-bounded alias; (b) a venture never reads another venture's path, schema or ledger.

---

## 5. Feature port matrix (what comes from where)

Effort is agent-days for a competent coding agent with a precise order (`agent-delegation` skill).

| # | Capability | From | Lands in | Effort | Depends on |
|---|---|---|---|---|---|
| P1 | Markdown routine parser + vault watcher | Rakazo + PDF | `services/worker` | 3 | — |
| P2 | Human-in-the-loop queue UI (approve/deny, resumable) | OpenDots card + OpenBot approvals | OpenBot `app` + Sentinel | 5 | P1 |
| P3 | Egress proxy with secret scrub + key injection | OpenBot egress + PDF Sentinel | `services/sentinel` (engine done) | 6 | — |
| P4 | Per-venture isolation (paths, schema, keys, budget) | PDF + OpenBot computers | supervisor + Sentinel policy | 4 | P3 |
| P5 | Post-mortem ledger + CI prevention checker | PDF + our `postmortem` skill | `.openbot/post_mortems` (done) + CI | 1 | — |
| P6 | Teach-by-demonstration (record session → routine) | Grok Bot | OpenBot computers + worker | 8 | P1,P2 |
| P7 | Group chat / delegation between personas | Rakazo | OpenBot channels + AG-UI bots | 10 | substrate |
| P8 | Shareable Pages (dashboards/docs by link) | Rakazo | new `services/pages` | 8 | — |
| P9 | Voice + calls | Rakazo/OpenDots | OpenBot channel plugin | 12 | P-expensive; defer |
| P10 | Mobile/desktop clients | Rakazo — **don't port** | use OpenBot's desktop build + Tauri mobile | 2 (config) | — |
| P11 | Eval harness for prompts/models | ours | `services/evals` | 5 | P5 |
| P12 | Market scraper feed (GitHub/PH/X/SEO gaps) | PDF | `services/scout` | 4 | P1,P3 |
| P13 | Venture SDK + manifest validation | ours | `packages/venture-sdk` | 3 | — |
| P14 | P&L ledger + payment webhooks + nightly MRR | ours | `services/ledger` | 5 | P13 |
| P15 | Deploy pipeline (build → migrate → canary → rollback) | ours | `scripts/deploy` + `ship-it` skill | 4 | P4 |
| P16 | Skill acquisition loop (learn → sandbox → promote) | PDF | `services/skills-lab` | 10 | P3,P11 |
| P17 | Admin/ops console: costs, incidents, ventures, pause-all | ours | OpenBot `app` route | 6 | P14 |

**Sequencing rule:** P5, P13, P3, P1 first — governance before features. A feature shipped before
its gate is a liability you will pay for at 3 a.m.

---

## 6. The self-evolution loop (the actual differentiator)

Five loops. Each has an owner agent, a cadence, an artifact and a hard stop.

### L1 — Incident loop (built today)
`exception → structured ledger row → earliest catching layer → rule of kind test|policy|type|lint|prompt
→ rule_ref must exist and be green → CI fails otherwise.`
Runs on every failure. Owner: **Auditor**. Artifact: `.openbot/post_mortems/error_registry.jsonl`.
Verifier: `.claude/skills/postmortem/check.sh` (run it in CI before every deploy).

### L2 — Verification loop (before anything ships)
Every routine runs its work, then a **separate** verifier agent (never the author) checks the
artifact against the order's acceptance test. If it fails twice, escalate model tier; three times,
stop and file L1. Staging only — never prod.

### L3 — Skill acquisition loop (month 2+)
`market/docs/GitHub → read → write a SKILL.md + a thin wrapper → run it in a deny_all sandbox with
mock credentials → record a replayable trace (muse's event log is exactly this) → promote by PR with
the trace attached.` Nothing learned enters production without a trace a human can replay.

### L4 — Model/prompt tuning loop (month 3+)
Track per-task outcomes (`success`, `cost`, `wall_ms`, `retries`) per model tier. A change to a
prompt or a model is an **experiment**: `services/evals` case → run against the current champion →
only a statistically honest win (≥20 cases, no regression on the safety cases) is promoted, then
canaried for a week. No autonomous prompt self-editing, ever.

### L5 — Business loop (weekly)
`ledger rows → weekly review → scale / fix / kill` per venture, using `venture-launch` kill
criteria. Output is a one-page doc generated from rows, plus exactly one decision per venture.

**What "never make the same mistake again" actually means here:** not memory, not a vector
retriever of old errors — *a test that fails, a policy rule that denies, or a type that won't
compile.* Memory helps; enforcement is what changes behaviour.

---

## 7. The venture engine

### 7.1 A venture is six files and one row

```text
.openbot/ventures/<slug>/
  venture.yaml            # manifest: thesis, ICP, pricing, unit economics, budgets, kill criteria
  AGENTS.md               # the venture's inherited rules (from the post-mortem ledger)
services/sentinel/policy/<slug>.yaml    # egress, spend, write roots, data class
services/<slug>/        # the product: FastAPI (or TS if it must share the substrate)
.openbot/routines/<slug>-*.md           # health check, COGS sync, growth, support triage
+ one Postgres schema + one ledger_account + one budget line
```

`python -m venture_sdk validate .openbot/ventures/<slug>` is the only way in. A venture that does
not validate cannot be started by the orchestrator.

### 7.2 Provisioning is automated; formation is not

| Step | Who | Automated? |
|---|---|---|
| Entity, bank, tax registration (KYC) | **human, once** | no — legally cannot be |
| Domain, DNS, repo, deploy target | agent | yes, gated on spend |
| Stripe product + prices (matching `venture.yaml`) | agent proposes, human approves price | price = gated |
| Landing page, docs, status page | agent | yes |
| Terms/privacy/refund text | agent drafts, human approves | gated (legal) |
| Health checks, alerts, on-call routines | agent | yes |
| Invoices, refunds, dunning | agent, within policy | refunds gated |

### 7.3 The revenue challenge, honestly

$100k in year one from an unattended system is possible but not by "spawning companies". The
realistic ladder, measured in the ledger:

| Milestone | Month | What must be true | Reading |
|---|---|---|---|
| First $1 | 2 | one venture live, one paying human, price approved | 1 row |
| $1k MRR | 4 | one repeatable channel with CAC payback < 6 mo | 30-day recurring rows |
| $5k MRR | 7 | second venture or second channel, margin > 60% | nightly `pnl.json` |
| $10k MRR (≈$120k ARR) | 10–12 | support cost near zero, churn < 5%/mo | ledger + incident rate |

Two paths, pick one deliberately:
- **A: narrow SaaS** (Venture 01/02 in the PDF). Slow start, compounding, low attention.
- **B: productized service** delivered by agents (e.g. "we convert/publish/audit your X, monthly").
  Faster to first dollar, higher price, but needs a human in the loop for trust at the start.
  **Recommended: B to fund A.** Use service cashflow to buy the time a SaaS needs.
The PDF's "challenge 100k+ revenue as fast as possible" is best served by B; "leave for a year" is
best served by A. You need both, in that order.

---

## 8. Guardrails (what makes walking away survivable)

| Guardrail | Mechanism | Where |
|---|---|---|
| Fail closed | unknown venture → deny; missing policy → deny; broken rule → deny | `services/sentinel/policy.py` (done) |
| Always-gated actions | money, credentials, delete, outbound comms, publish, sharing | `SAFETY_RULES` (done, tested) |
| Secret hygiene | shape detection → scrub + escalate; protected paths denied; per-run TTL alias | `policy.py` (done) + key injection (P3) |
| Isolation | write roots per venture; cross-venture read = kill the run + sev1 | `policy.py` (done) |
| Budget | per-run `budget_usd`, per-venture day/month cap, company cap, `auto_spend_usd=0` | `.openbot/state/budget.json` |
| Runaway loop | 3 consecutive failures on one step → stop + L1; `max_runtime_min` → kill | worker (P1) |
| Kill switch | one command pauses every venture + every routine, writes an audit row | `scripts/pause-all.sh` (to build, M1) |
| Dead-man's switch | external monitor; no heartbeat for 2h → email/SMS the human | M2 |
| Reversibility | every deploy records previous sha + migration id; rollback tested quarterly | `ship-it` skill |

---

## 8b. The company layer (added 2026-11-10, after M0)

The PDF described a company; a company needs an org chart that can veto itself. That is now data,
not prose:

- **`company/company.yaml`** — 6 roles (1 human owner + 5 agent roles), each with a mandate, explicit
  permissions, explicit prohibitions, an OpenBot `agent-*` implementation and a monthly cost ceiling;
  6 standing duties, each bound to a real routine file; 10 company-wide prohibitions.
- **`services/sentinel/company.py`** — refuses to load an inoperable company: no root, an **agent** at
  the root, a capability both allowed and forbidden, a duty with no budget or no `initiator: routine`,
  a routine faster than the 15-minute floor, a `bot` that does not match the duty's owner, an
  `agent_impl` OpenBot does not ship, fewer than 5 prohibitions, or role ceilings above the company cap.
  15 tests, each breaking the real file and requiring the refusal.
- **`scripts/verify.sh`** — 17 checks across artifacts, governance, routines, snapshot budget,
  substrate, and unattended-readiness. It is allowed to say **NOT GO**, and it does: substrate and
  accounts are warned, not faked.
- **`scripts/pause-all.sh`** — the kill switch: pauses a venture, appends a sev1 row with
  `rule_kind: policy`, stops the Sentinel, and prints the resume path. Tested end to end.

**Verified live on :8090** (six adversarial calls): clean read → `allow`; routine sending mail →
`gate` + approval id; cross-venture write → `deny isolation.write_root`; cloud metadata IP → `deny
network.metadata_or_internal`; secret in payload → `gate` + `[SCRUBBED]`; unknown venture → `deny
policy.unknown_venture`.

**Port corrections found while reverse-engineering** (these change §5):
`FEATURES.md` records that OpenBot **already ships** three things the PDF assumed we must build —
the teach-a-task recorder (`extension/` + masking rules + demonstrations schema), the per-computer
egress filter, and voice sessions. The genuinely missing pieces are Rakazo's **webhook-triggered
routines + watch mode**, its **ticket board**, and OpenDots' **per-tool approval toggles**. Build order
is in `FEATURES.md` §6.

## 9. Skills (the "use skills for everything" part)

Installed and load-bearing today (`.claude/skills/`, indexed in `.claude/skills/README.md`):

| Skill | Load when |
|---|---|
| `openbot-os` | every session, first — router + 7 operating rules |
| `routine-authoring` | writing/parsing markdown routines, schedules, review checklist |
| `sentinel-gate` | any outbound call, secret, spend, delete, message |
| `postmortem` | any failure; before any new venture |
| `venture-launch` | new business, pricing, P&L, kill criteria |
| `agent-delegation` | writing a work order for Claude Code or `muse` |
| `upstream-merge` | editing `repos/` or taking an upstream release |
| `ship-it` | deploy, migrate, monitor, run unattended |

Inherited from upstream and reused as-is: OpenBot's `openbot-copy` (the words a person reads),
`openbot-data-access`, `openbot-screen-layout`; Rakazo's `release`, `pr-watch`, `ux-declutter`,
`translate`, `composio` (pinned by hash in `skills-lock.json`).
The PDF's "skill of prompt engineering" is `agent-delegation` — a work order with an acceptance
test beats a "better prompt".

**Rule:** an agent that has to guess which rules apply will invent its own, and its own rules will
be wrong. Name the skill in the order.

---

## 10. The 365-day plan

Each phase ends with **exit criteria**, not a date. If criteria fail, the phase repeats — the calendar
is a forecast, not a promise.

### Phase 0 — M0 (done, day 0)
Install everything, verify, and put governance in place before features.
**Exit:** ✅ installs verified · ✅ Sentinel engine + 52 tests + running service · ✅ ledger + CI
checker · ✅ 8 skills · ✅ decisions + install logs.

### Phase 1 — M1 (weeks 1–4): **the unattended skeleton**
Build P5 (done), P13, P3, P1, P2, P4. Nothing customer-facing. The goal is: *a routine fires at
6 a.m., is audited as `initiator=routine`, asks permission for anything dangerous, and lands in a
channel — with nobody at the keyboard.*
**Exit criteria:** 7 consecutive days of scheduled routines with zero manual intervention; every
outbound action has an audit row; a deliberate spend attempt is blocked and requires a click; a
cross-venture read attempt is denied *and* flagged; `check.sh` green in CI.

### Phase 2 — M2 (weeks 5–10): **the first venture, end to end**
P14 (ledger + webhooks), P12 (scout), P15 (deploy), **Venture 01: Media API** — one endpoint, one
price, live, with status page, tests, health check, and a human-approved price.
**Exit:** a stranger can pay; the row lands in the ledger from the webhook; a refund was exercised
in test mode; a 250MB file is processed without the `/tmp` failure class; the deploy rolled back
once, on purpose, successfully.

### Phase 3 — M3 (weeks 11–20): **reliability and the second engine**
P17 (ops console), dead-man's switch, restore drill, P11 (evals), L2 verification loop. Venture 02
(the PDF's "dynamic UI generator" is fine **if** it has an ICP and a price; otherwise pick from the
scout feed). First outside user of the *service* path (path B) if that's the funding route.
**Exit:** 30 days without a sev1/sev2 incident; monthly review auto-generated; a model/prompt change
promoted through evals with a canary.

### Phase 4 — M4 (weeks 21–36): **scale what works, kill what doesn't**
P6 (teach-by-demonstration), P7 (delegation), P16 (skill lab), P8 (Pages). Scaling triggers: a
venture past its profit margin gets a duplicated stack, a second channel, and a budget increase —
approved by a human the first three times, then by rule.
**Exit:** ≥$5k MRR or a written, evidence-based decision to pivot; agent cost per venture known to
the dollar; two channels live on the best venture.

### Phase 5 — M5 (weeks 37–52): **hand it over**
The leave-for-a-year phase. Narrow the human's job to: approve prices, approve legal text, read the
monthly review. Everything else runs. Quarterly re-drills: restore, rollback, key rotation, canary.
**Exit (the real one):** you leave for **30 days** as a dress rehearsal, with a single read-only
dashboard, and come back to a company that (a) made money, (b) filed its own incidents and fixed
them, (c) did nothing you would not have approved.

> **Partner's note:** do the 30-day dress rehearsal at the *end of Phase 3*, not Phase 5. You will
> learn more from 30 days away at $1k MRR than at $10k MRR. If you can't leave at Phase 3, the
> problem is architectural, and more features will not fix it.

---

## 11. Immediate next 14 days (concrete)

| Day | Work | Owner | Done when |
|---|---|---|---|
| 1 | **B1–B7 in `BLOCKERS.md`**: Docker host, toolchain, repos with history, Intelligence project, one model key, generated secrets, `scripts/start.sh` | you | `app:3010` and `server:3001` respond; a Bot lists files on its computer |
| 1 | `git init` each repo, add upstream remotes, tag the pinned commit (`upstream-merge`) | agent | `scripts/os-markers.sh` runs |
| 2 | Move Sentinel audit + approvals from memory to Postgres (append-only, one unique index on idempotency) | agent | tests still green + a restart keeps rows |
| 2 | `scripts/pause-all.sh` + budget enforcement read from `.openbot/state/budget.json` | agent | one command pauses everything |
| 3–4 | P13 Venture SDK: pydantic manifest, `validate`, `media-api` passes, a bad manifest fails loudly | agent | `venture_sdk` tests green |
| 5–6 | P1 routine parser (`spec.py`) + vault watcher + `dry_run.py`; `scout-daily.md` parses | agent | dry run prints plan + cost |
| 7 | Wire OpenBot server gateway → Sentinel `decide()` (adapter, ~200 lines) | agent | a gated send in OpenBot appears in `/v1/approvals` |
| 8–9 | P2 approvals UI in OpenBot `app` (list, action, approve/deny, resume) | agent | a blocked run resumes on click |
| 10 | P4 per-venture isolation checks + adversarial tests (cross-venture read, metadata IP, secret in body) | agent | all three denied + sev1 rows |
| 11 | End-to-end unattended day: routines fire, audit, gate, report | you watch | 24h with no manual step |
| 12 | Post-mortems from that day → rules → ledger (`postmortem` skill) | agent | `check.sh` green, ≥1 new rule |
| 13 | Weekly review doc v1 auto-generated from rows | agent | one page, numbers only |
| 14 | Decision: go/no-go to Phase 2 with Venture 01 | **you** | written, in this repo |

---

## 12. Metrics (what we look at weekly, and nothing else)

**Leading (this week):** routines fired vs scheduled (%) · gated actions approved/denied · incidents
by class · open post-mortems without a rule · agent spend per venture · deploy rollbacks.
**Lagging (monthly):** MRR from ledger rows · gross margin · CAC payback · churn · cost per
customer-response · days since last manual intervention.

Targets: >99% routine success · 0 gated actions executed without an approval row · 0 post-mortems
without an enforced rule · agent spend < 15% of revenue by month 6 · **manual interventions per week
trending to 0**.

---

## 13. Risk register

| Risk | Likelihood | Impact | Mitigation (already partly built) | Early warning |
|---|---|---|---|---|
| Silent failure while you're away | high | fatal to trust | dead-man's switch, auto-pause on sev1, health routines | a missed routine alert |
| Runaway spend | medium | high | `auto_spend_usd=0`, day/month caps, gate on money | any `cost_usd>0` audit row |
| Key leak via agent | medium | high | scrub+escalate, protected paths, TTL aliases, rotation routine | a scrubbed-secret audit row |
| Prompt drift / model regression | high | medium | evals + canary + no self-editing prompts | falling eval pass rate |
| Upstream churn makes merges painful | high | medium | seam rules, markers, monthly single-upstream bump | marker count growth |
| Legal/ToS: agents acting as you on third-party sites | medium | high | gated sends, no fake accounts, read-only first, human approval for terms | a vendor complaint |
| Building the conglomerate before one venture pays | **very high** | fatal | Phase gates; one venture at a time (D7) | two ventures in `discovery` at once |
| The human becomes the bottleneck | high | medium | approval UX, batched digests, "approve all read-only" | approvals pending > 24h |
| Cold-start traffic: nobody finds the product | very high | high | channel-first: pick channel before code (step 4 of launch path) | zero visits in week 2 |

---

## 14. Decisions — answered 2026-11-10

| # | Question | Answer | What it locks in |
|---|---|---|---|
| 1 | Substrate | **OpenBot is the host** | Rakazo/OpenDots read-only reference; every feature lands as plugin / AG-UI bot / app route / `services/` |
| 2 | First venture | **Media API** | ffmpeg pipeline + the `/tmp` prevention test are on the critical path |
| 3 | Hosting | **Own VPS with Docker** | compose stack; backups, restore drill, dead-man's switch and firewall are ours (no Kubernetes, no managed Postgres) |
| 4 | Accounts | **None yet** | nothing model-driven runs until the chain in `BLOCKERS.md` is green |

Still open, and only you can close them: **entity + bank** (needed for live payments, not for test
mode) and **which model provider you want as the default tier** once you pick one.
The full blocker list with exact commands is `BLOCKERS.md`.

---

## 15. Definition of done (applies to every task in this repo)

- [ ] The order named a test; the test exists and is green.
- [ ] Any outward action has a policy rule and an audit row.
- [ ] Any failure has a ledger entry with an enforced `rule_kind` (not a prompt, if code can do it).
- [ ] Upstream edits are marked `OPENBOT-OS:` and listed in `patches/OPENBOT-OS.md`.
- [ ] User-facing words pass `openbot-copy`.
- [ ] Budget and blast radius are stated in the PR body, in dollars and in "who could be hurt".

---

## Appendix A — file map

```text
plan.md                          this document
STACK_DECISIONS.md               decisions D1–D9 + your confirmations C1–C4 (append-only)
BLOCKERS.md                      B1–B10: what to do, in order, to get from here to running 24/7
aboutme.md                       the employee profile: what I am, what I cost, how to manage me
advantages.md                    the positive case, each claim with a mechanism and a measurement
disadvantages.md                 the negative case: hard limits, legal walls, per-industry verdicts
FEATURES.md                      reverse-engineering sheet: Rakazo/OpenDots/Grok/Muse → ours, with build order
company/company.yaml             the org: 6 roles, mandates, prohibitions, duties, cost ceilings
services/sentinel/company.py     loads the org and refuses an inoperable one (15 tests)
scripts/verify.sh                the go/no-go gate: 17 checks, FAIL → not go
scripts/pause-all.sh             one-command kill switch, writes a sev1 audit row
scripts/restore-media.sh         re-fetch the 77 large upstream media files trimmed for the snapshot
INSTALL_LOG.md                   what was installed, verified, and the caveats
repos/OpenBot                    substrate
repos/rakazo                     feature donor
repos/OpenDots                   review-gate donor
services/sentinel/               FastAPI: policy.py, app.py, policy/*.yaml, tests/ (37 green)
.claude/skills/                  8 skills + README index + postmortem/check.sh
.openbot/routines/scout-daily.md the first real routine (markdown-first, budgeted, gated)
.openbot/ventures/media-api/     the first venture manifest
.openbot/post_mortems/           error_registry.jsonl (append-only ledger)
.openbot/state/                  budget.json, upstream.json, active_ventures.yaml
scripts/session-start.sh         the 10-second state check at session start
scripts/muse-order.sh            run a work order through muse, keep events.jsonl + redacted trace
scripts/os-markers.sh            marker <-> patches/OPENBOT-OS.md cross-check (CI)
examples/order-add-health-check.md   a real, well-formed work order (smoke-tested with --provider echo)
patches/OPENBOT-OS.md            every edit we make inside repos/, and why
tools/README.md                  re-create Node 24 / Bun / pnpm / muse on a fresh box
```

## Appendix B — commands

```sh
bash scripts/session-start.sh                       # what state am I in
bash .claude/skills/postmortem/check.sh             # ledger integrity (put this in CI)
cd services/sentinel && python3 -m pytest -q        # 52 tests
cd services/sentinel && uvicorn app:app --port 8090 # the gate, running
curl -sX POST localhost:8090/v1/decide -H 'content-type: application/json' \
  -d '{"kind":"mcp.call","venture":"media-api","initiator":"routine","name":"gmail.send_message"}'
~/.local/bin/muse --version                         # Muse Code 1.4.14
cd repos/OpenDots  && npm run typecheck             # green
cd repos/OpenBot   && bun test                      # needs Docker for the full suite
cd repos/rakazo    && pnpm turbo run typecheck      # needs Node 24
```
