# OpenBot OS work orders — active handoff, not a simulated agent team

Reviewed ancestor: `9f5600d1fd285e79922fbf69a2abce5243cb9291`; direct parent:
`cf2acb10530ab3c33c567bb9831c5d6dbe515349`. The successor's final ordinary
commit SHA and actual test logs are supplied in the external history handoff receipt,
so this committed document does not refer to its own future hash.

No direct Arena↔Antigravity channel, authenticated Arena push or external agent
team was established. These are prepared work assignments. The owner can give
Antigravity this one file with the current commit/bundle; no need to relay each
engineering decision. Agents must report actual work and blockers, not invent
collaborator activity or claim asynchronous progress after a chat ends.

## Engineering stewardship

Arena leads architecture, source reviews, bounded implementation, regressions and
acceptance evidence. Antigravity leads receiving/publishing ordinary shared commits
and actual approved Windows/native work. Each may use available sub-agents only
with explicit disjoint file ownership and returned commits/evidence. Do not claim
that happens until it actually does. The human retains legal ownership, secrets,
accounts, host changes/installations/spending/signing and release authority.

## Current completed increment / next boundary

A successor of `cf2acb10530ab3c33c567bb9831c5d6dbe515349` implements the opt-in
signed-device human history API: 58 new cases, included in 473 passing selected
gateway/journal tests with 87 explicit PostgreSQL skips. It adopts the exact MIT
AG-UI 1.0 schema for CUSTOM-envelope tests, **not** a live stream/runner/provider.
See AUTHENTICATED_HISTORY.md and FEATURE_REUSE.md; final SHA is external.

No direct Antigravity delivery is possible in this session: connector lookup
returned unsupported. This is a prepared handoff, not an active external team.

## W00 — integrate the current successor without overwriting work

**Receiver: Antigravity. Priority: first.**

1. Preserve local changes and refs. Read `git status --short` and the current full
   SHA; do not reset/clean/delete a folder/force-push or stage private state.
2. Verify the transported commit's full SHA/parent/changed paths. If your branch is
   exactly the base, use the supplied fast-forward-only transport instructions.
   If it advanced, return the head and reconcile with a normal reviewed merge;
   never re-import the historical c3 recorder repair on top of newer work.
3. Run actual Windows source/portable checks and the journal tests below. Report
   observed counts/skips/raw logs and platform; don't copy Linux outcomes.
4. Push normally to a review branch/PR. Publishing a head is not merging into main.
   Return PR URL, full head/base SHAs, cleanliness and the completed test evidence.

## W01 — review completed history, add UI and one compatible AG-UI adapter

**Primary: Arena/backend stream.** Authenticated human-history API completed;
UI/runner/provider and remaining lifecycle contracts are the next implementation.
File ownership: `work/services/sentinel/conversation_journal.py` + its tests,
new explicit auth/history routes and fixture contracts. Agree before touching
`app.py`, shared schemas or `SOURCE_MANIFEST.json` with another writer.

- Derive scope from authenticated session/organization membership, never request
  JSON. Reuse the existing authenticated gateway rather than exposing a parallel
  unauthenticated journal API. Existing single-owner pairing is not multi-tenancy.
- Specify list/create/read/delete/append wire contracts, stable error/no-existence-
  leak behavior, per-request byte limits, raw JSON duplicate-key rejection, CSRF/
  origin protections and secret redaction/retention. No production DB migration.
- Compare the optional pinned MIT SDK SQLite runner first. The new Python journal
  is not a drop-in AgentRunner. Decide its adapter/authoritative-state ownership
  before introducing two conflicting histories or duplicating SDK execution code.
- Add upstream AG-UI schema/fixture validation and run/message/tool correlation;
  the old narrow custom SSE profile must not be relabeled full AG-UI.
- Prove commit-before-notify, disconnect/replay, stale scope/revocation, duplicate
  IDs/changed retries, concurrent append, process death, retention/export/delete
  and cancel/uncertain-effect semantics. No frontend tool may bypass the kernel.
- First genuine provider run requires an explicit provider/account/cost cap and
  retained normalized raw evidence; do not silently enable billing or use tokens.

**Exit evidence:** integration tests and reproducible scope/reconnect failures
before fixes; no UI “connected” label until actual end-to-end connection exists.

### W01 remaining after this increment

Review `conversation_api.py` + the locked history admission in `control_api.py`.
Do not reopen a weaker unauthenticated journal service. Add actual Studio history
UI only against this contract, then a compatible pinned SDK/AG-UI agent adapter.
Do not accept arbitrary assistant/system/tool events from a browser. The existing
fixture SSE is not full AG-UI 1.0. Tombstones/lifecycle/export/backup deletion, full
org/multi-tenancy and PG history are not accepted. A real provider still needs an
explicit account/data/cost cap and host/security gate, not an invented fixture.

## W02 — Windows root-cause evidence (parallel with W01)

**Primary: Antigravity/native stream, owner-approved host only.**
Files: new Windows evidence directory/report; reserve collector edits with Arena.

1. Preserve historical binaries/traces and verify exact current hashes.
2. Run the new debug-string probe only with an already approved toolchain. Verify
   actual Unicode/raw byte counts and cleanup before trusting text capture.
