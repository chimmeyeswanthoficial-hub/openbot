# Foundation decision: keep the company kernel; reuse Bot HQ selectively

> **Scope update:** the owner explicitly requested actual Bot HQ installation after this review.
> `apps/bot-hq` now contains the pinned, attributed local-only profile and a real independently
> audited company-report task. See `BOT_HQ_INSTALLATION.md` / `CONTINUE_HERE.md` for current status.
> The queue-only recommendation and verification totals below are the **earlier review checkpoint**,
> not the current installation inventory. Kernel retention, excluded-artwork rules and all human/
> private-pilot gates remain. No provider-enabled runtime migration has been proved or authorized.

**Decision:** retain **OpenBot OS's independent governance, ledger, venture model and routines**.
Keep OpenBot/AG-UI as the current, replaceable workspace/runtime integration target. Do **not**
replace the project wholesale with Bot HQ. Take useful, appropriately licensed modules through
small adapters. No host migration, remote push, deployment or public product launch occurred.

The owner has made `openbot` and `findrepo` public and authorized this review/reuse. That reverses
the earlier source-privacy instruction—not the human-controlled spending/legal decisions or the
**one-to-six-month private real-world pilot before general product release**.

**Review label:** public-source intake, session date 2026-11-10. Upstream's `HANDOVER.md` is labelled
2026-11-13; its date is retained as an author-provided label, not an independently verified execution
chronology. Exact commits and measured commands, not document dates, identify the evidence.

## 1. What was actually examined

