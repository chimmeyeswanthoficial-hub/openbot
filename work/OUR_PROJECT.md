# Our project: OpenBot OS

## One file to understand the vision, the code, the truth today and the next work

**For:** the human owner and any engineer/AI continuing the project.  
**Task date:** 2026-11-10. Existing runner receipts observe 2026-11-13/14; these are kept as observed timestamps, not silently substituted for the supplied task date.  
**Bottom line:** We are building a company-operating agent, not just a chatbot. We have a tested local company-control foundation, an installed Bot HQ workspace and two narrow kinds of real local execution. We do **not** yet have a continuously operating company, a production-safe general agent or genuine settled revenue.

This is the owner's requested **single, self-contained explanation**. You can understand the project from this file without opening twenty other documents. Linked files are implementation/evidence references, not a substitute for the explanations here. This file is not a verbatim transcript of every earlier conversation.

### Latest engineering continuation — keep advancing, hand off at the real gate

The owner asked for continued technical stewardship until specific permissions/resources and the
Antigravity/human handoff. `DELIVERY_PLAN.md` is the current sequence; `ANTIGRAVITY_START.md` is
the short backup/import/paste checklist. Implemented a separate opt-in fixed-tool namespace
experiment and corrected default-off legacy dispatch, with red/green evidence and actual process
probes. `NAMESPACE_EXPERIMENT.md` / `audit/progression-review.json` define the exact tested scope.

The rootless namespace tool now works, with read-only mounts, minimal environment, seccomp,
fixed-worker rlimits and real cancellation/deadline/parent-death observations; no host fallback.
It is not arbitrary customer-code authorization or completed AG1. Cgroup delegation, mandatory
authenticated live execution, protected secrets/tenant separation and independent review remain.
A dispatcher reply is a draft, reported cost is unverified, timeout is not remote kill and the
same stored run cannot automatically dispatch twice. No paid provider or outbound action enabled.
The first pilot stays human-led QA/documentation, then owned-footage editing. Human legal,
accounts/prices/spend/sensitive outbound/release and the private observed pilot remain mandatory.

### Newer direction: a broader AI work-delivery platform

**Summary of the newer request, not a verbatim quotation:** go beyond an OS to find and perform
useful paid work, ask humans useful questions, learn from permitted feedback, improve through
reviewed changes, and eventually edit/generate video. The owner delegated technical priorities.
Chosen: **human-led QA/documentation first; owned-footage editing second**; transparent company
identity with a real administrator and social drafts only. Human consequential authority stays.

`WORKFORCE_PLATFORM.md` provides the concrete12-service readiness/quality matrix, opportunity
checks, platform/data rights and staged media plan. New offline code qualifies supplied metadata,
prepares clarification questions, packages actual-case JUnit evidence and stores separately
consented direct feedback pending exact-digest host-human review, with scope/revocation/expiry.
80 focused tests and an actual six-test media-boundary evidence packet support that narrow claim.
It is **not** autonomous job discovery/execution, posting/liking/commenting, safe customer-code
isolation, model training, video generation or measured human-specialist parity. No account or
customer was connected, no application sent and no income earned. Compliance reduces account
risk; nobody can guarantee no bans. See `audit/workforce-review.json` for the newest freeze.

Historical metadata/memory originals referenced below are recoverable byte-for-byte using the
mapping in `audit/workforce-evidence-consolidation.json`; no business/donor evidence was discarded.

### Newer workspace-cleanup decision

The owner asked to clear donor folders only after useful code is copied. We have **not** used all
features. Instead of pretending otherwise, all 5,086 selected Rakazo/OpenDots source files were
preserved in lossless checked archives, with 26 reviewed source/test/licence references directly
readable in `third_party/donor-library/`. Only exact redundant loose copies were removed AFTER
successful full restores. Unreviewed/deferred material is preserved too. OpenDots private `.env`
is untouched. The working `apps/bot-hq`, `tools/findrepo`, queue attribution and `repos/OpenBot`
remain; deleting these would remove installed value rather than just donor clutter.
`WORKSPACE_CLEANUP.md` / `audit/donor-consolidation.json` give the exact proof and recovery commands.
This is reversible source consolidation, not completion of all integrations or an off-host backup.

### Read by question

