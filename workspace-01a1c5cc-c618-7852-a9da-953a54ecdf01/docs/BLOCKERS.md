# BLOCKERS.md — what stands between today and a running company

Ordered. Each step has a **check** that must print green before the next step is worth starting.
Nothing below needs an agent to guess; if a check fails, stop and read the error.

---

## B1 — A Linux box with Docker (blocks everything)

Own VPS, Hetzner-class, 2 vCPU / 4 GB / 80 GB is enough for the substrate + first venture.

```sh
# on the box
sudo apt update && sudo apt install -y ca-certificates curl git ufw
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker "$USER" && newgrp docker
docker run --rm hello-world                      # CHECK 1
docker compose version                           # CHECK 2 (needs the compose plugin)
```

Then: `ufw allow 22,80,443/tcp && ufw enable`; disable password SSH; add your key.
**Do not** expose ports 3001, 4100, 4500, 5432, 8090 to the internet — they are host-local by design
(see `plan.md` §4). Public entry is nginx/caddy in front of `app:3010` only.

## B2 — Toolchain on the box (blocks the repos)

```sh
curl -fsSL https://fnm.vercel.app/install | bash && fnm install 24 && fnm default 24
curl -fsSL https://bun.sh/install | bash
npm i -g pnpm@12.18.0
node -v   # v24.x   — CHECK
bun -v    # 1.4+    — CHECK
pnpm -v   # 12.18.0 — CHECK
```

Install `muse` **outside** your workspace root (it warns otherwise): `MUSE_INSTALL_DIR=/opt/muse bash -c 'curl -fsSL https://dev.meta.ai/install.sh | bash'`
and `sudo apt install -y bubblewrap` — without bwrap, `muse exec` refuses to run sandboxed, and an
unsandboxed unattended agent is not acceptable (`plan.md` §8).

## B3 — The repos, with history this time

```sh
mkdir -p ~/openbot-os && cd ~/openbot-os
git clone --depth 1 https://github.com/CopilotKit/OpenBot.git  repos/OpenBot
git clone --depth 1 https://github.com/elie222/rakazo.git      repos/rakazo
git clone --depth 1 https://github.com/CopilotKit/OpenDots.git repos/OpenDots
(cd repos/OpenBot && bun install --frozen-lockfile)
(cd repos/rakazo && pnpm install --frozen-lockfile)
(cd repos/OpenDots && npm ci && cp .env.example .env)
```

Copy `services/`, `.claude/`, `.openbot/`, `scripts/`, `patches/`, `plan.md`, `STACK_DECISIONS.md`
from this workspace into `~/openbot-os` and commit them. Tag the upstream pins:

```sh
(cd repos/OpenBot && git tag upstream-pin-20261109)   # same for the other two
```

## B4 — CopilotKit Intelligence project (blocks any conversation)

OpenBot stores threads and memory in Intelligence; a licence/project is required (a free plan exists
and it can be self-hosted).

```sh
cd ~/openbot-os/repos/OpenBot
cp .env.example .env
npx --yes copilotkit@latest login
npx --yes copilotkit@latest project select   # writes CPK_INTELLIGENCE_API_KEY
bun scripts/setup-learning.ts                # creates/reuses the `openbot` learning container
```

## B5 — One model key (blocks every agent turn)

Pick one to start. OpenAI is the shortest path (OpenBot's proof-of-concept bot is OpenAI-only;
`BOT_PROVIDER=anthropic` is the alternative).

