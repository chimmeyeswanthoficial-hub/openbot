# Project memory — technical stewardship / fixed namespace continuation

**Task date supplied to this assistant:**2026-11-10. **Observed runner:**2026-11-14 for this
follow-up; historical HQ installation receipts observeNov13. Keep both distinct
(`audit/DATE_PROVENANCE.md`); do not rewrite old timestamps/incident IDs.

## Latest engineering continuation — fixed namespace and truthful transport

The owner asked us to keep advancing as technical steward until concrete permissions/resources,
Antigravity handoff and human work are reached. QA/documentation stays first, owned-footage editing
second; no new product-choice question is needed. Human accounts/legal/spend/outbound/release stays.
`DELIVERY_PLAN.md` is the current order; `ANTIGRAVITY_START.md` is the minimal owner/import prompt.

Implemented an **explicit fixed-tool rootless namespace experiment**, not completed AG1. Pinned
non-setuid cache-only Bubblewrap, mandatory namespaces, read-only mounts, minimal environment,
zero capabilities/no-new-privileges, ABI-guarded seccomp including io_uring/process-FD paths,
fixed-worker rlimits, bounded pipes, actual cancel/deadline/parent-death evidence; no host fallback.
Reuses existing policy/audit/exact review/attempt quota/outbox and binds namespace implementation
and tool hashes. It is not wired into HQ/HTTP/Worker/model execution. Read `NAMESPACE_EXPERIMENT.md`.
Rootless namespaces WORK here; old missing-bwrap/Docker assumptions must not stop feasible fixed
experiments. Writable per-job cgroup delegation remains absent; independent security review,
protected secrets/tenant separation and authenticated mandatory execution remain external gates.

Repaired legacy `dispatch_agui.py`: default HTTP transport disabled, store and scoped conditional
single-attempt claim required, confirmed positive audit before injected host callable; no replay
across connections/restart. Timeout/unknown/malformed response or overspend now requires
reconciliation, never a fake kill/delivery/settlement. Replies are draft-only response_received;
cost_usd=null/reported_cost_usd explicitly unverified; numeric run cost0 is only a legacy placeholder.
Advisory callable timeout is NOT enforced provider termination or a hard deadline. AG2 stays open.

Focused verification:117pass =46namespace +24bootstrap +43transport-truth +4updated legacy cases.
Namespace ABI/filter challenge5fail/40pass, missing-rlimit-evidence1fail/45pass then46green;
bootstrap shape/mode/version/partial-destination12fail/12pass then24green; transport35red then35,
follow-up huge-int/status-list/invalid-UTF8 challenge3fail/40pass then43truth+4legacy green.
An actual parent supervisor was killed; all3 observed namespace tree PIDs disappeared, adopted
children reaped withSIGKILL; restart kept interrupted marker/attempt and did not reexecute.
Primary and independently pinned-installed empty SAME-HOST source both measured578pass/2PGskip/
0fail/580collected, Node25reuse+26HQ, lint/build/typechecks, verify22/0/7, smoke10. The namespace
tool was separately downloaded/restored in the independent tree; old fixed-process, namespace
parent-death and explicitly synthetic workbench demos all passed. Source independence is not a
second machine or final-archive reinstall. `audit/progression-review.json` records the freeze;
adjacent bundle receipt records the actual final package/extraction. Earlier465/2/467 stays
historical.113new cases were added;117focused includes4updated existing cases. An installer was
initially invoked from the wrong primary cwd after source copy; its generated-only reinstall log
is retained but NOT counted as independent evidence. Correct fresh-cwd install/gates ran separately.

No provider, arbitrary customer code, social account, outbound delivery, spend, public release,
remote push or pilot enabled. Antigravity connector lookup was unsupported; importable package
is NOT direct IDE delivery. No background work is promised after the chat. Preserve all baseline
business/private/donor evidence and original14 incident lines; append prevention entries only.
Authoritative task date remains2026-11-10; runner UTC reportsNov14. `audit/DATE_PROVENANCE.md`
already distinguishes these; do not relabel the task date merely to match the host clock.

**Previous completed request / reversible source-cleanup checkpoint:** owner asked whether all useful
Rakazo/OpenDots/Bot HQ/findrepo value was copied and conditionally allowed cleanup after copying.
When asked about the technique they replied “I don't know”; technical stewardship chose a
conservative reversible consolidation, not permission to discard unconsumed code or active tools.
All 5,086 selected Rakazo/OpenDots source files (48,726,661 B) were archived, checked independently
against baseline sizes/hashes/modes and actually restored BEFORE removing exact redundant loose
copies. All deferred/unreviewed code/tests and root licences remain in `archive/donor-sources/`;
26 reviewed files (217,231 B) remain readable under `third_party/donor-library/`. The private
OpenDots `.env` remains byte/mode unchanged at its original path. Working HQ131files, queue3,
attribution3, findrepo7 and OpenBot3,479 are unchanged at consolidation. Protected19files stay exact.
No new donor runtime/provider/test was activated. Archives are local/private, not off-host backups.

