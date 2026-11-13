#!/usr/bin/env bash
# Your workspace snapshot is capped (128 MB / 10k files), so 77 large media files (33 MB) were removed
# from repos/*/docs, public/ and assets/. They are unmodified upstream assets — nothing of ours.
# Restore any of them, or all of them:
#   scripts/restore-media.sh                 # restore everything, from the upstream repos
#   scripts/restore-media.sh rakazo/docs/screenshots/demo.mp4
set -euo pipefail
cd "$(dirname "$0")/.."
MANIFEST=archive/repos-media/MANIFEST.json
[ -f "$MANIFEST" ] || { echo "manifest gone; nothing to restore"; exit 0; }
declare -A REPO_OF=( [OpenBot]=CopilotKit/OpenBot [rakazo]=elie222/rakazo [OpenDots]=CopilotKit/OpenDots )
restore() { # $1 = path relative to repos/
  local rel="$1" repo rest url
  repo="${rel%%/*}"; rest="${rel#*/}"
  url="https://raw.githubusercontent.com/${REPO_OF[$repo]}/main/${rest}"
  mkdir -p "repos/$(dirname "$rel")"
  curl -fsSL -o "repos/$rel" "$url" && echo "restored $rel"
}
if [ $# -gt 0 ]; then for p in "$@"; do restore "$p"; done; exit 0; fi
python3 -c "import json;[print(f['path']) for f in json.load(open('$MANIFEST'))['files']]" | while read -r p; do restore "$p"; done
