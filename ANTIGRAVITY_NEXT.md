# Antigravity — concrete next engineering handoff

**Delivery, not a sent IDE message.** Direct Antigravity integration is unsupported
in this session; no IDE/session/account was connected and no collaborator received
this file. The user should open this complete workspace in Antigravity and supply
this document. Do not claim work happened after this active session ended.

## Current repair successor — do this next, not another restoration

Current checkpoint `light-repair-verified-1`: the 258 missing source files are
restored. Arena independently reproduced your reported archive hash from pinned
commit `f40421329adc87e49698a752103a78d8d3aea507`; no laptop ZIP was received.
Read `REPAIR_REVIEW.md`. The aggregate digest is corrected and checked; archive
manifest mode is canonical 0644; root report/ignore/attributes are now manifest-listed.

1. Preserve your current workspace, uncommitted changes and backup refs. Review this
   complete successor on the existing repair branch; ordinary commit/PR only. No
   reset/clean/folder deletion/force push. Never stage private state or SDK/signing caches.
2. Verify the complete extraction. Strict now covers `.gitignore`, `.gitattributes`
   and `result.md`. POSIX Git checkouts lose 0600 modes: restore reviewed manifest
   modes in a clean test copy or extract the ZIP with a mode-preserving tool.
3. Current Linux units: Studio **49 pass / 1 Windows-only skip of 50**, handoff **10**,
   Studio Node **45**, retained Node **25**; native binary/static **27**. Recheck on
   Windows and report real skips/raw output; never relabel simulated link checks actual.
4. Your reported process launch is useful but not complete Task B. Collect actual
   Windows rendered light-UI screenshots and manual list/chat/search/resize/keyboard/
   DPI/offline/resume/close outcomes, OS/runtime and raw logs. Do not bypass device
   policy. A responding process/error dialog alone does not prove intended rendering.
5. Next Android device/emulator acceptance and real Mac/Xcode/iOS work require their
   actual devices/tools. No IPA, signing or complete R01-R13 acceptance is implied.

The unchanged HTML/kernel retain the scoped earlier Linux receipts; do not demand
another identical full Linux run instead of collecting missing Windows evidence.
Source changes still require their relevant regressions and one full verified ZIP.
No direct IDE message or GitHub write was sent by Arena.

## Read first / do not undo

1. `START_HERE.md`, `VERIFICATION.md`, `PUBLIC_RELEASE_ROADMAP.md`, `DESIGN_REFERENCE.md`.
2. Work from **this one extracted ZIP**, in a new directory; do not apply older patches.
3. Preserve the light reference-derived desktop/mobile design. Change UI source under
   `studio/web/`, run `python3 studio/scripts/build-web.py`, then rebuild **both** local
   native packages. Never hand-edit one generated HTML or ship a dark/old native fork.
4. API v1 / wire client 0.2.0 is deliberately unchanged; native package 0.3.0-local is
   independent. New client bytes require a newly reviewed gateway client-hash pin and
   a NEW fixture/profile. Do not disable source/hash/origin/TLS checks to load an update.
5. Do not remove `work/repos/OpenBot/` or historical/private source to solve storage.
   The archive audit found unique recovery/history data; **nothing was deleted**.
6. No account keys, provider/OAuth tokens, signing keys or production DSNs in chat,
   source, renderer drafts, public evidence or bot-writable directories. No spending,
   real external action, production deployment or release is authorized by this handoff.

## Task A — reproduce current evidence before changing code

From the extracted root:

```sh
python3 tools/verify-source.py --strict
python3 -m unittest discover -s studio/tests -p 'test*.py' -v
python3 -m unittest discover -s tools/tests -p 'test*.py' -v
node --test studio/tests/*.test.cjs
node --test work/packages/bot-hq-queue/serial-queue.test.mjs work/tools/findrepo/test/*.test.mjs
```

Use a separately installed reviewed Playwright 1.56.1/browser environment. Start
`python3 studio/src/studio.py serve --bind 127.0.0.1 --port 4183`, then in another shell:

