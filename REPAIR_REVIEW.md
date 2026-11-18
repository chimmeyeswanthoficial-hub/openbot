# Verified repair successor — light-repair-verified-1

The ZIP upload restriction did not block recovery. No laptop ZIP was uploaded or
received. Arena reconstructed the reported successor from pinned public Git source
at `f40421329adc87e49698a752103a78d8d3aea507`, independently reproducing its exact
reported SHA-256 `1c704f194ea06a139e72e4922c42be5056338d42be38ff4f5bb9e9ceaeb9b1cf`.
All 4418 parent manifest-listed files were present and verified. No more deletion,
forced update, external upload service, or disguised ZIP upload was needed.

## Corrections now included

- Correct aggregate file-metadata digest, with a regression that rejects a stale
  supplied digest. Legacy small manifests may omit this optional field; this full
  manifest includes and validates it.
- Canonical ZIP manifest mode 0644 regardless of Windows/POSIX observed manifest
  mode; approved source-file modes are preserved. A second regression covers this.
- Antigravity's UTF-8 / canonical-LF build fix and CRLF-input regression retained.
  Actual shared HTML stays byte-identical: 127185 bytes, SHA-256
  `bb99d979376841815bc5dcfe7c942bed28b36f2b87a0b3b80d8d366e5b8b3c67`.
- Root `.gitattributes` controls text LF and binary assets. `.gitignore` and imported
  `result.md` are explicitly included in the new source manifest, not extra hidden
  exclusions. Kernel, full 3475-file upstream source, native binaries and notices
  remain intact. No private build/signing/cache/runtime data was added.
- Current receipt index: `evidence/repair-review/INDEX.md`. Original evidence remains
  historical and is not relabeled as freshly rerun or independent acceptance.

## Current verification

Linux: Studio Python **49 passed / 1 Windows-only skip (50 collected)**; handoff
Python **10 passed**; Studio Node **45 passed**; retained Node **25 passed**; native
binary/assets/tool/static facts **27 passed**. No failures/errors in those profiles.
Selected Ruff check/14-file formatting is clean. Original hardlink tests use real
links on Linux; a separate forced-PermissionError run checks the Windows-style mock
fallback and is labeled simulation, not Windows filesystem evidence.

The unchanged shared payload and unchanged kernel retain their earlier scoped
browser/kernel receipts: UI35 and finance21 per engine, HTTPS application44/engine,
offline78; configured kernel1251 pass/173 PostgreSQL skips. These were **not** rerun
as new native-device acceptance in this metadata-only finalization. The WebKit local
HTTPS application fixture's test-only certificate exception is not native TLS proof.

## Windows and other external claims

`result.md` is the raw **Antigravity report**, not an Arena-certified acceptance
record. It reports Windows tests and a process start/respond/stop. No raw native UI
screenshots/runtime logs or interactive/DPI/accessibility/offline/resume acceptance
were supplied. Process responsiveness alone cannot prove WebView2 rendered the
intended UI. Its attribution of the earlier extraction failure to Windows Explorer
is reported, not independently established. Dates in that report are preserved
observations, not elapsed pilot time. Owner signing/distribution remain open.

Android is still a demo-signed unaccepted test APK; iOS is source only, no IPA.
Real providers, VMs/IDEs/social accounts, independent review, witnessed operations,
protected evaluation, the real pilot and human release remain open. Public release
false; accepted genuinely observed pilot days **0**. No remote Git writes occurred.

## Next practical action

Read `ANTIGRAVITY_NEXT.md`: preserve current work and backups, apply reviewed changes
on the existing repair branch with an ordinary commit/PR (never force), then collect
real Windows UI evidence. Do not repeat the resolved 258-file restoration. For the
complete archive use a new extraction folder and verify all files; if an extractor
reports errors, stop rather than treating omissions as intentional. Git does not
retain restrictive 0600 source modes: use a mode-preserving ZIP extraction on POSIX
or explicitly restore reviewed manifest modes in a clean copy before strict checks.
