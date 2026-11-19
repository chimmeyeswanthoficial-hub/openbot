# OpenBot OS Authenticated Studio History — Verification Evidence

Parent commit: `236d05e55d2fe7b210c85937523363bbcc9fc21b` on branch `repair/restore-manifest-files`.
Work slice: Authenticated Studio History on the signed HTTPS gateway (client adapter, WebCrypto unit tests, dedicated UI, single-file HTML compilation, Windows verification suite).

This is Antigravity's Windows development and verification evidence packet.
**Accepted real observed pilot days: 0. Not a public release or independent product security certification.**

---

## 1. Summary of Execution Results

| Check / Test Suite | Scope & Tool | Result | Durable Record |
|---|---|---|---|
| **Bounded HTTP Repetition** | `python -m unittest discover -s studio/tests -p "test_studio_http.py" -v` | **10 / 10 runs passed** (exit 0, 13 tests each, 0 socket resets observed) | `repetition-studio-http-10x.log`, `REPETITION_STUDIO_HTTP.json` |
| **Node Unit Suite** | `node --test studio/tests/*.test.cjs work/packages/bot-hq-queue/... work/tools/findrepo/...` | **79 passed / 0 failures** (9 new WebCrypto gateway history tests) | `node-tests.log` |
| **Studio Python Suite** | `python -m unittest discover -s studio/tests -p "test*.py" -v` | **48 passed / 4 skipped** of 52 (Windows POSIX permission skips expected) | `studio-tests.log` |
| **Tools Python Suite** | `python -m unittest discover -s tools/tests -p "test*.py" -v` | **77 passed / 0 failures** | `tools-tests.log` |
| **Sentinel Journal Suite** | `python -m unittest discover -s services/sentinel/tests -p "test_conversation_journal.py" -v` | **31 passed / 0 failures** | `journal-tests.log` |
| **Gateway History Suite** | `pytest services/gateway/tests/test_conversation_api.py -v` | **58 passed / 0 failures** (includes bounded synthetic-CA TLS test) | `gateway-history-tests.log` |
| **Web Build Check** | `python studio/scripts/build-web.py` | **150,155 bytes**, SHA-256 CSP hash verified, byte-identical outputs across web and native shells | `studio/web/index.html`, `control/web/index.html`, `control/native/ios/OpenBotControl/index.html` |

---

## 2. 10-Run Bounded Windows HTTP Repetition

To evaluate the unread-body socket reset hypothesis under Windows 11 (`Windows-11-10.0.26300-SP0`, Python 3.13.0 AMD64), `studio/tests/test_studio_http.py` was executed 10 consecutive times in bounded isolation:

- **Run 1**: exit=0, duration=1.712s, 13 tests passed, socket reset observed: False
- **Run 2**: exit=0, duration=1.655s, 13 tests passed, socket reset observed: False
- **Run 3**: exit=0, duration=1.607s, 13 tests passed, socket reset observed: False
- **Run 4**: exit=0, duration=1.607s, 13 tests passed, socket reset observed: False
- **Run 5**: exit=0, duration=1.647s, 13 tests passed, socket reset observed: False
- **Run 6**: exit=0, duration=1.575s, 13 tests passed, socket reset observed: False
- **Run 7**: exit=0, duration=1.619s, 13 tests passed, socket reset observed: False
- **Run 8**: exit=0, duration=1.801s, 13 tests passed, socket reset observed: False
- **Run 9**: exit=0, duration=1.589s, 13 tests passed, socket reset observed: False
- **Run 10**: exit=0, duration=1.563s, 13 tests passed, socket reset observed: False

**Conclusion**: All 10 runs passed cleanly with exit code 0. Zero `ConnectionResetError` or `WSAECONNRESET` occurrences were observed.

---

## 3. Implementation Details

### A. Client Session Adapter (`studio/web/gateway-session.js`)
- **Scopes**: Added frozen `historyScopes` (`history-read`, `history-write`, `history-delete`).
- **Route Allowlist**: Updated `allowed()` to permit signed POST routes matching `/api/v1/conversations/(create|list|c[a-f0-9]{32}/(read|messages|delete))`.
- **Viewer Role Boundary**: In `pair()`, viewer role is explicitly restricted to `['read', 'revoke-self', 'history-read']`. Pairing fails closed if viewer requests `history-write` or `history-delete`.
- **History Methods**:
  - `historyList(after, limit)`: Requires fresh `history-read`. Validates parameters. Returns `threads` array.
  - `historyCreate(title, threadId)`: Requires owner role + `history-write`. Generates client thread ID (`c` + 16 random hex bytes) if not provided. Validates 200-char non-control title.
  - `historyRead(threadId, after, limit)`: Requires fresh `history-read`. Validates thread ID and bounds. Returns `events` array.
  - `historyMessage(threadId, text, expectedSequence, messageId)`: Requires owner role + `history-write`. Validates 8192-byte UTF-8 bound and control characters. Uses compare-and-swap `expectedSequence`. Returns `sequence`.
  - `historyDelete(threadId)`: Requires owner role + `history-delete`. Validates thread ID. Asserts logical deletion contract (`deleted: true`, `secure_erasure: false`).
- **Session Freshness Lifecycle**: Preserves session freshness on successful history operations (`this.#seen = this.#now()`), but immediately invalidates freshness on error (`this.#seen = null`) to force explicit read-back and prevent uncoordinated writes.

### B. WebCrypto Node Unit Tests (`studio/tests/gateway-history.test.cjs`)
Added 9 comprehensive test cases:
1. `history scopes and regex patterns are exported correctly`
2. `allowed routes permit all valid history POST endpoints and reject invalid methods or paths`
3. `viewer role can pair with history-read but not history-write or history-delete`
4. `historyList requires fresh history-read scope and valid bounds`
5. `historyCreate requires owner history-write and enforces title boundaries`
6. `historyRead requires history-read and validates bounds`
7. `historyMessage requires owner history-write and enforces 8 KiB bound and control-char checks`
8. `historyDelete requires owner history-delete and validates thread ID`
9. `uncertain failure retains operation and prevents silent retry`

### C. Dedicated Authenticated History UI (`studio/web/app.js` & `studio/web/styles.css`)
- **View Integration**: Added `history: 'Authenticated history'` to `views` dictionary and navigation.
- **Two-Column Responsive Layout**: Thread management panel on left, message stream and human composer on right.
- **Plain-Text Escaping**: All thread titles, message text, author identities, and sequence numbers strictly escaped with `esc()`. No markdown parser or raw HTML injection.
- **Strict Separation**: Local companion drafts remain completely separate from server history.
- **Zero LocalStorage Persistence**: Server history state is in-memory only and never written to `localStorage`.
- **Session Invalidation Handling**: Stale in-memory history is cleared when session is revoked or forgotten.
- **Uncertain Operation Reconciliation**: 503/uncertain write outcomes display a prominent warning banner with "Refresh & reconcile" and "Dismiss" buttons, preventing blind retries.
- **Single-File Deterministic Compilation**: `build-web.py` bundles all assets into `studio/web/index.html` (150,155 bytes), with byte-identical copies in `control/web/index.html` and `control/native/ios/OpenBotControl/index.html`.

---

## 4. Honest Boundaries
- **No autonomous execution**: History messages represent inert `CUSTOM` events (`openbot.user_message.v1`), not autonomous assistant turns or model prompts.
- **No live model/teammates**: No LLM, provider API, or external network services are connected to this screen.
- **No hardware keystore**: Private keys are non-exportable but stored in renderer memory only.
- **Pilot status**: Accepted real observed pilot days: **0**.