New `scripts/donor_vault.py` is verify/recover-only, never a deletion tool: trusted SHA, bounded
regular members, manifest set/hash/size/mode checks, no links/traversal/private files or overwrites.
New initial feature absence was red; additional malformed source-root challenge and old provenance
report produced5fail/57pass, then62focused green after schema/ref-report fixes. Normal clean remains
cache-only. See `WORKSPACE_CLEANUP.md` and `audit/donor-consolidation.json` for current measured
gates/receipts. Do not infer that all donor features are integrated or erase source archives.

Primary and independently pinned-installed empty source candidate both measured465pass/2PGskip/
0fail/467collected; Node25reuse+26HQ, lint/typecheck/build, verify22/0/7 and smoke10 green.47new
cases (44vault+3provenance) are included, not added twice. After final router/plan wording sync,
both full gates repeated green.247runtime/config/skill files match across tested roots. Fresh source
had no copied deps/toolchain/build or loose retired donors; both full vaults recovered again with
5,086exact hashes/sizes/modes. Actual fixed-executor and synthetic workbench demos passed there.
Independent install is on same host/from source copy, not the final archive. No new browser run;
UI runtime unchanged. Current receipt-count/mirror guards first refused463pass/2skip/2fail, then
465/2/0 after actual JUnit recording/mirror sync, without weakening tests. Durable cleanup evidence
and final bundle extraction/DB redaction reconciliation are separately identified in their receipts.
Next substantive platform work remains AG1 authenticated mandatory OS/egress isolation, then AG2
real provider/cost/stop. Do not delete working HQ/findrepo or vaults to chase more free space.

**Previous workforce direction/checkpoint:** the owner wants a broad AI workforce/work-delivery platform,
permitted social/human feedback, questions, real jobs, reviewed self-improvement and video editing/
generation. Owner explicitly delegated first-service/social-identity technical choices. Chosen:
human-led QA/documentation first, owned-footage editing second; truthful company identity with real
administrator, draft-only social. Human legal/accounts/price/spend/outbound/release authority stays.
`WORKFORCE_PLATFORM.md` is the new source-backed job/readiness/quality/social/media plan.

New `services/gateway/src/workbench.py` implements offline metadata triage/questions, bounded honest
JUnit QA packets and scoped pending/exact-digest-host-review/revocable/expiring direct feedback.
80 focused tests pass. A final explicit notrun/result-metadata challenge measured79/1, then80
after strict refusal; its additional prevention incident preserves the earlier13-entry prefix.
New capability initially absent; first implementation58pass/14SQLfail→72;
structural/capability challenge73pass/7fail→80. Full Python418pass/2PGskip/420 after recording actual
outcomes and syncing docs; intermediate stale-count/mirror guards failed and were corrected, not
weakened. `scripts/workforce-demo.py` labels synthetic XML/consent/reviewer; separate actual six-case
media-boundary packet passed with brief/source/JUnit provenance and delivery=false/parity=not_measured.
No network/provider/customer job/financial change; not HQ/HTTP/Worker/model wiring, hostile isolation,
consent authentication, fine-tuning or automatic code promotion. Primary evidence/gates/final restore
scope is in `audit/workforce-review.json`, not historic HQ counts below.

LinkedIn/YouTube connector lookups unsupported in this conversation; no apps connected. Official
YouTube policies read in full; consent/fake engagement/data-use/training restrictions preserved in
plan. LinkedIn legal full-fetch500/news403; official docs plus search excerpts are not complete legal
clearance. No ban guarantee, scraping/session bots or automatic likes/comments. One real Cohesive
listing page retrieved ($60 advertised, not income); human-participation-only candidate, still needs
availability/eligibility/AI-use confirmation. Other QA URL redirected and is unverified. No applications.

