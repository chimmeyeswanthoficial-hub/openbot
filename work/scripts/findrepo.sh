#!/usr/bin/env bash
# Locally reviewed, pinned, public-by-default CLI. Does not install anything or invoke init.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec node "$ROOT/tools/findrepo/skills/findrepo/scripts/findrepo.mjs" "$@"
