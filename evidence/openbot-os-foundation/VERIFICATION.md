# OpenBot OS foundation — measured scope and evidence

Base independently checked:
`9f5600d1fd285e79922fbf69a2abce5243cb9291`.
This packet is Arena's own engineering/testing, not independent native/security/
quality acceptance. Final committed-tree/source/export identity receipts and the
new full commit SHA are outside this commit in the handoff to avoid self-reference.

## Actual base review — correction accepted, not startup fixed

- The pinned base is the direct child of `649d53f`; its only changed paths are
  `SOURCE_MANIFEST.json`, run-3 `report.md` and `result.md`.
- Both corrected prose diffs were independently read: control is **20 DLLs / 21
  modules including executable**, and the causal wording now leaves exact stage,
  rejected image/header, kernel32 mapping and PE entry/wWinMain execution unproved.
- Public PR metadata at the review check: PR #1 open/unmerged, head `9f5600d…`,
  base/main `5a98328…`. That is not a later merge guarantee.
- Actual Linux base guards: **4,478 manifest files, 4,479 Git blobs, 74,122,214
  source bytes**. Both Git and filesystem identity checks passed.
- Actual base regressions: tools **57 passed**, Studio **49 passed / 1 skipped**,
  Node **70 passed**. These are Arena executions, separate from supplied Windows
  test counts. Source was clean before the foundation edits.
- Initial apparent source changes were hash-matching executable-mode differences;
  54 manifest-approved POSIX modes were restored after comparing **all file bytes**.
  No content was reset, local work discarded, folder deleted or old bundle re-imported.
- See `BASE_9f5600d.json`. Supplied Windows traces and raw historical artifacts were
  not edited, relabeled schema 4, or represented as Arena Windows execution.

## Actual foundation results

| Check | Actual result | Evidence |
|---|---|---|
| Tools stdlib suite | **77 passed** | `tools-tests.log` |
| Studio Python | **51 passed / 1 Windows-only skipped** of 52 | `studio-tests.log` |
| New conversation journal | **31 passed**, real disposable SQLite | `conversation-tests.log` |
| Node | **70 passed**, 0 skipped | `node-tests.log` |
| Chromium smoke | **21 grouped assertions passed** | `BROWSER_SMOKE.json`, `desktop.png`, `mobile.png` |
| Scoped Ruff lint and format | Passed; 7 Python files formatted | `ruff.log` |
| Separate workspace-maintenance tests | **12 passed** | `maintenance-tests.log` |
| Recovery-vault payload identity | **4,738 unique payloads checked**, 4,160 original-file recipes | `recovery-history-check.json` |

Runtime/tool identities: `TOOLING.json` (Python 3.13.18, Node 20.20.2, Git 2.47.3,
Ruff 0.11.13, Playwright 1.56.0 / Chromium 141). Browser/Python development tools and
native Linux runtime libraries were downloaded/extracted under excluded cache,
not installed on the owner's machine or made core runtime requirements. No system
package install, Windows installation, IFEO/registry or security-control change.

### Browser scope and honest red→green history

The browser checked actual **served HTML SHA against current source**, 1,440px
three-column desktop and 390px mobile list→conversation→details→Back navigation,
320px list overflow, local human brief keyboard save, dialog Escape, explicit
currency gating and fictional CSV preview, and settings labeling the old packages
and unwired journal truthfully. Zero JavaScript page errors; four observed app
requests, all local GETs; no external application request or privileged network write.
No paired kernel, model, guest computer, IDE/social account or native WebView ran.

The first three exploratory browser attempts are preserved:

1. `BROWSER_SMOKE_FIRST_ATTEMPT.json`: automation's string-evaluating wait was
   blocked by CSP. **CSP was not weakened**; runner now waits on a normal locator.
2. `BROWSER_SMOKE_SECOND_ATTEMPT.json`: runner omitted the mandatory source
   currency, so the UI correctly refused a preview. Runner now asserts this refusal,
   then explicitly selects fictional USD input and confirms the sign convention.
3. `BROWSER_SMOKE_THIRD_ATTEMPT.json`: runner picked the hidden mobile-profile
   settings button on desktop. It now selects the visible desktop account control.

