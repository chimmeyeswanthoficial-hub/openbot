# OpenBot native control · 0.3.0-local light UI

**Latest native status:** Antigravity reports a Windows 0xc000007b launch failure.
Cause is not established; see `../WINDOWS_LOADER_REVIEW.md`. Git metadata corrections
do not fix this error. No native UI/device acceptance or public release is claimed.

**Repair note:** `../REPAIR_REVIEW.md` records Antigravity-reported Windows process
start/respond/stop. No raw native UI/screenshots/interactive acceptance was supplied;
this is not independent supported-platform acceptance. Binaries are unchanged.

Windows, Android and iOS are **clients**, not agent/PC hosts. The new light reference
interface is generated from `../studio/web/`, shared byte-for-byte with the gateway
and iOS source, and embedded in the fresh Windows/Android **local test builds**.
API v1 / wire client 0.2.0 remains unchanged. See top-level `START_HERE.md` and
`DESIGN_REFERENCE.md`. This is **not a public or production release**.

## Delivery truth

| Target | Actual current artifact | Not yet established |
|---|---|---|
| Windows x64 | `releases/windows-x64/OpenBot-Control-Local-x64.exe`, adjacent pinned WebView2 loader/license/README. Genuine MinGW GUI PE, **unsigned**, light shared UI, explicit trusted-origin confirmation and lifecycle events. | Windows launch/install/DPI/accessibility/OS trust/update/rollback/uninstall acceptance, Authenticode and distribution choice. |
| Android | `releases/OpenBot-Control-Local-android.apk`, 0.3.0-local/code 3, Java/DEX/APK, aligned, **demo v3 signature**, INTERNET only, light chrome and shared HTML. | Emulator/real device/WebView/accessibility/lifecycle acceptance, owner release key/recovery, AAB/store approval. |
| iOS/iPadOS | `native/ios/` SwiftUI/WKWebView/Xcode project + exact light HTML, iOS 16 target. | **No Mac/Xcode compile, simulator/device `.app` or `.ipa`**, provisioning, signing/export/distribution acceptance. Linux build intentionally exits 2. |

`releases/NATIVE_TEST_BUILDS.json` binds current test-artifact/UI hashes. These are
not release signatures. `OS_MATRIX.md`, `RELEASE_STATUS.md`, `PRIVACY_DRAFT.md` and
`../ANTIGRAVITY_NEXT.md` describe the remaining real-device gates.

## Interface / security contract

- Offline is a truthful local workspace, not preloaded current server work or a live
  computer screen. Historical recorded QA/media receipts remain separate evidence;
  `scripts/embed-recorded.py` now refuses to overwrite the shared bundle.
- Owner-approved HTTPS at exact `/control/` is required for connected mode. Scope,
  actor, venture, catalog and budget are server-derived. Displayed companion names
  never grant authority. No native JS authority bridge is installed.
- One-use host-console pairing proves a P-256 key. Private keys are non-exportable
  renderer-memory keys, not hardware keystores. Reload/close needs a fresh grant.
- Exact review needs a **separate** owner console code bound to device/task/digest;
  execution is another explicit request. No implicit mutation retry or provider work.
- Only fixed first-party invoice QA samples and local-review artifacts are accepted.
  Code, source, catalog, approval, expiry and scope are rechecked by the existing kernel.
- Offline/stale/background/in-flight states remove write authority; resume/reconnect
  reads back rather than replaying. Client artifact content is hash checked.
- Platform TLS is never overridden. Native requests/navigation stay on the selected
  HTTPS origin. File access, chooser/downloads, popups and permissions remain denied.
  Paste permitted text locally, or use the shared browser for imports/exports.

Native OS/server selection bars differ from the reference; the content UI is shared.
No live model, mailbox, real VM/IDE, social account or bank connects automatically.

## Try local test packages safely

- **Windows:** keep the whole `releases/windows-x64/` folder together. Current Microsoft
  Evergreen WebView2 x64 Runtime is required; none is auto-downloaded. No adjacent
  `server-origin.txt` means offline. To connect, the owner writes only an approved
  HTTPS origin in that file and confirms the native trust dialog. No passwords/keys
  in it; IPv6 literals are not supported. Read `native/windows/README-Windows.txt`.
- **Android:** only an explicitly approved test-device sideload, if you trust source
  and build. This fresh demo key differs from earlier package keys; do not silently
  uninstall data to update. Use **Server / Session** for the approved HTTPS origin.
- **iOS:** real Mac/Xcode required. Open the project and run `scripts/build-ios.sh` for
  an unsigned simulator build. Device/distribution signing stays with the owner.

The disposable localhost CA/SPKI in browser testing is **not** a native certificate-
installation instruction or a production trust policy. Do not bypass device policies.

## Build from this complete root

Review the recorded tool pins/licenses before use: MinGW-w64, Android platform/build-
tools 35 and Microsoft.Web.WebView2 1.0.2903.40. They are not claimed to be latest.
No SDK, runtime or signing secret is shipped in source.

```sh
python3 studio/scripts/build-web.py
# Set ANDROID_HOME and WEBVIEW2_SDK to separately reviewed tools.
# Set OPENBOT_BUILD_CACHE to a NEW excluded private directory.
bash control/scripts/build-windows.sh
bash control/scripts/build-android.sh
bash control/scripts/build-ios.sh # macOS/Xcode only; Linux exits 2
```

Java uses `--release 8` with Android's platform classpath; D8 compiles/desugars the
callbacks. Windows output is unsigned; Android creates only a local demo identity.
Keep build intermediates and demo/release private keys out of source/evidence.
After changing UI/native source, rebuild and reverify; do not ship stale package hashes.

## Tests and updates

`../ANTIGRAVITY_NEXT.md` gives complete commands and prerequisites.

- `scripts/test-connected.cjs` forwards to the actual shared UI HTTPS regression.
  Chromium uses only the disposable fixture SPKI with `ignoreHTTPSErrors=false`.
  WebKit's optional self-signed localhost application check uses test-only
  `ignoreHTTPSErrors=true`; it is **not** WebKit/native trust evidence. Separate
  real Python CA/default-trust/wrong-host/cleartext negatives still run.
- `scripts/test-ui.cjs` runs the shared offline HTML inside opaque `allow-scripts`
  iframes in Chromium/Linux WebKit, with no network or forms/storage authority.
- `scripts/verify-local-packages.py` checks actual PE/DEX/APK/UI/signature/alignment/
  version facts and static sources; **not** native launch or supported-device proof.
- Kernel `verified_updates.py` is a Linux-host local verifier/stager, not an OS-signed
  native updater/installer. JSON signatures are not Authenticode/Apple/release-key signing.

Reconstruct prior source into a NEW directory to inspect/roll back; never overlay
operating data. Revoke a device on the server before native removal. The guarded
Windows cleanup helper is owner-run and not Windows-tested here. No registry autorun,
service, background agent, push/merge/deployment or store release is performed.
