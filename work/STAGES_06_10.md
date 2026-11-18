# S06–S10 — local engineering continuation, not whole-stage acceptance

This source continues frozen S02–S05. Windows/Android/iOS are **control clients**; protected Linux runs the work. This is an isolated local checkpoint, not a deployment, customer service or public release. No production database, paid account, provider key, customer code, Git push/merge or external delivery was authorized or used.

The accompanying packet retains actual run logs/JUnit, package hashes, observed screenshots, source/reverse patch, reproduction and rollback. Historical S02–S05 evidence remains historical. Read `audit/verification-current.json` for the latest **completed** source-test outcome; do not add passes from overlapping runs. The sandbox runner's recorded timestamps are observations of that runner clock, not an independent wall-clock attestation.

| Stage | Local engineering supplied | Acceptance still missing |
|---|---|---|
| S06 | Reviewed/pinned FFmpeg profile, fixed media operations, bounded private spooling and concurrent drains, time/resource limits, real output/segment decode read-back, large-input benchmark and real HTTP lifecycle/cleanup tests | Independent complete linked-license/security review, hostile/customer-upload resource isolation, owner target-host performance and qualified human quality/usefulness acceptance |
| S07 | First-party source/license/version/capability catalog, signed scoped re-resolution/revocation, explicit consented untrusted quotes, deletion replay/backup retention, session-derived feedback adapter, fail-closed signed candidate review/canary/rollback contracts | Production retention/security/role operations, real independent evaluation/reviewer/canary evidence; no learning/training or improvement claim |
| S08 | Versioned HTTPS/device-key API, scoped expiring/revocable sessions, read-only status/tasks/audit/canonical exact book, server proposals, separate exact re-authentication/review and actual owned QA artifact read-back | Owner-selected real server/access and managed TLS identity, real native OS trust/device/accessibility tests; ephemeral renderer keys are not hardware identities |
| S09 | Live host inspection, required external security controls and signed current host/policy/witness/owner admission contracts; defaults remain closed | Actual delegated per-job cgroup/quota/deny-network staging and independent witnessed hostile tests, then one eligible tiny-budget real provider streaming/tool/stop/usage proof |
| S10 | Genuine unsigned Windows x64 executable and demo-key-signed Android APK; updated iOS source/Xcode target; local signed-manifest integrity/anti-rollback/recovery tooling and OS/privacy drafts | Windows launch/DPI/install/update/uninstall, Android devices/lifecycle/accessibility/release key/AAB if selected, Mac/Xcode/simulator+iPhone/provisioning/signed export, native updater and release signing |

## S06: fixed owned-media engine

`services/media-api/src/{media_app,owned_media,ffmpeg_runner,media_worker}.py` implements cut, concat, scale, literal caption overlay, audio and independently verified segment ZIP output. It accepts no arbitrary shell, arbitrary FFmpeg filter/argument, URL fetch or generative-media job. The service is **default-off**: `MEDIA_API_ENABLE_EXPERIMENTAL=1`, a trusted server token, an explicit reviewed tool receipt and a private spool root are required. It is a local synthetic/owned-media test service, not a mounted authenticated-control-client upload product. Browser control routes cap their JSON bodies separately at 16 KiB.

Input is at most 260 MiB; any individual output is at most 300 MiB; the input/output/private-directory accounting ceiling is 562 MiB. The upload/job boundary is 90 seconds and response lifetime 20 seconds. Each tool has a wall deadline, capped stderr and output; selectors drain stdout/stderr while feeding bounded input. A watcher does not rely on a consumer resuming a generator. Fixed child processes get CPU/address-space/file/open-file/process/core rlimits and parent-death signalling. Receipt sampling records actual `/proc/<pid>/limits`, RSS/threads and reaping. NPROC is UID-wide; address-space is not cgroup RSS; process sampling is not full process-tree accounting. Filesystem accounting is not a hard per-job quota. **None of these replace S09.**

Successful responses are sent only after actual probe + complete decode read-back. Split output remains inaccessible on invalid/missing segments; every delivered segment has its own digest/probe/decode manifest. ZIP packing is incremental and checks disk accounting. Unhandled errors/cancellation signal the fixed worker, terminate/wait/reap, and close only the lease-owned spool. Startup recovers abandoned private job directories under a cross-process lock without removing unrelated owner files. Parent SIGKILL cleanup was observed with a deliberately installed **test subreaper**; this is not a production init/process-tree guarantee.