```sh
PREVIEW_URL=http://127.0.0.1:4183 TEST_ENGINE=chromium EVIDENCE_DIR=.cache/check-ui-chromium node studio/scripts/test-ui.cjs
PREVIEW_URL=http://127.0.0.1:4183 TEST_ENGINE=webkit EVIDENCE_DIR=.cache/check-ui-webkit node studio/scripts/test-ui.cjs
PREVIEW_URL=http://127.0.0.1:4183 TEST_ENGINE=chromium EVIDENCE_DIR=.cache/check-finance-chromium node studio/scripts/test-finance-ui.cjs
PREVIEW_URL=http://127.0.0.1:4183 TEST_ENGINE=webkit EVIDENCE_DIR=.cache/check-finance-webkit node studio/scripts/test-finance-ui.cjs
CONTROL_UI_EVIDENCE=.cache/check-offline-NEW node control/scripts/test-ui.cjs
```

Expected current local cases: 50 Studio Python (Linux 49 pass / 1 Windows-only skip),
10 handoff Python, 45 Studio Node,
25 retained Node; 35 UI and 21 finance **per browser**, 78 offline viewer checks.
Counts overlap and are not a product-completion score. Preserve initial red logs.
Fix the actual defect/prerequisite; never remove a security assertion to make green.

For kernel tests, copy the **whole workspace**, keeping `control/` next to `work/`,
then follow `tools/KERNEL_TEST_PROFILE.md`. It needs NEW synthetic state and reviewed
hash-locked Bubblewrap/media tools. Do not test an operating company directory.
The configured namespace-opt-in/no-PostgreSQL run was **1251 pass / 173 skip / 0 fail**.
Keep PG skips unless a separately owned disposable write profile is explicitly created.
Do not use a production DSN. Do not invent placeholder tool binaries or empty agent
folders. Read the exact lock/bootstrap code before any explicit install/download.

### Real owned-QA integration on an approved disposable Linux x86_64 test host

Use the reviewed kernel Python environment and existing Playwright install. Validate
the pinned isolation binary with `python3 work/scripts/bootstrap-isolation.py` first.
Missing tools must fail closed; an explicit reviewed restore is a separate step.
Then use NEW cache/evidence directories:

```sh
python3 work/scripts/prove-control-browser.py --cache .cache/tls-fixtures --evidence .cache/check-gateway-chromium --client control/web/index.html --browser-test studio/scripts/test-gateway.cjs
TEST_ENGINE=webkit python3 work/scripts/prove-control-browser.py --cache .cache/tls-fixtures --evidence .cache/check-gateway-webkit --client control/web/index.html --browser-test studio/scripts/test-gateway.cjs
```

Expected 44 checks per engine plus 5 TLS/lifecycle checks per fixture. The driver
creates synthetic-only private profiles, starts a local HTTPS fixture and stops it
in `finally`. Never distribute that private profile or its pairing/review codes.
Chromium trusts only the disposable SPKI pin with `ignoreHTTPSErrors=false`.
WebKit uses **test-only** `ignoreHTTPSErrors=true` for the self-signed localhost
fixture; it proves application behavior, **not WebKit/native TLS trust**. Python
still independently checks trusted CA, default-store refusal, wrong hostname and
cleartext refusal. Production/native code must never inherit a certificate bypass.

Return: command/environment versions, exit codes, JUnit/JSON, initial failures and
fixes, screenshots and artifact hashes. No fabricated device, human or provider proof.

## Task B — highest next practical native work (R07/R08)

These require real owner-provided machines/devices; stop and ask when absent.

1. **Mac/Xcode:** rebuild shared HTML, run `bash control/scripts/build-ios.sh` on macOS.
   Record `xcodebuild -version`, SDK, architecture and simulator output. Test list/chat,
   safe areas, keyboard, VoiceOver/font scale, offline, background/resume and memory
   eviction. Then use the owner's signing team for an explicitly authorized physical
   iPhone/iPad build. No IPA/TestFlight/store claim before real export and validation.
2. **Windows:** use the full `control/releases/windows-x64/` folder on an owned test
   machine with current Evergreen WebView2 x64. Record OS/runtime, real launch,
   missing-runtime/error behavior, DPI 100–250%, resize, keyboard/Narrator/high contrast,
   suspend/network loss, fresh pairing/revocation and owner-selected-origin refusal.
   Do not bypass corporate trust policy or call an unsigned EXE Authenticode signed.
3. **Android:** use an approved test device/emulator, record OS/API and WebView. Test
   list/chat/search/back, rotation/recreation, large fonts/TalkBack, keyboard, background,
   process death, offline/reconnect, pairing expiry and revoke. Demo signing differs
   from earlier packages; never silently uninstall existing data to update. Owner
   release keystore, recovery, AAB/store work are separate authorized steps.
