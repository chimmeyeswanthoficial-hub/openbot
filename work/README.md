# OpenBot OS

> **Public source; controlled development/pilot, not a production launch.** The owner made
> `openbot` and `findrepo` public and authorized selective reuse. Read
> [`ADOPTION_REVIEW.md`](ADOPTION_REVIEW.md) for the current-source review and foundation decision,
> and [`CONTINUE_HERE.md`](CONTINUE_HERE.md) before resuming work. The **private 1–6-month
> real-world pilot and human release decision** still apply.

A self-hosted **company control-plane prototype**: agent roles, human approvals, routine preflight,
venture rules, audit records and ledger-derived P&L. It is not yet a fully connected autonomous
business, a hardened sandbox or evidence of real revenue.

## S11–S12 local controls and evidence contracts (unreleased)

Added an opt-in, default-paused operator gate with approval epochs; bounded authenticated
SQLite/config/secret/grant backup and isolated restore; an independent-process durable alert
outbox with exact receiver ACKs; and policy-pinned protected-evaluation/observed-day contracts.
Actual local crash/restore/worker-death/HTTP-ACK drills accompany executable regressions.
Read `docs/OPERATIONS_AND_PILOT.md` for integration boundaries, recovery, incidents, privacy,
retention and the remaining gates. Synthetic keys/clocks/tasks are not independent acceptance
or a real pilot. No existing preview/runtime was reconfigured; S09 external security/provider,
S10 native devices/signing, witnessed S11, real S12 and human S13 release remain open.

## S06–S10 local engineering continuation (unreleased)

The actual owned-media pipeline, first-party/consent governance and authenticated HTTPS
control-client workflow now have local implementations and observed tests. Genuine unsigned
Windows and demo-key-signed Android local packages accompany updated **source-only iOS**.
Read `STAGES_06_10.md` and the accompanying source/evidence/reproduction/rollback packet.
This does **not** clear the external cgroup/security/provider gate, native device/signing gates,
qualified human quality acceptance, S11 operations, S12 private pilot or S13 release decision.
No production pairing/migration, paid activation, customer execution, push or deployment occurred.
The S02–S05 sections below describe their historical checkpoint, not the newer local TLS adapter.

## S02–S05 local owned-work successor (unreleased)

Durable occurrences/reservations, a default-off authenticated owned-fixture API, bounded
local HTTP/SSE contracts and an actual QA/documentation workflow are implemented in this
successor. Read `WORK_STAGES.md` and the accompanying frozen source/evidence packet for
reproduction, recovery and the measured checkpoint. Real fixture-role review is **not**
qualified human acceptance. Paid providers, customer code, external delivery, client pairing,
production migration and release remain disabled. Earlier handoff text below is historical.

## Historical S01 disposable PostgreSQL checkpoint

This uncommitted local successor separates schema-owner setup from explicit existing-only
application connections (`initialize=False`). The application fixture role has no DDL or
evidence-rewrite rights. New real PostgreSQL process-race, disconnect, client-death and actual
restore probes supplement—not rewrite—the historical AG4 900-pass/6-skip result.
See `POSTGRES_PROFILE.md` and the stage evidence packet. The current structured Python row
is generated only from a completed run. No production schema/account, deployed app config,
provider, pairing, customer-code authority or public release is enabled. Durable occurrence /
whole-liability work was the next stage at that checkpoint; see the S02–S05 successor above.

## Current continuation

Technical stewardship continues through a fixed-tool rootless namespace experiment and repaired
legacy transport semantics. Read `NAMESPACE_EXPERIMENT.md`, `DELIVERY_PLAN.md` and
`audit/progression-review.json` before relying on older evidence below. Rootless namespaces now
work with a cache-only pinned non-setuid tool; per-job cgroups, mandatory authenticated runtime
wiring, protected secrets/tenants and independent security review remain missing. No broader
execution or provider was enabled. The dispatcher is default-off, single-attempt and honest about
unknown stop/cost/delivery; its valid reply is a draft, not a successful external job.
`ANTIGRAVITY_START.md` contains the owner's next three actions and paste-ready AG0 prompt.

## Broader work-platform direction

The goal is useful AI work delivery, not only an OS. **`WORKFORCE_PLATFORM.md`** explains the chosen
QA/documentation-first pilot, candidate paid services, realistic specialist-quality evaluation,
permitted social/feedback workflows and video roadmap. New offline intake/QA evidence/revocable
reviewed-feedback code has80 focused tests; it does not connect accounts, execute customer code,
train models, generate video or authorize sends. Run `make workforce-demo` in the locked environment.

## One file to understand the whole project

Read **[`OUR_PROJECT.md`](OUR_PROJECT.md)**: the owner's preserved exact request versus faithful
vision summary, architecture, working/planned features, Bot HQ and other donor reuse decisions,
limits, money/learning/pilot, human/AI responsibilities, restore and remaining work. It is a
self-contained explanation, not just a links index. Bot HQ's older transcript history is now
available through bounded owned generation-aware pages and an explicit retryable UI control;
`audit/hq-history-review.json` records this follow-up's red→green/browser/restore evidence.