Near-cap historical metadata/memory consolidation initially13 originals111,316B→31,112B; extended
with4 completed earlier receipts to17 originals163,733B→44,592B tar.xz. Every byte/mode roundtripped,
prior delivery receipt retained in `audit/workforce-evidence-consolidation.json`.
Recover originals via `tar -xJOf archive/historical-metadata-before-workforce.tar.xz ORIGINAL_PATH`.
Donors/licences/primary business/locks preserved. Restore pinned deps after snapshot resets; current
locked environment was actually restored, not assumed. Task dateNov10; observed runnerNov14 retained.
Next bottleneck remains AG1 authenticated mandatory OS/egress boundary, then AG2 real provider/cost/
stop—not broad social agents or executing arbitrary customer repositories on this host.

**Previous completed request:** `OUR_PROJECT.md` is the single comprehensive owner guide, including
exact preserved latest request and explicitly labelled reconstruction of earlier intent (the old
memory/brain are not verbatim user transcripts). Source-backed Bot HQ remaining-value review is
inside it. HQ was already useful/installed; added read-only older transcript paging/UI using the
existing store, with 3 observed red host regressions → 17 host +9 reducer Node tests green and an
actual disposable HTTP Chromium 451-row/retry/no-provider flow. `audit/hq-history-review.json`
records final gates, source delta, business/donor preservation and restore proof. New validated
source candidate8bed3819… was fully extracted and independently installed donor-free on the same
host:337/3/340 Python, Node25+26, full gates, actual fixed-process and history-browser checks passed.
The candidate's durable replacement was refused by the conservative cap guard (old deliverable
untouched); it was still integrity-valid for the disposable restore. Additional50 older logs were
losslessly grouped in archive/historical-test-logs-before-master-guide.tar.xz with byte/hash/mode
roundtrips. Final packaging uses the subsequently consolidated evidence/docs, not runtime changes. All old installed-
source/test/restore receipts below remain historical to their named freeze, not later-code proof.

**Current checkpoint:** pinned provider-disabled Bot HQ/report remains installed. A separate
trusted-host fixed local execution slice is implemented and its47 focused tests plus actual process/
SSE/restart/kill probe pass. Full cross-project/restore receipts and the refreshed bundle identify
the final freeze; consult `audit/EXECUTION_FINAL_VERIFICATION.md`, `verification-current.json`,
`execution-restore.json` and the adjacent bundle receipt, not remembered totals. No provider,
public deploy, business runner, genuine revenue or pilot has been started. This workspace has
no `.git`; nothing is committed/pushed or sent directly to Antigravity.

## 1. Owner direction / non-negotiable scope

- Continue feasible engineering, hand off concrete remaining acceptance work to Antigravity IDE,
  and explain the human-owner part besides both AIs. Antigravity connector lookup was unsupported;
  deliver an importable work order, not a claim that it was sent/run remotely.
- Inspect remaining Rakazo/OpenDots value before calling them unnecessary. The newer owner request
  conditionally allowed cleanup only after copying useful material. Completed consolidation keeps
  ALL selected source/notices in verified restorable archives plus readable reviewed references;
  do not generalize that one-time redundant-copy removal into new deletion authority.
- Earlier request to actually install Bot HQ and keep a downloadable entire source/state/context/
  brain continuation remains. Historical delivered bundle was complete, but predates this code;
  refresh it at the new verified freeze. Cache/deps/auth/processes do not transfer.
- Owner made openbot/findrepo public and authorized licensed reuse. Assistant decides technical
  architecture with candid pushback. Preserve independent Sentinel/ledger/venture/routine kernel,
  reviewed owner/PDF/Antigravity additions, maintenance regressions and business/audit/run evidence.
- Human retains legal/entity/prices/accounts/spend/sensitive outbound/release. Private1–6-month
  evidence-backed pilot and human product-release decision remain. No guaranteed profit or
  perfection/unrestricted autonomy/literal assistant-self transfer; quota is not observable.
- Use/extend skills; red→green and repeated independent verification. Keep 128 MB / 10,000 files,
  disclose cleanup; never delete history/donors/uncertain request markers to make a check pass.

## 2. Installed local HQ (unchanged architecture)

`apps/bot-hq` is an authenticated local-only workspace, not merely cloned source: pinned source,
locked Node/npm/hashed Python wheels, SQLite binding, TS/React builds and host tests. Reuses
roster/store/sessions/events/transcripts/tasks/notes/inert skills; neutral/Lucide artwork replaces
known excluded donor shapes/eyes/icons/logos. Licences/notices stay; this is not all-asset clearance.

HQ company-report task → fixed `scripts/hq_readiness.py` → independent Sentinel policy/audit →
three bounded real evidence reads → digest-bound report/task/replay. Not a model reply, new test
run or financial authority. Primary saved task 1 / kernel audit 6; no new primary task intentionally
created by this follow-up. Markers without valid completion require reconciliation, never rerun.

