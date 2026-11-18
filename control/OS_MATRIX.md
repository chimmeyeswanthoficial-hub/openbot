# Native target matrix — engineering targets, not certified support

All current native content comes from the same light shared HTML (0.3.0-local test
shells; API v1 / wire client 0.2.0). Exact embedded/bundled asset identity and light
source/chrome are checked. Native controls and OS bars differ from the reference;
compilation or Linux WebKit is not device/OS acceptance.

| Target | Engineering target / requirements | Actual current evidence | Still-required external acceptance |
|---|---|---|---|
| Windows x64 | Windows 10 1809+/11, current Evergreen WebView2 x64, owner-approved HTTPS, no admin elevation requested | Linux MinGW 0.3.0 GUI PE compile, exact embedded light UI, pinned loader, version/assembly resource, imports/mitigation/unsigned facts | Actual Windows launch, runtime/missing-runtime behavior, install/portable choice, DPI 100–250%, Narrator/keyboard/high contrast, suspend/network loss, upgrade/rollback/uninstall and Authenticode |
| Android | API 28+ / target 35, System WebView Chromium 100+ target, INTERNET only, cleartext disabled | Java/DEX/APK build, exact light UI, code 3 / 0.3.0-local, alignment and real **demo v3** signature, permissions/manifest/source checks | Real devices/emulator/WebView matrix, TalkBack/font scaling, back/rotation/recreation/process death, background/resume, TLS trust, owner release key/recovery, AAB/store policy if selected |
| iOS/iPadOS | Project iOS 16+ / Xcode 15+ target, platform TLS, no ATS cleartext exception | SwiftUI/WKWebView/Xcode/plist source, light appearance and byte-identical HTML/static parsing only; actual Linux build exits 2 | **Real Mac compile**, simulator/iPhone/iPad, VoiceOver/dynamic type, keyboard/safe areas/background/TLS, provisioning/signing/export, TestFlight/store if selected; **no `.app`/`.ipa` exists here** |
| Browser fixtures | Reviewed Playwright 1.56.1 cached Chromium/Linux WebKit | Actual 44 HTTPS application checks/engine; 35 UI + 21 finance/engine; combined 78 offline viewer checks | Not native compatibility, hardware-keystore, OS trust or independently qualified accessibility acceptance |

Chromium HTTPS fixtures use exact disposable SPKI with `ignoreHTTPSErrors=false`.
WebKit's self-signed localhost **test-only** application fixture uses
`ignoreHTTPSErrors=true`, explicitly **not WebKit/Apple/native TLS-trust evidence**.
Independent Python CA/default-store/wrong-host/cleartext checks remain separate.
Native clients never override certificate errors and allow only an owner-selected
HTTPS origin; this is not an OS-wide firewall.

Private device keys live only in renderer memory, not Secure Enclave/Android
Keystore/TPM. Reload loses pairing. Native test shells block file pickers/downloads;
use permitted pasted text or browser imports/exports. No authority bridge was added.

Release-signing/store/distribution choices remain with the owner. No App Store/Play
approval, SmartScreen reputation, production deployment or accepted platform support
is promised. See `RELEASE_STATUS.md` and `../ANTIGRAVITY_NEXT.md` for the next tests.