Observed measurements are in `s06-final-benchmark.json`: one 250,000,044-byte synthetic WAV and five 100 MB samples. The input is silence; timings are this sandbox's observations, not a 20-second promise or a statistically qualified p95 SLO. `scripts/prove-media-lifecycle.py` exercises real HTTP oversized/malformed/missing-tool/upload-disconnect/FFmpeg-disconnect/slow-consumer/parent-death/restart/success/split cases. `scripts/export-owned-media.py` exports real synthetic cut/concat/scale/captions/audio/segments; the decoded caption frame is visible in the preview. No human visual/audio quality acceptance is invented.

`bootstrap-owned-media.py` pins Debian package versions/digests and captures executable hashes, 211 resolved libraries and FFmpeg license/build output. Selected FFmpeg is GPL-enabled Debian 7.1.5; this is **not an LGPL-only binary**. The packet does not redistribute FFmpeg or its linked libraries. A host-specific linkage receipt is not a complete independent license, security or portability review. Rebootstrap and review the receipt on another host; never silently substitute an unreviewed system FFmpeg.

## S07: catalog, consent and controlled candidates

- `ToolCatalog` resolves only `owned.qa` 1.0.0 with locked first-party source/LICENSE digests and fixed capabilities. Current host-configured catalog authority is signed, scoped to a venture and expiring/revocable; resolution is repeated at proposal/review/execution. Work approval bindings include these governance/control/crypto sources and locks so an implementation change invalidates old approval.
- `ConsentedMemory` requires explicit protected-host consent: client/subject/scope/purpose, owned provenance, consent reference, expiry and an artifact digest. Quotes are returned as `untrusted_quote`, `authority=false`, `training_use=false`. Obvious poison/secret patterns are rejected, but pattern matching is **not a complete prompt-injection defense**. The safety boundary is that quotes cannot grant tools, approvals, budgets or policy authority.
- `MemoryFeedbackService` derives the identity from the authenticated WorkService session, never user JSON, and requires an actual verified scoped outbox artifact before accepting referenced feedback. This is a trusted Python adapter with tests, **not an enabled customer feedback/training endpoint**.
- Delete/revoke commits an independent deletion journal first, removes active quote content and replays tombstones before restored content can be read. Managed snapshots are integrity-checked, have at most seven-day retention, refuse expired restore and can be swept. Production scheduling, encryption, least-privilege separation and offsite deletion are still S11 work; secure physical erasure is not certified.
- `CandidateGate` records reproducer/isolated-test/protected-evaluation/qualified-review/canary/eligible/rollback stages with pinned source/policy/evaluation and signed roles. The evaluated agent cannot sign itself into eligibility, change thresholds or deploy. This module **never edits source, trains or installs** a candidate. Unit signing roles are synthetic fixtures, not real independent humans or observed canaries.

No scraping, fake engagement, social-account automation, automatic training corpus or better-performance claim was introduced.

## S08: actual client integration, explicit local identity

`control_api.py` wraps the existing fixed-owned WorkService, not a generic command/agent host. Trusted host-console setup issues a one-use short-lived pairing grant; the client generates a non-exportable P-256 key. Every subsequent read/mutation uses a single-use, device/method/path/body-bound challenge proof and rechecks server-side session expiry/revocation/scope. Rate/body/deadline/origin/path bounds and no-store/CSP headers are enforced. Device stores must already exist at runtime; no implicit production schema setup occurs.

Read snapshots expose the source of status/tasks/audit and **economic_v1 integer minor-unit postings**, with freshness. The synthetic exact-book example is captured 25,000, refunded 5,000, net captured 20,000 minor units; not profit, revenue, bank balance or settlement. Legacy float P&L is never relabeled exact.

A new task is a server-side proposal only. Approval needs a separate short-lived trusted-console code bound to the exact device/task/plan digest and current bindings; execution is another explicit request. Work remains fixed owned QA in deny-network namespaces. The real browser proof drives three sample workflows, verifies artifacts by read-back, keeps an additional task pending review, and exercises stale/offline/reconnect/lifecycle events/mobile/escaping/forgery/revocation negatives.

