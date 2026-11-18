# iOS control target — SOURCE ONLY

No Mac/Xcode/simulator/iPhone was available for this local run. No `.app` or `.ipa` was produced. Linux `scripts/build-ios.sh` exits 2 by design.

On an owner-controlled Mac with Xcode 15+ and the iOS SDK:

1. Copy the shared `web/index.html` to `native/ios/OpenBotControl/index.html` if rebuilding from source.
2. Inspect `ControlApp.swift`, `PreviewWebView.swift`, the project, Info.plist and privacy template. Select your own bundle identity, team and provisioning only after review. No identity is auto-created or uploaded by these scripts.
3. `bash scripts/build-ios.sh` requests an unsigned simulator build. A simulator `.app` is not an installable iPhone IPA.
4. Test explicit native HTTPS origin selection, default Apple TLS rejection, pairing/revocation, VoiceOver/dynamic type, navigation, process recreation, background/resume and reconnect on actual supported devices. Keys are renderer-memory-only, not Secure Enclave identities.
5. Finalize privacy, encryption/export declarations, owner-controlled signing, archive/export and TestFlight/App Store submission if selected. Those are external owner-authorized steps, not source ZIP features.

Execution stays on the protected Linux server. No provider key or agent runtime goes into this app. The ephemeral WebView permits only the selected HTTPS origin, rejects popups/media permission requests, and installs no native JS bridge. These source restrictions require native validation; Linux browser checks are not that evidence.
