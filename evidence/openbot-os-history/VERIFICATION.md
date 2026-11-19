# OpenBot OS authenticated-history increment — actual evidence

Parent `cf2acb10530ab3c33c567bb9831c5d6dbe515349`; this is Arena's own development
and testing, **not independent acceptance or a real pilot**. The final commit SHA,
manifest/source/export and commit-transport guards are external in the current
handoff receipt to avoid self-reference.

## Results actually executed

| Check | Actual result | Durable record |
|---|---|---|
| Selected gateway suites + journal | **473 passed / 87 PostgreSQL skips** of 560 collected | `gateway-tests.log`, raw `gateway-tests.xml` |
| New authenticated-history module | **58 passed**, included above | `history-tests.log` |
| Prior real SQLite journal methods | **31 passed**, included above | Gateway log and original journal tests |
| Tools standard-library suite | **77 passed** | `tools-tests.log` |
| Studio Python | **51 passed / 1 Windows-only skipped** of 52 | `studio-tests.log` |
| Node | **70 passed / 0 failures** | `node-tests.log` |
| Public planner Chromium smoke | **21 grouped checks passed**, Chromium 141.0.7390.37 | `BROWSER_SMOKE.json`, desktop/mobile PNGs |
| Scoped Ruff | 5 changed Python files lint/format passed | `ruff-tests.log` |

Do not add overlapping counts: the 58 HTTP cases and 31 journal methods are part
of the 473 passing selected gateway/journal cases. All 87 selected-suite skips
explicitly require a new disposable PostgreSQL DSN/write opt-in; none are passes.
`JUNIT_COUNT_NOTE.json` distinguishes the raw JUnit suite-header subtest accounting
from its 560 actual testcase nodes and the console count; raw XML is not rewritten.

The selected suite includes existing signed control API, work service, crash/
recovery, policy/catalog/executor, actual opted-in fixed namespace, evaluation,
external-gate and operational controls. Complete source layout was copied to a
**new excluded disposable test workspace**, retaining `control/` beside `work/`;
only new explicitly synthetic state was prepared there. Tested runtime/code/client
hashes are recorded in the final receipt. No owner's operating state was changed.

## What the new 58 cases actually establish

Real file-backed SQLite + actual ECDSA P-256 proofs through the real gateway code;
explicit capabilities, role/actor/venture/gateway scope denial; same-actor second
device; strict JSON and credential-pattern/UTF-8/byte bounds; no client-selected
assistant/system/tool/approval payload; ordered retry/conflict/pagination; concurrent
signed devices; genuine injected DB rollback and pre-access audit failure; history
commit followed by completion-audit failure and stable-ID reconciliation; device/
session revocation racing an admitted history write; logical delete preserving
other actors and immutable audit; all server-side stores reopened with no DDL.

One bounded **real TLS-socket test** creates only a synthetic short-lived test CA,
uses normal certificate verification and proves an untrusted CA fails. The other
HTTP cases use ASGI TestClient, not an actual TLS socket. None is owner hardware,
public-host deployment, browser WebCrypto acceptance, independent security review
or genuine user observation. Production profile and privacy/ACL/backup boundaries
remain operator/reviewer work; see `AUTHENTICATED_HISTORY.md`.

## Honest red → green and tool limits

`history-first-attempt.log` preserves **56 passing / 2 failing** first-pass tests.
The failures were in the test harness: a restarted no-DDL runtime tried to create
a trusted setup authority; the TLS write fixture omitted an explicit owner role
and correctly got the default viewer refusal. The harness now keeps the runtime
unprivileged and explicitly provisions an owner only in trusted new test setup.
No permission check, production assertion or TLS verification was disabled.
An initial lint command used the wrong cwd; formatting/paths were corrected.

Existing lock files were used with **require-hashes / binary-only** installation
into excluded cache, not global/system/Windows packages. New optional JSON-schema
validation tools have a separate exact wheel/hash test lock; no runtime SDK was
installed. `TOOLING.json` records tool scope and new test-dependency license metadata.

