# FEATURES.md — the reverse-engineering sheet

Every capability worth taking from Rakazo, Grok Bot, OpenAI Dots and Meta Muse, what we already have,
who owns the port, and — importantly — the things **none of them have** that a real company needs.
Effort is agent-days for a competent coding agent with a precise order (`skills/agent-delegation`).

Source verification: `[verified]` means I read the mechanism in the cloned source or its docs on
2026-11-10 (path given). `[reported]` means it comes from public product documentation and could not
be checked in code, because the product is closed.

---

## 1. Rakazo (feature donor) — verified in `repos/rakazo`

| # | Feature | Where it lives | We take | Effort | Owner |
|---|---|---|---|---|---|
| R1 | Markdown-first routines | `packages/db/.../routine_*` migrations, `docs/routines.md` `[verified]` | the *authoring ergonomics* (our parser is already spec'd) | 0 (pattern) | CTO |
| R2 | Routine reliability features: multi-schedule, webhook trigger, watch mode, per-account failure tracking | migrations `routine_multi_schedule_and_run_routine_id`, `routine_webhook_enabled`, `routine_watch`, `routine_account_failures` `[verified]` | **webhook-triggered routines** and **watch mode** — big: turns routines from cron into event-driven | 4 | CTO |
| R3 | Ticket board (To do → In progress → Review → Blocked → Done/Won't do), assign to a bot, bot posts a card when it needs a human | `docs/board.md` `[verified]` | the whole board — it is the work queue our roles need | 5 | CTO |
| R4 | Messaging apps: Slack, Telegram, WhatsApp, iMessage, SMS, Feishu; voice notes transcribed | `docs/messaging-apps.md` `[verified]` | **Telegram + WhatsApp** first (India), transcribed voice notes | 6 | Growth |
| R5 | Memory (per-bot, persisted) | `packages/memory/src` `[verified]` | conceptually already in OpenBot (Intelligence memory); no port needed | 0 | — |
| R6 | Skills library with GitHub import and a pinned external skill | `docs/skills.md`, `skills-lock.json` `[verified]` | the **catalog + import** UX so a learned skill is reviewable | 3 | CTO |
| R7 | Pages (shareable dashboards/docs by link) | `docs/pages.md` `[verified]` | yes — our reviews and status pages need it | 5 | Growth |
| R8 | Group chats + delegation between bots | `docs/groups.md` `[verified]` | yes, with our rule that a hop carries the original person's authority | 8 | CTO |
| R9 | Voice chat/calls; mobile & desktop clients | `apps/mobile`, `apps/desktop`, `modules/rakazo-voice-chat` `[verified]` | calls later; clients = use OpenBot's desktop build (don't port) | 12 / 2 | — |
| R10 | Self-host: docker computers, remote sandbox providers (e2b, daytona, boat, boxd, railway), backups, observability, restricted networks | `docs/self-host-*.md` `[verified]` | the **backup + observability** checklists feed our `ship-it` skill | 0 (pattern) | Ops |

## 2. Grok Bot (closed product — benchmark only) `[reported]`

| # | Feature | What it is | Our answer | Effort |
|---|---|---|---|---|
| G1 | Teach-a-task by doing it once | Record a human performing a workflow; the bot saves it as a reusable routine | **Do it, but better**: OpenBot already ships a recorder — `extension/` (a browser extension with masking), `shared/demonstration-rules.ts` (sensitive-field detection: password/OTP/card), `shared/recorder-masking.ts`, `server/src/db/schema/demonstrations.ts` `[verified]`. Our addition: a recording may never capture a *secret field*, and a learned routine enters `deny_all` egress until reviewed. | 6 |
| G2 | One persistent computer per teammate, logins survive | Persistent Linux VM per bot | already OpenBot's supervisor: one container per person/bot, own Chromium, own profile, own token (`docs/architecture.md`) `[verified]` | 0 |
| G3 | Works when your laptop is closed | cloud-side execution | yes by construction | 0 |
| G4 | Multi-bot coordination in group chats | bots in a group, @mention | R8 | (shared) |
| G5 | Works in any app via browser, no API needed | computer use | already OpenBot's computer + browser tools `[verified]` | 0 |

## 3. OpenAI Dots / OpenDots (review-gate donor) — verified in `repos/OpenDots`

| # | Feature | Where it lives | We take | Effort |
|---|---|---|---|---|
| D1 | **Approve & save / Decline** card that pauses the run, then resumes on your decision; a changed draft needs a new review; a retry recovers the same saved object | `src/server/runner.ts`, `src/client/TaskActions.tsx`, `src/server/page-tools.ts` `[verified]` | the **review-before-save** pattern for anything a customer sees, with idempotent retries | 3 |
| D2 | Per-tool permission toggles: read-only tools run on their own, everything else pauses for **Approve & run** | `src/server/connection-tools.ts`, `docs/CONNECTIONS.md` `[verified]` | yes — this is the UX our approvals queue was missing | 3 |
| D3 | Spaces + page tree + editor with autosave, draft recovery, revision checks | `src/server/page-service.ts`, docs `[verified]` | the page library our reviews/reports live in (overlaps R7, pick one backend) | (shared) |
| D4 | Connections: any MCP server, Composio connected apps with per-toolkit scoping and a stable `OWNER_ID` | `src/server/composio*.ts` `[verified]` | yes — the app catalogue our Growth role needs | 4 |
| D5 | Slack channel with explicit workspace/user allowlist | `src/server/slack-channel.ts` `[verified]` | yes, with the allowlist (we do not answer strangers) | 2 |
| D6 | Calls: realtime speech paired with a separate compute agent, shared context | `src/server/voice.ts` `[verified]` | later (M4) | 10 |
| D7 | Honest setup states: unconfigured services show a setup card, never fake success | `README`, `docs/SETUP.md` `[verified]` | copy this posture into every one of our screens | 1 |

## 4. Meta Muse Code (coding labour) — verified on this machine, `muse` 1.4.14

| # | Feature | Evidence | We take | Effort |
|---|---|---|---|---|
| M1 | Headless `muse exec` with JSONL events | `muse exec --help` `[verified]` | `scripts/muse-order.sh` — already wraps it, keeps `events.jsonl` + `meta.json` | 0 (done) |
| M2 | Replayable trace export | `muse export --last --redacted --out …` `[verified]` | the evidence artefact attached to every agent PR and every L3 skill promotion | 1 |
| M3 | Multi-agent by default in isolated git worktrees | product docs `[reported]`, consistent with the CLI surface | our delegation patterns (one worktree per feature) | 0 |
| M4 | Skills auto-import from Claude Code | `muse skills list` showed our 8 skills as user skills `[verified]` | write a skill once, both harnesses obey it | 0 |
| M5 | `side_effect_intent` with a `policy_decision` field in the event log | run trace `[verified]` | **copy that field into our audit row** instead of re-deriving why something was allowed | 2 |
| M6 | Fails closed without an OS sandbox (Bubblewrap) | warning on this host `[verified]` | pre-flight check in `verify.sh` before any unattended order | 0 (done) |

---

## 5. What none of the four have — our actual product

| # | Missing feature | Why a real company dies without it | Where it lands |
|---|---|---|---|
| N1 | **Venture as a validated object** (thesis, ICP, pricing, unit economics, budgets, kill criteria) | Without it, "autonomous company" is a pile of tasks | `packages/venture-sdk` |
| N2 | **P&L ledger fed by provider webhooks**, idempotent, reconciled to the cent | An agent that "reports" revenue is a liability | `services/ledger` |
| N3 | **Kill criteria that fire automatically** (auto-pause), with a human signature to resume | Otherwise every dead venture keeps spending | worker + Sentinel |
| N4 | **Prevention rules enforced in CI** (not a lessons-learned doc) | The only mechanism that makes the company improve | shipped |
| N5 | **Org definition that refuses to boot if it is unsafe** (agent at root, no prohibitions, unbudgeted duty) | An org chart that cannot veto itself is fiction | shipped (`company.py`, 15 tests) |
| N6 | **Role cost ceilings tied to company caps**, so agent spend cannot outrun revenue | Cost is the second-fastest way to die | shipped |
| N7 | **A dress-rehearsal contract**: leave 30 days at $1k MRR, not at $10k | You learn more about what is missing at low stakes | plan.md §10 |
| N8 | **Gate-starvation detection**: the company tells you it is blocked, not busy | The #1 real-world failure of human-in-the-loop systems | worker (M1) |

---

## 6. Build order (what to do next, in this order)

1. **N2/N1** — venture SDK + ledger (without numbers, nothing else can be judged).
2. **D2 + D1** — per-tool approval toggles and the review card (this is what makes daily operation pleasant enough that you keep clearing the queue).
3. **R2 + R3** — webhook-triggered routines and the ticket board (work stops arriving by cron only).
4. **R4** — Telegram/WhatsApp in, so customers reach the company where they already are.
5. **G1** — teach-a-task with our masking rule, in `deny_all` until reviewed.
6. **R7/D3 + R8** — pages, then multi-bot delegation.
7. Everything else (calls, mobile, learning loops) after the first venture pays.
