#!/usr/bin/env bash
# Session-start state check for OpenBot OS. Prints what an agent must know before it acts.
set -uo pipefail
cd "$(dirname "$0")/.." 2>/dev/null || true

echo "=== last 3 post-mortems ==="
tail -3 .openbot/post_mortems/error_registry.jsonl 2>/dev/null | jq -r \
  '"\(.id)  [\(.severity)/\(.class)]  \(.prevention_rule[0:110])"' 2>/dev/null || echo "(none yet)"

echo
echo "=== active ventures ==="
for f in .openbot/ventures/*/venture.yaml; do
  [ -e "$f" ] || continue
  slug=$(basename "$(dirname "$f")")
  status=$(grep -m1 '^status:' "$f" | awk '{print $2}')
  budget=$(grep -m1 'auto_spend_usd:' "$f" | awk '{print $2}')
  printf '%-14s %-10s auto_spend=%s\n' "$slug" "${status:-?}" "${budget:-?}"
done

echo
echo "=== budget today ==="
cat .openbot/state/budget.json 2>/dev/null || echo '{"note":"not initialised — run scripts/init-state.sh"}'

echo
echo "=== upstream pins ==="
cat .openbot/state/upstream.json 2>/dev/null || echo "(no pins recorded)"

echo
echo "=== skills available ==="
ls .claude/skills/*/SKILL.md 2>/dev/null | xargs -r -n1 dirname | xargs -r -n1 basename | paste -sd' '
