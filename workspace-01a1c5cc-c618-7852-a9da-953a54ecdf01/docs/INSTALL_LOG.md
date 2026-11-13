# Install log — 2026-11-10

What was installed, how it was verified, and what could not be done in this environment.
Everything below is reproducible from a clean Linux sandbox with network access.

## Environment found

| Thing | Found | Needed | Action |
|---|---|---|---|
| OS / user | Linux, non-root | — | — |
| Python | 3.13.16 | 3.11+ | used as-is |
| Node | 20.20.2 | **24.x** (Rakazo, OpenDots) | installed portable Node **24.22.2** → `tools/node24` |
| npm prefix | `/usr/lib` (not writable) | writable | `npm_config_prefix=/home/user/tools` |
| Bun | absent | 1.4+ (OpenBot) | Bun **1.4.4** → `tools/bun-linux-x64` |
| pnpm | absent | **12.18.0** (Rakazo pins it) | pnpm **12.18.0** → `tools/bin/pnpm` |
| Docker | **absent** | required by OpenBot/Rakazo computers | **not installed** — see Gaps |
| git | 2.47.3 | — | `git clone` crashes this sandbox shell; tarballs used |

> **Note:** the portable toolchain (`tools/node24`, `tools/bun-linux-x64`, `tools/bin/pnpm`) was
> removed after verification to keep the workspace snapshot small (~600 MB of binaries). Re-create it
> with `tools/README.md`. The Python side (Sentinel, tests) needs none of it and still runs.

Add to your shell once:

```sh
export PATH="$HOME/tools/node24/bin:$HOME/tools/bin:$HOME/tools/bun-linux-x64:$HOME/.local/bin:$PATH"
```

## 1. Repositories

`git clone` terminated the sandbox shell (no stderr, exit null) for every repo, so each was fetched
as a release tarball instead — identical source, no `.git` history.

```sh
cd ~/repos
curl -sSL -o rakazo.tar.gz   https://codeload.github.com/elie222/rakazo/tar.gz/refs/heads/main
curl -sSL -o OpenBot.tar.gz  https://codeload.github.com/CopilotKit/OpenBot/tar.gz/refs/heads/main
curl -sSL -o OpenDots.tar.gz https://codeload.github.com/CopilotKit/OpenDots/tar.gz/refs/heads/main
for f in *.tar.gz; do d="${f%.tar.gz}"; mkdir -p "$d" && tar xzf "$f" -C "$d" --strip-components=1; done
```

| Repo | Files | Size | Role |
|---|---|---|---|
| `repos/OpenBot` | 3,482 | 64 MB | substrate |
| `repos/rakazo` | 4,954 | 76 MB | feature donor |
| `repos/OpenDots` | 207 | 12 MB | review-gate donor |

To restore git history on your own machine:

```sh
cd repos/OpenBot && git init && git remote add origin https://github.com/CopilotKit/OpenBot.git && git fetch --depth 1 origin main && git reset --hard FETCH_HEAD
# same for rakazo (elie222/rakazo) and OpenDots (CopilotKit/OpenDots)
```

## 2. Dependencies

| Repo | Command | Result |
|---|---|---|
| OpenBot | `bun install --frozen-lockfile` | **1,282 packages in 12s**; 2 postinstalls blocked (safe) |
| rakazo | `pnpm install --frozen-lockfile --ignore-scripts` | **2,200 packages in 29.5s** |
| OpenDots | `npm ci --no-audit --no-fund` | **1,046 packages in 29s** |

Verification actually run:

| Check | Result |
|---|---|
| `repos/OpenDots`: `npm run typecheck` (`tsc --noEmit`) | ✅ exit 0, no output |
| `repos/OpenBot`: `bun test` | not run — the suite needs Docker (Postgres + computers) |
| `repos/rakazo`: `pnpm turbo run typecheck` | not run — needs a Postgres/Docker stack and ~2 min per package |

