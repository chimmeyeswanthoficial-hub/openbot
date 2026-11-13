#!/usr/bin/env bash
# End-to-end smoke: boot a fresh control plane on a scratch DB and port, seed it, assert the
# numbers, assert the gates, and shut it down. `make smoke`.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
PORT="${SMOKE_PORT:-8099}"
DB="$(mktemp -u /tmp/openbot-smoke-XXXXXX.db)"
LOG="$(mktemp /tmp/openbot-smoke-XXXXXX.log)"
fail=0
say() { printf '  %s %s\n' "$1" "$2"; }
check() { if [ "$1" = "1" ]; then say "PASS" "$2"; else say "FAIL" "$2"; fail=$((fail+1)); fi; }

echo "== booting a clean control plane on :$PORT with $DB"
SENTINEL_DB="$DB" python3 -m uvicorn app:app --host 127.0.0.1 --port "$PORT" \
  --app-dir services/sentinel >"$LOG" 2>&1 &
PID=$!
trap 'kill $PID 2>/dev/null; rm -f "$DB"' EXIT
for _ in $(seq 1 40); do
  curl -sf -m 1 "127.0.0.1:$PORT/healthz" >/dev/null 2>&1 && break
  sleep 0.25
done

health=$(curl -s -m 2 "127.0.0.1:$PORT/healthz")
[ -n "$health" ] && check 1 "service answers /healthz" || check 0 "service answers /healthz"

python3 scripts/seed-demo.py --base "http://127.0.0.1:$PORT" >/tmp/smoke-seed.log 2>&1
[ $? -eq 0 ] && check 1 "seed wrote through the validated paths" || { check 0 "seed"; cat /tmp/smoke-seed.log; }

# --- the numbers must be arithmetic, not decoration
pnl=$(curl -s "127.0.0.1:$PORT/v1/pnl")
python3 - "$pnl" <<'PY'
import json, sys
p = json.loads(sys.argv[1])["portfolio"]
# rows: 19 + 79 + 19 (one replay ignored) - 19 refund = 98 net
# cogs 14.60 + fee 3.42 = 18.02 -> gross 79.98 ; agent 8.21 + marketing 25 -> contribution 46.77
ok = (p["net_revenue"] == 98.0 and p["gross_profit"] == 79.98 and p["contribution"] == 46.77)
print(("  PASS" if ok else "  FAIL") + f" pnl arithmetic net={p['net_revenue']} gross={p['gross_profit']} contribution={p['contribution']}")
sys.exit(0 if ok else 1)
PY
[ $? -eq 0 ] && check 1 "revenue is arithmetic from rows (replay ignored)" || check 0 "revenue arithmetic"

# --- gates
gate=$(curl -s -X POST "127.0.0.1:$PORT/v1/decide" -H 'content-type: application/json' \
  -d '{"kind":"mcp.call","venture":"media-api","initiator":"routine","initiator_id":"support-triage","name":"gmail.send_message","url":"https://api.stripe.com/x"}')
echo "$gate" | grep -q '"effect":"gate"' && check 1 "a routine sending mail is gated" || check 0 "send gate"

deny=$(curl -s -X POST "127.0.0.1:$PORT/v1/decide" -H 'content-type: application/json' \
  -d '{"kind":"file.write","venture":"media-api","path":"/sandboxes/other-venture/x"}')
echo "$deny" | grep -q 'isolation.write_root' && check 1 "cross-venture write is denied" || check 0 "isolation"

meta=$(curl -s -X POST "127.0.0.1:$PORT/v1/decide" -H 'content-type: application/json' \
  -d '{"kind":"http.request","venture":"media-api","url":"http://169.254.169.254/latest/meta-data/"}')
echo "$meta" | grep -q 'metadata_or_internal' && check 1 "cloud metadata is denied" || check 0 "metadata"

# --- an approval resolves exactly once
ap=$(echo "$gate" | python3 -c 'import json,sys;print(json.load(sys.stdin)["approval_id"])')
r1=$(curl -s -o /dev/null -w '%{http_code}' -X POST "127.0.0.1:$PORT/v1/approvals/$ap" -H 'content-type: application/json' -d '{"decision":"approved","by":"smoke"}')
r2=$(curl -s -o /dev/null -w '%{http_code}' -X POST "127.0.0.1:$PORT/v1/approvals/$ap" -H 'content-type: application/json' -d '{"decision":"denied","by":"smoke"}')
[ "$r1" = "200" ] && [ "$r2" = "409" ] && check 1 "approval resolves once (200 then 409)" || { check 0 "approval exactly-once ($r1/$r2)"; }

# --- console + overview
curl -s "127.0.0.1:$PORT/" | grep -q "OpenBot OS" && check 1 "console renders" || check 0 "console"
curl -s "127.0.0.1:$PORT/v1/overview" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert d["company"]["ok"] and len(d["routines"]["routines"])>=6' \
  && check 1 "overview carries company + routines" || check 0 "overview"

echo
if [ "$fail" -eq 0 ]; then echo "SMOKE PASS — the control plane works end to end on a clean database."; exit 0; fi
echo "SMOKE FAIL — $fail check(s)"; echo "--- server log:"; tail -20 "$LOG"; exit 1
