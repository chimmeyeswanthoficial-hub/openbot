# disadvantages.md

**What OpenBot OS cannot do, where it will fail, and which companies it should not be sold to.**

Read this before you sell anything. Every item is either a hard limit (`[never]`), a legal line
(`[human]`), or a gap with a date (`[M1–M3]`). A capability that is not in `aboutme.md` is not a
capability; if it is here, it is a limit you must design around, price around, or refuse.

---

## 1. Hard limits — `[never]`

| # | Limit | Consequence | Design answer |
|---|---|---|---|
| 1 | **No legal personhood.** Cannot sign, be liable, hold a licence, or be sued. | Contracts, terms of service, NDAs, DPAs are all human artefacts. | Owner signs. Agents draft. Never auto-accept a vendor's T&C. |
| 2 | **No body.** Cannot ship, install, inspect, repair, meet, or handle cash. | Physical businesses are out of scope as a *primary* operation. | Sell software/services to physical businesses; do not try to be one. |
| 3 | **No accountability with consequences.** Cannot be fired, fined, or trusted with a secret it must keep from itself. | Anything where the downside is liability (safety, medical, legal, financial advice) is human-owned. | The human is the professional of record; agents do the work behind them. |
| 4 | **No genuine relationship.** Can write well; cannot *care*, cannot be trusted, cannot negotiate with a counterparty who needs a person across the table. | Enterprise deals, partnerships, hiring, and fundraising stay human. | Agent does the prep, the follow-up and the CRM; the human does the room. |
| 5 | **No true judgement under ambiguity.** It optimises against what you wrote. When the right answer is "this deal is wrong", it needs your criteria, not its instinct. | Novel situations default to the letter of the spec — sometimes confidently wrong. | Kill criteria, human review of anything irreversible, and a bias to ask. |
| 6 | **No reliable self-improvement without you.** It can learn a tool and file a rule; it cannot decide it should become a different company. | Strategy is human. Execution is agent. | Weekly one-decision review with a human signature. |

---

## 2. Legal and regulatory walls — `[human]`

These are not "risky". In most jurisdictions they are **prohibited** to automate away from a licensed
person. Selling into them as an unattended product is a legal exposure, not a productivity win.

| Domain | Why the line exists | What OpenBot OS may do | What it must never do |
|---|---|---|---|
| **Medical / clinical** | Diagnosis and treatment are licensed acts; patient data is special-category | Scheduling, billing, records hygiene, patient comms *drafts*, research summaries for a clinician | Triage a patient, recommend treatment, interpret a scan, answer "is this serious?" |
| **Legal services** | Practising law requires admission; advice creates liability | Document assembly from a lawyer's template, discovery organisation, deadline tracking, drafting | Give legal advice, decide a filing, interpret a contract as "safe", represent anyone |
| **Tax & accounting (attest)** | Filing and audit opinions require a licensed professional | Bookkeeping, reconciliation, VAT/GST data prep, chasing missing receipts | Sign a return, issue an audit opinion, decide a tax position |
| **Financial advice / trading** | Licensed; market conduct rules; client-money rules | Research, drafting, reporting, reconciliation, ops | Advise a client, execute a trade, manage client money, promise a return |
| **Insurance** | Underwriting and claims are regulated | Data prep, document collection, churn analysis | Underwrite, deny a claim, bind cover |
| **Real estate** | Brokerage is licensed; fair-housing rules | Listing drafts, CRM, market data | Represent a buyer/seller, negotiate an offer, discriminate on any protected attribute |
| **Immigration** | Representing a visa applicant is regulated in many countries | Form filling from a human's answers, checklist tracking | Advise on eligibility, submit a filing as the applicant's representative |
| **Employment decisions** | Hiring/firing is high-risk AI under the EU AI Act and similar | Draft job specs, schedule, summarise applications *for a human*, log decisions | Reject a candidate autonomously, decide a promotion or a termination |
| **Credit / lending** | Credit decisions are regulated and require explainability | Document collection, affordability data prep | Decide a loan, set an interest rate |
| **Education / grading** | Assessment and child-facing services are high-risk | Content drafting, admin, scheduling | Grade a student, decide an admission, teach children unsupervised |
| **Anything involving minors, weapons, gambling, adult content, or crypto custody** | Regulated, reputational, or outright unlawful in places | Nothing unattended | Everything |

**The rule in one line:** if the output needs a licence, an opinion, or a sign-off from a professional,
a professional signs it and OpenBot OS does the work *behind* them.

---

## 3. Where it will genuinely underperform a human — with numbers

| Work | Why the agent is worse | Realistic agent performance | Where the human must stay |
|---|---|---|---|
| Cold outbound sales | Reply rates depend on social proof and a real person; volume gets you blocked | 1–3% reply on cold email, worse than a good rep, and domains get burned | Offer, pricing, first 20 conversations |
| Enterprise / B2B deals >$10k | Procurement, trust, security review, negotiation | Can assemble the pack; cannot close | All of it |
| Hiring | Judgement + legal risk | Can screen for keywords and draft | Final call always |
| Negotiating a price with a supplier | Iterative pressure and relationship | Can gather alternatives | The call |
| Novel debugging of an unfamiliar system | Confident wrong turns; needs taste | Good with a precise order + trace, poor when exploring blind | First 2 hours of a novel outage |
| Design taste | Pixel-level judgement of a brand | Competent with a spec, mediocre without | Direction, once per project |
| Customer escalation / churn save | The customer wants to be heard | Can draft; cannot de-escalate | The call |
| Anything with a deadline that cannot slip (legal filing, payroll run) | A single wrong assumption is irreversible | Risky even gated | Human check on every run |
| Deep research | Synthesises well; misses the one source that matters | Good coverage, thin judgement | The conclusion |

