#!/usr/bin/env bash
# OpenBot OS — the go/no-go gate.
#
#   scripts/verify.sh          full check, prints PASS/FAIL per item, exits 1 on any FAIL
#   scripts/verify.sh --quick  skips the repo-dependency check (still runs the rest)
#
# This is the script that answers "is OpenBot OS good for go?" — and it is allowed to say no.
set -uo pipefail
cd "$(dirname "$0")/.." || exit 1
QUICK=0; [ "${1:-}" = "--quick" ] && QUICK=1
PASS=0; FAIL=0; WARN=0
ok()   { printf '  \033[32mPASS\033[0m  %s\n' "$1"; PASS=$((PASS+1)); }
bad()  { printf '  \033[31mFAIL\033[0m  %s\n' "$1"; FAIL=$((FAIL+1)); }
warn() { printf '  \033[33mWARN\033[0m  %s\n' "$1"; WARN=$((WARN+1)); }
head_() { printf '\n\033[1m%s\033[0m\n' "$1"; }

PY=${PYTHON:-python3}

head_ "1. Artifacts present"
for f in plan.md aboutme.md disadvantages.md advantages.md FEATURES.md BLOCKERS.md \
         STACK_DECISIONS.md INSTALL_LOG.md company/company.yaml; do
  [ -s "$f" ] && ok "$f" || bad "$f missing or empty"
done

head_ "2. Governance layer"
if ( $PY -m pytest >/tmp/verify-pytest.log 2>&1 ); then
  n=$(tail -2 /tmp/verify-pytest.log | grep -oE '[0-9]+ passed' | head -1)
  ok "test suite (every service): ${n:-green}"
else
  bad "sentinel tests failed — see /tmp/verify-pytest.log"; tail -5 /tmp/verify-pytest.log | sed 's/^/        /'
fi
if bash .claude/skills/postmortem/check.sh >/tmp/verify-ledger.log 2>&1; then
  ok "post-mortem ledger: $(tail -1 /tmp/verify-ledger.log)"
else
  bad "post-mortem ledger invalid — $(tail -1 /tmp/verify-ledger.log)"
fi
if $PY -c "
import sys; sys.path.insert(0,'services/sentinel')
from company import load_company
c = load_company(company_month_cap_usd=300)
print(f'roles={len(c.roles)} duties={len(c.duties)} prohibitions={len(c.prohibitions)}')
" >/tmp/verify-company.log 2>&1; then
  ok "company definition operable: $(cat /tmp/verify-company.log)"
else
  bad "company definition not operable: $(tail -3 /tmp/verify-company.log | tr '\n' ' ')"
fi
PYTHONPATH=packages/venture-sdk/src $PY -m venture_sdk validate "$PWD/.openbot/ventures" >/tmp/verify-ventures.log 2>&1
if [ $? -eq 0 ]; then
  ok "every venture manifest is operable ($(grep -c '^OK' /tmp/verify-ventures.log 2>/dev/null || echo 1) venture(s))"
else
  bad "a venture manifest is not operable: $(tail -2 /tmp/verify-ventures.log | tr '\n' ' ')"
fi
if bash scripts/os-markers.sh --check >/dev/null 2>&1; then
  ok "upstream markers match patches/OPENBOT-OS.md"; else bad "marker/doc mismatch"; fi
if $PY -m ruff check services packages scripts >/dev/null 2>&1; then
  ok "ruff clean"; else bad "ruff findings — run make lint"; fi

# A suite made only of test files proves nothing about a stranger's fresh clone: pytest would pass
# without the package being importable. Check the import surface a newcomer actually uses.
MISSING=""
for mod in fastapi pydantic yaml uvicorn; do
  $PY - "$mod" <<'EOF' 2>/dev/null || MISSING="$MISSING $mod"
import importlib, sys
importlib.import_module(sys.argv[1])
EOF
done
if [ -z "$MISSING" ]; then
  ok "runtime deps importable (fastapi, pydantic, yaml, uvicorn)"
else
  bad "missing runtime deps:$MISSING — run: pip install -r requirements.txt"
fi

drift=""
for f in plan.md aboutme.md advantages.md disadvantages.md FEATURES.md BLOCKERS.md \
         STACK_DECISIONS.md INSTALL_LOG.md CONTRIBUTING.md SECURITY.md CHANGELOG.md ROADMAP.md PROJECT_STATE.md PROJECT_REMAINING.md; do
  cmp -s "$f" "docs/$f" || drift="$drift $f"
done
if [ -z "$drift" ]; then ok "docs/ mirrors the root documents"; else bad "docs/ stale:$drift (run scripts/sync-docs.sh)"; fi

head_ "3. Routines: budgeted, bounded, unattended"
$PY - <<'PY'
import glob, sys, yaml
bad = 0; n = 0
for f in sorted(glob.glob('.openbot/routines/*.md')):
    n += 1
    text = open(f).read()
    if not text.startswith('---'):
        print(f"  FAIL  {f}: no front-matter"); bad += 1; continue
    fm = yaml.safe_load(text[3:text.find('\n---', 3)]) or {}
    need = ['id', 'bot', 'schedule', 'budget_usd', 'max_runtime_min', 'initiator']
    miss = [k for k in need if not fm.get(k)]
    if miss: print(f"  FAIL  {f}: missing {miss}"); bad += 1
    elif fm['initiator'] != 'routine':
        print(f"  FAIL  {f}: initiator must be 'routine'"); bad += 1
