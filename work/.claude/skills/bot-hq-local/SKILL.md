---
name: bot-hq-local
description: Install, verify, run and extend the pinned Bot HQ local-only derivative without enabling upstream providers, autonomous startup, excluded artwork or financial authority. Use for all work under apps/bot-hq or scripts/hq_readiness.py.
---

# Bot HQ local integration

Read CONTINUE_HERE.md, AGENTS.md, BOT_HQ_INSTALLATION.md and the project-owner,
upstream-merge and sentinel-gate skills before changing runtime permissions.

## What is installed

Pinned MIT Bot HQ source at `apps/bot-hq`, lockfile dependencies and a neutral,
authenticated local profile. Upstream live entry/helper scripts are quarantined;
the runtime imports only database/store/session/hub modules. Artwork/logos are not
included; replacement badges are original and icons use attributed Lucide.

The one implemented company tool is `company.readiness`: HQ persists a task,
invokes the fixed Python adapter with a minimal credential-free environment, and
receives hashed-input evidence plus independent Sentinel audit references. It is
not an LLM response, a new test run, revenue or product-release authorization.

## Commands

- `bash scripts/bot-hq.sh install`: restore pinned Node, hash-locked Python 3.13
  wheels and npm dependencies with all lifecycle scripts disabled; typecheck/build.
- `bash scripts/bot-hq.sh start`: foreground local profile, bind 0.0.0.0, token sign-in.
- `bash scripts/bot-hq.sh access-code`: host-only code; never put it in docs/bundles.
- `bash scripts/bot-hq.sh test`: disposable kernel/host regressions.
- Full Python, reuse, lint, verify and smoke gates remain required before handoff.

Dependencies, builds, browser/toolchain caches, authentication codes and running
processes are not portable snapshots. Restore them; do not merely cite old receipts.

## History and remaining reuse

`OUR_PROJECT.md` is the owner master guide and source-backed remaining HQ reuse review.
History uses existing store beforeSeq behind owned validated max200-row pages, paired generation,
revision watermark and tested shared state. Never expose unbounded afterRev as a shortcut.
Latest snapshot resync deliberately replaces gapped old windows; streamed newer revisions survive.
Run17host+9history-state Node cases via the wrapper; optional real HTTP browser flow is
`node scripts/test-hq-history-browser.mjs` (Chromium/OS dependencies separate). Preserve old rows;
do not enable upstream clear/delete/engine routes to implement history or test resets.
`audit/hq-history-review.json` records source delta; original installed inventory is historical.

## Extension rule

1. Add a red regression before behavior changes.
2. Keep business policy/audit in the independent kernel, not the HQ UI.
3. Do not import `engine`, `routes`, `computer`, `loop`, `voice`, MCP or schedulers
   into the local import graph. Neither a dashboard toggle nor a scheduler-off
   variable makes upstream startup safe.
4. Requests must not supply paths, programs, shell strings, URLs, budget limits or
   credentials to the tool. Unknown arguments refuse before any tool execution.
5. Audit before reads/writes; audit-store failure refuses. Exact request replay
   returns recorded evidence. Marker-without-completion requires reconciliation;
   never "fix" uncertainty by deleting markers or changing request IDs blindly.
6. A same-user fixed adapter is not OS isolation. Real outward tools still need a
   separately observed disposable execution boundary, exact-argument approval,
   durable budgets, cancellation and delivery evidence before provider enablement.
7. Update source/provenance, tests, notices, memory and continuation archive together.
   Preserve all existing ledger/audit/run evidence and keep the private pilot gate.