---

## 4. Failure modes you should expect (from this system specifically)

| Failure | How it shows up | Frequency | Mitigation already in the design |
|---|---|---|---|
| **Gate starvation** | Work silently stops because nobody cleared approvals | very likely in week 2 | daily digest, `#ops-alerts` nag, "blocked" count in the weekly review |
| **Routine rot** | A routine keeps firing and producing nothing anyone reads | likely | output destinations checked; archived channel → warning |
| **Prompt drift** | A model upgrade quietly changes tone or decisions | likely | eval suite + canary (M3); until then, pin the model tier |
| **Ledger fiction** | Someone "reports" revenue that is not settled | moderate | revenue only from webhook rows; trials tracked separately; reconciliation must be $0 |
| **Silent death** | The box dies, everything looks fine from outside | moderate | dead-man's switch on two independent signals (B10) |
| **Scope sprawl** | Three ventures in discovery, none paying | very likely | one venture until first payment (D7), enforced by review |
| **Secret sprawl** | A key ends up in a routine body or a trace | moderate | scrub + escalate, protected paths, redacted traces only |
| **Upstream rot** | OpenBot moves; our patches pile up | certain over 12 months | marker convention + monthly single-upstream bump |
| **Cost creep** | Agent spend grows faster than revenue | likely after month 3 | role ceilings + daily/monthly caps + cost as % of revenue metric |

---

## 5. Per-industry verdicts (can this company be run by OpenBot OS?)

Legend: **Yes** = primary operations can be agent-run with human sign-off · **Partly** = agents do the
work, a professional signs · **No** = unautomatable core (physical, licensed, or trust-based).

| Industry | Verdict | What agents do | What stays human |
|---|---|---|---|
| SaaS / API products | **Yes** | build, deploy, support drafts, billing rows, docs, status | price, terms, first customers |
| Content & publishing | **Yes** | research, draft, SEO, scheduling, analytics | editorial voice, legal review, final publish |
| Digital agency / productized service | **Yes** | delivery work, QA, reporting, client drafts | the client relationship, scope changes |
| E-commerce (dropship/digital goods) | **Yes** | listings, pricing tests, support drafts, ads analysis | supplier contracts, ad spend above budget |
| Dev tools / open source with paid support | **Yes** | triage, docs, releases, community drafts | maintainer authority, roadmap |
| Marketplaces / two-sided platforms | **Partly** | onboarding checks, support, fraud signals, ops | trust & safety decisions, disputes |
| Education / courses | **Partly** | content, grading *drafts*, comms | assessment sign-off, safeguarding |
| Recruiting agency | **Partly** | sourcing, scheduling, summarising | candidate decisions, client contracts |
| Accounting / bookkeeping firm | **Partly** | data entry, reconciliation, chasing documents | sign-off, tax positions |
| Law firm support (not practice) | **Partly** | document automation, discovery, docketing | advice, filings, representation |
| Healthcare admin (not care) | **Partly** | scheduling, billing, records hygiene | any clinical decision |
| Financial services ops (not advice) | **Partly** | reconciliation, reporting, KYC document collection | regulated decisions, client money |
| Real estate brokerage | **Partly** | listings, CRM, market data | representation, negotiation |
| Restaurants / retail / logistics | **No** (as primary) | marketing, support, inventory paperwork | the physical operation |
| Manufacturing / hardware | **No** (as primary) | design files, docs, procurement paperwork | everything physical |
| Construction / trades | **No** | quotes, scheduling, back office | the work |
| Personal services (salon, clinic, gym) | **Partly** | booking, marketing, reminders | the service itself |
| Non-profit / fundraising | **Partly** | grants drafts, donor comms drafts, reporting | asks, governance |
| Crypto / trading / custody | **No** | research only | everything else |
| Defence, weapons, gambling, adult, minors | **No** | nothing | everything |

---

## 6. The $100k question, answered against us

You asked for $100k+ revenue as fast as possible while leaving for a year. Honest arithmetic:

- A **validated** micro-SaaS at $19–79/mo reaches $100k ARR only with ~100–400 paying customers and a
  working acquisition channel. Agents can build and support that; they **cannot** create demand from
  nothing. Demand is the bottleneck, and it is human (or budget) work.
- The faster path is **productized service**: agents do the delivery, you sell the first ten
  engagements, price at $1–5k, and use the cash to fund the SaaS. This is why `plan.md` §7.3
  recommends path B to fund path A.
- What will actually kill the plan is not capability. It is **(a) gate starvation** (you stop
  approving), **(b) no channel** (nobody finds it), and **(c) scope sprawl** (five half-ventures).
  All three are human-behaviour failures, and all three are visible in the weekly review.

---

## 7. When NOT to use OpenBot OS

- When the work is a single, high-stakes decision (a merger, a lawsuit, a diagnosis) — use a
  professional and let the agents prepare the file.
- When the customer *requires* a named human (regulated engagements, government contracts, many
  enterprise security reviews).
- When you cannot give it 3 human hours a week. Without approvals being cleared, this system is an
  expensive way to do nothing.
- When the business depends on a relationship you have not built yet. Sell first, automate second.
- When you cannot afford the downside of one bad autonomous action (early-stage cash, regulated data,
  a brand with no reputation buffer). Then run it with every gate on and a human shadowing for a month.
