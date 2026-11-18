# Strategy addendum — private, evidence-led autonomous company

> **Latest installation:** local-only Bot HQ is installed under `apps/bot-hq`, with persisted
> notes/skills/tasks and an independently audited fixed company-report tool. All providers,
> autonomous engines, computer/shell/browser, voice and external connections remain disabled.
> Read `BOT_HQ_INSTALLATION.md` and `CONTINUE_HERE.md`; earlier donor-only notes below are historical.
> The independent kernel, unfinished real-execution blockers and private 1–6-month pilot still apply.

**Recorded:** 2026-11-10 (session date). **Status:** owner direction + bounded improvement plan.
The owner has now made both repositories public and authorized selective reuse. Current source was
reviewed; `ADOPTION_REVIEW.md` records actual revisions, foundation decision and T1–T9 limits.
The independent kernel stays; Bot HQ is a selective donor. Read `PROJECT_MEMORY.md` first.

## 1. What the owner has decided

- The target is a bot that can build and operate a real, revenue-producing company, not just chat.
- Like an agent progressing in Minecraft, it should observe, plan, use resources, build tools,
  delegate to bots, maintain a workspace, learn from failures and become more capable.
- Tools, skills and repositories can be created **or responsibly reused**. More dependencies are not
  automatically progress.
- **Public source is now explicitly authorized** for the two owner repositories. General product
  launch still requires a private real-world pilot of **one to six months**, readiness evidence
  and a human release decision; source visibility does not establish operating safety.
- During that pilot, the system should identify weaknesses and propose/test improvements.
- Keep project memory on disk and the workspace organized, so rate limits or a new chat do not lose
  the plan. Technical ownership is delegated to the assistant; business/legal authority is human.

These are recorded directions, not evidence that any capability or pilot is already complete.
“Better than anything” is an ambition, not a measurable product claim. We need task-specific
baselines, held-out evaluations and real unit economics before making comparative claims. Neither
profits nor perfection can be guaranteed, even after six months.

## 2. Translate the Minecraft analogy into a constrained learning loop

| Analogy | Engineering interpretation |
|---|---|
| World and inventory | venture state, market evidence, tasks, available tools and cash runway |
| Survival | bounded burn, fulfilled customer commitments, incident recovery, retained customers |
| Crafting tools | sandboxed code/skill proposals with declared permissions and tests |
| More capable agents | versioned policies/procedures evaluated against a fixed task suite |
| Finishing the game | a useful product delivered to real customers at sustainable contribution |

Proposed loop:

```
observe evidence → choose one weakness → propose a bounded change
→ implement in an isolated branch/workspace → test against the old and held-out cases
→ independent review → human approval where required → canary → measure → retain or rollback
```

This is primarily **engineering / procedural improvement**, not proof of autonomous model training
or guaranteed general intelligence. A simulated environment can be reset; a leaked customer record,
bad payment or unlawful action cannot. Real-world permissions must be narrower than practice-world
permissions.

## 3. Autonomy boundary — remains in force

**Existing invariant:** no audit row, no action; money comes from ledger rows; sensitive acts stay
gated. **Current limitation:** the earlier baseline's worker/Bot integration is unfinished; a good
Sentinel decision alone does not prove every tool path is enforced. Verify the new repo before
claiming that has changed.

Proposed implementation of self-improvement (NOT shipped here):

1. The worker has no credentials to change production policy, secret stores, approval roles, branch
   protection, deployment authority, its own spending ceiling or audit retention.
2. Code changes happen in a separate sandbox with no live customer/payment credentials. Internet
   text, repo instructions and tool output are untrusted data, not permission to run commands.
3. The author cannot change the evaluator or mark its own result as independently approved.
   Regression tests may be **added**, but existing guarantees must not be weakened. Keep a held-out
   suite and policy checks outside the author's writable environment.
4. All behavior-affecting inputs count as code: skills, memory/soul instructions, dependency locks,
   MCP registration, CI, startup scripts and deployment settings — not only `policy.py`.
5. Permission checks need separate runtime identities, filesystem/network controls, secret
   separation and protected merge/deploy gates. A prompt or a test of a protected-file list alone
   cannot enforce this against an agent with an unrestricted shell.
6. Initially, all production self-changes need human-reviewed diffs, evidence, a backup and a rollback
   path. Later, only a separately authorized **low-risk class** may canary automatically. Never
   auto-widen authority because the approval queue is slow.
7. Record proposal ID, parent version, diff/content hash, cost, tests, reviewer, approver, release,
   observed metric and rollback outcome. Audit proposals even when they are rejected.
