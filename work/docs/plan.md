# OpenBot OS — current master plan

**Owner:** the human. **Technical partner:** the engineering assistant/IDE agent, with candid
architecture judgment but no independent authority over money, identity, legal acts or release.
This plan supersedes the original milestone/install estimates, retained losslessly in
`archive/plan-and-handover-before-execution-refresh.tar.xz`. `audit/planning-consolidation.json`
verifies history. Dates, test counts and running-service claims in old plans remain historical.

**Newer product choice:** owner delegated priorities: human-led QA/documentation pilot first,
owned-footage editing second; transparent company identity and reviewed social drafts only.
`WORKFORCE_PLATFORM.md` defines the offline workbench and quality/rights gates. This supersedes
older Media-API-first wording, not the retained media track or human business authority.
`WORKSPACE_CLEANUP.md` records complete donor-source vaults and verified redundant-copy cleanup.

## 1. Product thesis and actual state

Build a self-hosted company-operating agent that observes, plans, learns/builds/adopts tools,
delegates and operates a narrow venture with explainable actions, costs and genuine settled
revenue. The ambition is useful bounded autonomy, **not** guaranteed profit, perfection, immunity
to repeated mistakes or an unattended legal/business owner.

Implemented locally: independent policy/audit/approval/ledger/venture/routine kernel; authenticated
provider-disabled Bot HQ/report; separate fixed trusted-host wordcount executor with actual process/
SSE/stop/restart/outbox proof; discovery/instruction skills and portable source/state context.
Not implemented/proved end-to-end: general live-agent tool enforcement, hostile isolation,
financial hard limits, canonical provider settlement, production media/deploy/monitoring or pilot.
`PROJECT_STATE.md` and exact receipts, not this plan's aspirations, define completed scope.

## 2. Architecture decisions

| Decision | Working choice and reason |
|---|---|
| Company authority | Independent Sentinel/ledger/venture/routine kernel; financial truth is derived from durable canonical rows, never UI task state or an agent's claimed cost |
| Workspace/runtime | Actual pinned local-only Bot HQ frontend now; OpenBot/AG-UI remains the replaceable real-agent target. Compare a governed workload before switching adapters, not the entire kernel |
| Language/interface | FastAPI/Python for policy and ventures; React/TypeScript/Tailwind UI and explicit AG-UI/event contracts; optional PG/Redis for durable deployment after live tests |
| Infrastructure | Owner-owned Docker-capable Linux VPS, no Kubernetes; unprivileged disposable workload isolation, separately protected secrets/evaluators/deploy authority |
| First paid-pilot target | Human-led QA/documentation first; owned-footage editing second. Retain the Media API track behind isolation/resource/rights gates. Measure quality and COGS before pricing/promises |
| Reuse | Small licensed modules/patterns/tests; installed HQ is not permission to enable its unsafe startup. Rakazo/OpenDots remain valuable reference, not whole hosts to merge |
| Models | Configured reviewed capability tiers, not hardcoded obsolete model names. Model changes are protected-eval/canary experiments, not self-granted upgrades |

See `STACK_DECISIONS.md` for original decisions/reasons and `ADOPTION_REVIEW.md` for foundation
review. CopilotKit Intelligence and provider services have separate terms; root application MIT
licence does not supply an account or clear assets. Current task changes are local/unpushed.

## 3. Governing invariants / threat boundary

1. No durable independent audited **explicit allow**, no effect. Unknown/malformed/unavailable
   governance refuses. The invariant must be wired immediately before every enabled real action.
2. Host-authenticated immutable actor/venture/original initiator and scoped capability—not caller
   JSON or model text—grant authority. Remote owner approval needs real human authentication.
3. Exact reviewed destination/draft/arguments/identity/policy/implementation/amount bound to TTL;
   changed review needs a new decision. Money, credentials, sensitive outbound and release remain
   human controlled. No “approve everything to unblock” workaround.
4. Reserve bounded liability transactionally before paid work; reconcile actual independent usage.
   An attempt quota, a prompt budget and post-hoc cost checks are not financial hard caps.
5. OS/egress/secret/data isolation is independent of the bot. Separate homes, path prefixes,
   process rlimits and HTTP-only proxies are not hostile-code containment.
6. Cancellation means independently observed process/provider stop, not a timeout label. Unknown
   outcomes remain unknown; preserve markers and reconcile before any repeat/new-ID retry.
