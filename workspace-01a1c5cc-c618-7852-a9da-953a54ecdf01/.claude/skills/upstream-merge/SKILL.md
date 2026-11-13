---
name: upstream-merge
description: Change OpenBot, Rakazo or OpenDots without losing the ability to merge upstream later — the seam rules, the OPENBOT-OS marker convention, plugin vs fork decisions, and the quarterly rebase drill. Use before editing anything under repos/, when an upstream release lands, or when deciding whether a feature should be a plugin, a patch, or a separate service.
---

# Upstream merge

Three fast-moving upstreams (OpenBot, Rakazo, OpenDots) and one small team. The only way this
survives a year of unattended operation is if our code is a **thin coat** on code we can re-pull.

## Decide the seam first

| Need | Do this | Never |
|---|---|---|
| New capability the product already models as an extension point | build a **plugin / bot / component / skill** using the upstream's own API (OpenBot plugins + AG-UI bots + components; Rakazo adapters; OpenDots tool permissions) | patch core |
| Business logic the product has no concept of (ventures, P&L, ledger) | a **separate service** in `services/` that talks over HTTP/AG-UI | put finance in the agent server |
| A small behaviour change in upstream | a **patch with an upstream PR first** — submit to the project; carry it in `patches/` (pnpm patch / bun patch) until merged | a silent edit |
| Security boundary | our own service (`services/sentinel`), in front, not inside | trust a prompt |

Naming: OpenBot already uses `agent-*`, `-agui` and `agent-computer`; OpenDots is a "template, not a
product" and forbids wide forks; Rakazo's monorepo is feature-dense but heavy. So: **OpenBot is the
host, Rakazo is a donor, OpenDots is a pattern.**

## The marker convention

Every edit inside `repos/` gets a comment on the line above, and an entry in
`patches/OPENBOT-OS.md`:

```ts
// OPENBOT-OS: initiator=routine must reach the audit row (see .openbot/post_mortems/pm_..._03)
```

Rules:
- one line, names the *why* and links the ledger id or issue.
- no markers in generated files, lockfiles, or vendored code.
- `scripts/os-markers.sh` lists every marker; CI fails if a marker has no line in
  `patches/OPENBOT-OS.md` (and vice versa).
- a marker older than two upstream releases must be either upstreamed or moved to `patches/`.

## Working a new upstream release

1. `git -C repos/OpenBot fetch --tags && git log --oneline HEAD..origin/main` — read, don't skim.
2. Read their `CHANGELOG.md` sections for **Security**, **Self-host upgrade notes**, and anything
   that changes database migrations or env var names.
3. Re-apply markers: `git rebase main` in our branch, then `scripts/os-markers.sh --diff`.
4. Run the three smokes: OpenBot `bun test` on the touched packages, Rakazo `pnpm turbo run
   typecheck`, OpenDots `npm run typecheck && npm test`.
5. Run **our** conformance suite (the thing that actually matters):
   - a routine fires, is audited with `initiator=routine`, and lands in its channel;
   - a spend attempt interrupts and cannot continue without approval;
   - a cross-venture file read is denied;
   - the P&L ledger still reconciles to the provider sandbox.
6. Only then upgrade the running deployment, in a canary computer first.

## Version pinning

- `repos/OpenBot` tracks a **tag**, not `main`. Write the tag in `STACK_DECISIONS.md` and in
  `.openbot/state/upstream.json`.
- Monthly: bump one upstream, not three in the same week. The month's postmortem ledger will tell
  you which one is causing churn.
- Rakazo/OpenDots: we pin the **patterns** we ported, with a link + commit sha in
  `services/*/PORTED_FROM.md`, so a later reader knows what "we copied this" means.

## Licensing and hygiene

- OpenBot is MIT, Rakazo Apache/MIT (check `LICENSE` before copying code), OpenDots MIT
  (verify each time — these change). Record the licence of every ported file.
- Never copy `Intelligence` (separately licensed) code or any CopilotKit cloud-only asset.
- No customer data, keys, or transcripts in `repos/` or docs — those go in the deployment's
  secret store and Postgres.
- Keep our `AGENTS.md`/`CLAUDE.md` additions in the root file's "OpenBot OS" section only, so a
  diff against upstream is one block.
