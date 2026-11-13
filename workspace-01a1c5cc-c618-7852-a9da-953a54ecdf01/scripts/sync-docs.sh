#!/usr/bin/env bash
# Keep docs/ an exact mirror of the root documents. Run after editing any of them; `make verify`
# fails when the mirror drifts, so a published docs site can never serve a stale claim.
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p docs
rm -f docs/PROJECT_BRAIN.md      # internal: it stays in the root, never published
for f in plan.md aboutme.md advantages.md disadvantages.md FEATURES.md BLOCKERS.md \
         STACK_DECISIONS.md INSTALL_LOG.md CONTRIBUTING.md SECURITY.md CHANGELOG.md ROADMAP.md \
         PROJECT_STATE.md PROJECT_REMAINING.md; do
  cp "$f" "docs/$f"
done
echo "docs/ synced: $(ls docs/*.md | wc -l | tr -d ' ') files"
