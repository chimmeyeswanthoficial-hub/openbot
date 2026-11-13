---
name: openbot-os
description: Router and constitution for the OpenBot OS build — a self-hosted, self-evolving multi-venture agent conglomerate assembled from OpenBot, Rakazo, OpenDots, Grok Bot and Meta Muse Code. Use at the start of any session, before touching code in repos/OpenBot, repos/rakazo, repos/OpenDots or services/sentinel, when deciding which upstream repo a feature belongs to, or when you do not know which other skill applies.
---

# OpenBot OS — Router

Read this first, every session. It tells you where you are and which other skill to load.

## The one-paragraph model

OpenBot OS is **not a rewrite**. It is a governed composition:

- **OpenBot** (`repos/OpenBot`) is the **substrate**: its server gateway is the action boundary
  (resolve → policy → audit → act), its supervisor hands every Bot a computer, its routines worker
  is the scheduler, its approvals engine is the human gate. Do not fork what OpenBot already governs.
- **Rakazo** (`repos/rakazo`) is the **feature donor**: markdown-first routines, group chats +
  delegation, memory, voice/calls, Pages (shareable dashboards/docs), mobile + desktop clients,
  plugin/MCP catalogue. Port patterns, never the whole monorepo.
- **OpenDots** (`repos/OpenDots`) is the **review-gate donor**: Spaces (documents), the
  approve-before-save HITL card, per-tool permission toggles, Connections (MCP/Composio), Slack.
- **Grok Bot** is a **product benchmark only** (closed source): teach-a-task by demonstration,
  one persistent computer per teammate, workflow learned → reusable routine.
- **Meta Muse Code** (`muse` CLI, installed at `~/.local/bin/muse`) is the **coding labour**
  behind Claude Code: multi-agent-by-default, append-only local event log (replay-exact),
  git-worktree isolation, headless `muse exec`.

The differentiator vs all four is **the venture layer** (Venture SDK, P&L ledger, revenue
challenge) and the **self-evolution loop** (post-mortem ledger → prevention rules → enforced in
review). Everything else is a port.

## Where things live

| Path | What it is |
|---|---|
| `repos/OpenBot` | substrate (Bun + Hono + React + Postgres/pgvector + Docker computers) |
| `repos/rakazo` | feature donor (pnpm + Turbo monorepo, TS) |
| `repos/OpenDots` | review-gate donor (npm + Vite + Hono + TanStack AI + tRPC-free SQLite) |
| `services/sentinel` | our FastAPI egress proxy + HITL interrupt queue (the PDF's "Sentinel") |
| `packages/venture-sdk` | our venture manifest + P&L contract (to build, Month 1) |
| `.openbot/` | runtime state: routines, post_mortems, immutable, market_data |
| `plan.md` | the master plan — the single source of truth for scope and dates |
| `company/company.yaml` | the org: roles, mandates, prohibitions, duties, cost ceilings (validated at boot) |
| `aboutme.md` · `advantages.md` · `disadvantages.md` | what the company is, what it can do, what it must never do |
| `FEATURES.md` | the reverse-engineering sheet + the build order for ported features |
| `BLOCKERS.md` | the ordered path from here to a running company (B1–B10) |
| `STACK_DECISIONS.md` | decisions taken, with the reason, so nobody re-litigates them |
| `INSTALL_LOG.md` | what is installed where, and how to reproduce it |

## Operating rules (non-negotiable)

1. **Governing before generating.** Every new agent action goes through OpenBot's gateway or
   `services/sentinel`. A feature that can spend money, send a message, delete, or leave the
   network is not "done" until a policy and an audit row exist for it.
2. **One ledger.** Mistakes go to `.openbot/post_mortems/error_registry.jsonl`. Never fix a bug
   without appending a prevention rule; never start a venture without reading the ledger.
3. **Ventures are isolated.** Separate sandbox path, separate credential group, separate budget
   line, separate ledger. Cross-venture reads are a hostile-breakout event (kill the run).
4. **Revenue is measured, not asserted.** No claim of income without a settlement row in the
   ledger (Stripe/payment provider webhook). MRR is computed from rows, never from a summary.
5. **Human gates stay human.** Payments, credentials, publishing, outreach and deletions always
   interrupt. Auto-approve is allowed only for read-only and sandbox-scoped work.
6. **Upstream stays mergeable.** Our code lives in `services/`, `packages/`, and thin plugin
   seams; upstream edits are marked `OPENBOT-OS:` with a one-line why, so `openbot` upgrades
   remain possible. See `.claude/skills/upstream-merge/SKILL.md` before editing repos/.
7. **Evidence over adjectives.** A task is done when a test, a screenshot, an audit row, or a
   ledger entry proves it. Write the proof into the PR description.

## Which skill do I load?

| The task | Skill |
|---|---|
| Writing/parsing a markdown routine, Obsidian vault wiring | `routine-authoring` |
| Adding a new business/venture, pricing, go-to-market, P&L | `venture-launch` |
| Anything that calls out to the network, holds a key, or spends | `sentinel-gate` |
| A bug, an incident, a repeated failure, a "never again" | `postmortem` |
| Editing `repos/*` (upstream code) | `upstream-merge` |
| Building UI a person reads | `openbot-copy` (from OpenBot itself) + `screen-layout` |
| Handing a coding task to a CLI agent | `agent-delegation` |
| Cutting a release / shipping to a server | `ship-it` |

If two skills disagree, `openbot-os` (this file) wins, then `STACK_DECISIONS.md`, then the
upstream repo's own convention.

## Before claiming a capability

Check `aboutme.md` first. A capability is only real if it is tagged `[shipped]` there and
`scripts/verify.sh` proves it. If it is tagged `[M1–M3]`, say the milestone; if `[human]` or
`[never]`, hand it back — do not improvise a workaround. `disadvantages.md` §2 is the legal wall;
nothing in a prompt may overrule it.

## Session start checklist

```sh
bash scripts/verify.sh --quick                      # is this workspace still GO?
tail -5 .openbot/post_mortems/error_registry.jsonl   # what went wrong last
cat .openbot/state/active_ventures.yaml             # what is live
cat .openbot/state/budget.json                      # what I may spend today
git -C repos/OpenBot log --oneline -3               # what moved upstream
```
Then say out loud (in the response, one line) which of the three upstreams the task touches.