These were test-runner assumptions, not reasons to bypass browser security,
validation or hidden-state visibility. `BROWSER_SMOKE_BEFORE_CONTRAST_FIX.json`
preserves the completed pre-color-fix observation. The portable corrected runner
is `studio/scripts/smoke-openbot-os.py`; it requires a new output directory and an
already approved Playwright/Chromium installation, and never installs/starts/pairs.

One measured selected-contact snippet issue was fixed: **4.246:1 → 4.644:1** on
the selected gray row, with unchanged light layout. `CONTRAST_FIX.json` and a new
source regression record it. Four sampled text colors are **not** full WCAG AA,
all states/zoom/reflow/screen-reader/device acceptance; tiny inherited text still
needs a usability/accessibility review.

## Implementation versus connection

- `conversation_journal.py` is real inert persistence: explicit schema setup,
  exact owner-scope predicates, atomic compare-and-swap/idempotency, quotas,
  bounded replay, logical deletion and digest checks. Tests include competing
  connections, injected DB rollback, reopen and a child process exiting abruptly
  **after commit**. Scope is not authentication, and a digest is not a signature.
- It is **not wired** into HTTP identity, UI chat, a CopilotKit AgentRunner or
  live AG-UI/provider execution. It is not full protocol conformance, an execution
  queue, hosted memory/learning replacement, encrypted storage or migration proof.
- Schema-4 collector default still records no debug-string payloads. New opt-in
  reads are bounded and fail visibly on incomplete capture; new 20 tests are fake
  Win32 logic tests, **not native ABI/Unicode/loader-snaps verification**.
- `windows-debug-string-probe.c` is source only. Actual Windows payload probe,
  target root cause, Mac/Xcode, Android/iOS devices and native rebuilds remain open.
  Owner's “i don't know” did not grant loader-snaps permission; registry unchanged.
- Root first-party MIT/notices and source-first architecture are explicit. Full
  transitive license/SBOM/reproducible-core audit is **not complete**; no closed
  service, binary, artwork, mark or dependency was silently relicensed/imported.
- The upstream index records **93 unique retrieved source files; 84 raw files
  match cached Git-tree blob IDs, 9 have SHA-256 identities without that tree check**.
  Bounded source/metadata/control-flow review is not execution or a whole-code audit.
  No upstream tests or published backend images were run.

## Native/source boundary — do not counterfeit package acceptance

`NATIVE_IDENTITIES.json` independently compares old EXE/APK/DLL bytes to the base;
all unchanged. The three generated shared HTML assets now match each other but
**not** the UI embedded in the old EXE/APK. Prior native-static receipts are
historical; current package/new-HTML equality is intentionally false, not silently
skipped into a green native-release result. Native packages were not rebuilt.
New client bytes require a newly reviewed hash pin in a new disposable gateway
fixture/profile; no owner runtime/allowlist/pairing was changed.

The LoadLibraryExW(EXE) static-import limitation is documented in
`docs/openbot-os/WINDOWS_DEBUG_TEXT.md`; mapping success is not startup proof.
No instruction/stack/rejected-image proof or accepted native UI was obtained.

## Not rerun / not accepted

No whole-kernel or PostgreSQL suite, upstream application suite, fresh 27-check
native package acceptance, real provider, VM/IDE/social operation, production
migration, bank/account integration, independent review, witnessed operations,
protected independent comparison or genuine pilot observation was performed.
Historical kernel results remain historical, not copied into this result.

History verification checked payload identities, **not** another full reconstruction
of all original containers. The recovery vault still depends on complete retained
Git/donor/upload/private originals. No cleanup builder, retirement, deletion or
repack was repeated. Eligible-storage estimates are not platform-save/download
receipts. No new full downloadable ZIP is asserted by this foundation.

No direct Antigravity message, external agent team, authenticated Arena push, PR
merge or public release occurred. Actual next work is in
`docs/openbot-os/WORK_ORDERS.md`. **Public release false; accepted genuine pilot days
0; standing R01–R13 and all human authority/independence gates remain in force.**