The existing locked **non-setuid Bubblewrap** executable was downloaded/verified
and extracted only into that disposable test copy. Selected real namespace cases
ran with explicit opt-in; cgroups are **not delegated**, and this does not establish
a general sandbox, VM or hostile-host acceptance. `ISOLATION_TEST_TOOL.json`.

A separate broader-media setup attempt downloaded/verified the original five exact
FFmpeg packages but could not resolve `libavfilter.so.10` and other required host
libraries. `full-kernel-media-setup-failed.log` is retained. **No host/PATH fallback,
pin weakening or manufactured full-kernel pass.** The full kernel/media/PostgreSQL
suites were not rerun or relabeled as fresh. The selected gateway/journal run does
not need those media tools and genuinely passed under its declared profile.

## Actual source/contract adoption versus planned features

- Exact upstream MIT **AG-UI spec/1.0/schema.json** + license/provenance is retained
  in `work/third_party/ag-ui-contract/`; SHA-256 and pinned API Git-blob IDs match.
  CUSTOM-envelope tests resolve the local schema only. That is actual contract
  reuse, **not a full SDK/runtime/AG-UI lifecycle/provider integration**.
- Current reviewed Nightly source remains PolyForm Noncommercial and no code/artwork
  was imported. Historical v0.1.11 annotated tag → `e9cae2ac…` resolves to a verified
  Apache-2.0 LICENSE, pinned in `NIGHTLY_LEGACY_LICENSE.json`. Only the license was
  verified; no historical module/NOTICE/dependency clearance or code reuse claimed.
- All four requested source families and forty capability states are covered by
  `docs/openbot-os/FEATURE_REUSE_LEDGER.json` / `FEATURE_REUSE.md`. This is selected
  bounded review, not every file/function executed or already integrated.
- No CopilotKit Intelligence account/activation, enterprise service, unknown backend
  image, current Nightly code, upstream website art/branding or full-access agent
  default was imported/enabled. No license purchase or bypass occurred.

## UI/native boundary

The light layout is unchanged. Settings truthfully state the optional authenticated
history API exists but is **not connected to this chat**. Public-planner browser
checks confirm source-response hash equality, desktop/mobile navigation/local brief,
CSV currency gating, stale-package/unwired-chat labels, no JavaScript page errors,
no external application requests and no privileged writes in that smoke.

Current generated HTML: **127,590 bytes**, byte-identical across Studio/gateway/iOS
source assets (`NATIVE_IDENTITIES.json`). Historical EXE/APK/DLL and all original
Windows traces remain unchanged from the parent; native packages still embed the
older 127,185-byte UI. No current package rebuild/launch/OS trust/device/signing/
update acceptance. The exact-payload package verifier was not weakened.
Public planner is not the authenticated gateway and contains no private history.

## Real-world trial — unstarted, no simulated credit

The owner's requirement is now an actual first month including ≥30 consecutive
observed real days, independent review/owner approval, then **six additional
calendar months**. `REAL_WORLD_ROLLOUT.md` and `REAL_WORLD_PILOT_STATUS.json` record
that sequence, upgrade/stop/evidence rules and **0 genuine accepted days** in both
phases. No pilot ledger was activated and no new daily observations were generated.

Existing Assessment v1 is limited to one frozen candidate/policy and 180 days.
It was not quietly weakened or misrepresented as this two-phase calendar process;
a reviewed versioned extension remains required. Real people, independently protected
held-out tasks, host/account/cost/consent/native/on-call approvals and actual months
cannot be substituted by this test run.

Antigravity connector lookup returned **unsupported**. Work orders and one-file
handoff are prepared; no direct message, active team, authenticated remote push,
PR merge or asynchronous engineering is claimed. Full R01–R13 remain in force.
**Overall project unfinished; public release false; accepted genuine pilot days 0.**