All providers/managed Hermes/autonomous engines/schedulers/computer/VNC/browser/shell/MCP/voice/
OAuth/app connections remain off/unmounted. Compiled local entry only; upstream entry refuses;
root/cloud installer helpers remain non-executable reference text. No primary-agent key loaded.
OpenBot/AG-UI remains a replaceable real-agent target, not an installed live-engine claim.

Inputs: owner openbot `a67fb041763bdfd16ed8b77f0ad24edd8e154f20`; findrepo
`4d512682b8e30cfcbda2a7f74f44ae76df9ed77a`; HQ
`decf9a215cddd8792a5f20f4a11a87d4dffa6d15`; REA
`cdc4541ef707f256f83abe5018df01a25182cf0b`. Source pin receipts retained. REA is instructions
and 8 references only; its engine/MCP/providers are not installed. findrepo CLI has local explicit
credential/cache/instruction-write controls. Read imported LOCAL_POLICY before skill contents.

## 3. New fixed execution slice — exact claim

Files: `services/gateway/src/{local_executor,local_tool_worker}.py`, tests in
`services/gateway/tests/test_local_executor.py`, `scripts/execution-demo.py`. Existing Store
`audit_tail` now optionally filters run_id/action; old defaults remain. `EXECUTION_SLICE.md` is
contract; `local-execution` skill records safety/replay/promotion method.

- Fixed `local.wordcount` / `local.reviewed_wordcount` only. Frozen trusted-host Authority;
  JSON cannot supply identity, owner, approval, cost, program or URL. Canonical UUID,8,192-byte
  bounded text, simple scoped JSON filename, known-secret refusal. Text persists; no real PII.
- Reuses GatewayAdapter/mapper + Sentinel policy/audit/approval storage. Host-only Owner is a
  capability convention, **not remote authentication**.15-minute exact draft/request/authority
  approval; relevant executor/worker/adapter/mapper/policy/repository hashes bind execution/replay.
- SQLite transactional claim/attempt quota, persisted cap cannot silently widen. Units are
  conservative **reserved attempts**, not dollars or revenue; uncertainty is not refunded.
- Actual fixed Linux Python-I-S subprocess, minimal env, parent-death guard/rlimits, bounded SSE
  consumption and run/tool/message correlations. Real process-group SIGKILL+wait for cancel/deadline.
- Independent completion binds output/result/events. Request-bound relative outbox path, bounded
  regular-file/symlink checks, exclusive fsynced local delivery, correct relocated restore replay.
  Partial/interrupted/corrupt work refuses and requires reconciliation rather than a new-ID repeat.

**Not wired into HQ, HTTP, Worker daemon or model AG-UI. Not hostile-code/OS/network/tenant
isolation, tamper-proof DB, paid-spend enforcement, provider kill or exactly-once external send.**
Same-user source/path races and two-DB crash gaps remain explicit limits. Do not generalize it into
an arbitrary program runner or enable raw upstream tools to demonstrate “completion”.

### Failure evidence / verification chronology

- Baseline after restoring excluded dependencies:291pass/2skip/293 before feature.
- `audit/execution-before.txt`: expected missing-module red. First implementation35pass/2fail:
  tests monkeypatched a frozen Store instance; corrected class-method fixture, then37green.
- `execution-integrity-before.txt`:37pass/3fail caught outbox absolute-path redirection,
  altered stored approval preview and relocated-state path. Full preview/implementation binding,
  relative request-derived routing and regular-file checks fixed them;40green.
- `execution-replay-binding-before.txt`: 42 pass / 5 fail caught stored request redirect, unaudited
  result/events replay, control-character JSON expansion and missing mapper hash. Added request/
  artifact/event binding, six-source digest and bounded larger worker input; **47green**.
- `audit/execution-after.txt`, `execution-demo.json`: actual fixed subprocess/SSE/output, restart
  without child/redelivery, reviewed task left pending, denied browser tool, real cancel/deadline,
  killed disposable parent and reaped child SIGKILL; interrupted marker not reexecuted. No network/
  model/payment call. Generated proof state is excluded.cache, not business backup.
- Final full/release/independent-restore evidence is in the final receipts; do not reuse earlier
  291/293 or focused47 as the current whole-project result. Record failures/skips honestly.

## 4. Donor reuse / history preservation