1. [What did you ask for, in your own words?](#1-your-exact-preserved-request-and-the-quotation-limit)
2. [What are we trying to build?](#2-your-project-in-plain-words--faithful-summary-not-a-quotation)
3. [What does the Minecraft comparison mean?](#3-the-minecraft-idea-translated-into-real-engineering)
4. [How does the system fit together?](#4-the-architecture-and-why-we-keep-the-company-kernel-independent)
5. [What works now, and what does not?](#5-what-exists-today)
6. [Is Bot HQ useful? What else should we copy?](#7-bot-hq-is-useful-here-is-the-actual-reuse-decision)
7. [How will it make money and improve?](#9-the-first-company-real-money-and-what-success-means)
8. [Who does the remaining work?](#12-who-does-what)
9. [How do I restore and use it?](#14-how-to-download-restore-run-and-stop-it)

---

## 1. Your exact preserved request and the quotation limit

Your previous guide/history request, preserved verbatim from the available conversation:

> Continue and also what about bot HQ is it useless or any useful features and codes to copy in our project and make .md file of show me everything about our project so 1 .md to understand everything about our project use exact words that i want our project and tell in words about i Tell you the words that our project okay

**Important honesty point:** I do not have a complete verbatim archive of all your earlier messages. `PROJECT_MEMORY.md`, `PROJECT_BRAIN.md`, `STRATEGY_ADDENDUM.md` and the archived memories preserve decisions and reasoning, but they are mostly **assistant-written records**, not your original sentences. I will not turn those records into invented quotations or claim that an earlier assistant's words were yours.

The next section expresses your intended project in plain language. It is a **faithful reconstruction of the preserved directions, not an exact quotation**. If you later supply the original messages, they can be added with their actual wording and source, without changing what the code is claimed to do.

## 2. Your project in plain words — faithful summary, not a quotation

**Reconstructed owner brief, written in the first person for readability; not verbatim speech:**

I want a capable bot that can help create and operate a real company and earn real money, not just answer questions or show a nice interface. It should observe what is happening, understand available resources, plan useful work, use tools, build tools when needed, responsibly reuse good repositories and skills, delegate bounded jobs to other bots, keep workspaces organized and learn from weaknesses and mistakes.

I want the engineering assistant to act as a technical partner: inspect the code, use skills, make justified technical decisions, actually install useful components, test them repeatedly and say honestly when something is not ready. I do not want another framework copied only because its demo looks impressive. Existing work, source notices, company records and failure evidence must not disappear during an upgrade or cleanup.

I remain the owner of the business. Legal responsibility, entity, accounts, prices, spending, sensitive outbound actions and release decisions stay with me. I want the whole project, its context, its working method and its remaining work preserved so another chat or IDE can continue. Public source is allowed for my `openbot` and `findrepo` repositories, but the product still needs a meaningful private real-world pilot lasting one to six months and an evidence-based human release decision.

**End of reconstructed brief.** These directions do not promise guaranteed profit, perfection, unlimited memory or unrestricted autonomy. They describe the goal and how we should work toward it.

### One-sentence product definition

**OpenBot is a self-hosted, governed AI work-delivery platform: specialist task workflows and a workspace/runtime around an independent policy, approval, audit, venture and accounting kernel.**

The long-term differentiator is not the conversation window. It is the ability to do useful work, account for its actions and costs, recover from mistakes, improve under controlled review and demonstrate real business results.

## 3. The Minecraft idea translated into real engineering

The useful analogy is progression with limited resources, not permission to experiment on customers.

| Game idea | Meaning in this project |
|---|---|
| Observe the world | Read permitted market, product, customer and operational evidence; identify stale data |
| Check inventory | Know approved tools, skills, workspace, cash/runway and remaining resource limits |
| Choose the next objective | Pick one measurable customer or operational outcome, not endless agent activity |
| Craft a tool | Build or adopt a versioned, licensed, tested tool with declared permissions |
| Work with teammates | Delegate bounded tasks with original identity, a shared total budget and hop limits |
| Learn after failure | Preserve the incident, find the cause and add an enforced prevention check |
| Progress | Deliver more reliable useful work at acceptable cost; compare against the previous version |
| Survive | Avoid unauthorized acts, uncontained spending, data loss and customer harm; restore when something breaks |

The intended loop is:

```text
observe permitted evidence → select one useful objective → propose a bounded plan
→ check authority / policy / budget → record the decision before the effect
→ execute in an isolated workspace → independently read back the result
→ account for actual cost / delivery / settlement → review quality and incidents
→ propose a tested improvement → independent review / required human approval
→ canary and measure → keep it or roll back
```

Parts of this loop exist locally. The whole loop is **not** running unattended. A game can be reset; an exposed customer document, a bad contract or an unauthorized payment cannot simply be reset. Production authority must be narrower than practice-world authority.

## 4. The architecture and why we keep the company kernel independent

### The three distinct layers

1. **Workspace:** where a person sees Bots, notes, tasks and evidence. The installed local workspace is our attributed Bot HQ derivative.
2. **Execution/runtime:** the program that actually performs a task. We have a separate fixed local executor; the replaceable real-agent target is OpenBot/AG-UI. A general governed live-agent bridge is still unfinished.
3. **Company kernel:** our policy, approval, independent audit, venture/routine rules and ledger-derived accounting. A new workspace must not become a new source of financial or legal authority.

### Actual connected paths today

```text
Human → authenticated local Bot HQ → local roster / notes / inert skills / task views
                                  │
                                  └─ fixed company.readiness request
                                     → fixed Python adapter
                                     → independent Sentinel audit + bounded evidence reads
                                     → hashed local report → HQ task / transcript

Trusted Python host → separate fixed LocalExecutor API
                     → GatewayAdapter / Sentinel decision + audit
                     → exact review when required + transactional ATTEMPT quota
                     → fixed Linux wordcount subprocess → bounded SSE events
                     → integrity-checked local artifact / outbox / replay
```

**There is no implemented arrow from HQ, the Worker daemon or a live model to that fixed LocalExecutor.** The two paths above are separate. A functioning report button is not proof that a model can safely browse, code, send or spend.

### Target path still to complete

```text
Authenticated human / durable scheduled occurrence
→ immutable actor + venture + original initiator
→ mandatory kernel policy / exact approval / financial reservation / audit
→ isolated replaceable agent runtime and controlled tool interface
→ observed result + real cancellation + durable events / delivery receipts
→ canonical cost and settlement reconciliation
```

OpenBot/AG-UI remains the working real-agent integration target. A future Hermes adapter could be justified by an equivalent governed workload comparison. That would replace an adapter, **not** rewrite the ledger or move business authority into Bot HQ.

### Stack: actual versus intended

| Area | Actual local state | Working target / qualification still needed |
|---|---|---|
| Company services | Python/FastAPI, deterministic rules, SQLite/in-memory support | Protected production identities; tested PostgreSQL migrations, concurrency and recovery |
| Installed workspace | React/TypeScript, Vite, Node/Hono, SQLite and the donor's CSS; neutral badges/Lucide | Consistent product UX; React/TS/Tailwind is a desired direction, not a reason to rewrite working CSS now |
| Agent interface | Existing mapper/adapter; fixed worker emits a narrow tested SSE dialect | Real bounded AG-UI streaming and authenticated mandatory tool interception |
| Scheduler | Markdown routine parser and preflight; in-process minute guard | Durable occurrence claims, leases/fencing and restart-safe delivery; Redis only if justified |
| Infrastructure | Local build/test environment; no deployed company host | Owner-approved Docker-capable Linux VPS, no Kubernetes; measured unprivileged isolation |
| First paid-pilot target | Human-led QA/documentation; offline work intake/evidence/feedback library | Verified customer delivery after isolation/authority gates; media is the second track |

Installed source, restored dependencies, a successful build, a running process, a connected provider and production readiness are **six different claims**. Never substitute one for another.

## 5. What exists today

**Labels:** *Implemented locally* means a tested mechanism within the stated scope. *Partial* means useful code exists but the end-to-end guarantee does not. *Planned* means acceptance work remains. None means a live business is operating.

| Capability | State | What it really means / main limit |
|---|---|---|
| Org and venture validation | Implemented locally | Six roles including the human owner, duties, prohibitions and manifest/economic validation. Role descriptions are not five active model workers |
| Sentinel policy and audit | Implemented locally | Named-action decisions, local audit and tested fail-closed persistence. Not all generic real tool routes are obligatorily intercepted yet |
| Approval storage | Implemented locally | Durable pending/resolution state; conditional one-time resolution. A stored card is not remote human authentication |
| Routine parsing and preflight | Implemented locally / partial operation | Strict markdown, due times, pause/venture/budget preflight and in-process minute guard. No proven restart-safe multi-worker business scheduler |
| Ledger and P&L | Implemented locally / partial accounting | Idempotent rows and computed totals. Canonical provider economic events, currencies, fees, refunds and settlement reconciliation are unfinished |
| Bot HQ workspace | Implemented locally | Authenticated roster, SQLite state, sessions, events, transcripts, task views, notes and inert skills; no paid account needed |
| Earlier transcript history | Implemented locally in this continuation | Validated owned pages of at most 200 rows, explicit earlier-entry control, retry and generation/revision protections; details in §7 |
| Company readiness report | Implemented locally | A fixed adapter reads three bounded evidence inputs through independent audit, stores a digest-bound report and replays known completion |
| Fixed local wordcount execution | Implemented locally | Real fixed subprocess, exact draft review, attempt reservation, SSE, real stop/reap and scoped output/replay; separate trusted-host API only |
| Generic live Bot / browser / shell | Unfinished | Mandatory authenticated interception, real OS/egress isolation, protected credentials and actual runtime wiring still needed |
| Provider hard budgets and remote stop | Unfinished | Fixed attempt units are not dollars; an HTTP timeout or AbortSignal is not observed remote termination |
| findrepo | Installed selected tooling | Research CLI/skill with explicit auth/cache/instruction-write controls; discovery does not approve installation |
| REA | Installed instructions only | Skill plus eight references and notices/local policy; engine/MCP/providers and demonstrated learning transfer are absent |
| Media API | Quarantined experiment | Default off, explicit experiment flag plus token; resource/process-lifecycle gaps remain; split returns 501, not fake success |
| Deployment | Record-only helper | Records a proposed operation. It does not deploy an image, execute migrations or prove rollback |
| Monitoring and owner digest | Partial | Heartbeat/digest formatting helpers exist; independent external alert/digest delivery and recovery drills are not proven |
| Self-improvement | Rules/method partly present | Incident ledger and regression discipline exist. Protected evaluator, learned-tool promotion, production canaries and measured general learning remain work |
| Pilot / genuine revenue | Not started / none evidenced | No meaningful private pilot, settled customer earnings or general release has occurred |

Some retained upstream settings/components have controls or copy for features the local API deliberately refuses. Their presence is not a supported connection, deletion, live-memory or autonomous-learning capability. The local banner and this contract define the actual profile; complete UX cleanup is not claimed.

### The real preserved company state

The primary HQ database contains **one saved company-report task**. Its independent kernel has **six audit rows** and a saved report/run. These are real **local evidence records**, not customer orders or earned revenue. Disposable regression/browser tests use separate databases and do not add primary business activity.

No project business server is intentionally left running at the delivery checkpoint. No model/payment provider, autonomous company runner or periodic maintenance job is operating merely because this file exists.

## 6. What the two local execution slices actually prove

### A. The company-report button inside HQ

1. The owner signs into the provider-disabled workspace using a host-generated local access code.
2. A canonical request ID starts a persisted HQ UX task/marker.
3. HQ calls only the fixed Python readiness adapter with a minimal environment. The request cannot supply a shell command, URL, path, credential or budget.
4. The independent kernel audits the fixed evidence reads and writes a digest-bound report.
5. HQ displays the report and records completion/task references.
6. A known exact request replays recorded evidence. An interrupted marker without trustworthy completion requires reconciliation; it is not automatically rerun.

The report reads existing receipts. It **does not rerun tests**, answer intelligently, earn money or authorize product release. A cached report also does not update itself when later tests change.

### B. The separate LocalExecutor

The supported tools are `local.wordcount` and `local.reviewed_wordcount`. A trusted Python host supplies frozen actor/venture/original-initiator context. JSON cannot grant owner rights or choose arbitrary programs, network destinations or costs.

The slice bounds UTF-8 text to 8,192 bytes, validates request IDs and scoped output names, binds reviewed input and relevant implementation hashes, reserves attempts transactionally, launches fixed Python with a minimal environment/rlimits, consumes correlated bounded SSE and checks actual output. Cancellation/deadline handling kills and waits for the real child/process group. Completion and replay verify output/result/event evidence and current relative delivery scope.

**Critical limits:**

- `Owner('human:owner')` is a host capability convention, **not a remotely authenticated human**. Do not expose its constructor through a JSON field.
- Reserved units are **attempts**, not USD, daily spending or revenue. They do not prove a financial ceiling.
- Same-user fixed code and rlimits are **not hostile-code, tenant, OS or network isolation**. Same-user source/path races remain.
- Its event dialect and process kill are not full AG-UI compatibility or cancellation of a remote model provider.
- Local outbox replay is not exactly-once sending to an external customer. Unknown remote outcomes need reconciliation.
- It is not wired into HQ, Worker, HTTP or a live model.

See `EXECUTION_SLICE.md` and its 47 focused regressions for the precise API and limits. Do not generalize it into an unrestricted shell tool to make the demo look more complete.

## 7. Bot HQ is useful: here is the actual reuse decision

**No, Bot HQ is not useless. We already use substantial useful code from it.** It gives us a coherent workspace faster than rebuilding roster, conversations, task views, settings and event handling. It is not a replacement for our company kernel, a security sandbox or an accounting engine.

The installed source is pinned to **`decf9a215cddd8792a5f20f4a11a87d4dffa6d15`**, not an unreviewed latest branch. The review below concerns the retained source at that pin and our local derivative; it does not claim every upstream module/dependency has been security-audited.

### Already adopted

- Database/store/session/authentication and event-hub building blocks, adapted to an authenticated provider-disabled profile.
- Bot roster, transcript rendering, live-state presentation, task views and inert skill/notes storage.
- The separate small per-bot serial queue under `packages/bot-hq-queue`, tested but not wired into the Worker.
- Our original narrow HQ-to-Python company-report bridge, which keeps audit authority independent.
- Neutral letter badges and separately attributed Lucide icons, not excluded donor artwork.

### Adopted in this continuation: accessible older history

**Problem:** the database kept entries, but the local route used only the default newest 200, and the client had no earlier-entry control. Long local work histories could become invisible after reload. This was a visibility limitation, **not evidence that rows were deleted**.

**Useful donor code:** `server/src/store.ts#listRows` already supports `beforeSeq`, ordering, generations and bounded reads. The original `routes.ts` has a cursor pattern. We reused the store capability, **not** the unsafe upstream route/import graph.

**What we added:**

- A read-only authenticated route accepting only validated positive safe-integer `limit`, `beforeSeq` and `generation`; maximum page size 200. Unknown, repeated, unbounded revision and malformed query fields refuse.
- Ownership checks before history access; an earlier-page cursor must include the conversation generation. A changed generation returns a conflict, not mixed history.
- An explicit **Load earlier entries** button with loading/retry feedback and reading-position anchoring.
- Shared pure generation/revision merge helpers. Older responses cannot resurrect a reset conversation or overwrite newer streamed row revisions.
- Reload/reconnect starts a fresh contiguous latest window and restores the earlier-page cursor. It deliberately does not pretend a union of widely separated cached windows is complete; you can load earlier pages again.

**Evidence:** three new host regressions failed on the old code. The completed HQ gate now has **26 Node tests: 17 host + 9 history-state**, plus the existing 30 Python HQ cases (a subset of the whole Python suite), typechecks and web/server builds. A real disposable Chromium flow reloaded 451 retained rows, recovered all 225 notes across two earlier-page clicks, retried an injected 503 without losing latest notes and ended the button at the oldest entry. Providers stayed disabled; no primary company task or kernel job was created. This is local HTTP browser proof, not HTTPS/proxy-cookie or hostile-tenant proof.

Sources: `server/src/local-app.ts`, `server/src/history-state.ts`, `server/test/{local,history}.test.mjs`, `web/src/{store.ts,lib/api.ts,components/ChatView.tsx,components/Transcript.tsx,styles/local.css}` under `apps/bot-hq`; browser reproduction is `scripts/test-hq-history-browser.mjs`.

### Remaining useful features: reuse, defer or reject

| Source under `apps/bot-hq/` | Useful mechanism | Our decision / reason |
|---|---|---|
| `server/src/store.ts` | Stable row sequence, per-row revision, conversation generation, transactional updates | **Keep/reuse now.** History builds on it. Do not expose its unbounded `afterRev` branch as a public catch-up endpoint without bounds and tests |
| `web/src/lib/events.ts` and `web/src/store.ts` | One event stream, reconnect/backoff and refetch after reconnect | **Keep/adapt.** Useful workspace recovery, not durable guaranteed event delivery or proof that a missed tool never ran |
| `web/src/components/Transcript.tsx` and `cards/Cards.tsx` | Grouped steps, status, citations, question/draft/approval presentation | **Keep presentation; later map kernel receipts.** An approval-looking card cannot grant financial/tool authority |
| `server/src/agent/loop.ts` | Per-bot serial work, live states, streamed engine-event mapping | **Selective adapter ideas after AG1/AG2.** The queue is in memory; local AbortController/interruption and restart-expired waiters are not durable execution or remote stop guarantees |
| `server/src/agent/rooms.ts`, `routes-rooms.ts` | Member checks, @mention selection, up to three responders, bounded recent context | **Defer governed groups.** Conversation membership is not venture/data/financial authority. Do not route one message into several spenders without shared caps and lineage |
| `server/src/agent/subagents.ts` | Parent linkage, hidden children, four-child cap, status summaries | **Defer delegation.** The cap is useful UX, not a race-safe total work/budget limit or hostile isolation; count-then-insert needs transactional review |
| `server/src/routines.ts` | Cron/timezone presentation and an existing routine UX | **Reuse display ideas; reject a second scheduler now.** Process-local jobs/`protect` and `last_run_at` do not give durable occurrence claims/fencing. Keep our routine authority and AG3 work |
| `server/src/triggers.ts` | Event-to-routine mapping and bounded event context | **Defer event adapters.** Requires reviewed provider subscription/identity, event authentication, deduplication, audit, egress and budget. The reviewed trigger handler does not establish a unique durable event claim |
| `server/src/proactive.ts` | Timezone-aware concise check-ins, useful-input context, silence/backoff | **Reuse digest idea later, not its autonomous engine now.** Need durable occurrence/outbox and real delivered owner alerts; a local timer is not an always-on monitor |
| `server/src/engine-memory.ts` | Inspectable memory entries and content-derived entry IDs | **Defer live memory.** It reads/writes Hermes-home files and imports the engine module. Direct rewrites, mtime-as-entry-time and content IDs do not prove provenance, concurrency safety, retention or evaluated learning |
| `server/src/engine.ts` | Replaceable Hermes engine API/home concept | **Possible future adapter, not startup code to copy now.** Managed provisioning creates config, can inherit model credentials and launches detached gateways; separate homes/screens are not OS security boundaries |
| `server/src/agent/tools.ts#policyFor` and loop approval helpers | App-action review UX | **Do not adopt as our policy authority.** Known in-app tools can default allow; unmatched tool paths can allow. Composio-write cards do not cover every browser/shell side effect, and “always” approval is not our exact human-review contract |
| `web/src/components/modals/SearchModal.tsx` | Keyboard-friendly Bot picker | **Keep, describe honestly.** Reviewed code filters Bot name/label/description, not full stored transcript text, despite broader placeholder wording. Full-text search is optional later, not a shipped claim |
| Computer/VNC, voice, MCP/Composio, connections and helper installers | Optional future interfaces/integrations | **Off. Reject wholesale enablement.** Separate costs, accounts, terms, privacy and security work; no need for them to run the current local workspace |

**Priority decision:** retain the useful workspace; next use donor ideas to close authority, actual runtime transport and durability gaps. Do not spend the next milestone building voice, mobile apps, another scheduler or an elaborate skill marketplace.

### Licence and safety conditions

Bot HQ code is MIT, copyright 2026 Nick Vasilescu; retain `LICENSE` and notices. Its upstream notices explicitly exclude certain xAI/Cursor-derived artwork, bot shapes/eyes, UI/app tiles, favicon and third-party logos from the project's MIT grant. Our installed derivative omits those known assets and uses neutral badges/licensed icons. Root MIT does not clear provider terms, every dependency or the whole retained project archive for public redistribution.

Its original startup can initialize engines/computers even if scheduling is off. Our compiled local entry does not import those modules; dangerous routes are **unmounted**, not merely hidden. No API toggle should turn them back on. Source/provenance and rollback are in `audit/bot-hq-installed-source.json`, `audit/hq-history-review.json` and `archive/bot-hq-before-history.tar.xz`.

## 8. The other repositories and tools: why they remain

| Component | Role in our project | Current truth / useful remaining work |
|---|---|---|
| Owner's `openbot` | Reviewed first-party project intake | Selected additions plus safety fixes preserved locally from `a67fb041763bdfd16ed8b77f0ad24edd8e154f20`. Root has no `.git`; local changes are not pushed |
| `repos/OpenBot` | Replaceable substrate/AG-UI integration target | Retained source is not a running engine. MIT application rights do not include separately licensed CopilotKit Intelligence services/code |
| Rakazo source vault + reviewed references | Feature/test donor, root Apache-2.0 | Useful occurrence/coalescing/fencing, change-watch, bounded ticket context, group handoff and backup patterns. Full selected source archived/restored before redundant loose-copy removal; no whole-runtime migration |
| OpenDots source vault + reviewed references | Review/recovery/scoping donor, root MIT / Atai Barkai | Useful stored-draft review, tool re-resolution/revocation, interrupted states and expected-revision edits. All selected source retained; private `.env` stays. Never copy blind external retry as exactly-once |
| `tools/findrepo` and skill | Installed licensed discovery helper | Pin `4d512682b8e30cfcbda2a7f74f44ae76df9ed77a`; reviewed auth/cache/write opt-ins. Search/ranking is not licence/security approval |
| REA skill/references | Optional authorized analysis/capture guidance | Pin `cdc4541ef707f256f83abe5018df01a25182cf0b`; instructions installed, engine not. Ordinary complete-source review does not need its runtime |
| Grok Bot and other closed products | Product benchmark | Learn generic interaction ideas; closed artwork/code and subscription terms are not ours to copy |
| Meta Muse/other coding labour references | Optional engineering helpers in older plans | Historical mention/configuration is not a currently running production worker or a requirement for local HQ |

Rakazo/OpenDots have **not** been fully consumed. Their retained selections and content fingerprints are in `audit/donor-review.json`: Rakazo 4,899 selected files, OpenDots 187. Their old main@date tarball labels are **not immutable upstream commit IDs**. Keep licences/notices and establish real provenance before upgrades. A scoped search found no direct first-party runtime imports from those two trees; that is not a transitive audit.

For OpenDots, the actual reviewed page-save path is `PageReviewCard → page-routes → pages#createReviewed`, not `TaskActions`. Authorized direct page tools can also write, so the donor does not automatically force human review of every write. AbortSignal/Promise timeout is not proof of stopped work; token text in a database is not a separated credential vault. These lessons matter more than copying a matching screen.

Donor source may be unnecessary **inside a production image** while still valuable in this private development/handoff archive. Those are different questions. The owner's newer cleanup request led to the lossless source-vault consolidation described above, not destruction of unconsumed source or permission to delete the working tools.

## 9. The first company, real money and what success means

### Start with one narrow venture

The updated engineering choice is **human-led QA/documentation first**, because bounded outputs
are easier to verify using the existing project. The default-off Media API remains a retained
experiment and **second-track** editing direction, not a service ready to sell. Start with one
customer/job profile and independent acceptance; service-led validation can precede polished SaaS.
`WORKFORCE_PLATFORM.md` describes the intake→clarify→review→produce→QA→approved delivery→settlement
funnel,12 candidate services and the explicit lack of measured human-specialist parity.

For the later media track, a future successful job would look like this:

1. A consenting customer submits a permitted, bounded media job under owner-approved terms and price.
2. The system authenticates/scopes it, reserves resource/cost liability and audits its permitted execution.
3. An isolated media worker enforces input/output/time/disk/memory/process bounds, verifies output and records usage.
4. Delivery is recorded and recovered without blind duplicate side effects.
5. Signed provider events are mapped to canonical economic events and reconciled with independent provider statements.
6. The owner sees quality, costs, refunds/fees, settlement and margin, not invented growth charts.

**That complete chain has not been achieved here.** Current experiments are not an offer ready to sell. `/split` remains 501; real streaming/backpressure, cancellation and ffmpeg lifecycle/resource tests remain required.

### What counts as money

A demo seed, test-mode payment, invoice marked paid, task marked done or an agent saying it earned money is **not genuine settled revenue**. Ledger totals must trace to validated canonical events and independent settlement evidence. Duplicate invoice/checkout/charge events must not count as three sales.

Useful business measures include settled receipts, recognized revenue under the approved accounting treatment, refunds/disputes, payment fees, model/media/infra/support costs, customer retention, actual delivery quality and human intervention time. Contribution and net profit are different; overhead, taxes and professional accounting treatment still matter. The current local P&L helper does not finish this provider/accounting work.

Old `$100k`, `$1k MRR`, `365 days`, fixed VPS costs, example prices or three-hours-per-week owner scenarios are **aspirations/configuration assumptions**, not forecasts, promises, observed workload or earnings. No profit guarantee is possible.

### Company types the broader idea could assist

| Business type | Plausible bounded assistance | What remains human / independently controlled |
|---|---|---|
| Software/API/digital services | Build/test drafts, process permitted jobs, triage support and report usage | Price, contracts, release, security, customer commitments, accounts and settlement |
| Research/content/back-office | Permitted research, sourced drafts, document processing, review queues | Accuracy/accountability, data rights, factual approval and consequential sends/publishing |
| E-commerce/logistics/manufacturing | Inventory analysis, catalog/support drafts, scheduling proposals | Physical inventory/delivery, supplier commitments, safety, payments and fulfillment operators |
| Medicine/legal/finance/insurance/tax | Administrative drafts and permitted clerical assistance | Qualified professional judgment, regulated advice, filings, signatures and liability |

A generic company goal does not make the bot a bank account holder, lawyer, doctor, tax authority, physical operator or accountable business owner.

## 10. Authority, safety and honest failure handling

### Non-negotiable intended rules

- **No independently persisted audited explicit allow, no effect.** Unknown/malformed/unavailable governance refuses. Mandatory coverage is still unfinished outside the narrow tested slices.
- Identity and scope come from an authenticated trusted host, not model text or caller-supplied JSON.
- Sensitive review binds the exact destination, draft, normalized arguments, actor, venture, policy/implementation and financial upper bound with expiry. Changed input needs new review.
- Money/legal/account credentials/sensitive outbound/release stay human-controlled. No blanket approval to unblock a queue.
- Reserve real bounded liability before paid work and reconcile actual independent usage. Prompt budgets and post-hoc reported cost do not impose hard caps.
- Agent workspaces cannot edit their own authority, production secrets, evaluator, audit retention or deploy approval.
- OS/network/secret/tenant boundaries must be independent of the agent. Path prefixes, separate homes, screenshots and `rlimit` settings alone are insufficient.
- Timeouts are not cancellation. Unknown completion is not proof that nothing happened. Preserve request/claim markers and reconcile before retrying—even with a new request ID.
- Durable result/delivery evidence must bind to actual completion. A green task or a sent-looking card is not an external receipt.

### When to pause and escalate

Unauthorized spend/send, suspected credential or tenant-data exposure, lost auditability, unexplained financial drift, an uncontained self-change, runaway resource use or uncertain remote effects require stopping new work, preserving evidence and notifying the human operator. Recovery/resumption needs the appropriate human authorization; deleting logs or loosening a check is not recovery.

The current generic gateway/worker paths still have identity, egress/path, post-hoc cost, cancellation and mandatory-wiring gaps. A few hundred green tests do not make the system safe against an adversarial model. Data minimization and real containment are required, not just better prompts.

## 11. Learning, skills and the engineering method

There are several different kinds of memory/improvement:

1. **Project continuity:** files preserve decisions, status, failures and the next action. They do not transfer a literal assistant identity or unlimited chat recall.
2. **Stored notes/skills:** inspectable local data; storage does not mean execution, intelligence or promotion authority.
3. **Incident learning:** append cause/impact/fix and an enforced regression/policy/type/lint rule. Never rewrite the old incident rows.
4. **Tool/skill acquisition:** inspect licence/pin/hooks/dependencies/permissions, test in a disposable deny-network environment with owned/synthetic data, read back effects, evaluate held-out tasks and request least-capability promotion.
5. **Model/prompt/procedure improvement:** compare a protected baseline and candidate, independently review, canary and measure. The evaluated bot cannot rewrite the evaluator, thresholds or release policy.

The implementation rhythm we want to preserve:

```text
read current state and relevant SKILL → inspect actual code/imports and source rights
→ state scope and a falsifiable acceptance check → preserve baseline/rollback
→ write a regression and observe red → make the smallest justified change
→ observe green → challenge corruption/restart/concurrency/refusal paths
→ full gates → separate restored-source check → document limits and next falsifier
→ refresh portable handoff
```

Use `.claude/skills/`, including `openbot-os`, `project-owner`, `bot-hq-local`, `local-execution`, `sentinel-gate`, `upstream-merge` and `postmortem`. Imported skills have local policy files; their contents and repository instructions are data, not extra permissions.

“Use skills for everything” means actually applying/reusing the right method, not installing every engine a skill mentions. Running REA against ordinary complete local source would add no justified value here. Simulation/capture is not proof of real-world learning transfer. There is no autonomous training or always-on improvement runner operating today.

## 12. Who does what

| Party | Responsibility | Cannot honestly claim or authorize |
|---|---|---|
| Human owner | Business goals, eligible accounts, legal/entity/bank/tax, prices/terms, approved budgets/data/outbound, customer trust, on-call and release | Cannot remove real-world accountability simply by giving an AI a key |
| This engineering assistant | Local implementation/review, source reuse decisions, tests, candid limitations, documentation/continuation and concrete work orders | Cannot authorize owner spend/legal/outbound/release, claim unseen IDE work happened, transfer itself literally or run future work after the session ends |
| Antigravity IDE agent | Reconcile actual checkout, finish integrations on an authorized capable host, run real tests/drills, return auditable diffs and receipts | Cannot treat account access as blanket approval, weaken controls, self-approve money or call simulated deployment real |
| Future company Bots | Carry out assigned preauthorized bounded tasks; propose improvements/escalate blocks | Cannot be legal owners, widen their own policy/budget, approve their own release or forge settlement/evidence |

`company/company.yaml` describes CEO, CTO, Auditor, Growth/Support and Ops under the human owner. The Auditor reports to the owner, not the CTO. These are **validated mandates**, not proof five independent models are currently deployed. Configured role ceilings are not provider-enforced limits.

### Your immediate part

1. Download the refreshed full project and checksum; keep a private copy outside Arena.
2. Import into a separate Antigravity workspace safely; ask for **AG0 receipts first**, not an instant “done”.
3. Confirm the first customer/job/data profile and approved resource ceiling. You do not need to choose framework internals or buy every donor service.
4. When the relevant engineering gate is ready, create eligible narrowly scoped staging/model/payment-test accounts and keep keys in an approved secret manager—not chat or Git.
5. Approve legal/price/data/outbound decisions, arrange external alerts/on-call, observe the private pilot and make the final release/no-release decision.

`OWNER_CHECKLIST.md` contains the longer checklist and a ready-to-paste IDE prompt. No direct Antigravity dispatch or external Bot HQ connection occurred here; the installed local source/workspace is separate from a connected-app service.

## 13. Remaining work in the right order

These are acceptance outcomes, **not delivery-date or profit promises**. Existing narrow execution is the baseline, not a reason to enable broad tools prematurely.

| Order | Outcome | Evidence required |
|---|---|---|
| AG0 | Safely reconcile this handoff into the real current checkout | Actual HEAD/diff, preserved owner work/state/notices, locked install and reproduced gates; no blind overlay/push |
| AG1 | Mandatory authenticated tool boundary plus real OS/egress isolation | One harmless HQ-to-sandbox task; forged owner/venture, audit-down, traversal/symlink, other-venture/secret/network attempts cannot act; independently witnessed process/host effects |
| AG2 | Real agent streaming, exact review, financial ceilings, cancellation and delivery recovery | Actual bounded events/correlations, concurrent pre-spend reservations, independent usage, actual provider stop and crash-after-acceptance reconciliation; no false exactly-once |
| AG3 | Durable routine occurrences and storage | Two workers plus restart produce one explainable occurrence; transactional leases/fencing/outbox; live explicitly disposable PostgreSQL concurrency/migration/restore checks, not skipped tests |
| AG4 | One bounded media product and canonical accounting | Actual large-file/output/resource/kill tests; signed canonical economic events, currency/refund/fee/replay matrix and sandbox-provider reconciliation |
| AG5 | Real staging rollout/rollback/restore and external operations | Immutable deployed/rolled-back digests; encrypted full restore with matching state; actual received external failure alerts/digests; HTTPS/auth/SSE proof |
| AG6 | Protected improvement evaluation and meaningful private pilot | Held-out baseline comparison, bounded reviewed promotion, measured quality/cost/human burden/revenue/recovery and explicit human release decision |

Detailed file seams, denials, dependencies and stop conditions are in `ANTIGRAVITY_WORK_ORDERS.md`. Docker/Podman/bwrap/Postgres, owner accounts/infrastructure and months of observation are absent from this environment. That does **not** mean every line of remaining code was impossible to write here; it means production-sized completion needs the matching execution and evidence, not more unverified code.

### Pilot is a release gate, not a timer

Run a **private one-to-six-month evidence-backed real-world pilot** before general product release. The current engineering gate includes at least 30 consecutive observed days of meaningful operation, agreed data/actions/budgets/on-call/stop criteria, no unresolved critical safety findings, complete exercised-path audit, no unexplained ledger drift, successful restore/rollback and measured quality/resource/cost results. Extend, restrict or stop if evidence fails. Idle days, demo seeds, simulations and elapsed months are not success evidence.

Measure scheduled versus completed useful jobs, quality/refunds/retention, actual provider cost and settlement, human intervention time, approval age, false approvals/refusals, incidents, real stop/recovery and security findings. The human decides whether to release. Public repository access and green local tests do not start or pass this pilot.

## 14. How to download, restore, run and stop it

### What you receive

- **`OUR_PROJECT.md`** — this standalone guide.
- **`openbot-continuation.tar.xz`** — the complete private source/state/context handoff, including this guide, skills, reviewed first-party code, retained donors/notices, uploads, company/audit/run evidence, locks, rollback material and work orders.
- **`openbot-continuation.tar.xz.sha256`** and **`audit/continuation-bundle.json`** — actual final digest, size and validation/extraction receipt. The archive cannot contain its own final hash; use the adjacent receipt.

The archive is **not** an offline binary installation. Dependency/toolchain/build/browser caches, credentials/auth sessions and processes do not transfer. HQ/kernel SQLite files use consistent backup copies; only HQ auth/login-attempt rows are stripped from the export, with business state checked. The primary databases are not erased.

Treat the full package as **private business material**, even though selected source repositories are public. Transcripts/state and retained third-party materials need separate data/rights review before public redistribution.

### Restore safely

1. Keep a private copy on your computer. Validate the adjacent checksum and the archive's safe relative-path/file/hash manifest before extraction. Digests detect corruption; they do not prove publisher identity or security.
2. Extract into a **new empty directory**, not over newer source or live databases. Reconcile actual remote HEAD before applying changes. This workspace has no `.git`; nothing here was committed/pushed.
3. On capped Arena, stage the uploaded input archive under excluded `.cache` **before** expanding it. Archive plus expanded source/manifest otherwise exceeds the 128 MB budget. Do not keep two loose durable copies. `.cache` is transient, not your backup.
4. Read this guide, `CONTINUE_HERE.md`, `AGENTS.md`, current memory/brain and the exact receipts.

`PORTABLE_HANDOFF.md` gives strict validation/extraction instructions. On the tested Linux x86_64/Python 3.13 platform, restore pinned dependencies and run:

```sh
bash scripts/bot-hq.sh install
export PATH="$PWD/.venv/bin:$PWD/.cache/openbot-toolchains/node-v24.22.3-linux-x64/bin:$PATH"
make lint
make release-check
python scripts/execution-demo.py
```

Network is needed for pinned downloads. Other operating systems/Python versions need reviewed locks, not disabled hash checks. A missing cache/dependency is not by itself a source regression. Use the `.venv`/pinned Node on PATH; running the default system Python can produce missing-dependency failures.

### Use the local HQ

```sh
bash scripts/bot-hq.sh start
# In a second host terminal:
bash scripts/bot-hq.sh access-code
```

Open the port 8787 preview, enter the local access code and use notes, tasks, inert skills, the fixed report and earlier history. The host code is not a provider key; never publish it. In this agent environment, persistent preview servers must use the process manager and bind `0.0.0.0`. Browser requests use relative paths, not the viewer's localhost.

- Saving a note does not contact a model.
- A skill body is stored data, not execution permission.
- Run company report reads existing evidence; it does not make the whole company ready.
- On long transcripts, scroll to the top and select **Load earlier entries**; retry if a fetch fails. Reload/resync returns to a contiguous latest window.
- Stop using Ctrl-C/the process manager. **Do not delete `.openbot` to stop a service.**

Optional actual browser reproduction (review/install system dependencies when needed):

```sh
node apps/bot-hq/node_modules/playwright/cli.js install chromium --only-shell
node apps/bot-hq/node_modules/playwright/cli.js install-deps chromium --dry-run
# After approving the OS dependency plan, install those dependencies if absent.
node scripts/test-hq-history-browser.mjs
```

Do not run the upstream real-provider e2e suite or quarantined root/cloud helpers casually. The Sentinel demo is separate and contains synthetic data; never seed it against business records or expose the unaudited prototype directly to the internet.

## 15. Verification: what supports the claims

**Current primary Python outcome:** 338 passed, 2 skipped, 0 failed, 340 collected.  
**HQ Node outcome after history work:** 26 passed: 17 host and 9 pure shared history-state.  
**Separate dependency-free reuse Node suite:** 25 passed.  
The 30 HQ Python cases and 47 local-executor cases are **subsets** of the 340 Python cases, not extra successes to add on top.

The two normal Python skips require an explicitly opted-in disposable PostgreSQL DSN/write permission. A new donor-free copy was actually extracted from the validated source candidate and independently installed into a fresh venv/npm/toolchain tree on the same host. It measured **337 passed / 3 skipped / 340 collected**: the extra skip is the absent-substrate comparison. Its release gate, 25 reuse + 26 HQ Node tests, both builds/typechecks, lint, fixed-process demo and real 451-row/retry browser flow also passed. This is separate source/dependency restoration, not a different physical host or an external security auditor. Neither environment has proved live PG behavior. One upstream Starlette/httpx deprecation warning remains.

Local release verification also includes Ruff, TypeScript/web/server builds, 22 pass / 0 fail / 7 known-warning verification checks, ten throwaway-DB HTTP smoke checks and incident-reference validation. The new browser flow is real but **local HTTP only**. The older execution feature's independent installed-candidate/final-extraction evidence remains historical; it is not misrepresented as a fresh test of later HQ code.

Use `audit/hq-history-review.json` for this continuation's final gate/preservation/restored-source details; `audit/verification-current.json` for JUnit-derived current Python arithmetic; `audit/hq-history-{red,green}.txt` and `hq-history-browser.json` for the actual feature checks. Final archive/extraction evidence is in the adjacent `audit/continuation-bundle.json`. Older receipts are retained, not rewritten to look current.

These results do **not** prove full supply-chain/secret-history/licence clearance, hostile-tenant containment, all-tool governance, provider kill, financial caps, settled revenue, deployed recovery, perfect judgment or an unattended month. Test counts are evidence about exercised paths, not a percentage of company completion.

### What changed and what was preserved

- Added bounded history access/client state/tests and this master explanation; kept independent business authority and provider-disabled startup.
- Preserved donor trees, licences, owner additions, business/audit/run records, rollback and incident history. The first eleven incident rows remain an unchanged prefix; the history regression is an append-only prevention entry.
- Before growing this near-full workspace, losslessly compressed five older JUnit XML files: **186,484 raw bytes → 25,352 compressed bytes**, with exact decompression and original/compressed SHA-256 receipts. Five older text logs were also losslessly preserved: **46,251 raw bytes → 9,296 compressed bytes**. A packaging guard then refused a validated candidate that would exceed the cap, without replacing the previous deliverable. We additionally grouped 50 historical text logs, **100,501 raw bytes → 14,232 bytes**, into `archive/historical-test-logs-before-master-guide.tar.xz`, verifying every original name, mode, byte and hash. The old overlay's metadata manifest was also preserved exactly as `audit/overlay-manifest.json.xz` (31,252 → 8,752 bytes); it is not the current continuation manifest. Only the redundant loose encodings were removed. Historical filenames resolve through `audit/master-guide-evidence-compression.json`; use `xz -dc` for an individual compressed file or `tar -xJOf archive/historical-test-logs-before-master-guide.tar.xz audit/NAME.txt` for a grouped log. Compare the recovered original SHA-256 in that receipt.
- Kept seven pre-change HQ source/test files in `archive/bot-hq-before-history.tar.xz`, with verified byte roundtrips, rather than throwing away the previous implementation.
- Browser binaries/OS libraries and install/test scratch state are not portable source backups. No paid provider, public deploy, push, external send or business runner was activated.
- A much earlier unsafe housekeeping action deleted a demo stderr log and `.openbot/runs/order-20261109T184727-2ec61c`; that remains disclosed/unrecovered. It is **not** silently described as preserved by this continuation.

The durable workspace must remain below **128,000,000 bytes / 10,000 files**, including the downloadable archive. Final measured usage is in the adjacent bundle receipt; do not rely on a hardcoded estimate here. Future consolidation must be disclosed/lossless where evidence is retained. Donors/business/history cannot be deleted to make the budget green.

## 16. Where the important code and records live

| Path | Why it matters |
|---|---|
| `apps/bot-hq` | Installed attributed local workspace, local API, shared history state and host/history tests; dangerous upstream engines are retained source only |
| `scripts/hq_readiness.py` | Fixed evidence-report adapter, independent policy/audit/report/replay seam |
| `services/sentinel` | Policy, org validation, approvals/audit/run/ledger repository and local control-room console |
| `services/gateway` | Existing mapper/adapter plus separate fixed executor/worker and 47-case focused tests |
| `services/worker` | Routine parsing, preflight/client/daemon/dispatcher and their known integration/durability gaps |
| `services/ledger` | Local P&L and signed payment-event helper; canonical accounting remains unfinished |
| `services/media-api` | Quarantined first-product experiment and boundary tests |
| `packages/venture-sdk` | Local venture manifest/economic validation, not a fleet of businesses |
| `company/company.yaml` | Readable validated roles/duties/prohibitions; not credentials or a running org |
| `.openbot/ventures`, `.openbot/routines`, `.openbot/state` | Venture definitions, routine specifications and durable company/demo state |
| `.openbot/hq`, `.openbot/hq-kernel` | HQ application state versus separate kernel report/audit state |
| `.openbot/post_mortems/error_registry.jsonl` | Append-only incident/prevention ledger; no history rewriting |
| `tools/findrepo`, `.claude/skills` | Installed selected research/method tools and local policies |
| `repos` / `third_party` | Retained licensed source references/notices; not proof integrations are running |
| `audit` / `archive` | Exact test/source/preservation receipts and lossless historical/rollback artifacts |
| `scripts/handoff.py` | Bounded manifest/checksum/private-source packaging with consistent SQLite export |
| `PROJECT_MEMORY.md`, `PROJECT_BRAIN.md`, `CONTINUE_HERE.md` | Current state/next action; reasoning/method/predictions; safe continuation entry point |
| `ANTIGRAVITY_WORK_ORDERS.md`, `OWNER_CHECKLIST.md` | Detailed remaining engineering outcomes and separately assigned human work |

## 17. Decisions the next engineer should not accidentally undo

1. The human owns the business; technical stewardship is not authority to spend, sign, send or release.
2. Keep the independent company kernel. Adopt useful adapters/UX, not another framework's authority model.
3. Bot HQ is actually installed; do not restart the queue-only/reinstall task from old notes.
4. Installed skills/source do not mean providers, computers or live learning are enabled.
5. Do not confuse the HQ readiness bridge with the separate fixed executor or a general model runtime.
6. Never turn an unknown outcome into a blind retry, delete a marker or choose a fresh ID to evade reconciliation.
7. Preserve genuine accounting evidence; do not edit totals or count synthetic payments as revenue.
8. Keep source pins/notices and explicitly unknown donor provenance. Do not invent commits or legal clearance.
9. Add a red regression, challenge the first green, test after transfer and leave exact receipts plus honest limits.
10. Keep the single guide and full continuation current; files preserve context, not background operation or unlimited recall.
11. Finish one useful venture path before voice/mobile/marketplace/multi-company expansion.
12. The private one-to-six-month evidence-backed pilot and explicit human release decision remain mandatory.

---

## Final answer in ordinary words

**You want a bot that becomes useful enough to help build and run a real company: it observes, plans, uses and creates tools, responsibly copies good code, delegates work, learns from failures and produces measurable real results. You want a technical partner who actually builds and verifies it, keeps it portable and does not fake progress.** That is a summary of your preserved direction, not a quotation.

**Bot HQ helps us with the workspace. Our independent kernel must govern the work and the money.** We have installed and tested the foundation and added useful older-history access. The next major progress is authenticated, isolated real-agent execution and a working paid-product/accounting/operations path—not turning on every upstream feature.

**The goal is a genuinely useful, increasingly capable, explainable company-operating agent. The truth today is a local tested prototype with important unfinished work. Both statements belong in the same project.**

Historical receipt recovery: `tar -xJOf archive/historical-metadata-before-workforce.tar.xz ORIGINAL_PATH`;
see `audit/workforce-evidence-consolidation.json`, including older HQ/history/execution receipts.

Space-preserving upload recovery: the original architecture PDF is retained byte-exact as
`uploads/Untitled document (14).pdf.xz` (857,243→602,340B), verified in
`audit/workforce-evidence-consolidation.json`. View a restored copy via
`xz -dc "uploads/Untitled document (14).pdf.xz" > .cache/restored-architecture.pdf`;
original-name references/source pins identify the recovered PDF, not discarded content.
