# Social integrations: official APIs, deliberate authorization

Policy review date: **10 November 2026**, the task's local date. Runtime timestamps
are observations, not a different authority for interpreting “today”. Requirements
can change; this file is not legal advice, compliance certification or ban immunity.
No account was connected and no platform request, upload or post was made.

## X

Official automation rules require opt-in and opt-out handling for automated replies
and DMs; following or OAuth alone does not establish the required action consent.
AI reply bots need **prior written and explicit approval from X**, in addition to
other rules. Automated likes are prohibited. [1](https://help.x.com/en/rules-and-policies/x-automation)

X's Developer Policy prohibits spam/manipulation and identical or substantially
similar posts across multiple accounts; bot/operator identification and explicit
consent remain review items. [1](https://docs.x.com/developer-terms/policy)

Implementation: own-post draft review only. No mentions/replies/DM/like automation,
account blasting, website scripting, cookie import, rate-limit evasion or automatic
follow/unfollow is implemented. Text containing a mention receives another review
requirement. Local duplicate warnings do not inspect actual platform history and
are not an evasion rewriter. No universal “safe posts per day” is claimed. API access,
commercial tier, scope availability and account-specific limits need current review.

## Instagram

The [official publishing documentation](https://developers.facebook.com/documentation/instagram-platform/content-publishing)
distinguishes login flows, professional-account eligibility, app access/review,
media containers, processing and publish stages. This prototype references only
the **Instagram Login** path: `graph.instagram.com`,
`instagram_business_basic`, `instagram_business_content_publish`. These are scope
references, **not granted permissions**. Facebook Login and Unified Login must not
be mixed into that path without a separate design/version review.

A chosen account, current version, token lifecycle, eligibility, permissions, media
route, asset hosting where required, container readiness and actual publishing-limit
usage must all be verified. Sections of the retrieved documentation gave conflicting
fixed daily numbers (50 vs 100); no fixed quota or “ban-safe” threshold is encoded.
Query actual account/API limits and apply conservative owner-authorized bounds.

The current documentation describes `is_ai_generated` on applicable containers;
its use still requires human content classification and a verified API version.
Unknown disclosure is represented as unknown, not silently false. No media URL is
accepted or fetched by the planner: there is no SSRF/download/hosting side channel.

## YouTube: do not repeat the obsolete private-only claim

The official revision history dated **2 November 2026** reverses the 2020
unverified-project private-only upload restriction. Omitting `status.privacyStatus`
can default an upload to **public**, with account-setting exceptions.
[1](https://developers.google.com/youtube/data/revision_history)
The [current videos.insert reference](https://developers.google.com/youtube/data/reference/rest/v3/videos/insert)
confirms this, defines scopes and metadata, and describes subscriber notifications.
This does not remove other OAuth, verification, quota, audit or policy obligations
that may apply to a particular app or account.

Implementation: the **non-executable metadata preview** always includes
`status.privacyStatus = "private"` and `notifySubscribers = false`. The latter is
previewed alongside metadata, not misrepresented as a field inside the video
resource. There is no transport request or uploader. `containsSyntheticMedia` and
`selfDeclaredMadeForKids` remain null when classification needs human review. An
asset digest and evidence reference do not prove ownership or inspect the video.
The upload scope is a least-purpose reference, not an OAuth connection.

## Common effect-boundary requirements

- Official OAuth, explicit chosen accounts, least scopes and revocation.
- Exact content/media/audience/visibility review and independent authorization.
- Current rules, rights/consent, AI disclosure and actual quota/rate-limit checks.
- Durable stop; respect `Retry-After` and provider errors; never rotate accounts,
  identities or proxies to bypass enforcement.
- Idempotency/reconciliation before retrying any ambiguous external write.
- Keep credentials in an appropriate server-side vault, not browser drafts or bot PCs.

The planner's requirement list is intentionally always nonempty while adapters and
accounts are absent. A local human checkbox never makes it publishable.
