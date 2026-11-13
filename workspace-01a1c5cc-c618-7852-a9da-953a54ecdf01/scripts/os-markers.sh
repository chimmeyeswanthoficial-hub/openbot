#!/usr/bin/env bash
# Lists OPENBOT-OS markers in repos/ and cross-checks them against patches/OPENBOT-OS.md.
# Usage: scripts/os-markers.sh          (report)
#        scripts/os-markers.sh --check  (exit 1 on a mismatch; for CI)
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
markers=$(grep -rn "OPENBOT-OS:" repos \
  --include='*.ts' --include='*.tsx' --include='*.js' --include='*.py' \
  --include='*.md' --include='*.yaml' --include='*.yml' --include='*.json' \
  --exclude-dir=node_modules --exclude-dir=build --exclude-dir=dist --exclude-dir=.git \
  --exclude-dir=coverage --exclude-dir=out --exclude-dir=target 2>/dev/null)
count=$(printf '%s\n' "$markers" | grep -c .)
echo "markers in repos/: ${count}"
printf '%s\n' "$markers" | grep . | sed 's/^/  /'
documented=$(grep -c '^| .repos/' patches/OPENBOT-OS.md 2>/dev/null | tail -1)
documented=${documented:-0}
echo "documented rows:   ${documented}"
if [ "${1:-}" = "--check" ] && [ "${count}" != "${documented}" ]; then
  echo "FAIL: marker/documentation count mismatch" >&2; exit 1
fi
[ "${1:-}" = "--check" ] && echo "OK: markers and patches/OPENBOT-OS.md agree"
exit 0