## The foundation decision

Keep our governance/accounting kernel independent. Retain OpenBot/AG-UI as the current replaceable
workspace/runtime target; **do not migrate wholesale to Bot HQ**. Reuse useful MIT code through
small adapters, without copying excluded artwork or importing browser/shell approval gaps.
CopilotKit Intelligence remains separately licensed; its services are not implemented by this kernel.

Current Antigravity first-party additions were reviewed and incorporated locally from
`a67fb041763bdfd16ed8b77f0ad24edd8e154f20`, preserving maintenance fixes and runtime evidence.
**These local corrections have not been pushed back to the public repository.**

## Installed Bot HQ local workspace and continuation

The owner expanded the earlier queue-only adoption: **Bot HQ is now locally installed** at
`apps/bot-hq`, with neutral artwork, pinned dependencies and a provider-disabled launcher.
It reuses the roster, SQLite/store/session/event/transcript/task/skill features. A real
company-readiness task crosses into our independent Sentinel kernel and returns hashed evidence,
zero provider cost and durable audit/replay references. Notes/skills remain inert local data.
It does **not** run a model, computer, scheduler, external connection, payment or release.

```sh
bash scripts/bot-hq.sh install     # Linux x86_64 / Python 3.13; pinned & hashed downloads
bash scripts/bot-hq.sh start       # foreground authenticated preview on :8787
bash scripts/bot-hq.sh access-code # another terminal; code is local, never bundled
```

Read [`BOT_HQ_INSTALLATION.md`](BOT_HQ_INSTALLATION.md) for capabilities/evidence/limits and
[`CONTINUE_HERE.md`](CONTINUE_HERE.md) for the downloadable full-project continuation workflow.
Dependencies, builds, authentication codes and processes must be restored after transfer.

## Fixed local execution and remaining handoff

`EXECUTION_SLICE.md` documents the separate trusted-host wordcount executor: real Linux subprocess/
SSE, exact-draft review, transactional **attempt** quota, real process stop, scoped outbox and
integrity/restart checks. Run `python scripts/execution-demo.py` with the locked environment.
It is not wired into HQ/HTTP/Worker/live-model AG-UI, hostile-code isolation or paid-spend control.

`ANTIGRAVITY_WORK_ORDERS.md` gives ordered remaining acceptance tasks; `OWNER_CHECKLIST.md`
separates human decisions/accounts/on-call/release. No direct IDE shipment occurred.
`DONOR_REUSE_REVIEW.md` assesses useful remaining Rakazo/OpenDots mechanisms/tests. All 5,086
selected source files/licences are preserved in verified `archive/donor-sources/` vaults, with
26 reviewed references directly readable under `third_party/donor-library/`. Redundant loose
copies were removed only after exact restores. Working HQ/findrepo and OpenBot stay in place;
not all donor features are integrated. Read `WORKSPACE_CLEANUP.md` for the audit and recovery.

## Run the local control-room demo

In this workspace, or after applying the reviewed local source changes:

```sh
python3 -m venv .venv && . .venv/bin/activate
make install
# terminal 1: throwaway in-memory DB, loopback only
python3 -m uvicorn app:app --app-dir services/sentinel --host 127.0.0.1 --port 8090
# terminal 2: activate the same venv, then seed SYNTHETIC demo records
python3 scripts/seed-demo.py --base http://127.0.0.1:8090
```

Open `http://127.0.0.1:8090/`. No Docker/model/provider key is needed for this demo. Never point the
seed at business data. `make demo` is a legacy convenience target; the explicit two-terminal path
above avoids its seed-before-server startup assumption. This is a governance demo, not a live Bot.

## What exists now

| Piece | Implemented | Important limit |
|---|---|---|
| Control room + Sentinel | Policy decisions, approval rows, audit trail, org/routine/ledger overview | Real substrate execution is **not yet obligatorily routed through it**; reads need network/auth protection |
| Worker | Strict routine parsing, preflight, minute deduplication, Sentinel HTTP client/daemon | Gate/deny/malformed response handling repaired; persistent restart-safe execution and real Bot pickup remain open |
| Gateway | Tool-action mapper and approval-card adapter | Unit-tested seam, not installed enforcement inside OpenBot/Hermes; raw browser/shell/path security incomplete |
| Ledger | Idempotent rows and computed P&L; signed webhook route | Absent signing secret disables webhook; provider currency/cross-event/refund reconciliation not production-ready |
| Storage | SQLite/in-memory; optional Postgres code | Live Postgres tests skipped; no claim of migration/crash/concurrency readiness |
| Media API | Experimental conversion/compression code | Disabled by default; explicit experiment flag + token needed; RAM buffering/process-lifecycle defects remain; split returns 501 |
| Deployment helper | Explicit record-only plan bookkeeping | **Not** an image deployer, migration verifier or real rollback mechanism |
| Monitoring/approvals | Heartbeat helper, digest formatter, age banner | External monitor/digest delivery/on-call drills not proven |
| Reuse tools | Installed findrepo CLI/skill, REA instructions, queue port and local-only Bot HQ with governed company reports | All HQ providers/engines/computer/voice/MCP/schedulers disabled; REA runtime not installed; queue port not wired into Worker |