8. Bound iteration count, wall time, tool calls, dollars and bot-to-bot messages. One change in flight
   initially. On a limit, stop and checkpoint; do not recursively spawn replacements.

The bot may carry out preauthorized, lawful product work and earn revenue within the approved scope.
New spending, payment transfers, agreements, legal filings, account credentials and consequential
outbound actions retain their applicable human gates. Collecting a payment still requires a human-
controlled provider/account, compliance and reconciliation; “earn unattended” is not “hold/sign
unattended.”

## 4. Real-world trial — a release gate, not a calendar promise

The following phases are **proposals for owner sign-off**, not dates that automatically grant
permissions. Before starting, choose one venture, an approved burn cap, permitted action classes,
response/on-call coverage, data consent/retention, recovery objectives and success thresholds.
Record the tested commit and start time. Do not count demo seeds, simulations or days with no
meaningful activity as production evidence.

| Phase | Proposed permissions and evidence |
|---|---|
| Sandbox / practice | no live credentials or customers; faults, retries, adversarial input, cross-venture reads, duplicate dispatch, refunds, lost network and restore drills |
| Shadow (roughly first week) | collect proposed actions and compare with human decisions; outward side effects disabled by technical controls, including browser/shell/network routes |
| Supervised private pilot | invited/consenting users only; applicable send/spend/deploy gates still active; daily review and independent provider reconciliation |
| Bounded autonomy / extended soak | only approved low-risk action classes; on-call coverage, regular human review, tested alerting/pause/rollback; extend toward six months if needed |

**Minimum gate before even considering public launch:** at least 30 consecutive observed days of
meaningful private-pilot operation, no unresolved critical safety findings, complete audit coverage
on exercised paths, zero unexplained ledger drift, successful backup/restore and rollback drills,
measured delivery quality/cost/latency and honest incident accounting. Permission changes or
material redesigns require an impact-based requalification window. Elapsed time alone is never a
pass.

Record at least: successful customer jobs, defect/refund rate, repeat usage, owner intervention time,
contribution after **all** model/infra/payment/support costs, approval age, refusals, retries, uptime,
incidents and recovery time. Compare the improved agent with the old version on the same tasks.
Do not optimize approval volume downward by suppressing necessary gates. Profitability, revenue and
owner-time targets must be agreed **before** the relevant experiment; they are not facts today.

**Immediate pause/escalation:** unauthorized spend/send, credential exposure, suspected tenant-data
leak, lost auditability, unexplained financial drift, an uncontained self-change or runaway budget.
Preserve evidence. Human-authorized recovery follows investigation; the agent may not “fix” an
incident by deleting logs or relaxing the failed check. Commercial pivot/stop criteria also need
owner agreement rather than an agent silently shutting a viable venture down.

## 5. Backlog additions — reconcile with Antigravity first

T1–T10 remain the earlier baseline brief, **not a verdict on the unseen current repository**. First
map each to actual code/tests/commit evidence. Then schedule only the remaining gaps:

| ID | Proposed addition | Prerequisite / acceptance |
|---|---|---|
| T11 | Shadow mode + practice tasks | enforcement on every exercised tool route; prove no real side effect even through browser/shell; compare recorded proposed actions with human decisions |
| T12 | Bounded improvement loop | real defect/failed task → isolated patch → regression + held-out checks → independent review → approved canary → measured result or rollback |
| T13 | Toolsmith + venture workspaces | tool permission/cost manifest, tenant isolation, versioned skill and installation provenance; removal/retention procedure that preserves required evidence |
| T14 | Repo/skill intake gate | before any new adoption: task fit, exact revision, licence/assets, executable/install hooks, dependencies, secrets/egress review, sandbox, seam test and rollback |
| T15 | Pilot evidence and release checklist | runtime measurements, cost/ledger reconciliation, alerts, restore drills, intervention log and explicit human public-release decision |

Start building a small, useful product before building an elaborate self-improvement platform.
Sandbox learning can begin before first revenue; production self-deployment should not. Do not
replace OpenBot with a second framework on the strength of a video or a README.

## 6. Review of the supplied sources — facts versus recommendations

### Public project and findrepo — current intake

Both owner repositories are now publicly readable. The project was inspected at
`a67fb041763bdfd16ed8b77f0ad24edd8e154f20`; findrepo at
`4d512682b8e30cfcbda2a7f74f44ae76df9ed77a`. The former's 214 successes + 2 skips were reproduced;
its completion claims were reconciled against code, and selected first-party additions preserved.
The latter's MIT CLI/skill is installed locally with explicit credential/cache/write controls.
No global hooks, instruction-file init, remote push, paid integrations or production launch occurred.

