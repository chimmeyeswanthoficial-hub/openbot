# Native build status — preserve the diagnostic baseline

The OpenBot OS source-branding change rebuilds the three shared HTML payloads
(`studio/web/index.html`, `control/web/index.html`, and the iOS source asset) from
one template. They are byte-identical, **127,581 bytes** at this foundation.
Layout, protocol IDs, pairing and native authority restrictions are unchanged.
The selected-contact text color has one measured normal-text contrast correction.
The JavaScript copy now also states that old packages were not rebuilt and the
journal is not a live chat engine; the generated script CSP digest is updated.

The retained Windows EXE and Android APK **were not rebuilt**. Their embedded UI
is the prior 127,185-byte shared asset at base
`9f5600d1fd285e79922fbf69a2abce5243cb9291`. They are historical local test builds,
not packages of this new OpenBot OS source. Existing binary/static verification
receipts remain historical; a verifier requiring the *new* HTML inside those old
packages should fail. Do not change that verifier or counterfeit a fresh pass.

| Artifact retained | SHA-256 | Status |
|---|---|---|
| `control/releases/windows-x64/OpenBot-Control-Local-x64.exe` | `ebcf4927302840f5b73f85e674590538569a0150703f55393d850f149be7bcdc` | Unsigned AMD64 local test PE; supplied Windows run exits `0xc000007b`. No root cause or accepted UI. |
| Adjacent `WebView2Loader.dll` | `462b36fd1be6ca9f7563466a89e57c41ef4a4def3e0a84fa885d203aea4a3aaf` | Historical Microsoft redistributable; own terms. Mapping it does not establish application startup. |
| `control/releases/OpenBot-Control-Local-android.apk` | `533ed5b781d4b04dc0420d6f60e7f994799912b60422d7b141f717af14550c56` | Demo-key-signed 0.3.0-local/code 3; no accepted device launch. |
| iOS/iPadOS | Source only | Updated shared source; no Mac/Xcode build, IPA, device or signing acceptance. |

Preserve the failing Windows bytes, adjacent DLL, raw traces and hashes for
controlled comparisons. A later new native build must have its own identity,
embedded-source pin, toolchain/SDK/license receipt, new source manifest and actual
native install/launch/lifecycle/manual-interaction evidence. Do not overwrite an
old trace or infer an earlier cause because a differently built binary works.

The newly generated gateway client also needs a newly reviewed client-hash pin in
a **new disposable fixture/profile** before authenticated QA acceptance. Do not
change a paired owner's live allowlist or weaken TLS/origin/hash checks to load it.
R08/native release remains blocked; signing and Windows startup are separate gates.