Notes: `--ignore-scripts` on rakazo skips native postinstalls; run `pnpm rebuild` on a real machine.
OpenDots `.env` was created from `.env.example`.

## 3. Meta Muse Code (`muse`)

The command you gave, `irm https://dev.meta.ai/install.ps1 | iex`, is the **Windows PowerShell**
installer for **Meta Muse Code**, the terminal coding agent (not the consumer "Muse" app). Its own
help text exits with `installer.ps1 supports Windows only; use installer.sh on macOS or Linux`.

Linux equivalent, with the install dir pinned inside the workspace:

```sh
curl -fsSL https://dev.meta.ai/install.sh -o meta-install.sh
MUSE_INSTALL_DIR=$HOME/.local/bin bash meta-install.sh
```

Result: `~/.local/bin/muse` → `muse-bin-1.4.14-R7309.1` (396 MB), and:

```
$ muse --version
Muse Code 1.4.14 (1.4.14-R7309.1)
```

The installer verifies an `x-content-sha256` header when the server advertises one. Muse needs a
**Meta Model API account** (subscription or API key) before it can run a turn; none is configured.
Note: `~/.local` is treated as a cache directory by this workspace's snapshotter, so re-install on a
fresh session with the two commands above, or install to `~/tools/muse` to keep it.

## 4. What we built on top (all verified)

| Artifact | Verification |
|---|---|
| `services/sentinel/policy.py` + `app.py` | `pytest -q` → **37 passed** |
| Sentinel service on `:8090` | `curl /healthz` → `{"ok":true,"policies":["media-api"],...}` |
| Live gate demo | `POST /v1/decide` with `gmail.send_message` → `gate`, `rule: comms.outbound`, `approval_id: ap_…` |
| Post-mortem ledger + checker | `.claude/skills/postmortem/check.sh` → `1 entries, 0 problem(s)` |
| Skills | 8 × `SKILL.md` + `README.md` index, listed by `scripts/session-start.sh` |
| Session state check | `scripts/session-start.sh` prints ledger, ventures, budget, pins, skills |

## 5. Gaps and why they matter

1. **No Docker.** OpenBot's value is its per-bot computers and supervisor, RabbitMQ-free Postgres and
   its compose stack; Rakazo's local computers are Docker too. Neither can start here. The substrate
   must be deployed on a Docker host — that is item 1 of the 14-day list in `plan.md` §11.
2. **No model keys / no Intelligence project.** OpenBot and OpenDots both need a CopilotKit
   Intelligence project plus a model provider key before a conversation works. Not installed.
3. **No git history** in the three repos (tarball install), so `upstream-merge`'s rebase flow has
   nothing to rebase against yet.
4. **No Meta Model API key**, so `muse` is installed but cannot run a task.
5. **`~/.local` is excluded from workspace snapshots**; re-run the Muse installer when resuming a
   fresh sandbox, or move it under `~/tools`.

## 6. One-command re-create (on a normal Linux box with Docker)

```sh
# toolchain
curl -fsSL https://fnm.vercel.app/install | bash && fnm install 24 && fnm default 24
curl -fsSL https://bun.sh/install | bash
npm i -g pnpm@12.18.0
curl -fsSL https://dev.meta.ai/install.sh | bash

# repos
cd ~ && mkdir -p repos && cd repos
git clone --depth 1 https://github.com/CopilotKit/OpenBot.git
git clone --depth 1 https://github.com/elie222/rakazo.git
git clone --depth 1 https://github.com/CopilotKit/OpenDots.git

# deps
(cd OpenBot && bun install) && (cd rakazo && pnpm install) && (cd OpenDots && npm ci && cp .env.example .env)

# our services
cd ~ && python3 -m venv .venv && . .venv/bin/activate && pip install fastapi uvicorn pytest httpx pyyaml pydantic
cd services/sentinel && pytest -q && uvicorn app:app --port 8090
```
