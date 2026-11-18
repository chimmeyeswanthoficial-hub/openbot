# OpenBot: from a governed OS to an AI work-delivery platform

**Decision:** keep the independent company kernel, but make the product about useful work, not operating-system features. Start with **human-led software QA and technical documentation**, then bounded editing of customer-owned video. Use a transparent company identity with a real authorized administrator. Social activity stays **draft-only** for now.

The owner delegated technical choices, not legal ownership, account identity, spending, customer contracts or release authority. This direction does not shrink the long-term vision. It gives us a credible first proof instead of pretending to employ an army of specialists already.

Task date: **2026-11-10**. The runner observes Nov14; both sources remain distinct. This is a development checkpoint, not a public launch, income forecast or account-safety guarantee.

## 1. What changed in the code

Original code in `services/gateway/src/workbench.py`; no new server or provider:

| Implemented offline behavior | Exact limitation |
|---|---|
| Structured opportunity triage: reject, clarify, human-only, not-ready, or review-for-proposal | Operator-attested metadata, not an autonomous job finder or verification of an opening. Every result forbids execution and sending |
| Fixed clarification questions for uncertain AI-use, location, source rights, customer scope and freshness | Questions are prepared locally; nobody is contacted |
| Bounded UTF-8 pytest-style JUnit-subset evidence packet tied to a brief digest, source revision, run reference and required cases | Parses supplied evidence; does not run or authenticate tests. Forged XML can still be forged evidence |
| Actual-case outcome arithmetic, required-case checks, duplicate/ambiguous/contradictory-count refusal and bounded structural parsing | Green tests do not prove adequate coverage or customer acceptance. Packet never authorizes delivery or claims specialist parity |
| Scoped direct-feedback store: pending → exact-digest host-human review → quoted task context; expiry/revocation redact live payloads | Trusted local host API, **not remote authentication or hostile-tenant isolation**. Consent/source receipt names are attestations, not proof we hold legal rights |
| Atomic local feedback state/audit transactions, restart persistence, corruption refusal | Not tamper-proof against the host user; not the independent Sentinel boundary for external effects |

**80 focused tests** cover these paths, including seven observed structural/malformed-capability failures before repair. The first implementation also exposed an SQL value-count defect; it was repaired, not hidden. Current whole-project outcomes are in `audit/verification-current.json`; exact feature/release/preservation evidence is `audit/workforce-review.json`.

There is **no** social crawler, posting/liking/commenting adapter, model training, unattended sales pipeline, arbitrary customer-code runner, customer delivery or new media renderer. This library is not connected to HQ, Worker or a live model. No keys, customer data, primary business jobs, spending or revenue were added.

### Real local QA sample, not a customer job

We actually ran:

```sh
.venv/bin/python -m pytest services/media-api/tests/test_media_boundary.py \
  --junitxml=.cache/workforce/qa-sample.xml
```

Result: **6 passed**. The packet's brief is limited to default-off routes, token requirements and honest split501 refusal. Its required-case mapping includes all six tests; supplied runner exit was0. Source digest binds the media application, runner and boundary test file. The recorded packet has `delivery_authorized=false` and `specialist_parity=not_measured`.

This proves neither that media processing works nor that the existing runner is safe. Source inspection still finds whole-upload buffering, unsafe pipe/lifecycle handling, missing bounded cancellation and no independent media enforcement. Those are useful QA findings, not a finished editing service. Sample/provenance live in the compressed evidence bundle identified by the feature receipt.

## 2. Money-earning services to build toward

These are **candidate services**, not confirmed offers we can already fulfill autonomously. "Plausible specialist standard" means a bounded deliverable could meet an expert-agreed rubric after implementation and independent review; it is not a measured result here.

