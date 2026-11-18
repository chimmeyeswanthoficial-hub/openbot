# Bot HQ installation and governed reuse

**Status: local-only installation, build, runtime/restart and local/fresh gates VERIFIED.**
The full continuation archive was created, extracted and independently reinstalled/tested.
`PORTABLE_HANDOFF.md` and its separate receipts give exact handoff integrity/restore evidence.
Read `CONTINUE_HERE.md` first after a transfer. This report supersedes the earlier
queue-only adoption scope in `ADOPTION_REVIEW.md`; it does not waive its safety or licence limits.

## What the owner asked / technical decision

Actually install Bot HQ and reuse useful licensed features, while preserving our
company project and making it portable to a new chat. Done as a pinned, attributed
local derivative under `apps/bot-hq`, **not** a wholesale financial-authority migration.
The independent Sentinel/ledger/venture/routine kernel remains. OpenBot/AG-UI remains
the current replaceable real-agent runtime target; the new HQ profile is a working
local workspace and evaluated frontend, not evidence of a live provider runtime.

## Installed and useful now

| Capability | Actual implementation | Limit |
|---|---|---|
| Bot HQ source + dependencies | Pinned MIT text/source, npm lock, supported Node, SQLite binding, TS/React build | Dependencies/builds/toolchain are regenerated after transfer |
| Local roster and settings | Persistent SQLite bot workspaces and neutral badges | No managed engine or computer is provisioned |
| Transcripts / live UI | Persistent notes, donor event hub and SSE, reload recovery | Notes are not model replies; no autonomous agent running |
| Skills | Store and consult inert per-bot skill data | Instructions do not execute or create permissions |
| Company task workflow | HQ task → fixed Python adapter → independent Sentinel → real local evidence report → task/transcript | Three fixed state/receipt inputs only; no arbitrary commands/URLs/paths/cost |
| Audit/replay | Separate kernel SQLite, audited allow/deny, report digest, durable identity/marker and idempotent replay | Same-user local adapter, not OS isolation; incomplete jobs require reconciliation |

The report references existing verification evidence with input hashes. It **does not**
rerun tests, earn revenue, release a product or declare the company ready. UI writes
(notes/roster/skills) are local application data; only the fixed report is the new
governed company-tool slice. No broader runtime enforcement is claimed.

## Follow-up: remaining reuse review and older history

Bot HQ is not exhausted/useless. `OUR_PROJECT.md` §7 gives source-backed keep/adopt/defer/reject
choices for store/events/cards, engine streaming, rooms/subagents, routines/triggers/proactive,
Hermes memory/provisioning, approvals and search. No wholesale kernel/scheduler migration.
New owned generation-bound read-only pages (maximum200 entries), explicit **Load earlier entries**,
retry/scroll anchoring and stale-generation/revision merge protection now expose retained history.
Three host regressions failed before the change;17 host +9 reducer Node cases now pass, with
30 existing HQ Python cases and both builds/typechecks. An actual disposable HTTP Chromium flow
recovered451 rows/225notes, including503retry; no provider/task/kernel job was started by that
browser fixture. Exact source delta, gates/preservation/restore: `audit/hq-history-review.json`.
The original installed-source inventory/installation results below remain historical. Historical
loose XML/log encodings now have exact `.xz` counterparts and a hash mapping in
`audit/master-guide-evidence-compression.json`; their evidence bytes were not discarded.

## Safe install / run / stop

Tested platform: Linux x86_64 / Python 3.13. Installer pins Node **v24.22.3** to its
official HTTPS archive SHA-256 (`audit/bot-hq-runtime-lock.json`) and installs the
24 hash-locked Python wheels in `requirements.handoff.lock.txt` into `.venv`.
Other Python/platform targets need a reviewed wheel/runtime lock refresh; do not
silently weaken hash verification. Network access is needed for dependency downloads.

```sh
bash scripts/bot-hq.sh install
bash scripts/bot-hq.sh test
bash scripts/bot-hq.sh start       # foreground 0.0.0.0:8787, authenticated
# second terminal, only on the host:
bash scripts/bot-hq.sh access-code
```

Open the port-8787 live preview (or local `http://localhost:8787` outside Arena).
Use its **Local access code** field. No public account/password, OAuth or provider
credential is required. Auth material is generated under snapshot-excluded `.cache/`,
not included in a continuation archive. Stop with Ctrl-C or the process manager;
never delete `.openbot/` to stop it. Port can be selected by `HQ_PORT` at startup.

The launcher strips inherited provider/payment/SSH environment variables. Runtime
imports only the reviewed local graph, starts no scheduler/idle/engine/VNC/MCP/voice,
and accepts no API toggle to enable them. Upstream's old entry throws; helper scripts
are quarantined reference text. UI uses relative requests; the server accepts the
preview host, enforces same-origin JSON writes and uses HttpOnly partitioned HTTPS
sessions. This is local-development authentication, not a production security audit.

## Licence, dependency and startup decisions

- Upstream source pin: `decf9a215cddd8792a5f20f4a11a87d4dffa6d15`.
  `LICENSE`/`THIRD_PARTY_NOTICES.md` retained. Known excluded artwork/media, generated
  shapes, logos and favicon were not installed. New letter badges and licensed
  Lucide icons replace them. No blanket rights claim over prior donor code/assets.
- Original intake: 122 text/source files; Git, binary/media/design assets excluded.
  Per-file upstream hashes/omissions: `audit/bot-hq-source-intake.json`.
