# Stack decisions

Append-only. Each entry: the decision, the date, the reason, and what would change our mind.
Nothing here is re-litigated without a new entry.

---

## D1 — OpenBot is the substrate; Rakazo and OpenDots are donors
**2026-11-10.** OpenBot already ships the four things that are expensive to build and dangerous to
improvise: an action-policy gateway with CEL rules and audit rows, per-bot computer containers via a
supervisor, a routines worker, and an approvals engine with a documented, tested safety ladder. It is
MIT, TypeScript, and structured as `agent-*` pieces so an outside agent can be plugged in over AG-UI.
**Would change our mind:** if OpenBot's licence or its dependency on CopilotKit Intelligence (separately
licensed) becomes unacceptable for the business model. Rakazo is the fallback host: more features out
of the box, but we would rebuild governance.

## D2 — Our code is a thin coat: `services/`, `packages/`, plugin seams, marked patches
**2026-11-10.** Three fast-moving upstreams plus a year unattended means we must be able to re-pull.
Every edit inside `repos/` carries an `OPENBOT-OS:` marker with a one-line why, and an entry in
`patches/OPENBOT-OS.md`; `scripts/os-markers.sh` will fail CI when the two disagree.
**Would change our mind:** never, short of an upstream going dormant or hostile.

## D3 — Policy is code, not prose
**2026-11-10.** `services/sentinel/policy.py` is a pure function: safety → policy → budget →
unattended-PII → default, first match wins, fail closed. Prompts are suggestions; a tested regex and
an allowlist are boundaries. Vocabulary deliberately mirrors OpenBot's `docs/approvals.md` so one
reviewer can read both.
**Would change our mind:** nothing known.

## D4 — Money is human-gated until revenue exists
**2026-11-10.** Every venture starts `auto_spend_usd: 0.00`; any `cost_usd > 0` becomes a `gate`.
Company caps live in `.openbot/state/budget.json` (day $20 / month $300 to start) and are raised only
by a human in a PR with a reason.
**Would change our mind:** after a venture has 3 months of settled revenue, raise its auto-spend to a
measured fraction of gross margin — in a PR, once.

## D5 — Revenue is read from webhook rows, never from agent claims
**2026-11-10.** `venture_ledger` has a unique index on `idempotency_key` (the provider event id), so a
replayed webhook cannot double-count. MRR is a nightly computation from rows, written to
`.openbot/state/pnl.json`, which the dashboard reads. Trials are `pipeline`, never revenue.
**Would change our mind:** nothing.

## D6 — Python for the Sentinel, worker and ventures; TypeScript for the product
**2026-11-10.** The PDF asks for FastAPI; the repos are TypeScript. Splitting by concern gets both: the
governance and business logic is Python (fast to write, easy to test, good media/AI libraries), the
product surface stays in the substrate's TS so we inherit its components, approvals UI and AG-UI
streaming. The contract between them is three HTTP endpoints.
**Would change our mind:** if the OpenBot gateway needs sub-10ms in-process policy checks — then port
`policy.py` to TS behind the same test suite, keeping Python as the reference.

## D7 — One venture until the first one pays
**2026-11-10.** The PDF's multi-company vision is the reward for focus, not a substitute for it. A
second venture in `discovery` is allowed only after the first has a settled payment.
**Would change our mind:** if a venture is killed by its own kill criteria — then start the next one
with the post-mortem rules attached.

## D8 — Toolchain pins (and why this box needed its own)
**2026-11-10.** Rakazo requires Node ≥24.15 (`^24.15 || >=26`) and pnpm 12.18.0; OpenBot requires Bun
1.4+; OpenDots requires Node 24 with npm. The sandbox shipped Node 20 only, and `npm i -g` cannot write
to `/usr/lib`, so a portable toolchain lives in `tools/` (`node24/`, `bun-linux-x64/`, `bin/pnpm`).
**Would change our mind:** on your own machine, install Node 24 via fnm/nvm and Bun normally; keep the
pins in `.openbot/state/upstream.json` and in a `.tool-versions` file.

## D9 — Muse Code is coding labour, not a runtime dependency
**2026-11-10.** `muse` (Meta Muse Code, v1.4.14) is the second agent CLI beside Claude Code. Its
**append-only local event log** is the reason it matters to us: it is a replayable trace, which is
exactly what L2 (verification) and L3 (skill acquisition) need. It is closed source and needs a Meta
Model API account, so no production path may *require* it.
**Would change our mind:** if Meta ships an SDK we can call headlessly in CI with predictable pricing.

---

## Confirmed by the owner — 2026-11-10

Four questions in `plan.md` §14 were answered. These are now constraints, not options.

### C1 — Substrate: **OpenBot is the host** (confirms D1)
Rakazo and OpenDots stay donors. Consequence: every feature in §5 lands as a plugin, an AG-UI bot, an
OpenBot app route, or a `services/` HTTP service. Nothing is added to `repos/rakazo` or
`repos/OpenDots`; they are read-only reference from here.

### C2 — First venture: **Media API** (confirms §7.3 path A, with path B as a possible funder)
The manifest is `discovery`; it becomes `build` only when §11 day-14 says go. Consequence: the media
pipeline (ffmpeg split/convert/compress) is the *first* thing customers touch, so the post-mortem class
"never write intermediate media to /tmp" must be a test before the first endpoint ships.

### C3 — Infrastructure: **own VPS with Docker** (a Hetzner-class box)
Consequence: compose stack, no Kubernetes, no managed Postgres. Backups, restore drills, the
dead-man's switch and the firewall are ours to own — that is `ship-it`, and it is now on the critical
path, not a later nicety. Budget line for infra goes in the ledger as `cogs` from day one.

### C4 — No model or payment accounts yet
Consequence: **nothing model-driven can run today**, and no revenue can land. The blocker list is
`BLOCKERS.md`. The correct order is: VPS + Docker → Intelligence project + one model key → OpenBot
boots → routines fire. Do not build venture features before this chain is green, because every
"works on my laptop" fix will need re-verification on the box anyway.
**Also:** no Stripe account means the first venture's checkout cannot be tested end to end. Stripe
test mode needs no entity; live mode needs one. Start in test mode as soon as the account exists.