`DONOR_REUSE_REVIEW.md` gives selective reuse/defer/reject with source seams. `audit/donor-review.json`
fingerprints selected Rakazo 4,899 files / 47,148,124 B (`8fe178f0…`) and
OpenDots 187 files / 1,578,537 B (`a140f68f…`); no tree modification/deletion. Tarball main@Nov9 labels
are **not upstream commits**. No direct reference/import found across 177 first-party source files
in scoped search; not a transitive audit. OpenDots.env excluded without reading/deleting.
Rakazo root Apache2, OpenDots MIT/AtaiBarkai; root licence is not all-asset/dependency clearance.

Remaining useful material: occurrence/coalescing/watch/backoff, board/context, exact stored review,
revocation, expectedRevision/scoped pages, delegation/hop limits, skills/import UX and backup methods.
Actual page review lives in PageReviewCard/page-routes/pages#createReviewed, not TaskActions.
Reject copying stale interrupted external-call retry as exactly-once or AbortSignal/Promise timeout
as termination. Do not import tokenTEXT storage as separated vault, or whole donor host/kernel.
Local executor is original code/pattern reuse; `services/gateway/PORTED_FROM.md` records this.

Near-cap stale planning/status pages were losslessly preserved before consolidation in
`archive/planning-before-execution-refresh.tar.xz` (33,652B, SHA `b62b99ce…`), with every roundtrip
hash checked in `audit/planning-consolidation.json`; a second 17,156 B archive preserves the old
master plan/combined handover. Docs mirrors stay current; new verbose JUnit/gate evidence is
losslessly compressed with exact decompression receipts rather than discarded. No donor, business,
audit/run, rollback/overlay artifact removed. Earlier unsafe deletion of a demo stderr/run directory
remains disclosed/unrecovered in history. Existing 10 registry rows retained; new execution-integrity
incident is append-only with actual regression rule. No periodic maintenance runs without a runner.

## 5. Current handoff / next action

`ANTIGRAVITY_WORK_ORDERS.md`: AG0 safe source intake/gates → AG1 mandatory authenticated hook and
real OS/egress isolation → AG2 real AG-UI/provider stop/cost → AG3 durable scheduler/PG → AG4
accounting/streaming media → AG5 actual deploy/rollback/restore/alerts → AG6 protected eval/learning/
private pilot. Broader tasks are unfinished, not all “impossible to code here”; external environment,
owner accounts/authority and operational evidence must accompany integration. Docker/Podman/bwrap/
psql absent here. Media default-off/token/split501; deploy helper record-only. Generic legacy
worker/cost/timeout paths are **not** made production-safe by the separate new executor.

`OWNER_CHECKLIST.md`: owner imports project/prompt, controls eligible accounts, budget/legal/price/
data/outbound, on-call/customer trust, private pilot and release. Do not buy all donor services.

Restore on Linuxx86_64/Python3.13:
`bash scripts/bot-hq.sh install`; prefer `.venv/bin` and pinned
`.cache/openbot-toolchains/node-v24.22.3-linux-x64/bin` on PATH; `make lint` then
`make release-check`, plus fixed execution demo. Network needed for downloads. Optional foreground
`bash scripts/bot-hq.sh start`, second host terminal `access-code`; stop via process manager/Ctrl-C.
Old process/auth/cache/browser/OS-library state is not portable. HTTPS preview cookies remain
unproved by historical HTTP-only browser evidence; do not claim that coverage without AG5 proof.

`PORTABLE_HANDOFF.md` / `NEXT_CHAT_PROMPT.txt` preserve restore context. The historical delivered
checkpoint (18,588,188B, SHA `36fef8b01a676121f1b3b3f93ec68743705b446548df888582378d888f716c83`)
was complete but excludes this execution work. New bundle receipt governs its replacement freeze.
Stage incoming archive in excluded.cache before extraction; do not leave two loose durable trees.

Space-preserving upload recovery: the original architecture PDF is retained byte-exact as
`uploads/Untitled document (14).pdf.xz` (857,243→602,340B), verified in
`audit/workforce-evidence-consolidation.json`. View a restored copy via
`xz -dc "uploads/Untitled document (14).pdf.xz" > .cache/restored-architecture.pdf`;
original-name references/source pins identify the recovered PDF, not discarded content.

Completed workforce verification: primary and independently installed source candidate each
418pass/2PGskip/420, Node25+26, lint/build/typecheck, verify22/0/7, smoke10 and offline demo passed.
The245-file first-party runtime/config/skill inventory matches byte/mode/hash across both roots.
Independent source was copied to a new target with sanitized SQLite exports and separately
restored dependencies on this same host; it was NOT installed from the final delivery archive.
Final archive extraction/source reconciliation is recorded separately in the adjacent bundle
receipt.14 incident entries preserve the original12-entry prefix; no customer/provider action.
