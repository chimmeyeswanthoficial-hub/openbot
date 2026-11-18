# Final verification — reviewed local intake

**Scope:** current first-party intake plus maintained local repairs and selected reuse modules.
Not a production-security, real-provider, profitability or unattended-operation certification.
Session date: 2026-11-10; runner/source timestamps may differ. Exact pins: `source-pins.json`.

## Measured outcomes

| Check | Actual result | Retained evidence |
|---|---|---|
| Incoming public project, unmodified Python suite | 214 successes, 2 skips, 216 collected | `upstream-python.txt` |
| Incoming direct lint | 24 findings; exit 1 | `upstream-ruff.txt` |
| Reviewed local Python suite | **251 successes, 2 skips, 0 failures, 253 collected** | `local-python.xml`, `verification-current.json`, `release-check.txt` |
| Local lint | clean over `services packages scripts` | verify/ruff result in `release-check.txt` |
| Reuse code | **25 successes, 0 failures, 0 skips** (16 findrepo upstream + 4 local safety + 5 Bot HQ queue) | `reuse-tests.txt` and release receipt |
| Local verify | **22 pass / 0 fail / 7 warn**; fresh health body explicitly checked `ok=true, store=ok` | `release-check.txt` |
| Local scratch HTTP smoke | **10/10** | `release-check.txt` |
| Full local `make release-check` | successful; includes Node gate; explicitly not public-release approval | `release-check.txt` |
| Fresh venv + requirements-only, whitelisted source copy without donors/history/dependencies/runtime DBs | **250 successes, 3 skips, 0 failures, 253 collected** | `fresh-python.xml`, `fresh-python.txt`, `verification-fresh.json` |
| Same independent fresh copy: lint / Node / verify / smoke | clean / 25 successes / 22 pass, 0 fail, 7 warn / 10 checks | `fresh-{lint,node,verify,smoke}.txt` |
| Incident registry structural validator | **8 entries / 0 problems** | 5 original rows retained; 3 intake rows appended, linked to regressions |
| findrepo installed CLI | version 1.1.0; live public-only `inspect nickvasilescu/bot-hq --no-cache --json` succeeded | selected source pin and local policy |

The local skips are the two **unconfigured disposable-PostgreSQL tests**. The fresh copy adds the
substrate-versus-manifest comparison skip because donors are intentionally absent. No skip is a
pass. One upstream Starlette/httpx deprecation warning remains in each Python run; it is not a
failed check. Requirements use ranges, so this proves this installation, not reproducibility of all
future dependency resolutions.

## Cross-checks and regression evidence

- Worker verdict + missing-webhook-secret regressions: `boundary-before.txt` records **8 failed /
  1 passed** before repair. Targeted repaired checks succeeded, including the actual in-process
  Sentinel response-model contract through the client/Worker seam.
- Deployment/media quarantine regressions: `quarantine-before.txt` records **7 failures** before
  repair; the repaired combined target set in `quarantine-after.txt` records 26 successes.
- The findrepo safety tests initially reproduced inherited-auth transmission, authenticated
  public-cache writes and unapproved instruction-file mutation; all 4 local boundary cases now pass.
- Full checks were repeated. The final local and donor-free **health/smoke gates were rerun serially**
  after confirming no existing listeners on 8090/8091/8092/8097/8099. This avoids counting another
  run's server as the fresh boot. Each returned health body was explicitly parsed for true/ok.
- The deliberately created donor-free source copies/venvs were removed after successful checks.
  These were disposable test fixtures, not the donor trees, review clones or business records.
- Current docs use JUnit-derived pass/skip/fail arithmetic and real collection; dated historical
  results remain historical. The old collected-equals-passed assertion was incorrect.

## What these checks do not establish

No mandatory OpenBot/Hermes gateway hook, real model/AG-UI turn or output delivery, hard provider
cancellation, pre-spend transactional reservations, OS/tenant isolation, live PG durability,
canonical payment/currency/refund/fee reconciliation, production streaming/splitting, real image
rollout/migration/rollback/restore, external monitor/digest/on-call drill, real revenue or 1–6-month
pilot was demonstrated. Full Bot HQ host and REA runtime/MCP/providers were not installed/run.

Experimental media is disabled without explicit experiment opt-in plus a token; split returns 501.
Deploy CLI is record-only. A signed event is not accounting correctness, a timeout is not a kill,
a queue is not isolation and a passing matcher suite is not a security audit.

The working-tree secret heuristic is shallow/filtered and not full-history or dependency clearance.
Public source was owner-authorized; no remote push/tag/release/deployment or new spending occurred.

## Retention and resource closeout

See `cleanup.json` for the measured cache-only apply, before/after non-cache SHA-256 equality and
final listener check, and `workspace-budget.json` for the final persistence-aware size/file count.
The earlier demo-run deletion remains disclosed in PROJECT_MEMORY; no new business/run evidence
was removed for this intake. `archive/handover-before-public-intake.tar.gz` is the rollback source
snapshot, not a remote Git commit. The reviewed overlay contains no `.openbot` runtime state.


Measured cleanup: **16 cache directories removed; all
8,772 non-cache files hash-identical before/after** at cleanup time.
Zero cache candidates remained. Inventory digest:
`54cd0b87a771700c77f6630e03cdb5607aa377767eb3a466c198fd6d931bc6e9`. Closeout documents/artifacts added afterward are not deletions.