7. Bind durable events/results/delivery to request and completion evidence. Local outbox recovery
   is not proof of exactly-once external action. Protect raw data and keep audit append-only.
8. Human-accountable business/legal/customer responsibilities stay human across every industry.

## 4. Ordered delivery / definition of done

`ANTIGRAVITY_WORK_ORDERS.md` contains file seams, tests, dependencies and stop conditions:

AG0 safe source intake/reproduce → AG1 mandatory authenticated enforcement + real isolation →
AG2 actual streaming agent/cost/stop → AG3 durable scheduler/PG → AG4 accounting/media product →
AG5 real staging deploy/rollback/restore/alerts → AG6 protected learning/evaluation/private pilot.
Independent work uses disjoint branches; kernel/schema changes are reviewed serially.

A task is done only with a red→green regression, actual governed effect/refusal evidence,
measured resource/cost scope, documented limitations and tested reversal/recovery where relevant.
Run lint/full Python/Node/HQ builds+tests/verify/smoke, refresh real JUnit outcomes and docs, then
repeat in an independent restored environment. Skips/failures are never relabelled as passes.
Keep the whole continuation current after substantive changes. No blind upstream install/push.

## 5. Learning and incident loops

- **Incident:** append cause/impact/fix and enforce the earliest catching test/policy/type/lint.
  Preserve old registry bytes. A `rule_ref` path alone does not prove semantic prevention; run it.
- **Verification:** different reviewer from implementer; adversarial boundaries and actual read-back
  of effects. Stop and report after repeated unsuccessful attempts instead of broadening authority.
- **Acquisition:** pin/licence/dependency review → disposable deny-network test with synthetic/owned
  data → trace/read-back → held-out evaluation → human-reviewed least-capability promotion.
- **Model/prompt:** protected baseline/candidate comparisons, safety no-regression and staging
  canary; evaluated bot cannot change evaluator/thresholds/release controls.
- **Business:** reconcile canonical settlement/COGS, sample quality/customer outcomes, compare
  agreed numeric kill criteria, propose scale/fix/stop. Never create balancing revenue or profits.

Skills live in `.claude/skills/`; read the index and task-specific SKILL before work. Installed REA
instructions do not prove learning/transfer; findrepo rankings are not security/licence clearance.

## 6. Human and pilot gates

`OWNER_CHECKLIST.md` separates import/account custody, eligible providers, entity/bank/tax,
price/legal/refund/data rights, exact outbound/spend approvals, customer trust and on-call work.
Do not require every donor's account up front. Local HQ/fixed tooling needs no paid provider.

Before unattended private work: independently witness authentic authority, hostile denials,
concurrent hard limits, exact approval/replay, remote cancellation/unknown-outcome reconciliation,
billing/media bounds, encrypted restore, actual rollback and delivered external failure alerts.
Then conduct a **private 1–6-month evidence-backed pilot**, including at least 30 consecutive
observed days, explicit budgets/allowed data/on-call/kill criteria and incident reviews. Extend or
stop if evidence fails. Product release is an explicit human decision, not elapsed time or MRR.

Measure task success versus scheduled work, false approvals/refusals, blocked-queue age, incidents,
human interventions, real stop/recovery, independent usage costs, settled revenue/refunds/fees,
quality, margin and retention. Historic $100k/$1k-MRR/365-day scenarios were aspirations, not forecasts,
earnings, contractual targets or permission to run without oversight.

## 7. Preservation and next action

Start at `CONTINUE_HERE.md`; `PROJECT_MEMORY.md` is state, `PROJECT_BRAIN.md` is method/taste/
predictions. Keep licences/source/rollback/business/audit/run evidence. The newer conditional
cleanup preserved all selected Rakazo/OpenDots sources in checked/restored vaults before removing
only redundant loose copies. Keep those vaults/readable references; no general deletion authority.
Near-cap planning consolidation is lossless and receipted, not evidence deletion. Persisted
workspace stays below 128 MB / 10,000 files; dependencies/caches/builds are excluded, not a backup.

The owner imports the refreshed full archive and prompt. IDE starts AG0, compares actual remote
HEAD, reproduces gates and returns AG1's plan. No provider activation/public deploy/background
company work or maintenance is running merely because these files exist.
