#!/usr/bin/env bash
# Dry-run by default. --apply removes allowlisted untracked caches only.
# Never removes .openbot state/runs, logs, donor repos, archives or Git-tracked files.
set -euo pipefail
cd "$(dirname "$0")/.."
exec "${PYTHON:-python3}" -B scripts/workspace_hygiene.py "$@"