print(f"  {'PASS' if not bad else 'FAIL'}  {n} routines, {bad} problem(s)")
sys.exit(1 if bad else 0)
PY
[ $? -eq 0 ] && PASS=$((PASS+1)) || FAIL=$((FAIL+1))

head_ "4. Workspace budget (your snapshot is capped)"
$PY - <<'PY'
import os, sys
EXCL={'.arena','.cache','.local','.mypy_cache','.next','.nox','.npm','.nuxt','.output','.parcel-cache','.playwright-cli','.pytest_cache','.ruff_cache','.svelte-kit','.tox','.turbo','.venv','.vite','__pycache__','build','coverage','dist','node_modules','out','target'}
tot=n=0
for r,d,f in os.walk('.', topdown=True):
    d[:] = [x for x in d if x not in EXCL]
    for name in f:
        try: tot += os.path.getsize(os.path.join(r,name)); n += 1
        except OSError: pass
mb, budget = tot/1e6, 128.0
print(f"  {'PASS' if mb < budget and n < 10000 else 'WARN'}  {mb:.1f} MB / {budget:.0f} MB, {n} / 10,000 files")
sys.exit(0 if mb < budget and n < 10000 else 2)
PY
case $? in 0) PASS=$((PASS+1));; *) WARN=$((WARN+1));; esac

head_ "5. Substrate (needs the VPS — expected to fail here)"
# A stranger booting the API with nothing but requirements.txt must get /healthz, not a traceback.
# This is the cheapest possible answer to "does it actually run?", and it is skipped, not faked,
# when the port is busy.
$PY -m uvicorn app:app --app-dir services/sentinel --host 127.0.0.1 --port 8097 \
  >/tmp/verify-healthz.log 2>&1 &
BOOT_PID=$!
BOOTED=""
for _ in $(seq 1 40); do
  if curl -fsS http://127.0.0.1:8097/healthz >/tmp/verify-healthz.json 2>/dev/null; then BOOTED=1; break; fi
  sleep 0.5
done
kill "$BOOT_PID" 2>/dev/null; wait "$BOOT_PID" 2>/dev/null
if [ -n "$BOOTED" ] && grep -q '"ok"' /tmp/verify-healthz.json; then
  ok "the API boots from a clean database and answers /healthz: $(cat /tmp/verify-healthz.json)"
else
  bad "the API did not answer /healthz when booted fresh — see /tmp/verify-healthz.log"
fi
if command -v docker >/dev/null 2>&1; then ok "docker present"; else warn "docker absent: OpenBot computers/supervisor cannot start (BLOCKERS B1)"; fi
if curl -sf -m 3 localhost:8090/healthz >/dev/null 2>&1; then ok "sentinel answering on :8090"; else warn "sentinel not running (start it: services/sentinel/uvicorn app:app --port 8090)"; fi
if [ -d repos/OpenBot/node_modules ]; then ok "OpenBot dependencies installed"; else warn "OpenBot dependencies absent (bun install)"; fi
[ -d repos/OpenBot/.env ] && ok "OpenBot .env present" || warn "OpenBot .env absent: no Intelligence project or model key (BLOCKERS B4/B5)"

head_ "6. Unattended-readiness (the honest part)"
warn "model + payment accounts missing by design — nothing model-driven can run yet (C4)"
warn "no git history in repos/ (tarball install) — upstream-merge has nothing to rebase (B3)"
warn "dead-man's switch not installed (B10)"
# The kill switch is the one script that must work when everything else is on fire: callable, and
# refusing a bad argument *without* touching state.
NOT_EXEC=$(find scripts -name '*.sh' ! -perm -u+x | tr '\n' ' ')
if [ -z "$NOT_EXEC" ]; then ok "every script is executable"; else bad "not executable:$NOT_EXEC"; fi
BEFORE=$(md5sum .openbot/state/active_ventures.yaml | cut -d' ' -f1)
if bash scripts/pause-all.sh --definitely-not-an-argument >/dev/null 2>&1; then
  bad "the kill switch accepted an unknown argument"
else
  AFTER=$(md5sum .openbot/state/active_ventures.yaml | cut -d' ' -f1)
  if [ "$BEFORE" = "$AFTER" ]; then
    ok "kill switch refuses an unknown argument and leaves state untouched"
  else
    bad "the kill switch mutated state on a rejected argument"
  fi
fi

head_ "Summary"
printf '  %d pass, %d fail, %d warn\n' "$PASS" "$FAIL" "$WARN"
if [ "$FAIL" -gt 0 ]; then
  printf '\n\033[31mNOT GO\033[0m — fix the FAILs above.\n'; exit 1
fi
printf '\n\033[32mGO for the parts that are built.\033[0m The WARNs are the known, documented blockers\n'
printf '(BLOCKERS.md); they are calendar work, not code work. Re-run this after each blocker.\n'
