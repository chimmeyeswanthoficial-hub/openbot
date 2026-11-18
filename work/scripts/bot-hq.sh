#!/usr/bin/env bash
# Installed Bot HQ local profile. NO provider setup, sudo, deploy or background daemon.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
mode="${1:-help}"
CACHE="$ROOT/.cache/openbot-hq"
case "$mode" in
  access-code)
    if [ ! -f "$CACHE/access-code" ]; then echo 'Start the local workspace first; no access code exists yet.' >&2; exit 2; fi
    cat "$CACHE/access-code"; exit 0 ;;
  help|-h|--help)
    printf '%s\n' 'Bot HQ local-only installation (Linux x86_64 / Python 3.13):' \
      '  bash scripts/bot-hq.sh install      # checksum-pinned Node, hashed Python wheels, npm ci --ignore-scripts, build' \
      '  bash scripts/bot-hq.sh start        # foreground authenticated workspace on 0.0.0.0:8787; no providers' \
      '  bash scripts/bot-hq.sh access-code  # print local sign-in code; do not share or commit it' \
      '  bash scripts/bot-hq.sh test         # kernel and host regressions; disposable state' \
      '  bash scripts/bot-hq.sh build        # typecheck and build without enabling providers' \
      'Stop with Ctrl-C or the process manager. State is preserved under .openbot/hq{,-kernel}/.'
    exit 0 ;;
esac
if [ "$mode" = install ]; then
  # Some workspace transfers normalize file modes; restore our own entry scripts, not donors.
  chmod u+x scripts/*.sh .claude/skills/postmortem/check.sh
  python3 -c 'import sys; assert sys.version_info[:2] == (3, 13), "Tested hashed wheel lock requires Python 3.13. Review a new lock for other runtimes."'
  NODE_BIN="$(python3 scripts/bootstrap-bot-hq.py)"
  export PATH="$NODE_BIN:$PATH"
  if [ ! -x .venv/bin/python ]; then python3 -m venv .venv; fi
  .venv/bin/python -m pip install --disable-pip-version-check --require-hashes --only-binary=:all: -r requirements.handoff.lock.txt
  npm ci --ignore-scripts --no-audit --no-fund --prefix apps/bot-hq
  (cd apps/bot-hq && node --input-type=module -e 'import Database from "better-sqlite3"; const db=new Database(":memory:"); if(db.prepare("select 1 ready").get().ready!==1) process.exit(1); db.close(); console.log("SQLite packaged native binding verified; no lifecycle script/rebuild run.");')
  npm run typecheck --prefix apps/bot-hq
  npm run build --prefix apps/bot-hq
  echo 'Bot HQ local profile installed and built. No server/provider/daemon was started.'
  exit 0
fi
NODE_BIN="$ROOT/.cache/openbot-toolchains/node-v24.22.3-linux-x64/bin"
if [ ! -x "$NODE_BIN/node" ] || [ ! -d apps/bot-hq/node_modules ] || [ ! -x .venv/bin/python ]; then
  echo 'Dependencies/toolchain are absent (snapshots exclude them). Run: bash scripts/bot-hq.sh install' >&2; exit 2
fi
export PATH="$NODE_BIN:$PATH"
case "$mode" in
  build)
    npm run typecheck --prefix apps/bot-hq
    npm run build --prefix apps/bot-hq ;;
  test)
    npm run typecheck --prefix apps/bot-hq
    npm run build --prefix apps/bot-hq
    PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest scripts/tests/test_hq_readiness.py scripts/tests/test_hq_installation.py -p no:cacheprovider
    node --test apps/bot-hq/server/test/*.test.mjs ;;
  start)
    if [ ! -f apps/bot-hq/server/dist/local-entry.js ] || [ ! -f apps/bot-hq/web/dist/index.html ]; then
      echo 'Build outputs do not persist in snapshots. Run: bash scripts/bot-hq.sh build' >&2; exit 2
    fi
    umask 077
    mkdir -p "$CACHE" "$ROOT/.openbot/hq" "$ROOT/.openbot/hq-kernel"
    python3 - "$CACHE" <<'PY'
from pathlib import Path
import os, secrets, sys
base = Path(sys.argv[1])
for name in ('access-code', 'session-secret'):
    p = base / name
    if p.is_symlink():
        raise SystemExit('Refusing symlinked authentication file')
    if not p.exists():
        fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'w') as stream:
            stream.write(secrets.token_urlsafe(36) + '\n')
    os.chmod(p, 0o600)
PY
    echo 'Starting authenticated local HQ. Get the code in another terminal: bash scripts/bot-hq.sh access-code'
    # Strip the inherited environment. Even accidentally present provider/SSH/payment keys do not reach Node.
    exec env -i PATH="$NODE_BIN:/usr/local/bin:/usr/bin:/bin" HOME="$HOME" LANG=C.UTF-8 \
      HQ_LOCAL_ONLY=1 HQ_ACCESS_CODE="$(cat "$CACHE/access-code")" SESSION_SECRET="$(cat "$CACHE/session-secret")" \
      PORT="${HQ_PORT:-8787}" DB_PATH="${HQ_DB_PATH:-$ROOT/.openbot/hq/hq.sqlite3}" \
      HQ_KERNEL_STATE_DIR="${HQ_KERNEL_STATE_DIR:-$ROOT/.openbot/hq-kernel}" \
      OPENBOT_PROJECT_ROOT="$ROOT" OPENBOT_PYTHON="$ROOT/.venv/bin/python" \
      node "$ROOT/apps/bot-hq/server/dist/local-entry.js" ;;
  *) echo "Unknown mode: $mode. Use --help." >&2; exit 2 ;;
esac
