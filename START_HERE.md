# Start here — one complete OpenBot workspace

**Engineering preview, not a public release.** Extract this ZIP into a **new folder**.
Do not apply old patches or overlay an operating company directory. The kernel,
shared light interface, native source, explicit local test binaries, licenses,
tests, evidence and next instructions are together here.

## Current repair note

This is `OpenBot-Workspace-Verified-Complete.zip`, one full successor, not a patch.
The 258 missing Git files are restored; no repetition of that repair is needed.
Read `REPAIR_REVIEW.md`. Arena reconstructed the pinned public source; your laptop
ZIP was not uploaded. `result.md` is an attributed report, not independent acceptance.

On Windows, extract into a **new** directory. If Explorer fails/skips entries, use
Python's ZIP tools and require success; do not disable antivirus/device policy:

```powershell
python -m zipfile -t .\OpenBot-Workspace-Verified-Complete.zip
python -m zipfile -e .\OpenBot-Workspace-Verified-Complete.zip .\OpenBot-Verified-New
```

Then run the strict verifier inside `OpenBot-Verified-New\OpenBot-Workspace`.
On POSIX use a mode-preserving extractor such as `unzip` (Python zipfile extraction
alone does not restore original modes). Keep old files/backups; do not overlay data.

## 1. Try the light interface

From this root with Python 3.11+:

```sh
python3 studio/src/studio.py serve --bind 127.0.0.1 --port 4183
```

Open `http://127.0.0.1:4183` on that computer. No package install or account key is
needed for local planning. On Arena's shared preview use `--bind 0.0.0.0`; browser
code uses relative URLs. This development server is **stateless, public planning**,
not a production perimeter or confidential-data vault.

Desktop: companion sidebar / conversation / computer-and-routine requests.
Mobile: pinned companions and list → selected conversation → Back. Original letter
avatars replace the reference's closed artwork. The default screen shows no invented
messages; **See design example** is explicitly fictional. Briefs are human input,
not live AI responses. A computer placeholder is not a real screen or allocated PC.

Opening `studio/web/index.html` directly works for local briefs/navigation/CSV.
Full companion/social planning validation needs the development server. The gateway
is deliberately not proxied through this public planner.

## 2. Windows, Android, iOS

| Target | Where to find it | Honest status |
|---|---|---|
| Windows x64 | `control/releases/windows-x64/OpenBot-Control-Local-x64.exe` | Unsigned portable **test build**. Keep `WebView2Loader.dll`, license and README beside it; current Microsoft Evergreen WebView2 x64 Runtime required. Not launched on Windows here. |
| Android | `control/releases/OpenBot-Control-Local-android.apk` | Version 0.3.0-local / code 3, aligned, **demo v3 signature**, not a release identity. No emulator/device acceptance or Play/AAB release. Optional test-device sideload only if you trust the source and accept the risk. |
| iOS/iPadOS | `control/native/ios/OpenBotControl.xcodeproj` | Shared light UI and Swift/Xcode source only. **No `.app` / `.ipa`.** A real Mac/Xcode, simulator, device, provisioning and your signing team are required. |

All three use the same generated UI bytes. Native trusted-server controls and OS
status/window bars differ. Native test shells intentionally block file pickers and
downloads; paste permitted local text, or use the browser for file import/export.
No native bridge, file access or certificate bypass was added to imitate a screenshot.
No model, mailbox, VM, IDE or social account connects automatically.

## 3. Authenticated owned-QA — a separate, narrow mode

`studio/web/gateway-session.js` speaks the existing API v1 / wire client 0.2.0.
Only an owner-approved HTTPS gateway serving **this exact bundle at `/control/`**
enables pairing. The server derives identity/role/venture/scopes. A console pairing
code is not an approval code. Exact review requires a separate console code, then
a separate execution confirmation. Only the three bundled first-party invoice QA
samples and local-review destination are accepted; provider exposure is USD 0.00.

Actual disposable HTTPS fixture tests pass; this is **not production pairing**.
Follow `studio/docs/INTEGRATION_CONTRACT.md` and `ANTIGRAVITY_NEXT.md` for reproduction.
The kernel needs its reviewed dependencies and locked isolation prerequisites.
Do not paste API keys, OAuth tokens, passwords, signing keys or production secrets
into chat, browser drafts or fixture commands.

## 4. Verify before changing anything

```sh
python3 tools/verify-source.py --strict
python3 -m unittest discover -s studio/tests -p 'test*.py' -v
python3 -m unittest discover -s tools/tests -p 'test*.py' -v
node --test studio/tests/*.test.cjs
```

The read-only manifest verifier does not install or contact anything. There are
50 Studio Python cases (Linux 49 passed / 1 Windows-only skip), 10 handoff tests,
19 finance and 26 gateway Node unit tests.
Browser and native package checks have separate prerequisites and evidence. The
configured kernel run has **1,251 passed, 173 PostgreSQL skips, zero failures/errors**;
that is not a claim that unconfigured `pytest` passes or that skipped tests ran.

**Kernel tests:** copy this **entire workspace** into a disposable directory, keeping
`control/` beside `work/`. Read `tools/KERNEL_TEST_PROFILE.md` before preparing NEW
synthetic state and reviewed locked tools. Never restore private operating state
or use a production DSN to make a test green. The 1,424-pass fully provisioned older
runs remain historical, not the current no-PostgreSQL result.

## 5. File map and next actions

| Path | Purpose |
|---|---|
| `PUBLIC_RELEASE_ROADMAP.md` | All R01–R13 requirements, current status, dependencies and human gates |
| `ANTIGRAVITY_NEXT.md` | Exact next engineering/build/device/security tasks and evidence to return |
| `YOUR_NEXT_STEPS.md` | Your download, preview, scope and host/account/device decisions |
| `DESIGN_REFERENCE.md` | Shared light UI implementation and deliberate OS/asset/truth boundaries |
| `studio/` | Shared UI source, deterministic planning CLI/server, original integration, tests and OpenMuse notices |
| `control/` | Native sources, pinned build/verification scripts and labeled local test artifacts |
| `work/` | Preserved independent kernel, routines/declaration, configuration, retained attributed donors and tests |
| `evidence/reference-interface/` | Current local evidence, scoped failures, screenshots and receipt index |
| `evidence/openmuse/` | Historical predecessor adoption evidence, not current native acceptance |
| `SOURCE_MANIFEST.json` | File identity and explicit exclusions; not a signature |

`work/.openbot/` contains only reviewed routine templates and one required venture
source declaration, not runtime grants/budget state/databases. Illustrative caps
are not spending authorization. The optional upstream reference source is retained;
not all source is integrated, licensed for every service or an installed runtime.

Use `tools/export-source.py --output /a/new/location/OpenBot-Workspace.zip` to
re-export the verified manifest-listed workspace. It never overwrites a target.
The explicit test EXE/APK are included; private build/signing material is not.

**Nothing here closes R01–R13 in full.** Real providers/PCs/IDEs/social, native
acceptance/signing, independent reviews, witnessed operations, protected evaluation,
the real pilot and human release remain. Accepted genuine observed pilot days: **0**.
Save your downloaded ZIP outside Arena; a live preview or session cache is not a backup.
