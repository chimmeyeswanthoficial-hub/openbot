#!/usr/bin/env bash
# Verifies the post-mortem ledger is real, not decoration.
#   1. every line parses and has the required fields
#   2. rule_kind is one of the allowed values
#   3. rule_ref exists (a file path, optionally with ::test_name)
#   4. no duplicate ids
# Exit 1 on any failure — this is meant to run in CI before a deploy.
set -uo pipefail
LEDGER="${1:-.openbot/post_mortems/error_registry.jsonl}"
fail=0
python3 - "$LEDGER" <<'PY'
import json, os, sys, pathlib
ledger = sys.argv[1]
allowed = {"test", "policy", "type", "lint", "prompt", "routine-change"}
required = {"id", "ts", "venture", "severity", "class", "root_cause", "fix",
            "prevention_rule", "rule_kind", "rule_ref"}
ids, bad = set(), 0
lines = [l for l in open(ledger, encoding="utf-8") if l.strip()]
for n, line in enumerate(lines, 1):
    try:
        d = json.loads(line)
    except json.JSONDecodeError as e:
        print(f"line {n}: not JSON ({e})"); bad += 1; continue
    missing = required - set(d)
    if missing:
        print(f"line {n} ({d.get('id','?')}): missing {sorted(missing)}"); bad += 1; continue
    if d["id"] in ids:
        print(f"line {n}: duplicate id {d['id']}"); bad += 1
    ids.add(d["id"])
    if d["rule_kind"] not in allowed:
        print(f"line {n}: rule_kind {d['rule_kind']!r} not in {sorted(allowed)}"); bad += 1
    ref = d["rule_ref"].split("::")[0]
    if d["rule_kind"] in {"test", "policy", "lint"} and not pathlib.Path(ref).exists():
        print(f"line {n}: rule_ref {ref!r} does not exist"); bad += 1
    if d["rule_kind"] == "prompt" and "evals" not in d.get("rule_ref", ""):
        print(f"line {n}: prompt rules need an eval case (rule_ref must name services/evals/...)"); bad += 1
print(f"{len(lines)} entries, {bad} problem(s)")
sys.exit(1 if bad else 0)
PY
fail=$?
exit $fail
