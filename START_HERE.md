# Start here — OpenBot OS complete codebase

**Latest increment:** authenticated history/reuse/real-world plan — read
[AUTHENTICATED_HISTORY.md](docs/openbot-os/AUTHENTICATED_HISTORY.md),
[FEATURE_REUSE.md](docs/openbot-os/FEATURE_REUSE.md),
[REAL_WORLD_ROLLOUT.md](docs/openbot-os/REAL_WORLD_ROLLOUT.md), then
[OPENBOT_OS.md](OPENBOT_OS.md),
[the upstream review](docs/openbot-os/UPSTREAM_REVIEW.md) and
[active work orders](docs/openbot-os/WORK_ORDERS.md). The older repair reports and
package receipts remain historical. Current source is based on reviewed
`9f5600d1fd285e79922fbf69a2abce5243cb9291`; no new native acceptance is implied.

**One canonical workspace, not folder replacement.** If you already have the Git
checkout, preserve your changes and use normal reviewed Git integration. Never
delete/reset/clean/overlay the laptop folder. For a fresh complete download, use a
new directory and retain backups. The private whole-workspace download is not a
public product release and contains owner/recovery material outside this repo.
No new full ZIP is claimed by this foundation; a small Git bundle is only commit
transport for the existing repository.

In a Git clone, run `python tools/verify-git-source.py --ref HEAD` and inspect
`git status --short` separately. For a clean manifest-only, mode-preserving source
extraction, use `python tools/verify-source.py --strict`; `.git/` is not part of
that extraction. Identity verification is not runtime, license or release approval.

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
| Windows x64 | `control/releases/windows-x64/OpenBot-Control-Local-x64.exe` | Unsigned portable **test build**. Keep `WebView2Loader.dll`, license and README beside it; current Microsoft Evergreen WebView2 x64 Runtime required. Reported native Windows launch error 0xc000007b is unresolved; not accepted. |
| Android | `control/releases/OpenBot-Control-Local-android.apk` | Version 0.3.0-local / code 3, aligned, **demo v3 signature**, not a release identity. No emulator/device acceptance or Play/AAB release. Optional test-device sideload only if you trust the source and accept the risk. |
| iOS/iPadOS | `control/native/ios/OpenBotControl.xcodeproj` | Shared light UI and Swift/Xcode source only. **No `.app` / `.ipa`.** A real Mac/Xcode, simulator, device, provisioning and your signing team are required. |

All three **source payloads** use the same generated UI bytes. The retained EXE/APK
still embed the previous UI and were not rebuilt; see
`docs/openbot-os/NATIVE_BUILD_STATUS.md`. Native trusted-server controls and OS
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

## 3a. Optional authenticated history, not live chat

The existing gateway can now receive an explicitly initialized `ConversationAPI`
through trusted host setup. It is **off by default** and not exposed by the public
planner or wired into Studio chat. Old generic grants gain no history authority.
See [the contract](docs/openbot-os/AUTHENTICATED_HISTORY.md) and the real file-backed/
signed-device/TLS tests. No production DB, owner pairing or host state was changed.
The official AG-UI schema is actually reused for a namespaced CUSTOM-event test;
no complete stream/runner or model connection is implied.

## 4. Verify before changing anything

```sh
# Git clone:
python3 tools/verify-git-source.py --ref HEAD
# Clean ZIP extraction instead: python3 tools/verify-source.py --strict
python3 -m unittest discover -s studio/tests -p 'test*.py' -v
python3 -m unittest discover -s tools/tests -p 'test*.py' -v
node --test studio/tests/*.test.cjs
```

The read-only manifest verifier does not install or contact anything. Current
counts/logs are in `evidence/openbot-os-history/VERIFICATION.md` (selected gateway+
journal: 473 passed / 87 PG skips, including 58 new HTTP history cases); older
foundation evidence remains in `evidence/openbot-os-foundation/VERIFICATION.md`; Windows reports must use actual
Windows outcomes/skips, not copied Linux counts. New standalone journal tests are
in `OPENBOT_OS.md`. The older configured whole-kernel result (1,251 passed / 173
PostgreSQL skips), 27 native static checks and earlier browser receipts remain
historical, not freshly rerun acceptance. Old-package/new-HTML equality is now
intentionally false until separately reviewed native rebuilds.

**Kernel tests:** copy this **entire workspace** into a disposable directory, keeping
`control/` beside `work/`. Read `tools/KERNEL_TEST_PROFILE.md` before preparing NEW
synthetic state and reviewed locked tools. Never restore private operating state
or use a production DSN to make a test green. The 1,424-pass fully provisioned older
runs remain historical, not the current no-PostgreSQL result.

## 5. File map and next actions

| Path | Purpose |
|---|---|
| `PUBLIC_RELEASE_ROADMAP.md` | All R01–R13 requirements, current status, dependencies and human gates |
| `docs/openbot-os/WORK_ORDERS.md` | Active OpenBot OS engineering/build/device/security tasks and evidence to return |
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
