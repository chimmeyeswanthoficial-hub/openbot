# Light companion interface — shared implementation, not a screenshot claim

The user's supplied light desktop/mobile reference supersedes the earlier dark /
Grok-inspired direction. The delivered UI uses the reference's visual structure:

- White desktop workspace, soft-neutral companion sidebar, compact thread header,
  black human brief bubbles, light-gray intake/example bubbles and a bottom composer.
- Three desktop columns: companions, conversation, companion computer/routine panel.
  Details can close/reopen; at medium widths they become an overlay.
- Mobile pinned companions plus a list; selecting one opens a conversation with Back.
  Search includes pinned profiles. Computer/routine details occupy a mobile overlay.
- Named role profiles, a restrained accent palette, rounded controls, original inline
  SVG-letter avatars, keyboard focus, dialog labels, reduced-motion and safe-area CSS.

## One UI source of truth

```sh
python3 studio/scripts/build-web.py
```

The build embeds, in order, `finance-preview.js`, `finance-workspace.js`,
`gateway-session.js`, `app.js` and local CSS into one CSP-hashed HTML file. It writes
byte-identical payloads to:

1. `studio/web/index.html` — local browser/planning interface;
2. `control/web/index.html` — exact gateway client and Windows/Android build input;
3. `control/native/ios/OpenBotControl/index.html` — iOS embedded source payload.

The Windows RCDATA and APK `assets/index.html` are checked against these actual bytes.
This prevents separate dark/native forks or an old browser screenshot being used as
proof of a new package. Native package version 0.3.0-local is separate from the
existing authenticated API v1 / wire client 0.2.0 contract.

## Deliberate differences and honest boundaries

- Original OpenBot wordmark/letter avatars are used, not the reference's branded
  characters, closed artwork, copied account identity or fictional live app screens.
- No macOS traffic lights, iPhone hardware frame, Dynamic Island or fake OS status bar
  is drawn inside Windows or Android. OS chrome, font rendering and trusted-server
  selectors remain platform-specific. **Exact cross-OS pixel parity is not claimed.**
- No invented teammate replies, connected computer, account messages or completed
  actions appear by default. The optional conversation is explicitly fictional.
  Local intake checklists are deterministic, not model output.
- Microphone, requested routines, PC and IDE controls explain missing implementation
  or export a request. They do not record audio, create a schedule, allocate a VM,
  install software or authenticate a tool.
- Shared native shells stay exact-origin, TLS-validating and bridge-free. File picker
  and download restrictions are not relaxed for aesthetics; use the browser for files.
  A user-agent capability hint only changes affordances, NEVER server authority.
- Native UI embedding/compilation and Chromium/Linux WebKit checks do not establish
  Windows launch, Android/iPhone behavior, OS trust, full WCAG or release acceptance.

## Behavior/data changes

New optional storage key: `openbot.workspace.local-drafts.v2`, schema 2. Only
non-secret briefs, custom requests and routine requests are saved, off by default.
Legacy `openbot.studio.local-drafts.v1` is detected but never silently imported or
deleted. Financial imports, keys, pairing/review codes and authoritative task receipts
are excluded. Restored custom requests lose any previously verified plan authority.

Bounds, text escaping, invalid/delayed file reads, edited/late social checks, offline,
background/resume, exact approval and uncertain mutation read-back are regression
cases. Stronger contrast and larger mobile header targets were added. Qualified
screen-reader/font-scale/device accessibility and actual useful-output acceptance
remain R07/R08 gates, not passed by these scripted checks.

Historical recorded QA/media demo receipts remain evidence; they are not preloaded
as current server work or a real PC screen. The old recorded-data injection tool now
fails explicitly rather than overwriting the shared bundle. Kernel media processing
source/tests remain preserved; no media, social or real-PC requirement was removed
from the requested product vision.
