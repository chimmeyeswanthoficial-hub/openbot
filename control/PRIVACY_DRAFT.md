# Privacy and retention — local engineering draft

**Not finalized privacy terms, legal advice, store declarations or production acceptance.** Only synthetic owned fixtures were exercised.

## Data flows

The connected client sends a device public key, device label, one-time pairing/review grants, request signatures and the task brief/rights/acceptance text to the **owner-selected HTTPS server**. It reads that server's scoped task/audit/exact-book/artifact records. No provider credential belongs in the client. There is no automatic provider work, analytics SDK, advertising/tracking SDK, social scraping or training upload in this application code.

Device private keys are non-exportable WebCrypto keys in renderer memory, not hardware-keystore credentials. Closing/reloading loses them. Sensitive codes are cleared after submission and on pause where wired. No durable client task DB, credential file or automatic background agent is implemented. The Windows WebView profile can retain browser/system cache metadata; the embedded engine/OS can have diagnostic/update traffic outside our page code. This app is not a system-wide firewall or certified secure-erasure tool.

## Local briefs, financial files and optional browser storage

The shared light UI defaults to tab memory. Optional v2 browser draft saving stores
only non-secret human briefs, custom companion requests and routine requests in
unencrypted local storage. Those records are editable, not authenticated approvals.
Legacy v1 data is detected and left untouched; clearing v2 does not silently erase
v1. Financial CSV data, device keys, pairing/review codes and authoritative task
receipts are not persisted there. Financial reports/brief exports may contain
sensitive data if the user explicitly downloads them in browser mode.

Native test shells block file pickers/downloads and may block or discard browser
storage. Paste permitted text or use the browser for file operations. The page's
native user-agent hint affects affordances only, never authentication/authority.
Local clear, tab close or unlink is not certified memory/disk erasure. Full real-
provider/server retention, privacy, export and scoped deletion remain release work.

## Server retention and consent

Work/audit evidence is retained on the server. The S07 consented-memory module separately requires explicit purpose/client/subject/scope/provenance and expiry. It returns untrusted quotes, not instructions, permissions or a training corpus. Consent deletion/revocation immediately removes active quote content; an independent deletion journal is replayed before restored content may be read. Managed content snapshots have a maximum seven-day retention, with expiry/refusal/sweeping tooling. Physical disk/SSD erasure and offsite backup deletion are **not certified**. Production encryption, access-role separation, retention scheduling, export/deletion support and notices still require S11 owner/security/legal work.

The S07 candidate queue records review-only proposals, not automatic training or self-deployment. Synthetic signing-role unit fixtures do not count as actual independent evaluation, qualified human review, observed canary or improved performance.

## Platform declarations

- Android declares INTERNET only, disables cleartext and app backup, denies WebView permission/file chooser/download requests and blocks non-selected origins in this host. No camera/microphone/location/storage permissions are requested.
- iOS has no ATS cleartext exception. A local-network usage description explains explicit self-hosted access; no discovery/scanning/Bonjour service is configured. The privacy manifest and export-encryption fields are source templates requiring owner review against the final app/server/SDK behavior before signing or submitting. Empty template collection arrays are **not a completed App Store privacy disclosure**.
- Windows is a portable unsigned test build. No registry autorun, system service or scheduled startup job is installed by this source. Owner-controlled release signing and installer/uninstaller choices remain pending.

Before real users: choose the server and data roles, finalize privacy/terms/retention, secure and recover release identities, validate actual native device behavior, and obtain the required human release decision. Never paste real credentials into chat.