Our intended action ladder is **safety → policy → budget → audit → act**. The core invariant is
“no audit row, no action,” but the real browser/shell/runtime integration must still demonstrate it.
A UI approval card or a model prompt is not a security boundary.

## Verification

Current Python: `pass=1424, skip=0, fail=0, collected=1424`

The current row is generated from completed JUnit by `scripts/record-verification.py`; exact evidence
and limitations live in [`audit/EXECUTION_FINAL_VERIFICATION.md`](audit/EXECUTION_FINAL_VERIFICATION.md) and
[`PROJECT_STATE.md`](PROJECT_STATE.md). Historical run counts are not current results, and skips
are never counted as passes.

```sh
make test            # Python source tests
make reuse-test      # dependency-free findrepo/queue tests, Node 18+
make hq-test         # pinned Node: build/typecheck + local HQ/kernel regressions
make lint            # findings/missing dependencies fail
make verify          # measured local gates + fresh health boot
make smoke           # 10 scratch-DB HTTP checks
make release-check   # includes all above; NOT public-release approval
```

The remote baseline independently reproduced `pass=214, skip=2, collected=216`, but direct lint
found 24 issues and new boundary regressions exposed defects its tests missed. See the review for
exact repairs. No local green result proves provider cancellation, strict tenant isolation, safe
billing, profit or a month of unattended operation.

## Safe private operation

**Do not expose this prototype directly to the internet.** Protect the entire service—including
read endpoints—with network controls, authentication and TLS. Set `SENTINEL_UI_TOKEN` for approvals
and manual ledger writes before any shared private deployment. Keep bot execution, secrets and
protected evaluator/deploy authority outside bot-writable workspaces.

`SENTINEL_DB` may select a SQLite file; default in-memory data vanishes on restart. Optional PG
support requires the `postgres` extra and a separate disposable test deployment. Mutating PG tests
only run when `OPENBOT_TEST_POSTGRES_DSN` and `OPENBOT_TEST_POSTGRES_ALLOW_WRITES=1` are deliberately
set; normal production `DATABASE_URL`/`SENTINEL_DB` are never used by those tests.

Do not enable the experimental Media API or configure payment ingestion for real customers until
the open product/accounting/security issues in the review are closed. An HTTP timeout does not
stop a remote agent, and checking reported cost afterward does not impose a hard budget.

## Skills and discovery

Use `.claude/skills/` and the local policy file beside each imported skill. Example:

```sh
bash scripts/findrepo.sh repos "agent queue" --no-cache
```

findrepo performs public research by default, without inheriting account tokens or invoking `gh`
credential discovery. Account use and instruction-file initialization require explicit opt-in.
Search text leaves the machine; never include secrets/customer data. REA's own instructions say
ordinary complete-source architecture reviews should use normal repository tools, not its engine.

## Documentation

| Need | Read |
|---|---|
| Current decision, source evidence, Antigravity reconciliation and limits | [`ADOPTION_REVIEW.md`](ADOPTION_REVIEW.md) |
| Resume with exact state and next action | [`AGENTS.md`](AGENTS.md) → [`PROJECT_MEMORY.md`](PROJECT_MEMORY.md) |
| Measured local status / remaining acceptance criteria | [`PROJECT_STATE.md`](PROJECT_STATE.md) · [`PROJECT_REMAINING.md`](PROJECT_REMAINING.md) |
| Learning loop, pilot and human boundaries | [`STRATEGY_ADDENDUM.md`](STRATEGY_ADDENDUM.md) |
| IDE handoff and safe integration | [`HANDOVER_CHECKLIST.md`](HANDOVER_CHECKLIST.md) |
| Reasoning/taste/predictions, not a current runtime claim | [`PROJECT_BRAIN.md`](PROJECT_BRAIN.md) |
| Company types, advantages and hard legal and real-world limits | [`aboutme.md`](aboutme.md) · [`advantages.md`](advantages.md) · [`disadvantages.md`](disadvantages.md) |
| Original plan / feature sources / environment blockers | [`plan.md`](plan.md) · [`FEATURES.md`](FEATURES.md) · [`BLOCKERS.md`](BLOCKERS.md) |

No background maintenance or pilot is running merely because these files exist. Further progress
requires another active session or an explicitly deployed, monitored runner.

## Licences

Our first-party code is MIT. Donors retain their own licences; CopilotKit Intelligence is separately
licensed. Selected Bot HQ code carries its MIT notice under `third_party/bot-hq/`; its excluded
Grok-derived artwork/logos were **not** copied. findrepo and REA notices and local policies are
retained alongside their installed files. An analysis tool's licence does not license its targets.