- All npm lifecycle scripts disabled. The published SQLite package ships a working
  native binding; it was loaded successfully without a rebuild or install script.
  Native packages remain third-party binaries, not an independent build attestation.
- Initial npm audit reported two moderate development-tool findings (`tsx` / old
  `esbuild`). The unused tsx development runner and its dependency subtree were
  removed; no remaining package version was upgraded. Final advisory snapshot is
  `audit/bot-hq-npm-audit.json`; this is advisory coverage, not malware clearance.
- Upstream startup and tool/helper scripts were statically reviewed, **not run**.
  `GROKBOT_NO_SCHEDULER=1` alone does not stop engine initialization. The current
  pinned idle watcher is a logging no-op, but that does not make the rest safe.

## Measured evidence — historical HQ installation checkpoint

The table below preserves the completed installation/old-package measurements. The subsequent
separate local executor adds tests without enabling providers or changing HQ's supported routes.
Use `audit/EXECUTION_FINAL_VERIFICATION.md` / `verification-current.json` for refreshed whole-suite
results and `audit/execution-restore.json` for its restore proof; do not call the old table current.

| Check | Actual result |
|---|---|
| Full local Python | **291 passed, 2 skipped, 0 failed / 293 collected** |
| Fresh donor-free Python, locked independent reinstall | **290 passed, 3 skipped, 0 failed / 293 collected** |
| Added Python cases (included above) | 30 HQ/kernel/install/integrity + 10 handoff safety/integrity cases |
| Node | 25 dependency-free reuse + 14 installed-host = **39 passed** |
| TypeScript / web / server build / Ruff | passed / passed / passed / clean |
| Actual Chromium | sign-in, real report/task, note, reload; 0 external browser attempts, 0 JS exceptions |
| Serial local/fresh kernel gates | **22 pass, 0 fail, 7 warn**; explicit healthy JSON |
| HTTP smoke | **10/10** local and fresh; full local release-check successful |
| Incident registry | 10 entries, 0 structural/reference problems (not a semantic security audit) |
| Current-workspace HTTP + actual process restart | same report/task/kernel run; six audit rows unchanged; no repeat execution |
| npm advisory snapshot | 0 reported after unused dev-tool removal; not malware clearance |

Two default Python skips are opt-in disposable PostgreSQL tests; fresh donor-free adds the
substrate-comparison skip. One Starlette/httpx deprecation warning remains. Fresh source/state came from the actual archive, without donor repos/caches; runtime and
dependencies were independently restored with unchanged locks and all fresh gates rerun. Read exact receipts, not expected counts.
The archive's own extraction/manifest validation is recorded separately in the handoff receipt.
Restored old credentials were refused; new authentication, saved task + independent digest-bound
kernel replay, one new disposable report and local HTTP SSE hello were verified. Both local
verification servers were stopped after measurement. No preview HTTPS-cookie proof is claimed.

- `audit/hq-local-python.{txt,xml}`, `verification-current.json`, `hq-fresh-python.{txt,xml}`
- `audit/hq-verification-fresh.json`, `hq-fresh-{install,final-gates}.txt`, `hq-release-check.txt`
- `audit/bot-hq-{install,typecheck,build,host-after,kernel-after,browser}.txt`
- `audit/bot-hq-browser.json` and screenshot; `audit/bot-hq-runtime-smoke.json` (actual restart replay)
- `audit/bot-hq-{kernel-before,host-before,host-first-attempt,integrity-before,installation-guards-before}.txt`
- `audit/bot-hq-{runtime-lock,dependency-changes,npm-audit,source-intake}.json`

The first host run caught missing neutral schema migrations: 4 host cases passed,
10 failed; safely migrating the required columns restored 14/14. Integrity tests
then caught a corrupted report replay and ambiguous mid-run audit failure; both
now refuse/reconcile instead of claiming completion or automatically repeating work.
The shell deploy wrapper was tested with disposable copies: explicit `--record-only`
is passed correctly, omission refuses; no infrastructure was changed. Verification
recording now derives the measurement date from JUnit, not a hardcoded date.

## Portable handoff

`PORTABLE_HANDOFF.md` explains the full source/state archive, manifest/digest checks, safe new-directory
extraction and tested reinstall commands. `CONTINUE_HERE.md`, current memory/brain and
`NEXT_CHAT_PROMPT.txt` preserve operating context. Authentication is stripped only from export copies;
business/audit/run evidence is retained. Dependencies, builds and processes must be restored.

## Next engineering step / blockers

A **separate fixed trusted-host executor** now covers harmless local work, exact drafts,
attempt reservations, real process stop and scoped outbox/replay (`EXECUTION_SLICE.md`). It is not
wired into this HQ, Worker, HTTP or a live model. Next: mandatory authenticated bridge plus real
OS/egress isolation (AG1), then actual streaming runtime, financial caps and provider stop proof
(AG2). Do not enable upstream browser/shell/providers and hope a prompt/card supplies the boundary.
`ANTIGRAVITY_WORK_ORDERS.md` is the build handoff; `OWNER_CHECKLIST.md` separates the human part.

Still not proved: real model/provider operation, adversarial OS/tenant isolation,
production media streaming/resources, canonical payment/refund/currency reconciliation,
PG durability, deployment/rollback, external monitoring/digest delivery, a real paying
customer or the mandatory **private 1–6-month pilot and human release decision**.
No public deployment, remote push, provider spend or background business runner has
been authorized/executed by this installation.
