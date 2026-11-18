# Verification — light-reference-1 engineering checkpoint

**Public release: false. Accepted genuinely observed pilot days: 0.**
This is measured local engineering evidence, not an independent security review,
a completed R01–R13 roadmap, native-device acceptance or production authorization.
Original runner, donor and predecessor timestamps are retained as observations;
none creates elapsed pilot time. Counts below overlap and must not be added into
a feature-completion percentage.

## Current observations

| Check / exact scope | Result | Receipt under `evidence/reference-interface/` |
|---|---|---|
| Studio standard-library source/build/export/planning/HTTP/native-source tests | **48 passed** | `unit-final/studio-python.log` |
| Source-handoff / synthetic-state tool tests | **8 passed** | `unit-final/handoff-python.log` |
| Studio Node units: attributed CSV 19 + gateway protocol 26 | **45 passed**, no skips | `unit-final/node.log` |
| Retained queue/findrepo dependency-free Node profile | **25 passed**, no skips | `retained-node/run.log` |
| Shared light UI, responsive navigation, truthful drafts and accessibility-related regressions | **35 passed per engine**, no page errors | `ui-final/{chromium,webkit}/` |
| Browser-local CSV/finance workflow, privacy/races/exact integers | **21 passed per engine**, no page errors | `finance-final/chromium/`, `finance-fixed/webkit/` |
| Opaque offline `allow-scripts` viewer, Chromium + Linux WebKit | **78 checks passed**, no page errors | `offline-initial/viewer-checks.json` |
| Actual HTTPS shared UI → authenticated kernel → owned QA | **44 passed per engine**, no page errors | `gateway-final-chromium/`, `gateway-webkit-fixed/` |
| Actual HTTPS fixture TLS/lifecycle checks | **5 passed per fixture run** | Each current gateway folder's `s08-tls.json` |
| Actual PE/DEX/APK/assets/version/alignment/signature plus native static-source facts | **27 passed**; no native launch or iOS compilation | `native/packages-current.json`, `native/package-verification-current.log` |
| Configured complete-workspace kernel, namespace opt-in / locked real tools / no PostgreSQL | **1,251 passed / 173 PostgreSQL skips / zero failures or errors** | `kernel/namespace-opt-in.{log,xml}` |
| Selected Python lint/format | Ruff clean; **14 files** formatted | `unit-final/ruff.log` |
| Running light preview payload | HTTP 200; exact current **127,185 bytes** | `preview-final.json` |
| Original saved workspace and immutable prior archives | **4,212 files / 127,999,912 bytes** byte/size/mode unchanged; originals not deleted/repacked | `preservation.json` |

Browser evidence uses separately installed Playwright 1.56.1 and Chromium/Linux
WebKit, not Safari/iPhone/Android/Windows runtime tests. All owned-QA and finance
inputs are synthetic. No live provider, real VM/IDE, social/bank account, paid
activation or public deployment is established by these tests.

### What the connected regression actually does

At the exact HTTPS `/control/` path, the real shared renderer creates a non-exportable
P-256 memory key, pairs using a one-use console grant, and receives server-derived
actor/venture/scopes. It proposes each of three fixed first-party invoice QA samples.
An independent **console interface**, not an independent human evaluator, issues a
separate exact task/digest/device review code; approval queues without executing.
Explicit execution then produces actual local artifacts, whose bytes/hash/content,
scoped audit and exact-book records are read back through the signed API.

Negative cases exercise invalid review codes, untrusted text, real proof replay,
wrong paths/forged signatures/viewer/other-venture denial, revocation, lost responses
with **no implicit mutation retry**, explicit refresh/cancellation, stale/offline and
native-style pause/resume events. This is bounded actual local integration, **not**
general AI chat, arbitrary commands, a real computer screen or production pairing.

### TLS is not interchangeable evidence

- Chromium trusts only the disposable fixture's exact SPKI;
  `ignoreHTTPSErrors=false`. This is not a general certificate bypass.
- Linux WebKit's self-signed-localhost **application** fixture uses test-only
  `ignoreHTTPSErrors=true`. Its 44 passing cases do **not** prove WebKit/Apple/native
  certificate trust. The exception stays in the test driver, not native clients.
- Separate actual Python TLS checks validate the fixture CA, default-store refusal,
  wrong-host refusal and cleartext refusal; fixture shutdown is also checked.
- Native clients never override platform TLS errors. Real devices must use their
  actual managed/platform trust policy. No production CA installation was done.

## Current native artifacts

`control/releases/NATIVE_TEST_BUILDS.json` binds all packaged test-build files and
the exact shared UI. These hashes are identity, **not release signatures**.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `control/releases/windows-x64/OpenBot-Control-Local-x64.exe` | 448,512 | `ebcf4927302840f5b73f85e674590538569a0150703f55393d850f149be7bcdc` |
| Adjacent `WebView2Loader.dll` | 165,968 | `462b36fd1be6ca9f7563466a89e57c41ef4a4def3e0a84fa885d203aea4a3aaf` |
| `control/releases/OpenBot-Control-Local-android.apk` | 53,589 | `533ed5b781d4b04dc0420d6f60e7f994799912b60422d7b141f717af14550c56` |
| Identical Studio/gateway/iOS bundled HTML | 127,185 | `bb99d979376841815bc5dcfe7c942bed28b36f2b87a0b3b80d8d366e5b8b3c67` |

