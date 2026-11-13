# PROJECT_BRAIN.md — how I thought about this, and what I expect you to produce

**Audience:** the next engineer/AI taking this project over. Not a status report — `PROJECT_STATE.md`
is that, and `PROJECT_REMAINING.md` is the queue. This file is the *reasoning layer*: the heuristics,
the reflexes, the taste, the specific places I expected the work to break, and the outcomes I expect
to see when it is done well. Read this **before** you touch code; read it again after your first task.

**One standing instruction:** I am no longer part of this project. Do not wait for me, do not write
"as the previous agent suggested", and do not treat any sentence here as a requirement you cannot
question. Take the *method*, not the *conclusions*. Where you disagree, prove it with a test and a
dated entry in `STACK_DECISIONS.md` — that file was built for exactly this.

---

## 1. What this project actually is

Not an agent framework, not a chatbot, not a "company simulator". It is **a boundary around
autonomous action, with a company attached to it.**

The product thesis, in one sentence: *a person should be able to leave a machine running for a month,
and when they come back, every dollar it made and every action it took should be explainable from
rows it wrote before it acted.*

Everything else — routines, agents, consoles, P&L — is there to make that sentence usable and
sellable. If a change you make would weaken the sentence, it is the wrong change, no matter how much
demo value it adds. If a change strengthens it and nobody notices, it is probably still the right
change.

The mechanism is three invariants, and they are not negotiable:

1. **No audit row, no action.** The decision is persisted *before* the outward call. That is why
   `_must_persist()` turns a storage failure into a refusal (`503`) instead of a 500 after the fact.
2. **Money is derived, never stored.** `pnl.compute(rows)` recomputes everything from ledger rows;
   the ledger is idempotency-keyed and a replay is *ignored*, not merged. There is no total anywhere
   that an agent can edit.
3. **The boundary is deny-by-default about act/not-act, and narrow-by-design about *what* it can
   deny.** It judges actions, not intentions, and it cannot think — see §10 for where this actually
   fails.

## 2. How I think — the loops I ran

You can copy these. They are the method that produced this repository, and they are the method I'd
expect you to continue with.

**Loop A — measure before you claim.** Before writing anything into a document, run the command that
would falsify it. I described `packages/venture-sdk` as built; it was an **empty directory**. The fix
was not the code, it was the habit: `ls`, `wc -l`, `pytest --collect-only`, then write the number.
Every number in `PROJECT_STATE.md` came from a command, not from memory.

**Loop B — let the document fail the build.** A claim that only a human audits rots. So: claims in
`aboutme.md` carry evidence tags, `test_contract.py` fails when a tag has no test, `verify.sh` fails
when `docs/` drifts, and the test-count guard now shells out to the collector instead of trusting
arithmetic I wrote by hand. When you add a claim, add the check that can break it. **A document that
cannot fail is fiction.**

**Loop C — break it on purpose.** I deleted the SQLite file under a running server; that is how the
`500`-after-decision leak was found, not by reading the code. Adversarial probes found the credential
regexes missing plurals and a harmless invoice read being gated. Once per task, ask: *what is the
shabbiest input a stranger will send?* Send it.

**Loop D — one pass is not a pass.** After the system worked, I did three more passes: hardening, then
honesty (docs vs reality), then strangers (a fresh clone, no `.env`, no Docker). Every pass found
something real. Assume your first green run is the *start* of the work.