The disposable test runs real HTTPS sockets: explicitly trusted fixture CA succeeds; default trust and wrong hostname fail; cleartext does not serve the API; the server/listener stops. Chromium uses a single exact fixture SPKI launch pin with `ignoreHTTPSErrors=false`. **This does not establish native OS CA acceptance or production server identity.** Test private CA/device/session/signing profiles are not distributed. The standalone preview embeds only recorded synthetic snapshots, labels them offline/no authority, performs no fetch and cannot approve/spend/execute. A live unpaired page starts empty, never mislabeled with recorded tasks.

Keys are renderer-memory-only; there is no TPM/Keystore/Secure Enclave binding. Reload/close loses them and requires new pairing. Scope/tokens stay on the server; provider secrets are never accepted by the client. Native origins are selected explicitly by the owner and shell certificate errors are not bypassed. Actual platform behavior still needs device testing.

## S09: external gate stays closed

Run `PYTHONPATH=services/gateway/src python -m staging_readiness --receipt NEW.json`. A refusal exit is intentional when delegation/current external witness/owner evidence is absent. The actual host's cgroup2 mount is present but not delegated/writable; no independently witnessed disk/network/secrets/socket/authority/process-tree tests exist here. `audit/staging-required-controls.json` describes the required controls, not an installed sandbox. No JSON, API key, namespace demo, rlimit, synthetic signer or readiness result alone clears that gate.

Only after that external gate can the owner separately admit one eligible provider/account with a tiny current budget. The admission module still does not enable an adapter. Actual streaming/tool reservations/stop and independent final usage receipts remain unrun. No provider was started and no spending was authorized.

## S10: packages versus release

The sibling client source contains the actual builds and current OS/privacy/status drafts. Windows is a portable unsigned PE plus pinned loader, not an installer or Windows-launch-tested artifact. Android is an actual APK signed with a clearly labeled **local demo** certificate; its private key stays in cache. It is not release-key-signed, device-tested or an AAB/store submission. iOS compilation on Linux exits 2; updated Swift/Xcode/plist source is not an `.app` or `.ipa`.

`verified_updates.py` is Linux-host integrity tooling: out-of-band SHA-pinned trusted public keys, size/path/hash checks, platform/package/device/version/expiry binding, atomic stage/pointer updates, monotonic version high-water, separately signed rollback decisions, recovery and adversarial tests. It never downloads/launches/installs or acts as a native updater. Example usage:

```sh
PYTHONPATH=services/gateway/src python -m verified_updates verify-stage \
  --root /NEW/PRIVATE/UPDATE-ROOT --trust /OWNER/REVIEWED/TRUST.json \
  --trust-sha256 THE_OUT_OF_BAND_REVIEWED_DIGEST --platform windows-x64 \
  --device-ref LOCAL_REVIEWED_DEVICE_REFERENCE --manifest REVIEWED_SIGNED_MANIFEST.json \
  --source /ALREADY/DOWNLOADED/REVIEWED/PACKAGE
```

The placeholders above are documentation only, never submitted tool values. Local test signatures are not Authenticode, Android release/Play identity, Apple provisioning, safe native update/uninstall proof or an owner release decision. The guarded optional Windows cleanup helper is supplied but unexecuted on Windows.

## Reproduction, preservation and rollback

Follow the delivery reproduction guide for hash-verified incremental reconstruction from frozen S05 into a **NEW** directory. Install hash-locked handoff/PG/control wheels in a NEW Python environment. Invoke `python -m pytest` / `python -m ruff`, not copied console-script shebangs. Explicit disposable PG DSN + write opt-in + namespace opt-in and matching `OPENBOT_PG_TEST_BIN` are required for all backend/restore cases. Never fall back to `DATABASE_URL` or `SENTINEL_DB`. Keep each evidence destination new; restore tests intentionally refuse overwriting an older receipt.

Use cache-only SDKs/tools; no FFmpeg binary, private disposable profile, demo/release signing key, source-control credential, real database or provider key enters the packet. The original source, older deliveries/private state and preview listener are preserved by per-file hash/size/mode comparison. Roll back by selecting the frozen predecessor in a NEW review directory, revoke fixture devices and stop this checkpoint's disposable services. Do not overlay an old source snapshot/database onto a live service. Reverse patch is for hash-verified throwaway review source only.

S11 operations, S12 protected evaluation and the private 1–6-month pilot (including at least 30 consecutive observed days), and S13 human release decision still follow. These local tests/builds neither start the pilot nor authorize public use.