| Source | Immutable revision / evidence | Scope and limit |
|---|---|---|
| [Owner's current OpenBot OS](https://github.com/chimmeyeswanthoficial-hub/openbot/tree/a67fb041763bdfd16ed8b77f0ad24edd8e154f20) | `a67fb041763bdfd16ed8b77f0ad24edd8e154f20` | Actual nested first-party source, handover, test code, selected runtime paths and full Python suite; not a complete audit of every donor/dependency |
| [Owner's findrepo](https://github.com/chimmeyeswanthoficial-hub/findrepo/tree/4d512682b8e30cfcbda2a7f74f44ae76df9ed77a) | `4d512682b8e30cfcbda2a7f74f44ae76df9ed77a` | MIT skill/CLI, IO/credential/cache/instruction-write boundaries and scoring tests |
| [Bot HQ](https://github.com/nickvasilescu/bot-hq/tree/decf9a215cddd8792a5f20f4a11a87d4dffa6d15) | `decf9a215cddd8792a5f20f4a11a87d4dffa6d15` | README, code/artwork licences, manifests, architecture and selected queue/MCP/approval/memory/routine/UI seams; no whole-host install/build/provider run |
| [REA](https://github.com/morluto/rea/tree/cdc4541ef707f256f83abe5018df01a25182cf0b) | `cdc4541ef707f256f83abe5018df01a25182cf0b` | Instruction skill v62, reference inventory, practice-environment workflow, licence/disclaimer; not a full engine audit or runtime execution |
| Owner's PDF | `uploads/Untitled document (14).pdf`; digest in `audit/source-pins.json` | All 3 pages / 8 embedded images visually reviewed. Stack diagrams and IDE reconstruction prompts, not runtime proof |

The PDF points to Grok-style UI/voice/X research, Hermes, Orgo, Composio and additional services.
The inspected Bot HQ code supports some of that composition; screenshots do not establish that
all depicted services are integrated. I have **not watched the entire 36-minute video** or obtained
its complete transcript. No claim here depends on having done so.

## 2. Why this is the better foundation decision

| Criterion | Keep independent kernel + selective reuse | Wholesale Bot HQ migration |
|---|---|---|
| Business-specific behavior | Preserves tested policy decisions, idempotent ledger, venture validation, routines, incident rules and maintenance | Would still need all of those ported; chat/tasks/memory are not company accounting/governance |
| Execution safety | Allows an external enforcement boundary that neither the UI nor agent can relax; **not yet complete** | Upstream approvals cover Composio writes, not browser/shell; a shared Orgo computer is not venture/tenant isolation |
| Model/workspace coupling | Keeps AG-UI/runtime adapters replaceable and finance outside either host | Current composition centers Hermes gateways, Orgo, Composio and xAI; different storage, event and runtime contracts |
| UI and collaboration | Existing control room works; Bot HQ's queue/transcript/live-state patterns are useful donors | Attractive coherent UI, live screens, tasks and voice—but that does not close business/security gaps |
| Licence and operating costs | Our kernel stays independent; verify any optional substrate/service licence before operating | MIT code can be reused; **some artwork is expressly excluded**, and providers/accounts have separate terms and costs |
| Migration evidence | Local Python behavior is executable and reviewed; current-source additions can be preserved incrementally | No proven build, workload isolation, model/provider access or cost advantage in this environment; Node 20 does not meet full host's Node >=22 requirement |

**Not a claim that OpenBot is universally superior.** CopilotKit Intelligence is separately licensed;
the existing OpenBot stack is not a proven free, fully running company engine here. We do not copy
Intelligence or assume its learning services are available. If a later disposable, governed workload
shows a Hermes/Bot HQ adapter is materially simpler or better, it can replace the workspace/runtime
adapter without replacing the ledger or policy authority.

**Reconsider migration only after** the same bounded task runs through both candidates with real
intercept-before-side-effect enforcement, independent accounting, stop/restart tests, tenant isolation,
licence clearance and measured total cost. Screenshots, larger test totals and sunk effort are not
selection criteria.

## 3. Antigravity reconciliation: useful work, overstated completion

I independently reproduced the current remote result: **214 passed + 2 skipped = 216 collected**.
Direct `ruff check services packages scripts` returned **24 findings**. The remote Makefile masks
lint failures and its old clean target deletes business data. Neither behavior was adopted.

| Task | Actual evidence | Honest status after this intake |
|---|---|---|
| T1 worker → Sentinel | HTTP client and daemon exist. The remote Worker only recognized `decision=deny`, while the real endpoint returns `effect`; gate/unknown responses could queue | Fail-closed normalization repaired, with synthetic verdict regressions and an in-process real-response contract test. Real persistent unattended operation still unproven; unscoped platform routines require explicit policy |
| T2 substrate → governance | Mapper/adapter have unit tests, but no inspected OpenBot server call site invokes the Python gateway | **Not end-to-end complete.** Add a real mandatory execution hook; unknown tools, trustworthy initiator/venture identity, browser/shell/file paths and exact approval binding need adversarial tests |
| T3 worker → real Bot | `AGUIDispatcher` exists but no production Worker call site invokes it. Transport expects ordinary JSON, not demonstrated AG-UI event-stream handling | **Not complete.** HTTP timeout does not cancel remote work; post-response cost checks do not prevent spending; formatted outputs are not proven channel delivery |
| T4 Postgres | Optional backend code and 2 PG tests exist | Both tests skipped. No Postgres runtime, crash/reconnect/transaction/migration or production role test. Tests now require explicit disposable-test DSN + write opt-in, never inherited production DSNs |
| T5 billing | HMAC helper, handler and replay unit tests exist | Repaired a concrete unsigned-write defect: absent signing secret now disables the webhook. Currency, canonical economic-event deduplication, cumulative refunds/fees and provider reconciliation still block real accounting |
| T6 first product | Convert/compress append all input chunks in RAM before joining. ffmpeg writes stdin before draining stdout/stderr and lacks reliable error/timeout/cancellation cleanup. Segment output was mocked | **Experimental, disabled by default**; explicit experiment flag plus token required. `/split` now returns 501 rather than fake success. Not a finished streaming business product |
| T7 deploy/rollback | Original implementation only edits JSON and prints success; no image rollout, reversible migration check, health gate or actual rollback | Relabelled/quarantined as **record-only simulation**. CLI refuses without `--record-only`; no infrastructure changed. Real T7 remains open |
| T8 monitoring | Heartbeat helper called from worker tick | Tests mock the network. No external monitor/on-call delivery or missed-heartbeat recovery drill performed |
| T9 approvals | Digest formatter and console age banner exist | Useful UI/formatting; no verified scheduled digest delivery to a human or end-to-end escalation |
| T10 onward | No meaningful long-running pilot evidence | Still open; preserve human gates and independent evaluation |

### Regressions actually demonstrated before repair

- Worker verdict + missing-webhook-secret checks: **8 failed / 1 passed before**, then repaired.
  The unsigned test created only a synthetic row in an in-memory test database, not real revenue.
- Deployment/media quarantine checks: **7 failed before**, then repaired.
- Local findrepo safety checks reproduced inherited-token transmission, authenticated public-cache
  writes and unapproved instruction-file edits; all are blocked by default in our local port.
- The old documentation guard equated *collected* with *passed*. It has been replaced with
  JUnit-derived pass/skip/fail arithmetic, actual collection and explicitly current document rows.
  Historical measurements are retained as history, not forced to equal today's collection.

These fixes do **not** make the gateway a security sandbox. Host-level least privilege, egress,
filesystem isolation, credential separation, durable budget reservations and protected evaluators
remain release blockers. The present policy has incomplete handling of raw shell/browser actions
and normalized filesystem paths; passing matcher tests cannot certify those boundaries.

## 4. What was adopted—and what was not

### Preserved current project work

Reviewed first-party `services/`, SDK, deploy tests/simulator and Python path configuration were
brought into this local workspace. Our 15 maintenance regressions, safe clean/mirror scripts,
strict lint behavior, smoke repair and business state were retained. No remote `.openbot` state,
customer data, budgets, deployment history, donor tree or Git metadata was overlaid.

- Pre-intake source rollback: `archive/handover-before-public-intake.tar.gz`.
- File-level source provenance: `audit/antigravity-intake.json`.
- Immutable inputs: `audit/source-pins.json`.
- Portable reviewed source: `openbot-reviewed-overlay.tar.gz`; extract into an empty review
  directory and compare with the actual current remote HEAD, not blindly over a newer checkout.
  `audit/APPLY_LOCAL_CHANGES.md` explains preservation and ID-checked incident append.
- No remote branch/commit/tag/push or deployment was performed. The public repository does **not**
  automatically contain these local fixes.

### Installed findrepo

`tools/findrepo/` contains the owner's zero-dependency CLI, licence and tests;
`.claude/skills/findrepo/` contains its skill and a forwarding script. Run
`bash scripts/findrepo.sh ...`. Version 1.1.0 and an unauthenticated public `inspect` lookup were
successfully executed. No npm install, global hook or instruction-file initialization was needed.

Local safety patches require explicit opt-in for account credentials/`gh` auth, prevent shared
public caching of authenticated responses, and disable instruction-file writes by default. Read
`.claude/skills/findrepo/LOCAL_POLICY.md`; search results/scores are triage, not security approval.

### Installed Bot HQ code port, not its host

`packages/bot-hq-queue/serial-queue.mjs` adapts the MIT per-bot serial queue from
`server/src/agent/loop.ts`. It has 5 executable tests for ordering, cross-bot concurrency, failure
recovery, close/drain and input validation. It is a tested runtime-adapter building block, **not yet
wired into Worker/OpenBot**, durable queueing, tenant isolation or a provider kill switch.

MIT copyright, original excerpt and artwork exclusions are retained in `third_party/bot-hq/`.
No avatars, eyes, original UI icons/app tiles, favicon, logos or Grok-branded artwork were copied.
No full Bot HQ dependencies were installed and no whole-host build/e2e/provider claim is made.

### Installed REA instructions, not its analysis engine

`.claude/skills/reverse-engineer-anything/` contains pinned skill v62, all 8 references, MIT licence,
disclaimer and third-party notices. Its own guidance says **skip REA for ordinary complete-source
architecture analysis**, so no unnecessary REA engine was run for these repositories.

The practice-world guide informed the bounded-learning plan: disposable seeded first-party app,
explicit write permission, declared/redacted secrets, read-back-confirmed state changes, coverage
and withheld-write reporting, held-out evaluation and a simulator-to-real check. A captured world is
not a general learning engine. Runtime/MCP/providers are **not installed or registered**; Node/runtime
compatibility, package pinning and a concrete authorized target precede that separate step.

## 5. Verification and retained evidence

Exact current Python arithmetic is generated from completed JUnit into
`audit/verification-current.json` and displayed in `README.md` / `PROJECT_STATE.md` / `CHANGELOG.md`.
The final command receipts and limitations are recorded in `audit/FINAL_VERIFICATION.md`.

`make release-check` now includes **25 offline Node tests**: findrepo's 16 upstream cases, 4 local
credential/cache/write boundaries and 5 Bot HQ queue cases. No external provider is required.
Postgres skips are reported as skips, not passes. A donor-free copy adds a substrate-comparison
skip; that is not evidence the donor runtime works.

The shallow current-tree secret heuristic scanned **8,695 eligible text files**, found no sensitive
filename candidates and returned 20 pattern candidates, mostly fixture/demo/scanner literals. No
live credential was confirmed. This is **not full-history scanning or public-source clearance**.
Before a production pilot: independently inspect all reachable history, large/binary files,
submodules and dependencies; rotate/revoke any real exposure. Public source is not a secret store.

## 6. The next engineering bottleneck

**Execution follow-up:** a separate fixed trusted-host local slice now exists with real process/SSE,
exact drafts, transactional attempt quota, kill/reap and scoped digest-bound delivery/replay.
`EXECUTION_SLICE.md` and `audit/EXECUTION_FINAL_VERIFICATION.md` define its tested limits.
It is not HQ/Worker/HTTP/live-model wiring, OS isolation or financial hard limits. Current ordered
work: `ANTIGRAVITY_WORK_ORDERS.md`; human work: `OWNER_CHECKLIST.md`; retained donor assessment:
`DONOR_REUSE_REVIEW.md`. The earlier acceptance ladder below remains for broader runtime coverage:

Build **one disposable end-to-end governed execution slice**, not another dashboard or a bigger
skill catalogue:

1. A trusted venture/actor identity enters the chosen runtime adapter; independent Sentinel records
   a decision before any side effect. Only explicit, well-formed audited `allow` can continue.
2. Test a harmless local tool, a browser egress denial, a cross-venture/path-traversal denial and a
   sensitive send/spend gate. Never perform the sensitive side effect during the test.
3. Reserve budget transactionally before paid work. A real cancel/kill mechanism must stop work;
   a client timeout or a UI label saying “killed” is not cancellation.
4. Consume actual AG-UI events, correlate run/tool/approval IDs, deliver the output, reconcile
   observed cost and prove restart recovery without duplicate actions.
5. Keep raw credentials, protected evaluator and deployment authority outside the bot's writable
   workspace. Queue ordering is not isolation. Policy/permission changes require human approval.

Only after that slice is independently witnessed should Media API be completed in a sandbox,
provider test payments reconciled, backup/restore and external monitoring drilled, and the **private
1–6-month real-world pilot** started under agreed budgets and human on-call coverage.

**Bottom line:** the useful thing in Bot HQ is its composable agent experience—not a reason to
throw away the company's control/accounting kernel. Preserve Antigravity's work, correct what the
evidence disproves, and make one real governed task work before expanding autonomy.