4. Native file/download restrictions currently remain closed. If implementing them,
   design an owner-reviewed document/export permission boundary, quotas/cancellation,
   no arbitrary native bridge and negative tests. Until then retain the visible browser
   fallback instructions; never toast that a blocked file was saved.
5. Use actual managed/platform TLS trust on native devices. A fixture SPKI flag or
   headless certificate bypass is not a device trust policy or acceptance result.

Build after changes with separately reviewed/pinned SDKs and a NEW private cache:

```sh
python3 studio/scripts/build-web.py
# Set ANDROID_HOME, WEBVIEW2_SDK and OPENBOT_BUILD_CACHE to your reviewed tools/cache.
bash control/scripts/build-windows.sh
bash control/scripts/build-android.sh
# Mac only:
bash control/scripts/build-ios.sh
```

`control/scripts/verify-local-packages.py` verifies binary/assets/static facts, not
launches. Its `--ios-zip` is a temporary source-inspection archive from the actual
`control/native/ios/` tree, not a built app. Keep SDK/demo-signing private caches out
of the final workspace. Review dependency/license pins before changing them.

## Task C — actual-host integration and real services (R03–R06)

Proceed only after the owner names the host/account, permissible data, use case,
install permission, hard cost/exposure cap and stop policy. The present UI is not a
general model/chat, PC or social executor and must not become an arbitrary shell.

1. R03: deploy exact reviewed client/API to one approved HTTPS staging origin; pin
   reviewed bytes through the trusted setup flow. Recheck scopes, exact approvals,
   replay, revocation, cross-venture, expiry, crash recovery and ambiguous outcomes.
2. R04: with an independent qualified reviewer, enforce cgroups/CPU/RAM/PIDs/disk/
   egress/secret/control-plane separation on the real host. Implement one eligible
   provider adapter, streamed/tool-call correlation, durable reservation/idempotency,
   cancellation/uncertain-state reconciliation and independently checked real usage.
   No unattended paid retries; a timeout/spinner/reported cap is not a remote hard cap.
3. R05: provision **real separate guest VMs** only under the approved host/budget.
   Record guest/image/disk/network identity, isolation/resource tests, stop/expiry,
   orphan billing, image updates and restore. Review and pin compatible licensed
   Claude Code, Antigravity and T3 Code installs; authenticate only through approved
   flows. A directory/container/requested IDE name is not the requested per-bot PC.
4. R06: choose one official social platform/account/use case. Revalidate live official
   policies/scopes/quotas and exact action/account/media/privacy/rights/disclosure
   approval. Keep OAuth in a vault and implement token revoke, durable emergency stop,
   ambiguous-effect read-back and no duplicates. No browser-cookie login, spam or evasion.
   Keep X AI replies disabled without prior explicit written platform approval.
   Any owner-approved YouTube upload must explicitly request **private** visibility;
   an upload is still a real external effect, not a harmless preview.

## Task D — external acceptance, not more self-awarded green checks (R09–R13)

- R09: assign independent security/privacy/license reviewers; produce actual threat,
  dependency/SBOM and linked-binary review, remediate/retest findings and arrange real
  terms/privacy/support/security-reporting ownership. Do not call this self-review independent.
- R10: named operator/on-call must witness real deploy/canary/rollback/off-host restore,
  key recovery, vault/grants, failure alerts/monitor-of-monitor and emergency stop.
- R11: independently pre-freeze ≥20 protected held-out tasks/criteria/stop thresholds
  **outside bot-writable work**. Never expose the protected set here then call it held-out.
- R12: real authorized 1–6-month private pilot, including ≥30 consecutive genuinely
  observed days, with consent, incidents, caps and independent acceptance. Current
  accepted days **0**. No clock jumps, calendar-only credit or synthetic day records.
- R13: exact human-approved scope, reviewed terms/on-call, signed accepted artifacts,
  supported platform matrix and observed bounded rollout/rollback. No auto-release.

## Return one successor, not a patch chain

Return one NEW complete workspace ZIP, manifest, exact package/file hashes, scoped
receipts, unresolved R01–R13 rows and the user's next actions. Preserve unique
history/private state. Verify a fresh extraction and byte-identical re-export before
asking the user to replace their downloaded copy. Say precisely what was **not** run.