3. Read `WINDOWS_DEBUG_TEXT.md`: current IFEO permission is **not granted**. Do not
   enable loader snaps/install tools/change registry/security controls silently.
4. Do not claim LoadLibraryExW(EXE) resolves static imports. Do not guess DLL/TLS/
   MSVC/signing fixes from `0xc000007b`. Return rejected-image/path/status/stage
   evidence or the honest next blocker, not another identical three-event trace.
5. A changed build is a separately hashed diagnostic experiment. After a justified
   fix, rebuild current shared UI and capture genuine light-UI launch, list/chat/
   search/keyboard/resize/DPI/lifecycle/close behavior on the support matrix.

**Exit evidence:** raw private trace plus separately reviewed/sanitized publication,
new SHA/report and actual native UI proof. Collection status alone is insufficient.

## W03 — frontend and device stream

**Receiver: a real available frontend/native agent; not yet launched.**
Files: `studio/web/` sources/tests; generator writes the three explicit HTML assets.

- Preserve the owner's light reference layout and original artwork. Do not copy
  the upstream brand, dark-default UI or product screenshots as our own.
- Connect authenticated history only after W01's API contract and revocation tests.
  Keep local examples/requests distinct from live state, screens and effects.
- Measure contrast/focus/keyboard/reflow/reduced-motion and screen-reader behavior;
  the inherited tiny/muted text must not be assumed WCAG-conformant.
- Render stale/historical computer frames differently from live frames, show which
  human/bot controls input, and stop work on unknown scope/control state.
- Regenerate deterministic shared HTML. New client bytes require a **new reviewed
  hash pin and disposable pairing profile**, never weakened origin/TLS/hash checks.
- Old EXE/APK remain historical; Android device and real Mac/Xcode/iOS acceptance,
  signing/update/rollback/uninstall need actual tools/devices and owner authority.

## W04 — real PCs, IDEs, official social and independent gates

Do not drop these requirements for a narrower QA-only release. Implement after
W01's mandatory broker: real VM/microVM provider and hostile-host limits first,
then actual Claude Code/Antigravity/T3Code sessions, then official X/Instagram/
YouTube scopes/consent/private test operations. Containers are not real VMs.
No scraping, credential sharing or platform-policy/rate-limit evasion.

S09 hostile-host/capped-provider, S10 supported native devices/signing/update,
S11 witnessed operations/recovery/alerts/on-call/privacy/supply chain, S12 protected
independent ≥20 pre-frozen held-out tasks and both requested real-world phases
(first month/≥30 consecutive observed days, then six additional calendar months),
and S13 exact human release approvals remain open.
Accepted pilot days 0; public release false. Agents cannot self-approve independent
acceptance, permissions, licenses or a pilot they did not genuinely observe.

## W05 — sequential real-world pilot and safe upgrades

The owner's latest requirement is one real month (≥30 consecutive genuine observed
days), then independent phase-1 review/owner expansion approval, then **six
additional calendar months**. Read REAL_WORLD_ROLLOUT.md. No start date/real user/
on-call/reviewer/provider/VM/pilot observation is invented; accepted days 0.

Reuse the existing protected evaluation machinery; design/review a versioned
phase/candidate-transition/upgrade-continuity extension first. Assessment v1 only
handles one candidate/policy and ≤180 days: do not silently call it six calendar
months, remove its protection or pool old/new builds into one cohort. Freeze
held-out tasks/criteria/limits outside bot-writable source; no tests count as days.
Actually authorized private real-world launch precedes observations; public
release and each external account/host/spend/consent/native gate stay human-owned.

## Required checks and return format

```sh
python tools/verify-git-source.py --ref HEAD
python -m unittest discover -s tools/tests -p 'test*.py' -v
python -m unittest discover -s studio/tests -p 'test*.py' -v
node --test studio/tests/*.test.cjs work/packages/bot-hq-queue/serial-queue.test.mjs work/tools/findrepo/test/*.test.mjs
```

Journal: set session-local `PYTHONPATH` to `work/services/sentinel`, then
`python -m unittest discover -s work/services/sentinel/tests -p test_conversation_journal.py -v`.
Use `OPENBOT_OS.md` for POSIX and PowerShell examples. The current selected gateway/journal and portable
checks are recorded in the current evidence packet; historical whole-kernel/PG/native
receipts are not fresh results. Do not run production migrations, blind pytest or package installs.
Use `tools/KERNEL_TEST_PROFILE.md` when a broader kernel change needs that profile.

Return: full base/head SHA + changed paths + actual platform/test counts/skips +
source guard result + raw-evidence hashes + remaining blocker + permissions used.
For the new history/official-contract cases explicitly select the existing
handoff/control locks plus `work/requirements.agui-test.lock.txt` in a NEW approved
disposable environment, then run `services/gateway/tests/test_conversation_api.py`
from `work/`. See AUTHENTICATED_HISTORY.md. Dependencies are not installed by import.
One writer regenerates the manifest **last**, preserves approved file modes and
verifies the exact tree. No self-referential commit/hash receipt in that tree.
