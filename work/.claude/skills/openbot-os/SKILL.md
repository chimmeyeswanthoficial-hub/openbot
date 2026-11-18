---
name: openbot-os
description: Router and constitution for the OpenBot OS build — a self-hosted, self-evolving multi-venture agent conglomerate assembled from OpenBot, Rakazo, OpenDots, Grok Bot and Meta Muse Code. Use at the start of any session, before touching code in repos/OpenBot, repos/rakazo, repos/OpenDots or services/sentinel, when deciding which upstream repo a feature belongs to, or when you do not know which other skill applies.
---

# OpenBot OS — Router

Read this with `AGENTS.md` and `PROJECT_MEMORY.md` every session. The latter records current
access and the next action; `STRATEGY_ADDENDUM.md` contains the newer private-pilot and bounded-
improvement direction. Public source is owner-authorized, not production release. Current Antigravity
source was reviewed; see ADOPTION_REVIEW.md before the legacy queue. Keep the independent kernel;
Bot HQ is now an installed provider-disabled local profile, not merely a donor. The separate fixed
execution slice is described by EXECUTION_SLICE.md and the local-execution skill; it is not wired
into HQ/Worker/HTTP and is not hostile-code isolation. ANTIGRAVITY_WORK_ORDERS.md is the current
remaining queue; OWNER_CHECKLIST.md separates human work. DONOR_REUSE_REVIEW.md supersedes old
“all features consumed”/generic review-card assumptions. Read LOCAL_POLICY.md before imported skills.

## Current donor storage / actual scope override

Rakazo/OpenDots references below are logical ORIGINAL paths, not live donor runtime directories.
All 5,086 selected source files/licences are preserved in checked `archive/donor-sources/` vaults,
with26 reviewed references readable in `third_party/donor-library/`. Full scratch restores and
hash/size/mode checks preceded the owner's conditional redundant-loose-copy cleanup. The private
OpenDots `.env` is untouched. Working HQ/findrepo/OpenBot remain. Read `WORKSPACE_CLEANUP.md`;
never delete source vaults or mistake a copied reference for an integrated feature.

The layer descriptions below are the reuse/target architecture, NOT a claim that OpenBot's
runtime already enforces our kernel. Current execution/isolation/provider gaps are in AGENTS.md
and PROJECT_STATE.md. Human-led QA/documentation is now the first pilot target, owned-footage
editing second. No template, archived instruction or this skill can widen human/host permissions.
Current `.git`/tool availability must be inspected; old Muse/install descriptions are historical.

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
| `archive/donor-sources/rakazo.tar.xz` | full selected feature-donor snapshot; inert, not a runtime dependency |
| `archive/donor-sources/OpenDots.tar.xz` | full selected review-gate snapshot; private .env excluded and left unchanged |
| `third_party/donor-library/` |26 reviewed source/test/licence references; not compiled or active instructions |
| `services/sentinel` | our FastAPI egress proxy + HITL interrupt queue (the PDF's "Sentinel") |
| `packages/venture-sdk` | implemented local venture manifest validation; see measured state |
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
| Paid-work intake, QA evidence, direct feedback, social/media readiness | `work-delivery` + `sentinel-gate`; read WORKFORCE_PLATFORM.md |
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
Then state which upstream(s) the task touches. Before handoff, update `PROJECT_MEMORY.md`;
preview cleanup with `make tidy-check` and apply only untracked cache removal with `make tidy`.
Never erase run/financial/audit evidence or initialize/push mirrors to tidy the workspace.
