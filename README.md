# OpenBot OS

**A source-first, governed AI workspace under active development.** Keep the
owner's light desktop/mobile companion design; build around our independent
kernel and open protocols, not a mandatory licensed cloud backend.

Start with **[OPENBOT_OS.md](OPENBOT_OS.md)** for the architecture decision, real
implementation status, pinned upstream review and Antigravity work orders.
[START_HERE.md](START_HERE.md) explains the existing local interface and checks.

## This foundation

- First-party **MIT** license at the repository root, with retained donor notices
  and explicit [third-party/service boundaries](THIRD_PARTY_NOTICES.md).
- A real, application-owned SQLite **conversation journal**: scoped queries,
  atomic/idempotent ordered appends, bounded replay and quotas; **31 new tests**.
  Standalone backend library only — not connected to HTTP auth, UI or a live agent.
- Shared **OpenBot OS** source branding while preserving the light layout, protocol
  identifiers, pairing controls and lack of a native authority bridge.
- Opt-in bounded **Windows debug-string capture**, schema 4, with **20 new
  fake-backend tests**. No Windows native verification or registry changes.
- [Pinned upstream features/code/frontend review](docs/openbot-os/UPSTREAM_REVIEW.md),
  [architecture/acceptance targets](docs/openbot-os/ARCHITECTURE.md) and
  [concrete work orders](docs/openbot-os/WORK_ORDERS.md).

CopilotKit's MIT frontend SDK and application-server runtime can connect to
AG-UI agents without Intelligence in the TypeScript OSS mode. Intelligence is
separately licensed. It is not the whole backend engine and self-hosting alone
does not make a service open source. The review records exact source pins and
limits; it does not claim an exhaustive upstream security audit or superiority.

## Existing working scope and hard limits

The earlier local slices remain: human briefs, validated local planning,
draft-only social review, an attributed OpenMuse read-only CSV preview and a
narrow authenticated Studio→HTTPS→kernel→fixed-owned QA→artifact read-back path.
These are **not** general live AI chat, a real virtual PC or social publishing.

No provider, per-bot VM, authenticated IDE, social account or bank is connected.
The old unsigned Windows EXE still has a supplied `0xc000007b` startup failure;
Android is a demo-key local APK; iOS is source only. **Old EXE/APK embed the prior
UI, not this newly branded source.** See
[NATIVE_BUILD_STATUS.md](docs/openbot-os/NATIVE_BUILD_STATUS.md).

**Public release is blocked. Accepted genuine observed pilot days: 0.** Standing
[R01–R13](PUBLIC_RELEASE_ROADMAP.md), independent security/operations/evaluation,
supported native devices/signing/update, the 1–6-month pilot including ≥30
consecutive genuinely observed days and human release approval remain required.
A fully OSS core is the design/release requirement, not a completed audit of all
historic binaries, SDKs or optional third-party services.

## One canonical codebase

`studio/` shared light UI · `control/` native source/labeled old test builds ·
`work/` preserved kernel/configuration/tests/retained donors · `tools/` source and
diagnostic guards · `docs/openbot-os/` current architecture/work orders ·
`evidence/` scoped evidence and source identities.

Base independently reviewed: `9f5600d1fd285e79922fbf69a2abce5243cb9291`. Use
ordinary reviewed Git commits, preserve local work/backups and never replace or
delete the laptop folder to sync. No direct Antigravity message, external agent
team, authenticated Arena push or public release occurred. The private complete
workspace includes recovery dependencies and owner data: **do not publish it all**.

`SOURCE_MANIFEST.json` verifies selected file identity, not signer identity,
license compliance, production safety, permissions or release approval.
