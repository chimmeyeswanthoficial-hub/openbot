# OpenBot OS

**A self-hosted company you can audit: five agent roles, one human owner, and a control plane that
refuses unsafe work before any model is involved.**

```sh
git clone <this repo> openbot-os && cd openbot-os
python3 -m venv .venv && . .venv/bin/activate
make install && make demo
# → http://127.0.0.1:8090   the control room, with real rows, no API keys
```

No Docker. No model key. No cloud account. If that demo does not come up, that is a bug, and it is
the most important bug in the project.

---

## The idea in one screen

Most "autonomous company" projects are a chatbot with a to-do list. They fail for one reason: when
the model is wrong, nothing stands between the mistake and the world.

OpenBot OS puts that thing between. **Every outward action** — an HTTP call, a file write, a message,
a spend, a deploy — is resolved, judged, recorded, and only then performed. The judgement ladder is
short enough to read in one sitting:

```
1 safety   money · credentials · delete · send · publish · share      → always a human
2 policy   egress allowlist · venture isolation · protected paths    → deny or allow
3 budget   this run · this venture today · the company this month    → gate or deny
4 default  read-only, in-bounds, in-budget                           → allow
```

A blocked action does not poll and does not continue. It becomes a row in **Waiting for you**, and
an approval can be resolved exactly once.

That is the whole architecture. Everything else — routines, ventures, the ledger, incidents — is
built on it.

## What is in the box today

| Piece | What it does | Status |
|---|---|---|
| **Control room** (`/`) | One page: roles, duties, prohibitions, money, the approval queue, routines, audit trail, runs, incidents | runs |
| **Sentinel** (`services/sentinel`) | `POST /v1/decide` judges an action; `/v1/approvals` is the human queue; `/v1/audit` is append-only | 88 tests |
| **Ledger** (`services/ledger`) | Money derived from rows only: net revenue, margin, contribution, agent share, reconciliation | 10 tests |
| **Contract tests** | Docs, console and changelog must agree with the code, and `docs/` must not go stale | 12 checks |
| **Worker** (`services/worker`) | Markdown routines → validated runs; refuses paused ventures, un-budgeted runs, unknown routines | 47 tests |
| **Venture SDK** (`packages/venture-sdk`) | A business is a validated object: plans, measured COGS, budgets, kill criteria — an unworkable venture cannot start | 20 tests |
| **Company** (`company/company.yaml`) | Roles, mandates, prohibitions, duties, cost ceilings — validated at boot; an unsafe org cannot load | 15 tests |
| **Skills** (`.claude/skills`) | The operating manual: 9 skills both Claude Code and Muse Code load | — |

`make smoke` proves it end to end on a throwaway database: seed → arithmetic → gates → exactly-once
approval → console renders. `make release-check` runs verify + test + smoke together, and pasting its
output into a release note is the only way a version gets tagged.

## Running it where other people can reach it

The console is safe to publish because it renders only what the server computed and escapes every
value. But **an unauthenticated console on a public address lets anyone approve a pending action** —
so the moment it leaves localhost, set a token:

```sh
export SENTINEL_UI_TOKEN=$(python3 -c "import secrets;print(secrets.token_urlsafe(32))")
make run                       # approvals + ledger writes now require X-OpenBot-Token
# behind Caddy/nginx with TLS; the console asks for the token once and keeps it for the tab
```

Put it behind a reverse proxy with TLS, bind it to the loopback interface, and keep Postgres, the
OpenBot server, the computer service and the supervisor off the public internet entirely
(`plan.md` §4 lists the ports). `$SENTINEL_DB` points at a file for persistence; the default is an
in-memory store that vanishes on restart, which is right for a demo and wrong for a company.

## The honest part

This is a **dozen people's work reduced to a week of work**, which means it is early. Read
[`aboutme.md`](aboutme.md) for what it can do (tagged `[shipped]`, `[M1–M3]`, `[human]`, `[never]`)
and [`disadvantages.md`](disadvantages.md) for what it must never do — including the per-industry
verdicts and the legal walls.

The three things that are missing and matter most:

1. **The substrate is not wired yet.** Routine dispatch is implemented and tested; OpenBot's Bot
   still has to be connected to it over AG-UI (M1). `make demo` shows *governance working*, not a
   Bot answering you.
2. **No accounts.** No model key, no CopilotKit Intelligence project, no payment provider — so no
   conversations, and no real revenue can settle. See [`BLOCKERS.md`](BLOCKERS.md).
3. **Docker is not available in the dev sandbox** where this was built, so OpenBot's per-bot
   computers have not been started here (install + typecheck were verified).

Nothing in this repo pretends otherwise. Any number on the console traces to a stored row; the demo
seeds replayable provider events, including one replay that is correctly ignored.

## Documentation map

| If you want to… | Read |
|---|---|
| understand the plan, phases and the 365-day path | [`plan.md`](plan.md) |
| know what the system is, in the voice of an employee | [`aboutme.md`](aboutme.md) |
| know the case for it, with measurements | [`advantages.md`](advantages.md) |
| know where it fails, by industry | [`disadvantages.md`](disadvantages.md) |
| see what we take from Rakazo / OpenDots / Grok / Muse | [`FEATURES.md`](FEATURES.md) |
| get it running on a real box | [`BLOCKERS.md`](BLOCKERS.md) · [`INSTALL_LOG.md`](INSTALL_LOG.md) |
| know why a choice was made | [`STACK_DECISIONS.md`](STACK_DECISIONS.md) |
| contribute | [`CONTRIBUTING.md`](CONTRIBUTING.md) |
| see what is next, in order | [`ROADMAP.md`](ROADMAP.md) |
| take over the project: what exists, measured | [`PROJECT_STATE.md`](PROJECT_STATE.md) |
| take over the project: what to build next, with acceptance checks | [`PROJECT_REMAINING.md`](PROJECT_REMAINING.md) |
| take over the project: how the previous owner thought, and what they expect | [`PROJECT_BRAIN.md`](PROJECT_BRAIN.md) *(kept in the repo root, not published — it is a note to the next engineer, not marketing)* |

## How it is kept honest

```sh
make test        # every test in the repo
make smoke       # end-to-end on a clean database
make verify      # the go/no-go gate; it is allowed to say NOT GO
make release-check   # all three
```

`make verify` fails the build when: a capability doc claims something no test covers, a routine has
no budget, the org chart is inoperable, an incident has no enforced prevention rule, or the workspace
exceeds its size budget. A project that cannot fail its own checks is a demo.

## Licence

MIT for this repository. The substrate ([OpenBot](https://github.com/CopilotKit/OpenBot)) and the
donors ([Rakazo](https://github.com/elie222/rakazo),
[OpenDots](https://github.com/CopilotKit/OpenDots)) carry their own licences; CopilotKit Intelligence
is separately licensed and is not included here.
