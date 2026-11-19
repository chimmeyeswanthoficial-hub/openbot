# OpenBot OS — source-first foundation

**Decision:** build OpenBot OS as an independently governed, open-source agent
workspace/control plane. This is not a new operating-system kernel or an official
CopilotKit product. Keep the requested light desktop/mobile companion design.
Retain the existing kernel, recovery history and useful MIT reference source;
do not replace the workspace with an upstream checkout.

**Base reviewed:** `9f5600d1fd285e79922fbf69a2abce5243cb9291`.
This foundation is a local engineering successor, not an upstream merge, remote
publication, accepted native release or finished autonomous company.

## Answer: is CopilotKit the core backend engine?

**Not the whole engine.** Its open-source SDK supplies frontend hooks/components
and a runtime mounted in an application server. The runtime brokers streams and
tools to an AG-UI-compatible agent, which can be an in-process BuiltInAgent or an
external framework. Identity, policy, databases, jobs, computers, credentials,
spending and operations are still application responsibilities.

**CopilotKit Intelligence is separate.** Its platform-backed threads, memory,
learning and other services have separate terms. Self-hosting a service does not
make it open source. The TypeScript runtime can work without Intelligence, and
the reviewed SDK even documents local runners; a persistence component is not
exclusive to our project. See the pinned code and official sources in
[the upstream review](docs/openbot-os/UPSTREAM_REVIEW.md).

Our decision is **AG-UI interoperability, optional MIT CopilotKit TypeScript
runtime/UI adapters, project-owned authoritative state and governance**. No
mandatory Intelligence account, cloud license renewal or opaque backend image
for the intended OSS core. Optional commercial services must not gate core startup.

## What this change actually builds

- **OpenBot OS identity:** root MIT license and explicit third-party boundaries;
  visible browser/iOS-source/shared-gateway branding, with the light design kept.
  Protocol IDs, pairing semantics and existing native package IDs are unchanged.
  A measured selected-contact text contrast issue is corrected without a layout change.
- **Application-owned conversation journal:** real SQLite persistence, explicit
  tenant/principal query scopes, atomic ordered appends, idempotent retries,
  conflict detection, byte-bounded replay pages, quotas and logical deletion.
  **31 new tests** exercise real disposable databases, competing connections,
  transaction rollback, reopen and a child-process abrupt exit after commit.
  This is an inert backend library, **not wired into live chat, HTTP auth or the
  Studio UI**, and not a complete AG-UI runner. [Component contract](docs/openbot-os/CONVERSATION_JOURNAL.md).
- **Opt-in Windows diagnostic-text capability:** schema-4 collector reads only
  OS-reported debug-string byte ranges from its own newly created target,
  capped at 16 KiB/event and 256 KiB/session. Default remains no payload reads.
  Twenty new fake-backend tests cover bounds, Unicode, errors and CLI behavior.
  No Windows ABI/native run, registry edit, install or loader-snaps approval is
  implied. [Capture/permission plan](docs/openbot-os/WINDOWS_DEBUG_TEXT.md).
- **Pinned upstream analysis and implementation work orders:** source boundaries,
  feature/function/frontend review, reuse decisions and measurable acceptance
  targets, rather than an unqualified “better than OpenBot” claim.

The generated shared HTML is now newer than the retained EXE/APK. Those binaries
are intentionally unchanged diagnostic/history artifacts, **not OpenBot OS
builds**. [Native build status](docs/openbot-os/NATIVE_BUILD_STATUS.md).

## Fresh bounded checks

| Check | Result |
|---|---|
| Tools | 77 passed (new payload tests use fake Win32, not Windows execution) |
| Studio Python | 51 passed / 1 skipped |
| New standalone SQLite journal | 31 passed |
| Node | 70 passed |
| Linux Chromium smoke | 21 grouped checks passed; desktop/mobile screenshots retained |
| Source formatting/lint | Passed for the seven scoped Python files |

[Measured evidence and exclusions](evidence/openbot-os-foundation/VERIFICATION.md).
Selected-contact text contrast improved from 4.246:1 to 4.644:1; this is not a
full WCAG/native/device acceptance claim. Optional browser reproduction uses an
already-approved Playwright 1.56.0/Chromium setup and a running public planner:
`python studio/scripts/smoke-openbot-os.py --output-dir NEW_PRIVATE_DIRECTORY`.
The script never installs tools, starts a service, pairs or uses real accounts.

## Read in this order

1. [Upstream review and feature gaps](docs/openbot-os/UPSTREAM_REVIEW.md)
2. [Architecture and measurable differentiation](docs/openbot-os/ARCHITECTURE.md)
3. [Antigravity/Arena work orders](docs/openbot-os/WORK_ORDERS.md)
4. [License boundaries](THIRD_PARTY_NOTICES.md)
5. Standing [R01–R13 roadmap](PUBLIC_RELEASE_ROADMAP.md), which remains in force.

## Verify the bounded foundation

From this repository root, Python 3.11+ and Node 18+:

```sh
python -m unittest discover -s tools/tests -p 'test*.py' -v
python -m unittest discover -s studio/tests -p 'test*.py' -v
node --test studio/tests/*.test.cjs work/packages/bot-hq-queue/serial-queue.test.mjs work/tools/findrepo/test/*.test.mjs
```

New journal only (no third-party packages, providers or database service):

```sh
# POSIX
PYTHONPATH=work/services/sentinel python -m unittest discover -s work/services/sentinel/tests -p 'test_conversation_journal.py' -v
```

```powershell
# Windows PowerShell, in this repository; session-local module path only
$env:PYTHONPATH = (Resolve-Path .\work\services\sentinel).Path
python -m unittest discover -s work/services/sentinel/tests -p test_conversation_journal.py -v
```

Committed identity: `python tools/verify-git-source.py --ref HEAD`.
Working-file identity: `python tools/verify-source.py`. Strict verification belongs
on a clean manifest-only extraction, not a Git directory containing `.git/`.
Identity checks are not licensing, security, live-provider or native acceptance.

## Delivery and human boundaries

One canonical project remains under `openbot/`; no laptop folder deletion,
replacement, reset/clean or force-push. Use ordinary reviewed Git changes. A small
Git bundle, if supplied outside the repository, is commit transport for the
existing checkout, not a replacement workspace or a chain of source patches.
The private **whole-workspace download** is recovery/continuation material, not
something to publish publicly; preserve its vault dependencies and owner files.

Arena can lead code, architecture, tests and handoffs. No direct Antigravity
channel, external agent team or authenticated remote writer was established.
Work orders are ready for an actual receiving agent, not evidence it has run.
The owner keeps legal ownership, accounts, host/install/spend/signing decisions
and final release authority. No continuous background work is implied.

**Public release: false. Genuine accepted pilot days: 0.** Provider, real per-bot
VM, official social, IDE, native/device/signing, independent review, operations,
protected evaluation and the 1–6-month pilot including ≥30 consecutive genuinely
observed days remain open. This change does not silently shrink that scope.