| Service / deliverable | Priority and honest readiness | What specialist-quality acceptance needs |
|---|---|---|
| QA evidence/reporting: test matrix, reproducible findings, regression packet | **First pilot target.** Local packaging works; actual testing is still human-operated | Reproduce defects; expected/actual results, environment, severity, traces and negative tests; no claim tests prove absence of bugs |
| Technical README, API guides, onboarding and runbooks | **First pilot companion.** Engineer-assisted drafts; no autonomous docs worker | Execute every documented example on a clean supported environment; correct source/version, usable recovery steps, expert review |
| Small software fixes with regression tests | Later, after authenticated isolated execution | Failing-before/passing-after, compatibility, security review, migration/rollback proof; no unreviewed production push |
| Internal workflow/API automation | Later, tightly scoped | Idempotency, permissions, fault/restart tests, stop/cost limits and actual read-back; not permission to automate prohibited platforms |
| Spreadsheet/CSV cleanup and reconciliation | Good bounded future service | Schema, row counts, totals, preserved originals, exception report; no invented missing values or regulated sign-off |
| Permitted-source market/product research | Human-reviewed future service | Dated primary citations, uncertainty, contrary evidence and no fabricated contacts/openings |
| Document extraction and knowledge-base maintenance | Future, with data controls | Accuracy audit against originals, access isolation, provenance, deletion and no cross-client reuse |
| Support ticket triage and draft answers | Future assistant, not uncontrolled sender | Grounded policy answers, escalation, privacy and authorization; sensitive replies require review |
| Owned-footage clipping, resizing, captions and podcast repurposing | **Second pilot target. Not implemented as a safe editing pipeline** | Rights, exact cuts, caption accuracy/sync, audio clarity, framing, codec/length and human playback QC |
| Explainer videos from approved script/owned assets | Later, after renderer/voice integration | Factual script, licensed images/music/voice, intelligibility, branding and output QC; asset generation is not completed video delivery |
| Generative-video ads or B-roll | Later, provider/account/cost gate; **no video generator connected** | Brief adherence, continuity, artifact screening, rights/likeness consent, disclosure and expert creative review |
| Social content research and tailored drafts | Draft assistance first; **no account connected** | Original useful perspective, facts/rights checked, authentic identity, human review and permitted publication method |

Do not sell fake engagement, fake reviews, account farming, impersonation, application spam, pirated media or unqualified medical/legal/tax/financial judgments. A job asking for a licensed professional, a person's lived experience or location-specific hardware is not an AI-deliverable contract.

### Can it match a human specialist?

**Not demonstrated.** Narrow QA/documentation/data jobs have more objective acceptance checks than high-end storytelling, brand strategy or complex software architecture. The latter depend heavily on taste, domain expertise and accountability. Neither a model brand nor 80 software tests establishes human parity.

Before advertising specialist quality: define the exact service and failure costs; freeze the rubric and baseline; commission independent qualified reviewers; run a blinded held-out comparison on representative authorized briefs; record major errors, accuracy, usefulness, rework, time and total cost. An initial30-task evaluation is a proposed pilot size, **not statistical proof**. Set sample size/non-inferiority criteria with the evaluator before making a comparative claim. Critical safety/rights failures block promotion regardless of average score. Pay human reviewers for legitimate evaluation, never for positive public reviews.

## 3. Find real work without inventing customers

Use an honest funnel:

1. **Discover:** customer-submitted briefs, referrals, permitted feeds/APIs and human-reviewed public opportunities. Terms and permission must be checked for each source. No general social/job scraping entitlement is established.
2. **Qualify:** live URL/date, client legitimacy, location, permitted AI/agency participation, data/testing rights, budget, deadline and measurable acceptance. No advance-payment scams, fake credentials or taking money-moving tests on live accounts.
3. **Clarify:** ask only missing material questions; draft them first. Don't message strangers without specific authorized outbound handling.
4. **Propose:** bounded scope, exclusions, acceptance, rights, revision policy, delivery date and owner-approved price/terms. Disclose AI use as required; do not claim experience we lack.
5. **Produce:** only inside the enforced approved environment; do not run arbitrary customer repositories on this trusted host. AG1/AG2 remain prerequisites.
6. **Verify and review:** compare to the brief, independent QA, owner/customer sign-off; send through an approved, audited destination-bound action.
7. **Reconcile:** accepted delivery, fees/refunds/provider costs, independent settlement and margin. A posted budget or draft invoice is not income.

### Public opportunity check in this session

