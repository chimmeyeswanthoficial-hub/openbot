#!/usr/bin/env bash
# OpenBot OS — the kill switch. Stops every venture and every duty, writes an audit row.
#
#   scripts/pause-all.sh                    pause everything (asks for confirmation)
#   scripts/pause-all.sh --yes              no prompt (for a pager or cron)
#   scripts/pause-all.sh --venture media-api  pause one venture
#
# What it actually does:
#   1. flips `paused: true` in .openbot/state/active_ventures.yaml
#   2. writes a sev1 audit row to .openbot/post_mortems/error_registry.jsonl
#      (rule_kind: policy — the rule is "paused ventures do not run", enforced by the worker)
#   3. stops the Sentinel process if it is running on this host
#   4. prints what a human must do to resume
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
ASSUME_YES=0; VENTURE=""
while [ $# -gt 0 ]; do case "$1" in
  --yes|-y) ASSUME_YES=1;; --venture) VENTURE="${2:-}"; shift;; *) echo "unknown arg: $1" >&2; exit 2;; esac; shift; done

target="${VENTURE:-ALL}"
if [ "$ASSUME_YES" -ne 1 ]; then
  printf 'This stops %s and records a sev1. Type PAUSE to continue: ' "$target"
  read -r answer; [ "$answer" = "PAUSE" ] || { echo "aborted, nothing changed"; exit 1; }
fi

stamp=$(date -u +%Y-%m-%dT%H:%M:%SZ)
id="pm_$(date -u +%Y_%m_%d)_pause_$(date -u +%H%M%S)"

# 1. state
python3 - "$VENTURE" <<'PY'
import sys, yaml, pathlib
p = pathlib.Path('.openbot/state/active_ventures.yaml')
d = yaml.safe_load(p.read_text()) or {}
only = sys.argv[1] if len(sys.argv) > 1 else ''
for v in d.get('ventures', []):
    if not only or v.get('slug') == only:
        v['paused'] = True
        v['status'] = 'paused'
p.write_text(yaml.safe_dump(d, sort_keys=False))
print("state:", ", ".join(f"{v['slug']}={v.get('status')}" for v in d.get('ventures', [])))
PY

# 2. the ledger entry (append-only; never edit history)
python3 - "$id" "$stamp" "$target" <<'PY'
import json, sys
id_, ts, target = sys.argv[1], sys.argv[2], sys.argv[3]
row = {"id": id_, "ts": ts, "venture": target.lower(), "run_id": "pause-all",
       "severity": "sev1", "class": "manual-pause",
       "symptom": f"operator paused {target}",
       "root_cause": "human decision (kill switch, incident, or travel)",
       "fix": "nothing to fix; resume only after the reasons in plan.md §8 are met",
       "prevention_rule": "a paused venture never runs: the worker refuses any run whose venture is paused, and the Sentinel denies every action for it",
       "rule_kind": "policy",
       "rule_ref": ".openbot/state/active_ventures.yaml",
       "impact": {"customers_affected": 0, "revenue_usd": 0, "duration_min": 0}}
with open('.openbot/post_mortems/error_registry.jsonl', 'a') as f:
    f.write(json.dumps(row) + "\n")
print("ledger: appended", id_)
PY

# 3. stop the sentinel on this host, if any
if curl -sf -m 2 localhost:8090/healthz >/dev/null 2>&1; then
  pkill -f "uvicorn app:app" 2>/dev/null && echo "sentinel: stopped" || echo "sentinel: could not stop (check manually)"
else
  echo "sentinel: not running"
fi

cat <<TXT

PAUSED: $target
  - workers/agents must read .openbot/state/active_ventures.yaml before every run
  - to resume: set paused: false, give a reason in the ledger, then re-run scripts/verify.sh
  - approvals already pending stay pending; they do NOT auto-approve
TXT