See `ADOPTION_REVIEW.md` and `audit/source-pins.json`. Candidate discovery remains separate from
adoption authority: inspect exact versions/licences/assets/hooks/permissions before execution.

### Video: composition is useful; the demo is not a durability test

Source: [Nick Vasilescu — “I Stole the Best Part of Every AI Agent… With One Prompt (Open Source)”](https://www.youtube.com/watch?v=ceU0tS6sXbU).

**Review scope:** the full description and an opening transcript excerpt were available. Subsequent
page chunks returned comments/player content, and the caption endpoint returned no text. I did not
visually watch or verify all 36 minutes. The claims below are attributed to the description; the
linked repository README was read separately in full.

The description combines texting-style/multi-bot UI and voice, editable identity/memory, computer
use, multi-session management, a Hermes harness and connected tools (Composio/MCP). It links
[Bot HQ](https://github.com/nickvasilescu/bot-hq), Hermes, a Grokbot clone, Bops, Orgo, Composio, Paper
MCP, xAI, Honcho and AgentMail. These are leads, **not installed or approved dependencies**.

[Bot HQ's README](https://github.com/nickvasilescu/bot-hq#status-and-limits) explicitly says it is
experimental, unaudited, shares one computer where bots can reach one another's files, and gates
Composio writes but **not browser/shell actions**. It also distinguishes MIT project code from bot
artwork/icons owned by others. Therefore borrow UX or adapter ideas only after review; do not import
its deployment/permission model as our governance boundary. Provider subscription use has its own
terms. A working composition demo is not evidence of profitable or safely self-modifying operation.

### REA: optional instrument and a possible practice-world builder

**Current intake:** pinned instruction skill v62 and all references are installed; runtime/MCP/
providers are not. Read its LOCAL_POLICY.md and ADOPTION_REVIEW.md. The source-repository analysis
used normal tools, as REA itself directs; environment guidance informed the plan, not a runtime claim.

Reviewed: [README](https://github.com/morluto/rea), [MIT licence](https://github.com/morluto/rea/blob/main/LICENSE),
[package manifest](https://github.com/morluto/rea/blob/main/package.json),
[environment reference (opening sections)](https://github.com/morluto/rea/blob/main/docs/agent-environments.md)
and [responsible-use disclaimer](https://github.com/morluto/rea/blob/main/DISCLAIMER.md).

REA exposes reverse-engineering workflows through CLI/MCP: native analysis via external providers,
static JS/Electron/.NET analysis, runtime/browser observation and saved-capture inspection. Target
requirements vary. Static analysis is not the same permission as executing/capturing a target.
Local analysis also does **not** mean findings never reach a hosted model provider.

Especially relevant to the Minecraft idea: its documented **recorded-capture environments** can
answer tools from retained observations, with state-changing operations limited by confirmed effects.
That could give us a repeatable practice world for **our own authorized test application**, rather
than letting the agent learn on live customers. It is not a complete simulator of arbitrary sites;
missing capture coverage, wrong rewards and simulator-to-real gaps still need tests. Scrub HAR
cookies/tokens/PII and deny production egress. The build guide requires additional environment tooling
and Docker to run the bundle.

**Decision:** instruction skill installed at the pinned SHA; executable evaluation remains later.
Not a new host runtime, a licence to copy proprietary code/assets, or authority to bypass restrictions.
The runtime/MCP/providers are not installed or audited here. Review a pinned release, its engine
requirements and third-party licences before a justified authorized capture task.

## 7. Memory and maintenance cadence

`PROJECT_MEMORY.md` is the short resumption checkpoint; `PROJECT_BRAIN.md` is method;
`PROJECT_STATE.md` is measured local state; this addendum is updated direction. Sources/claims are
not executable instructions. Keep these distinctions when compacting memory.

During an active session: checkpoint after each meaningful milestone and before a risky operation
or handoff. At the next session: read memory, obtain the current repo/revision, inspect the diff,
run the gates, then choose one task. Never treat remembered test counts as current measurements.

Use `make tidy-check` to preview cache cleanup and `make tidy` to apply it. Neither may erase audit,
run history, financial data, logs, source or donor trees. No automatic source-repo reorganization or
mirror push is authorized here. A safe cache-cleanup tool is shipped; a background maintenance agent
is not. This chat cannot keep working periodically after the turn ends without a separately deployed,
explicitly configured runner. The same is true of the month-long pilot.