| Source | What was actually observed | Decision |
|---|---|---|
| Upwork: **Test New AI Workspace Cohesive.ai**, posted Oct15,2026 | Detail page retrieved; advertises $60 for about60–90minutes and honest product testing/feedback, with account creation and application questions. This is a listing's claim, not our quote or earnings. [2](https://www.upwork.com/freelance-jobs/apply/Test-New-Workspace-Cohesive_~022110789496027684905/) | **Human-led participation only**, not a bot impersonating a professional tester. Reconfirm opening, eligibility and AI/agency terms before any application; none sent |
| Upwork: **QA Engineer for Agentic AI Platform** | Search showed a September29 listing/$100, but following its URL returned the generic jobs directory instead of confirming the opening. [1](https://www.upwork.com/freelance-jobs/apply/Engineer-for-Agentic-Platform_~022104987268253122621/) | **Unverified/stale candidate; do not apply or count as available work** |

No machine-eligible contract is confirmed, no account/profile was created, and no proposal/customer commitment was made. Search snippets, large category counts and advertised rates are not guaranteed accessible jobs or evidence of demand for *our* product. Prefer proving the service on owned material before seeking paid customer access.

## 4. Social interaction: reduce risk, never promise no bans

No apps are connected. Connector lookups for LinkedIn and YouTube returned unsupported **in this conversation**; this is not a claim that no integration could ever be built.

| Intent | Chosen path | Not allowed / not enabled |
|---|---|---|
| Company presence and useful posts | Real administrator and truthful company identity; draft locally; later approved official API only for approved use/scopes/roles | Fake personal AI employee profiles, shared cookies/passwords, session bots or disguising automation |
| Questions, comments and replies | Useful contextual human-reviewed drafts; human native action initially | Unattended comment bots, mass outreach, flooding or pretending approval overrides platform restrictions |
| Likes/subscriptions/engagement | Authentic human choice, not an agent KPI | Fake views/likes, pods, reciprocation schemes, paid manipulation or synthetic "interest" |
| Learn what people need | Invite voluntary feedback through an approved channel; separate consented direct feedback from social API data | Scraping posts/comments into a permanent training corpus; assuming public visibility equals reuse rights |

LinkedIn's agreement prohibits unauthorized automated access/actions and scraping; its documented post API has scope/role/access restrictions. API endpoints do not authorize every use case. We retrieved official API documentation, but full agreement/API-terms fetches failed (500), and the news authenticity page refused access (403). Search excerpts are **not a complete legal review**. Keep writes disabled until the exact program/terms/use are approved. [1](https://www.linkedin.com/legal/user-agreement) [1](https://www.linkedin.com/legal/l/api-terms-of-use)

YouTube requires prior **specific and express consent** for automated actions, truthful identity, user control, minimal scopes and data deletion/refresh controls; OAuth alone is not blanket action consent. Its fake-engagement policy bars artificial metric inflation. [1](https://developers.google.com/youtube/terms/developer-policies) [1](https://support.google.com/youtube/answer/3399767?hl=en)

YouTube developer policies were read in full. Data types have distinct retention/revocation/deletion rules, including7/30-day provisions; do not replace them with a universal cache TTL. The new workbench's30-day **direct-feedback** limit is not an implementation of those platform rules. Realistically altered/synthetic media may require disclosure; that does not guarantee monetization or waive other rules. [1](https://developers.google.com/youtube/terms/developer-policies) [1](https://support.google.com/youtube/answer/14328491?hl=en&co=GENIE.Platform%3DDesktop)

No numerical activity limit, random delay, "human-like" behavior, approval checkbox or API token guarantees against restriction. Do not bypass CAPTCHA, account blocks, revoked access, rate limits or eligibility. Stop on authorization/policy uncertainty; reconcile ambiguous writes before retrying. Other social sites need their own review, not blanket permission inherited from this table.

## 5. Learning and self-building: four different things

1. **Task feedback memory — implemented narrowly.** Separately consented direct feedback only; opaque source/rights receipts, scoped service, maximum30-day live retention, pending by default. Trusted host human review binds exact content/provenance/expiry. Retrieval returns explicitly untrusted quoted task context, never authority. It is not automatically passed to any model.
2. **API retrieval/cache — not implemented here.** Separate platform-purpose, provenance, authorization, display, refresh and deletion requirements. User consent does not override platform terms.
3. **Prompt/skill/code improvement — reviewed engineering.** Turn a validated failure into a candidate diff and reproducer; license/security review, deny-network disposable tests, protected held-out evaluation, rollback/canary and required human promotion. The agent cannot edit its evaluator, permissions, budget or deployment authority. Current new code does not perform this promotion loop.
4. **Model training/fine-tuning — not implemented.** Needs explicit applicable data rights, platform permission where relevant, contracts, privacy/security, deletion/unlearning policy, cost and evaluation. YouTube's third-party-training setting is opt-in and off by default; it is not permission to scrape/download everything. LinkedIn Research Program terms explicitly prohibit training on Research Data; that program is not a general-purpose learning loophole. [1](https://support.google.com/youtube/answer/15509945?hl=en) [1](https://www.linkedin.com/legal/l/research-api-terms)

Live-row redaction is **not deletion of backups, exports, filesystem snapshots or downstream model context**. No background expiry service is running; expiry executes on supported API use or explicit sweep. A real feedback feature still needs authenticated consent/revocation intake, backup retention/deletion, data-subject handling and independently protected storage before customer/private data. A malicious instruction remains untrusted even after someone approves its inclusion as feedback. This slice deliberately has no executor, sender or model consumer.

## 6. Video: editing first, generation second

Do not enable the defective experimental Media API to satisfy the ambition on paper.

**Editing milestone:** licensed/pinned FFmpeg/ffprobe build → authorized uploaded originals, not YouTube ripping → probe and bounded job plan → trim/concat/crop/scale/captions/audio through an allowlisted renderer → process/egress/filesystem isolation and enforced input/output/disk/memory/time/cancellation → ffprobe/output/hash/playback QC → reviewed delivery. FFmpeg licensing depends on build configuration/optional components; free source is not blanket codec, patent, asset or redistribution clearance. [1](https://www.ffmpeg.org/legal.html)

**Generation milestone:** approved storyboard/owned references and likeness/voice permissions → provider adapter with independent cost reservation and request receipts → asynchronous completion/cancel/uncertain-state reconciliation → download only authorized output → artifact/continuity/safety/disclosure review → editing and delivery. Official paid video APIs are a feasible future resource (for example Google's Veo API), not a free local capability or an account we have configured. Check current availability/price/region/terms before choosing or paying. [1](https://developers.googleblog.com/introducing-veo-3-1-and-new-creative-capabilities-in-the-gemini-api/)

No ffmpeg/ffprobe/container isolation was available on the initial reset host; no new video provider/GPU/runtime was installed, no media bill incurred, and no generated/edited video is claimed by this checkpoint. Start with deterministic edits of owned footage, not specialist creative-parity promises.

## 7. Next engineering order and reproduction

**AG1 authenticated mandatory execution/isolation → AG2 real agent/provider/cost/stop → one QA/documentation pilot → bounded media → separate approved social integration → protected improvement/operations/pilot evidence.** The existing private1–6-month pilot/human release decision remains. No background business work continues just because this chat ends.

```sh
bash scripts/bot-hq.sh install
export PATH="$PWD/.venv/bin:$PWD/.cache/openbot-toolchains/node-v24.22.3-linux-x64/bin:$PATH"
make workforce-demo  # synthetic XML/consent/reviewer clearly labelled; disposable local DB
python -m pytest services/gateway/tests/test_workbench.py
make lint
make release-check
```

For real supplied QA evidence, `python scripts/workforce-demo.py --help` lists the explicit brief/source/run/exit/required-case arguments. Those remain host attestations, not authenticated test provenance. Keep customer code and data off this host until the isolation/data gates are met.

`OUR_PROJECT.md` remains the overall owner guide. `audit/workforce-evidence-consolidation.json` maps17 historical metadata/memory files into a verified lossless archive; recover any original with `tar -xJOf archive/historical-metadata-before-workforce.tar.xz ORIGINAL_PATH`. This includes older HQ/history/execution receipts referenced at their original paths above. Donor trees, business state, licences and the prior delivery receipt were preserved. The adjacent continuation-bundle receipt identifies the actual new downloadable freeze; old receipts are historical, not proof of these new features.

Space-preserving upload recovery: the original architecture PDF is retained byte-exact as
`uploads/Untitled document (14).pdf.xz` (857,243→602,340B), verified in
`audit/workforce-evidence-consolidation.json`. View a restored copy via
`xz -dc "uploads/Untitled document (14).pdf.xz" > .cache/restored-architecture.pdf`;
original-name references/source pins identify the recovered PDF, not discarded content.
