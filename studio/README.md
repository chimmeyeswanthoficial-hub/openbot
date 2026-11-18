# OpenBot companion workspace · light reference interface

Original light three-column desktop and companion-list → chat mobile UI, shared
with the Windows/Android build input and iOS source. **Not live AI chat or a public
release.** Avatars are original SVG lettering, not the reference's closed artwork.
Read top-level `START_HERE.md`, `DESIGN_REFERENCE.md` and `PUBLIC_RELEASE_ROADMAP.md`.

## Local planning start (Python 3.11+, standard library)

```sh
python3 src/studio.py serve --bind 127.0.0.1 --port 4183
```

Open `http://127.0.0.1:4183` on that computer. Arena preview hosts need `--bind 0.0.0.0`;
relative browser URLs are used. This is public stateless development planning, **not**
a production perimeter, private-data vault or gateway proxy. Private CLI stores are
never read by the HTTP handler. No account/key/install/VM is activated by startup.

`web/index.html` also works offline for local briefs/navigation/CSV, with embedded
styles, scripts and SVGs and no CDN/fonts. Missing companion/social validation is
shown as unavailable. An opaque `allow-scripts` file-viewer iframe needs no forms,
storage, network or same-origin sandbox grant for local drafting/calculation.

## Actual implemented workflows

- Ten display-role blueprints plus explicit custom companion/model/tool requests.
  None is a connected account, server actor, real PC or installed IDE.
- Human briefs, deterministic local intake, safe bounded UTF-8 text reads, Markdown
  library exports, search and responsive list/chat/back/details interaction.
- Local routine requests with IANA time zone validation and non-authorizing JSON;
  no scheduler, mailbox or background job starts.
- X/Instagram/YouTube own-draft checklists with exact draft hash/invalidation,
  duplicate warnings and explicit private YouTube metadata. No OAuth/publish/DM/like/
  auto-reply endpoint, platform permission or ban-immunity promise.
- Attributed OpenMuse CSV spending preview with exact integer minor units, explicit
  source currency/sign confirmation, duplicate disclosure, caps, safe rendering and
  race-safe file reads. No model/upload/bank/ledger/spend authority. Imports stay in
  tab memory, including when optional draft saving is on. See `docs/FINANCE_PREVIEW.md`.
- Authenticated fixed-owned QA through `web/gateway-session.js` **only** at the exact
  owner-approved HTTPS gateway `/control/` page: device proofs, separate proposal,
  owner exact review, execution, cancellation, artifact hash and audit/exact-book read-back.
  The public planner cannot execute or proxy this. See `docs/INTEGRATION_CONTRACT.md`.
- Opt-in unencrypted non-secret browser drafts, v2 schema; financial imports, device
  keys, pairing/review codes and authoritative receipts excluded. Legacy v1 storage
  is neither silently migrated nor deleted; restored requests are unvalidated.

Native hosts intentionally block file pickers/downloads and may block storage. Paste
permitted local text or use the browser for imports/exports. A native user-agent hint
changes affordances only; it never grants API authority. Device keys are renderer-
memory-only non-exportable keys, not Secure Enclave/Keystore/TPM identities.

## Explicit CLI planning (no runtime start)

Use a NEW owner-controlled path; never overlay private runtime state:

```sh
python3 src/studio.py inspect-host
python3 src/studio.py init-store --root ../my-private-blueprints
python3 src/studio.py create-companion --root ../my-private-blueprints --request docs/companion-request.example.json
python3 src/studio.py list-companions --root ../my-private-blueprints
python3 src/studio.py review-social --request docs/social-request.example.json
python3 src/studio.py export-source --output ../OpenBot-Studio-source.zip
```

The module export is **not the complete workspace**. The top-level manifest/exporter
is used for the one full handoff. POSIX permissions/secret-pattern heuristics are
not protection against a malicious same-user process or full-history secret clearance.

## Build/test from the complete root

```sh
python3 studio/scripts/build-web.py
python3 -m unittest discover -s studio/tests -p 'test*.py' -v
node --test studio/tests/*.test.cjs
```

The build writes exact same HTML to `studio/web/`, `control/web/` and iOS source.
Rebuild Windows/Android packages after changing it; verify actual embedded bytes.
No SDK or package install occurs in the web build or Python tests.

With separately installed reviewed Playwright 1.56.1/browsers, start the local
preview, select NEW evidence directories and run `scripts/test-ui.cjs` and
`scripts/test-finance-ui.cjs` with `TEST_ENGINE=chromium` / `webkit`.
`PREVIEW_URL` defaults to runner localhost port 4184; set it explicitly to your
preview port. `ANTIGRAVITY_NEXT.md` has full commands, prerequisites and expected
counts. `scripts/test-gateway.cjs` needs the separately orchestrated synthetic HTTPS
kernel fixture; it is not a browser test against the public planner.

48 Studio Python tests, 19 finance + 26 gateway Node tests, 35 UI + 21 finance cases
per browser are local evidence, not native device or independent acceptance.

Real providers, PCs/IDEs, official social, production identity/operations, native
Mac/devices/signing, independent reviews/evaluation, the actual 1–6-month pilot
including ≥30 consecutive observed days and explicit human release remain open.
Accepted genuine observed pilot days: **0**. No background collaboration is claimed.
