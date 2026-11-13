#!/usr/bin/env bash
# OpenBot OS — Deploy & Rollback Runner (T7)
set -euo pipefail
cd "$(dirname "$0")/.."

python3 scripts/deploy.py "$@"

