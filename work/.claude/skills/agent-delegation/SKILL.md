---
name: agent-delegation
description: Hand coding work to a CLI agent (Claude Code, or Meta Muse Code's `muse`) with prompts that actually land — subagent patterns, worktree isolation, budget and stop conditions, verification gates, and how to review what came back. Use when writing a prompt for claude/muse, splitting work across subagents, or when a subagent produced plausible-looking code that does not work.
---

# Agent delegation

We are not "prompting". We are writing a **work order** with an acceptance test. A subagent that
returns code you have to rewrite was a badly written order, not a bad model.

## The order template (copy this)

```markdown
## Outcome
<One sentence a tester could verify. Not "improve X" — "POST /v1/split returns 200 with N segments for a 300MB mp4 in <20s".>

## Context you must read first
- docs/approvals.md (how gates work)
- services/media-api/AGENTS.md (venture rules)
- .openbot/post_mortems/error_registry.jsonl — class `dependency-version-drift` (write to /tmp kills big splits)

## Constraints
- Sandbox: work only inside repos/.../services/media-api. Never touch other ventures.
- Do not add dependencies without naming them here: ffmpeg (system), pytest.
- Boring over clever. Zeros: no placeholders, no TODO, no `pass`.
- Keep the public surface: existing tests must pass unmodified.

## Acceptance
1. `pytest -q` green, including a new test `test_300mb_split` using a synthetic fixture.
2. `curl` example in the PR body, with real output pasted.
3. A one-paragraph "what I would break next" note.

## Stop and ask when
- You need a real credential or a paid API.
- The acceptance test cannot pass without changing an existing public contract.
- You are about to touch repos/OpenBot (upstream) — write what you need instead.
- Two attempts at the same failing step. Do not try a third; report the trace.

## Report back
- files changed (paths), tests run (names), anything you could not do, and the exact command to reproduce.
```

## Splitting the work

| Situation | Pattern |
|---|---|
| One feature, one owner | single agent, one worktree |
| Independent features | parallel agents, **one git worktree each** (`git worktree add ../wt-<feature> -b feat/<feature>`) — Muse Code does this natively; with Claude Code do it by hand |
| A big refactor | explorer (read-only map) → planner (writes the plan file) → 2–3 implementers on disjoint dirs → reviewer |
| Reviewing | always a **separate** agent with the diff and the acceptance test, never the author |
| Anything touching money/security | human review, no exceptions, plus the sentinel-gate skill's test obligations |

Never let two agents write the same file. If they must, sequence them and say so.

## Muse Code specifics (`muse`, installed at ~/.local/bin/muse, verified 1.4.14)

**Use `scripts/muse-order.sh <order.md>` instead of calling `muse` by hand.** It refuses an order
without Outcome / Acceptance / Stop-and-ask, runs `muse exec --json`, streams events to
`.openbot/runs/<id>/events.jsonl`, exports a redacted trace with `muse export --last --redacted
--out <dir>/trace.json`, and writes `meta.json` (exit code, wall time, order sha, event bytes) so
agent cost is auditable. Smoke-test the plumbing any time with `--provider echo` (no key needed).

Verified behaviours that change how you plan:

- `muse skills list` **auto-loads this workspace's 8 `.claude/skills`** as user skills (34 loaded).
  Good: write a skill once, both Claude Code and Muse Code obey it.
- Project skills are **skipped until the workspace is trusted**; agent delegation is "auto
  unavailable" in an untrusted workspace. Trust it deliberately, once, not per run.
- `muse exec` **fails closed without a sandbox**: on this host it reported "Bubblewrap is
  unavailable … install your distribution's bwrap package" and that the binary itself sits under a
  writable root. Fix both (`apt install bubblewrap`, install muse outside your workspace) before any
  unattended order — an unsandboxed unattended agent is not acceptable.
- Every run emits an append-only event log (`task.lifecycle.*`, `side_effect_intent` with a
  `policy_decision`). That field is the bridge to our audit rows: copy `policy_decision` +
  `idempotency_key` into the run's audit entry rather than re-deriving why something was allowed.
- `muse export --redacted` gives a self-contained JSON (messages, tool calls, approvals, reasoning,
  lineage) — this is the artifact L2/L3 attach to a PR. Never export unredacted into the repo.

## Legacy notes (same rules, older CLI surface)

- Multi-agent by default: it fans work into background agents in isolated worktrees, with a
  reviewer in the background. Give it the order above; do not re-implement orchestration inside
  the prompt.
- It writes an **append-only local event log** (every model call, tool run, approval, edit). Use it:
  `muse` session logs are the replay source for post-mortems and for the postmortem skill's
  "replay test". Export the trace into `.openbot/runs/<run_id>/trace.jsonl`.
- Headless for routines and CI: `muse exec "<order>" --cwd <path>` (verify flags with
  `muse --help` on the installed version). Treat non-zero exit as a hard stop, then file a postmortem.
- Sandbox is on by default; a headless run needs bubblewrap on Linux. If `bwrap` is missing, the
  agent will refuse or run unsandboxed — never accept unsandboxed for unattended runs.
- It needs a Meta Model API account (subscription or key). Keep the key in the Sentinel keyring,
  not in the repo, and never in a routine body.

## Claude Code specifics

- `CLAUDE.md` at repo root is the constitution; keep it short (under ~150 lines) or the model
  starts skipping sections. Venture-specific rules go in `services/<x>/AGENTS.md`.
- Use `/skills` — the `.claude/skills/*/SKILL.md` files in this workspace are loaded on demand;
  name the skill you want it to load ("use the postmortem skill") instead of pasting rules.
- Subagents: `master-clone` pattern for heavy terminal work (OpenBot's own convention) — one
  long-lived clone per task, reuse it, so caches and shell state survive.

## Judging what came back (the 6-second triage)

1. Does the diff touch files the order did not name? → scope creep, read carefully.
2. Are new dependencies justified in the report? → if not, reject.
3. Did it delete or weaken a test? → `git diff --stat -- '**/tests/**'`. Weakening a test to pass
   is the most common failure mode of all coding agents.
4. Is there a pasted real output, or a described one? → described means not run.
5. Zeros present (`pass`, `TODO`, `NotImplemented`, `# type: ignore`, `any`)? → fix or reject.
6. Is the "what I would break next" note honest? → a dishonest note predicts the next incident;
   file a sev3 postmortem on the *process*.

## Cost and rate discipline

- State a token/time budget in the order when the task is exploratory ("spend at most 20 minutes
  mapping before proposing").
- Prefer one good agent with a precise order over five agents hunting. Parallelism earns its cost
  only when the work is genuinely disjoint.
- Log `{order_id, agent, model, wall_ms, tokens, exit}` to the run trace, so per-venture agent spend
  is visible in the P&L as `cogs`. Agents that hide their cost make the company's margin unknowable.
