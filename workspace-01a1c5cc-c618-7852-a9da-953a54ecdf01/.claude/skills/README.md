# Skills index — OpenBot OS

Skills are the operating manual for this workspace. Each one is a `SKILL.md` with YAML
front-matter (`name`, `description`) that an agent loads on demand — Claude Code reads
`.claude/skills/`, Muse Code reads the same order text when you paste/point it, and humans read
them as the design decisions they are.

| Skill | Load when |
|---|---|
| [`project-owner`](project-owner/SKILL.md) | the role the assistant holds: release bar, decision rights, self-policing |
| [`openbot-os`](openbot-os/SKILL.md) | always, first |
| [`routine-authoring`](routine-authoring/SKILL.md) | writing/parsing markdown routines, schedules |
| [`sentinel-gate`](sentinel-gate/SKILL.md) | any outbound call, secret, spend, delete, message |
| [`postmortem`](postmortem/SKILL.md) | any failure; before any new venture |
| [`venture-launch`](venture-launch/SKILL.md) | a new business, pricing, P&L, kill criteria |
| [`agent-delegation`](agent-delegation/SKILL.md) | writing a work order for claude/muse |
| [`upstream-merge`](upstream-merge/SKILL.md) | editing `repos/` or taking an upstream release |
| [`ship-it`](ship-it/SKILL.md) | deploy, migrate, monitor, run unattended |

## The company's own documents (read before promising anything)

| Document | What it settles |
|---|---|
| `aboutme.md` | what the company is, its roles, its honest costs, how to manage it |
| `advantages.md` | the positive case, each claim with a mechanism and a measurement |
| `disadvantages.md` | hard limits, legal walls by industry, where it underperforms a human |
| `FEATURES.md` | what we take from each upstream, verified in source, and the build order |
| `company/company.yaml` | the org chart the runtime validates before it will run |

The rule: **`aboutme.md` is the only place a capability may be claimed.** If it says `[M2]`, quote
the milestone; if it says `[human]` or `[never]`, hand it back.

Inherited from the upstream repos and kept as-is (do not duplicate):

- `repos/OpenBot/.claude/skills/openbot-copy` — the words and voice for anything a person reads.
- `repos/OpenBot/.claude/skills/openbot-data-access` — how to read product data safely.
- `repos/OpenBot/.claude/skills/openbot-screen-layout` — screen structure conventions.
- `repos/rakazo/.agents/skills/*` — release, pr-watch, ux-declutter, translate, composio.
- `repos/rakazo/skills-lock.json` — pinned external skill (Composio) with a content hash.

## How to invoke

Say the skill's name in the order: *"Use the sentinel-gate skill. Add a refund path to
media-api."* An agent that has to guess which rules apply will invent its own, and its own rules
will be wrong.
