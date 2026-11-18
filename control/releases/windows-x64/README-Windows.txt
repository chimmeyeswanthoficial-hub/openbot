OpenBot Control 0.3.0-local | UNSIGNED local test portable build

1. Extract the complete Windows bundle. Keep WebView2Loader.dll beside the EXE.
2. A current Microsoft Evergreen WebView2 x64 Runtime is required. No runtime is downloaded by this app.
3. Without server-origin.txt, the app shows an offline light companion workspace with no network authority.
4. To test an owner-approved server, create server-origin.txt beside the EXE containing only its HTTPS origin (no slash/path/credentials), for example https://YOUR-APPROVED-HOST. Do not put passwords, API keys or pairing codes in this file. Hostname/IPv4 and an optional numeric port are supported; IPv6 literals are not yet supported.
5. Confirm the displayed origin in the native Windows dialog. Platform TLS validation is mandatory; self-signed certificates without managed trust will fail. There is no bypass or HTTP fallback.
6. Pair using a short-lived one-use host-console code. Every API request proves the ephemeral P-256 device key. A separate exact-review host-console code is required for approval. No provider keys go to this client.
7. Closing/reloading loses the memory-only key; pair again. Device expiry/revocation remains server-authoritative.

This is not an installer, an agent host, an Authenticode-signed release, or a Windows-launch-tested build. Signed JSON manifests are integrity tooling, NOT OS code signing. Update by verifying a newly approved portable bundle and extracting into a new directory. Native auto-update, enterprise installer selection and OS matrix acceptance remain pending.

Uninstall: first revoke this device on the server, close all app windows, then remove the extracted folder. Optional user profile data is under %LOCALAPPDATA%\OpenBotControlLocal. See scripts/uninstall-local-preview.ps1 for a guarded owner-run cleanup helper. Do not remove server databases or the protected Linux runtime. No Windows registry autorun/service/startup task is created.

This light companion UI is shared byte-for-byte with Studio and native Android/iOS payloads. Layout follows the supplied reference with original OpenBot SVG-letter avatars. File pickers/downloads are intentionally disabled in this native test shell; paste allowed local text or use the browser workspace for imports/exports. This restriction is not missing-file success. No live model, real PC/IDE, social or bank connection is created.
