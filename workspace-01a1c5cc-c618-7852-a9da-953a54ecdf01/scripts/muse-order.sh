#!/usr/bin/env bash
# Run one work order through Muse Code, and keep the evidence.
#
#   scripts/muse-order.sh path/to/order.md            # headless, recorded
#   scripts/muse-order.sh order.md --provider echo    # no model key needed (echo mode)
#
# What it does (per .claude/skills/agent-delegation):
#   * validates the order has Outcome / Acceptance / Stop-and-ask sections
#   * runs `muse exec --json` headless, streaming JSONL events to .openbot/runs/<id>/events.jsonl
#   * exports the durable session trace (redacted) to .openbot/runs/<id>/trace.json
#   * writes <id>/meta.json with exit code, wall time, order sha — so agent cost is auditable
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
ORDER="${1:?usage: scripts/muse-order.sh <order.md> [extra muse exec flags]}"; shift || true
MUSE="${MUSE_BIN:-$HOME/.local/bin/muse}"

[ -f "$ORDER" ] || { echo "no such order: $ORDER" >&2; exit 2; }
for section in "Outcome" "Acceptance" "Stop and ask"; do
  grep -qi "^#* *$section" "$ORDER" || { echo "order is missing a '$section' section" >&2; exit 2; }
done

RUN_ID="order-$(date +%Y%m%dT%H%M%S)-$(sha256sum "$ORDER" | cut -c1-6)"
DIR=".openbot/runs/$RUN_ID"; mkdir -p "$DIR"; cp "$ORDER" "$DIR/order.md"
start=$(date +%s)
"$MUSE" exec --json --prompt-file "$DIR/order.md" "$@" 2>"$DIR/stderr.log" | tee "$DIR/events.jsonl"
code=${PIPESTATUS[0]}
end=$(date +%s)
"$MUSE" export --last --redacted --out "$DIR/trace.json" >>"$DIR/stderr.log" 2>&1 || true
python3 - "$DIR" "$code" "$((end-start))" <<'PY'
import json, pathlib, sys, hashlib
d, code, secs = pathlib.Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
order = (d / "order.md").read_bytes()
meta = {"run_id": d.name, "exit_code": code, "wall_s": secs,
        "order_sha256": hashlib.sha256(order).hexdigest()[:16],
        "trace": (d / "trace.json").exists(), "events": (d / "events.jsonl").stat().st_size}
(d / "meta.json").write_text(json.dumps(meta, indent=2))
print(json.dumps(meta))
PY
exit "$code"