**Loop E — separate "works" from "is honest".** These fail independently. A system can work and lie
about it (`aboutme.md` claiming a capability no test covers), or be honest and broken (docs describing
a correct design the code doesn't implement). Check them in different passes with different tools.

## 3. The nine reflexes I used constantly

| Situation | Reflex |
|---|---|
| A new outward action appears | Where is its audit row? What happens if the write fails? |
| A number appears in prose | Which command produced it, when, and is it still true? |
| A test fails after a plausible change | Read **the tests diff** first. Weakening a test is the default failure mode. |
| Something "obviously" safe | Name the worst input a stranger sends. If you can't, you haven't looked. |
| A rule can be written in prose or code | Code + a failing test. Prose is decoration. |
| A feature would make a nicer demo | Does it move a milestone? If not, it is scope sprawl; `D7` says so. |
| A dependency or substrate change | What breaks if upstream moves? Is the seam ours or theirs? |
| An agent reports success | Which rows prove it? Cost, decision, and outcome must be in the store. |
| A blocker outside the code (keys, entity, box) | Say it once, loudly, in `BLOCKERS.md`, then build what doesn't need it. |

## 4. What I optimised for, and what I deliberately sacrificed

**Optimised:** trustworthiness; a stranger's ability to run and audit it; the cost of being wrong
(human gates on money/legal/sends); the ability to *say no* with a reason (refusals are first-class
objects with codes, not exceptions).

**Sacrificed, on purpose:**

- **Speed of the demo.** No chat wow-factor hook yet. The console reads from rows and looks plain.
- **Breadth.** One venture, one endpoint, one product surface. `D7` in `plan.md`: a second venture
  before the first one pays is the most expensive mistake available.
- **Autonomy theatre.** I refused to ship "agent buys the domain" style features. They are the most
  impressive and the most dangerous thing you can demo.
- **Polish.** The console is deliberately one file with inline styles — because it is served by the
  API itself and must survive a sandboxed iframe and a strict CSP.
- **The substrate's richness.** OpenBot has dozens of agent runtimes and a computer-control layer.
  We use it as a host and judge its actions; we did not re-implement or fork it.

If you find yourself optimising the sacrificed column without being asked, stop. Those were trades,
not oversights.

## 5. My taste, stated plainly, so you can predict my review

**I would reject these in review:**

- An `except: pass`, a bare `except Exception` that swallows, or a fallback `return True` on a check.
- A policy rule that lives only in a markdown document.
- Caching an "allow" decision, or widening a rule to make a test pass.
- A new endpoint without a test for its refusal path.
- A migration that is not reversible, or a deploy script that has never been rolled back.
- A number in a doc with no command behind it, and a doc in `docs/` that differs from the root.
- Any change to `**/tests/**` that makes an assertion weaker, in a PR whose description doesn't say
  the assertion was wrong.
- A new external dependency added to get a feature 20% faster.
- Anything that lets an unattended actor move money, sign, publish, or email without a human gate.

**I would approve, gladly:**

- Deleting code, docs, or a feature that no longer earns its maintenance cost.
- A refusal code added because you found a failure mode I missed.
- A test that fails on `main` today (a bug you found before shipping it).
- A plain, boring implementation with an ugly-but-readable diff.
- A post-mortem entry with a prevention rule that is enforced by code.

## 6. Where I expect the project to break (my predictions, ranked)

Confidence is my honest estimate, and each one is checkable *before* it happens:

1. **The Bot ↔ boundary seam (T2/T3) — high confidence.** My brief describes it from upstream *docs*,
   not from my own reading of the tool-call path. The likely reality: there is no single chokepoint
   where every action passes, and you will have to build one. If so, that is not a detour — that is
   the project. Budget a week and do it properly; do not put the Sentinel "near" the calls.
2. **Routine double-dispatch — high.** `tick()` claims "exactly once per clock minute" and does not
   enforce it. Two ticks, two runs, double budget consumption. Write the failing test first.
3. **Approval starvation — high, and the most likely real-world failure.** A human gate that nobody
   clears means the company silently stops (or worse, someone approves blindly to unblock it). That
   is why T9 exists and why the digest escalates on age.
4. **Money drift — medium.** Idempotency keys are the only thing standing between you and double
   revenue. Test the replay. Test the webhook signature. Test the conditional approval update under
   concurrency; the SQLite version proves the shape, Postgres proves the behaviour.
5. **Untested recovery — medium.** Restore drill, rollback drill, kill-the-box drill. A backup you
   have never restored is a rumour.
6. **Model-cost creep — medium.** Agents with no per-run cap plus no per-day cap = a bill with no
   ceiling. Both caps exist in the code; keep them hard stops, passed down as constraints, and never
   as suggestions inside a prompt.
7. **Scope sprawl — medium.** The plan's own biggest stated risk. The next agent will be tempted by a
   second venture or a pretty dashboard. Milestones are the guard.
8. **Silent data staleness — low-medium.** The routine language for "the data is old, say so" exists
   (`STALE DATA — no market refresh today` in `scout-daily`). Keep that habit in every routine.
9. **A verification that silently skips when its input is absent — confirmed twice, so assume it is
   still somewhere.** The count guard compared against the wrong arithmetic; the `agent_impl` check
   was wrapped in `if os.path.isdir(repos/OpenBot)`. Both looked green. Test every guard by running it
   on a machine that is missing the thing it verifies — a copy without `repos/` found the second one
   in minutes.
10. **Upstream breaking changes — low-medium.** `repos/` has no git history (B3). Fix that on day one
   or you can never rebase.

## 7. What I expect you to produce (outcome, not activity)

Given ~2–3 focused weeks and the owner clearing B1/B4/B5/B6/B9:

- **M1:** one routine fires at 06:00 for seven consecutive days with no human step; anything dangerous
  asks first; the run row shows cost and outcome; the channel gets the brief. *Proof:* seven audit
  rows and seven channel messages with no manual touch.
- **M2:** a stranger pays for the Media API endpoint; the ledger row comes from a signed webhook; a
  refund is exercised in test mode; a rollback is executed once, on purpose; the 250 MB streaming test
  is green. *Proof:* `pnl.reconcile` returns `drift_usd == 0.00` against the provider's own total.
- **The intangible I actually want:** the console's P&L is something the owner would screenshot for an
  investor *without a human charting it by hand first*, and every number on it can be traced to rows
  in one query.

**What "done" does not mean:** a chat UI, a marketplace of skills, a mobile client, or a second
venture. None of those are in the milestone path, and any one of them can consume the whole budget.

## 8. The three texts I would write if this project needed one paragraph

- For the owner: *"You can leave. It asks before it hurts you, it writes everything down, and the
  numbers are arithmetic from rows — but it cannot think, so read the digest every morning."*
- For a customer: *"It turns media files into the exact format you need, priced per call, and you pay
  only after it works."*
- For a sceptic: *"It is a governance boundary with a company around it. The boundary is tested; the
  company is the part still being built."*

## 9. What I know I did not do, and my honest accounting

- I did not run the substrate (no Docker host, no model key, no Intelligence project). Everything
  about the OpenBot seam is documented, not exercised. `verify.sh` says this out loud in its warns.
- I did not deploy. No live URL, no TLS, no real users. `BLOCKERS.md` is the path; none of it executed.
- I did not test prompt quality or agent reliability beyond structure. **The agent's judgement is
  unmeasured** — this is the largest unknown, and it is why `aboutme.md` tags model quality as
  unverified rather than good.
- I did not do any legal, tax, or financial work, and nothing here should be read as advice.
- I left the workspace at 105 MB of a 128 MB cap; 8.6k of 10k files. Node/Bun binaries were removed
  by the snapshot cap and the recipe is in `tools/README.md`.
- I built skill files under `.claude/skills/` but the substrate is **not** wired to load them
  (`FEATURES.md`). Wiring them is small and unglamorous, so it will get forgotten. Do it before M1.
- `Worker.tick()` is not idempotent; I recorded that as a defect in `PROJECT_REMAINING.md` T1 instead
  of quietly fixing it inside a document-writing pass. That was a deliberate choice about honesty —
  fix it with a failing test, not a patch.
- `muse` is installed and configured but not used in any production path. Treat it as a lab tool.

## 10. Where my own reasoning has a hole (so you don't inherit it as confidence)

**The boundary judges actions; it cannot judge intent.** A plausible action name with a benign verb —
`read the customer list` — passes, and the assistant executing it may copy that list into an outbound
draft. The gate holds on *acts*, not on *thought*. Two implications:

1. Do not describe this system as safe against an adversarial model. It is safe against *wrong actions
   reaching the world unrecorded*. Those are different claims, and `disadvantages.md` says so.
2. The mitigation that actually works is not a better regex — it is **data minimisation** (a bot only
   reads what its routine declares) and **egress control** (what leaves the box). That is the next
   real safety upgrade after M1, and I would not let it slide past M3.

**Second hole: refusals are cheap, so the queue can act as a rubber stamp.** Friction is not
oversight. If a human approves twenty cards a day without reading, the gate is theatre. That is why
the digest carries age and why I would eventually want approval *samples* audited by a second human —
not because it is delightful, but because it is the failure mode that looks like success.

**Third hole: my cost model is a guess.** ~$100–150/mo for a small VPS + model usage at demo volume.
It is not measured against real traffic. Replace it with numbers from the first paid month before
anyone prices a second product off it.

## 11. If the owner or the substrate changes under you

- **If the substrate changes shape** (OpenBot renames tools, drops the policy hook, or breaks the AG-UI
  contract): the Sentinel stays valid — it judges actions, not frameworks. Re-point the adapter and
  move the mapping table; do not rewrite the boundary. Then bump the pin and log it in
  `INSTALL_LOG.md` + `patches/OPENBOT-OS.md`.
- **If the owner changes the product direction:** the boundary and the ledger still hold. What changes
  is the venture manifest and the policy file, which are data. Keep them data.
- **If the owner wants autonomy over money, legal, or sending:** say no once, explain the blast
  radius, then implement a *human operator console* instead. That is the version of the request that
  is safe and still useful.
- **If someone asks you to make it look further along than it is:** that is the one request that ends
  the project's value. The documents are the product's other half.

## 12. Final: my definition of "finished", and yours

Mine was: *the boundary works, the money is arithmetic, the refusals have reasons, a stranger can run
it, and the documents can fail the build when they stop being true.* That is done — 162 tests, smoke
green, verify GO for what is built.

Yours is: *a real person can pay, a real month can pass unattended without a sev1, and the owner can
read one page and know the truth.* Nothing in this repository is allowed to fake that, including the
documents you are about to write. When you get there, write your own version of this file, delete
mine, and sign it with what you actually measured — not with what you hoped.

---

## 13. What changed on the last day (so you trust the "state verified" line)

After I wrote the first version of these handover documents, I did the thing I should have done first:
**copied the repository the way a stranger gets it** — everything except `repos/`, `.git`,
`node_modules`, `__pycache__`, `.venv`, `archive/` — and ran the suite on the copy. It found two
guards that were green for the wrong reason:

1. the test-count guard compared against the wrong arithmetic (now asks pytest; it caught me three
   times while fixing it, which is the guard working);
2. `company.py` skipped its `agent_impl` verification entirely when `repos/OpenBot` was absent — so an
   invented runtime loaded clean on any machine without the substrate (now: committed manifest +
   drift check + refusal when it cannot verify).

Let me say that plainly, because it is the most useful thing in this file: **I had already declared
"done" once, and the fresh-copy test found two false greens in twenty minutes.** Whatever you declare
done, copy it somewhere clean and bet against yourself before you say it. That is the job, and it does
not stop being the job when the tests are all passing.

Also changed on the last day, so you are not surprised by them: `verify.sh` gained three gates
(deps importable, the API boots from an empty database, the kill switch rejects a bad argument without
mutating state); `scripts/*.sh` were not executable and now are, with a gate that fails if any is not;
CI gained a `fresh-clone` job that installs only `requirements.txt`, runs the suite, boots the app and
curls `/healthz`. All of it was found by being suspicious of a green board, not by reading code.

**Handover complete. Build well, and leave the next person a repository that can still fail.**