```sh
# in repos/OpenBot/.env
OPENAI_API_KEY=sk-...        # CHECK: server starts and a bot answers
# or
BOT_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

Optional, later: a Meta Model API key so `muse` can run turns (`muse auth set --provider meta --api-key-stdin`).

## B6 — Generate the real secrets (OpenBot refuses placeholder secrets in production)

```sh
cd ~/openbot-os/repos/OpenBot
python3 - <<'PY'
import base64, os, secrets, pathlib
vals = {
 "KEY_ENCRYPTION_KEY": base64.b64encode(os.urandom(32)).decode(),
 "COMPUTER_TOKEN": secrets.token_urlsafe(32),
 "SUPERVISOR_TOKEN": secrets.token_urlsafe(32),
 "AGENT_TOOL_TOKEN": secrets.token_urlsafe(32),
 "MANAGED_AGENT_TOKEN": secrets.token_urlsafe(32),
 "WORKER_SHARED_SECRET": secrets.token_urlsafe(32),
}
env = pathlib.Path(".env"); text = env.read_text()
for k, v in vals.items():
    if f"\n{k}=" in text:
        text = "\n".join(l if not l.startswith(k + "=") else f"{k}={v}" for l in text.splitlines())
        if not text.endswith("\n"): text += "\n"
    else:
        text += f"{k}={v}\n"
env.write_text(text); print("wrote", ", ".join(vals))
PY
```

`KEY_ENCRYPTION_KEY` encrypts stored credentials: **changing it later orphans every stored key.**
Back it up in your password manager now, not later.

## B7 — Boot the substrate

```sh
cd ~/openbot-os/repos/OpenBot
bash scripts/start.sh      # Postgres, agent-computer, agent-langgraph, agent-bot, supervisor, migrate, server, worker, app
```

Checks, in order:

```sh
curl -sf localhost:3001/health || echo "server down"     # CHECK
open http://localhost:3010                                # app loads, sign in
# in the app: open a Bot, ask it to list files in its computer → proves agent → computer → gateway
```

Then put Caddy/nginx in front with TLS so the app is reachable at `https://…` (Intelligence setup and
provider OAuth need HTTPS). `TRUSTED_ORIGINS` in `.env` must include that origin.

## B8 — Sentinel in the loop

```sh
cd ~/openbot-os/services/sentinel
python3 -m venv .venv && . .venv/bin/activate && pip install fastapi uvicorn pytest httpx pyyaml pydantic
pytest -q                                  # 37 passed — CHECK
uvicorn app:app --host 127.0.0.1 --port 8090
curl -s localhost:8090/healthz             # {"ok":true,...} — CHECK
```

Keep it on 127.0.0.1 behind the same reverse proxy, and add it to the compose file as a service when
you move past M1.

## B9 — Money rails (needed for the first dollar, not for the first commit)

1. Create a **Stripe account** (test mode works immediately, no entity required).
2. Create the two products/prices from `venture.yaml` (`starter $19`, `growth $79`).
3. Point the webhook at your venture service; verify the signature; write ledger rows keyed by the
   Stripe event id (idempotent — `STACK_DECISIONS.md` D5).
4. **Live mode needs an entity + bank account.** That is a human, days-to-weeks task. Start it in
   parallel with B1–B7, or the first paying customer will arrive before you can take the money.

## B10 — The dead-man's switch (needed before you leave, not before you launch)

An external monitor (Healthchecks.io, Better Stack, or a $5 cron on a different provider) that alerts
you if:
- the control plane stops heartbeating for 2 hours, **and**
- no routine has completed in 6 hours.

Two different signals on purpose: a company that is alive but idle and a company that is dead look
identical from one metric.

---

## What can be done *today*, with none of the above

These are real and they compound later:

- `services/sentinel` — extend policies, add the Postgres store for audit + approvals (M1).
- `packages/venture-sdk` — manifest validation, so `media-api` can't be started half-specified.
- `services/worker` — the markdown routine parser + `dry_run.py`; `scout-daily.md` already parses.
- `.claude/skills` — keep adding rules as you learn them; they cost nothing and they are what makes
  the repos obey you later.
- `services/evals` — write the 20 safety cases now, so model changes in month 3 are decidable.

Order: **B1 → B2 → B3 → B4 → B5 → B6 → B7 → B8**. B9 and B10 run in parallel; they are calendar
tasks, not engineering tasks.