- Windows: genuine x64 GUI PE, ASLR/NX/high-entropy flags, matching 0.3.0 version
  resource/assembly identity, exact shared UI, **no Authenticode signature**. Keep
  loader/license/README together. Current Microsoft Evergreen WebView2 x64 required.
  Built on Linux; **no Windows launch, trust, DPI/a11y, update or uninstall acceptance**.
- Android: package `dev.openbot.controlpreview`, code 3 / `0.3.0-local`, min API 28 /
  target 35, real DEX, alignment and **demo v3 signature** verified. INTERNET only;
  cleartext/backup/debugging disabled. Demo certificate SHA-256:
  `132a0d33eacd39271fb85fcd54787a8367839cbbe7f336f54a2c144c2985ae22`.
  No emulator/device launch, owner release key/AAB/Play acceptance. Changed demo
  keys can make prior installs incompatible; no automatic uninstall is authorized.
- iOS: SwiftUI/WKWebView/Xcode/plist/privacy **source only**, same light HTML and
  light appearance source. Actual Linux build exits **2**, explaining missing
  Mac/Xcode. **No `.app`, `.ipa`, simulator/device, provisioning or signed export**.
  The temporary source ZIP used by the static checker is not a built application
  or a separate release artifact and is not included as a nested delivery ZIP.
- Native test shells retain restrictive file/download/origin/permission boundaries.
  No authority bridge, arbitrary file access or certificate bypass was added for
  visual parity. Native controls and OS chrome differ from the reference.

## Retained initial failures and narrower profiles

The evidence index describes the red-to-green sequence; initial failures were not
erased or silently reclassified as accepted results.

- `ui-initial/webkit`: Escape navigation regression; corrected to 35/35.
- `finance-initial/webkit`: teardown assertion raced an absent gateway badge; explicit
  synchronization corrected the harness, preserving financial/privacy assertions.
- `gateway-initial`: exact locked mode-0755 Bubblewrap missing; real reviewed hash-
  pinned file restored, never replaced by a stub or weaker isolation fallback.
- `gateway-configured`: loss-injection hook installed after app startup; moved before
  startup. `gateway-loss-fixed`: offline render assertion raced; explicit wait added.
- `gateway-webkit`: final revocation DOM assertion raced; wait for no freshness,
  no busy mutation and disabled proposal preserved the actual denial checks.
- `kernel/configured.*`: work-only test layout caused 24 missing-sibling setup errors
  (1199 pass / 201 skip). Complete workspace fixed the layout (1223 / 201); documented
  namespace opt-in plus locked real media tools produced **1251 / 173 / zero errors**.
  No PostgreSQL service/write profile was used. Older 1424-pass provisioned runs are
  historical, not the current result; skipped tests did not pass.
- `native/earlier-local-build/`: earlier local package facts, before final Windows
  assembly-version correction and the added light iOS plist assertion. Current
  `native/packages-current.json` and current build logs are authoritative.

## Reproduce and understand the boundary

From the complete extracted root:

```sh
python3 tools/verify-source.py --strict
python3 -m unittest discover -s studio/tests -p 'test*.py' -v
python3 -m unittest discover -s tools/tests -p 'test*.py' -v
node --test studio/tests/*.test.cjs
node --test work/packages/bot-hq-queue/serial-queue.test.mjs work/tools/findrepo/test/*.test.mjs
```

`ANTIGRAVITY_NEXT.md` provides exact browser/gateway/native commands, reviewed
prerequisites, new private fixture directories and evidence to return. Kernel tests
need the **whole** disposable workspace, synthetic non-operating state and real
locked isolation/media prerequisites: read `tools/KERNEL_TEST_PROFILE.md`. A bare
unconfigured pytest can fail closed. Do not alter operating data or use production
DSNs to make tests green. SDKs/dependencies/private fixtures are not shipped here.

## Packaging and preservation

The manifest-listed combined workspace includes kernel, full retained optional
upstream reference source, shared UI, native source and **explicitly labeled local
test EXE/APK/loader**, tests, notices and scoped evidence. It is not merely a UI
module export, a patch chain, or a runtime backup. All **3,475** optional upstream
files are retained, not silently omitted to reduce size.

Private operating state, owner uploads, historical delivery/recovery archives,
dependency/tool caches, private fixture credentials and private signing/build caches
are excluded from this export, **not deleted from the originals**. Two audited old
archives each contain unique recovery/history entries, so neither was removed.
The immediate parent ZIP remains unchanged:
`657c89aec18c3410cdb9ef7972ba53713337ca307391ce057dfe97b53024c9d6`.

Before presentation the final ZIP is checked by safe fresh extraction, strict
manifest verification, extracted unit/source checks and **byte-identical re-export**.
A post-export delivery receipt is recorded separately rather than inserted into its
own hash. The conversation supplies the final ZIP's actual hash and file card.
Manifest/hash checks do not establish signer identity, complete secret clearance,
account rights, native safety, real-host controls or release approval.

## Still open

Real host/provider cost controls and independent hostile-host review; real per-bot
VMs and authenticated IDEs; official social integrations; native machines/devices,
signing and updates; independent security/privacy/license/accessibility acceptance;
witnessed operations/key recovery/on-call; ≥20 protected independently evaluated
held-out tasks; consented 1–6-month pilot including ≥30 consecutive genuinely observed
days; exact human release authorization. See `PUBLIC_RELEASE_ROADMAP.md` R01–R13.
No reviewer, account, IDE message, pilot day or background progress was invented.
